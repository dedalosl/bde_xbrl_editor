"""Shared background workers for long-running UI loading flows."""

from __future__ import annotations

import multiprocessing
import queue
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from bde_xbrl_editor.taxonomy import (
    LoaderSettings,
    TaxonomyCache,
    TaxonomyLoader,
    TaxonomyLoadError,
)


def _instance_load_process_entry(
    path: str,
    settings: LoaderSettings,
    preloaded_taxonomy: object | None,
    result_queue,
) -> None:
    """Run instance parsing in a dedicated process to avoid UI-thread starvation."""
    from bde_xbrl_editor.instance.models import (  # noqa: PLC0415
        InstanceParseError,
        TaxonomyResolutionError,
    )
    from bde_xbrl_editor.instance.parser import InstanceParser  # noqa: PLC0415

    loader = TaxonomyLoader(cache=TaxonomyCache(), settings=settings)
    parser = InstanceParser(taxonomy_loader=loader)
    resolved_taxonomy = None

    def on_progress(message: str, current: int, total: int) -> None:
        result_queue.put(("progress", message, current, total))

    def on_taxonomy_ready(taxonomy: object) -> None:
        nonlocal resolved_taxonomy
        resolved_taxonomy = taxonomy

    try:
        instance, orphaned_facts = parser.load(
            path,
            progress_callback=on_progress,
            taxonomy_resolved_callback=on_taxonomy_ready,
            preloaded_taxonomy=preloaded_taxonomy,
        )
        taxonomy = resolved_taxonomy or preloaded_taxonomy
        if taxonomy is None:
            on_progress("Preparing editor…", 96, 100)
            taxonomy = loader.load(instance.taxonomy_entry_point, progress_callback=on_progress)
        result_queue.put(("finished", instance, taxonomy, len(orphaned_facts)))
    except TaxonomyResolutionError as exc:
        result_queue.put(("error", str(exc)))
    except InstanceParseError as exc:
        result_queue.put(("error", str(exc)))
    except Exception as exc:  # noqa: BLE001
        result_queue.put(("error", f"Unexpected error: {exc}"))


def _parse_instance_with_preloaded_taxonomy(
    path: str,
    settings: LoaderSettings,
    preloaded_taxonomy: object,
    *,
    progress_callback,
) -> tuple[object, object, int]:
    """Parse an instance in the current worker thread when taxonomy is already loaded.

    This avoids serializing a large TaxonomyStructure into and back out of a
    spawned process for the common "open another instance for the current
    taxonomy" workflow.
    """
    from bde_xbrl_editor.instance.parser import InstanceParser  # noqa: PLC0415

    loader = TaxonomyLoader(cache=TaxonomyCache(), settings=settings)
    parser = InstanceParser(taxonomy_loader=loader)
    instance, orphaned_facts = parser.load(
        path,
        progress_callback=progress_callback,
        preloaded_taxonomy=preloaded_taxonomy,
    )

    return instance, preloaded_taxonomy, len(orphaned_facts)


def _table_layout_process_entry(
    request_id: int,
    table: object,
    taxonomy: object,
    instance: object,
    z_index: int,
    z_constraints: object,
    result_queue,
) -> None:
    """Compute a table layout in a dedicated process to keep the UI responsive."""
    from bde_xbrl_editor.table_renderer.errors import (  # noqa: PLC0415
        TableLayoutError,
        ZIndexOutOfRangeError,
    )
    from bde_xbrl_editor.table_renderer.layout_engine import TableLayoutEngine  # noqa: PLC0415

    engine = TableLayoutEngine(taxonomy)

    try:
        layout = engine.compute(
            table, instance=instance, z_index=z_index, z_constraints=z_constraints
        )
        result_queue.put(("finished", request_id, layout, ""))
    except TableLayoutError as exc:
        try:
            layout = engine.compute(
                table, instance=None, z_index=z_index, z_constraints=z_constraints
            )
        except Exception:  # noqa: BLE001
            result_queue.put(("error", request_id, f"Table layout warning: {exc.reason}"))
        else:
            result_queue.put(("finished", request_id, layout, exc.reason))
    except ZIndexOutOfRangeError as exc:
        result_queue.put(("error", request_id, str(exc)))
    except Exception as exc:  # noqa: BLE001
        result_queue.put(("error", request_id, f"Unexpected error: {exc}"))


class TaxonomyLoadWorker(QObject):
    """Worker that runs ``TaxonomyLoader.load()`` in a background thread."""

    finished = Signal(object)
    error = Signal(str)
    progress = Signal(str, int, int)

    def __init__(self, loader: TaxonomyLoader, path: str | Path) -> None:
        super().__init__()
        self._loader = loader
        self._path = str(path)

    def run(self) -> None:
        def on_progress(message: str, current: int, total: int) -> None:
            self.progress.emit(message, current, total)

        try:
            structure = self._loader.load(self._path, progress_callback=on_progress)
            skipped = self._loader.last_skipped_urls
            self.finished.emit((structure, skipped))
        except TaxonomyLoadError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Unexpected error: {exc}")


class InstanceLoadWorker(QObject):
    """Supervisor that performs instance loading in a separate process."""

    finished = Signal(object, object)  # (XbrlInstance, TaxonomyStructure)
    error = Signal(str)
    orphaned = Signal(int)
    progress = Signal(str, int, int)
    taxonomy_resolved = Signal(object)

    def __init__(self, cache: TaxonomyCache, settings: LoaderSettings, path: str | Path) -> None:
        super().__init__()
        self._settings = settings
        self._path = str(path)
        self._preloaded_taxonomy = None

    def set_preloaded_taxonomy(self, taxonomy: object | None) -> None:
        """Provide a resolved taxonomy that can be reused inside the worker process."""
        self._preloaded_taxonomy = taxonomy

    def run(self) -> None:
        if self._preloaded_taxonomy is not None:
            self._run_with_preloaded_taxonomy()
            return

        ctx = multiprocessing.get_context("spawn")
        result_queue = ctx.Queue()
        process = ctx.Process(
            target=_instance_load_process_entry,
            args=(self._path, self._settings, self._preloaded_taxonomy, result_queue),
            daemon=True,
        )

        finished = False
        process.start()

        try:
            while True:
                try:
                    message = result_queue.get(timeout=0.1)
                except queue.Empty:
                    if process.is_alive():
                        continue
                    if not finished:
                        exit_code = process.exitcode
                        if exit_code == 0:
                            self.error.emit("Instance load ended unexpectedly without a result.")
                        else:
                            self.error.emit(
                                f"Instance load process exited unexpectedly (code {exit_code})."
                            )
                    break

                kind = message[0]
                if kind == "progress":
                    _, text, current, total = message
                    self.progress.emit(text, current, total)
                elif kind == "taxonomy_resolved":
                    _, taxonomy = message
                    self.taxonomy_resolved.emit(taxonomy)
                elif kind == "finished":
                    _, instance, taxonomy, orphaned_count = message
                    if orphaned_count:
                        self.orphaned.emit(orphaned_count)
                    self.progress.emit(
                        f"Instance ready — {len(instance.facts)} facts, {len(instance.contexts)} contexts",
                        100,
                        100,
                    )
                    self.finished.emit(instance, taxonomy)
                    finished = True
                    break
                elif kind == "error":
                    _, error_message = message
                    self.error.emit(error_message)
                    finished = True
                    break
        finally:
            if process.is_alive():
                process.join(timeout=0.2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=0.5)
            result_queue.close()

    def _run_with_preloaded_taxonomy(self) -> None:
        """Load an instance in this worker thread when the taxonomy is already warm."""

        def on_progress(message: str, current: int, total: int) -> None:
            self.progress.emit(message, current, total)

        try:
            instance, taxonomy, orphaned_count = _parse_instance_with_preloaded_taxonomy(
                self._path,
                self._settings,
                self._preloaded_taxonomy,
                progress_callback=on_progress,
            )
            if orphaned_count:
                self.orphaned.emit(orphaned_count)
            self.progress.emit(
                f"Instance ready — {len(instance.facts)} facts, {len(instance.contexts)} contexts",
                100,
                100,
            )
            self.finished.emit(instance, taxonomy)
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class TableLayoutLoadWorker(QObject):
    """Supervisor that computes a table layout in a separate process."""

    finished = Signal(int, object, str)  # request_id, layout, warning
    error = Signal(int, str)  # request_id, message

    def __init__(
        self,
        request_id: int,
        table: object,
        taxonomy: object,
        instance: object,
        z_index: int = 0,
        z_constraints: object = None,
    ) -> None:
        super().__init__()
        self._request_id = request_id
        self._table = table
        self._taxonomy = taxonomy
        self._instance = instance
        self._z_index = z_index
        self._z_constraints = z_constraints
        self._cancelled = False
        self._process = None

    def cancel(self) -> None:
        self._cancelled = True
        process = self._process
        if process is not None and process.is_alive():
            process.terminate()

    def run(self) -> None:
        ctx = multiprocessing.get_context("spawn")
        result_queue = ctx.Queue()
        process = ctx.Process(
            target=_table_layout_process_entry,
            args=(
                self._request_id,
                self._table,
                self._taxonomy,
                self._instance,
                self._z_index,
                self._z_constraints,
                result_queue,
            ),
            daemon=True,
        )
        self._process = process

        finished = False
        process.start()

        try:
            while True:
                if self._cancelled:
                    break
                try:
                    message = result_queue.get(timeout=0.1)
                except queue.Empty:
                    if process.is_alive():
                        continue
                    if not finished and not self._cancelled:
                        exit_code = process.exitcode
                        if exit_code == 0:
                            self.error.emit(
                                self._request_id,
                                "Table layout ended unexpectedly without a result.",
                            )
                        else:
                            self.error.emit(
                                self._request_id,
                                f"Table layout process exited unexpectedly (code {exit_code}).",
                            )
                    break

                kind = message[0]
                if self._cancelled:
                    break
                if kind == "finished":
                    _, request_id, layout, warning = message
                    self.finished.emit(request_id, layout, warning)
                    finished = True
                    break
                if kind == "error":
                    _, request_id, error_message = message
                    self.error.emit(request_id, error_message)
                    finished = True
                    break
        finally:
            if process.is_alive():
                process.join(timeout=0.2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=0.5)
            result_queue.close()
            self._process = None

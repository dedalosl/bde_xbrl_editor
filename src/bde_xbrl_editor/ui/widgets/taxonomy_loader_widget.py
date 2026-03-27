"""TaxonomyLoaderWidget — file-picker + load trigger with background thread loading."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from bde_xbrl_editor.taxonomy import (
    LoaderSettings,
    TaxonomyCache,
    TaxonomyLoader,
    TaxonomyLoadError,
    TaxonomyStructure,
)
from bde_xbrl_editor.ui.widgets.progress_dialog import TaxonomyProgressDialog


class _LoadWorker(QObject):
    """Worker that runs TaxonomyLoader.load() in a background QThread."""

    finished = Signal(object)   # TaxonomyStructure
    error = Signal(str)         # error message string
    progress = Signal(str, int, int)

    def __init__(self, loader: TaxonomyLoader, path: str) -> None:
        super().__init__()
        self._loader = loader
        self._path = path

    def run(self) -> None:
        def on_progress(msg: str, current: int, total: int) -> None:
            self.progress.emit(msg, current, total)

        try:
            structure = self._loader.load(self._path, progress_callback=on_progress)
            self.finished.emit(structure)
        except TaxonomyLoadError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Unexpected error: {exc}")


class TaxonomyLoaderWidget(QWidget):
    """File-picker widget for selecting and loading a BDE taxonomy.

    Signals:
        taxonomy_loaded(TaxonomyStructure): Emitted on successful load.
    """

    taxonomy_loaded = Signal(object)  # TaxonomyStructure

    def __init__(
        self,
        cache: TaxonomyCache | None = None,
        settings: LoaderSettings | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._cache = cache or TaxonomyCache()
        self._settings = settings or LoaderSettings()
        self._loader = TaxonomyLoader(cache=self._cache, settings=self._settings)
        self._thread: QThread | None = None
        self._worker: _LoadWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        label = QLabel("Taxonomy entry-point (.xsd):")
        layout.addWidget(label)

        path_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select the taxonomy entry-point XSD file…")
        path_row.addWidget(self._path_edit)

        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        button_row = QHBoxLayout()
        self._load_btn = QPushButton("Load Taxonomy")
        self._load_btn.setDefault(True)
        self._load_btn.clicked.connect(self._on_load)
        button_row.addWidget(self._load_btn)

        settings_btn = QPushButton("Settings…")
        settings_btn.clicked.connect(self._on_settings)
        button_row.addWidget(settings_btn)
        layout.addLayout(button_row)

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Taxonomy Entry Point",
            "",
            "XBRL Schema Files (*.xsd);;All Files (*)",
        )
        if path:
            self._path_edit.setText(path)

    def _on_load(self) -> None:
        path = self._path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "No File Selected", "Please select a taxonomy entry-point file.")
            return
        if not Path(path).exists():
            QMessageBox.warning(self, "File Not Found", f"File not found:\n{path}")
            return

        self._load_btn.setEnabled(False)

        self._progress_dialog = TaxonomyProgressDialog(self)
        self._progress_dialog.show()

        self._worker = _LoadWorker(self._loader, path)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_load_finished)
        self._worker.error.connect(self._on_load_error)
        self._worker.progress.connect(self._progress_dialog.as_callback().__call__)
        self._thread.start()

    def _on_load_finished(self, structure: TaxonomyStructure) -> None:
        self._cleanup_thread()
        self._progress_dialog.close()
        self._load_btn.setEnabled(True)
        self.taxonomy_loaded.emit(structure)

    def _on_load_error(self, message: str) -> None:
        self._cleanup_thread()
        self._progress_dialog.close()
        self._load_btn.setEnabled(True)
        QMessageBox.critical(self, "Taxonomy Load Error", message)

    def _cleanup_thread(self) -> None:
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
            self._worker = None

    def _on_settings(self) -> None:
        """Open the LoaderSettings dialog."""
        from bde_xbrl_editor.ui.widgets.loader_settings_dialog import LoaderSettingsDialog

        dialog = LoaderSettingsDialog(self._settings, self)
        if dialog.exec():
            self._settings = dialog.get_settings()
            self._loader = TaxonomyLoader(cache=self._cache, settings=self._settings)

"""TaxonomyLoaderWidget — welcome screen with two panels: Open Taxonomy / Open Instance."""

from __future__ import annotations

import contextlib
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from bde_xbrl_editor.performance import LoadTiming, StageTiming, format_duration
from bde_xbrl_editor.taxonomy import (
    LoaderSettings,
    TaxonomyCache,
    TaxonomyLoader,
)
from bde_xbrl_editor.ui import theme
from bde_xbrl_editor.ui.loading import InstanceLoadWorker, TaxonomyLoadWorker
from bde_xbrl_editor.ui.widgets.loader_settings_dialog import (
    add_recent_file,
    add_recent_instance,
    load_recent_files,
    load_recent_instances,
)
from bde_xbrl_editor.ui.widgets.progress_dialog import TaxonomyProgressDialog

# ── Palette ────────────────────────────────────────────────────────────────
_NAVY = theme.NAV_BG_DEEP
_NAVY_MID = theme.NAV_BG_DARK
_NAVY_LIGHT = theme.NAV_BG
_ACCENT = theme.ACCENT
_BG = theme.WINDOW_BG
_CARD_BG = theme.SURFACE_BG
_TEXT_MAIN = theme.TEXT_MAIN
_TEXT_MUTED = theme.TEXT_MUTED
_BORDER = theme.BORDER
_HOVER_ROW = theme.HOVER_BG


class _RecentFileRow(QFrame):
    """A single clickable row in the Recent Files list."""

    clicked = Signal(str)

    def __init__(self, path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = path
        p = Path(path)
        self._file_name = p.name
        self._directory = str(p.parent)

        self.setObjectName("RecentFileRow")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_row_style(hovered=False, pressed=False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        icon = QLabel("◈")
        icon.setStyleSheet(
            f"color: {_ACCENT}; font-size: 14px; font-weight: bold;"
            f" background: {theme.SURFACE_ALT_BG}; border-radius: 10px; padding: 4px 6px;"
        )
        icon.setFixedWidth(28)
        layout.addWidget(icon)

        text_wrap = QWidget()
        text_wrap.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        text_wrap.setMinimumWidth(0)

        text_col = QVBoxLayout(text_wrap)
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(2)

        name_lbl = QLabel(p.name)
        name_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        name_lbl.setMinimumWidth(0)
        name_lbl.setWordWrap(False)
        name_lbl.setStyleSheet(
            f"color: {_TEXT_MAIN}; font-weight: bold; font-size: 12px; background: transparent;"
        )
        text_col.addWidget(name_lbl)

        dir_lbl = QLabel(self._directory)
        dir_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        dir_lbl.setMinimumWidth(0)
        dir_lbl.setWordWrap(False)
        dir_lbl.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 10px; background: transparent;"
        )
        text_col.addWidget(dir_lbl)

        layout.addWidget(text_wrap, stretch=1)

        arrow = QLabel("›")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setFixedSize(20, 20)
        arrow.setStyleSheet(
            f"color: {_TEXT_MUTED}; font-size: 16px; background: transparent;"
        )
        layout.addWidget(arrow)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._apply_row_style(hovered=True, pressed=True)
            self.clicked.emit(self._path)
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._apply_row_style(hovered=True, pressed=False)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._apply_row_style(hovered=False, pressed=False)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._apply_row_style(hovered=True, pressed=False)
        super().mouseReleaseEvent(event)

    def _apply_row_style(self, *, hovered: bool, pressed: bool) -> None:
        if pressed:
            background = theme.SELECTION_BG
            border = theme.BORDER_STRONG
        elif hovered:
            background = _HOVER_ROW
            border = theme.ACCENT_SOFT
        else:
            background = "transparent"
            border = "transparent"

        self.setStyleSheet(
            f"""
            QFrame#RecentFileRow {{
                background: {background};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            """
        )


class TaxonomyLoaderWidget(QWidget):
    """Welcome screen with two panels: Open Taxonomy (left) and Open Instance (right).

    Signals:
        taxonomy_loaded(TaxonomyStructure): Emitted on successful taxonomy load.
        instance_loaded(XbrlInstance, TaxonomyStructure): Emitted on successful instance load.
    """

    taxonomy_loaded = Signal(object)
    instance_loaded = Signal(object, object)  # (XbrlInstance, TaxonomyStructure)

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
        self._worker: TaxonomyLoadWorker | None = None
        self._inst_thread: QThread | None = None
        self._inst_worker: InstanceLoadWorker | None = None
        self._progress_dialog: TaxonomyProgressDialog | None = None
        self.last_taxonomy_load_timing: LoadTiming | None = None
        self.last_instance_load_timing: LoadTiming | None = None
        self._taxonomy_load_started_at: float | None = None
        self._instance_load_started_at: float | None = None
        self._setup_ui()

    # ── UI construction ────────────────────────────────────────────────────

    def _show_progress_dialog(self, title: str, initial_message: str) -> TaxonomyProgressDialog:
        if self._progress_dialog is None:
            self._progress_dialog = TaxonomyProgressDialog(self)
        self._progress_dialog.setWindowTitle(title)
        self._progress_dialog.reset()
        self._progress_dialog.setLabelText(initial_message)
        self._progress_dialog.show()
        return self._progress_dialog

    def _close_progress_dialog(self) -> None:
        if self._progress_dialog is not None:
            self._progress_dialog.close()

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"TaxonomyLoaderWidget {{ background: {_BG}; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header banner ──────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet(
            f"QFrame {{ background: qlineargradient("
            f"x1:0, y1:0, x2:1, y2:0, "
            f"stop:0 {_NAVY}, stop:1 {_NAVY_MID}); }}"
        )
        header.setFixedHeight(132)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(44, 18, 44, 18)
        header_layout.setSpacing(24)

        title_col = QVBoxLayout()
        title_col.setSpacing(6)

        eyebrow = QLabel("XBRL filing workspace")
        eyebrow.setStyleSheet(
            f"color: {theme.HEADER_BG_LIGHT}; font-size: 11px; font-weight: bold; "
            "background: transparent;"
        )
        title_col.addWidget(eyebrow)

        app_title = QLabel("BDE XBRL Editor")
        app_title.setStyleSheet(
            f"color: {theme.TEXT_INVERSE}; font-size: 28px; font-weight: bold; background: transparent;"
        )
        title_col.addWidget(app_title)

        subtitle = QLabel("Load a taxonomy first, then browse tables or open an existing filing instance.")
        subtitle.setStyleSheet(
            f"color: {theme.ACCENT_SOFT}; font-size: 12px; background: transparent;"
        )
        title_col.addWidget(subtitle)

        header_layout.addLayout(title_col)
        header_layout.addStretch()

        summary = QFrame()
        summary.setStyleSheet(
            "QFrame { background: rgba(255, 253, 248, 20); border: 1px solid rgba(255, 253, 248, 46);"
            " border-radius: 10px; }}"
        )
        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(16, 12, 16, 12)
        summary_layout.setSpacing(2)

        summary_label = QLabel("Recommended flow")
        summary_label.setStyleSheet(
            f"color: {theme.TEXT_INVERSE}; font-size: 11px; font-weight: bold; background: transparent;"
        )
        summary_layout.addWidget(summary_label)

        summary_text = QLabel("Open a taxonomy to unlock tables, metadata, validation rules, and instance editing.")
        summary_text.setWordWrap(True)
        summary_text.setStyleSheet(
            f"color: {theme.ACCENT_SOFT}; font-size: 11px; background: transparent;"
        )
        summary_layout.addWidget(summary_text)
        header_layout.addWidget(summary, stretch=0)

        outer.addWidget(header)

        # ── Main workspace area ────────────────────────────────────────
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(32, 24, 32, 20)
        content_layout.setSpacing(20)

        primary_card = self._build_taxonomy_card()
        primary_card.setMinimumWidth(560)
        content_layout.addWidget(primary_card, stretch=13)

        secondary_col = QVBoxLayout()
        secondary_col.setContentsMargins(0, 0, 0, 0)
        secondary_col.setSpacing(14)
        secondary_col.addWidget(self._build_instance_card(), stretch=0)
        secondary_col.addWidget(self._build_guidance_panel(), stretch=0)
        secondary_col.addStretch(1)

        footer = QHBoxLayout()
        footer.addStretch()
        settings_btn = QPushButton("Settings…")
        settings_btn.setFlat(True)
        settings_btn.setStyleSheet(
            f"QPushButton {{ color: {_TEXT_MUTED}; font-size: 11px; border: none;"
            f" padding: 4px 8px; background: transparent; }}"
            f"QPushButton:hover {{ color: {_NAVY}; }}"
        )
        settings_btn.clicked.connect(self._on_settings)
        footer.addWidget(settings_btn)
        secondary_col.addLayout(footer)

        secondary = QWidget()
        secondary.setLayout(secondary_col)
        secondary.setMinimumWidth(340)
        content_layout.addWidget(secondary, stretch=7)

        outer.addWidget(content, stretch=1)

    def _make_card(self) -> tuple[QFrame, QVBoxLayout]:
        """Create a styled card frame and return (card, layout)."""
        card = QFrame()
        card.setObjectName("LoaderCard")
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        card.setStyleSheet(
            f"QFrame#LoaderCard {{ background: {_CARD_BG}; border-radius: 14px;"
            f" border: 1px solid {theme.ACCENT_SOFT}; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(0)
        return card, layout

    def _add_section_header(self, layout: QVBoxLayout, title: str) -> None:
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {_TEXT_MAIN}; font-size: 16px; font-weight: bold;"
            f" border: none; background: transparent;"
        )
        layout.addWidget(lbl)
        layout.addSpacing(12)

    def _build_taxonomy_card(self) -> QFrame:
        card, layout = self._make_card()

        intro = QLabel("Start with a taxonomy")
        intro.setStyleSheet(
            f"color: {_TEXT_MAIN}; font-size: 22px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(intro)

        body = QLabel(
            "Use an entry-point schema to load the reporting structure, tables, and validations before opening or creating an instance."
        )
        body.setWordWrap(True)
        body.setStyleSheet(
            f"color: {_TEXT_MUTED}; font-size: 12px; background: transparent;"
        )
        layout.addWidget(body)
        layout.addSpacing(18)

        self._add_section_header(layout, "Taxonomy Entry Point")

        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select the taxonomy entry-point .xsd file…")
        self._path_edit.setStyleSheet(self._input_style())
        path_row.addWidget(self._path_edit)

        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(80)
        browse_btn.setStyleSheet(self._secondary_btn_style())
        browse_btn.clicked.connect(self._on_browse_taxonomy)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)
        layout.addSpacing(12)

        self._load_btn = QPushButton("Load Taxonomy")
        self._load_btn.setDefault(True)
        self._load_btn.setFixedHeight(38)
        self._load_btn.setStyleSheet(self._primary_btn_style())
        self._load_btn.clicked.connect(self._on_load)
        layout.addWidget(self._load_btn)

        hint = QLabel("After loading, you can browse tables, inspect DTS files, and open or create an XBRL instance.")
        hint.setWordWrap(True)
        hint.setStyleSheet(
            f"color: {_TEXT_MUTED}; font-size: 11px; background: transparent; padding-top: 8px;"
        )
        layout.addWidget(hint)

        recent_paths = load_recent_files()
        if recent_paths:
            layout.addSpacing(24)
            self._add_section_header(layout, "Recent Taxonomies")
            recent_intro = QLabel("Resume a recently used reporting taxonomy.")
            recent_intro.setStyleSheet(
                f"color: {_TEXT_MUTED}; font-size: 11px; background: transparent;"
            )
            layout.addWidget(recent_intro)
            layout.addSpacing(8)

            for path in recent_paths:
                row = _RecentFileRow(path)
                row.clicked.connect(self._on_recent_taxonomy_clicked)
                layout.addWidget(row)

        layout.addStretch()
        return card

    def _build_instance_card(self) -> QFrame:
        card, layout = self._make_card()

        title = QLabel("Open an existing instance")
        title.setStyleSheet(
            f"color: {_TEXT_MAIN}; font-size: 17px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(title)

        summary = QLabel(
            "If the instance already references a taxonomy, the editor will resolve it and prepare the workspace for editing."
        )
        summary.setWordWrap(True)
        summary.setStyleSheet(
            f"color: {_TEXT_MUTED}; font-size: 11px; background: transparent;"
        )
        layout.addWidget(summary)
        layout.addSpacing(18)

        self._add_section_header(layout, "Instance File")

        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        self._inst_path_edit = QLineEdit()
        self._inst_path_edit.setPlaceholderText("Select an XBRL instance file…")
        self._inst_path_edit.setStyleSheet(self._input_style())
        path_row.addWidget(self._inst_path_edit)

        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(80)
        browse_btn.setStyleSheet(self._secondary_btn_style())
        browse_btn.clicked.connect(self._on_browse_instance)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)
        layout.addSpacing(12)

        self._load_inst_btn = QPushButton("Load Instance")
        self._load_inst_btn.setFixedHeight(38)
        self._load_inst_btn.setStyleSheet(self._primary_btn_style())
        self._load_inst_btn.clicked.connect(self._on_load_instance)
        layout.addWidget(self._load_inst_btn)

        recent_instances = load_recent_instances()
        if recent_instances:
            layout.addSpacing(24)
            self._add_section_header(layout, "Recent Instances")
            layout.addSpacing(8)

            for path in recent_instances:
                row = _RecentFileRow(path)
                row.clicked.connect(self._on_recent_instance_clicked)
                layout.addWidget(row)

        layout.addStretch()
        return card

    def _build_guidance_panel(self) -> QFrame:
        panel, layout = self._make_card()
        panel.setMaximumHeight(152)

        title = QLabel("Workspace notes")
        title.setStyleSheet(
            f"color: {_TEXT_MAIN}; font-size: 13px; font-weight: bold; background: transparent;"
        )
        layout.addWidget(title)
        layout.addSpacing(8)

        notes = (
            "1. Load a taxonomy to unlock tables and validation rules.",
            "2. Open an instance to edit facts against that structure.",
            "3. Use recent files to jump back into previous work.",
        )
        for note in notes:
            row = QLabel(note)
            row.setWordWrap(True)
            row.setStyleSheet(
                f"color: {_TEXT_MUTED}; font-size: 10px; background: transparent; padding-bottom: 4px;"
            )
            layout.addWidget(row)

        layout.addStretch()
        return panel

    # ── Button / input styles ──────────────────────────────────────────────

    def _input_style(self) -> str:
        return (
            f"QLineEdit {{ border: 1px solid {_BORDER}; border-radius: 5px;"
            f" padding: 7px 10px; font-size: 12px; color: {_TEXT_MAIN};"
            f" background: {theme.INPUT_BG}; }}"
            f"QLineEdit:focus {{ border-color: {_ACCENT}; }}"
        )

    def _primary_btn_style(self) -> str:
        return (
            f"QPushButton {{ background: {_NAVY}; color: {theme.TEXT_INVERSE};"
            f" border: none; border-radius: 5px;"
            f" font-size: 13px; font-weight: bold; padding: 6px 20px; }}"
            f"QPushButton:hover {{ background: {_NAVY_MID}; }}"
            f"QPushButton:pressed {{ background: {_NAVY_LIGHT}; }}"
            f"QPushButton:disabled {{ background: {theme.DISABLED_BG}; color: {theme.DISABLED_FG}; }}"
        )

    def _secondary_btn_style(self) -> str:
        return (
            f"QPushButton {{ background: {theme.SURFACE_BG}; color: {_TEXT_MAIN};"
            f" border: 1px solid {_BORDER}; border-radius: 5px;"
            f" font-size: 12px; padding: 6px 12px; }}"
            f"QPushButton:hover {{ background: {_HOVER_ROW}; border-color: {_ACCENT}; }}"
        )

    # ── Taxonomy slots ─────────────────────────────────────────────────────

    def _on_browse_taxonomy(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Taxonomy Entry Point",
            "",
            "XBRL Schema Files (*.xsd);;All Files (*)",
        )
        if path:
            self._path_edit.setText(path)

    def _on_recent_taxonomy_clicked(self, path: str) -> None:
        self._path_edit.setText(path)
        self._on_load()

    def _on_load(self) -> None:
        path = self._path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "No File Selected", "Please select a taxonomy entry-point file.")
            return
        if not Path(path).exists():
            QMessageBox.warning(self, "File Not Found", f"File not found:\n{path}")
            return

        self._load_btn.setEnabled(False)
        self._taxonomy_load_started_at = time.perf_counter()
        self.last_taxonomy_load_timing = None

        progress_dialog = self._show_progress_dialog(
            "Loading Taxonomy…",
            "Initialising taxonomy load…",
        )
        progress_dialog.set_context("Taxonomy", path)

        self._worker = TaxonomyLoadWorker(self._loader, path)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(
            self._on_load_finished, Qt.ConnectionType.QueuedConnection
        )
        self._worker.error.connect(
            self._on_load_error, Qt.ConnectionType.QueuedConnection
        )
        self._worker.progress.connect(progress_dialog.update_progress)
        self._thread.start()

    def _on_load_finished(self, payload: object) -> None:
        structure, skipped_urls = payload  # type: ignore[misc]
        self._cleanup_thread()
        self._load_btn.setEnabled(True)
        elapsed = 0.0
        if self._taxonomy_load_started_at is not None:
            elapsed = time.perf_counter() - self._taxonomy_load_started_at
        self.last_taxonomy_load_timing = LoadTiming(
            total_seconds=elapsed,
            stages=(StageTiming("taxonomy load", elapsed),),
        )

        with contextlib.suppress(OSError):
            add_recent_file(self._path_edit.text().strip())

        if skipped_urls:
            url_list = "\n".join(f"  • {u}" for u in skipped_urls[:20])
            suffix = f"\n  … and {len(skipped_urls) - 20} more" if len(skipped_urls) > 20 else ""
            QMessageBox.warning(
                self,
                "Remote References Skipped",
                "The following remote URL(s) could not be resolved locally and were skipped.\n"
                "The taxonomy was loaded from local files only.\n\n"
                "To resolve them, add URL-to-path mappings in Settings → URL Mappings.\n\n"
                f"{url_list}{suffix}",
            )

        if self._progress_dialog is not None and elapsed > 0:
            self._progress_dialog.update_progress(
                f"Taxonomy parsed in {format_duration(elapsed)}",
                100,
                100,
            )
        self.taxonomy_loaded.emit(structure)
        self._close_progress_dialog()

    def _on_load_error(self, message: str) -> None:
        self._cleanup_thread()
        self._close_progress_dialog()
        self._load_btn.setEnabled(True)
        QMessageBox.critical(self, "Taxonomy Load Error", message)

    def _cleanup_thread(self) -> None:
        if self._thread:
            self._thread.quit()
            self._thread.wait()
            self._thread = None
            self._worker = None

    # ── Instance slots ─────────────────────────────────────────────────────

    def _on_browse_instance(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open XBRL Instance",
            "",
            "XBRL Files (*.xbrl *.xml);;All Files (*)",
        )
        if path:
            self._inst_path_edit.setText(path)

    def _on_recent_instance_clicked(self, path: str) -> None:
        self._inst_path_edit.setText(path)
        self._on_load_instance()

    def _on_load_instance(self) -> None:
        path = self._inst_path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "No File Selected", "Please select an XBRL instance file.")
            return
        if not Path(path).exists():
            QMessageBox.warning(self, "File Not Found", f"File not found:\n{path}")
            return

        self._load_inst_btn.setEnabled(False)
        self._instance_load_started_at = time.perf_counter()
        self.last_instance_load_timing = None

        progress_dialog = self._show_progress_dialog(
            "Loading Instance…",
            "Initialising instance load…",
        )
        progress_dialog.set_context("Instance", path)

        self._inst_worker = InstanceLoadWorker(self._cache, self._settings, path)
        self._inst_thread = QThread(self)
        self._inst_worker.moveToThread(self._inst_thread)
        self._inst_thread.started.connect(self._inst_worker.run)
        self._inst_worker.finished.connect(
            self._on_inst_load_finished, Qt.ConnectionType.QueuedConnection
        )
        self._inst_worker.error.connect(
            self._on_inst_load_error, Qt.ConnectionType.QueuedConnection
        )
        self._inst_worker.progress.connect(
            progress_dialog.update_progress, Qt.ConnectionType.QueuedConnection
        )
        self._inst_worker.orphaned.connect(
            self._on_inst_orphaned, Qt.ConnectionType.QueuedConnection
        )
        self._inst_thread.start()

    def _on_inst_load_finished(self, instance: object, taxonomy: object) -> None:
        self._cleanup_inst_thread()
        self._load_inst_btn.setEnabled(True)
        elapsed = 0.0
        if self._instance_load_started_at is not None:
            elapsed = time.perf_counter() - self._instance_load_started_at
        self.last_instance_load_timing = LoadTiming(
            total_seconds=elapsed,
            stages=(StageTiming("instance parse", elapsed),),
        )

        with contextlib.suppress(OSError):
            add_recent_instance(self._inst_path_edit.text().strip())
        if self._progress_dialog is not None:
            timing_text = (
                f" after {format_duration(elapsed)}" if elapsed > 0 else ""
            )
            self._progress_dialog.update_progress(
                f"Opening workspace…{timing_text}",
                100,
                100,
            )
        self.instance_loaded.emit(instance, taxonomy)
        self._close_progress_dialog()

    def _on_inst_orphaned(self, count: int) -> None:
        QMessageBox.information(
            self,
            "Orphaned Facts",
            f"{count} fact(s) in this instance have concepts not found in the "
            f"taxonomy and will be preserved verbatim on save.",
        )

    def _on_inst_load_error(self, message: str) -> None:
        self._cleanup_inst_thread()
        self._close_progress_dialog()
        self._load_inst_btn.setEnabled(True)
        QMessageBox.critical(self, "Instance Load Error", message)

    def _cleanup_inst_thread(self) -> None:
        if self._inst_thread:
            self._inst_thread.quit()
            self._inst_thread.wait()
            self._inst_thread = None
            self._inst_worker = None

    # ── Settings ───────────────────────────────────────────────────────────

    def _on_settings(self) -> None:
        from bde_xbrl_editor.ui.widgets.loader_settings_dialog import (  # noqa: PLC0415
            LoaderSettingsDialog,
        )

        dialog = LoaderSettingsDialog(self._settings, self)
        if dialog.exec():
            self._settings = dialog.get_settings()
            self._loader = TaxonomyLoader(cache=self._cache, settings=self._settings)

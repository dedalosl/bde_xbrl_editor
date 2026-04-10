"""TaxonomyLoaderWidget — welcome screen with two panels: Open Taxonomy / Open Instance."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal
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

from bde_xbrl_editor.taxonomy import (
    LoaderSettings,
    TaxonomyCache,
    TaxonomyLoader,
    TaxonomyLoadError,
)
from bde_xbrl_editor.ui.widgets.loader_settings_dialog import (
    add_recent_file,
    add_recent_instance,
    load_recent_files,
    load_recent_instances,
)
from bde_xbrl_editor.ui.widgets.progress_dialog import TaxonomyProgressDialog

# ── Palette ────────────────────────────────────────────────────────────────
_NAVY = "#1E3A5F"
_NAVY_MID = "#2B5287"
_NAVY_LIGHT = "#3A6AA8"
_ACCENT = "#4A90D9"
_BG = "#F0F4FA"
_CARD_BG = "#FFFFFF"
_TEXT_MAIN = "#1E3A5F"
_TEXT_MUTED = "#6B8AAE"
_BORDER = "#C8D4E5"
_HOVER_ROW = "#EEF3FA"


class _LoadWorker(QObject):
    """Worker that runs TaxonomyLoader.load() in a background QThread."""

    finished = Signal(object)
    error = Signal(str)
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
            skipped = self._loader.last_skipped_urls
            self.finished.emit((structure, skipped))
        except TaxonomyLoadError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Unexpected error: {exc}")


class _InstanceLoadWorker(QObject):
    """Worker that runs InstanceParser.load() in a background QThread."""

    finished = Signal(object, object)  # (XbrlInstance, TaxonomyStructure)
    error = Signal(str)
    orphaned = Signal(int)  # emits orphaned fact count if > 0

    def __init__(self, cache: TaxonomyCache, settings: LoaderSettings, path: str) -> None:
        super().__init__()
        self._cache = cache
        self._settings = settings
        self._path = path

    def run(self) -> None:
        from bde_xbrl_editor.instance.models import (  # noqa: PLC0415
            InstanceParseError,
            TaxonomyResolutionError,
        )
        from bde_xbrl_editor.instance.parser import InstanceParser  # noqa: PLC0415
        from bde_xbrl_editor.taxonomy.loader import TaxonomyLoader  # noqa: PLC0415

        loader = TaxonomyLoader(cache=self._cache, settings=self._settings)
        parser = InstanceParser(taxonomy_loader=loader)
        try:
            instance, orphaned_facts = parser.load(self._path)
            taxonomy = loader.load(instance.taxonomy_entry_point)
            if orphaned_facts:
                self.orphaned.emit(len(orphaned_facts))
            self.finished.emit(instance, taxonomy)
        except TaxonomyResolutionError as exc:
            self.error.emit(str(exc))
        except InstanceParseError as exc:
            self.error.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.error.emit(f"Unexpected error: {exc}")


class _RecentFileRow(QFrame):
    """A single clickable row in the Recent Files list."""

    clicked = Signal(str)

    def __init__(self, path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = path
        p = Path(path)

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            _RecentFileRow {
                background: transparent;
                border-radius: 6px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(10)

        icon = QLabel("◈")
        icon.setStyleSheet(f"color: {_ACCENT}; font-size: 16px;")
        icon.setFixedWidth(20)
        layout.addWidget(icon)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        name_lbl = QLabel(p.name)
        name_lbl.setStyleSheet(
            f"color: {_TEXT_MAIN}; font-weight: 600; font-size: 12px;"
        )
        text_col.addWidget(name_lbl)

        dir_lbl = QLabel(str(p.parent))
        dir_lbl.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 10px;")
        dir_lbl.setWordWrap(False)
        text_col.addWidget(dir_lbl)

        layout.addLayout(text_col, stretch=1)

        arrow = QLabel("›")
        arrow.setStyleSheet(f"color: {_TEXT_MUTED}; font-size: 18px;")
        layout.addWidget(arrow)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._path)
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self.setStyleSheet(f"""
            _RecentFileRow {{
                background: {_HOVER_ROW};
                border-radius: 6px;
            }}
        """)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self.setStyleSheet("""
            _RecentFileRow {
                background: transparent;
                border-radius: 6px;
            }
        """)
        super().leaveEvent(event)


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
        self._worker: _LoadWorker | None = None
        self._inst_thread: QThread | None = None
        self._inst_worker: _InstanceLoadWorker | None = None
        self._setup_ui()

    # ── UI construction ────────────────────────────────────────────────────

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
        header.setFixedHeight(110)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(48, 0, 48, 0)

        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        app_title = QLabel("BDE XBRL Editor")
        app_title.setStyleSheet(
            "color: #FFFFFF; font-size: 24px; font-weight: 700; background: transparent;"
        )
        title_col.addWidget(app_title)

        subtitle = QLabel("Banco de España — Financial Reporting Tool")
        subtitle.setStyleSheet(
            f"color: {_ACCENT}; font-size: 12px; background: transparent;"
        )
        title_col.addWidget(subtitle)

        header_layout.addLayout(title_col)
        header_layout.addStretch()
        outer.addWidget(header)

        # ── Two-panel card area ────────────────────────────────────────
        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        content.addSpacing(32)

        cards_row = QHBoxLayout()
        cards_row.setContentsMargins(32, 0, 32, 0)
        cards_row.setSpacing(24)

        cards_row.addWidget(self._build_taxonomy_card(), stretch=1)
        cards_row.addWidget(self._build_instance_card(), stretch=1)

        content.addLayout(cards_row)
        content.addStretch()

        # Settings link at bottom-right
        footer = QHBoxLayout()
        footer.addStretch()
        settings_btn = QPushButton("⚙  Settings…")
        settings_btn.setFlat(True)
        settings_btn.setStyleSheet(
            f"QPushButton {{ color: {_TEXT_MUTED}; font-size: 11px; border: none;"
            f" padding: 4px 8px; background: transparent; }}"
            f"QPushButton:hover {{ color: {_NAVY}; }}"
        )
        settings_btn.clicked.connect(self._on_settings)
        footer.addWidget(settings_btn)
        footer.setContentsMargins(0, 0, 20, 12)
        content.addLayout(footer)

        outer.addLayout(content, stretch=1)

    def _make_card(self) -> tuple[QFrame, QVBoxLayout]:
        """Create a styled card frame and return (card, layout)."""
        card = QFrame()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        card.setStyleSheet(
            f"QFrame {{ background: {_CARD_BG}; border-radius: 10px;"
            f" border: 1px solid {_BORDER}; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(0)
        return card, layout

    def _add_section_header(self, layout: QVBoxLayout, title: str) -> None:
        lbl = QLabel(title)
        lbl.setStyleSheet(
            f"color: {_TEXT_MAIN}; font-size: 15px; font-weight: 700;"
            f" border: none; background: transparent;"
        )
        layout.addWidget(lbl)
        layout.addSpacing(4)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"border: none; background: {_BORDER}; max-height: 1px;")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        layout.addSpacing(16)

    def _build_taxonomy_card(self) -> QFrame:
        card, layout = self._make_card()

        self._add_section_header(layout, "Open Taxonomy")

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

        recent_paths = load_recent_files()
        if recent_paths:
            layout.addSpacing(24)
            self._add_section_header(layout, "Recent Taxonomies")
            layout.addSpacing(-12)  # tighten after header spacing

            for path in recent_paths:
                row = _RecentFileRow(path)
                row.clicked.connect(self._on_recent_taxonomy_clicked)
                layout.addWidget(row)

        layout.addStretch()
        return card

    def _build_instance_card(self) -> QFrame:
        card, layout = self._make_card()

        self._add_section_header(layout, "Open Instance")

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
            layout.addSpacing(-12)

            for path in recent_instances:
                row = _RecentFileRow(path)
                row.clicked.connect(self._on_recent_instance_clicked)
                layout.addWidget(row)

        layout.addStretch()
        return card

    # ── Button / input styles ──────────────────────────────────────────────

    def _input_style(self) -> str:
        return (
            f"QLineEdit {{ border: 1px solid {_BORDER}; border-radius: 5px;"
            f" padding: 7px 10px; font-size: 12px; color: {_TEXT_MAIN};"
            f" background: #FAFCFF; }}"
            f"QLineEdit:focus {{ border-color: {_ACCENT}; }}"
        )

    def _primary_btn_style(self) -> str:
        return (
            f"QPushButton {{ background: {_NAVY}; color: #FFFFFF;"
            f" border: none; border-radius: 5px;"
            f" font-size: 13px; font-weight: 600; padding: 6px 20px; }}"
            f"QPushButton:hover {{ background: {_NAVY_MID}; }}"
            f"QPushButton:pressed {{ background: {_NAVY_LIGHT}; }}"
            f"QPushButton:disabled {{ background: #B0C0D4; color: #FFFFFF; }}"
        )

    def _secondary_btn_style(self) -> str:
        return (
            f"QPushButton {{ background: #FFFFFF; color: {_TEXT_MAIN};"
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

        self._progress_dialog = TaxonomyProgressDialog(self)
        self._progress_dialog.show()

        self._worker = _LoadWorker(self._loader, path)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(
            self._on_load_finished, Qt.ConnectionType.QueuedConnection
        )
        self._worker.error.connect(
            self._on_load_error, Qt.ConnectionType.QueuedConnection
        )
        self._worker.progress.connect(self._progress_dialog.update_progress)
        self._thread.start()

    def _on_load_finished(self, payload: object) -> None:
        structure, skipped_urls = payload  # type: ignore[misc]
        self._cleanup_thread()
        self._progress_dialog.close()
        self._load_btn.setEnabled(True)

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

        self._inst_progress_dialog = TaxonomyProgressDialog(self)
        self._inst_progress_dialog.show()

        self._inst_worker = _InstanceLoadWorker(self._cache, self._settings, path)
        self._inst_thread = QThread(self)
        self._inst_worker.moveToThread(self._inst_thread)
        self._inst_thread.started.connect(self._inst_worker.run)
        self._inst_worker.finished.connect(
            self._on_inst_load_finished, Qt.ConnectionType.QueuedConnection
        )
        self._inst_worker.error.connect(
            self._on_inst_load_error, Qt.ConnectionType.QueuedConnection
        )
        self._inst_worker.orphaned.connect(
            self._on_inst_orphaned, Qt.ConnectionType.QueuedConnection
        )
        self._inst_thread.start()

    def _on_inst_load_finished(self, instance: object, taxonomy: object) -> None:
        self._cleanup_inst_thread()
        self._inst_progress_dialog.close()
        self._load_inst_btn.setEnabled(True)

        add_recent_instance(self._inst_path_edit.text().strip())
        self.instance_loaded.emit(instance, taxonomy)

    def _on_inst_orphaned(self, count: int) -> None:
        QMessageBox.information(
            self,
            "Orphaned Facts",
            f"{count} fact(s) in this instance have concepts not found in the "
            f"taxonomy and will be preserved verbatim on save.",
        )

    def _on_inst_load_error(self, message: str) -> None:
        self._cleanup_inst_thread()
        self._inst_progress_dialog.close()
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

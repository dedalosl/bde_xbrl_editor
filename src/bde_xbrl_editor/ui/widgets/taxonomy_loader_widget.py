"""TaxonomyLoaderWidget — welcome screen with recent-file picker and load trigger."""

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
    load_recent_files,
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
_SELECTED_ROW = "#DCE8F5"


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


class _RecentFileRow(QFrame):
    """A single clickable row in the Recent Files list."""

    clicked = Signal(str)  # emits the file path

    def __init__(self, path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._path = path
        p = Path(path)

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            _RecentFileRow {{
                background: transparent;
                border-radius: 6px;
            }}
            _RecentFileRow:hover {{
                background: {_HOVER_ROW};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(10)

        # File icon indicator
        icon = QLabel("◈")
        icon.setStyleSheet(f"color: {_ACCENT}; font-size: 16px;")
        icon.setFixedWidth(20)
        layout.addWidget(icon)

        # Name + path stacked vertically
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

        # Arrow
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
    """Welcome screen — file picker + recent files list.

    Signals:
        taxonomy_loaded(TaxonomyStructure): Emitted on successful load.
    """

    taxonomy_loaded = Signal(object)

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

    # ── UI construction ────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        # Full-screen background
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

        # ── Centred card area ──────────────────────────────────────────
        scroll_area = QVBoxLayout()
        scroll_area.setContentsMargins(0, 0, 0, 0)

        # Centering wrapper
        h_center = QHBoxLayout()
        h_center.addStretch()

        card = QFrame()
        card.setFixedWidth(580)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        card.setStyleSheet(
            f"QFrame {{ background: {_CARD_BG}; border-radius: 10px;"
            f" border: 1px solid {_BORDER}; }}"
        )
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 28, 32, 28)
        card_layout.setSpacing(0)

        # ── Open taxonomy section ──────────────────────────────────────
        open_title = QLabel("Open Taxonomy")
        open_title.setStyleSheet(
            f"color: {_TEXT_MAIN}; font-size: 15px; font-weight: 700;"
            f" border: none; background: transparent;"
        )
        card_layout.addWidget(open_title)
        card_layout.addSpacing(4)

        divider1 = QFrame()
        divider1.setFrameShape(QFrame.Shape.HLine)
        divider1.setStyleSheet(f"border: none; background: {_BORDER}; max-height: 1px;")
        divider1.setFixedHeight(1)
        card_layout.addWidget(divider1)
        card_layout.addSpacing(16)

        # Path row
        path_row = QHBoxLayout()
        path_row.setSpacing(8)

        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select the taxonomy entry-point .xsd file…")
        self._path_edit.setStyleSheet(
            f"QLineEdit {{ border: 1px solid {_BORDER}; border-radius: 5px;"
            f" padding: 7px 10px; font-size: 12px; color: {_TEXT_MAIN};"
            f" background: #FAFCFF; }}"
            f"QLineEdit:focus {{ border-color: {_ACCENT}; }}"
        )
        path_row.addWidget(self._path_edit)

        browse_btn = QPushButton("Browse…")
        browse_btn.setFixedWidth(80)
        browse_btn.setStyleSheet(self._secondary_btn_style())
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(browse_btn)
        card_layout.addLayout(path_row)
        card_layout.addSpacing(12)

        # Load button
        self._load_btn = QPushButton("Load Taxonomy")
        self._load_btn.setDefault(True)
        self._load_btn.setFixedHeight(38)
        self._load_btn.setStyleSheet(self._primary_btn_style())
        self._load_btn.clicked.connect(self._on_load)
        card_layout.addWidget(self._load_btn)

        # ── Recent files section ───────────────────────────────────────
        recent_paths = load_recent_files()
        if recent_paths:
            card_layout.addSpacing(24)

            recent_title = QLabel("Recent Files")
            recent_title.setStyleSheet(
                f"color: {_TEXT_MAIN}; font-size: 15px; font-weight: 700;"
                f" border: none; background: transparent;"
            )
            card_layout.addWidget(recent_title)
            card_layout.addSpacing(4)

            divider2 = QFrame()
            divider2.setFrameShape(QFrame.Shape.HLine)
            divider2.setStyleSheet(f"border: none; background: {_BORDER}; max-height: 1px;")
            divider2.setFixedHeight(1)
            card_layout.addWidget(divider2)
            card_layout.addSpacing(4)

            self._recent_container = QVBoxLayout()
            self._recent_container.setSpacing(2)
            for path in recent_paths:
                row = _RecentFileRow(path)
                row.clicked.connect(self._on_recent_clicked)
                self._recent_container.addWidget(row)
            card_layout.addLayout(self._recent_container)

        h_center.addWidget(card)
        h_center.addStretch()

        v_center = QVBoxLayout()
        v_center.addSpacing(32)
        v_center.addLayout(h_center)
        v_center.addStretch()

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

        v_center.addLayout(footer)

        scroll_area.addLayout(v_center)
        outer.addLayout(scroll_area, stretch=1)

    # ── Button styles ──────────────────────────────────────────────────────

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

    # ── Slots ──────────────────────────────────────────────────────────────

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Taxonomy Entry Point",
            "",
            "XBRL Schema Files (*.xsd);;All Files (*)",
        )
        if path:
            self._path_edit.setText(path)

    def _on_recent_clicked(self, path: str) -> None:
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

        # Persist to recent files
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

    def _on_settings(self) -> None:
        from bde_xbrl_editor.ui.widgets.loader_settings_dialog import (  # noqa: PLC0415
            LoaderSettingsDialog,
        )

        dialog = LoaderSettingsDialog(self._settings, self)
        if dialog.exec():
            self._settings = dialog.get_settings()
            self._loader = TaxonomyLoader(cache=self._cache, settings=self._settings)

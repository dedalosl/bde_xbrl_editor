"""QMainWindow shell — Features 001 + 002 + 004 + 005 UI."""

from __future__ import annotations

import contextlib
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDockWidget,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from bde_xbrl_editor.performance import (
    LoadTiming,
    StageTiming,
    format_duration,
    format_stage_timings,
)
from bde_xbrl_editor.taxonomy import TaxonomyCache, TaxonomyStructure
from bde_xbrl_editor.ui import theme
from bde_xbrl_editor.ui.loading import InstanceLoadWorker
from bde_xbrl_editor.ui.widgets.activity_sidebar import ActivitySidebar
from bde_xbrl_editor.ui.widgets.loader_settings_dialog import load_saved_settings
from bde_xbrl_editor.ui.widgets.progress_dialog import TaxonomyProgressDialog
from bde_xbrl_editor.ui.widgets.taxonomy_loader_widget import TaxonomyLoaderWidget


class MainWindow(QMainWindow):
    """Application main window."""

    _INITIAL_TABLE_RENDER_DELAY_MS = 16

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BDE XBRL Editor[*]")
        self.resize(1000, 700)

        self._apply_stylesheet()
        self._cache = TaxonomyCache()
        self._settings = load_saved_settings()
        self._current_taxonomy: TaxonomyStructure | None = None
        self._current_instance = None  # XbrlInstance | None
        self._editor = None  # InstanceEditor | None
        self._table_view = None  # XbrlTableView | None
        self._sidebar: ActivitySidebar | None = None
        self._browser_splitter: QSplitter | None = None
        self._context_bar: QFrame | None = None
        self._table_chip_sep: QLabel | None = None
        self._table_chip_label: QLabel | None = None
        self._context_title_label: QLabel | None = None
        self._context_meta_label: QLabel | None = None
        self._language_combo: QComboBox | None = None
        self._loading_dialog: TaxonomyProgressDialog | None = None
        self._instance_open_thread: QThread | None = None
        self._instance_open_worker: InstanceLoadWorker | None = None
        self._pending_load_timing: LoadTiming | None = None
        self._pending_initial_table_started_at: float | None = None
        self._instance_open_started_at: float | None = None

        # Validation
        self._validation_thread: QThread | None = None
        self._validation_worker = None  # ValidationWorker | None
        self._validation_panel = None  # ValidationPanel | None

        self._setup_menu()
        self._setup_central()
        self._setup_statusbar()

    @staticmethod
    def _table_identity(table: object | None) -> str:
        if table is None:
            return ""
        table_code = getattr(table, "table_code", None)
        table_id = getattr(table, "table_id", "")
        parts = [part for part in (table_code, table_id) if part]
        return "  |  ".join(parts)

    @staticmethod
    def _taxonomy_entry_point(taxonomy: TaxonomyStructure | None) -> Path | None:
        if taxonomy is None:
            return None
        return taxonomy.metadata.entry_point_path.resolve()

    def _same_taxonomy(self, taxonomy: TaxonomyStructure) -> bool:
        current_entry = self._taxonomy_entry_point(self._current_taxonomy)
        incoming_entry = self._taxonomy_entry_point(taxonomy)
        return current_entry is not None and current_entry == incoming_entry

    def _apply_stylesheet(self) -> None:
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                font-family: "Helvetica Neue", Arial, sans-serif;
                font-size: 12px;
                color: {theme.TEXT_MAIN};
            }}
            QMenuBar {{
                background: {theme.NAV_BG_DEEP};
                color: {theme.TEXT_INVERSE};
                padding: 2px 4px;
                border-bottom: 1px solid {theme.BORDER_STRONG};
            }}
            QMenuBar::item:selected {{
                background: {theme.NAV_BG};
            }}
            QMenu {{
                background: {theme.SURFACE_BG};
                border: 1px solid {theme.BORDER};
                color: {theme.TEXT_MAIN};
            }}
            QMenu::item:selected {{
                background: {theme.SELECTION_BG};
                color: {theme.TEXT_MAIN};
            }}
            QStatusBar {{
                background: {theme.PANEL_BG};
                color: {theme.TEXT_MAIN};
                border-top: 1px solid {theme.BORDER};
                font-size: 11px;
                padding: 2px 6px;
            }}
            QTableView, QTreeView, QListView {{
                background: {theme.CELL_BG};
                alternate-background-color: {theme.CELL_BG_MUTED};
                color: {theme.TEXT_MAIN};
                gridline-color: {theme.BORDER};
                border: 1px solid {theme.BORDER};
                selection-background-color: {theme.SELECTION_BG};
                selection-color: {theme.SELECTION_FG};
            }}
            QHeaderView::section {{
                background: {theme.HEADER_BG_LIGHT};
                color: {theme.TEXT_MAIN};
                border: 1px solid {theme.BORDER};
                padding: 4px 6px;
                font-weight: 600;
            }}
            QPushButton, QComboBox, QLineEdit, QTextEdit {{
                background: {theme.INPUT_BG};
                color: {theme.TEXT_MAIN};
                border: 1px solid {theme.BORDER};
                border-radius: 4px;
            }}
            QPushButton {{
                padding: 4px 10px;
            }}
            QPushButton:hover, QComboBox:hover, QLineEdit:hover {{
                border-color: {theme.BORDER_STRONG};
                background: {theme.SURFACE_BG};
            }}
            QPushButton:disabled, QComboBox:disabled, QLineEdit:disabled {{
                background: {theme.DISABLED_BG};
                color: {theme.DISABLED_FG};
                border-color: {theme.BORDER};
            }}
            QTextEdit {{
                selection-background-color: {theme.SELECTION_BG};
                selection-color: {theme.SELECTION_FG};
            }}
            QScrollBar:vertical {{
                width: 10px;
                background: {theme.SURFACE_ALT_BG};
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {theme.ACCENT_SOFT};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {theme.ACCENT};
            }}
            QScrollBar:horizontal {{
                height: 10px;
                background: {theme.SURFACE_ALT_BG};
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: {theme.ACCENT_SOFT};
                border-radius: 4px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {theme.ACCENT};
            }}
            QSplitter::handle {{
                background: {theme.BORDER};
            }}
        """)

    def _setup_menu(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")


        open_taxonomy_action = file_menu.addAction("&Open Taxonomy…")
        open_taxonomy_action.setShortcut("Ctrl+O")
        open_taxonomy_action.triggered.connect(self._show_loader)

        self._reload_action = file_menu.addAction("&Reload Taxonomy")
        self._reload_action.setShortcut("Ctrl+R")
        self._reload_action.setEnabled(False)
        self._reload_action.triggered.connect(self._on_reload)

        file_menu.addSeparator()

        self._new_instance_action = file_menu.addAction("&New Instance…")
        self._new_instance_action.setShortcut("Ctrl+N")
        self._new_instance_action.setEnabled(False)
        self._new_instance_action.triggered.connect(self._on_new_instance)

        self._open_instance_action = file_menu.addAction("Open &Instance…")
        self._open_instance_action.setShortcut("Ctrl+Shift+O")
        self._open_instance_action.setEnabled(True)
        self._open_instance_action.triggered.connect(self._on_open_instance)

        file_menu.addSeparator()

        self._save_action = file_menu.addAction("&Save")
        self._save_action.setShortcut("Ctrl+S")
        self._save_action.setEnabled(False)
        self._save_action.triggered.connect(self._on_save)

        self._save_as_action = file_menu.addAction("Save &As…")
        self._save_as_action.setShortcut("Ctrl+Shift+S")
        self._save_as_action.setEnabled(False)
        self._save_as_action.triggered.connect(self._on_save_as)

        file_menu.addSeparator()

        self._close_instance_action = file_menu.addAction("Close &Instance")
        self._close_instance_action.setEnabled(False)
        self._close_instance_action.triggered.connect(self._on_close_instance)

        self._close_taxonomy_action = file_menu.addAction("Close &Taxonomy")
        self._close_taxonomy_action.setEnabled(False)
        self._close_taxonomy_action.triggered.connect(self._on_close_taxonomy)

        file_menu.addSeparator()
        quit_action = file_menu.addAction("&Quit")
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)

        # Validation menu
        validation_menu = menu_bar.addMenu("&Validation")
        self._validate_action = validation_menu.addAction("&Validate Instance")
        self._validate_action.setShortcut("Ctrl+Shift+V")
        self._validate_action.setEnabled(False)
        self._validate_action.triggered.connect(self._trigger_validation)

        self._show_validation_panel_action = validation_menu.addAction("Show Validation Panel")
        self._show_validation_panel_action.setEnabled(False)
        self._show_validation_panel_action.triggered.connect(self._show_validation_panel)

    def _setup_central(self) -> None:
        self._loader_widget: TaxonomyLoaderWidget | None = None
        self._show_loader_widget()

    def _clear_browser_view_refs(self) -> None:
        """Drop references to Qt-owned browser widgets before replacing the central view."""
        self._table_view = None
        self._sidebar = None
        self._browser_splitter = None
        self._context_bar = None
        self._table_chip_sep = None
        self._table_chip_label = None
        self._context_title_label = None
        self._context_meta_label = None
        self._language_combo = None

    def _show_loader_widget(self, path: str | None = None) -> None:
        """Create a fresh TaxonomyLoaderWidget and set it as the central widget.

        Qt takes ownership of (and deletes) the previous central widget, so we
        must never reuse the old reference — always construct a new instance.
        """
        if self._editor is not None:
            with contextlib.suppress(RuntimeError, TypeError):
                self._editor.changes_made.disconnect(self._on_changes_made)
                self._editor.filing_indicators_changed.disconnect(self._on_filing_indicators_changed)
        self._editor = None
        if self._table_view is not None:
            self._table_view.set_editor(None)
        self._current_instance = None
        self._clear_browser_view_refs()
        self._pending_load_timing = None
        self._pending_initial_table_started_at = None

        widget = TaxonomyLoaderWidget(
            cache=self._cache,
            settings=self._settings,
            parent=self,
        )
        widget.taxonomy_loaded.connect(self._on_taxonomy_loaded)
        widget.instance_loaded.connect(self._on_instance_loaded_from_widget)
        if path is not None:
            widget._path_edit.setText(path)
        self._loader_widget = widget
        self.setCentralWidget(widget)

    def _setup_statusbar(self) -> None:
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("No taxonomy loaded")

    # ------------------------------------------------------------------
    # Taxonomy actions
    # ------------------------------------------------------------------

    def _show_loader(self) -> None:
        if not self._check_unsaved_changes():
            return
        self._show_loader_widget()

    def _on_taxonomy_loaded(self, structure: TaxonomyStructure) -> None:
        workspace_started_at = time.perf_counter()
        self._current_instance = None
        self._editor = None
        if self._table_view is not None:
            self._table_view.set_editor(None)
        self._current_taxonomy = structure
        meta = structure.metadata
        table_count = len(structure.tables)
        concept_count = len(structure.concepts)
        self._reload_action.setEnabled(True)
        self._new_instance_action.setEnabled(True)
        self._open_instance_action.setEnabled(True)
        self._close_taxonomy_action.setEnabled(True)

        self._setup_browser_layout()
        workspace_elapsed = time.perf_counter() - workspace_started_at
        loader_timing = self._loader_widget.last_taxonomy_load_timing if self._loader_widget is not None else None
        if loader_timing is not None:
            self._pending_load_timing = LoadTiming(
                total_seconds=loader_timing.total_seconds + workspace_elapsed,
                stages=loader_timing.stages + (StageTiming("workspace", workspace_elapsed),),
            )
            timing_text = format_stage_timings(self._pending_load_timing.stages)
            self._status.showMessage(
                f"Loaded: {meta.name} v{meta.version} — "
                f"{concept_count} concepts, {table_count} tables — {timing_text}"
            )
        else:
            self._status.showMessage(
                f"Loaded: {meta.name} v{meta.version} — "
                f"{concept_count} concepts, {table_count} tables"
            )

    def _on_instance_loaded_from_widget(self, instance, taxonomy: TaxonomyStructure) -> None:
        """Handle an instance+taxonomy loaded directly from the welcome screen."""
        self._current_taxonomy = taxonomy
        meta = taxonomy.metadata
        self._reload_action.setEnabled(True)
        self._new_instance_action.setEnabled(True)
        self._open_instance_action.setEnabled(True)
        self._close_taxonomy_action.setEnabled(True)
        self._pending_load_timing = (
            self._loader_widget.last_instance_load_timing
            if self._loader_widget is not None
            else None
        )
        self._status.showMessage(
            f"Loaded: {meta.name} v{meta.version} — "
            f"{len(taxonomy.concepts)} concepts, {len(taxonomy.tables)} tables"
        )
        self._load_instance(instance)

    def _setup_browser_layout(self) -> None:
        """Create the main split layout: context bar + activity sidebar + XbrlTableView."""
        from bde_xbrl_editor.ui.widgets.xbrl_table_view import XbrlTableView  # noqa: PLC0415

        assert self._current_taxonomy is not None
        self._sidebar = ActivitySidebar(
            self._current_taxonomy,
            parent=self,
            visible_indexes=(1, 2),
            initial_index=1,
        )
        self._sidebar.set_language_preference(self._current_language_preference())
        self._sidebar.table_selected.connect(self._on_table_selected)
        self._sidebar.width_changed.connect(self._on_sidebar_width_changed)

        self._table_view = XbrlTableView(parent=self)
        self._table_view.set_language_preference(self._current_language_preference())
        self._table_view.editing_mode_changed.connect(self._on_table_editing_mode_changed)
        self._table_view.layout_ready.connect(self._on_table_layout_ready)
        self._table_view.cell_info_changed.connect(self._on_cell_info_changed)
        self._table_view.cell_info_changed.connect(self._on_cell_info_changed)

        splitter = QSplitter(self)
        splitter.addWidget(self._sidebar)
        splitter.addWidget(self._table_view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self._browser_splitter = splitter

        container = QWidget(self)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self._context_bar = self._build_context_bar(instance=None)
        container_layout.addWidget(self._context_bar)
        container_layout.addWidget(splitter, stretch=1)

        self.setCentralWidget(container)

        # Give Qt a chance to paint the workspace shell before the first table render starts.
        QTimer.singleShot(self._INITIAL_TABLE_RENDER_DELAY_MS, self._select_first_taxonomy_table)

    # ------------------------------------------------------------------
    # Context bar
    # ------------------------------------------------------------------

    def _build_context_bar(self, instance=None) -> QFrame:
        """Return a structured workspace header with context on the left and actions on the right."""
        bar = QFrame()
        bar.setFixedHeight(72)
        bar.setStyleSheet(
            f"QFrame {{ background: {theme.SURFACE_ALT_BG}; }}"
        )

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)

        context_block = QWidget(bar)
        context_layout = QVBoxLayout(context_block)
        context_layout.setContentsMargins(0, 0, 0, 0)
        context_layout.setSpacing(2)

        eyebrow = QLabel("Workspace")
        eyebrow.setStyleSheet(
            f"color: {theme.TEXT_SUBTLE}; font-size: 10px; font-weight: bold;"
        )
        context_layout.addWidget(eyebrow)

        title = QLabel()
        title.setStyleSheet(
            f"color: {theme.TEXT_MAIN}; font-size: 18px; font-weight: bold; background: transparent;"
        )
        context_layout.addWidget(title)
        self._context_title_label = title

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(8)

        meta_label = QLabel()
        meta_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 11px; background: transparent;"
        )
        meta_row.addWidget(meta_label)
        self._context_meta_label = meta_label

        meta_row.addStretch()
        context_layout.addLayout(meta_row)
        layout.addWidget(context_block, stretch=1)

        info_group = QWidget(bar)
        info_layout = QHBoxLayout(info_group)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(14)

        context_note_style = (
            f"color: {theme.TEXT_MUTED}; font-size: 10px; font-weight: 600; background: transparent;"
        )

        if self._current_taxonomy:
            meta = self._current_taxonomy.metadata
            tax_label = QLabel(f"Taxonomy {meta.name}  |  Version {meta.version}")
            tax_label.setStyleSheet(context_note_style)
            info_layout.addWidget(tax_label)

        if instance is not None:
            fname = Path(instance.source_path).name if instance.source_path else "Unsaved instance"
            inst_label = QLabel(f"Instance {fname}")
            inst_label.setStyleSheet(context_note_style)
            info_layout.addWidget(inst_label)

        self._table_chip_label = None
        self._table_chip_sep = None
        self._language_combo = None

        layout.addWidget(info_group, stretch=0)

        btn_style = (
            f"QPushButton {{ color: {theme.TEXT_MAIN}; background: {theme.SURFACE_BG};"
            f" border: 1px solid {theme.BORDER}; border-radius: 8px;"
            " font-size: 10px; font-weight: 600; padding: 0 12px; }"
            f"QPushButton:hover {{ background: {theme.INPUT_BG}; border-color: {theme.BORDER_STRONG}; }}"
            f"QPushButton:disabled {{ color: {theme.DISABLED_FG}; background: transparent;"
            f" border-color: {theme.BORDER}; }}"
        )
        primary_btn_style = (
            f"QPushButton {{ color: {theme.TEXT_INVERSE}; background: {theme.NAV_BG_DEEP};"
            " border: none; border-radius: 8px; font-size: 10px; font-weight: 600; padding: 0 12px; }"
            f"QPushButton:hover {{ background: {theme.NAV_BG_DARK}; }}"
            f"QPushButton:disabled {{ background: {theme.DISABLED_BG}; color: {theme.DISABLED_FG}; }}"
        )

        action_group = QWidget(bar)
        action_layout = QHBoxLayout(action_group)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)

        if self._current_taxonomy is not None:
            self._language_combo = self._build_language_combo(bar)
            action_layout.addWidget(self._language_combo)

        if instance is not None:
            back_btn = QPushButton("Back")
            back_btn.setStyleSheet(btn_style)
            back_btn.setFixedHeight(28)
            back_btn.clicked.connect(self._on_close_taxonomy)
            action_layout.addWidget(back_btn)

            close_inst_btn = QPushButton("Close Instance")
            close_inst_btn.setStyleSheet(btn_style)
            close_inst_btn.setFixedHeight(28)
            close_inst_btn.clicked.connect(self._on_close_instance)
            action_layout.addWidget(close_inst_btn)

            validate_btn = QPushButton("Validate")
            validate_btn.setStyleSheet(primary_btn_style)
            validate_btn.setFixedHeight(28)
            validate_btn.setToolTip("Run validation on the current instance (Ctrl+Shift+V)")
            validate_btn.clicked.connect(self._on_validate_from_context_bar)
            action_layout.addWidget(validate_btn)

            save_btn = QPushButton("Save")
            save_btn.setStyleSheet(primary_btn_style)
            save_btn.setFixedHeight(28)
            save_btn.clicked.connect(self._on_save)
            action_layout.addWidget(save_btn)

            open_inst_btn = QPushButton("Open Instance…")
            open_inst_btn.setStyleSheet(btn_style)
            open_inst_btn.setFixedHeight(28)
            open_inst_btn.clicked.connect(self._on_open_instance)
            action_layout.addWidget(open_inst_btn)

            new_inst_btn = QPushButton("New Instance…")
            new_inst_btn.setStyleSheet(btn_style)
            new_inst_btn.setFixedHeight(28)
            new_inst_btn.clicked.connect(self._on_new_instance)
            action_layout.addWidget(new_inst_btn)

        elif self._current_taxonomy is not None:
            back_btn = QPushButton("Back")
            back_btn.setStyleSheet(btn_style)
            back_btn.setFixedHeight(28)
            back_btn.clicked.connect(self._on_close_taxonomy)
            action_layout.addWidget(back_btn)

            open_inst_btn = QPushButton("Open Instance…")
            open_inst_btn.setStyleSheet(btn_style)
            open_inst_btn.setFixedHeight(28)
            open_inst_btn.clicked.connect(self._on_open_instance)
            action_layout.addWidget(open_inst_btn)

            new_inst_btn = QPushButton("New Instance…")
            new_inst_btn.setStyleSheet(primary_btn_style)
            new_inst_btn.setFixedHeight(28)
            new_inst_btn.clicked.connect(self._on_new_instance)
            action_layout.addWidget(new_inst_btn)

        layout.addWidget(action_group, stretch=0)

        if self._current_taxonomy is not None:
            meta = self._current_taxonomy.metadata
            title_text = meta.name
            meta_parts = [f"Version {meta.version}", f"{len(self._current_taxonomy.tables)} tables"]
            if instance is not None:
                fname = Path(instance.source_path).name if instance.source_path else "Unsaved instance"
                meta_parts.append(fname)
            self._context_title_label.setText(title_text)
            self._context_meta_label.setText("  |  ".join(meta_parts))
        else:
            self._context_title_label.setText("Workspace")
            self._context_meta_label.setText("")

        return bar

    def _current_language_preference(self) -> list[str]:
        combo = self._language_combo
        if combo is not None:
            selected = combo.currentData()
            if isinstance(selected, str) and selected:
                return [selected, *[lang for lang in self._settings.language_preference if lang != selected]]
        return list(self._settings.language_preference or ["es", "en"])

    def _build_language_combo(self, parent: QWidget) -> QComboBox:
        combo = QComboBox(parent)
        combo.setFixedHeight(28)
        combo.setToolTip("Table label language")
        combo.setStyleSheet(
            f"QComboBox {{ color: {theme.TEXT_MAIN}; background: {theme.SURFACE_BG};"
            f" border: 1px solid {theme.BORDER}; border-radius: 8px;"
            " font-size: 10px; font-weight: 600; padding: 0 8px; min-width: 72px; }"
        )
        languages: list[str] = []
        for lang in self._settings.language_preference:
            if lang and lang not in languages:
                languages.append(lang)
        if self._current_taxonomy is not None:
            for lang in self._current_taxonomy.metadata.declared_languages:
                if lang and lang not in languages:
                    languages.append(lang)
        for lang in languages or ["es", "en"]:
            combo.addItem(lang.upper(), lang)
        combo.currentIndexChanged.connect(self._on_language_changed)
        return combo

    def _on_language_changed(self) -> None:
        table = getattr(self._table_view, "_table", None) if self._table_view is not None else None
        if table is not None and self._context_title_label is not None:
            variants = dict(getattr(table, "label_variants", ()) or ())
            label = next(
                (variants[lang] for lang in self._current_language_preference() if lang in variants),
                getattr(table, "label", None) or getattr(table, "table_id", ""),
            )
            self._context_title_label.setText(label)
        if self._table_view is not None:
            self._table_view.set_language_preference(self._current_language_preference())
        if self._sidebar is not None:
            self._sidebar.set_language_preference(self._current_language_preference())

    # ------------------------------------------------------------------
    # Close taxonomy / instance
    # ------------------------------------------------------------------

    def _on_close_taxonomy(self) -> None:
        """Return to the loader screen, discarding the current taxonomy and instance."""
        if not self._check_unsaved_changes():
            return

        # Disconnect editor signals
        if self._editor is not None:
            with contextlib.suppress(RuntimeError):
                self._editor.changes_made.disconnect(self._on_changes_made)
                self._editor.filing_indicators_changed.disconnect(self._on_filing_indicators_changed)

        self._current_taxonomy = None
        self._current_instance = None
        self._editor = None
        self._table_view = None
        self._sidebar = None
        self._browser_splitter = None
        self._context_bar = None
        self._table_chip_sep = None
        self._table_chip_label = None
        self._context_title_label = None
        self._context_meta_label = None

        self._reload_action.setEnabled(False)
        self._new_instance_action.setEnabled(False)
        self._open_instance_action.setEnabled(True)  # Keep enabled; allows opening instances directly
        self._save_action.setEnabled(False)
        self._save_as_action.setEnabled(False)
        self._validate_action.setEnabled(False)
        self._close_instance_action.setEnabled(False)
        self._close_taxonomy_action.setEnabled(False)

        self.setWindowTitle("BDE XBRL Editor[*]")
        self.setWindowModified(False)
        self._status.showMessage("No taxonomy loaded")
        self._show_loader_widget()

    def _on_close_instance(self) -> None:
        """Close the current instance and return to the taxonomy browser."""
        if not self._check_unsaved_changes():
            return

        if self._editor is not None:
            with contextlib.suppress(RuntimeError):
                self._editor.changes_made.disconnect(self._on_changes_made)
                self._editor.filing_indicators_changed.disconnect(self._on_filing_indicators_changed)

        self._current_instance = None
        self._editor = None

        self._save_action.setEnabled(False)
        self._save_as_action.setEnabled(False)
        self._validate_action.setEnabled(False)
        self._close_instance_action.setEnabled(False)

        # Return the sidebar to browse mode before rebuilding the layout
        if self._sidebar is not None:
            self._sidebar.clear_instance()

        # Discard existing table view so _setup_browser_layout creates a fresh one
        self._table_view = None

        meta = self._current_taxonomy.metadata if self._current_taxonomy else None
        title = f"BDE XBRL Editor — {meta.name}[*]" if meta else "BDE XBRL Editor[*]"
        self.setWindowTitle(title)
        self.setWindowModified(False)
        self._status.showMessage(
            f"Loaded: {meta.name} v{meta.version}" if meta else "No taxonomy loaded"
        )

        self._setup_browser_layout()

    def _select_first_taxonomy_table(self) -> None:
        if self._sidebar is not None and isValid(self._sidebar):
            self._pending_initial_table_started_at = time.perf_counter()
            self._sidebar.select_first_table()

    def _on_reload(self) -> None:
        if self._current_taxonomy:
            entry_point = self._current_taxonomy.metadata.entry_point_path
            self._show_loader_widget(path=str(entry_point))
            self._loader_widget._on_load()

    def _on_new_instance(self) -> None:
        if self._current_taxonomy is None:
            return
        from bde_xbrl_editor.ui.widgets.instance_creation_wizard.wizard import (
            InstanceCreationWizard,
        )

        wizard = InstanceCreationWizard(taxonomy=self._current_taxonomy, parent=self)
        if wizard.exec() == QDialog.DialogCode.Accepted:
            instance = wizard.created_instance
            if instance:
                self._load_instance(instance, enable_editing=True)

    # ------------------------------------------------------------------
    # File → Open Instance (T015)
    # ------------------------------------------------------------------

    def _on_open_instance(self) -> None:
        if not self._check_unsaved_changes():
            return

        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Open XBRL Instance",
            "",
            "XBRL Files (*.xbrl *.xml);;All Files (*)",
        )
        if not path_str:
            return

        self._begin_instance_open(path_str)

    def _begin_instance_open(self, path_str: str) -> None:
        if self._instance_open_thread is not None:
            return

        dialog = self._show_loading_dialog("Loading Instance…", "Initialising instance load…")
        dialog.set_context("Instance", path_str)

        self._status.showMessage("Opening instance…")
        self._open_instance_action.setEnabled(False)
        self._instance_open_started_at = time.perf_counter()
        self._pending_load_timing = None
        self._instance_open_worker = InstanceLoadWorker(self._cache, self._settings, path_str)
        self._instance_open_worker.set_preloaded_taxonomy(self._current_taxonomy)
        self._instance_open_thread = QThread(self)
        self._instance_open_worker.moveToThread(self._instance_open_thread)
        self._instance_open_thread.started.connect(self._instance_open_worker.run)
        self._instance_open_worker.progress.connect(
            dialog.update_progress,
            Qt.ConnectionType.QueuedConnection,
        )
        self._instance_open_worker.finished.connect(
            self._on_open_instance_finished,
            Qt.ConnectionType.QueuedConnection,
        )
        self._instance_open_worker.taxonomy_resolved.connect(
            self._on_open_instance_taxonomy_resolved,
            Qt.ConnectionType.QueuedConnection,
        )
        self._instance_open_worker.error.connect(
            self._on_open_instance_error,
            Qt.ConnectionType.QueuedConnection,
        )
        self._instance_open_worker.orphaned.connect(
            self._on_instance_orphaned,
            Qt.ConnectionType.QueuedConnection,
        )
        self._instance_open_thread.start()

    def _show_loading_dialog(self, title: str, message: str) -> TaxonomyProgressDialog:
        if self._loading_dialog is None:
            self._loading_dialog = TaxonomyProgressDialog(self)
        self._loading_dialog.setWindowTitle(title)
        self._loading_dialog.reset()
        self._loading_dialog.setLabelText(message)
        self._loading_dialog.show()
        return self._loading_dialog

    def _close_loading_dialog(self) -> None:
        if self._loading_dialog is not None:
            self._loading_dialog.close()

    def _cleanup_instance_open_thread(self) -> None:
        if self._instance_open_thread is not None:
            self._instance_open_thread.quit()
            self._instance_open_thread.wait()
            self._instance_open_thread = None
            self._instance_open_worker = None
        self._open_instance_action.setEnabled(True)

    def _on_open_instance_finished(self, instance, taxonomy: TaxonomyStructure) -> None:
        self._cleanup_instance_open_thread()
        elapsed = 0.0
        if self._instance_open_started_at is not None:
            elapsed = time.perf_counter() - self._instance_open_started_at
        self._pending_load_timing = LoadTiming(
            total_seconds=elapsed,
            stages=(StageTiming("instance parse", elapsed),),
        )
        if self._loading_dialog is not None:
            self._loading_dialog.update_progress(
                f"Opening workspace… after {format_duration(elapsed)}",
                100,
                100,
            )
        self._current_taxonomy = taxonomy
        self._reload_action.setEnabled(True)
        self._new_instance_action.setEnabled(True)
        self._close_taxonomy_action.setEnabled(True)
        self._load_instance(instance)

    def _on_open_instance_taxonomy_resolved(self, taxonomy: TaxonomyStructure) -> None:
        """Surface taxonomy readiness before instance parsing completes."""
        if (
            self._current_taxonomy is not None
            and self._same_taxonomy(taxonomy)
            and self._sidebar is not None
            and isValid(self._sidebar)
        ):
            return
        self._on_taxonomy_loaded(taxonomy)

    def _on_open_instance_error(self, message: str) -> None:
        self._cleanup_instance_open_thread()
        self._close_loading_dialog()
        self._status.showMessage("Instance load failed")
        QMessageBox.critical(self, "Instance Load Error", message)

    def _on_instance_orphaned(self, count: int) -> None:
        QMessageBox.information(
            self,
            "Orphaned Facts",
            f"{count} fact(s) in this instance have concepts not found in the "
            f"taxonomy and will be preserved verbatim on save.",
        )

    def _load_instance(self, instance, *, enable_editing: bool = False) -> None:
        from bde_xbrl_editor.instance.editor import InstanceEditor  # noqa: PLC0415
        from bde_xbrl_editor.ui.widgets.xbrl_table_view import XbrlTableView  # noqa: PLC0415
        workspace_started_at = time.perf_counter()

        # Disconnect old editor signals
        if self._editor is not None:
            self._editor.changes_made.disconnect(self._on_changes_made)
            self._editor.filing_indicators_changed.disconnect(self._on_filing_indicators_changed)

        self._current_instance = instance
        self._editor = InstanceEditor(instance, parent=self)
        self._editor.changes_made.connect(self._on_changes_made)
        self._editor.filing_indicators_changed.connect(self._on_filing_indicators_changed)
        if self._table_view is not None:
            self._table_view.set_editor(self._editor)

        self._table_view = XbrlTableView(parent=self)
        self._table_view.editing_mode_changed.connect(self._on_table_editing_mode_changed)
        self._table_view.layout_ready.connect(self._on_table_layout_ready)

        self._sidebar = ActivitySidebar(
            self._current_taxonomy,
            parent=self,
            visible_indexes=(3,),
            initial_index=3,
        )
        self._sidebar.table_selected.connect(self._on_table_selected)
        self._sidebar.width_changed.connect(self._on_sidebar_width_changed)
        self._sidebar.set_instance(instance, self._current_taxonomy, self._editor)
        self._table_view.set_editing_enabled(enable_editing)
        self._sidebar.set_instance_editing_enabled(self._table_view.editing_enabled)

        splitter = QSplitter(self)
        splitter.addWidget(self._sidebar)
        splitter.addWidget(self._table_view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self._browser_splitter = splitter

        container = QWidget(self)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self._context_bar = self._build_context_bar(instance=instance)
        container_layout.addWidget(self._context_bar)
        container_layout.addWidget(splitter, stretch=1)

        self.setCentralWidget(container)

        self._save_action.setEnabled(True)
        self._save_as_action.setEnabled(True)
        self._validate_action.setEnabled(True)
        self._close_instance_action.setEnabled(True)

        fname = Path(instance.source_path).name if instance.source_path else "instance"
        self.setWindowTitle(f"BDE XBRL Editor — {fname}[*]")
        self.setWindowModified(False)
        self._status.showMessage(
            f"Opened: {instance.source_path} — "
            f"{len(instance.facts)} facts, {len(instance.contexts)} contexts"
        )

        self._ensure_validation_panel()
        dock = self._find_validation_dock()
        if dock:
            dock.setVisible(True)
        if self._validation_panel:
            self._validation_panel.clear()
        self._show_validation_panel_action.setEnabled(True)

        self._close_loading_dialog()
        workspace_elapsed = time.perf_counter() - workspace_started_at
        if self._pending_load_timing is not None:
            self._pending_load_timing = LoadTiming(
                total_seconds=self._pending_load_timing.total_seconds + workspace_elapsed,
                stages=self._pending_load_timing.stages + (StageTiming("workspace", workspace_elapsed),),
            )

        # Give Qt a chance to paint the workspace shell before the first table render starts.
        QTimer.singleShot(self._INITIAL_TABLE_RENDER_DELAY_MS, self._select_initial_instance_table)

    def _on_sidebar_width_changed(self, width: int) -> None:
        splitter = self._browser_splitter
        if splitter is None or not isValid(splitter):
            return

        def _apply() -> None:
            if not isValid(splitter):
                return
            total = sum(splitter.sizes())
            if total <= 0:
                total = splitter.width()
            main_width = max(total - width, 0)
            splitter.setSizes([width, main_width])

        if splitter.width() > 0 or sum(splitter.sizes()) > 0:
            _apply()
        else:
            QTimer.singleShot(0, _apply)

    def _select_initial_instance_table(self) -> None:
        if (
            self._sidebar is None
            or not isValid(self._sidebar)
            or self._table_view is None
            or not isValid(self._table_view)
            or self._current_instance is None
            or self._table_view.active_table_id is not None
        ):
            return
        self._pending_initial_table_started_at = time.perf_counter()
        self._sidebar.select_first_instance_table()

    # ------------------------------------------------------------------
    # Table selection → XbrlTableView (T017)
    # ------------------------------------------------------------------

    def _on_table_selected(self, table) -> None:
        if self._table_view is None or self._current_taxonomy is None:
            return
        if self._sidebar is not None:
            self._sidebar.set_cell_info_html(None)
        if self._context_title_label is not None:
            variants = dict(getattr(table, "label_variants", ()) or ())
            table_label = next(
                (variants[lang] for lang in self._current_language_preference() if lang in variants),
                getattr(table, "label", None) or getattr(table, "table_id", ""),
            )
            self._context_title_label.setText(table_label)
        if self._context_meta_label is not None and self._current_taxonomy is not None:
            meta = self._current_taxonomy.metadata
            meta_parts = [meta.name, f"Version {meta.version}"]
            table_identity = self._table_identity(table)
            if table_identity:
                meta_parts.append(table_identity)
            if self._current_instance is not None:
                fname = Path(self._current_instance.source_path).name if self._current_instance.source_path else "Unsaved instance"
                meta_parts.append(fname)
            self._context_meta_label.setText("  |  ".join(meta_parts))
        self._table_view.request_table(
            table=table,
            taxonomy=self._current_taxonomy,
            instance=self._current_instance,
        )

    def _on_cell_info_changed(self, html: str) -> None:
        if self._sidebar is not None:
            self._sidebar.set_cell_info_html(html)

    def _on_table_layout_ready(self, layout) -> None:
        if (
            self._table_view is None
            or self._current_taxonomy is None
            or layout is None
        ):
            return
        if self._editor is not None:
            from bde_xbrl_editor.ui.widgets.cell_edit_delegate import (
                CellEditDelegate,  # noqa: PLC0415
            )

            delegate = CellEditDelegate(
                taxonomy=self._current_taxonomy,
                editor=self._editor,
                table_layout=layout,
                table_view_widget=self._table_view._body_view,
            )
            self._table_view._body_view.setItemDelegate(delegate)
            self._table_view.set_editor(self._editor)
        if self._pending_initial_table_started_at is not None:
            first_table_elapsed = time.perf_counter() - self._pending_initial_table_started_at
            if self._pending_load_timing is not None:
                final_timing = LoadTiming(
                    total_seconds=self._pending_load_timing.total_seconds + first_table_elapsed,
                    stages=self._pending_load_timing.stages + (StageTiming("first table", first_table_elapsed),),
                )
                timing_text = format_stage_timings(final_timing.stages)
                if self._current_instance is not None:
                    self._status.showMessage(
                        f"Opened: {self._current_instance.source_path} — "
                        f"{len(self._current_instance.facts)} facts, {len(self._current_instance.contexts)} contexts — {timing_text}"
                    )
                else:
                    meta = self._current_taxonomy.metadata
                    self._status.showMessage(
                        f"Loaded: {meta.name} v{meta.version} — "
                        f"{len(self._current_taxonomy.concepts)} concepts, {len(self._current_taxonomy.tables)} tables — {timing_text}"
                    )
            self._pending_initial_table_started_at = None

    def _on_changes_made(self) -> None:
        self.setWindowModified(True)
        if self._sidebar is not None and isValid(self._sidebar) and self._current_instance is not None and self._current_taxonomy is not None:
            self._sidebar.refresh_instance_panel(self._current_instance, self._current_taxonomy, self._editor)
            self._sidebar.set_instance_editing_enabled(
                bool(self._table_view is not None and isValid(self._table_view) and self._table_view.editing_enabled)
            )
        table_view = self._table_view
        if table_view is not None and isValid(table_view):
            # Defer refresh so the editor widget is fully closed before the model is replaced.
            def _refresh() -> None:
                if not isValid(table_view):
                    return
                table_view.refresh_instance(self._current_instance)

            QTimer.singleShot(0, _refresh)

    # ------------------------------------------------------------------
    # File → Save / Save As (T029, T030)
    # ------------------------------------------------------------------

    def _on_save(self) -> None:
        if self._current_instance is None:
            return
        if self._current_instance.source_path:
            self._do_save(self._current_instance.source_path)
        else:
            self._on_save_as()

    def _on_save_as(self) -> None:
        if self._current_instance is None:
            return
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Save XBRL Instance As",
            str(self._current_instance.source_path or ""),
            "XBRL Files (*.xbrl *.xml);;All Files (*)",
        )
        if not path_str:
            return
        target = Path(path_str)
        if (
            target.exists()
            and target != self._current_instance.source_path
        ):
            reply = QMessageBox.question(
                self,
                "Overwrite?",
                f"'{target.name}' already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        self._do_save(target)

    def _do_save(self, path: Path) -> None:
        from bde_xbrl_editor.instance.constants import is_bde_schema_ref  # noqa: PLC0415
        from bde_xbrl_editor.instance.models import InstanceSaveError  # noqa: PLC0415
        from bde_xbrl_editor.instance.serializer import InstanceSerializer  # noqa: PLC0415

        if self._current_instance is not None and (
            is_bde_schema_ref(self._current_instance.schema_ref_href)
            or self._current_instance.bde_preambulo is not None
        ):
            reply = QMessageBox.question(
                self,
                "Check Filing Indicators",
                "Please confirm the Filing Indicators / Estados Reportados are set correctly before saving. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        serializer = InstanceSerializer()
        try:
            serializer.save(self._current_instance, path)
            if self._editor is not None:
                self._editor.mark_saved(path)
        except InstanceSaveError as exc:
            QMessageBox.critical(self, "Save Error", str(exc))
            return

        self.setWindowModified(False)
        self._status.showMessage(f"Saved: {path}")

    def _on_table_editing_mode_changed(self, enabled: bool) -> None:
        if self._sidebar is not None and isValid(self._sidebar):
            self._sidebar.set_instance_editing_enabled(enabled)

    def _on_filing_indicators_changed(self) -> None:
        self.setWindowModified(True)
        if self._sidebar is not None and isValid(self._sidebar) and self._current_instance is not None and self._current_taxonomy is not None:
            self._sidebar.refresh_instance_panel(self._current_instance, self._current_taxonomy, self._editor)
            self._sidebar.set_instance_editing_enabled(
                bool(self._table_view is not None and isValid(self._table_view) and self._table_view.editing_enabled)
            )

    # ------------------------------------------------------------------
    # Unsaved-changes guard (T034, T035)
    # ------------------------------------------------------------------

    def _check_unsaved_changes(self) -> bool:
        """Return True if it's safe to proceed (no unsaved changes or user chose to handle them)."""
        if self._current_instance is None or not self._current_instance.has_unsaved_changes:
            return True
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes. Save before continuing?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            self._on_save()
            return True
        return reply == QMessageBox.StandardButton.Discard

    # ------------------------------------------------------------------
    # Validation (Feature 005)
    # ------------------------------------------------------------------

    def _ensure_validation_panel(self) -> None:
        """Lazily create and dock the ValidationPanel."""
        if self._validation_panel is not None:
            return
        from bde_xbrl_editor.ui.widgets.validation_panel import ValidationPanel  # noqa: PLC0415

        self._validation_panel = ValidationPanel(self)
        self._validation_panel.revalidate_requested.connect(self._trigger_validation)
        self._validation_panel.navigate_to_cell.connect(self._on_navigate_to_cell)

        dock = QDockWidget("Validation", self)
        dock.setObjectName("ValidationDock")
        dock.setWidget(self._validation_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        self._show_validation_panel_action.setEnabled(True)

    def _show_validation_panel(self) -> None:
        self._ensure_validation_panel()
        dock = self._find_validation_dock()
        if dock:
            dock.setVisible(True)
            dock.raise_()

    def _find_validation_dock(self) -> QDockWidget | None:
        for dock in self.findChildren(QDockWidget):
            if dock.objectName() == "ValidationDock":
                return dock
        return None

    def _on_validate_from_context_bar(self) -> None:
        """Show the validation dock and start a validation run."""
        self._show_validation_panel()
        self._trigger_validation()

    def _trigger_validation(self) -> None:
        """Start a background validation run. Guard against double-trigger."""
        if self._current_instance is None or self._current_taxonomy is None:
            return
        if self._validation_thread is not None and self._validation_thread.isRunning():
            return

        self._ensure_validation_panel()
        assert self._validation_panel is not None  # guaranteed by _ensure_validation_panel

        from bde_xbrl_editor.ui.widgets.validation_panel import ValidationWorker  # noqa: PLC0415

        self._validate_action.setEnabled(False)
        self._validation_panel.clear()
        self._validation_panel.show_progress(0, 1, "Starting validation…")

        self._validation_worker = ValidationWorker(
            taxonomy=self._current_taxonomy,
            instance=self._current_instance,
        )
        self._validation_thread = QThread(self)

        self._validation_worker.moveToThread(self._validation_thread)
        self._validation_thread.started.connect(self._validation_worker.run)
        self._validation_worker.progress_changed.connect(
            self._on_validation_progress, Qt.ConnectionType.QueuedConnection
        )
        self._validation_worker.findings_ready.connect(
            self._on_validation_findings_ready, Qt.ConnectionType.QueuedConnection
        )
        self._validation_worker.validation_completed.connect(
            self._on_validation_done, Qt.ConnectionType.QueuedConnection
        )
        self._validation_worker.validation_failed.connect(
            self._on_validation_error, Qt.ConnectionType.QueuedConnection
        )
        self._validation_thread.start()

    def _on_validation_progress(self, current: int, total: int, message: str) -> None:
        if self._validation_panel:
            self._validation_panel.show_progress(current, total, message)

    def _on_validation_findings_ready(self, findings) -> None:
        if self._validation_panel:
            self._validation_panel.append_findings(tuple(findings))

    def _on_validation_done(self, report) -> None:
        self._cleanup_validation_thread()
        if self._validation_panel:
            self._validation_panel.show_report(report)
        status = "PASSED" if report.passed else f"FAILED ({report.error_count} error(s))"
        if report.stage_timings:
            self._status.showMessage(
                f"Validation {status} in {format_duration(report.total_elapsed_seconds)} — "
                f"{format_stage_timings(report.stage_timings)}"
            )
        else:
            self._status.showMessage(f"Validation {status}")

    def _on_validation_error(self, error_message: str) -> None:
        self._cleanup_validation_thread()
        if self._validation_panel:
            self._validation_panel.clear()
        QMessageBox.critical(self, "Validation Error", error_message)

    def _cleanup_validation_thread(self) -> None:
        self._validate_action.setEnabled(
            self._current_instance is not None and self._current_taxonomy is not None
        )
        if self._validation_thread:
            self._validation_thread.quit()
            self._validation_thread.wait()
            self._validation_thread = None
        self._validation_worker = None

    def _on_navigate_to_cell(self, context_ref: str, finding) -> None:
        """Navigate XbrlTableView to the cell for this finding (best-effort)."""
        # Currently just scrolls to a matching table; full navigation depends on
        # the table view's ability to locate a context_ref within a rendered cell.
        if self._table_view is None:
            return
        # No-op for now; full implementation would locate cell by (concept, context_ref).

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Warn if there are unsaved changes before closing (T034)."""
        if self._current_instance is None or not self._current_instance.has_unsaved_changes:
            event.accept()
            return
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes. Save before quitting?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            self._on_save()
            event.accept()
        elif reply == QMessageBox.StandardButton.Discard:
            event.accept()
        else:
            event.ignore()

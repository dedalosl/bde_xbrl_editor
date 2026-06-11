"""QMainWindow shell — Features 001 + 002 + 004 + 005 UI."""

from __future__ import annotations

import contextlib
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
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
from bde_xbrl_editor.taxonomy import TaxonomyCache, TaxonomyLoader, TaxonomyStructure
from bde_xbrl_editor.ui import theme
from bde_xbrl_editor.ui.loading import FormulaHydrationWorker, InstanceLoadWorker
from bde_xbrl_editor.ui.widgets.activity_sidebar import ActivitySidebar
from bde_xbrl_editor.ui.widgets.loader_settings_dialog import (
    load_loader_page_mode,
    load_saved_settings,
)
from bde_xbrl_editor.ui.widgets.progress_dialog import TaxonomyProgressDialog
from bde_xbrl_editor.ui.widgets.taxonomy_catalog_loader_widget import (
    TaxonomyCatalogLoaderWidget,
)
from bde_xbrl_editor.ui.widgets.taxonomy_loader_widget import TaxonomyLoaderWidget


@dataclass(frozen=True)
class _FormulaInputHint:
    name: str
    fallback: str | None = None
    hint: str = "Enter an XPath literal value"
    example: str = "Example: 123, true(), 2026-01-31, or text"


def _formula_input_hint(name: str, select_xpath: str | None = None) -> str:
    text = f"{name} {select_xpath or ''}".lower()
    if "codigoparticipada" in text or "cod_participada" in text:
        return "Bank of Spain code for a participating entity. Use the taxonomy-specific code."
    if "leipresentadora" in text or "lei_presentadora" in text:
        return "LEI code for the reporting entity. Use the taxonomy-specific code."
    if "date" in text or "fecha" in text:
        return "Date value. Use ISO format YYYY-MM-DD."
    if "qname" in text or "tipoentidad" in text or "tipo_entidad" in text:
        return "QName or code-like text. Use the taxonomy prefix when the rule expects a QName."
    if "bool" in text or "succomunitaria" in text:
        return "Boolean-like value. Use true()/false() or the taxonomy-specific code."
    if "count" in text or "number" in text or "amount" in text or "importe" in text:
        return "Numeric value. Use digits with a dot as decimal separator."
    return "XPath atomic value. Numbers, booleans, dates, QNames, and plain text are accepted."


def _formula_input_example(
    name: str,
    select_xpath: str | None = None,
    fallback: str | None = None,
) -> str:
    if fallback is not None:
        return f"Blank uses fallback: {fallback}"
    hint = _formula_input_hint(name, select_xpath).lower()
    if "code" in hint and "participating" in hint:
        return "Example: 12345 (Bank of Spain-specific code for a participating entity)"
    if "lei" in hint and "code" in hint:
        return "Example: 5493001KJTIIGC8Y1R12 (taxonomy-specific LEI code for the reporting entity)"
    if "date" in hint:
        return "Example: 2026-01-31"
    if "qname" in hint:
        return "Example: prefix:member or code"
    if "boolean" in hint:
        return "Example: true() or false()"
    if "numeric" in hint:
        return "Example: 123.45"
    return "Example: 123, true(), prefix:member, 2026-01-31, or text"


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
        self._formula_hydration_thread: QThread | None = None
        self._formula_hydration_worker: FormulaHydrationWorker | None = None
        self._formula_hydration_entry_point: Path | None = None
        self._pending_load_timing: LoadTiming | None = None
        self._pending_initial_table_started_at: float | None = None
        self._instance_open_started_at: float | None = None

        # Validation
        self._validation_thread: QThread | None = None
        self._validation_worker = None  # ValidationWorker | None
        self._validation_panel = None  # ValidationPanel | None
        self._validation_stack: QStackedWidget | None = None
        self._validation_collapsed_button: QPushButton | None = None
        self._pending_validation_navigation = None

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
                font-family: "Inter", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
                font-size: 12px;
                color: {theme.TEXT_MAIN};
            }}
            QMenuBar {{
                background: {theme.SURFACE_BG};
                color: {theme.TEXT_MAIN};
                padding: 3px 8px;
                border-bottom: 1px solid {theme.BORDER};
            }}
            QMenuBar::item:selected {{
                background: {theme.HOVER_BG};
                border-radius: 4px;
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
                background: {theme.SURFACE_BG};
                color: {theme.TEXT_MUTED};
                border-top: 1px solid {theme.BORDER};
                font-size: 11px;
                padding: 3px 8px;
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
                border: none;
                border-right: 1px solid {theme.BORDER};
                border-bottom: 1px solid {theme.BORDER};
                padding: 5px 8px;
                font-weight: 600;
            }}
            QPushButton, QComboBox, QLineEdit, QTextEdit {{
                background: {theme.INPUT_BG};
                color: {theme.TEXT_MAIN};
                border: 1px solid {theme.BORDER};
                border-radius: 6px;
            }}
            QPushButton {{
                padding: 5px 11px;
            }}
            QPushButton:hover, QComboBox:hover, QLineEdit:hover {{
                border-color: {theme.ACCENT};
                background: {theme.INPUT_BG};
            }}
            QPushButton:pressed {{
                background: {theme.HOVER_BG};
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
                width: 11px;
                background: {theme.SURFACE_BG};
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {theme.BORDER};
                border-radius: 5px;
                margin: 2px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {theme.BORDER_STRONG};
            }}
            QScrollBar:horizontal {{
                height: 11px;
                background: {theme.SURFACE_BG};
                border: none;
            }}
            QScrollBar::handle:horizontal {{
                background: {theme.BORDER};
                border-radius: 5px;
                margin: 2px;
                min-width: 20px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {theme.BORDER_STRONG};
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
        self._loader_widget: TaxonomyLoaderWidget | TaxonomyCatalogLoaderWidget | None = None
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
        """Create a fresh welcome screen and set it as the central widget.

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
        self._cleanup_formula_hydration_thread(cancel=True)

        if load_loader_page_mode() == "catalog":
            widget: TaxonomyLoaderWidget | TaxonomyCatalogLoaderWidget = TaxonomyCatalogLoaderWidget(
                cache=self._cache,
                settings=self._settings,
                parent=self,
            )
        else:
            widget = TaxonomyLoaderWidget(
                cache=self._cache,
                settings=self._settings,
                parent=self,
            )
        widget.taxonomy_loaded.connect(self._on_taxonomy_loaded)
        widget.instance_loaded.connect(self._on_instance_loaded_from_widget)
        widget.settings_changed.connect(self._on_loader_settings_changed)
        if isinstance(widget, TaxonomyCatalogLoaderWidget):
            widget.status_message_changed.connect(self._on_loader_status_message)
        if path is not None:
            if isinstance(widget, TaxonomyLoaderWidget):
                widget._path_edit.setText(path)
            else:
                widget.load_entry_point_path(path)
        self._loader_widget = widget
        self.setCentralWidget(widget)

    def _setup_statusbar(self) -> None:
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("No taxonomy loaded")

    def _on_loader_status_message(self, message: str) -> None:
        if hasattr(self, "_status"):
            self._status.showMessage(message)

    # ------------------------------------------------------------------
    # Taxonomy actions
    # ------------------------------------------------------------------

    def _show_loader(self) -> None:
        if not self._check_unsaved_changes():
            return
        self._show_loader_widget()

    def _on_loader_settings_changed(self) -> None:
        self._settings = load_saved_settings()
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
        self._start_formula_hydration_if_needed()

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
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        self._browser_splitter = splitter

        container = QWidget(self)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self._context_bar = self._build_context_bar(instance=None)
        container_layout.addWidget(self._context_bar)
        container_layout.addWidget(splitter, stretch=1)

        self.setCentralWidget(container)
        self._on_sidebar_width_changed(self._sidebar.width())

        # Give Qt a chance to paint the workspace shell before the first table render starts.
        QTimer.singleShot(self._INITIAL_TABLE_RENDER_DELAY_MS, self._select_first_taxonomy_table)

    # ------------------------------------------------------------------
    # Context bar
    # ------------------------------------------------------------------

    def _build_context_bar(self, instance=None) -> QFrame:
        """Return a structured workspace header with context on the left and actions on the right."""
        bar = QFrame()
        bar.setObjectName("ContextBar")
        bar.setFixedHeight(70)
        bar.setStyleSheet(
            f"QFrame#ContextBar {{ background: {theme.SURFACE_BG}; border-bottom: 1px solid {theme.BORDER}; }}"
        )

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        context_block = QWidget(bar)
        context_layout = QVBoxLayout(context_block)
        context_layout.setContentsMargins(0, 0, 0, 0)
        context_layout.setSpacing(2)

        eyebrow = QLabel("Workspace")
        eyebrow.setStyleSheet(
            f"color: {theme.TEXT_SUBTLE}; font-size: 10px; font-weight: 700; letter-spacing: 0;"
        )
        context_layout.addWidget(eyebrow)

        title = QLabel()
        title.setStyleSheet(
            f"color: {theme.TEXT_MAIN}; font-size: 17px; font-weight: 700; background: transparent;"
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
        self._table_chip_label = None
        self._table_chip_sep = None
        self._language_combo = None

        layout.addWidget(context_block, stretch=1)

        btn_style = (
            f"QPushButton {{ color: {theme.TEXT_MAIN}; background: {theme.SURFACE_BG};"
            f" border: 1px solid {theme.BORDER}; border-radius: 6px;"
            " font-size: 11px; font-weight: 600; padding: 0 11px; }"
            f"QPushButton:hover {{ background: {theme.HOVER_BG}; border-color: {theme.ACCENT}; }}"
            f"QPushButton:disabled {{ color: {theme.DISABLED_FG}; background: transparent;"
            f" border-color: {theme.BORDER}; }}"
        )
        primary_btn_style = (
            f"QPushButton {{ color: {theme.TEXT_INVERSE}; background: {theme.ACCENT};"
            " border: none; border-radius: 6px; font-size: 11px; font-weight: 700; padding: 0 12px; }"
            f"QPushButton:hover {{ background: {theme.NAV_BG}; }}"
            f"QPushButton:disabled {{ background: {theme.DISABLED_BG}; color: {theme.DISABLED_FG}; }}"
        )

        action_group = QWidget(bar)
        action_layout = QHBoxLayout(action_group)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(7)

        if self._current_taxonomy is not None:
            self._language_combo = self._build_language_combo(bar)
            action_layout.addWidget(self._language_combo)

        if instance is not None:
            close_inst_btn = QPushButton("Close Instance")
            close_inst_btn.setStyleSheet(btn_style)
            close_inst_btn.setFixedHeight(30)
            close_inst_btn.clicked.connect(self._on_close_instance)
            action_layout.addWidget(close_inst_btn)

            validate_btn = QPushButton("Validate")
            validate_btn.setStyleSheet(primary_btn_style)
            validate_btn.setFixedHeight(30)
            validate_btn.setToolTip("Run validation on the current instance (Ctrl+Shift+V)")
            validate_btn.clicked.connect(self._on_validate_from_context_bar)
            action_layout.addWidget(validate_btn)

            save_btn = QPushButton("Save")
            save_btn.setStyleSheet(primary_btn_style)
            save_btn.setFixedHeight(30)
            save_btn.clicked.connect(self._on_save)
            action_layout.addWidget(save_btn)

            open_inst_btn = QPushButton("Open Instance…")
            open_inst_btn.setStyleSheet(btn_style)
            open_inst_btn.setFixedHeight(30)
            open_inst_btn.clicked.connect(self._on_open_instance)
            action_layout.addWidget(open_inst_btn)

            new_inst_btn = QPushButton("New Instance…")
            new_inst_btn.setStyleSheet(btn_style)
            new_inst_btn.setFixedHeight(30)
            new_inst_btn.clicked.connect(self._on_new_instance)
            action_layout.addWidget(new_inst_btn)

        elif self._current_taxonomy is not None:
            back_btn = QPushButton("Back")
            back_btn.setStyleSheet(btn_style)
            back_btn.setFixedHeight(30)
            back_btn.clicked.connect(self._on_close_taxonomy)
            action_layout.addWidget(back_btn)

            open_inst_btn = QPushButton("Open Instance…")
            open_inst_btn.setStyleSheet(btn_style)
            open_inst_btn.setFixedHeight(30)
            open_inst_btn.clicked.connect(self._on_open_instance)
            action_layout.addWidget(open_inst_btn)

            new_inst_btn = QPushButton("New Instance…")
            new_inst_btn.setStyleSheet(primary_btn_style)
            new_inst_btn.setFixedHeight(30)
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
            f" border: 1px solid {theme.BORDER}; border-radius: 6px;"
            " font-size: 11px; font-weight: 600; padding: 0 8px; min-width: 72px; }"
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
        if dock := self._find_validation_dock():
            dock.setVisible(False)
        self._set_validation_panel_expanded(False, "Validation — not run")

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
        if dock := self._find_validation_dock():
            dock.setVisible(False)
        self._set_validation_panel_expanded(False, "Validation — not run")

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
        self._start_formula_hydration_if_needed()

    def _select_first_taxonomy_table(self) -> None:
        if self._sidebar is not None and isValid(self._sidebar):
            self._pending_initial_table_started_at = time.perf_counter()
            self._sidebar.select_first_table()

    def _on_reload(self) -> None:
        if self._current_taxonomy and self._loader_widget is not None:
            entry_point = self._current_taxonomy.metadata.entry_point_path
            self._show_loader_widget(path=str(entry_point))
            if isinstance(self._loader_widget, TaxonomyLoaderWidget):
                self._loader_widget._on_load()
            else:
                self._loader_widget.load_entry_point_path(str(entry_point))

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
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        self._browser_splitter = splitter

        container = QWidget(self)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        self._context_bar = self._build_context_bar(instance=instance)
        container_layout.addWidget(self._context_bar)
        container_layout.addWidget(splitter, stretch=1)

        self.setCentralWidget(container)
        self._on_sidebar_width_changed(self._sidebar.width())

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
            self._set_validation_panel_expanded(False, "Validation — not run")
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
        self._start_formula_hydration_if_needed()

    def _start_formula_hydration_if_needed(self) -> None:
        taxonomy = self._current_taxonomy
        if taxonomy is None:
            return

        entry_point = taxonomy.metadata.entry_point_path.resolve()
        if (
            self._formula_hydration_thread is not None
            and self._formula_hydration_thread.isRunning()
        ):
            if self._formula_hydration_entry_point == entry_point:
                return
            self._cleanup_formula_hydration_thread(cancel=True)

        loader = TaxonomyLoader(cache=self._cache, settings=self._settings)
        if not loader.has_deferred_formula_assertions(taxonomy):
            return

        self._formula_hydration_entry_point = entry_point
        self._formula_hydration_worker = FormulaHydrationWorker(loader, taxonomy)
        self._formula_hydration_thread = QThread(self)
        self._formula_hydration_worker.moveToThread(self._formula_hydration_thread)
        self._formula_hydration_thread.started.connect(self._formula_hydration_worker.run)
        self._formula_hydration_worker.progress.connect(
            self._on_formula_hydration_progress,
            Qt.ConnectionType.QueuedConnection,
        )
        self._formula_hydration_worker.partial.connect(
            self._on_formula_hydration_partial,
            Qt.ConnectionType.QueuedConnection,
        )
        self._formula_hydration_worker.finished.connect(
            self._on_formula_hydration_finished,
            Qt.ConnectionType.QueuedConnection,
        )
        self._formula_hydration_worker.error.connect(
            self._on_formula_hydration_error,
            Qt.ConnectionType.QueuedConnection,
        )
        self._status.showMessage("Loading validation rules in background…")
        self._formula_hydration_thread.start()

    def _on_formula_hydration_progress(self, message: str, current: int, total: int) -> None:
        if total > 0:
            percent = int(current / total * 100)
            self._status.showMessage(f"{message} ({percent}%)")
        else:
            self._status.showMessage(message)

    def _on_formula_hydration_partial(self, taxonomy: TaxonomyStructure) -> None:
        if not self._same_taxonomy(taxonomy):
            return
        self._current_taxonomy = taxonomy
        if self._sidebar is not None and isValid(self._sidebar):
            self._sidebar.update_taxonomy_validations(taxonomy)

    def _on_formula_hydration_finished(self, taxonomy: TaxonomyStructure) -> None:
        self._cleanup_formula_hydration_thread()
        if not self._same_taxonomy(taxonomy):
            return
        self._current_taxonomy = taxonomy
        if self._sidebar is not None and isValid(self._sidebar):
            self._sidebar.update_taxonomy_validations(taxonomy)
        assertion_count = len(taxonomy.formula_assertion_set.assertions)
        self._cache.put(str(taxonomy.metadata.entry_point_path.resolve()), taxonomy)
        self._status.showMessage(f"Validation rules loaded — {assertion_count} assertion(s)")

    def _on_formula_hydration_error(self, message: str) -> None:
        self._cleanup_formula_hydration_thread()
        self._status.showMessage(f"Validation rule loading failed: {message}")

    def _cleanup_formula_hydration_thread(self, *, cancel: bool = False) -> None:
        worker = self._formula_hydration_worker
        if cancel and worker is not None:
            worker.cancel()
        thread = self._formula_hydration_thread
        if thread is not None:
            thread.quit()
            thread.wait()
        self._formula_hydration_thread = None
        self._formula_hydration_worker = None
        self._formula_hydration_entry_point = None

    def _on_sidebar_width_changed(self, width: int) -> None:
        splitter = self._browser_splitter
        if splitter is None or not isValid(splitter):
            return

        def _apply() -> None:
            if not isValid(splitter):
                return
            parent_width = 0
            parent = splitter.parentWidget()
            if parent is not None and isValid(parent):
                parent_width = parent.width()
            total = max(sum(splitter.sizes()), splitter.width(), parent_width, self.width())
            main_width = max(total - width, 1)
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
        if self._pending_validation_navigation is not None:
            context_ref, finding = self._pending_validation_navigation
            self._pending_validation_navigation = None
            self._on_navigate_to_cell(context_ref, finding)

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
        self._validation_panel.collapse_requested.connect(
            lambda: self._set_validation_panel_expanded(False)
        )

        self._validation_stack = QStackedWidget(self)
        self._validation_collapsed_button = QPushButton("  ●  Validation — not run")
        self._validation_collapsed_button.setFixedHeight(34)
        self._validation_collapsed_button.setStyleSheet(
            f"""
            QPushButton {{
                text-align: left;
                color: {theme.TEXT_MAIN};
                background: {theme.SURFACE_BG};
                border: 1px solid {theme.BORDER};
                border-radius: 6px;
                font-size: 11px;
                font-weight: 650;
                padding: 0 12px;
            }}
            QPushButton:hover {{
                background: {theme.HOVER_BG};
                border-color: {theme.ACCENT};
            }}
            """
        )
        self._validation_collapsed_button.clicked.connect(self._show_validation_panel)
        self._validation_stack.addWidget(self._validation_collapsed_button)
        self._validation_stack.addWidget(self._validation_panel)

        dock = QDockWidget("", self)
        dock.setObjectName("ValidationDock")
        dock.setTitleBarWidget(QWidget(dock))
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        dock.setStyleSheet(
            f"""
            QDockWidget {{
                background: {theme.WINDOW_BG};
                border-top: 1px solid {theme.BORDER};
            }}
            """
        )
        dock.setWidget(self._validation_stack)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        self._set_validation_panel_expanded(False, "Validation — not run")
        self._show_validation_panel_action.setEnabled(True)

    def _show_validation_panel(self) -> None:
        self._ensure_validation_panel()
        self._set_validation_panel_expanded(True)
        dock = self._find_validation_dock()
        if dock:
            dock.setVisible(True)
            dock.raise_()

    def _set_validation_panel_expanded(self, expanded: bool, label: str | None = None) -> None:
        dock = self._find_validation_dock()
        stack = self._validation_stack
        if dock is None or stack is None:
            return
        if self._validation_collapsed_button is not None and label is not None:
            self._validation_collapsed_button.setText(f"  ●  {label}")
        stack.setCurrentIndex(1 if expanded else 0)
        if expanded:
            dock.setMinimumHeight(220)
            dock.setMaximumHeight(420)
        else:
            dock.setMinimumHeight(44)
            dock.setMaximumHeight(44)

    def _find_validation_dock(self) -> QDockWidget | None:
        for dock in self.findChildren(QDockWidget):
            if dock.objectName() == "ValidationDock":
                return dock
        return None

    def _on_validate_from_context_bar(self) -> None:
        """Start a validation run from the compact command bar."""
        self._trigger_validation()

    def _trigger_validation(self) -> None:
        """Start a background validation run. Guard against double-trigger."""
        if self._current_instance is None or self._current_taxonomy is None:
            return
        if self._validation_thread is not None and self._validation_thread.isRunning():
            return

        general_variable_values = self._prompt_formula_general_variable_values()
        if general_variable_values is None:
            return

        self._ensure_validation_panel()
        assert self._validation_panel is not None  # guaranteed by _ensure_validation_panel
        self._set_validation_panel_expanded(True)

        from bde_xbrl_editor.ui.widgets.validation_panel import ValidationWorker  # noqa: PLC0415

        self._validate_action.setEnabled(False)
        self._validation_panel.clear()
        self._validation_panel.show_progress(0, 1, "Starting validation…")

        self._validation_worker = ValidationWorker(
            taxonomy=self._current_taxonomy,
            instance=self._current_instance,
            general_variable_values=general_variable_values,
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

    def _prompt_formula_general_variable_values(self) -> dict[str, str] | None:
        if self._current_taxonomy is None:
            return {}
        input_hints = self._formula_general_variable_hints()
        if not input_hints:
            return {}

        dialog = QDialog(self)
        dialog.setWindowTitle("Formula General Variables")
        dialog.setMinimumWidth(760)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        intro = QLabel(
            "Provide values for Formula variables before validation. Leave a field blank to use "
            "its fallback when available."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(8)
        edits: dict[str, QLineEdit] = {}
        for item in input_hints:
            edit = QLineEdit()
            edit.setMinimumWidth(380)
            edit.setPlaceholderText(item.example)
            edit.setToolTip(item.hint)
            label_text = item.name
            if item.fallback is not None:
                label_text = f"{label_text} (fallback: {item.fallback})"
            label = QLabel(label_text)
            label.setToolTip(item.hint)
            form.addRow(label, edit)
            edits[item.name] = edit
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return {
            name: edit.text().strip()
            for name, edit in edits.items()
            if edit.text().strip()
        }

    def _formula_general_variable_hints(self) -> list[_FormulaInputHint]:
        if self._current_taxonomy is None:
            return []
        assertion_set = self._current_taxonomy.formula_assertion_set
        from bde_xbrl_editor.validation.formula.static import (  # noqa: PLC0415
            collect_formula_external_variable_names,
        )

        seen: set[str] = set()
        variables: list[_FormulaInputHint] = []
        variable_sets = (*assertion_set.assertions, *assertion_set.output_formulas)
        for variable_set in variable_sets:
            for variable in variable_set.general_variables:
                if variable.variable_name in seen:
                    continue
                seen.add(variable.variable_name)
                variables.append(
                    _FormulaInputHint(
                        name=variable.variable_name,
                        fallback=variable.fallback_value,
                        hint=_formula_input_hint(variable.variable_name, variable.select_xpath),
                        example=_formula_input_example(
                            variable.variable_name,
                            variable.select_xpath,
                            variable.fallback_value,
                        ),
                    )
                )
        for name in collect_formula_external_variable_names(self._current_taxonomy):
            if name in seen:
                continue
            seen.add(name)
            variables.append(
                _FormulaInputHint(
                    name=name,
                    hint=_formula_input_hint(name),
                    example=_formula_input_example(name),
                )
            )
        return variables

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
        label = (
            "Validation — passed"
            if report.passed
            else f"Validation — {report.error_count} error(s)"
        )
        self._set_validation_panel_expanded(True, label)
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
        self._set_validation_panel_expanded(False, "Validation — failed")
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
        if self._table_view is None or not context_ref:
            return
        table_id = getattr(finding, "table_id", None)
        if (
            table_id
            and self._table_view.active_table_id != table_id
            and self._sidebar is not None
        ):
            self._pending_validation_navigation = (context_ref, finding)
            if self._sidebar.select_table_by_id(table_id) is None:
                self._pending_validation_navigation = None
                self._status.showMessage(f"Validation table {table_id} was not found")
            return

        navigated = self._table_view.navigate_to_fact_cell(
            concept_qname=getattr(finding, "concept_qname", None),
            context_ref=context_ref,
        )
        if navigated:
            self._status.showMessage(f"Selected validation cell for context {context_ref}")
        else:
            self._status.showMessage(f"No rendered cell found for context {context_ref}")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """Warn if there are unsaved changes before closing (T034)."""
        if self._current_instance is None or not self._current_instance.has_unsaved_changes:
            self._cleanup_formula_hydration_thread(cancel=True)
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
            self._cleanup_formula_hydration_thread(cancel=True)
            event.accept()
        elif reply == QMessageBox.StandardButton.Discard:
            self._cleanup_formula_hydration_thread(cancel=True)
            event.accept()
        else:
            event.ignore()

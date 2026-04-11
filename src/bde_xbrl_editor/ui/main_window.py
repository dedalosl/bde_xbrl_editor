"""QMainWindow shell — Features 001 + 002 + 004 + 005 UI."""

from __future__ import annotations

import contextlib
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtWidgets import (
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

from bde_xbrl_editor.taxonomy import TaxonomyCache, TaxonomyStructure
from bde_xbrl_editor.ui import theme
from bde_xbrl_editor.ui.widgets.activity_sidebar import ActivitySidebar
from bde_xbrl_editor.ui.widgets.loader_settings_dialog import load_saved_settings
from bde_xbrl_editor.ui.widgets.taxonomy_loader_widget import TaxonomyLoaderWidget


class MainWindow(QMainWindow):
    """Application main window."""

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

        # Validation
        self._validation_thread: QThread | None = None
        self._validation_worker = None  # ValidationWorker | None
        self._validation_panel = None  # ValidationPanel | None

        self._setup_menu()
        self._setup_central()
        self._setup_statusbar()

    def _apply_stylesheet(self) -> None:
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
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

    def _show_loader_widget(self, path: str | None = None) -> None:
        """Create a fresh TaxonomyLoaderWidget and set it as the central widget.

        Qt takes ownership of (and deletes) the previous central widget, so we
        must never reuse the old reference — always construct a new instance.
        """
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
        self._current_taxonomy = structure
        meta = structure.metadata
        table_count = len(structure.tables)
        concept_count = len(structure.concepts)
        self._status.showMessage(
            f"Loaded: {meta.name} v{meta.version} — "
            f"{concept_count} concepts, {table_count} tables"
        )
        self._reload_action.setEnabled(True)
        self._new_instance_action.setEnabled(True)
        self._open_instance_action.setEnabled(True)
        self._close_taxonomy_action.setEnabled(True)

        self._setup_browser_layout()

    def _on_instance_loaded_from_widget(self, instance, taxonomy: TaxonomyStructure) -> None:
        """Handle an instance+taxonomy loaded directly from the welcome screen."""
        self._current_taxonomy = taxonomy
        meta = taxonomy.metadata
        self._reload_action.setEnabled(True)
        self._new_instance_action.setEnabled(True)
        self._open_instance_action.setEnabled(True)
        self._close_taxonomy_action.setEnabled(True)
        self._status.showMessage(
            f"Loaded: {meta.name} v{meta.version} — "
            f"{len(taxonomy.concepts)} concepts, {len(taxonomy.tables)} tables"
        )
        self._load_instance(instance)

    def _setup_browser_layout(self) -> None:
        """Create the main split layout: context bar + activity sidebar + XbrlTableView."""
        from bde_xbrl_editor.ui.widgets.xbrl_table_view import XbrlTableView  # noqa: PLC0415

        assert self._current_taxonomy is not None
        self._sidebar = ActivitySidebar(self._current_taxonomy, parent=self)
        self._sidebar.table_selected.connect(self._on_table_selected)
        self._sidebar.width_changed.connect(self._on_sidebar_width_changed)

        if self._table_view is None:
            self._table_view = XbrlTableView(parent=self)

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

        # Defer first-table render so the splitter/headers are fully laid out first
        QTimer.singleShot(0, self._select_first_taxonomy_table)

    # ------------------------------------------------------------------
    # Context bar
    # ------------------------------------------------------------------

    def _build_context_bar(self, instance=None) -> QFrame:
        """Return a slim bar showing taxonomy + instance breadcrumbs with × close buttons."""
        bar = QFrame()
        bar.setFixedHeight(36)
        bar.setStyleSheet(
            f"QFrame {{ background: {theme.NAV_BG}; border-bottom: 1px solid {theme.BORDER_STRONG}; }}"
        )

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(6)

        chip_style = (
            f"QLabel {{ color: {theme.TEXT_MAIN}; font-size: 11px; font-weight: 600;"
            f" background: rgba(255,253,248,0.55); border: 1px solid {theme.BORDER};"
            " border-radius: 3px; padding: 2px 7px; }"
        )
        close_style = (
            f"QPushButton {{ color: {theme.TEXT_MUTED}; background: transparent; border: none;"
            " font-size: 14px; padding: 0 3px; }"
            f"QPushButton:hover {{ color: {theme.TEXT_MAIN}; background: rgba(255,253,248,0.35);"
            " border-radius: 3px; }"
        )
        sep_style = f"QLabel {{ color: {theme.TEXT_MUTED}; font-size: 14px; background: transparent; }}"

        # ── Taxonomy chip ──────────────────────────────────────────────
        if self._current_taxonomy:
            meta = self._current_taxonomy.metadata
            tax_chip = QLabel(f"◈  {meta.name}  v{meta.version}")
            tax_chip.setStyleSheet(chip_style)
            layout.addWidget(tax_chip)

            tax_close = QPushButton("×")
            tax_close.setFixedSize(20, 20)
            tax_close.setStyleSheet(close_style)
            tax_close.setToolTip("Close taxonomy")
            tax_close.clicked.connect(self._on_close_taxonomy)
            layout.addWidget(tax_close)

        # ── Instance chip ──────────────────────────────────────────────
        if instance is not None:
            sep = QLabel("›")
            sep.setStyleSheet(sep_style)
            layout.addWidget(sep)

            fname = Path(instance.source_path).name if instance.source_path else "instance"
            inst_chip = QLabel(f"  {fname}")
            inst_chip.setStyleSheet(chip_style)
            layout.addWidget(inst_chip)

            inst_close = QPushButton("×")
            inst_close.setFixedSize(20, 20)
            inst_close.setStyleSheet(close_style)
            inst_close.setToolTip("Close instance")
            inst_close.clicked.connect(self._on_close_instance)
            layout.addWidget(inst_close)

        # ── Selected-table chip ────────────────────────────────────────
        table_sep = QLabel("›")
        table_sep.setStyleSheet(sep_style)
        table_sep.setVisible(False)
        layout.addWidget(table_sep)
        self._table_chip_sep = table_sep

        table_chip = QLabel()
        table_chip.setStyleSheet(
            f"QLabel {{ color: {theme.TEXT_MAIN}; font-size: 11px; font-weight: 600;"
            f" background: rgba(255,248,236,0.65); border: 1px solid {theme.BORDER};"
            " border-radius: 3px; padding: 2px 7px; }"
        )
        table_chip.setVisible(False)
        layout.addWidget(table_chip)
        self._table_chip_label = table_chip

        layout.addStretch()

        # ── Action buttons on the right ────────────────────────────────
        btn_style = (
            f"QPushButton {{ color: {theme.TEXT_MAIN}; background: rgba(255,250,242,0.72);"
            f" border: 1px solid {theme.BORDER}; border-radius: 3px;"
            " font-size: 11px; padding: 3px 10px; }"
            f"QPushButton:hover {{ background: {theme.HEADER_BG_LIGHT}; border-color: {theme.BORDER_STRONG}; }}"
            f"QPushButton:disabled {{ color: {theme.DISABLED_FG}; background: transparent;"
            f" border-color: {theme.BORDER}; }}"
        )

        if instance is not None:
            validate_btn = QPushButton("⚡ Validate")
            validate_btn.setStyleSheet(btn_style)
            validate_btn.setToolTip("Run validation on the current instance (Ctrl+Shift+V)")
            validate_btn.clicked.connect(self._on_validate_from_context_bar)
            layout.addWidget(validate_btn)

            save_btn = QPushButton("Save")
            save_btn.setStyleSheet(btn_style)
            save_btn.clicked.connect(self._on_save)
            layout.addWidget(save_btn)

            open_inst_btn = QPushButton("Open Instance…")
            open_inst_btn.setStyleSheet(btn_style)
            open_inst_btn.clicked.connect(self._on_open_instance)
            layout.addWidget(open_inst_btn)

            new_inst_btn = QPushButton("New Instance…")
            new_inst_btn.setStyleSheet(btn_style)
            new_inst_btn.clicked.connect(self._on_new_instance)
            layout.addWidget(new_inst_btn)

        elif self._current_taxonomy is not None:
            open_inst_btn = QPushButton("Open Instance…")
            open_inst_btn.setStyleSheet(btn_style)
            open_inst_btn.clicked.connect(self._on_open_instance)
            layout.addWidget(open_inst_btn)

            new_inst_btn = QPushButton("New Instance…")
            new_inst_btn.setStyleSheet(btn_style)
            new_inst_btn.clicked.connect(self._on_new_instance)
            layout.addWidget(new_inst_btn)

        return bar

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

        self._current_taxonomy = None
        self._current_instance = None
        self._editor = None
        self._table_view = None
        self._sidebar = None
        self._browser_splitter = None
        self._context_bar = None
        self._table_chip_sep = None
        self._table_chip_label = None

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
        if self._sidebar is not None:
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
                self._load_instance(instance)

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

        from bde_xbrl_editor.instance.models import InstanceParseError, TaxonomyResolutionError
        from bde_xbrl_editor.instance.parser import InstanceParser
        from bde_xbrl_editor.taxonomy.loader import TaxonomyLoader

        loader = TaxonomyLoader(cache=self._cache, settings=self._settings)
        parser = InstanceParser(taxonomy_loader=loader)
        try:
            instance, orphaned = parser.load(path_str)
        except TaxonomyResolutionError as exc:
            QMessageBox.critical(self, "Taxonomy Error", str(exc))
            return
        except InstanceParseError as exc:
            QMessageBox.critical(self, "Parse Error", str(exc))
            return

        # Resolve the taxonomy from the instance (may be newly loaded or already in cache)
        if instance.taxonomy_entry_point:
            with contextlib.suppress(Exception):
                self._current_taxonomy = loader.load(instance.taxonomy_entry_point)

        if self._current_taxonomy is None:
            QMessageBox.critical(
                self,
                "Taxonomy Error",
                "Could not resolve the taxonomy for this instance. "
                "Please open the taxonomy first via File → Open Taxonomy.",
            )
            return

        # Enable taxonomy-level actions now that a taxonomy is loaded
        self._reload_action.setEnabled(True)
        self._new_instance_action.setEnabled(True)
        self._close_taxonomy_action.setEnabled(True)

        if orphaned:
            QMessageBox.information(
                self,
                "Orphaned Facts",
                f"{len(orphaned)} fact(s) in this instance have concepts not found in the "
                f"taxonomy and will be preserved verbatim on save.",
            )

        self._load_instance(instance)

    def _load_instance(self, instance) -> None:
        from bde_xbrl_editor.instance.editor import InstanceEditor  # noqa: PLC0415
        from bde_xbrl_editor.ui.widgets.xbrl_table_view import XbrlTableView  # noqa: PLC0415

        # Disconnect old editor signals
        if self._editor is not None:
            self._editor.changes_made.disconnect(self._on_changes_made)

        self._current_instance = instance
        self._editor = InstanceEditor(instance, parent=self)
        self._editor.changes_made.connect(self._on_changes_made)

        # Reuse existing table view if available, otherwise create one
        if self._table_view is None:
            self._table_view = XbrlTableView(parent=self)

        # Ensure the sidebar exists (may be absent when loading directly from welcome screen)
        if self._sidebar is None:
            self._sidebar = ActivitySidebar(self._current_taxonomy, parent=self)
            self._sidebar.table_selected.connect(self._on_table_selected)
            self._sidebar.width_changed.connect(self._on_sidebar_width_changed)

        # Switch the sidebar to instance mode (6th panel: entity, period, FI, filed tables)
        self._sidebar.set_instance(instance, self._current_taxonomy)

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

        # Auto-render the first filed table immediately
        self._sidebar.select_first_instance_table()

        # Show validation panel (cleared) so user sees it's ready
        self._ensure_validation_panel()
        dock = self._find_validation_dock()
        if dock:
            dock.setVisible(True)
        if self._validation_panel:
            self._validation_panel.clear()
        self._show_validation_panel_action.setEnabled(True)

    def _on_sidebar_width_changed(self, width: int) -> None:
        if self._browser_splitter is None:
            return

        def _apply() -> None:
            if self._browser_splitter is None:
                return
            total = sum(self._browser_splitter.sizes())
            if total <= 0:
                total = self._browser_splitter.width()
            main_width = max(total - width, 0)
            self._browser_splitter.setSizes([width, main_width])

        QTimer.singleShot(0, _apply)

    # ------------------------------------------------------------------
    # Table selection → XbrlTableView (T017)
    # ------------------------------------------------------------------

    def _on_table_selected(self, table) -> None:
        if self._table_view is None or self._current_taxonomy is None:
            return
        # Update the selected-table chip in the context bar
        if self._table_chip_label is not None and self._table_chip_sep is not None:
            label = getattr(table, "label", None) or ""
            table_id = getattr(table, "table_id", "")
            chip_text = f"⊡  {table_id}" + (f"  —  {label}" if label else "")
            self._table_chip_label.setText(chip_text)
            self._table_chip_label.setVisible(True)
            self._table_chip_sep.setVisible(True)
        self._table_view.set_table(
            table=table,
            taxonomy=self._current_taxonomy,
            instance=self._current_instance,
        )
        # Wire delegate (T025)
        if self._editor is not None and self._table_view._layout is not None:
            from bde_xbrl_editor.ui.widgets.cell_edit_delegate import (
                CellEditDelegate,  # noqa: PLC0415
            )

            delegate = CellEditDelegate(
                taxonomy=self._current_taxonomy,
                editor=self._editor,
                table_layout=self._table_view._layout,
                table_view_widget=self._table_view._body_view,
            )
            self._table_view._body_view.setItemDelegate(delegate)

    # ------------------------------------------------------------------
    # Dirty-state tracking (T033)
    # ------------------------------------------------------------------

    def _on_changes_made(self) -> None:
        self.setWindowModified(True)
        if self._table_view is not None:
            # Defer refresh so the editor widget is fully closed before the model is replaced.
            QTimer.singleShot(0, lambda: (
                self._table_view.refresh_instance(self._current_instance)
                if self._table_view is not None else None
            ))

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
        from bde_xbrl_editor.instance.models import InstanceSaveError  # noqa: PLC0415
        from bde_xbrl_editor.instance.serializer import InstanceSerializer  # noqa: PLC0415

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

    def _on_validation_done(self, report) -> None:
        self._cleanup_validation_thread()
        if self._validation_panel:
            self._validation_panel.show_report(report)
        status = "PASSED" if report.passed else f"FAILED ({report.error_count} error(s))"
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

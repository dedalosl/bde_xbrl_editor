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
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from bde_xbrl_editor.taxonomy import TaxonomyCache, TaxonomyStructure
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
        self._taxonomy_table_list: QListWidget | None = None
        self._context_bar: QFrame | None = None

        # Validation
        self._validation_thread: QThread | None = None
        self._validation_worker = None  # ValidationWorker | None
        self._validation_panel = None  # ValidationPanel | None

        self._setup_menu()
        self._setup_central()
        self._setup_statusbar()

    def _apply_stylesheet(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget {
                font-family: -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                font-size: 12px;
            }
            QMenuBar {
                background: #1E3A5F;
                color: #FFFFFF;
                padding: 2px 4px;
            }
            QMenuBar::item:selected {
                background: #2B5287;
            }
            QMenu {
                background: #FFFFFF;
                border: 1px solid #C8D4E5;
                color: #1E3A5F;
            }
            QMenu::item:selected {
                background: #1E3A5F;
                color: #FFFFFF;
            }
            QStatusBar {
                background: #F0F4FA;
                color: #1E3A5F;
                border-top: 1px solid #C8D4E5;
                font-size: 11px;
                padding: 2px 6px;
            }
            QScrollBar:vertical {
                width: 10px;
                background: #F0F4FA;
                border: none;
            }
            QScrollBar::handle:vertical {
                background: #B0C4DE;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #2B5287;
            }
            QScrollBar:horizontal {
                height: 10px;
                background: #F0F4FA;
                border: none;
            }
            QScrollBar::handle:horizontal {
                background: #B0C4DE;
                border-radius: 4px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #2B5287;
            }
            QSplitter::handle {
                background: #C8D4E5;
            }
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
        self._open_instance_action.setEnabled(False)
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

    def _setup_browser_layout(self) -> None:
        """Create the main split layout: context bar + table-list sidebar + XbrlTableView."""
        from bde_xbrl_editor.ui.widgets.xbrl_table_view import XbrlTableView  # noqa: PLC0415

        sidebar = self._build_taxonomy_sidebar()

        if self._table_view is None:
            self._table_view = XbrlTableView(parent=self)

        splitter = QSplitter(self)
        splitter.addWidget(sidebar)
        splitter.addWidget(self._table_view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

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

    def _build_taxonomy_sidebar(self) -> QWidget:
        """Build the sidebar: taxonomy header + table list + taxonomy info panel."""
        assert self._current_taxonomy is not None
        meta = self._current_taxonomy.metadata

        sidebar = QFrame(self)
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet("QFrame { background: #F5F7FA; }")

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Taxonomy name header
        header = QLabel(f"{meta.name}  v{meta.version}")
        header.setStyleSheet(
            "background: #1E3A5F; color: #FFFFFF; font-weight: bold;"
            " font-size: 13px; padding: 8px 12px;"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        # "TABLES" section label
        section = QLabel(f"TABLES  ({len(self._current_taxonomy.tables)})")
        section.setStyleSheet(
            "background: #2B5287; color: #FFFFFF; font-weight: bold;"
            " font-size: 11px; padding: 4px 8px;"
        )
        layout.addWidget(section)

        # Table list — stretch to fill available space
        self._taxonomy_table_list = QListWidget()
        self._taxonomy_table_list.setStyleSheet("""
            QListWidget {
                border: none;
                background: #FFFFFF;
                font-size: 12px;
                color: #1E3A5F;
                outline: none;
            }
            QListWidget::item {
                padding: 5px 8px;
                border-bottom: 1px solid #E8EDF5;
            }
            QListWidget::item:selected {
                background: #1E3A5F;
                color: #FFFFFF;
            }
            QListWidget::item:hover:!selected {
                background: #DCE8F5;
            }
        """)
        for table in self._current_taxonomy.tables:
            item = QListWidgetItem(f"{table.table_id}\n{table.label}")
            item.setData(0x0100, table)
            self._taxonomy_table_list.addItem(item)
        self._taxonomy_table_list.itemClicked.connect(self._on_taxonomy_table_list_clicked)
        layout.addWidget(self._taxonomy_table_list, stretch=1)

        # ── Taxonomy info panel (collapsed under the list) ──────────────
        info_section = QLabel("TAXONOMY INFO")
        info_section.setStyleSheet(
            "background: #2B5287; color: #FFFFFF; font-weight: bold;"
            " font-size: 11px; padding: 4px 8px;"
        )
        layout.addWidget(info_section)

        info_style = "color: #1E3A5F; font-size: 11px; padding: 2px 10px;"
        key_style = "color: #5A7FA8; font-size: 10px; padding: 1px 10px; font-weight: bold;"

        def _row(key: str, value: str) -> None:
            layout.addWidget(QLabel(key, styleSheet=key_style))
            lbl = QLabel(value)
            lbl.setStyleSheet(info_style)
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(lbl)

        _row("NAME", meta.name)
        _row("VERSION", meta.version)
        _row("PUBLISHER", meta.publisher)
        _row("ENTRY POINT", str(meta.entry_point_path.name))
        _row("LOADED AT", meta.loaded_at.strftime("%Y-%m-%d %H:%M"))
        _row("LANGUAGES", ", ".join(meta.declared_languages) or "—")
        _row("CONCEPTS", str(len(self._current_taxonomy.concepts)))
        _row("TABLES", str(len(self._current_taxonomy.tables)))

        # Spacer at the very bottom
        layout.addSpacing(6)

        return sidebar

    # ------------------------------------------------------------------
    # Context bar
    # ------------------------------------------------------------------

    def _build_context_bar(self, instance=None) -> QFrame:
        """Return a slim bar showing taxonomy + instance breadcrumbs with × close buttons."""
        bar = QFrame()
        bar.setFixedHeight(36)
        bar.setStyleSheet(
            "QFrame { background: #2B5287; border-bottom: 1px solid #1E3A5F; }"
        )

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(6)

        chip_style = (
            "QLabel { color: #FFFFFF; font-size: 11px; font-weight: 600;"
            " background: rgba(255,255,255,0.12); border-radius: 3px; padding: 2px 7px; }"
        )
        close_style = (
            "QPushButton { color: #A8C8EE; background: transparent; border: none;"
            " font-size: 14px; padding: 0 3px; }"
            "QPushButton:hover { color: #FFFFFF; background: rgba(255,255,255,0.2);"
            " border-radius: 3px; }"
        )
        sep_style = "QLabel { color: #7BA4C8; font-size: 14px; background: transparent; }"

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

        layout.addStretch()

        # ── Action buttons on the right ────────────────────────────────
        btn_style = (
            "QPushButton { color: #FFFFFF; background: rgba(255,255,255,0.15);"
            " border: 1px solid rgba(255,255,255,0.3); border-radius: 3px;"
            " font-size: 11px; padding: 3px 10px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.25); }"
            "QPushButton:disabled { color: #7BA4C8; background: transparent;"
            " border-color: rgba(255,255,255,0.1); }"
        )

        if instance is None and self._current_taxonomy is not None:
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
        self._taxonomy_table_list = None
        self._context_bar = None

        self._reload_action.setEnabled(False)
        self._new_instance_action.setEnabled(False)
        self._open_instance_action.setEnabled(False)
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

    def _on_taxonomy_table_list_clicked(self, item: QListWidgetItem) -> None:
        table = item.data(0x0100)
        if table is not None:
            self._on_table_selected(table)

    def _select_first_taxonomy_table(self) -> None:
        if self._taxonomy_table_list is not None and self._taxonomy_table_list.count() > 0:
            first = self._taxonomy_table_list.item(0)
            self._taxonomy_table_list.setCurrentItem(first)
            self._on_taxonomy_table_list_clicked(first)

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
            if instance and instance.source_path:
                self._status.showMessage(
                    f"Instance created: {instance.source_path}"
                )

    # ------------------------------------------------------------------
    # File → Open Instance (T015)
    # ------------------------------------------------------------------

    def _on_open_instance(self) -> None:
        if self._current_taxonomy is None:
            return
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
        from bde_xbrl_editor.ui.widgets.instance_info_panel import (
            InstanceInfoPanel,  # noqa: PLC0415
        )
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

        info_panel = InstanceInfoPanel(
            instance=instance,
            taxonomy=self._current_taxonomy,
            parent=self,
        )
        info_panel.table_selected.connect(self._on_table_selected)

        splitter = QSplitter(self)
        splitter.addWidget(info_panel)
        splitter.addWidget(self._table_view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

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
        info_panel.select_first_table()

    # ------------------------------------------------------------------
    # Table selection → XbrlTableView (T017)
    # ------------------------------------------------------------------

    def _on_table_selected(self, table) -> None:
        if self._table_view is None or self._current_taxonomy is None:
            return
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

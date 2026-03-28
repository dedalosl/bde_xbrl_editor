"""QMainWindow shell — Features 001 + 002 + 004 UI."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QStatusBar,
)

from bde_xbrl_editor.taxonomy import TaxonomyCache, TaxonomyStructure
from bde_xbrl_editor.ui.widgets.loader_settings_dialog import load_saved_settings
from bde_xbrl_editor.ui.widgets.taxonomy_loader_widget import TaxonomyLoaderWidget


class MainWindow(QMainWindow):
    """Application main window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BDE XBRL Editor[*]")
        self.resize(800, 600)

        self._cache = TaxonomyCache()
        self._settings = load_saved_settings()
        self._current_taxonomy: TaxonomyStructure | None = None
        self._current_instance = None  # XbrlInstance | None
        self._editor = None  # InstanceEditor | None
        self._table_view = None  # XbrlTableView | None

        self._setup_menu()
        self._setup_central()
        self._setup_statusbar()

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
        quit_action = file_menu.addAction("&Quit")
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)

    def _setup_central(self) -> None:
        self._loader_widget = TaxonomyLoaderWidget(
            cache=self._cache,
            settings=self._settings,
            parent=self,
        )
        self._loader_widget.taxonomy_loaded.connect(self._on_taxonomy_loaded)
        self.setCentralWidget(self._loader_widget)

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
        self.setCentralWidget(self._loader_widget)

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

        from bde_xbrl_editor.ui.widgets.taxonomy_info_panel import TaxonomyInfoPanel

        panel = TaxonomyInfoPanel(structure, parent=self)
        self.setCentralWidget(panel)

    def _on_reload(self) -> None:
        if self._current_taxonomy:
            entry_point = self._current_taxonomy.metadata.entry_point_path
            self._loader_widget._path_edit.setText(str(entry_point))
            self.setCentralWidget(self._loader_widget)
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
        from bde_xbrl_editor.instance.editor import InstanceEditor
        from bde_xbrl_editor.ui.widgets.instance_info_panel import InstanceInfoPanel
        from bde_xbrl_editor.ui.widgets.xbrl_table_view import XbrlTableView

        # Disconnect old editor signals
        if self._editor is not None:
            self._editor.changes_made.disconnect(self._on_changes_made)

        self._current_instance = instance
        self._editor = InstanceEditor(instance, parent=self)
        self._editor.changes_made.connect(self._on_changes_made)

        self._table_view = XbrlTableView(parent=self)

        info_panel = InstanceInfoPanel(
            instance=instance,
            taxonomy=self._current_taxonomy,
            parent=self,
        )
        info_panel.table_selected.connect(self._on_table_selected)

        from PySide6.QtWidgets import QSplitter  # noqa: PLC0415

        splitter = QSplitter(self)
        splitter.addWidget(info_panel)
        splitter.addWidget(self._table_view)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self._save_action.setEnabled(True)
        self._save_as_action.setEnabled(True)

        fname = Path(instance.source_path).name if instance.source_path else "instance"
        self.setWindowTitle(f"BDE XBRL Editor — {fname}[*]")
        self.setWindowModified(False)
        self._status.showMessage(
            f"Opened: {instance.source_path} — "
            f"{len(instance.facts)} facts, {len(instance.contexts)} contexts"
        )

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

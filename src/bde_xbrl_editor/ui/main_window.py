"""QMainWindow shell — Features 001 + 002 UI."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QMainWindow,
    QStatusBar,
)

from bde_xbrl_editor.taxonomy import TaxonomyCache, TaxonomyStructure
from bde_xbrl_editor.ui.widgets.loader_settings_dialog import load_saved_settings
from bde_xbrl_editor.ui.widgets.taxonomy_loader_widget import TaxonomyLoaderWidget


class MainWindow(QMainWindow):
    """Application main window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("BDE XBRL Editor")
        self.resize(800, 600)

        self._cache = TaxonomyCache()
        self._settings = load_saved_settings()
        self._current_taxonomy: TaxonomyStructure | None = None

        self._setup_menu()
        self._setup_central()
        self._setup_statusbar()

    def _setup_menu(self) -> None:
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        open_action = file_menu.addAction("&Open Taxonomy…")
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._show_loader)

        self._reload_action = file_menu.addAction("&Reload Taxonomy")
        self._reload_action.setShortcut("Ctrl+R")
        self._reload_action.setEnabled(False)
        self._reload_action.triggered.connect(self._on_reload)

        file_menu.addSeparator()

        self._new_instance_action = file_menu.addAction("&New Instance…")
        self._new_instance_action.setShortcut("Ctrl+N")
        self._new_instance_action.setEnabled(False)
        self._new_instance_action.triggered.connect(self._on_new_instance)

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

    def _show_loader(self) -> None:
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

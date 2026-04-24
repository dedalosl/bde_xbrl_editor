"""InstanceCreationWizard — QWizard subclass for the 4-step instance creation flow."""

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QWizard

from bde_xbrl_editor.instance.factory import InstanceFactory
from bde_xbrl_editor.instance.models import XbrlInstance
from bde_xbrl_editor.taxonomy.models import TaxonomyStructure
from bde_xbrl_editor.ui.widgets.instance_creation_wizard.page_dimensional import (
    DimensionalPage,
)
from bde_xbrl_editor.ui.widgets.instance_creation_wizard.page_entity_period import (
    EntityPeriodPage,
)
from bde_xbrl_editor.ui.widgets.instance_creation_wizard.page_save import SavePage
from bde_xbrl_editor.ui.widgets.instance_creation_wizard.page_table_selection import (
    TableSelectionPage,
)

_PAGE_ENTITY = 0
_PAGE_TABLES = 1
_PAGE_DIMS = 2
_PAGE_SAVE = 3


class InstanceCreationWizard(QWizard):
    """4-step wizard for creating a new XBRL instance.

    Usage::

        wizard = InstanceCreationWizard(taxonomy=app.current_taxonomy, parent=window)
        if wizard.exec() == QDialog.Accepted:
            instance = wizard.created_instance
    """

    def __init__(
        self, taxonomy: TaxonomyStructure, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._taxonomy = taxonomy
        self._created_instance: XbrlInstance | None = None

        self.setWindowTitle("New XBRL Instance")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        self._page_entity = EntityPeriodPage(taxonomy, self)
        self._page_tables = TableSelectionPage(taxonomy, self)
        self._page_dims = DimensionalPage(taxonomy, self)
        self._page_save = SavePage(self)

        self.setPage(_PAGE_ENTITY, self._page_entity)
        self.setPage(_PAGE_TABLES, self._page_tables)
        self.setPage(_PAGE_DIMS, self._page_dims)
        self.setPage(_PAGE_SAVE, self._page_save)

        # Assemble the instance just before the save page becomes active
        self.currentIdChanged.connect(self._on_page_changed)

    def _on_page_changed(self, page_id: int) -> None:
        if page_id == _PAGE_SAVE:
            self._assemble_instance()

    def _assemble_instance(self) -> None:
        """Call InstanceFactory with data collected from earlier pages."""
        try:
            entity = self._page_entity.get_entity()
            period = self._page_entity.get_period()
            agrupacion_member = self._page_entity.get_agrupacion_member()
            table_ids = self._page_tables.get_selected_table_ids()
            dim_configs = self._page_dims.get_dimensional_configs()

            factory = InstanceFactory(self._taxonomy)
            instance = factory.create(
                entity,
                period,
                table_ids,
                dim_configs,
                agrupacion_member=agrupacion_member,
            )
            self.setProperty("assembled_instance", instance)
            self._created_instance = instance
        except Exception:  # noqa: BLE001
            self._created_instance = None

    @property
    def created_instance(self) -> XbrlInstance | None:
        """The newly created and saved instance, or None if wizard was cancelled."""
        return self._created_instance

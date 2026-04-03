"""InstanceInfoPanel — sidebar panel showing instance metadata and table list."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.models import XbrlInstance
    from bde_xbrl_editor.taxonomy.models import TableDefinitionPWD, TaxonomyStructure


class InstanceInfoPanel(QFrame):
    """Sidebar panel that displays instance metadata and allows table selection.

    Emits ``table_selected(TableDefinitionPWD)`` when the user clicks a table entry.
    """

    table_selected: Signal = Signal(object)  # TableDefinitionPWD

    def __init__(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._instance = instance
        self._taxonomy = taxonomy
        self._table_map: dict[str, TableDefinitionPWD] = {}
        self._setup_ui()
        self._populate(instance, taxonomy)

    # ------------------------------------------------------------------
    # Internal setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        layout.addWidget(QLabel("<b>Instance</b>"))

        self._entity_label = QLabel()
        self._entity_label.setWordWrap(True)
        layout.addWidget(self._entity_label)

        self._period_label = QLabel()
        layout.addWidget(self._period_label)

        layout.addWidget(QLabel("<b>Filing Indicators</b>"))

        self._fi_label = QLabel()
        self._fi_label.setWordWrap(True)
        layout.addWidget(self._fi_label)

        layout.addWidget(QLabel("<b>Tables</b>"))

        self._table_list = QListWidget()
        self._table_list.itemClicked.connect(self._on_table_clicked)
        layout.addWidget(self._table_list)

    def _populate(self, instance: XbrlInstance, taxonomy: TaxonomyStructure) -> None:
        # Entity
        entity = instance.entity
        self._entity_label.setText(f"{entity.identifier}\n({entity.scheme})")

        # Period
        period = instance.period
        if period.period_type == "instant":
            period_text = f"Instant: {period.instant_date}"
        else:
            period_text = f"Duration: {period.start_date} – {period.end_date}"
        self._period_label.setText(period_text)

        # Filing indicators
        fi_texts = []
        for fi in instance.filing_indicators:
            status = "filed" if fi.filed else "not filed"
            fi_texts.append(f"• {fi.template_id} [{status}]")
        self._fi_label.setText("\n".join(fi_texts) if fi_texts else "None")

        # Tables — show only filed tables that exist in the taxonomy
        filed_ids = {fi.template_id for fi in instance.filing_indicators if fi.filed}
        for table in taxonomy.tables:
            if table.table_id in filed_ids or not filed_ids:
                item = QListWidgetItem(f"{table.table_id} — {table.label}")
                item.setData(0x0100, table.table_id)  # Qt.UserRole = 0x0100
                self._table_list.addItem(item)
                self._table_map[table.table_id] = table

    def _on_table_clicked(self, item: QListWidgetItem) -> None:
        table_id = item.data(0x0100)
        table = self._table_map.get(table_id)
        if table is not None:
            self.table_selected.emit(table)

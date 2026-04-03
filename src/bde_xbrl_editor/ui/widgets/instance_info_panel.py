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
    QWidget,
)

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.models import XbrlInstance
    from bde_xbrl_editor.taxonomy.models import TableDefinitionPWD, TaxonomyStructure

_SIDEBAR_BG = "#F5F7FA"
_SECTION_HEADER_STYLE = (
    "background: #2B5287; color: #FFFFFF; font-weight: bold; font-size: 11px;"
    " padding: 4px 8px; margin-top: 4px;"
)
_VALUE_STYLE = (
    "color: #1E3A5F; font-size: 12px; padding: 2px 8px;"
)
_TABLE_LIST_STYLE = """
QListWidget {
    border: 1px solid #C8D4E5;
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
"""


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(_SECTION_HEADER_STYLE)
    return lbl


class InstanceInfoPanel(QFrame):
    """Sidebar panel that displays instance metadata and allows table selection.

    Emits ``table_selected(TableDefinitionPWD)`` when the user clicks a table entry.
    """

    table_selected: Signal = Signal(object)  # TableDefinitionPWD

    def __init__(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._instance = instance
        self._taxonomy = taxonomy
        self._table_map: dict[str, TableDefinitionPWD] = {}
        self.setStyleSheet(f"InstanceInfoPanel {{ background: {_SIDEBAR_BG}; }}")
        self.setFixedWidth(240)
        self._setup_ui()
        self._populate(instance, taxonomy)

    # ------------------------------------------------------------------
    # Internal setup
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(_section_label("INSTANCE"))

        self._entity_label = QLabel()
        self._entity_label.setWordWrap(True)
        self._entity_label.setStyleSheet(_VALUE_STYLE)
        layout.addWidget(self._entity_label)

        self._period_label = QLabel()
        self._period_label.setStyleSheet(_VALUE_STYLE)
        layout.addWidget(self._period_label)

        layout.addWidget(_section_label("FILING INDICATORS"))

        self._fi_label = QLabel()
        self._fi_label.setWordWrap(True)
        self._fi_label.setStyleSheet(_VALUE_STYLE)
        layout.addWidget(self._fi_label)

        layout.addWidget(_section_label("TABLES"))

        self._table_list = QListWidget()
        self._table_list.setStyleSheet(_TABLE_LIST_STYLE)
        self._table_list.itemClicked.connect(self._on_table_clicked)
        layout.addWidget(self._table_list)

    def _populate(self, instance: XbrlInstance, taxonomy: TaxonomyStructure) -> None:
        # Entity
        entity = instance.entity
        self._entity_label.setText(f"{entity.identifier}\n{entity.scheme}")

        # Period
        period = instance.period
        if period.period_type == "instant":
            period_text = f"Instant: {period.instant_date}"
        else:
            period_text = f"{period.start_date} – {period.end_date}"
        self._period_label.setText(period_text)

        # Filing indicators
        fi_texts = []
        for fi in instance.filing_indicators:
            status = "✓" if fi.filed else "✗"
            fi_texts.append(f"{status} {fi.template_id}")
        self._fi_label.setText("\n".join(fi_texts) if fi_texts else "None")

        # Tables — show only filed tables that exist in the taxonomy
        filed_ids = {fi.template_id for fi in instance.filing_indicators if fi.filed}
        for table in taxonomy.tables:
            if table.table_id in filed_ids or not filed_ids:
                item = QListWidgetItem(f"{table.table_id}\n{table.label}")
                item.setData(0x0100, table.table_id)  # Qt.UserRole = 0x0100
                self._table_list.addItem(item)
                self._table_map[table.table_id] = table

    def select_first_table(self) -> None:
        """Select and emit the first table in the list, if any."""
        if self._table_list.count() > 0:
            first = self._table_list.item(0)
            self._table_list.setCurrentItem(first)
            self._on_table_clicked(first)

    def _on_table_clicked(self, item: QListWidgetItem) -> None:
        table_id = item.data(0x0100)
        table = self._table_map.get(table_id)
        if table is not None:
            self.table_selected.emit(table)

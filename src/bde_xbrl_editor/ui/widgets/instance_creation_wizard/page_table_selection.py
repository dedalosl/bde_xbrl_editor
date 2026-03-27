"""Wizard page 2 — Table selection from taxonomy."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWizardPage,
)

from bde_xbrl_editor.taxonomy.models import TaxonomyStructure


class TableSelectionPage(QWizardPage):
    """Wizard page 2: select which tables to include in the instance."""

    def __init__(self, taxonomy: TaxonomyStructure, parent=None) -> None:
        super().__init__(parent)
        self._taxonomy = taxonomy
        self.setTitle("Table Selection")
        self.setSubTitle("Select the report tables to include in this instance.")

        layout = QVBoxLayout(self)

        # Toolbar
        btn_layout = QHBoxLayout()
        self._select_all_btn = QPushButton("Select All")
        self._select_all_btn.clicked.connect(self._select_all)
        self._deselect_all_btn = QPushButton("Deselect All")
        self._deselect_all_btn.clicked.connect(self._deselect_all)
        btn_layout.addWidget(self._select_all_btn)
        btn_layout.addWidget(self._deselect_all_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Table list
        self._list_widget = QListWidget()
        self._list_widget.itemChanged.connect(self._on_item_changed)
        for table in taxonomy.tables:
            label = table.label or table.table_id
            item = QListWidgetItem(f"{table.table_id} — {label}")
            item.setData(Qt.ItemDataRole.UserRole, table.table_id)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._list_widget.addItem(item)
        layout.addWidget(self._list_widget)

        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red;")
        layout.addWidget(self._error_label)

    def _select_all(self) -> None:
        for i in range(self._list_widget.count()):
            self._list_widget.item(i).setCheckState(Qt.CheckState.Checked)

    def _deselect_all(self) -> None:
        for i in range(self._list_widget.count()):
            self._list_widget.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _on_item_changed(self, _item: QListWidgetItem) -> None:
        self._error_label.setText("")

    def validatePage(self) -> bool:
        selected = self.get_selected_table_ids()
        if not selected:
            self._error_label.setText("Please select at least one table.")
            return False
        self._error_label.setText("")
        # Store in wizard field for downstream pages
        self.wizard().setProperty("selected_table_ids", selected)
        return True

    def get_selected_table_ids(self) -> list[str]:
        result = []
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                result.append(item.data(Qt.ItemDataRole.UserRole))
        return result

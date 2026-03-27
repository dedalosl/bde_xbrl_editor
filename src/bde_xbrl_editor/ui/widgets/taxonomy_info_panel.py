"""TaxonomyInfoPanel — displays loaded taxonomy metadata and table list."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bde_xbrl_editor.taxonomy import TaxonomyStructure


class TaxonomyInfoPanel(QWidget):
    """Widget displaying taxonomy metadata and the list of available tables.

    Shown after a successful taxonomy load in place of the loader widget.
    """

    def __init__(self, taxonomy: TaxonomyStructure, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._taxonomy = taxonomy
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        # --- Metadata group ---
        meta_group = QGroupBox("Taxonomy Information")
        meta_form = QFormLayout(meta_group)
        meta = self._taxonomy.metadata

        meta_form.addRow("Name:", QLabel(meta.name))
        meta_form.addRow("Version:", QLabel(meta.version))
        meta_form.addRow("Publisher:", QLabel(meta.publisher))
        meta_form.addRow("Entry Point:", QLabel(str(meta.entry_point_path)))
        meta_form.addRow("Loaded At:", QLabel(meta.loaded_at.strftime("%Y-%m-%d %H:%M:%S")))
        meta_form.addRow("Languages:", QLabel(", ".join(meta.declared_languages) or "—"))
        meta_form.addRow("Concepts:", QLabel(str(len(self._taxonomy.concepts))))
        meta_form.addRow("Tables:", QLabel(str(len(self._taxonomy.tables))))

        layout.addWidget(meta_group)

        # --- Table list ---
        tables_group = QGroupBox(f"Available Tables ({len(self._taxonomy.tables)})")
        tables_layout = QVBoxLayout(tables_group)

        self._table_list = QListWidget()
        for table in self._taxonomy.tables:
            item = QListWidgetItem(f"{table.table_id}  —  {table.label}")
            item.setData(256, table)  # Qt.UserRole = 256
            self._table_list.addItem(item)

        tables_layout.addWidget(self._table_list)
        layout.addWidget(tables_group)

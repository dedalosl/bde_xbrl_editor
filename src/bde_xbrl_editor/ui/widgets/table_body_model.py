"""TableBodyModel — QAbstractTableModel for the table body."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from bde_xbrl_editor.table_renderer.models import ComputedTableLayout
from bde_xbrl_editor.ui import theme

_COLOR_HAS_FACT = QColor(theme.CELL_BG)
_COLOR_DUPLICATE = QColor(theme.CELL_BG_DUPLICATE)
_COLOR_NOT_APPLICABLE = QColor(theme.CELL_BG_MUTED)
_COLOR_EXCLUDED = QColor(theme.CELL_BG_DISABLED)  # dark grey for dimensionally-excluded cells

# Custom role for the cell code (row_fin_code + col_fin_code)
CELL_CODE_ROLE = Qt.ItemDataRole.UserRole + 2
OPEN_KEY_ROLE = Qt.ItemDataRole.UserRole + 3
FACT_OPTIONS_ROLE = Qt.ItemDataRole.UserRole + 4

# XBRL numeric type local names (used for right-alignment)
_NUMERIC_TYPE_LOCALS = frozenset({
    "monetaryItemType",
    "decimalItemType",
    "floatItemType",
    "doubleItemType",
    "integerItemType",
    "nonNegativeIntegerItemType",
    "positiveIntegerItemType",
    "nonPositiveIntegerItemType",
    "negativeIntegerItemType",
    "longItemType",
    "intItemType",
    "shortItemType",
    "byteItemType",
    "unsignedLongItemType",
    "unsignedIntItemType",
    "unsignedShortItemType",
    "unsignedByteItemType",
    "pureItemType",
    "sharesItemType",
    "percentItemType",
})


class TableBodyModel(QAbstractTableModel):
    """Qt model backing the body QTableView."""

    def __init__(self, layout: ComputedTableLayout, parent: Any = None) -> None:
        super().__init__(parent)
        self._layout = layout
        self._formatter: Any = None  # set by XbrlTableView when taxonomy is available
        self._taxonomy: Any = None
        self._open_key_handler: Any = None

    def set_formatter(self, formatter: Any, taxonomy: Any) -> None:
        """Inject FactFormatter for DisplayRole formatting."""
        self._formatter = formatter
        self._taxonomy = taxonomy

    def set_open_key_handler(self, handler: Any) -> None:
        self._open_key_handler = handler

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        if parent.isValid():
            return 0
        return self._layout.row_header.leaf_count

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: B008
        if parent.isValid():
            return 0
        return self._layout.column_header.leaf_count

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if row >= len(self._layout.body) or col >= len(self._layout.body[row]):
            return None
        cell = self._layout.body[row][col]

        if role == Qt.ItemDataRole.DisplayRole:
            if cell.cell_kind == "open-key":
                if cell.open_key_text:
                    return cell.open_key_text
                if cell.open_key_member is None:
                    return ""
                if self._taxonomy is not None:
                    resolved = self._taxonomy.labels.resolve(cell.open_key_member)
                    if resolved != str(cell.open_key_member):
                        return resolved
                return getattr(cell.open_key_member, "local_name", str(cell.open_key_member))
            if cell.cell_kind == "placeholder":
                return ""
            if cell.fact_value is None:
                return ""
            if self._formatter is not None and cell.coordinate.concept is not None:
                return self._formatter.format(cell.fact_value, cell.coordinate.concept, cell.fact_decimals)
            return cell.fact_value

        if role == Qt.ItemDataRole.UserRole:
            if cell.cell_kind == "open-key":
                if cell.open_key_text:
                    return cell.open_key_text
                if cell.open_key_member is None:
                    return ""
                if self._taxonomy is not None:
                    resolved = self._taxonomy.labels.resolve(cell.open_key_member)
                    if resolved != str(cell.open_key_member):
                        return resolved
                return getattr(cell.open_key_member, "local_name", str(cell.open_key_member))
            return cell.fact_value

        if role == CELL_CODE_ROLE:
            return cell.cell_code

        if role == OPEN_KEY_ROLE and cell.cell_kind == "open-key":
            return {
                "signature": cell.open_key_signature,
                "dimension": cell.open_key_dimension,
                "member": cell.open_key_member,
                "text": cell.open_key_text,
                "options": cell.open_key_options,
            }

        if role == FACT_OPTIONS_ROLE and cell.fact_options:
            return cell.fact_options

        if role == Qt.ItemDataRole.BackgroundRole:
            if cell.cell_kind == "open-key":
                return _COLOR_HAS_FACT
            if not cell.is_applicable:
                return _COLOR_NOT_APPLICABLE
            if cell.is_excluded:
                return _COLOR_EXCLUDED
            if cell.is_duplicate:
                return _COLOR_DUPLICATE
            return _COLOR_HAS_FACT

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if cell.cell_kind == "open-key":
                return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            if self._taxonomy is not None and cell.coordinate.concept is not None:
                concept_def = self._taxonomy.concepts.get(cell.coordinate.concept)
                if concept_def is not None:
                    type_qname = concept_def.data_type
                    local = str(type_qname).split("}")[-1].split(":")[-1] if type_qname else ""
                    if local in _NUMERIC_TYPE_LOCALS:
                        return int(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        if role == Qt.ItemDataRole.ToolTipRole:
            if cell.cell_kind == "open-key":
                parts = []
                if cell.open_key_dimension is not None:
                    dim_label = (
                        self._taxonomy.labels.resolve(cell.open_key_dimension)
                        if self._taxonomy is not None
                        else str(cell.open_key_dimension)
                    )
                    parts.append(f"Open row key: {dim_label}")
                if cell.open_key_member is not None:
                    mem_label = (
                        self._taxonomy.labels.resolve(cell.open_key_member)
                        if self._taxonomy is not None
                        else str(cell.open_key_member)
                    )
                    parts.append(f"Selected member: {mem_label}")
                elif cell.open_key_text:
                    parts.append(f"Selected value: {cell.open_key_text}")
                return "\n".join(parts) if parts else None
            coord = cell.coordinate
            parts = []
            if coord.concept is not None:
                label = ""
                if self._taxonomy is not None:
                    label = self._taxonomy.labels.resolve(coord.concept)
                data_type = ""
                if self._taxonomy is not None:
                    concept_def = self._taxonomy.concepts.get(coord.concept)
                    if concept_def is not None:
                        data_type = str(concept_def.type_qname) if hasattr(concept_def, "type_qname") else ""
                parts.append(f"Concept: {label or str(coord.concept)}")
                if data_type:
                    parts.append(f"Type: {data_type}")
                parts.append(f"QName: {coord.concept}")
            if coord.explicit_dimensions:
                for dim, mem in coord.explicit_dimensions.items():
                    parts.append(f"  {dim} = {mem}")
            if coord.period_override is not None:
                parts.append(f"Period: {coord.period_override}")
            return "\n".join(parts) if parts else None

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        row, col = index.row(), index.column()
        if row < len(self._layout.body) and col < len(self._layout.body[row]):
            cell = self._layout.body[row][col]
            if cell.cell_kind == "open-key" or cell.is_applicable and not cell.is_excluded:
                base |= Qt.ItemFlag.ItemIsEditable
        return base

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.ItemDataRole.EditRole) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        row = index.row()
        col = index.column()
        if row >= len(self._layout.body) or col >= len(self._layout.body[row]):
            return False
        cell = self._layout.body[row][col]
        if cell.cell_kind != "open-key" or self._open_key_handler is None:
            return False
        if not isinstance(value, str):
            return False
        changed = bool(self._open_key_handler(row, col, value))
        if changed:
            self.dataChanged.emit(index, index, [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.UserRole])
        return changed

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            return str(section + 1)
        return None

"""TableBodyModel — QAbstractTableModel for the table body."""

from __future__ import annotations

import contextlib
from html import escape
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

_TOOLTIP_LANG_PREF = ["es", "en"]
_MAX_TOOLTIP_OPTIONS = 24

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


def _qname_to_clark(qname: Any) -> str:
    namespace = getattr(qname, "namespace", "")
    local_name = getattr(qname, "local_name", "")
    if namespace or local_name:
        return f"{{{namespace}}}{local_name}"
    return str(qname)


def _build_prefix_to_namespace(taxonomy: Any) -> dict[str, str]:
    out: dict[str, str] = {}
    for concept in getattr(taxonomy, "concepts", {}).values():
        qname = getattr(concept, "qname", None)
        prefix = getattr(qname, "prefix", None)
        namespace = getattr(qname, "namespace", None)
        if prefix and namespace and prefix not in out:
            out[prefix] = namespace
    return out


def _parse_option_qname(raw_value: str, taxonomy: Any) -> Any | None:
    """Best-effort parser for enumeration option values used in taxonomy metadata."""
    from bde_xbrl_editor.taxonomy.models import QName  # noqa: PLC0415

    value = raw_value.strip()
    if not value:
        return None
    if value.startswith("{") and "}" in value:
        with contextlib.suppress(Exception):
            return QName.from_clark(value)
        return None
    if value.startswith(("http://", "https://")) and "#" in value:
        namespace, _, local_name = value.partition("#")
        if namespace and local_name:
            return QName(namespace=namespace, local_name=local_name)
    if ":" in value and not value.startswith(("http://", "https://")):
        prefix, _, local_name = value.partition(":")
        namespace = _build_prefix_to_namespace(taxonomy).get(prefix)
        if namespace:
            return QName(namespace=namespace, local_name=local_name, prefix=prefix)
    return None


def _display_raw_option(raw_value: str) -> str:
    if raw_value.startswith(("http://", "https://")) and "#" in raw_value:
        return raw_value.rsplit("#", 1)[-1]
    if raw_value.startswith("{") and "}" in raw_value:
        return raw_value.split("}", 1)[1]
    if ":" in raw_value:
        return raw_value.split(":", 1)[1]
    return raw_value


def _resolve_label(taxonomy: Any, qname: Any) -> str:
    if taxonomy is not None:
        with contextlib.suppress(Exception):
            resolved = taxonomy.labels.resolve(qname, language_preference=_TOOLTIP_LANG_PREF)
            if resolved and resolved != str(qname):
                return str(resolved)
    return getattr(qname, "local_name", None) or str(qname)


def _html_row(label: str, value: str) -> str:
    return (
        "<tr>"
        f"<td style='color:{theme.TEXT_MUTED}; padding:2px 12px 2px 0; white-space:nowrap;'>"
        f"{escape(label)}</td>"
        f"<td style='color:{theme.TEXT_MAIN}; padding:2px 0;'>{value}</td>"
        "</tr>"
    )


def _html_section(title: str, rows: list[str]) -> str:
    if not rows:
        return ""
    return (
        f"<div style='font-size:12px; font-weight:700; color:{theme.TEXT_MAIN}; "
        "margin:8px 0 3px;'>"
        f"{escape(title)}</div>"
        "<table cellspacing='0' cellpadding='0' style='border-collapse:collapse;'>"
        f"{''.join(rows)}"
        "</table>"
    )


def _html_dimension_item(dimension_label: str, member_html: str, technical_detail: str) -> str:
    return (
        f"<div style='border-top:1px solid {theme.BORDER}; padding:7px 0 8px;'>"
        f"<div style='color:{theme.TEXT_MUTED}; font-weight:600; margin-bottom:3px;'>"
        f"{escape(dimension_label)}</div>"
        f"<div style='color:{theme.TEXT_MAIN}; margin-bottom:2px;'>{member_html}</div>"
        f"<div style='color:{theme.TEXT_SUBTLE}; font-size:11px;'>{escape(technical_detail)}</div>"
        "</div>"
    )


def _html_block_section(title: str, blocks: list[str]) -> str:
    if not blocks:
        return ""
    return (
        f"<div style='font-size:12px; font-weight:700; color:{theme.TEXT_MAIN}; "
        "margin:8px 0 3px;'>"
        f"{escape(title)}</div>"
        f"{''.join(blocks)}"
    )


def _html_open_dimension_item(taxonomy: Any, item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    dim = item.get("dimension")
    if dim is None:
        return ""
    dim_label = _resolve_label(taxonomy, dim)
    options = tuple(item.get("options") or ())
    if item.get("typed"):
        return _html_dimension_item(
            dim_label,
            f"<span style='color:{theme.TEXT_MUTED};'>Typed value entered by the user</span>",
            _qname_to_clark(dim),
        )
    if not options:
        return _html_dimension_item(
            dim_label,
            f"<span style='color:{theme.TEXT_MUTED};'>No available values</span>",
            _qname_to_clark(dim),
        )
    option_lines = []
    for option in options[:_MAX_TOOLTIP_OPTIONS]:
        option_lines.append(
            "<div style='margin:1px 0;'>"
            f"<b>{escape(_resolve_label(taxonomy, option))}</b>"
            f"<span style='color:{theme.TEXT_SUBTLE};'> {escape(_qname_to_clark(option))}</span>"
            "</div>"
        )
    remaining = len(options) - len(option_lines)
    if remaining > 0:
        option_lines.append(
            f"<div style='color:{theme.TEXT_MUTED}; margin-top:3px;'>+ {remaining} more values</div>"
        )
    return _html_dimension_item(dim_label, "".join(option_lines), _qname_to_clark(dim))


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
            open_dimension_rows = [
                row
                for item in cell.open_dimension_info
                if (row := _html_open_dimension_item(self._taxonomy, item))
            ]
            if cell.cell_kind == "open-key":
                rows = []
                if cell.open_key_dimension is not None:
                    dim_label = _resolve_label(self._taxonomy, cell.open_key_dimension)
                    rows.append(
                        _html_row(
                            "Dimension",
                            (
                                f"<b>{escape(dim_label)}</b><br>"
                                f"<span style='color:{theme.TEXT_SUBTLE};'>{escape(_qname_to_clark(cell.open_key_dimension))}</span>"
                            ),
                        )
                    )
                if cell.open_key_member is not None:
                    mem_label = _resolve_label(self._taxonomy, cell.open_key_member)
                    rows.append(
                        _html_row(
                            "Selected member",
                            (
                                f"<b>{escape(mem_label)}</b><br>"
                                f"<span style='color:{theme.TEXT_SUBTLE};'>{escape(_qname_to_clark(cell.open_key_member))}</span>"
                            ),
                        )
                    )
                elif cell.open_key_text:
                    rows.append(_html_row("Selected value", escape(cell.open_key_text)))
                if cell.open_key_options:
                    option_items = []
                    for option in cell.open_key_options[:_MAX_TOOLTIP_OPTIONS]:
                        option_items.append(
                            "<div style='margin:1px 0;'>"
                            f"<b>{escape(_resolve_label(self._taxonomy, option))}</b>"
                            f"<span style='color:{theme.TEXT_SUBTLE};'> {escape(_qname_to_clark(option))}</span>"
                            "</div>"
                        )
                    remaining = len(cell.open_key_options) - len(option_items)
                    if remaining > 0:
                        option_items.append(
                            f"<div style='color:{theme.TEXT_MUTED}; margin-top:3px;'>"
                            f"+ {remaining} more values</div>"
                        )
                    rows.append(_html_row("Allowed values", "".join(option_items)))
                if not rows:
                    return None
                return (
                    "<qt>"
                    f"<div style='background:{theme.SURFACE_BG}; color:{theme.TEXT_MAIN}; "
                    f"border:1px solid {theme.BORDER}; padding:8px; min-width:280px;'>"
                    f"<div style='font-size:13px; font-weight:700; margin-bottom:4px;'>Open Row Key</div>"
                    f"{_html_section('Selection', rows)}"
                    f"{_html_block_section('Open Dimensions', open_dimension_rows)}"
                    "</div></qt>"
                )
            coord = cell.coordinate
            concept_rows = []
            if coord.concept is not None:
                label = ""
                if self._taxonomy is not None:
                    label = _resolve_label(self._taxonomy, coord.concept)
                data_type = None
                period_type = None
                balance = None
                if self._taxonomy is not None:
                    concept_def = self._taxonomy.concepts.get(coord.concept)
                    if concept_def is not None:
                        data_type = getattr(concept_def, "data_type", None)
                        period_type = getattr(concept_def, "period_type", None)
                        balance = getattr(concept_def, "balance", None)
                concept_rows.append(
                    _html_row(
                        "Metric",
                        (
                            f"<b>{escape(label or str(coord.concept))}</b><br>"
                            f"<span style='color:{theme.TEXT_SUBTLE};'>{escape(_qname_to_clark(coord.concept))}</span>"
                        ),
                    )
                )
                if data_type:
                    concept_rows.append(_html_row("Data type", escape(_qname_to_clark(data_type))))
                if period_type:
                    concept_rows.append(_html_row("Period type", escape(str(period_type))))
                if balance:
                    concept_rows.append(_html_row("Balance", escape(str(balance))))

            dimension_rows = []
            if coord.explicit_dimensions:
                for dim, mem in coord.explicit_dimensions.items():
                    dim_label = _resolve_label(self._taxonomy, dim)
                    mem_label = _resolve_label(self._taxonomy, mem)
                    dimension_rows.append(
                        _html_dimension_item(
                            dim_label,
                            f"<b>{escape(mem_label)}</b>",
                            f"{_qname_to_clark(dim)} = {_qname_to_clark(mem)}",
                        )
                    )
            if coord.typed_dimensions:
                for dim, value in coord.typed_dimensions.items():
                    dim_label = _resolve_label(self._taxonomy, dim)
                    typed_element = (coord.typed_dimension_elements or {}).get(dim)
                    detail = f"{_qname_to_clark(dim)}"
                    if typed_element is not None:
                        detail += f" = {_qname_to_clark(typed_element)}"
                    dimension_rows.append(
                        _html_dimension_item(dim_label, escape(str(value)), detail)
                    )
            if not dimension_rows:
                dimension_rows.extend(open_dimension_rows)

            allowed_rows = []
            if cell.fact_options:
                visible_options = cell.fact_options[:_MAX_TOOLTIP_OPTIONS]
                option_items = []
                for option in visible_options:
                    option_text = str(option)
                    qname = _parse_option_qname(option_text, self._taxonomy)
                    if qname is not None:
                        label = _resolve_label(self._taxonomy, qname)
                        detail = _qname_to_clark(qname)
                    else:
                        label = _display_raw_option(option_text)
                        detail = option_text
                    option_items.append(
                        "<div style='margin:1px 0;'>"
                        f"<b>{escape(label)}</b>"
                        f"<span style='color:{theme.TEXT_SUBTLE};'> {escape(detail)}</span>"
                        "</div>"
                    )
                remaining = len(cell.fact_options) - len(visible_options)
                if remaining > 0:
                    option_items.append(
                        f"<div style='color:{theme.TEXT_MUTED}; margin-top:3px;'>"
                        f"+ {remaining} more values</div>"
                    )
                allowed_rows.append(_html_row("Values", "".join(option_items)))

            context_rows = []
            if coord.period_override is not None:
                context_rows.append(_html_row("Period", escape(str(coord.period_override))))

            sections = "".join(
                [
                    _html_section("Concept", concept_rows),
                    _html_block_section("Dimensions", dimension_rows),
                    _html_section("Allowed Values", allowed_rows),
                    _html_section("Context", context_rows),
                ]
            )
            if not sections:
                return None
            return (
                "<qt>"
                f"<div style='background:{theme.SURFACE_BG}; color:{theme.TEXT_MAIN}; "
                f"border:1px solid {theme.BORDER}; padding:9px; min-width:360px; max-width:680px;'>"
                f"<div style='font-size:13px; font-weight:700; margin-bottom:4px;'>Cell Information</div>"
                f"{sections}"
                "</div></qt>"
            )

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

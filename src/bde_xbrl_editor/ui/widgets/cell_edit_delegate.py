"""CellEditDelegate — QStyledItemDelegate for inline XBRL fact value editing."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QModelIndex, QPoint, QRect, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPolygon
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QLineEdit,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QToolTip,
    QWidget,
)

from bde_xbrl_editor.instance.constants import BDE_DIM_NS
from bde_xbrl_editor.instance.models import DuplicateFactError
from bde_xbrl_editor.instance.validator import XbrlTypeValidator
from bde_xbrl_editor.taxonomy.models import QName, TaxonomyStructure
from bde_xbrl_editor.ui import theme
from bde_xbrl_editor.ui.widgets.table_body_model import (
    CELL_CODE_ROLE,
    FACT_OPTIONS_ROLE,
    OPEN_KEY_ROLE,
)

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.editor import InstanceEditor
    from bde_xbrl_editor.instance.models import XbrlInstance
    from bde_xbrl_editor.table_renderer.models import CellCoordinate, ComputedTableLayout

_FACT_ENUM_LANG_PREF = ["es", "en"]
_AGRUPACION_DIM = QName(namespace=BDE_DIM_NS, local_name="Agrupacion")


def _build_namespace_prefix_map(taxonomy: TaxonomyStructure) -> dict[str, str]:
    """Pick the most common XML prefix for each target namespace from declared concepts."""
    votes: dict[str, Counter[str]] = {}
    for c in taxonomy.concepts.values():
        pfx = c.qname.prefix
        ns = c.qname.namespace
        if not pfx or not ns:
            continue
        votes.setdefault(ns, Counter())[pfx] += 1
    return {ns: counter.most_common(1)[0][0] for ns, counter in votes.items()}


def _build_prefix_to_namespace(taxonomy: TaxonomyStructure) -> dict[str, str]:
    """Map QName prefix → namespace URI (first declaration wins on collision)."""
    out: dict[str, str] = {}
    for c in taxonomy.concepts.values():
        pfx = c.qname.prefix
        ns = c.qname.namespace
        if pfx and ns and pfx not in out:
            out[pfx] = ns
    return out


def _fallback_prefix_for_namespace(namespace: str) -> str:
    """Derive a readable prefix when the taxonomy did not declare one for this namespace."""
    tail = namespace.rstrip("/").split("/")[-1] or "mem"
    slug = "".join(ch if ch.isalnum() else "_" for ch in tail).strip("_").lower()
    return (slug[:20] or "mem").lstrip("0123456789") or "mem"


def _qname_to_prefixed_lexical(qname: QName, ns_to_prefix: dict[str, str]) -> str:
    """Return ``prefix:local`` for XBRL instance lexical form."""
    ns = qname.namespace
    pfx = qname.prefix or ns_to_prefix.get(ns)
    if not pfx:
        pfx = _fallback_prefix_for_namespace(ns)
    return f"{pfx}:{qname.local_name}"


def _parse_fact_option_lexical(
    lexical: str,
    taxonomy: TaxonomyStructure,
    prefix_to_ns: dict[str, str],
) -> QName | None:
    """Parse XSD QName lexical, Clark, EE2 URI, or ``prefix:local`` into a QName."""
    s = lexical.strip()
    if not s:
        return None
    if s.startswith("{") and "}" in s:
        return QName.from_clark(s)
    if s.startswith(("http://", "https://")) and "#" in s:
        ns, _, local = s.partition("#")
        if ns and local:
            return QName(namespace=ns, local_name=local)
    if ":" in s and not s.startswith("http"):
        prefix, _, local = s.partition(":")
        ns = prefix_to_ns.get(prefix)
        if ns:
            return QName(namespace=ns, local_name=local, prefix=prefix)
    return None


def _fact_option_match_candidates(
    raw: str,
    taxonomy: TaxonomyStructure,
    ns_to_prefix: dict[str, str],
    prefix_to_ns: dict[str, str],
) -> list[str]:
    """All string forms that should select the same combo row (prefix, Clark, URI)."""
    s = raw.strip()
    if not s:
        return []
    out: list[str] = []

    def _push(x: str) -> None:
        if x and x not in out:
            out.append(x)

    _push(s)
    qn = _parse_fact_option_lexical(s, taxonomy, prefix_to_ns)
    if qn is None:
        return out
    _push(_qname_to_prefixed_lexical(qn, ns_to_prefix))
    _push(_qname_to_clark(qn))
    uri = _clark_to_expanded_name_uri(_qname_to_clark(qn))
    if uri:
        _push(uri)
    return out


_CELL_CODE_FG = QColor(theme.TEXT_MAIN)
_CELL_CODE_CORNER = QColor("#8B7355")  # dark triangle corner marker
_CELL_CODE_BG = QColor("#E4EEF9")
_CELL_CODE_BORDER = QColor("#9EB6D4")


def _qname_to_clark(concept: QName) -> str:
    return f"{{{concept.namespace}}}{concept.local_name}"


def _clark_to_expanded_name_uri(clark: str) -> str | None:
    """Map ``{ns}local`` to EE2 expanded name URI ``ns#local``."""
    if not (clark.startswith("{") and "}" in clark):
        return None
    end = clark.index("}")
    ns, local = clark[1:end], clark[end + 1 :]
    if not ns or not local:
        return None
    return f"{ns}#{local}"


def _display_option_value(raw_value: str) -> str:
    if raw_value.startswith(("http://", "https://")) and "#" in raw_value:
        return raw_value.rsplit("#", 1)[-1]
    if raw_value.startswith("{") and "}" in raw_value:
        return raw_value.split("}", 1)[1]
    if ":" in raw_value:
        return raw_value.split(":", 1)[1]
    return raw_value


def _get_type_category(taxonomy: TaxonomyStructure, concept: QName) -> str:
    """Return the broad type category for a concept."""
    from bde_xbrl_editor.instance.validator import _type_category  # noqa: PLC0415

    concept_def = taxonomy.concepts.get(concept)
    if concept_def is None:
        return "string"
    return _type_category(concept_def.data_type.local_name)


def _find_fact_index(
    instance: XbrlInstance,
    coordinate: CellCoordinate,
) -> int | None:
    """Find the index in instance.facts that matches coordinate, or None."""
    if coordinate.concept is None:
        return None
    coord_dims = coordinate.explicit_dimensions or {}
    coord_typed_dims = {
        dim_qname: value.strip()
        for dim_qname, value in (coordinate.typed_dimensions or {}).items()
        if value.strip()
    }
    for i, fact in enumerate(instance.facts):
        if fact.concept != coordinate.concept:
            continue
        context = instance.contexts.get(fact.context_ref)
        if context is None:
            continue
        typed_dim_keys = set((getattr(context, "typed_dimensions", {}) or {}).keys())
        fact_dims = {
            dim_qname: member_qname
            for dim_qname, member_qname in context.dimensions.items()
            if dim_qname not in typed_dim_keys
        }
        fact_dims.pop(_AGRUPACION_DIM, None)
        fact_typed_dims = {
            dim_qname: value.strip()
            for dim_qname, value in (getattr(context, "typed_dimensions", {}) or {}).items()
            if value.strip()
        }
        # All coordinate dims must match
        if any(fact_dims.get(d) != m for d, m in coord_dims.items()):
            continue
        if any(fact_typed_dims.get(d) != v for d, v in coord_typed_dims.items()):
            continue
        # Fact must not have extra dims the coordinate doesn't specify
        if any(d not in coord_dims for d in fact_dims):
            continue
        if any(d not in coord_typed_dims for d in fact_typed_dims):
            continue
        return i
    return None


def _report_level_bde_dimensions(
    instance: XbrlInstance,
) -> tuple[dict[QName, QName], dict[QName, str]]:
    """Return report-level BDE dimensions that must be preserved on all contexts."""
    for context in instance.contexts.values():
        dimensions = getattr(context, "dimensions", {}) or {}
        if _AGRUPACION_DIM not in dimensions:
            continue
        dim_containers = getattr(context, "dim_containers", {}) or {}
        return (
            {_AGRUPACION_DIM: dimensions[_AGRUPACION_DIM]},
            {_AGRUPACION_DIM: dim_containers.get(_AGRUPACION_DIM, "segment")},
        )
    return {}, {}


def _ensure_context_ref(instance: XbrlInstance, coordinate: CellCoordinate) -> str:
    """Return the deterministic context_ref for this coordinate, creating the context if needed."""
    from bde_xbrl_editor.instance.context_builder import (  # noqa: PLC0415
        build_dimensional_context,
        generate_context_id,
    )

    report_level_dims, report_level_dim_containers = _report_level_bde_dimensions(instance)
    dims = dict(report_level_dims)
    dims.update(coordinate.explicit_dimensions or {})
    typed_dims = coordinate.typed_dimensions or {}
    typed_dimension_elements = coordinate.typed_dimension_elements or {}
    dim_containers = dict(report_level_dim_containers)
    context_element = "scenario"
    for dim_qname in coordinate.explicit_dimensions or {}:
        dim_containers[dim_qname] = "scenario"
    for dim_qname in typed_dims:
        dim_containers[dim_qname] = "scenario"
    ctx_id = generate_context_id(
        instance.entity,
        instance.period,
        dims,
        typed_dims,
        dim_containers,
    )
    if ctx_id not in instance.contexts:
        ctx = build_dimensional_context(
            instance.entity,
            instance.period,
            dims,
            typed_dimensions=typed_dims,
            typed_dimension_elements=typed_dimension_elements,
            dim_containers=dim_containers,
            context_element=context_element,
        )
        instance.contexts[ctx_id] = ctx
    return ctx_id


class CellEditDelegate(QStyledItemDelegate):
    """Inline delegate for editing XBRL fact values in XbrlTableView body cells."""

    def __init__(
        self,
        taxonomy: TaxonomyStructure | None = None,
        editor: InstanceEditor | None = None,
        table_layout: ComputedTableLayout | None = None,
        table_view_widget: QWidget | None = None,
    ) -> None:
        super().__init__(table_view_widget)
        self._taxonomy = taxonomy
        self._editor = editor
        self._table_layout = table_layout
        self._table_view_widget = table_view_widget
        self._validator = XbrlTypeValidator(taxonomy) if taxonomy is not None else None
        self._invalid_editors: set[int] = set()  # id(editor) for invalid-state editors
        self._prefix_maps_cache: tuple[int, dict[str, str], dict[str, str]] | None = None

    def set_table_layout(self, layout: ComputedTableLayout | None) -> None:
        """Update active layout reference after Z-axis change."""
        self._table_layout = layout

    def _prefix_maps(self) -> tuple[dict[str, str], dict[str, str]]:
        """Cached (namespace→prefix, prefix→namespace) maps for the active taxonomy."""
        if self._taxonomy is None:
            return {}, {}
        tid = id(self._taxonomy)
        if self._prefix_maps_cache is None or self._prefix_maps_cache[0] != tid:
            self._prefix_maps_cache = (
                tid,
                _build_namespace_prefix_map(self._taxonomy),
                _build_prefix_to_namespace(self._taxonomy),
            )
        return self._prefix_maps_cache[1], self._prefix_maps_cache[2]

    # ------------------------------------------------------------------
    # paint — draws cell content + regulator-style cell-code badge
    # ------------------------------------------------------------------

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        super().paint(painter, option, index)

        cell_code = index.data(CELL_CODE_ROLE)
        if not cell_code:
            return

        rect = option.rect
        _CORNER = 7  # triangle leg size in pixels

        painter.save()
        painter.setClipping(False)

        # Small folded-corner triangle in top-right
        tr = rect.topRight()
        triangle = QPolygon([
            QPoint(tr.x(), tr.y()),
            QPoint(tr.x() - _CORNER, tr.y()),
            QPoint(tr.x(), tr.y() + _CORNER),
        ])
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_CELL_CODE_CORNER)
        painter.drawPolygon(triangle)

        font = QFont(painter.font())
        font.setPointSizeF(7.5)
        painter.setFont(font)

        # Blue badge behind the cell code, aligned to the top-left like the regulator tables.
        badge_width = min(rect.width() - _CORNER - 2, 40)
        badge_height = min(rect.height() - 2, 18)
        if badge_width > 10 and badge_height > 8:
            badge_rect = QRect(rect.x() + 1, rect.y() + 1, badge_width, badge_height)
            painter.setPen(_CELL_CODE_BORDER)
            painter.setBrush(_CELL_CODE_BG)
            painter.drawRect(badge_rect)
            text_rect = badge_rect.adjusted(3, 0, -2, -1)
        else:
            text_rect = QRect(rect.x() + 2, rect.y() + 1, rect.width() - _CORNER - 4, rect.height() - 2)

        painter.setPen(_CELL_CODE_FG)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignCenter,
            cell_code,
        )

        painter.restore()

    # ------------------------------------------------------------------
    # Coordinate lookup
    # ------------------------------------------------------------------

    def _get_coordinate(self, index: QModelIndex) -> CellCoordinate | None:
        if self._table_layout is None:
            return None
        row, col = index.row(), index.column()
        body = self._table_layout.body
        if row >= len(body) or col >= len(body[row]):
            return None
        return body[row][col].coordinate

    # ------------------------------------------------------------------
    # createEditor
    # ------------------------------------------------------------------

    def createEditor(
        self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ) -> QWidget | None:
        open_key = index.data(OPEN_KEY_ROLE)
        if isinstance(open_key, dict):
            options = open_key.get("options") or ()
            if options:
                ed = QComboBox(parent)
                for option_qname in options:
                    if hasattr(option_qname, "namespace") and hasattr(option_qname, "local_name"):
                        label = (
                            self._taxonomy.labels.resolve(
                                option_qname, language_preference=_FACT_ENUM_LANG_PREF
                            )
                            if self._taxonomy is not None
                            else str(option_qname)
                        )
                        if label == str(option_qname):
                            label = getattr(option_qname, "local_name", label)
                        ed.addItem(label, _qname_to_clark(option_qname))
                    else:
                        text = str(option_qname)
                        ed.addItem(text, text)
                return ed
            return QLineEdit(parent)

        fact_options = index.data(FACT_OPTIONS_ROLE)
        if isinstance(fact_options, tuple) and fact_options:
            ed = QComboBox(parent)
            if self._taxonomy is not None:
                ns_to_prefix, prefix_to_ns = self._prefix_maps()
                for option in fact_options:
                    option_text = str(option)
                    qn = _parse_fact_option_lexical(option_text, self._taxonomy, prefix_to_ns)
                    if qn is None:
                        ed.addItem(_display_option_value(option_text), option_text)
                        continue
                    label = self._taxonomy.labels.resolve(
                        qn, language_preference=_FACT_ENUM_LANG_PREF
                    )
                    if label == str(qn):
                        label = qn.local_name
                    data = _qname_to_prefixed_lexical(qn, ns_to_prefix)
                    ed.addItem(label, data)
            else:
                for option in fact_options:
                    option_text = str(option)
                    ed.addItem(_display_option_value(option_text), option_text)
            return ed
        if self._editor is None or self._taxonomy is None:
            return None
        coordinate = self._get_coordinate(index)
        if coordinate is None or coordinate.concept is None:
            return None

        category = _get_type_category(self._taxonomy, coordinate.concept)

        if category == "date":
            ed = QDateEdit(parent)
            ed.setDisplayFormat("yyyy-MM-dd")
            ed.setCalendarPopup(True)
            return ed

        if category == "boolean":
            ed = QComboBox(parent)
            ed.addItems(["true", "false"])
            return ed

        # monetary, decimal, integer, string
        line = QLineEdit(parent)
        if category in ("monetary", "decimal"):
            from PySide6.QtGui import QDoubleValidator  # noqa: PLC0415

            v = QDoubleValidator(line)
            v.setNotation(QDoubleValidator.Notation.StandardNotation)
            line.setValidator(v)
        elif category == "integer":
            from PySide6.QtGui import QIntValidator  # noqa: PLC0415

            line.setValidator(QIntValidator(line))
        return line

    # ------------------------------------------------------------------
    # setEditorData
    # ------------------------------------------------------------------

    def setEditorData(self, editor_widget: QWidget, index: QModelIndex) -> None:
        raw_value = index.data(Qt.ItemDataRole.UserRole) or ""
        if isinstance(editor_widget, QDateEdit):
            from PySide6.QtCore import QDate  # noqa: PLC0415

            d = QDate.fromString(raw_value, "yyyy-MM-dd")
            if d.isValid():
                editor_widget.setDate(d)
        elif isinstance(editor_widget, QComboBox):
            idx = -1
            if isinstance(raw_value, str) and self._taxonomy is not None:
                ns_to_prefix, prefix_to_ns = self._prefix_maps()
                for cand in _fact_option_match_candidates(
                    raw_value, self._taxonomy, ns_to_prefix, prefix_to_ns
                ):
                    idx = editor_widget.findData(cand)
                    if idx >= 0:
                        break
            elif isinstance(raw_value, str):
                candidates = [raw_value]
                alt = _clark_to_expanded_name_uri(raw_value)
                if alt and alt not in candidates:
                    candidates.append(alt)
                for cand in candidates:
                    idx = editor_widget.findData(cand)
                    if idx >= 0:
                        break
            if idx < 0 and isinstance(raw_value, str):
                idx = editor_widget.findText(raw_value)
            if idx >= 0:
                editor_widget.setCurrentIndex(idx)
        elif isinstance(editor_widget, QLineEdit):
            editor_widget.setText(raw_value)

    # ------------------------------------------------------------------
    # updateEditorGeometry
    # ------------------------------------------------------------------

    def updateEditorGeometry(
        self, editor_widget: QWidget, option: QStyleOptionViewItem, index: QModelIndex
    ) -> None:
        editor_widget.setGeometry(option.rect)

    # ------------------------------------------------------------------
    # setModelData
    # ------------------------------------------------------------------

    def setModelData(
        self, editor_widget: QWidget, model, index: QModelIndex
    ) -> None:
        open_key = index.data(OPEN_KEY_ROLE)
        if isinstance(open_key, dict):
            if isinstance(editor_widget, QComboBox):
                selected = editor_widget.currentData()
                if isinstance(selected, str):
                    model.setData(index, selected, Qt.ItemDataRole.EditRole)
            elif isinstance(editor_widget, QLineEdit):
                model.setData(index, editor_widget.text(), Qt.ItemDataRole.EditRole)
            return

        fact_options = index.data(FACT_OPTIONS_ROLE)
        if isinstance(fact_options, tuple) and fact_options:
            if isinstance(editor_widget, QComboBox):
                selected = editor_widget.currentData()
                submitted = (
                    selected if isinstance(selected, str) else editor_widget.currentText()
                )
            else:
                submitted = ""
        elif self._editor is None or self._taxonomy is None or self._validator is None:
            return
        coordinate = self._get_coordinate(index)
        if coordinate is None or coordinate.concept is None:
            return

        # Read submitted value from widget
        if isinstance(fact_options, tuple) and fact_options:
            pass
        elif isinstance(editor_widget, QDateEdit):
            submitted = editor_widget.date().toString("yyyy-MM-dd")
        elif isinstance(editor_widget, QComboBox):
            submitted = editor_widget.currentText()
        elif isinstance(editor_widget, QLineEdit):
            submitted = editor_widget.text()
        else:
            submitted = ""

        instance = self._editor.instance
        fact_index = _find_fact_index(instance, coordinate)

        # Empty submission → remove existing fact
        if not submitted.strip():
            if fact_index is not None:
                self._editor.remove_fact(fact_index)
            return

        # Validate
        is_valid, error_msg = self._validator.validate(submitted, coordinate.concept)
        if not is_valid:
            self._mark_invalid(editor_widget, error_msg)
            return

        # Normalise
        normalised = self._validator.normalise(submitted, coordinate.concept)

        # Update or add
        try:
            if fact_index is not None:
                self._editor.update_fact(fact_index, normalised)
            else:
                context_ref = _ensure_context_ref(instance, coordinate)
                category = _get_type_category(self._taxonomy, coordinate.concept)
                unit_ref = None
                if category in ("monetary", "decimal", "integer"):
                    unit_ref = next(iter(instance.units), None)
                self._editor.add_fact(
                    concept=coordinate.concept,
                    context_ref=context_ref,
                    value=normalised,
                    unit_ref=unit_ref,
                )
        except DuplicateFactError:
            # Race condition — re-read index and try update
            fact_index = _find_fact_index(instance, coordinate)
            if fact_index is not None:
                self._editor.update_fact(fact_index, normalised)

    # ------------------------------------------------------------------
    # eventFilter — keep editor open on invalid input focus-out
    # ------------------------------------------------------------------

    def eventFilter(self, obj: object, event: QEvent) -> bool:
        if (
            event.type() == QEvent.Type.FocusOut
            and isinstance(obj, QWidget)
            and id(obj) in self._invalid_editors
        ):
            obj.setFocus()
            return True
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _mark_invalid(self, editor_widget: QWidget, message: str) -> None:
        editor_widget.setStyleSheet("border: 2px solid red;")
        self._invalid_editors.add(id(editor_widget))
        editor_widget.installEventFilter(self)
        QToolTip.showText(editor_widget.mapToGlobal(editor_widget.rect().bottomLeft()), message)
        editor_widget.setFocus()

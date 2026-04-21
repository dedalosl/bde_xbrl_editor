"""CellEditDelegate — QStyledItemDelegate for inline XBRL fact value editing."""

from __future__ import annotations

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

from bde_xbrl_editor.instance.models import DuplicateFactError
from bde_xbrl_editor.ui import theme
from bde_xbrl_editor.instance.validator import XbrlTypeValidator
from bde_xbrl_editor.ui.widgets.table_body_model import CELL_CODE_ROLE, FACT_OPTIONS_ROLE, OPEN_KEY_ROLE

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.editor import InstanceEditor
    from bde_xbrl_editor.instance.models import XbrlInstance
    from bde_xbrl_editor.table_renderer.models import CellCoordinate, ComputedTableLayout
    from bde_xbrl_editor.taxonomy.models import QName, TaxonomyStructure


_CELL_CODE_FG = QColor(theme.TEXT_MAIN)
_CELL_CODE_CORNER = QColor("#8B7355")  # dark triangle corner marker
_CELL_CODE_BG = QColor("#E4EEF9")
_CELL_CODE_BORDER = QColor("#9EB6D4")


def _qname_to_clark(concept: QName) -> str:
    return f"{{{concept.namespace}}}{concept.local_name}"


def _display_option_value(raw_value: str) -> str:
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


def _ensure_context_ref(instance: XbrlInstance, coordinate: CellCoordinate) -> str:
    """Return the deterministic context_ref for this coordinate, creating the context if needed."""
    from bde_xbrl_editor.instance.context_builder import (  # noqa: PLC0415
        build_dimensional_context,
        generate_context_id,
    )

    dims = coordinate.explicit_dimensions or {}
    typed_dims = coordinate.typed_dimensions or {}
    typed_dimension_elements = coordinate.typed_dimension_elements or {}
    ctx_id = generate_context_id(instance.entity, instance.period, dims, typed_dims)
    if ctx_id not in instance.contexts:
        ctx = build_dimensional_context(
            instance.entity,
            instance.period,
            dims,
            typed_dimensions=typed_dims,
            typed_dimension_elements=typed_dimension_elements,
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

    def set_table_layout(self, layout: ComputedTableLayout | None) -> None:
        """Update active layout reference after Z-axis change."""
        self._table_layout = layout

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
                            self._taxonomy.labels.resolve(option_qname)
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
            idx = editor_widget.findData(raw_value)
            if idx < 0:
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
                if isinstance(selected, str):
                    submitted = selected
                else:
                    submitted = editor_widget.currentText()
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

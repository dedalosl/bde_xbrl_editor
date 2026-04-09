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
from bde_xbrl_editor.instance.validator import XbrlTypeValidator
from bde_xbrl_editor.ui.widgets.table_body_model import CELL_CODE_ROLE

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.editor import InstanceEditor
    from bde_xbrl_editor.instance.models import XbrlInstance
    from bde_xbrl_editor.table_renderer.models import CellCoordinate, ComputedTableLayout
    from bde_xbrl_editor.taxonomy.models import QName, TaxonomyStructure


_CELL_CODE_FG = QColor("#1E3A5F")      # dark navy text for cell code
_CELL_CODE_CORNER = QColor("#8B7355")  # dark triangle corner marker


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
    for i, fact in enumerate(instance.facts):
        if fact.concept != coordinate.concept:
            continue
        context = instance.contexts.get(fact.context_ref)
        if context is None:
            continue
        fact_dims = context.dimensions
        # All coordinate dims must match
        if any(fact_dims.get(d) != m for d, m in coord_dims.items()):
            continue
        # Fact must not have extra dims the coordinate doesn't specify
        if any(d not in coord_dims for d in fact_dims):
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
    ctx_id = generate_context_id(instance.entity, instance.period, dims)
    if ctx_id not in instance.contexts:
        ctx = build_dimensional_context(instance.entity, instance.period, dims)
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
    # paint — draws cell content + soft-blue cell-code badge
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

        # Cell code text — top-left, small font
        painter.setPen(_CELL_CODE_FG)
        font = QFont(painter.font())
        font.setPointSizeF(7.0)
        painter.setFont(font)
        text_rect = QRect(rect.x() + 2, rect.y() + 1, rect.width() - _CORNER - 4, rect.height() - 2)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
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
        if self._editor is None or self._taxonomy is None or self._validator is None:
            return
        coordinate = self._get_coordinate(index)
        if coordinate is None or coordinate.concept is None:
            return

        # Read submitted value from widget
        if isinstance(editor_widget, QDateEdit):
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

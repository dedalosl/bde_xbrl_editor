"""ZAxisSelector — per-dimension Z-axis assignment widget."""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QWidget

from bde_xbrl_editor.ui import theme

if False:  # pragma: no cover
    from bde_xbrl_editor.taxonomy.models import QName


@dataclass(frozen=True)
class ZAxisOption:
    """One selectable member for a Z-axis dimension."""

    member_qname: "QName"
    label: str
    is_used: bool = False


@dataclass(frozen=True)
class ZAxisDimension:
    """UI-ready dimension selector definition."""

    dimension_qname: "QName"
    label: str
    options: tuple[ZAxisOption, ...] = field(default_factory=tuple)
    selected_member: "QName | None" = None


_MUTED_OPTION_COLOR = QColor(theme.TEXT_SUBTLE)
_USED_OPTION_COLOR = QColor(theme.TEXT_MAIN)


class ZAxisSelector(QWidget):
    """One dropdown per Z-axis dimension, with optional valid-combination filtering."""

    z_selection_changed = Signal(object)

    def __init__(
        self,
        dimensions: list[ZAxisDimension],
        valid_combinations: list[dict["QName", "QName"]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._dimensions = dimensions
        self._valid_combinations = valid_combinations or []
        self._combo_by_dimension: dict["QName", QComboBox] = {}
        self._selected: dict["QName", "QName"] = {}
        self._syncing = False

        layout = QFormLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(6)

        if not dimensions:
            self.hide()
            return

        for dimension in dimensions:
            label = QLabel(dimension.label, self)
            label.setStyleSheet(
                f"color: {theme.TEXT_MUTED}; font-size: 11px; font-weight: 600;"
            )
            combo = QComboBox(self)
            combo.setStyleSheet(
                f"""
                QComboBox {{
                    min-width: 240px;
                    background: {theme.INPUT_BG};
                    color: {theme.TEXT_MAIN};
                    border: 1px solid {theme.BORDER};
                    border-radius: 4px;
                    padding: 4px 8px;
                }}
                """
            )
            combo.currentIndexChanged.connect(
                lambda _idx, dim=dimension.dimension_qname: self._on_combo_changed(dim)
            )
            self._combo_by_dimension[dimension.dimension_qname] = combo
            layout.addRow(label, combo)

        self._initialise_selection()
        self._refresh_combos()

    @property
    def selected_assignments(self) -> dict["QName", "QName"]:
        return dict(self._selected)

    def set_dimensions(
        self,
        dimensions: list[ZAxisDimension],
        valid_combinations: list[dict["QName", "QName"]] | None = None,
    ) -> None:
        """Replace selector definitions and rebuild combo contents."""
        self._dimensions = dimensions
        self._valid_combinations = valid_combinations or []
        self._selected.clear()
        self._initialise_selection()
        self._refresh_combos()
        self.setVisible(bool(dimensions))

    def _initialise_selection(self) -> None:
        for dimension in self._dimensions:
            if dimension.selected_member is not None:
                self._selected[dimension.dimension_qname] = dimension.selected_member
            elif dimension.options:
                self._selected[dimension.dimension_qname] = dimension.options[0].member_qname

    def _allowed_options(self, dimension: ZAxisDimension) -> list[ZAxisOption]:
        if not self._valid_combinations:
            return list(dimension.options)

        other_selected = {
            dim_qname: member_qname
            for dim_qname, member_qname in self._selected.items()
            if dim_qname != dimension.dimension_qname
        }
        allowed_members = {
            combo[dimension.dimension_qname]
            for combo in self._valid_combinations
            if dimension.dimension_qname in combo
            and all(combo.get(dim_qname) == member_qname for dim_qname, member_qname in other_selected.items())
        }
        if not allowed_members:
            return list(dimension.options)
        return [opt for opt in dimension.options if opt.member_qname in allowed_members]

    def _refresh_combos(self) -> None:
        self._syncing = True
        try:
            for dimension in self._dimensions:
                combo = self._combo_by_dimension[dimension.dimension_qname]
                allowed_options = self._allowed_options(dimension)
                combo.blockSignals(True)
                combo.clear()
                for option in allowed_options:
                    combo.addItem(option.label, option.member_qname)
                    combo.setItemData(
                        combo.count() - 1,
                        _USED_OPTION_COLOR if option.is_used else _MUTED_OPTION_COLOR,
                        Qt.ItemDataRole.ForegroundRole,
                    )
                selected_member = self._selected.get(dimension.dimension_qname)
                if selected_member not in {opt.member_qname for opt in allowed_options} and allowed_options:
                    selected_member = allowed_options[0].member_qname
                    self._selected[dimension.dimension_qname] = selected_member
                if selected_member is not None:
                    idx = combo.findData(selected_member)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                combo.setEnabled(combo.count() > 1)
                combo.blockSignals(False)
        finally:
            self._syncing = False

    def _on_combo_changed(self, dimension_qname: "QName") -> None:
        if self._syncing:
            return
        combo = self._combo_by_dimension.get(dimension_qname)
        if combo is None:
            return
        member_qname = combo.currentData()
        if member_qname is None:
            return
        self._selected[dimension_qname] = member_qname
        self._refresh_combos()
        self.z_selection_changed.emit(self.selected_assignments)

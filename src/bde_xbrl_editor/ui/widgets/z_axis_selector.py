"""ZAxisSelector — adaptive Z-axis navigation widget (QTabBar / QComboBox)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QTabBar, QWidget

from bde_xbrl_editor.table_renderer.models import ZMemberOption

_TAB_BAR_THRESHOLD = 10


class ZAxisSelector(QWidget):
    """Adaptive Z-axis selector: QTabBar for <=10 members, QComboBox for >10.

    Hidden entirely when there is only 1 member (or none).
    """

    z_index_changed = Signal(int)

    def __init__(self, z_members: list[ZMemberOption], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._z_members = z_members
        self._tab_bar: QTabBar | None = None
        self._combo: QComboBox | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if len(z_members) <= 1:
            self.hide()
            return

        if len(z_members) <= _TAB_BAR_THRESHOLD:
            self._tab_bar = QTabBar(self)
            for opt in z_members:
                self._tab_bar.addTab(opt.label)
            self._tab_bar.currentChanged.connect(self._on_tab_changed)
            layout.addWidget(self._tab_bar)
        else:
            self._combo = QComboBox(self)
            for opt in z_members:
                self._combo.addItem(opt.label, opt.index)
            self._combo.currentIndexChanged.connect(self._on_combo_changed)
            layout.addWidget(self._combo)

    def _on_tab_changed(self, index: int) -> None:
        self.z_index_changed.emit(index)

    def _on_combo_changed(self, index: int) -> None:
        self.z_index_changed.emit(index)

    def set_z_members(self, z_members: list[ZMemberOption]) -> None:
        """Update members — rebuilds the widget."""
        self._z_members = z_members
        # Clear existing
        if self._tab_bar is not None:
            self._tab_bar.blockSignals(True)
            while self._tab_bar.count():
                self._tab_bar.removeTab(0)
            for opt in z_members:
                self._tab_bar.addTab(opt.label)
            self._tab_bar.blockSignals(False)
        elif self._combo is not None:
            self._combo.blockSignals(True)
            self._combo.clear()
            for opt in z_members:
                self._combo.addItem(opt.label, opt.index)
            self._combo.blockSignals(False)

        self.setVisible(len(z_members) > 1)

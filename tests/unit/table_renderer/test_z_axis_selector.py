"""Unit tests for ZAxisSelector — QTabBar vs QComboBox selection, visibility."""

from __future__ import annotations

import pytest

from bde_xbrl_editor.table_renderer.models import ZMemberOption


def _options(n: int) -> list[ZMemberOption]:
    return [ZMemberOption(index=i, label=f"Z{i}") for i in range(n)]


@pytest.mark.qt
class TestZAxisSelector:
    def test_hidden_for_single_member(self, qtbot):
        from bde_xbrl_editor.ui.widgets.z_axis_selector import ZAxisSelector

        w = ZAxisSelector(_options(1))
        qtbot.addWidget(w)
        assert not w.isVisible()

    def test_hidden_for_no_members(self, qtbot):
        from bde_xbrl_editor.ui.widgets.z_axis_selector import ZAxisSelector

        w = ZAxisSelector(_options(0))
        qtbot.addWidget(w)
        assert not w.isVisible()

    def test_tab_bar_for_small_count(self, qtbot):

        from bde_xbrl_editor.ui.widgets.z_axis_selector import ZAxisSelector

        w = ZAxisSelector(_options(5))
        qtbot.addWidget(w)
        w.show()
        assert w._tab_bar is not None
        assert w._combo is None
        assert w._tab_bar.count() == 5

    def test_combo_for_large_count(self, qtbot):

        from bde_xbrl_editor.ui.widgets.z_axis_selector import ZAxisSelector

        w = ZAxisSelector(_options(15))
        qtbot.addWidget(w)
        w.show()
        assert w._combo is not None
        assert w._tab_bar is None
        assert w._combo.count() == 15

    def test_exactly_10_uses_tab_bar(self, qtbot):
        from bde_xbrl_editor.ui.widgets.z_axis_selector import ZAxisSelector

        w = ZAxisSelector(_options(10))
        qtbot.addWidget(w)
        w.show()
        assert w._tab_bar is not None

    def test_signal_emitted_on_tab_change(self, qtbot):
        from bde_xbrl_editor.ui.widgets.z_axis_selector import ZAxisSelector

        w = ZAxisSelector(_options(3))
        qtbot.addWidget(w)
        w.show()
        with qtbot.waitSignal(w.z_index_changed, timeout=1000) as blocker:
            w._tab_bar.setCurrentIndex(2)
        assert blocker.args[0] == 2

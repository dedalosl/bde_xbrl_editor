"""Unit tests for XbrlInstance mutation methods and has_unsaved_changes."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from bde_xbrl_editor.instance.models import (
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlInstance,
)
from bde_xbrl_editor.taxonomy.models import QName


def _make_instance() -> XbrlInstance:
    entity = ReportingEntity(identifier="ES123", scheme="http://www.bde.es/")
    period = ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31))
    return XbrlInstance(
        taxonomy_entry_point=Path("/tmp/entry_point.xsd"),
        schema_ref_href="/tmp/entry_point.xsd",
        entity=entity,
        period=period,
        _dirty=True,
    )


def _make_fact(value: str = "100") -> Fact:
    return Fact(
        concept=QName("http://example.com/ns", "Assets"),
        context_ref="ctx_abc12345",
        unit_ref="EUR",
        value=value,
        decimals="-3",
    )


class TestHasUnsavedChanges:
    def test_true_after_creation(self):
        inst = _make_instance()
        assert inst.has_unsaved_changes is True

    def test_false_after_mark_saved(self):
        inst = _make_instance()
        inst.mark_saved(Path("/tmp/out.xbrl"))
        assert inst.has_unsaved_changes is False

    def test_true_after_add_fact(self):
        inst = _make_instance()
        inst.mark_saved(Path("/tmp/out.xbrl"))
        inst.add_fact(_make_fact())
        assert inst.has_unsaved_changes is True

    def test_true_after_update_fact(self):
        inst = _make_instance()
        inst.add_fact(_make_fact("100"))
        inst.mark_saved(Path("/tmp/out.xbrl"))
        inst.update_fact(0, "200")
        assert inst.has_unsaved_changes is True

    def test_true_after_remove_fact(self):
        inst = _make_instance()
        inst.add_fact(_make_fact())
        inst.mark_saved(Path("/tmp/out.xbrl"))
        inst.remove_fact(0)
        assert inst.has_unsaved_changes is True


class TestMarkSaved:
    def test_sets_source_path(self):
        inst = _make_instance()
        p = Path("/tmp/saved.xbrl")
        inst.mark_saved(p)
        assert inst.source_path == p

    def test_clears_dirty_flag(self):
        inst = _make_instance()
        inst.mark_saved(Path("/tmp/saved.xbrl"))
        assert inst._dirty is False


class TestAddFact:
    def test_fact_appended(self):
        inst = _make_instance()
        fact = _make_fact()
        inst.add_fact(fact)
        assert fact in inst.facts
        assert len(inst.facts) == 1

    def test_dirty_set(self):
        inst = _make_instance()
        inst._dirty = False
        inst.add_fact(_make_fact())
        assert inst._dirty is True


class TestUpdateFact:
    def test_value_updated(self):
        inst = _make_instance()
        inst.add_fact(_make_fact("100"))
        inst.update_fact(0, "999")
        assert inst.facts[0].value == "999"

    def test_dirty_set(self):
        inst = _make_instance()
        inst.add_fact(_make_fact())
        inst._dirty = False
        inst.update_fact(0, "1")
        assert inst._dirty is True


class TestRemoveFact:
    def test_fact_removed(self):
        inst = _make_instance()
        fact = _make_fact()
        inst.add_fact(fact)
        inst.remove_fact(0)
        assert inst.facts == []

    def test_dirty_set(self):
        inst = _make_instance()
        inst.add_fact(_make_fact())
        inst._dirty = False
        inst.remove_fact(0)
        assert inst._dirty is True

"""Qt notifications adapt the pure editor without duplicating its mutations."""

from pathlib import Path

import pytest
from PySide6.QtCore import QObject

from bde_xbrl_editor.instance.models import DuplicateFactError, Fact
from bde_xbrl_editor.ui.instance_editor_adapter import InstanceEditorAdapter
from tests.unit.instance.test_editor import _make_instance, _qname


def test_add_fact_emits_changes_made_signal() -> None:
    instance = _make_instance()
    editor = InstanceEditorAdapter(instance)
    received = []
    editor.changes_made.connect(lambda: received.append(True))
    editor.add_fact(concept=_qname("Assets"), context_ref="C1", value="500.00")
    assert received == [True]


def test_update_fact_emits_changes_made_signal() -> None:
    instance = _make_instance()
    instance.facts.append(
        Fact(concept=_qname("Assets"), context_ref="C1", unit_ref="EUR", value="100.00")
    )
    editor = InstanceEditorAdapter(instance)
    received = []
    editor.changes_made.connect(lambda: received.append(True))
    editor.update_fact(0, "999.00")
    assert received == [True]


def test_remove_fact_emits_changes_made_signal() -> None:
    instance = _make_instance()
    instance.facts.append(
        Fact(concept=_qname("Assets"), context_ref="C1", unit_ref="EUR", value="100.00")
    )
    editor = InstanceEditorAdapter(instance)
    received = []
    editor.changes_made.connect(lambda: received.append(True))
    editor.remove_fact(0)
    assert received == [True]


def test_adapter_parent_and_wrapped_instance():
    parent = QObject()
    instance = _make_instance()
    adapter = InstanceEditorAdapter(instance, parent=parent)
    assert adapter.parent() is parent
    assert adapter.instance is instance


def test_context_reassignment_notifies_once_and_empty_is_silent():
    adapter = InstanceEditorAdapter(_make_instance())
    adapter.add_fact(_qname("Assets"), "c1", "10")
    calls = []
    adapter.changes_made.connect(lambda: calls.append(True))
    adapter.reassign_facts_context([], "c2")
    assert calls == []
    adapter.reassign_facts_context([0, 0], "c2")
    assert calls == [True]
    assert adapter.instance.facts[0].context_ref == "c2"


def test_failures_do_not_emit_or_change_facts():
    adapter = InstanceEditorAdapter(_make_instance())
    adapter.add_fact(_qname("Assets"), "c1", "10")
    adapter.add_fact(_qname("Assets"), "c2", "20")
    calls = []
    adapter.changes_made.connect(lambda: calls.append(True))
    with pytest.raises(DuplicateFactError):
        adapter.add_fact(_qname("Assets"), "c1", "30")
    with pytest.raises(DuplicateFactError):
        adapter.reassign_facts_context([0], "c2")
    with pytest.raises(IndexError):
        adapter.update_fact(99, "30")
    with pytest.raises(IndexError):
        adapter.remove_fact(99)
    assert calls == []
    assert [(f.context_ref, f.value) for f in adapter.instance.facts] == [
        ("c1", "10"),
        ("c2", "20"),
    ]


def test_filing_indicator_emits_its_signal_only_and_save_is_silent():
    adapter = InstanceEditorAdapter(_make_instance())
    changes, indicators = [], []
    adapter.changes_made.connect(lambda: changes.append(True))
    adapter.filing_indicators_changed.connect(lambda: indicators.append(True))
    adapter.set_filing_indicator("T1", True, context_ref="c1")
    assert changes == [] and indicators == [True]
    assert adapter.instance.filing_indicators[0].filed
    assert adapter.instance.included_table_ids == ["T1"]
    adapter.mark_saved(Path("saved.xbrl"))
    assert not adapter.instance.has_unsaved_changes
    assert adapter.instance.source_path == Path("saved.xbrl")
    assert changes == [] and indicators == [True]

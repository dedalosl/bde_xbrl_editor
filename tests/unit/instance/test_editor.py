"""Unit tests for InstanceEditor."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

# QApplication must exist before creating QObject subclasses with signals
from PySide6.QtWidgets import QApplication

from bde_xbrl_editor.instance.editor import InstanceEditor
from bde_xbrl_editor.instance.models import (
    DuplicateFactError,
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlInstance,
)
from bde_xbrl_editor.taxonomy.models import QName

_app = QApplication.instance() or QApplication([])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NS = "http://example.com/test"


def _qname(local: str) -> QName:
    return QName(namespace=_NS, local_name=local)


def _make_instance() -> XbrlInstance:
    return XbrlInstance(
        taxonomy_entry_point=Path("/tmp/e.xsd"),
        schema_ref_href="e.xsd",
        entity=ReportingEntity(identifier="ES1", scheme="http://bde.es"),
        period=ReportingPeriod(period_type="instant", instant_date=date(2023, 12, 31)),
        _dirty=False,
    )


# ---------------------------------------------------------------------------
# add_fact
# ---------------------------------------------------------------------------


def test_add_fact_appends_and_sets_dirty() -> None:
    instance = _make_instance()
    editor = InstanceEditor(instance)
    fact = editor.add_fact(
        concept=_qname("Assets"),
        context_ref="C1",
        value="1000.00",
        unit_ref="EUR",
        decimals="2",
    )
    assert len(instance.facts) == 1
    assert instance._dirty is True  # noqa: SLF001
    assert fact.value == "1000.00"


def test_add_fact_raises_duplicate_error() -> None:
    instance = _make_instance()
    editor = InstanceEditor(instance)
    editor.add_fact(concept=_qname("Assets"), context_ref="C1", value="100.00")
    with pytest.raises(DuplicateFactError):
        editor.add_fact(concept=_qname("Assets"), context_ref="C1", value="200.00")


def test_add_fact_emits_changes_made_signal() -> None:
    instance = _make_instance()
    editor = InstanceEditor(instance)
    received = []
    editor.changes_made.connect(lambda: received.append(True))
    editor.add_fact(concept=_qname("Assets"), context_ref="C1", value="500.00")
    assert received == [True]


# ---------------------------------------------------------------------------
# update_fact
# ---------------------------------------------------------------------------


def test_update_fact_changes_value_and_sets_dirty() -> None:
    instance = _make_instance()
    instance.facts.append(
        Fact(concept=_qname("Assets"), context_ref="C1", unit_ref="EUR", value="100.00")
    )
    instance._dirty = False  # noqa: SLF001
    editor = InstanceEditor(instance)
    editor.update_fact(0, "200.00")
    assert instance.facts[0].value == "200.00"
    assert instance._dirty is True  # noqa: SLF001


def test_update_fact_emits_changes_made_signal() -> None:
    instance = _make_instance()
    instance.facts.append(
        Fact(concept=_qname("Assets"), context_ref="C1", unit_ref="EUR", value="100.00")
    )
    editor = InstanceEditor(instance)
    received = []
    editor.changes_made.connect(lambda: received.append(True))
    editor.update_fact(0, "999.00")
    assert received == [True]


# ---------------------------------------------------------------------------
# remove_fact
# ---------------------------------------------------------------------------


def test_remove_fact_removes_and_sets_dirty() -> None:
    instance = _make_instance()
    instance.facts.append(
        Fact(concept=_qname("Assets"), context_ref="C1", unit_ref="EUR", value="100.00")
    )
    instance._dirty = False  # noqa: SLF001
    editor = InstanceEditor(instance)
    editor.remove_fact(0)
    assert len(instance.facts) == 0
    assert instance._dirty is True  # noqa: SLF001


def test_remove_fact_emits_changes_made_signal() -> None:
    instance = _make_instance()
    instance.facts.append(
        Fact(concept=_qname("Assets"), context_ref="C1", unit_ref="EUR", value="100.00")
    )
    editor = InstanceEditor(instance)
    received = []
    editor.changes_made.connect(lambda: received.append(True))
    editor.remove_fact(0)
    assert received == [True]


# ---------------------------------------------------------------------------
# mark_saved
# ---------------------------------------------------------------------------


def test_mark_saved_clears_dirty() -> None:
    instance = _make_instance()
    instance._dirty = True  # noqa: SLF001
    editor = InstanceEditor(instance)
    save_path = Path("/tmp/saved.xbrl")
    editor.mark_saved(save_path)
    assert instance._dirty is False  # noqa: SLF001
    assert instance.source_path == save_path


# ---------------------------------------------------------------------------
# instance property
# ---------------------------------------------------------------------------


def test_instance_property_returns_wrapped_instance() -> None:
    instance = _make_instance()
    editor = InstanceEditor(instance)
    assert editor.instance is instance

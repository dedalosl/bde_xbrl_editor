"""Unit tests for InstanceEditor."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from bde_xbrl_editor.instance.editor import InstanceEditor
from bde_xbrl_editor.instance.models import (
    DuplicateFactError,
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlInstance,
)
from bde_xbrl_editor.taxonomy.models import QName

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


def test_public_core_editor_imports_and_mutates_without_qt():
    """An isolated consumer can use the public API with Qt imports forbidden."""
    import subprocess
    import sys
    import textwrap

    script = textwrap.dedent("""
        import importlib.abc
        import sys
        from datetime import date
        from pathlib import Path

        class RejectQt(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == "PySide6" or fullname.startswith("PySide6."):
                    raise AssertionError("Core imported Qt: " + fullname)
                return None

        sys.meta_path.insert(0, RejectQt())
        from bde_xbrl_editor.instance import InstanceEditor, XbrlInstance, ReportingEntity, ReportingPeriod, DuplicateFactError, BdePreambulo
        from bde_xbrl_editor.taxonomy.models import QName
        instance = XbrlInstance(Path("test.xsd"), "test.xsd",
            ReportingEntity("entity", "urn:entity"), ReportingPeriod("instant", instant_date=date(2025, 12, 31)))
        editor = InstanceEditor(instance)
        concept = QName("urn:test", "amount")
        fact = editor.add_fact(concept, "c1", "10.00", "EUR", "2")
        assert editor.instance is instance and fact.value == "10.00"
        try:
            editor.add_fact(concept, "c1", "duplicate")
        except DuplicateFactError:
            pass
        else:
            raise AssertionError("Duplicate accepted")
        fact.is_nil = True
        editor.update_fact(0, "20.00")
        assert fact.value == "20.00" and not fact.is_nil
        editor.reassign_facts_context([0, 0], "c2")
        assert fact.context_ref == "c2"
        instance.bde_preambulo = BdePreambulo(context_ref="c2")
        editor.set_filing_indicator("T1", True, context_ref="c2")
        assert instance.included_table_ids == ["T1"]
        assert instance.bde_preambulo.estados_reportados[0].codigo == "T1"
        assert not instance.bde_preambulo.estados_reportados[0].blanco
        editor.remove_fact(0)
        assert not instance.facts and instance.has_unsaved_changes
        editor.mark_saved(Path("saved.xbrl"))
        assert not instance.has_unsaved_changes
        assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)
    """)
    completed = subprocess.run(
        [sys.executable, "-I", "-c", script], capture_output=True, text=True, timeout=30
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr

"""Unit tests for the conformance suite registry."""

from __future__ import annotations

import pytest

from bde_xbrl_editor.conformance.registry import SUITE_REGISTRY, SuiteDefinition


def test_registry_has_four_suites() -> None:
    assert len(SUITE_REGISTRY) == 4


def test_registry_keys() -> None:
    assert set(SUITE_REGISTRY.keys()) == {"xbrl21", "dimensions", "table-linkbase", "formula"}


def test_all_entries_are_suite_definitions() -> None:
    for key, val in SUITE_REGISTRY.items():
        assert isinstance(val, SuiteDefinition), f"Expected SuiteDefinition, got {type(val)} for {key!r}"


def test_xbrl21_is_blocking() -> None:
    assert SUITE_REGISTRY["xbrl21"].blocking is True


def test_dimensions_is_blocking() -> None:
    assert SUITE_REGISTRY["dimensions"].blocking is True


def test_formula_is_blocking() -> None:
    assert SUITE_REGISTRY["formula"].blocking is True


def test_table_linkbase_is_not_blocking() -> None:
    assert SUITE_REGISTRY["table-linkbase"].blocking is False


def test_table_linkbase_has_informational_note() -> None:
    note = SUITE_REGISTRY["table-linkbase"].informational_note
    assert note is not None
    assert len(note) > 0


def test_index_filenames() -> None:
    assert SUITE_REGISTRY["xbrl21"].index_filename == "xbrl.xml"
    assert SUITE_REGISTRY["dimensions"].index_filename == "xdt.xml"
    assert SUITE_REGISTRY["table-linkbase"].index_filename == "testcases-index.xml"
    assert SUITE_REGISTRY["formula"].index_filename == "index.xml"


def test_subdirectories() -> None:
    assert SUITE_REGISTRY["xbrl21"].subdirectory == "xbrl-2.1"
    assert SUITE_REGISTRY["dimensions"].subdirectory == "dimensions-1.0"
    assert SUITE_REGISTRY["table-linkbase"].subdirectory == "table-linkbase-1.0"
    assert SUITE_REGISTRY["formula"].subdirectory == "formula-1.0"


def test_suite_definition_is_frozen() -> None:
    defn = SUITE_REGISTRY["xbrl21"]
    with pytest.raises((AttributeError, TypeError)):
        defn.blocking = False  # type: ignore[misc]

"""Integration tests for the Table Linkbase 1.0 conformance suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from bde_xbrl_editor.conformance.models import SuiteStatus
from bde_xbrl_editor.conformance.parser import ConformanceSuiteParser
from bde_xbrl_editor.conformance.registry import SUITE_REGISTRY
from bde_xbrl_editor.conformance.runner import ConformanceRunner

from .conftest import table_linkbase_available


@table_linkbase_available
def test_table_linkbase_suite_parses_without_error(suite_data_dir: Path) -> None:
    """The Table Linkbase 1.0 index and test cases should parse without raising."""
    parser = ConformanceSuiteParser(suite_data_dir)
    suite_def = SUITE_REGISTRY["table-linkbase"]
    test_cases = parser.load_suite(suite_def)
    assert len(test_cases) > 0, "Expected at least one test case"


@table_linkbase_available
def test_table_linkbase_suite_is_non_blocking() -> None:
    """Table Linkbase suite should be configured as non-blocking."""
    assert SUITE_REGISTRY["table-linkbase"].blocking is False


@table_linkbase_available
@pytest.mark.slow
def test_table_linkbase_runner_completes(suite_data_dir: Path) -> None:
    runner = ConformanceRunner(
        suite_data_dir=suite_data_dir,
        selected_suites=["table-linkbase"],
    )
    report = runner.run()
    tl_result = next(
        (sr for sr in report.suite_results if sr.suite_id == "table-linkbase"), None
    )
    assert tl_result is not None
    # Non-blocking suite failures don't affect exit code
    assert report.exit_code == 0

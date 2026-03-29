"""Pytest fixtures for conformance suite integration tests.

The integration tests use the actual conformance suite data located at
conformance/ in the project root. We create symlinks under a temporary
directory that matches the expected SuiteDefinition.subdirectory structure.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Project root (3 levels up from this file: tests/integration/conformance/conftest.py)
_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Actual conformance data locations
_ACTUAL_SUITES = {
    "xbrl-2.1": _PROJECT_ROOT / "conformance" / "XBRL-CONF-2025-07-16",
    "dimensions-1.0": _PROJECT_ROOT / "conformance" / "XBRL-XDT-CONF-2025-09-09",
    "table-linkbase-1.0": _PROJECT_ROOT / "conformance" / "table-linkbase-conformance-2024-12-17",
    "formula-1.0": _PROJECT_ROOT / "conformance" / "formula-conformance-2022-07-21",
}


@pytest.fixture(scope="session")
def suite_data_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A session-scoped suite data directory with symlinks to actual conformance data."""
    base = tmp_path_factory.mktemp("suite-data", numbered=False)
    for subdir_name, actual_path in _ACTUAL_SUITES.items():
        link = base / subdir_name
        if actual_path.exists():
            link.symlink_to(actual_path, target_is_directory=True)
        else:
            link.mkdir(parents=True, exist_ok=True)
    return base


def _suite_available(suite_key: str) -> bool:
    return _ACTUAL_SUITES.get(suite_key, Path()).exists()


xbrl21_available = pytest.mark.skipif(
    not _suite_available("xbrl-2.1"),
    reason="XBRL 2.1 conformance suite data not available",
)

dimensions_available = pytest.mark.skipif(
    not _suite_available("dimensions-1.0"),
    reason="Dimensions 1.0 conformance suite data not available",
)

formula_available = pytest.mark.skipif(
    not _suite_available("formula-1.0"),
    reason="Formula 1.0 conformance suite data not available",
)

table_linkbase_available = pytest.mark.skipif(
    not _suite_available("table-linkbase-1.0"),
    reason="Table Linkbase 1.0 conformance suite data not available",
)

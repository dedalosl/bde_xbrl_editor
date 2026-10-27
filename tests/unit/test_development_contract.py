"""Executable contracts for the documented development workflow."""

import tomllib
from pathlib import Path
from types import SimpleNamespace

from packaging.requirements import Requirement

from tests import conftest

ROOT = Path(__file__).resolve().parents[2]


def test_development_extra_provides_coverage_plugin():
    config = tomllib.loads((ROOT / "pyproject.toml").read_text())
    requirements = [
        Requirement(value) for value in config["project"]["optional-dependencies"]["dev"]
    ]
    assert any(requirement.name.replace("_", "-") == "pytest-cov" for requirement in requirements)


def test_external_data_selection_keeps_unit_regressions_in_fast_suite():
    selected = {}
    items = []
    for relative in (
        "tests/integration/conformance/test_xbrl21_suite.py",
        "tests/unit/conformance/test_runner.py",
        "tests/unit/ui/test_validation_freshness.py",
    ):
        markers = []
        selected[relative] = markers
        items.append(SimpleNamespace(path=ROOT / relative, add_marker=markers.append))
    conftest.pytest_collection_modifyitems(items)
    assert [
        marker.name for marker in selected["tests/integration/conformance/test_xbrl21_suite.py"]
    ] == ["external_conformance"]
    assert selected["tests/unit/conformance/test_runner.py"] == []
    assert selected["tests/unit/ui/test_validation_freshness.py"] == []

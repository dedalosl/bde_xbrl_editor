"""Conformance suite registry — describes all known conformance suites."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SuiteDefinition:
    """Describes a single conformance suite and how to locate its data."""

    suite_id: str
    label: str
    blocking: bool
    informational_note: str | None
    index_filename: str
    subdirectory: str


SUITE_REGISTRY: dict[str, SuiteDefinition] = {
    "xbrl21": SuiteDefinition(
        suite_id="xbrl21",
        label="XBRL 2.1 Conformance Suite",
        blocking=True,
        informational_note=None,
        index_filename="xbrl.xml",
        subdirectory="xbrl-2.1",
    ),
    "dimensions": SuiteDefinition(
        suite_id="dimensions",
        label="Dimensions 1.0 Conformance Suite",
        blocking=True,
        informational_note=None,
        index_filename="xdt.xml",
        subdirectory="dimensions-1.0",
    ),
    "table-linkbase": SuiteDefinition(
        suite_id="table-linkbase",
        label="Table Linkbase 1.0 Conformance Suite",
        blocking=False,
        informational_note=(
            "This suite is INFORMATIONAL in v1. The application implements Table Linkbase PWD; "
            "Table Linkbase 1.0 failures are expected and non-blocking. "
            "Full TL 1.0 support is planned for a future version."
        ),
        index_filename="testcases-index.xml",
        subdirectory="table-linkbase-1.0",
    ),
    "formula": SuiteDefinition(
        suite_id="formula",
        label="Formula 1.0 Conformance Suite",
        blocking=True,
        informational_note="v1 scope: value, existence, and consistency assertions only.",
        index_filename="index.xml",
        subdirectory="formula-1.0",
    ),
}

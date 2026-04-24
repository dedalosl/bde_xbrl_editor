"""ConformanceSuiteParser — parses XBRL conformance suite index and test case files."""

from __future__ import annotations

import logging
from pathlib import Path

from lxml import etree

from bde_xbrl_editor.conformance.errors import SuiteDataMissingError, TestCaseParseError
from bde_xbrl_editor.conformance.models import (
    ExpectedOutcome,
    ExpectedOutcomeType,
    TestCase,
    TestVariation,
)
from bde_xbrl_editor.conformance.registry import SuiteDefinition
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file

log = logging.getLogger(__name__)

# Data element local names that describe input files
_DATA_FILE_TAGS = frozenset(["xsd", "schema", "instance", "linkbase"])


def _local(tag: object) -> str:
    """Return the local name from a Clark-notation tag.

    Returns empty string for non-string tags (lxml Comment/PI nodes have callable tags).
    """
    if not isinstance(tag, str):
        return ""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_expected_outcome(result_el: etree._Element | None) -> ExpectedOutcome:
    """Convert a <result> element into an ExpectedOutcome."""
    if result_el is None:
        return ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)

    # Check @expected attribute
    expected_attr = result_el.get("expected", "")
    if expected_attr == "valid":
        return ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)
    if expected_attr == "invalid":
        return ExpectedOutcome(outcome_type=ExpectedOutcomeType.ERROR)

    # Check child elements for error/warning codes
    for child in result_el:
        local = _local(child.tag)
        code = (child.text or "").strip()
        if local == "error":
            return ExpectedOutcome(
                outcome_type=ExpectedOutcomeType.ERROR,
                error_code=code if code else None,
            )
        if local == "warning":
            return ExpectedOutcome(
                outcome_type=ExpectedOutcomeType.WARNING,
                error_code=code if code else None,
            )

    # Empty <result/> element with no attributes and no children = valid
    return ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)


class ConformanceSuiteParser:
    """Parses a conformance suite index and all referenced test case files."""

    def __init__(self, suite_data_dir: Path) -> None:
        self._suite_data_dir = suite_data_dir

    def load_suite(self, suite_def: SuiteDefinition) -> list[TestCase]:
        """Load all test cases for the given suite definition.

        Raises:
            SuiteDataMissingError: if the index file does not exist.
        """
        suite_dir = self._suite_data_dir / suite_def.subdirectory
        index_path = suite_dir / suite_def.index_filename

        if not index_path.exists():
            raise SuiteDataMissingError(suite_def.suite_id, index_path)

        try:
            tc_paths = self._parse_index(index_path, suite_def)
        except SuiteDataMissingError:
            raise
        except Exception as exc:
            raise SuiteDataMissingError(suite_def.suite_id, index_path) from exc

        test_cases: list[TestCase] = []
        for tc_path in tc_paths:
            if not tc_path.exists():
                log.warning("Test case file not found, skipping: %s", tc_path)
                continue
            try:
                tc = self._parse_test_case(tc_path, suite_def.suite_id)
                test_cases.append(tc)
            except TestCaseParseError as exc:
                log.warning("Skipping test case due to parse error: %s", exc)
            except Exception as exc:  # noqa: BLE001
                log.warning("Skipping test case '%s': %s", tc_path, exc)

        return test_cases

    def _parse_index(
        self, index_path: Path, suite_def: SuiteDefinition
    ) -> list[Path]:
        """Parse the index XML and return absolute paths to all test case files."""
        try:
            tree = parse_xml_file(index_path)
        except etree.XMLSyntaxError as exc:
            raise TestCaseParseError(index_path, f"XML syntax error: {exc}") from exc

        root = tree.getroot()
        root_local = _local(root.tag)

        uris: list[str] = []

        if root_local == "documentation":
            # Formula index format: <documentation><testcases root="subdir"><testcase uri="..."/>
            # The @root attribute on <testcases> is a subdirectory prefix for all URIs.
            for testcases_el in root:
                if _local(testcases_el.tag) != "testcases":
                    continue
                root_prefix = testcases_el.get("root", "").strip()
                for tc_el in testcases_el:
                    if _local(tc_el.tag) == "testcase":
                        uri = tc_el.get("uri", "").strip()
                        if uri:
                            full_uri = f"{root_prefix}/{uri}" if root_prefix else uri
                            uris.append(full_uri)
        else:
            # XBRL 2.1, Dimensions, Table Linkbase: flat <testcases><testcase uri="..."/>
            for tc_el in root.iter():
                if _local(tc_el.tag) == "testcase":
                    uri = tc_el.get("uri", "").strip()
                    if uri:
                        uris.append(uri)

        paths: list[Path] = []
        for uri in uris:
            resolved = (index_path.parent / uri).resolve()
            paths.append(resolved)

        return paths

    def _parse_test_case(self, tc_path: Path, suite_id: str) -> TestCase:
        """Parse a single test case XML file into a TestCase model."""
        try:
            tree = parse_xml_file(tc_path)
        except etree.XMLSyntaxError as exc:
            raise TestCaseParseError(tc_path, f"XML syntax error: {exc}") from exc

        root = tree.getroot()

        # Extract test case id and description
        test_case_id = root.get("name", "") or tc_path.stem
        description = root.get("description", "")

        # Check for <description> child element if attribute not present
        if not description:
            for child in root:
                if _local(child.tag) == "description":
                    description = (child.text or "").strip()
                    break

        # XBRL 2.1 marks full-conformance-only test cases with testcase@minimal="false".
        # The default is minimal="true", so missing/other values remain mandatory for
        # minimal conformance. Variation-level optional markers may still narrow scope.
        testcase_mandatory = True
        if suite_id == "xbrl21" and root.get("minimal", "").lower() == "false":
            testcase_mandatory = False

        # Parse variations
        variations: list[TestVariation] = []
        for var_el in root:
            if _local(var_el.tag) != "variation":
                continue
            try:
                variation = self._parse_variation(
                    var_el,
                    tc_path,
                    suite_id,
                    testcase_mandatory=testcase_mandatory,
                )
                variations.append(variation)
            except Exception as exc:  # noqa: BLE001
                var_id = var_el.get("id", "?")
                log.warning(
                    "Skipping variation '%s' in '%s': %s", var_id, tc_path, exc
                )

        return TestCase(
            test_case_id=test_case_id,
            description=description,
            source_file=tc_path,
            suite_id=suite_id,
            variations=tuple(variations),
        )

    def _parse_variation(
        self,
        var_el: etree._Element,
        tc_path: Path,
        suite_id: str,
        *,
        testcase_mandatory: bool = True,
    ) -> TestVariation:
        """Parse a single <variation> element."""
        variation_id = var_el.get("id", "")
        name = var_el.get("name", "") or variation_id

        # Determine mandatory
        mandatory = testcase_mandatory
        var_type = var_el.get("type", "").lower()
        blocked = var_el.get("blocked", "").lower()
        status = var_el.get("status", "").lower()
        if var_type == "optional" or blocked == "true" or status == "optional":
            mandatory = False

        # Parse description child
        description: str | None = None
        for child in var_el:
            if _local(child.tag) == "description":
                description = (child.text or "").strip() or None
                break

        # Parse <data> child for input files
        input_files: list[Path] = []
        instance_file: Path | None = None
        taxonomy_file: Path | None = None

        for child in var_el:
            if _local(child.tag) == "data":
                for file_el in child:
                    local_name = _local(file_el.tag)
                    if local_name in _DATA_FILE_TAGS:
                        filename = (file_el.text or "").strip()
                        if filename:
                            resolved = (tc_path.parent / filename).resolve()
                            input_files.append(resolved)
                            if local_name == "instance" and instance_file is None:
                                instance_file = resolved
                            elif (
                                local_name in ("xsd", "schema")
                                and taxonomy_file is None
                            ):
                                taxonomy_file = resolved
                break

        # Parse <result> child
        result_el: etree._Element | None = None
        for child in var_el:
            if _local(child.tag) == "result":
                result_el = child
                break

        expected_outcome = _parse_expected_outcome(result_el)

        return TestVariation(
            variation_id=variation_id,
            name=name,
            description=description,
            input_files=tuple(input_files),
            instance_file=instance_file,
            taxonomy_file=taxonomy_file,
            expected_outcome=expected_outcome,
            mandatory=mandatory,
        )

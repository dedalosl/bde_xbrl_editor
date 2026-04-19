"""Unit tests for ConformanceSuiteParser."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from bde_xbrl_editor.conformance.errors import SuiteDataMissingError, TestCaseParseError
from bde_xbrl_editor.conformance.models import (
    ExpectedOutcomeType,
    TestCase,
    TestVariation,
)
from bde_xbrl_editor.conformance.parser import ConformanceSuiteParser
from bde_xbrl_editor.conformance.registry import SuiteDefinition


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, rel: str, content: str) -> Path:
    p = tmp_path / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def _make_suite_def(
    suite_id: str = "test-suite",
    subdirectory: str = "test-suite",
    index_filename: str = "index.xml",
) -> SuiteDefinition:
    return SuiteDefinition(
        suite_id=suite_id,
        label="Test Suite",
        blocking=True,
        informational_note=None,
        index_filename=index_filename,
        subdirectory=subdirectory,
    )


# ---------------------------------------------------------------------------
# Index parsing tests
# ---------------------------------------------------------------------------


def test_load_suite_raises_when_index_missing(tmp_path: Path) -> None:
    parser = ConformanceSuiteParser(tmp_path)
    suite_def = _make_suite_def(subdirectory="missing-suite", index_filename="index.xml")
    with pytest.raises(SuiteDataMissingError) as exc_info:
        parser.load_suite(suite_def)
    assert "missing-suite" in str(exc_info.value) or "index.xml" in str(exc_info.value)


def test_parse_flat_testcases_index(tmp_path: Path) -> None:
    """XBRL 2.1 / Dimensions format: <testcases><testcase uri="..."/></testcases>"""
    # Create a minimal test case file
    tc_content = """\
        <?xml version="1.0"?>
        <testcase name="MyTest" description="A test">
          <variation id="V-01" name="Valid">
            <data><xsd readMeFirst="true">foo.xsd</xsd></data>
            <result expected="valid"/>
          </variation>
        </testcase>
    """
    tc_path = _write(tmp_path, "suite/testcases/001-test.xml", tc_content)
    _write(tmp_path, "suite/testcases/foo.xsd", "<schema/>")

    index_content = f"""\
        <?xml version="1.0"?>
        <testcases name="Test">
          <testcase uri="testcases/001-test.xml"/>
        </testcases>
    """
    _write(tmp_path, "suite/index.xml", index_content)

    parser = ConformanceSuiteParser(tmp_path)
    suite_def = _make_suite_def(subdirectory="suite", index_filename="index.xml")
    test_cases = parser.load_suite(suite_def)

    assert len(test_cases) == 1
    assert test_cases[0].test_case_id == "MyTest"
    assert len(test_cases[0].variations) == 1


def test_parse_formula_documentation_index(tmp_path: Path) -> None:
    """Formula format: <documentation><testcases><testcase uri="..."/></testcases>"""
    tc_content = """\
        <?xml version="1.0"?>
        <testcase xmlns="http://xbrl.org/2008/conformance" name="FormulaTest">
          <variation id="V-01">
            <data><schema readMeFirst="true">test.xsd</schema></data>
            <result><error>xbrlfe:someError</error></result>
          </variation>
        </testcase>
    """
    tc_path = _write(tmp_path, "formula-suite/tests/001-test.xml", tc_content)
    _write(tmp_path, "formula-suite/tests/test.xsd", "<schema/>")

    index_content = """\
        <?xml version="1.0"?>
        <documentation name="Formula Tests">
          <testcases title="Formula Spec" root="tests">
            <testcase uri="001-test.xml"/>
          </testcases>
        </documentation>
    """
    _write(tmp_path, "formula-suite/index.xml", index_content)

    parser = ConformanceSuiteParser(tmp_path)
    suite_def = _make_suite_def(
        suite_id="formula", subdirectory="formula-suite", index_filename="index.xml"
    )
    test_cases = parser.load_suite(suite_def)
    assert len(test_cases) == 1
    assert test_cases[0].test_case_id == "FormulaTest"
    variation = test_cases[0].variations[0]
    assert variation.expected_outcome.outcome_type == ExpectedOutcomeType.ERROR
    assert variation.expected_outcome.error_code == "xbrlfe:someError"


# ---------------------------------------------------------------------------
# Test case parsing tests
# ---------------------------------------------------------------------------


def test_parse_variation_valid_expected(tmp_path: Path) -> None:
    content = """\
        <?xml version="1.0"?>
        <testcase name="MyTest">
          <variation id="V-01" name="ValidVariation">
            <description>A valid variation</description>
            <data>
              <xsd readMeFirst="false">schema.xsd</xsd>
              <instance readMeFirst="true">instance.xml</instance>
            </data>
            <result expected="valid"/>
          </variation>
        </testcase>
    """
    tc_path = _write(tmp_path, "tc.xml", content)
    parser = ConformanceSuiteParser(tmp_path)
    tc = parser._parse_test_case(tc_path, "test-suite")

    assert tc.test_case_id == "MyTest"
    assert len(tc.variations) == 1
    var = tc.variations[0]
    assert var.variation_id == "V-01"
    assert var.name == "ValidVariation"
    assert var.description == "A valid variation"
    assert var.expected_outcome.outcome_type == ExpectedOutcomeType.VALID
    assert var.mandatory is True
    assert var.instance_file is not None
    assert var.taxonomy_file is not None


def test_parse_variation_invalid_expected(tmp_path: Path) -> None:
    content = """\
        <?xml version="1.0"?>
        <testcase name="InvalidTest">
          <variation id="V-02">
            <data><xsd readMeFirst="true">schema.xsd</xsd></data>
            <result expected="invalid"/>
          </variation>
        </testcase>
    """
    tc_path = _write(tmp_path, "tc.xml", content)
    parser = ConformanceSuiteParser(tmp_path)
    tc = parser._parse_test_case(tc_path, "test-suite")

    var = tc.variations[0]
    assert var.expected_outcome.outcome_type == ExpectedOutcomeType.ERROR
    assert var.expected_outcome.error_code is None


def test_parse_variation_error_code(tmp_path: Path) -> None:
    content = """\
        <?xml version="1.0"?>
        <testcase xmlns="http://xbrl.org/2005/conformance" name="ErrorCodeTest">
          <variation id="V-02">
            <data><xsd readMeFirst="true">schema.xsd</xsd></data>
            <result>
              <error>xbrldte:HypercubeElementIsNotAbstractError</error>
            </result>
          </variation>
        </testcase>
    """
    tc_path = _write(tmp_path, "tc.xml", content)
    parser = ConformanceSuiteParser(tmp_path)
    tc = parser._parse_test_case(tc_path, "test-suite")

    var = tc.variations[0]
    assert var.expected_outcome.outcome_type == ExpectedOutcomeType.ERROR
    assert var.expected_outcome.error_code == "xbrldte:HypercubeElementIsNotAbstractError"


def test_parse_variation_empty_result(tmp_path: Path) -> None:
    """Empty <result/> should be interpreted as valid."""
    content = """\
        <?xml version="1.0"?>
        <testcase xmlns="http://xbrl.org/2005/conformance" name="EmptyResult">
          <variation id="V-01">
            <data><xsd readMeFirst="true">schema.xsd</xsd></data>
            <result/>
          </variation>
        </testcase>
    """
    tc_path = _write(tmp_path, "tc.xml", content)
    parser = ConformanceSuiteParser(tmp_path)
    tc = parser._parse_test_case(tc_path, "test-suite")

    var = tc.variations[0]
    assert var.expected_outcome.outcome_type == ExpectedOutcomeType.VALID


def test_parse_variation_missing_result(tmp_path: Path) -> None:
    """Missing <result> element defaults to valid."""
    content = """\
        <?xml version="1.0"?>
        <testcase name="NoResult">
          <variation id="V-01">
            <data><xsd readMeFirst="true">schema.xsd</xsd></data>
          </variation>
        </testcase>
    """
    tc_path = _write(tmp_path, "tc.xml", content)
    parser = ConformanceSuiteParser(tmp_path)
    tc = parser._parse_test_case(tc_path, "test-suite")

    var = tc.variations[0]
    assert var.expected_outcome.outcome_type == ExpectedOutcomeType.VALID


def test_parse_variation_warning_code(tmp_path: Path) -> None:
    content = """\
        <?xml version="1.0"?>
        <testcase name="WarnTest">
          <variation id="V-01">
            <data><xsd readMeFirst="true">schema.xsd</xsd></data>
            <result><warning>xbrl:someWarning</warning></result>
          </variation>
        </testcase>
    """
    tc_path = _write(tmp_path, "tc.xml", content)
    parser = ConformanceSuiteParser(tmp_path)
    tc = parser._parse_test_case(tc_path, "test-suite")

    var = tc.variations[0]
    assert var.expected_outcome.outcome_type == ExpectedOutcomeType.WARNING
    assert var.expected_outcome.error_code == "xbrl:someWarning"


def test_parse_optional_variation(tmp_path: Path) -> None:
    content = """\
        <?xml version="1.0"?>
        <testcase name="OptionalTest">
          <variation id="V-01" type="optional">
            <data><xsd readMeFirst="true">schema.xsd</xsd></data>
            <result expected="valid"/>
          </variation>
        </testcase>
    """
    tc_path = _write(tmp_path, "tc.xml", content)
    parser = ConformanceSuiteParser(tmp_path)
    tc = parser._parse_test_case(tc_path, "test-suite")

    assert tc.variations[0].mandatory is False


def test_xbrl21_testcase_minimal_false_marks_variations_non_mandatory(tmp_path: Path) -> None:
    content = """\
        <?xml version="1.0"?>
        <testcase name="FullOnlyTest" minimal="false">
          <variation id="V-01">
            <data><xsd readMeFirst="true">schema.xsd</xsd></data>
            <result expected="valid"/>
          </variation>
        </testcase>
    """
    tc_path = _write(tmp_path, "tc.xml", content)
    parser = ConformanceSuiteParser(tmp_path)

    tc = parser._parse_test_case(tc_path, "xbrl21")

    assert tc.variations[0].mandatory is False


def test_xbrl21_testcase_without_minimal_attribute_defaults_to_mandatory(tmp_path: Path) -> None:
    content = """\
        <?xml version="1.0"?>
        <testcase name="MinimalDefaultTest">
          <variation id="V-01">
            <data><xsd readMeFirst="true">schema.xsd</xsd></data>
            <result expected="valid"/>
          </variation>
        </testcase>
    """
    tc_path = _write(tmp_path, "tc.xml", content)
    parser = ConformanceSuiteParser(tmp_path)

    tc = parser._parse_test_case(tc_path, "xbrl21")

    assert tc.variations[0].mandatory is True


def test_xbrl21_variation_optional_still_overrides_minimal_default(tmp_path: Path) -> None:
    content = """\
        <?xml version="1.0"?>
        <testcase name="OptionalVariationDefaultMinimal">
          <variation id="V-01" type="optional">
            <data><xsd readMeFirst="true">schema.xsd</xsd></data>
            <result expected="valid"/>
          </variation>
        </testcase>
    """
    tc_path = _write(tmp_path, "tc.xml", content)
    parser = ConformanceSuiteParser(tmp_path)

    tc = parser._parse_test_case(tc_path, "xbrl21")

    assert tc.variations[0].mandatory is False


def test_skip_missing_testcase_file(tmp_path: Path) -> None:
    """load_suite should warn and skip test cases whose files don't exist."""
    index_content = """\
        <?xml version="1.0"?>
        <testcases name="Test">
          <testcase uri="missing/nonexistent.xml"/>
        </testcases>
    """
    _write(tmp_path, "suite/index.xml", index_content)

    parser = ConformanceSuiteParser(tmp_path)
    suite_def = _make_suite_def(subdirectory="suite", index_filename="index.xml")
    # Should not raise; just return empty list
    test_cases = parser.load_suite(suite_def)
    assert test_cases == []

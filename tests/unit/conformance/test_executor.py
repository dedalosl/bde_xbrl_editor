"""Unit tests for TestCaseExecutor._match_outcome."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bde_xbrl_editor.conformance.executor import (
    TestCaseExecutor,
    _with_input_formula_linkbases,
)
from bde_xbrl_editor.conformance.models import (
    ExpectedOutcome,
    ExpectedOutcomeType,
    TestResultOutcome,
)
from bde_xbrl_editor.taxonomy.cache import TaxonomyCache
from bde_xbrl_editor.taxonomy.models import TaxonomyMetadata, TaxonomyStructure
from bde_xbrl_editor.validation.formula.static import FormulaStaticValidator
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity
from bde_xbrl_editor.validation.xbrl_documents import (
    _validate_xlink_file,
    validate_lax_known_declarations,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_executor() -> TestCaseExecutor:
    return TestCaseExecutor(TaxonomyCache(max_size=1))


def _error_finding(rule_id: str) -> ValidationFinding:
    return ValidationFinding(
        rule_id=rule_id,
        severity=ValidationSeverity.ERROR,
        message="test error",
        source="structural",
    )


def _warning_finding(rule_id: str) -> ValidationFinding:
    return ValidationFinding(
        rule_id=rule_id,
        severity=ValidationSeverity.WARNING,
        message="test warning",
        source="structural",
    )


def _write_xml(path, body: str) -> None:
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:link="http://www.xbrl.org/2003/linkbase"
           xmlns:xlink="http://www.w3.org/1999/xlink"
           targetNamespace="http://example.com/test">
  <xs:annotation>
    <xs:appinfo>
      {body}
    </xs:appinfo>
  </xs:annotation>
  <xs:element name="source" id="source"/>
  <xs:element name="target" id="target"/>
</xs:schema>
""",
        encoding="utf-8",
    )


def _write_lax_defs(path) -> None:
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="http://example.com/lax"
           elementFormDefault="qualified"
           attributeFormDefault="unqualified">
  <xs:element name="integerElement" type="xs:integer"/>
  <xs:element name="stringElement" type="xs:string"/>
  <xs:attribute name="integerAttribute" type="xs:integer"/>
</xs:schema>
""",
        encoding="utf-8",
    )


def _write_linkbase(path, link_element: str) -> None:
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:{link_element} xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link"/>
</link:linkbase>
""",
        encoding="utf-8",
    )


def _empty_taxonomy(tmp_path: Path) -> TaxonomyStructure:
    return TaxonomyStructure(
        metadata=TaxonomyMetadata(
            name="Test",
            version="1.0",
            publisher="Example",
            entry_point_path=tmp_path / "test.xsd",
            loaded_at=datetime(2026, 1, 1),
            declared_languages=("en",),
        ),
        concepts={},
        labels=None,
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
    )


# ---------------------------------------------------------------------------
# XLink/linkbase structural validation
# ---------------------------------------------------------------------------


def test_lax_validation_reports_known_integer_element(tmp_path) -> None:
    defs_path = tmp_path / "defs.xsd"
    _write_lax_defs(defs_path)
    xml_path = tmp_path / "input.xml"
    xml_path.write_text(
        """<root xmlns:lax="http://example.com/lax"
                 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xsi:schemaLocation="http://example.com/lax defs.xsd">
  <lax:integerElement>not an integer</lax:integerElement>
</root>
""",
        encoding="utf-8",
    )

    findings = validate_lax_known_declarations((xml_path,))

    assert [finding.rule_id for finding in findings] == ["xmlschema:lax-validation-error"]


def test_lax_validation_allows_unknown_open_content(tmp_path) -> None:
    defs_path = tmp_path / "defs.xsd"
    _write_lax_defs(defs_path)
    xml_path = tmp_path / "input.xml"
    xml_path.write_text(
        """<root xmlns:lax="http://example.com/lax"
                 xmlns:other="http://example.com/other"
                 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xsi:schemaLocation="http://example.com/lax defs.xsd">
  <other:unknownElement>not checked in lax mode</other:unknownElement>
</root>
""",
        encoding="utf-8",
    )

    assert validate_lax_known_declarations((xml_path,)) == ()


def test_lax_validation_reports_known_integer_attribute(tmp_path) -> None:
    defs_path = tmp_path / "defs.xsd"
    _write_lax_defs(defs_path)
    xml_path = tmp_path / "input.xml"
    xml_path.write_text(
        """<root xmlns:lax="http://example.com/lax"
                 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                 xsi:schemaLocation="http://example.com/lax defs.xsd"
                 lax:integerAttribute="not an integer"/>
""",
        encoding="utf-8",
    )

    findings = validate_lax_known_declarations((xml_path,))

    assert [finding.rule_id for finding in findings] == ["xmlschema:lax-validation-error"]


def test_lax_validation_checks_xml_language_and_space(tmp_path) -> None:
    xml_path = tmp_path / "input.xml"
    xml_path.write_text(
        """<root xml:lang="x-startrek-klingonian" xml:space="bad"/>""",
        encoding="utf-8",
    )

    findings = validate_lax_known_declarations((xml_path,))

    assert [finding.rule_id for finding in findings] == [
        "xmlschema:lax-validation-error",
        "xmlschema:lax-validation-error",
    ]


def test_lax_validation_reports_known_element_in_linkbase_content(tmp_path) -> None:
    defs_path = tmp_path / "defs.xsd"
    _write_lax_defs(defs_path)
    xml_path = tmp_path / "linkbase.xml"
    xml_path.write_text(
        """<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
                  xmlns:xlink="http://www.w3.org/1999/xlink"
                  xmlns:lax="http://example.com/lax"
                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                  xsi:schemaLocation="http://example.com/lax defs.xsd">
  <link:labelLink xlink:type="extended">
    <lax:stringElement>declared but not allowed here</lax:stringElement>
  </link:labelLink>
</link:linkbase>
""",
        encoding="utf-8",
    )

    findings = validate_lax_known_declarations((xml_path,))

    assert [finding.rule_id for finding in findings] == ["xmlschema:lax-validation-error"]


def test_xlink_allows_duplicate_role_refs_in_different_linkbases(tmp_path) -> None:
    xml_path = tmp_path / "different-linkbases.xsd"
    _write_xml(
        xml_path,
        """
      <link:linkbase>
        <link:roleRef xlink:type="simple" xlink:href="#role" roleURI="http://example.com/role"/>
        <link:definitionLink xlink:type="extended">
          <link:loc xlink:type="locator" xlink:href="#source" xlink:label="source"/>
        </link:definitionLink>
      </link:linkbase>
      <link:linkbase>
        <link:roleRef xlink:type="simple" xlink:href="#role" roleURI="http://example.com/role"/>
        <link:definitionLink xlink:type="extended">
          <link:loc xlink:type="locator" xlink:href="#target" xlink:label="target"/>
        </link:definitionLink>
      </link:linkbase>
""",
    )

    assert _validate_xlink_file(xml_path) == []


def test_xlink_reports_duplicate_role_refs_in_same_linkbase(tmp_path) -> None:
    xml_path = tmp_path / "duplicate-role-ref.xsd"
    _write_xml(
        xml_path,
        """
      <link:linkbase>
        <link:roleRef xlink:type="simple" xlink:href="#role" roleURI="http://example.com/role"/>
        <link:roleRef xlink:type="simple" xlink:href="#role" roleURI="http://example.com/role"/>
      </link:linkbase>
""",
    )

    findings = _validate_xlink_file(xml_path)

    assert [finding.rule_id for finding in findings] == ["xbrl:duplicate-role-ref"]


def test_xlink_reports_duplicate_arcrole_refs_in_same_linkbase(tmp_path) -> None:
    xml_path = tmp_path / "duplicate-arcrole-ref.xsd"
    _write_xml(
        xml_path,
        """
      <link:linkbase>
        <link:arcroleRef xlink:type="simple" xlink:href="#arcrole" arcroleURI="http://example.com/arcrole"/>
        <link:arcroleRef xlink:type="simple" xlink:href="#arcrole" arcroleURI="http://example.com/arcrole"/>
      </link:linkbase>
""",
    )

    findings = _validate_xlink_file(xml_path)

    assert [finding.rule_id for finding in findings] == ["xbrl:duplicate-arcrole-ref"]


def test_linkbase_ref_role_must_match_target_linkbase_type(tmp_path) -> None:
    _write_linkbase(tmp_path / "references.xml", "referenceLink")
    xml_path = tmp_path / "schema.xsd"
    _write_xml(
        xml_path,
        """
      <link:linkbaseRef xlink:type="simple"
                        xlink:href="references.xml"
                        xlink:role="http://www.xbrl.org/2003/role/labelLinkbaseRef"
                        xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"/>
""",
    )

    findings = _validate_xlink_file(xml_path)

    assert [finding.rule_id for finding in findings] == ["xbrl:linkbase-reference-error"]


def test_linkbase_ref_uses_xml_base_when_resolving_target(tmp_path) -> None:
    base_dir = tmp_path / "base"
    base_dir.mkdir()
    _write_linkbase(base_dir / "labels.xml", "labelLink")
    xml_path = tmp_path / "schema.xsd"
    _write_xml(
        xml_path,
        """
      <link:linkbaseRef xlink:type="simple"
                        xml:base="base/"
                        xlink:href="labels.xml"
                        xlink:role="http://www.xbrl.org/2003/role/labelLinkbaseRef"
                        xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"/>
""",
    )

    assert _validate_xlink_file(xml_path) == []


# ---------------------------------------------------------------------------
# Formula input linkbase merge
# ---------------------------------------------------------------------------


def test_input_formula_linkbases_merge_custom_function_signatures(tmp_path) -> None:
    formula_path = tmp_path / "formula.xml"
    formula_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:generic="http://xbrl.org/2008/generic"
               xmlns:formula="http://xbrl.org/2008/formula"
               xmlns:xlink="http://www.w3.org/1999/xlink"
               xmlns:my-fn="http://example.com/functions">
  <generic:link xlink:type="extended">
    <formula:formula xlink:type="resource"
                     xlink:label="formula"
                     value="my-fn:add(1, 2)"
                     aspectModel="dimensional"
                     implicitFiltering="true"/>
  </generic:link>
</link:linkbase>
""",
        encoding="utf-8",
    )
    function_path = tmp_path / "functions.xml"
    function_path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:generic="http://xbrl.org/2008/generic"
               xmlns:variable="http://xbrl.org/2008/variable"
               xmlns:cfi="http://xbrl.org/2010/custom-function"
               xmlns:xlink="http://www.w3.org/1999/xlink"
               xmlns:xs="http://www.w3.org/2001/XMLSchema"
               xmlns:my-fn="http://example.com/functions">
  <generic:link xlink:type="extended">
    <variable:function xlink:type="resource"
                       xlink:label="add-signature"
                       name="my-fn:add"
                       output="xs:decimal">
      <variable:input type="xs:decimal"/>
      <variable:input type="xs:decimal"/>
    </variable:function>
    <generic:arc xlink:type="arc"
                 xlink:arcrole="http://xbrl.org/arcrole/2010/function-implementation"
                 xlink:from="add-signature"
                 xlink:to="add-implementation"/>
    <cfi:implementation xlink:type="resource" xlink:label="add-implementation">
      <cfi:input name="left"/>
      <cfi:input name="right"/>
      <cfi:output>$left + $right</cfi:output>
    </cfi:implementation>
  </generic:link>
</link:linkbase>
""",
        encoding="utf-8",
    )

    taxonomy = _with_input_formula_linkbases(
        _empty_taxonomy(tmp_path),
        (formula_path, function_path),
    )

    assert [definition.name for definition in taxonomy.custom_functions] == ["my-fn:add"]
    assert "xbrlve:noCustomFunctionSignature" not in {
        finding.rule_id for finding in FormulaStaticValidator(taxonomy).validate()
    }


# ---------------------------------------------------------------------------
# VALID expected
# ---------------------------------------------------------------------------


def test_valid_no_findings_passes() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)
    outcome, codes = executor._match_outcome(expected, (), None)
    assert outcome == TestResultOutcome.PASS
    assert codes == ()


def test_valid_with_error_findings_fails() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)
    findings = (_error_finding("xbrl:someError"),)
    outcome, codes = executor._match_outcome(expected, findings, None, None)
    assert outcome == TestResultOutcome.FAIL
    assert "xbrl:someError" in codes


def test_formula_valid_ignores_s_equal_structural_and_calc_errors() -> None:
    """Formula suite VALID: duplicate-fact / summation-inconsistent are out of scope."""
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)
    findings = (
        ValidationFinding(
            rule_id="structural:duplicate-fact",
            severity=ValidationSeverity.ERROR,
            message="dup",
            source="structural",
        ),
        ValidationFinding(
            rule_id="calculation:summation-inconsistent",
            severity=ValidationSeverity.ERROR,
            message="calc",
            source="calculation",
        ),
    )
    outcome, codes = executor._match_outcome(expected, findings, None, "formula")
    assert outcome == TestResultOutcome.PASS
    assert codes == ()


def test_xbrl21_valid_ignores_duplicate_fact_product_finding() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)
    findings = (_error_finding("structural:duplicate-fact"),)
    outcome, codes = executor._match_outcome(expected, findings, None, "xbrl21")
    assert outcome == TestResultOutcome.PASS
    assert codes == ()


def test_formula_valid_still_fails_on_other_structural_errors() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)
    findings = (_error_finding("structural:unresolved-context-ref"),)
    outcome, codes = executor._match_outcome(expected, findings, None, "formula")
    assert outcome == TestResultOutcome.FAIL
    assert "structural:unresolved-context-ref" in codes


def test_valid_with_load_error_fails() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)
    outcome, codes = executor._match_outcome(expected, (), ValueError("bad"))
    assert outcome == TestResultOutcome.FAIL


def test_valid_with_only_warnings_passes() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID)
    findings = (_warning_finding("xbrl:someWarning"),)
    outcome, codes = executor._match_outcome(expected, findings, None)
    assert outcome == TestResultOutcome.PASS


# ---------------------------------------------------------------------------
# ERROR expected (any error)
# ---------------------------------------------------------------------------


def test_error_any_with_error_finding_passes() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.ERROR, error_code=None)
    findings = (_error_finding("xbrl:someError"),)
    outcome, codes = executor._match_outcome(expected, findings, None)
    assert outcome == TestResultOutcome.PASS


def test_error_any_with_load_error_passes() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.ERROR, error_code=None)
    outcome, codes = executor._match_outcome(expected, (), RuntimeError("load failed"))
    assert outcome == TestResultOutcome.PASS


def test_error_any_with_no_errors_fails() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(outcome_type=ExpectedOutcomeType.ERROR, error_code=None)
    outcome, codes = executor._match_outcome(expected, (), None)
    assert outcome == TestResultOutcome.FAIL


# ---------------------------------------------------------------------------
# ERROR expected (specific code)
# ---------------------------------------------------------------------------


def test_error_code_matching_finding_passes() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(
        outcome_type=ExpectedOutcomeType.ERROR,
        error_code="xbrldte:HypercubeElementIsNotAbstractError",
    )
    findings = (_error_finding("xbrldte:HypercubeElementIsNotAbstractError"),)
    outcome, codes = executor._match_outcome(expected, findings, None)
    assert outcome == TestResultOutcome.PASS


def test_error_code_wrong_code_fails() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(
        outcome_type=ExpectedOutcomeType.ERROR,
        error_code="xbrldte:SomeSpecificError",
    )
    findings = (_error_finding("xbrldte:OtherError"),)
    outcome, codes = executor._match_outcome(expected, findings, None)
    assert outcome == TestResultOutcome.FAIL


def test_error_code_in_load_error_message_passes() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(
        outcome_type=ExpectedOutcomeType.ERROR,
        error_code="xbrldte:HypercubeElementIsNotAbstractError",
    )
    load_error = Exception("HypercubeElementIsNotAbstractError was raised")
    outcome, codes = executor._match_outcome(expected, (), load_error)
    assert outcome == TestResultOutcome.PASS


def test_error_code_no_match_anywhere_fails() -> None:
    executor = _make_executor()
    expected = ExpectedOutcome(
        outcome_type=ExpectedOutcomeType.ERROR,
        error_code="xbrldte:VerySpecificError",
    )
    outcome, codes = executor._match_outcome(expected, (), None)
    assert outcome == TestResultOutcome.FAIL


# ---------------------------------------------------------------------------
# Skip list
# ---------------------------------------------------------------------------


def test_skip_list_returns_skipped_result(tmp_path) -> None:
    from bde_xbrl_editor.conformance.models import (
        ExpectedOutcome,
        ExpectedOutcomeType,
        TestCase,
        TestVariation,
    )

    executor = TestCaseExecutor(
        TaxonomyCache(max_size=1),
        formula_skip_list=frozenset(["V-01"]),
    )
    variation = TestVariation(
        variation_id="V-01",
        name="Skipped",
        description=None,
        input_files=(),
        instance_file=None,
        taxonomy_file=None,
        expected_outcome=ExpectedOutcome(outcome_type=ExpectedOutcomeType.VALID),
        mandatory=True,
    )
    test_case = TestCase(
        test_case_id="TC-001",
        description="",
        source_file=tmp_path / "tc.xml",
        suite_id="formula",
        variations=(variation,),
    )
    result = executor.execute(variation, test_case)
    assert result.outcome == TestResultOutcome.SKIPPED
    assert result.duration_ms == 0

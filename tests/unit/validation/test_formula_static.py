"""Unit tests for Formula 1.0 static output-resource validation."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from bde_xbrl_editor.instance.models import (
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlContext,
    XbrlInstance,
)
from bde_xbrl_editor.taxonomy.linkbases.formula import parse_formula_linkbase
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    ConsistencyAssertionDefinition,
    CustomFunctionDefinition,
    ExistenceAssertionDefinition,
    FactVariableDefinition,
    FormulaAssertionSet,
    FormulaFilterResource,
    FormulaOutputDefinition,
    GeneralVariableDefinition,
    ParameterDefinition,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
    TypedDimensionFilter,
    ValueAssertionDefinition,
    XPathFilterDefinition,
)
from bde_xbrl_editor.validation.formula.static import (
    FormulaStaticValidator,
    collect_formula_external_variable_names,
    validate_assertion_severity_linkbases,
    validate_custom_function_linkbases,
    validate_generic_message_linkbases,
    validate_typed_dimension_equality_linkbases,
)
from bde_xbrl_editor.validation.models import ValidationSeverity

_NS = "http://example.com/formula"
_XBRLI = "http://www.xbrl.org/2003/instance"


class _FakeLabels:
    def get(self, *args, **kwargs):
        return None


def _concept(local: str, type_local: str, period_type: str = "instant") -> Concept:
    return Concept(
        qname=QName(_NS, local, "eg"),
        data_type=QName(_XBRLI, type_local, "xbrli"),
        period_type=period_type,  # type: ignore[arg-type]
    )


def _taxonomy(
    assertion_set: FormulaAssertionSet,
    custom_functions: tuple[CustomFunctionDefinition, ...] = (),
) -> TaxonomyStructure:
    return TaxonomyStructure(
        metadata=TaxonomyMetadata(
            name="Test",
            version="1.0",
            publisher="Example",
            entry_point_path=Path("test.xsd"),
            loaded_at=datetime(2026, 1, 1),
            declared_languages=("en",),
        ),
        concepts={
            QName(_NS, "assets", "eg"): _concept("assets", "monetaryItemType"),
            QName(_NS, "note", "eg"): _concept("note", "stringItemType", "duration"),
        },
        labels=_FakeLabels(),
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
        formula_assertion_set=assertion_set,
        custom_functions=custom_functions,
    )


def _taxonomy_with_custom_functions(
    custom_functions: tuple[CustomFunctionDefinition, ...],
) -> TaxonomyStructure:
    return TaxonomyStructure(
        metadata=TaxonomyMetadata(
            name="Test",
            version="1.0",
            publisher="Example",
            entry_point_path=Path("test.xsd"),
            loaded_at=datetime(2026, 1, 1),
            declared_languages=("en",),
        ),
        concepts={},
        labels=_FakeLabels(),
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
        formula_assertion_set=FormulaAssertionSet(),
        custom_functions=custom_functions,
    )


def _formula_set(tmp_path: Path, formula_body: str) -> FormulaAssertionSet:
    path = tmp_path / "static-analysis-formula.xml"
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:generic="http://xbrl.org/2008/generic"
               xmlns:formula="http://xbrl.org/2008/formula"
               xmlns:variable="http://xbrl.org/2008/variable"
               xmlns:cf="http://xbrl.org/2008/filter/concept"
               xmlns:xlink="http://www.w3.org/1999/xlink"
               xmlns:eg="{_NS}">
  <generic:link xlink:type="extended">
    <variable:factVariable xlink:type="resource" xlink:label="source_fact"/>
    <cf:conceptName xlink:type="resource" xlink:label="source_concept">
      <cf:concept><cf:qname>eg:assets</cf:qname></cf:concept>
    </cf:conceptName>
    {formula_body}
    <variable:variableArc xlink:type="arc"
                          xlink:from="formula1"
                          xlink:to="source_fact"
                          name="v:source"
                          xlink:arcrole="http://xbrl.org/arcrole/2008/variable-set"/>
    <variable:variableFilterArc xlink:type="arc"
                                xlink:from="source_fact"
                                xlink:to="source_concept"
                                xlink:arcrole="http://xbrl.org/arcrole/2008/variable-filter"/>
  </generic:link>
</link:linkbase>
""",
        encoding="utf-8",
    )
    return parse_formula_linkbase(path)


def _rule_ids(assertion_set: FormulaAssertionSet) -> set[str]:
    return {
        finding.rule_id for finding in FormulaStaticValidator(_taxonomy(assertion_set)).validate()
    }


def test_static_parser_binds_standard_prefix_defaults() -> None:
    assertion = ValueAssertionDefinition(
        assertion_id="assertion1",
        label="assertion1",
        severity="error",
        abstract=False,
        variables=(),
        parameters=(),
        preconditions=(),
        test_xpath="exists(link:schemaRef) or exists(xbrli:context)",
        namespaces={},
    )

    assert "err:XPST0081" not in _rule_ids(FormulaAssertionSet(assertions=(assertion,)))


def test_formula_static_validation_rejects_prohibited_custom_function_namespace() -> None:
    taxonomy = _taxonomy_with_custom_functions(
        (
            CustomFunctionDefinition(
                name="xfi:function",
                namespace="http://www.xbrl.org/2008/function/instance",
                local_name="function",
                prefix="xfi",
                input_names=("arg1",),
                input_types=("xs:string",),
                output_type="xs:string",
            ),
        )
    )

    findings = FormulaStaticValidator(taxonomy).validate()

    assert any(
        finding.rule_id == "xbrlve:noProhibitedNamespaceForCustomFunction"
        for finding in findings
    )


def test_formula_static_validation_rejects_consistency_assertion_variables() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ConsistencyAssertionDefinition(
                assertion_id="consistency1",
                label="consistency1",
                severity="error",
                abstract=False,
                variables=(
                    FactVariableDefinition(
                        variable_name="v:fact",
                        bind_as_sequence=False,
                    ),
                ),
            ),
        )
    )

    assert "xbrlcae:variablesNotAllowed" in _rule_ids(assertion_set)


def test_formula_static_validation_rejects_conflicting_consistency_acceptance_radii() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ConsistencyAssertionDefinition(
                assertion_id="consistency1",
                label="consistency1",
                severity="error",
                abstract=False,
                variables=(),
                absolute_radius=Decimal("100"),
                relative_radius=Decimal("0.005"),
            ),
        )
    )

    assert "xbrlcae:acceptanceRadiusConflict" in _rule_ids(assertion_set)


def test_formula_static_validation_rejects_existence_assertion_fact_reference() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ExistenceAssertionDefinition(
                assertion_id="existence1",
                label="existence1",
                severity="error",
                abstract=False,
                variables=(
                    FactVariableDefinition(
                        variable_name="v:fact",
                        bind_as_sequence=False,
                    ),
                ),
                test_xpath="string-length($v:fact) ge 3",
                namespaces={"v": "http://example.com/variables"},
            ),
        )
    )

    assert "xbrleae:variableReferenceNotAllowed" in _rule_ids(assertion_set)


def test_formula_static_validation_rejects_inconsistent_aspect_cover_filters() -> None:
    variable = FactVariableDefinition(
        variable_name="v:fact",
        filter_resources=(
            FormulaFilterResource(
                label="unit-covered",
                namespace="http://xbrl.org/2010/filter/aspect-cover",
                local_name="aspectCover",
                cover=True,
                aspects=("unit",),
            ),
            FormulaFilterResource(
                label="unit-uncovered",
                namespace="http://xbrl.org/2010/filter/aspect-cover",
                local_name="aspectCover",
                cover=False,
                aspects=("unit",),
            ),
        ),
    )
    assertion_set = FormulaAssertionSet(
        output_formulas=(
            FormulaOutputDefinition(
                formula_id="f1",
                label="f1",
                value_xpath="1",
                source=None,
                aspect_model="dimensional",
                implicit_filtering=True,
                variables=(variable,),
            ),
        )
    )

    assert "xbrlacfe:inconsistentAspectCoverFilters" in _rule_ids(assertion_set)


def test_formula_static_validation_allows_matched_sequence_with_covered_period() -> None:
    variable = FactVariableDefinition(
        variable_name="v:facts",
        concept_filter=QName(_NS, "assets", "eg"),
        bind_as_sequence=True,
        matches=True,
        filter_resources=(
            FormulaFilterResource(
                label="period-covered",
                namespace="http://xbrl.org/2010/filter/aspect-cover",
                local_name="aspectCover",
                cover=True,
                aspects=("period",),
            ),
        ),
    )
    assertion_set = FormulaAssertionSet(
        output_formulas=(
            FormulaOutputDefinition(
                formula_id="f1",
                label="f1",
                value_xpath="sum($v:facts)",
                source=None,
                aspect_model="non-dimensional",
                implicit_filtering=True,
                variables=(variable,),
                namespaces={"v": "http://example.com/variables"},
            ),
        )
    )
    instance = XbrlInstance(
        taxonomy_entry_point=Path("test.xsd"),
        schema_ref_href="test.xsd",
        entity=ReportingEntity(identifier="ENT1", scheme="http://example.com"),
        period=ReportingPeriod(period_type="instant", instant_date=date(2026, 1, 1)),
    )
    instance.contexts["ctx1"] = XbrlContext(
        context_id="ctx1",
        entity=instance.entity,
        period=ReportingPeriod(period_type="instant", instant_date=date(2026, 1, 1)),
    )
    instance.contexts["ctx2"] = XbrlContext(
        context_id="ctx2",
        entity=instance.entity,
        period=ReportingPeriod(period_type="instant", instant_date=date(2026, 2, 1)),
    )
    instance.facts.extend(
        (
            Fact(
                concept=QName(_NS, "assets", "eg"),
                context_ref="ctx1",
                unit_ref=None,
                value="1",
            ),
            Fact(
                concept=QName(_NS, "assets", "eg"),
                context_ref="ctx2",
                unit_ref=None,
                value="2",
            ),
        )
    )

    findings = FormulaStaticValidator(_taxonomy(assertion_set)).validate(instance)

    assert "xbrlmfe:inconsistentMatchedVariableSequence" not in {
        finding.rule_id for finding in findings
    }


def _severity_linkbase(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "severity-formula.xml"
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:generic="http://xbrl.org/2008/generic"
               xmlns:va="http://xbrl.org/2008/assertion/value"
               xmlns:label="http://xbrl.org/2008/label"
               xmlns:xlink="http://www.w3.org/1999/xlink">
  <generic:link xlink:type="extended">
    <va:valueAssertion xlink:type="resource" xlink:label="assertion1" id="assertion1" test="true()"/>
    {body}
  </generic:link>
</link:linkbase>
""",
        encoding="utf-8",
    )
    return path


def _severity_rule_ids(path: Path) -> set[str]:
    return {finding.rule_id for finding in validate_assertion_severity_linkbases((path,))}


def test_assertion_severity_validation_reports_bad_source(tmp_path: Path) -> None:
    path = _severity_linkbase(
        tmp_path,
        """
    <link:loc xlink:type="locator" xlink:label="sev" xlink:href="http://www.xbrl.org/2016/severities.xml#ERROR"/>
    <label:label xlink:type="resource" xlink:label="wrong">Wrong source</label:label>
    <generic:arc xlink:type="arc"
                 xlink:arcrole="http://xbrl.org/arcrole/2016/assertion-unsatisfied-severity"
                 xlink:from="wrong" xlink:to="sev"/>
""",
    )

    assert "seve:assertionSeveritySourceError" in _severity_rule_ids(path)


def test_assertion_severity_validation_reports_bad_target(tmp_path: Path) -> None:
    path = _severity_linkbase(
        tmp_path,
        """
    <label:label xlink:type="resource" xlink:label="wrong">Wrong target</label:label>
    <generic:arc xlink:type="arc"
                 xlink:arcrole="http://xbrl.org/arcrole/2016/assertion-unsatisfied-severity"
                 xlink:from="assertion1" xlink:to="wrong"/>
""",
    )

    assert "seve:assertionSeverityTargetError" in _severity_rule_ids(path)


def test_assertion_severity_validation_reports_multiple_targets(tmp_path: Path) -> None:
    path = _severity_linkbase(
        tmp_path,
        """
    <link:loc xlink:type="locator" xlink:label="error" xlink:href="http://www.xbrl.org/2016/severities.xml#ERROR"/>
    <link:loc xlink:type="locator" xlink:label="ok" xlink:href="http://www.xbrl.org/2016/severities.xml#OK"/>
    <generic:arc xlink:type="arc"
                 xlink:arcrole="http://xbrl.org/arcrole/2016/assertion-unsatisfied-severity"
                 xlink:from="assertion1" xlink:to="error"/>
    <generic:arc xlink:type="arc"
                 xlink:arcrole="http://xbrl.org/arcrole/2016/assertion-unsatisfied-severity"
                 xlink:from="assertion1" xlink:to="ok"/>
""",
    )

    assert "seve:multipleSeveritiesForAssertionError" in _severity_rule_ids(path)


def _message_linkbase(
    tmp_path: Path,
    message_text: str,
    *,
    assertion_tag: str = "va:valueAssertion",
    implicit_filtering: bool = True,
) -> Path:
    path = tmp_path / "message-formula.xml"
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:generic="http://xbrl.org/2008/generic"
               xmlns:va="http://xbrl.org/2008/assertion/value"
               xmlns:ea="http://xbrl.org/2008/assertion/existence"
               xmlns:variable="http://xbrl.org/2008/variable"
               xmlns:msg="http://xbrl.org/2010/message"
               xmlns:xlink="http://www.w3.org/1999/xlink"
               xmlns:xff="http://www.xbrl.org/2010/function/formula">
  <generic:link xlink:type="extended">
    <{assertion_tag} xlink:type="resource"
                     xlink:label="assertion1"
                     id="assertion1"
                     implicitFiltering="{str(implicit_filtering).lower()}"
                     test="$var = 1"/>
    <msg:message xlink:type="resource"
                 xlink:label="message1"
                 xlink:role="http://www.xbrl.org/2010/role/message"
                 xml:lang="en">{message_text}</msg:message>
    <generic:arc xlink:type="arc"
                 xlink:arcrole="http://xbrl.org/arcrole/2010/assertion-unsatisfied-message"
                 xlink:from="assertion1"
                 xlink:to="message1"/>
    <variable:factVariable xlink:type="resource" xlink:label="fact1"/>
    <variable:variableArc xlink:type="arc"
                          xlink:arcrole="http://xbrl.org/arcrole/2008/variable-set"
                          xlink:from="assertion1"
                          xlink:to="fact1"
                          name="var"/>
  </generic:link>
</link:linkbase>
""",
        encoding="utf-8",
    )
    return path


def _message_rule_ids(path: Path) -> set[str]:
    return {finding.rule_id for finding in validate_generic_message_linkbases((path,))}


def test_generic_message_validation_reports_unknown_variable(tmp_path: Path) -> None:
    path = _message_linkbase(tmp_path, "Bad variable { node-name($missing) }")

    assert "xqt-err:XPST0008" in _message_rule_ids(path)


def test_generic_message_validation_reports_missing_right_brace(tmp_path: Path) -> None:
    path = _message_linkbase(tmp_path, "Missing right { 'abc' ")

    assert "xbrlmsge:missingRightCurlyBracketInMessage" in _message_rule_ids(path)


def test_generic_message_validation_reports_missing_left_brace(tmp_path: Path) -> None:
    path = _message_linkbase(tmp_path, "Missing left 'abc' }")

    assert "xbrlmsge:missingLeftCurlyBracketInMessage" in _message_rule_ids(path)


def test_generic_message_validation_reports_existence_assertion_variable_reference(
    tmp_path: Path,
) -> None:
    path = _message_linkbase(
        tmp_path,
        "Existence assertion message { node-name($var) }",
        assertion_tag="ea:existenceAssertion",
    )

    assert "xqt-err:XPST0008" in _message_rule_ids(path)


def test_generic_message_validation_reports_invalid_uncovered_aspect_use(
    tmp_path: Path,
) -> None:
    path = _message_linkbase(
        tmp_path,
        "Bad uncovered aspect { xff:uncovered-aspect(xs:token('concept')) }",
        implicit_filtering=False,
    )

    assert "xffe:invalidFunctionUse" in _message_rule_ids(path)


def _custom_function_linkbase(
    tmp_path: Path,
    body: str,
    filename: str = "custom-function-formula.xml",
) -> Path:
    path = tmp_path / filename
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:generic="http://xbrl.org/2008/generic"
               xmlns:formula="http://xbrl.org/2008/formula"
               xmlns:variable="http://xbrl.org/2008/variable"
               xmlns:cfi="http://xbrl.org/2010/custom-function"
               xmlns:my-fn="http://example.com/functions"
               xmlns:xbrli="http://www.xbrl.org/2003/instance"
               xmlns:xs="http://www.w3.org/2001/XMLSchema"
               xmlns:xlink="http://www.w3.org/1999/xlink">
  <generic:link xlink:type="extended">
    {body}
  </generic:link>
</link:linkbase>
""",
        encoding="utf-8",
    )
    return path


def _custom_function_rule_ids(path: Path) -> set[str]:
    return {finding.rule_id for finding in validate_custom_function_linkbases((path,))}


def _custom_function_rule_ids_for(paths: tuple[Path, ...]) -> set[str]:
    return {finding.rule_id for finding in validate_custom_function_linkbases(paths)}


def _typed_dimension_equality_rule_ids(paths: tuple[Path, ...]) -> set[str]:
    return {finding.rule_id for finding in validate_typed_dimension_equality_linkbases(paths)}


def test_typed_dimension_equality_validation_reports_duplicate_domain(
    tmp_path: Path,
) -> None:
    path = tmp_path / "typed-dimension-aspectTest.xml"
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:generic="http://xbrl.org/2008/generic"
               xmlns:variable="http://xbrl.org/2008/variable"
               xmlns:xlink="http://www.w3.org/1999/xlink">
  <generic:link xlink:type="extended">
    <link:loc xlink:type="locator" xlink:label="domain" xlink:href="typed.xsd#dimVal"/>
    <variable:equalityDefinition xlink:type="resource" xlink:label="test1" test="true()"/>
    <variable:equalityDefinition xlink:type="resource" xlink:label="test2" test="true()"/>
    <generic:arc xlink:type="arc"
                 xlink:arcrole="http://xbrl.org/arcrole/2008/equality-definition"
                 xlink:from="domain" xlink:to="test1"/>
    <generic:arc xlink:type="arc"
                 xlink:arcrole="http://xbrl.org/arcrole/2008/equality-definition"
                 xlink:from="domain" xlink:to="test2"/>
  </generic:link>
</link:linkbase>
""",
        encoding="utf-8",
    )

    assert "xbrlve:multipleTypedDimensionEqualityDefinitions" in (
        _typed_dimension_equality_rule_ids((path,))
    )


def test_custom_function_validation_reports_input_mismatch(tmp_path: Path) -> None:
    path = _custom_function_linkbase(
        tmp_path,
        """
    <variable:function xlink:type="resource" xlink:label="sig" name="my-fn:a" output="xs:decimal">
      <variable:input type="schema-element(xbrli:item)"/>
      <variable:input type="schema-element(xbrli:item)"/>
    </variable:function>
    <cfi:implementation xlink:type="resource" xlink:label="impl">
      <cfi:input name="a"/>
      <cfi:output>$a</cfi:output>
    </cfi:implementation>
    <generic:arc xlink:type="arc"
                 xlink:arcrole="http://xbrl.org/arcrole/2010/function-implementation"
                 xlink:from="sig" xlink:to="impl"/>
""",
    )

    assert "xbrlcfie:inputMismatch" in _custom_function_rule_ids(path)


def test_custom_function_validation_reports_too_many_relationships(tmp_path: Path) -> None:
    path = _custom_function_linkbase(
        tmp_path,
        """
    <variable:function xlink:type="resource" xlink:label="sig" name="my-fn:a" output="xs:decimal">
      <variable:input type="schema-element(xbrli:item)"/>
    </variable:function>
    <cfi:implementation xlink:type="resource" xlink:label="impl1">
      <cfi:input name="a"/>
      <cfi:output>$a</cfi:output>
    </cfi:implementation>
    <cfi:implementation xlink:type="resource" xlink:label="impl2">
      <cfi:input name="a"/>
      <cfi:output>$a</cfi:output>
    </cfi:implementation>
    <generic:arc xlink:type="arc"
                 xlink:arcrole="http://xbrl.org/arcrole/2010/function-implementation"
                 xlink:from="sig" xlink:to="impl1"/>
    <generic:arc xlink:type="arc"
                 xlink:arcrole="http://xbrl.org/arcrole/2010/function-implementation"
                 xlink:from="sig" xlink:to="impl2"/>
""",
    )

    assert "xbrlcfie:tooManyCFIRelationships" in _custom_function_rule_ids(path)


def test_custom_function_validation_reports_missing_relationship(tmp_path: Path) -> None:
    path = _custom_function_linkbase(
        tmp_path,
        """
    <cfi:implementation xlink:type="resource" xlink:label="orphan">
      <cfi:input name="a"/>
      <cfi:output>$a</cfi:output>
    </cfi:implementation>
""",
    )

    assert "xbrlcfie:missingCFIRelationship" in _custom_function_rule_ids(path)


def test_custom_function_validation_reports_used_signature_without_implementation(
    tmp_path: Path,
) -> None:
    path = _custom_function_linkbase(
        tmp_path,
        """
    <link:arcroleRef arcroleURI="http://xbrl.org/arcrole/2010/function-implementation"
                 xlink:href="http://www.xbrl.org/2010/custom-function-implementation.xsd#cfi-implementation"
                 xlink:type="simple"/>
    <formula:formula xlink:type="resource" xlink:label="formula1" value="my-fn:a($b)"/>
    <variable:function xlink:type="resource" xlink:label="sig" name="my-fn:a" output="xs:decimal">
      <variable:input type="schema-element(xbrli:item)"/>
    </variable:function>
""",
    )

    assert "err:XPST0017" in _custom_function_rule_ids(path)


def test_custom_function_validation_allows_processor_implemented_signature(
    tmp_path: Path,
) -> None:
    path = _custom_function_linkbase(
        tmp_path,
        """
    <formula:formula xlink:type="resource" xlink:label="formula1" value="my-fn:a($b)"/>
    <variable:function xlink:type="resource" xlink:label="sig" name="my-fn:a" output="xs:decimal">
      <variable:input type="schema-element(xbrli:item)"/>
    </variable:function>
""",
    )

    assert "err:XPST0017" not in _custom_function_rule_ids(path)


def test_custom_function_validation_resolves_locator_implementation(
    tmp_path: Path,
) -> None:
    formula_path = _custom_function_linkbase(
        tmp_path,
        """
    <variable:function xlink:type="resource" xlink:label="sig" name="my-fn:a" output="xs:decimal">
      <variable:input type="schema-element(xbrli:item)"/>
    </variable:function>
    <link:loc xlink:type="locator" xlink:href="implementation.xml#impl" xlink:label="impl-loc"/>
    <generic:arc xlink:type="arc"
                 xlink:arcrole="http://xbrl.org/arcrole/2010/function-implementation"
                 xlink:from="sig" xlink:to="impl-loc"/>
""",
        filename="formula.xml",
    )
    implementation_path = _custom_function_linkbase(
        tmp_path,
        """
    <cfi:implementation xlink:type="resource" xlink:label="impl" id="impl">
      <cfi:input name="a"/>
      <cfi:output>$a</cfi:output>
    </cfi:implementation>
""",
        filename="implementation.xml",
    )

    assert "xbrlcfie:missingCFIRelationship" not in _custom_function_rule_ids_for(
        (formula_path, implementation_path)
    )


def test_duplicate_inherited_global_parameters_do_not_name_clash() -> None:
    global_parameter = ParameterDefinition(
        parameter_name="RepEntity",
        scope="global",
        namespaces={},
    )
    assertion = ValueAssertionDefinition(
        assertion_id="assertion1",
        label="assertion1",
        severity="error",
        abstract=False,
        variables=(),
        parameters=(global_parameter, global_parameter),
        preconditions=(),
        test_xpath="true()",
        namespaces={},
    )
    assertion_set = FormulaAssertionSet(
        assertions=(assertion,),
        global_parameters=(global_parameter,),
    )

    assert "xbrlve:parameterNameClash" not in _rule_ids(assertion_set)


def test_formula_static_validation_reports_missing_output_concept(tmp_path) -> None:
    assertion_set = _formula_set(
        tmp_path,
        """
    <formula:formula xlink:type="resource" xlink:label="formula1" value="1">
      <formula:aspects>
        <formula:entityIdentifier scheme="'scheme'" value="'entity'"/>
        <formula:period><formula:instant value="xs:date('2026-01-01')"/></formula:period>
      </formula:aspects>
    </formula:formula>
""",
    )

    assert "xbrlfe:missingConceptRule" in _rule_ids(assertion_set)


def test_formula_static_validation_reports_missing_unit_for_numeric_concept(tmp_path) -> None:
    assertion_set = _formula_set(
        tmp_path,
        """
    <formula:formula xlink:type="resource" xlink:label="formula1" value="1">
      <formula:aspects>
        <formula:concept><formula:qname>eg:assets</formula:qname></formula:concept>
        <formula:entityIdentifier scheme="'scheme'" value="'entity'"/>
        <formula:period><formula:instant value="xs:date('2026-01-01')"/></formula:period>
      </formula:aspects>
    </formula:formula>
""",
    )

    assert "xbrlfe:missingUnitRule" in _rule_ids(assertion_set)


def test_formula_static_validation_reports_unknown_source_variable(tmp_path) -> None:
    assertion_set = _formula_set(
        tmp_path,
        """
    <formula:formula xlink:type="resource" xlink:label="formula1" value="1" source="eg:assets"/>
""",
    )

    assert "xbrlfe:nonexistentSourceVariable" in _rule_ids(assertion_set)


def test_formula_static_validation_allows_formula_uncovered_source(tmp_path) -> None:
    assertion_set = _formula_set(
        tmp_path,
        """
    <formula:formula xlink:type="resource" xlink:label="formula1" value="1" source="formula:uncovered">
      <formula:aspects>
        <formula:concept><formula:qname>eg:assets</formula:qname></formula:concept>
      </formula:aspects>
    </formula:formula>
""",
    )

    assert "xbrlfe:nonexistentSourceVariable" not in _rule_ids(assertion_set)


def test_formula_static_validation_reports_conflicting_unit_for_non_numeric_concept(
    tmp_path,
) -> None:
    assertion_set = _formula_set(
        tmp_path,
        """
    <formula:formula xlink:type="resource" xlink:label="formula1" value="1" source="v:source">
      <formula:aspects>
        <formula:concept><formula:qname>eg:note</formula:qname></formula:concept>
        <formula:unit/>
      </formula:aspects>
    </formula:formula>
""",
    )

    assert "xbrlfe:conflictingAspectRules" in _rule_ids(assertion_set)


def test_formula_static_validation_reports_invalid_output_value_xpath() -> None:
    assertion_set = FormulaAssertionSet(
        output_formulas=(
            FormulaOutputDefinition(
                formula_id="formula1",
                label=None,
                value_xpath="count($v:c1))",
                source="v:c1",
                aspect_model="non-dimensional",
                implicit_filtering=True,
                namespaces={"v": "http://example.com/vars"},
            ),
        )
    )

    assert "err:XPST0003" in _rule_ids(assertion_set)


def test_formula_static_validation_reports_undeclared_output_value_xpath_prefix() -> None:
    assertion_set = FormulaAssertionSet(
        output_formulas=(
            FormulaOutputDefinition(
                formula_id="formula1",
                label=None,
                value_xpath="$missing:var + 1",
                source=None,
                aspect_model="non-dimensional",
                implicit_filtering=True,
                namespaces={},
            ),
        )
    )

    assert "err:XPST0081" in _rule_ids(assertion_set)


def test_formula_static_validation_reports_duplicate_variable_names() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(
                    FactVariableDefinition(variable_name="dup"),
                    FactVariableDefinition(variable_name="dup"),
                ),
                test_xpath="true()",
            ),
        )
    )
    assert "xbrlve:duplicateVariableNames" in _rule_ids(assertion_set)


def test_formula_static_validation_reports_missing_custom_function_name() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(),
                test_xpath="fext:EsNoResidenteVigente($code)",
                namespaces={"fext": "http://www.bde.es/xbrl/func/external-functions"},
            ),
        )
    )

    findings = FormulaStaticValidator(_taxonomy(assertion_set)).validate()

    assert findings[0].rule_id == "xbrlve:noCustomFunctionSignature"
    assert "fext:EsNoResidenteVigente" in findings[0].message


def test_formula_static_validation_accepts_declared_iaf_numeric_subtract() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(),
                test_xpath="iaf:numeric-equal($a, iaf:numeric-subtract($b, $c))",
                namespaces={
                    "iaf": "http://www.eurofiling.info/xbrl/func/interval-arithmetics",
                },
            ),
        )
    )
    custom_functions = (
        CustomFunctionDefinition(
            name="iaf:numeric-subtract",
            namespace="http://www.eurofiling.info/xbrl/func/interval-arithmetics",
            local_name="numeric-subtract",
            prefix="iaf",
            input_names=("paramA", "paramB"),
            input_types=("item()", "item()"),
            output_type="item()",
        ),
    )

    findings = FormulaStaticValidator(
        _taxonomy(assertion_set, custom_functions=custom_functions)
    ).validate()

    assert "xbrlve:noCustomFunctionSignature" not in {finding.rule_id for finding in findings}


def test_formula_static_validation_reports_unresolved_and_cycle_dependencies() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(FactVariableDefinition(variable_name="fact", referenced_names=("missing",)),),
                general_variables=(
                    GeneralVariableDefinition(
                        variable_name="g1",
                        select_xpath="$g2",
                        referenced_names=("g2",),
                    ),
                    GeneralVariableDefinition(
                        variable_name="g2",
                        select_xpath="$g1",
                        referenced_names=("g1",),
                    ),
                ),
                test_xpath="$g1 = 1",
                referenced_names=("g1",),
            ),
        )
    )
    codes = _rule_ids(assertion_set)
    assert "xbrlve:unresolvedDependency" in codes
    assert "xbrlve:cyclicDependencies" in codes


def test_formula_static_validation_reports_parameter_clashes_and_parameter_cycles() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(FactVariableDefinition(variable_name="p"),),
                parameters=(
                    ParameterDefinition(
                        parameter_name="p",
                        select_xpath="$q",
                        referenced_names=("q",),
                        scope="local",
                    ),
                    ParameterDefinition(
                        parameter_name="q",
                        select_xpath="$p",
                        referenced_names=("p",),
                        scope="local",
                    ),
                ),
                test_xpath="true()",
            ),
        )
    )
    codes = _rule_ids(assertion_set)
    assert "xbrlve:parameterNameClash" in codes
    assert "xbrlve:parameterCyclicDependencies" in codes


def test_formula_static_validation_allows_global_parameter_name_to_overlap_fact_variable() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(FactVariableDefinition(variable_name="p"),),
                parameters=(
                    ParameterDefinition(
                        parameter_name="p",
                        select_xpath="'global'",
                        scope="global",
                    ),
                ),
                test_xpath="$p = 'fact'",
            ),
        )
    )

    assert "xbrlve:parameterNameClash" not in _rule_ids(assertion_set)


def test_formula_static_validation_allows_required_external_parameter_without_select() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(),
                parameters=(
                    ParameterDefinition(
                        parameter_name="mydate",
                        as_type="xs:date",
                        required=True,
                        scope="local",
                    ),
                ),
                test_xpath="true()",
            ),
        )
    )

    assert "xbrlve:parameterTypeMismatch" not in _rule_ids(assertion_set)


def test_formula_static_validation_reports_required_external_qname_parameter_mismatch() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(),
                parameters=(
                    ParameterDefinition(
                        parameter_name="name",
                        as_type="xs:QName",
                        required=True,
                        scope="local",
                    ),
                ),
                test_xpath="true()",
            ),
        )
    )

    assert "xbrlve:parameterTypeMismatch" in _rule_ids(assertion_set)


def test_formula_static_validation_rejects_fallback_referencing_fact_variable() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(
                    FactVariableDefinition(variable_name="n1"),
                    FactVariableDefinition(variable_name="n2", fallback_value="$n1 + 1"),
                ),
                test_xpath="true()",
            ),
        )
    )

    assert "xbrlve:fallbackValueVariableReferenceNotAllowed" in _rule_ids(assertion_set)


def test_formula_static_validation_rejects_fallback_referencing_general_variable() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(
                    FactVariableDefinition(variable_name="n1", fallback_value="$g1"),
                ),
                general_variables=(
                    GeneralVariableDefinition(variable_name="g1", select_xpath="1"),
                ),
                test_xpath="true()",
            ),
        )
    )

    assert "xbrlve:fallbackValueVariableReferenceNotAllowed" in _rule_ids(assertion_set)


def test_formula_static_validation_allows_fallback_referencing_parameter() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(FactVariableDefinition(variable_name="n1", fallback_value="$p1"),),
                parameters=(ParameterDefinition(parameter_name="p1", select_xpath="1"),),
                test_xpath="true()",
            ),
        )
    )

    assert "xbrlve:fallbackValueVariableReferenceNotAllowed" not in _rule_ids(assertion_set)


def test_formula_static_validation_reports_unknown_and_mismatched_aspect_model() -> None:
    assertion_set = FormulaAssertionSet(
        output_formulas=(
            FormulaOutputDefinition(
                formula_id="f1",
                label=None,
                value_xpath="1",
                source=None,
                aspect_model="unexpected",
                implicit_filtering=True,
            ),
            FormulaOutputDefinition(
                formula_id="f2",
                label=None,
                value_xpath="1",
                source=None,
                aspect_model="non-dimensional",
                implicit_filtering=True,
                variables=(
                    FactVariableDefinition(
                        variable_name="v",
                        typed_dimension_filters=(
                            TypedDimensionFilter(
                                dimension_qname=QName(_NS, "d1", "eg"),
                            ),
                        ),
                    ),
                ),
            ),
        )
    )
    codes = _rule_ids(assertion_set)
    assert "xbrlve:unknownAspectModel" in codes
    assert "xbrlve:filterAspectModelMismatch" in codes


def test_formula_static_validation_collects_external_variable_references() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(),
                test_xpath="$SucComunitaria and $TipoEntidad = 'B'",
                referenced_names=("SucComunitaria", "TipoEntidad"),
            ),
        )
    )

    assert collect_formula_external_variable_names(_taxonomy(assertion_set)) == (
        "SucComunitaria",
        "TipoEntidad",
    )


def test_formula_static_validation_treats_supplied_external_variables_as_known() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(),
                test_xpath="$SucComunitaria and $TipoEntidad = 'B'",
                referenced_names=("SucComunitaria", "TipoEntidad"),
            ),
        )
    )
    validator = FormulaStaticValidator(
        _taxonomy(assertion_set),
        external_variable_names={"SucComunitaria", "TipoEntidad"},
    )

    assert "xbrlve:unresolvedDependency" not in {f.rule_id for f in validator.validate()}


def test_formula_static_validation_ignores_flwor_local_variable_references() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(FactVariableDefinition(variable_name="fact"),),
                test_xpath="for $x in (1, 2) return $x + $fact",
                referenced_names=("x", "fact"),
            ),
        )
    )

    assert "xbrlve:unresolvedDependency" not in _rule_ids(assertion_set)


def test_formula_static_validation_ignores_xpath_comment_variable_references() -> None:
    assertion_set = FormulaAssertionSet(
        output_formulas=(
            FormulaOutputDefinition(
                formula_id="f1",
                label=None,
                value_xpath="(: replaced $missing with a custom function :) $source + 1",
                source="source",
                aspect_model="non-dimensional",
                implicit_filtering=True,
                variables=(FactVariableDefinition(variable_name="source"),),
            ),
        )
    )

    assert "xbrlve:unresolvedDependency" not in _rule_ids(assertion_set)


def test_formula_static_validation_ignores_filter_local_variable_references() -> None:
    assertion_set = FormulaAssertionSet(
        assertions=(
            ValueAssertionDefinition(
                assertion_id="a1",
                label=None,
                severity=ValidationSeverity.ERROR,
                abstract=False,
                variables=(
                    FactVariableDefinition(
                        variable_name="fact",
                        referenced_names=("restatementDate", "restatementDateTime"),
                        xpath_filters=(
                            XPathFilterDefinition(
                                xpath_expr=(
                                    "for $restatementDate in (), "
                                    "$restatementDateTime in dateTime($restatementDate, "
                                    "xs:time('24:00:00')) return true()"
                                ),
                                namespaces={"xs": "http://www.w3.org/2001/XMLSchema"},
                            ),
                        ),
                    ),
                ),
                test_xpath="true()",
            ),
        )
    )

    assert "xbrlve:unresolvedDependency" not in _rule_ids(assertion_set)

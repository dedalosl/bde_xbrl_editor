"""Unit tests for isolated output-formula runtime evaluation."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from bde_xbrl_editor.instance.models import (
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlContext,
    XbrlInstance,
)
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    FactVariableDefinition,
    FormulaAssertionSet,
    FormulaFilterResource,
    FormulaOutputDefinition,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
    XPathFilterDefinition,
)
from bde_xbrl_editor.validation.formula.output_runtime import OutputFormulaRuntimeEvaluator

_NS = "http://example.com/tax"
_XBRLI_NS = "http://www.xbrl.org/2003/instance"


def _qn(local: str) -> QName:
    return QName(namespace=_NS, local_name=local)


def _concept(local: str, type_local: str) -> Concept:
    qname = _qn(local)
    return Concept(
        qname=qname,
        data_type=QName(_XBRLI_NS, type_local, "xbrli"),
        period_type="instant",
    )


def _taxonomy(
    formula: FormulaOutputDefinition,
    concepts: dict[QName, Concept] | None = None,
) -> TaxonomyStructure:
    return TaxonomyStructure(
        metadata=TaxonomyMetadata(
            name="Test",
            version="1.0",
            publisher="Example",
            entry_point_path=Path("tax.xsd"),
            loaded_at=datetime(2024, 1, 1),
            declared_languages=("en",),
        ),
        concepts=concepts or {},
        labels={},
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
        formula_assertion_set=FormulaAssertionSet(output_formulas=(formula,)),
        custom_functions=(),
    )


def _instance(value: str = "1") -> XbrlInstance:
    inst = XbrlInstance(
        taxonomy_entry_point=Path("tax.xsd"),
        schema_ref_href="tax.xsd",
        entity=ReportingEntity(identifier="ENT1", scheme="http://example.com"),
        period=ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31)),
    )
    inst.contexts["ctx1"] = XbrlContext(
        context_id="ctx1",
        entity=inst.entity,
        period=inst.period,
    )
    inst.facts.append(
        Fact(
            concept=_qn("Amount"),
            context_ref="ctx1",
            unit_ref=None,
            value=value,
        )
    )
    return inst


def test_output_runtime_evaluator_reports_xpath_runtime_error_code() -> None:
    formula = FormulaOutputDefinition(
        formula_id="f1",
        label=None,
        value_xpath="1 div 0",
        source=None,
        aspect_model=None,
        implicit_filtering=True,
        variables=(FactVariableDefinition(variable_name="a", concept_filter=_qn("Amount")),),
    )
    findings = OutputFormulaRuntimeEvaluator(_taxonomy(formula)).evaluate_runtime_errors(_instance())
    assert findings
    assert findings[0].rule_id == "err:FOAR0001"


def test_output_runtime_v07_xfi_period_then_divide_by_zero_foar() -> None:
    """22010 V-07: xfi:period on fact variable + minutes-from-dateTime + div by zero."""
    value_xpath = """
        if ( string-length( $v:c1 ) div
             minutes-from-dateTime( xfi:period-instant(xfi:period($v:c1)))
             eq 0 )
        then 'survived a divide by zero and got non-zero result'
        else 'survived a divide by zero and got zero result'
        """
    formula = FormulaOutputDefinition(
        formula_id="formula1",
        label=None,
        value_xpath=value_xpath,
        source=None,
        aspect_model=None,
        implicit_filtering=True,
        variables=(FactVariableDefinition(variable_name="v:c1", concept_filter=_qn("c1")),),
        namespaces={
            "v": "http://xbrl.org/2008/formula/conformance/variable",
        },
    )
    inst = XbrlInstance(
        taxonomy_entry_point=Path("tax.xsd"),
        schema_ref_href="tax.xsd",
        entity=ReportingEntity(identifier="ENT1", scheme="http://example.com"),
        period=ReportingPeriod(period_type="instant", instant_date=date(2007, 12, 31)),
    )
    inst.contexts["ctxt1"] = XbrlContext(
        context_id="ctxt1",
        entity=inst.entity,
        period=inst.period,
    )
    inst.facts.append(
        Fact(
            concept=_qn("c1"),
            context_ref="ctxt1",
            unit_ref=None,
            value="hello world",
        )
    )
    findings = OutputFormulaRuntimeEvaluator(_taxonomy(formula)).evaluate_runtime_errors(inst)
    assert findings
    assert findings[0].rule_id == "err:FOAR0001"


def test_output_runtime_evaluator_ignores_successful_output_formula() -> None:
    formula = FormulaOutputDefinition(
        formula_id="f1",
        label=None,
        value_xpath="$a + 1",
        source=None,
        aspect_model=None,
        implicit_filtering=True,
        variables=(FactVariableDefinition(variable_name="a", concept_filter=_qn("Amount")),),
    )
    findings = OutputFormulaRuntimeEvaluator(_taxonomy(formula)).evaluate_runtime_errors(_instance())
    assert findings == ()


def test_output_runtime_reports_invalid_filter_effective_boolean_value() -> None:
    formula = FormulaOutputDefinition(
        formula_id="formula1",
        label=None,
        value_xpath="$c1",
        source=None,
        aspect_model=None,
        implicit_filtering=True,
        variables=(
            FactVariableDefinition(
                variable_name="c1",
                xpath_filters=(
                    XPathFilterDefinition(
                        xpath_expr="QName('http://example.com/tax', 'eg:c1')",
                        filter_type="general",
                    ),
                ),
            ),
        ),
    )
    findings = OutputFormulaRuntimeEvaluator(_taxonomy(formula)).evaluate_runtime_errors(_instance())
    assert [finding.rule_id for finding in findings] == ["err:FORG0006"]


def test_output_runtime_reports_tuple_atomization_error_for_string_join_sequence() -> None:
    formula = FormulaOutputDefinition(
        formula_id="formula1",
        label=None,
        value_xpath="concat('hello ', string-join( $c1 | (), '') )",
        source=None,
        aspect_model=None,
        implicit_filtering=False,
        variables=(
            FactVariableDefinition(
                variable_name="c1",
                bind_as_sequence=True,
                filter_resources=(
                    FormulaFilterResource(
                        label="location",
                        namespace="http://xbrl.org/2008/filter/tuple",
                        local_name="ancestorFilter",
                    ),
                ),
            ),
        ),
    )
    findings = OutputFormulaRuntimeEvaluator(_taxonomy(formula)).evaluate_runtime_errors(_instance())
    assert [finding.rule_id for finding in findings] == ["err:FOTY0012"]


def test_output_runtime_reports_xqt_type_error_for_numeric_string_join_sequence() -> None:
    number = _concept("Number", "decimalItemType")
    formula = FormulaOutputDefinition(
        formula_id="formula1",
        label=None,
        value_xpath="concat('hello ', string-join( $v | (), '') )",
        source=None,
        aspect_model=None,
        implicit_filtering=False,
        variables=(
            FactVariableDefinition(
                variable_name="v",
                bind_as_sequence=True,
                filter_resources=(
                    FormulaFilterResource(
                        label="namefilter",
                        namespace="http://xbrl.org/2008/filter/concept",
                        local_name="conceptName",
                        qnames=(number.qname,),
                    ),
                ),
            ),
        ),
    )
    findings = OutputFormulaRuntimeEvaluator(
        _taxonomy(formula, concepts={number.qname: number})
    ).evaluate_runtime_errors(_instance())
    assert [finding.rule_id for finding in findings] == ["xqt-err:XPTY0004"]

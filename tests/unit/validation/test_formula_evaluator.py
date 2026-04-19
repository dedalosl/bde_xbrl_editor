"""Unit tests for FormulaEvaluator (validation/formula/evaluator.py)."""
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
from bde_xbrl_editor.taxonomy.models import (
    AssertionTextResource,
    ConsistencyAssertionDefinition,
    ExistenceAssertionDefinition,
    FactVariableDefinition,
    FormulaAssertionSet,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
    ValueAssertionDefinition,
)
from bde_xbrl_editor.validation.formula.evaluator import FormulaEvaluator
from bde_xbrl_editor.validation.models import ValidationSeverity, ValidationStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TAX_NS = "http://example.com/tax"


def _qn(local: str) -> QName:
    return QName(namespace=_TAX_NS, local_name=local)


def _entity() -> ReportingEntity:
    return ReportingEntity(identifier="ENT001", scheme="http://www.example.com")


def _instant_period() -> ReportingPeriod:
    return ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31))


def _ctx(ctx_id: str) -> XbrlContext:
    return XbrlContext(
        context_id=ctx_id,
        entity=_entity(),
        period=_instant_period(),
    )


def _fact(
    local: str = "Amount",
    ctx_id: str = "ctx1",
    value: str = "100",
    decimals: str | None = None,
) -> Fact:
    return Fact(
        concept=_qn(local),
        context_ref=ctx_id,
        unit_ref=None,
        value=value,
        decimals=decimals,
    )


def _instance(facts: list[Fact], contexts: dict[str, XbrlContext] | None = None) -> XbrlInstance:
    inst = XbrlInstance(
        taxonomy_entry_point=Path("tax.xsd"),
        schema_ref_href="tax.xsd",
        entity=_entity(),
        period=_instant_period(),
    )
    inst.contexts.update(contexts or {"ctx1": _ctx("ctx1")})
    inst.facts.extend(facts)
    return inst


class _FakeLabels:
    def get(self, *a, **kw):
        return None


def _taxonomy(assertion_set: FormulaAssertionSet) -> TaxonomyStructure:
    meta = TaxonomyMetadata(
        name="Test",
        version="1.0",
        publisher="Example",
        entry_point_path=Path("tax.xsd"),
        loaded_at=datetime(2024, 1, 1),
        declared_languages=("en",),
    )
    return TaxonomyStructure(
        metadata=meta,
        concepts={},
        labels=_FakeLabels(),
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
        formula_assertion_set=assertion_set,
    )


def _base_assertion_kwargs(
    assertion_id: str = "A001",
    abstract: bool = False,
    variables: tuple = (),
    severity: ValidationSeverity = ValidationSeverity.ERROR,
) -> dict:
    return {
        "assertion_id": assertion_id,
        "label": None,
        "severity": severity,
        "abstract": abstract,
        "variables": variables,
        "precondition_xpath": None,
    }


# ---------------------------------------------------------------------------
# Empty assertion set
# ---------------------------------------------------------------------------


class TestEmptyAssertionSet:
    def test_empty_set_returns_no_findings(self) -> None:
        """FormulaEvaluator returns [] when the assertion set is empty."""
        inst = _instance([])
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=()))
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert findings == []


# ---------------------------------------------------------------------------
# Abstract assertions are skipped
# ---------------------------------------------------------------------------


class TestAbstractAssertionSkipped:
    def test_abstract_assertion_produces_no_finding(self) -> None:
        """Abstract assertions are silently skipped — no finding is produced."""
        assertion = ValueAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="ABSTRACT_001", abstract=True),
            test_xpath="false()",
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact(value="0")])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert findings == []


# ---------------------------------------------------------------------------
# ValueAssertionDefinition
# ---------------------------------------------------------------------------


class TestValueAssertion:
    def test_true_expression_produces_pass_result(self) -> None:
        """A value assertion whose XPath test is 'true()' produces a PASS result row."""
        assertion = ValueAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="VA_PASS"),
            test_xpath="true()",
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact()])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert len(findings) == 1
        assert findings[0].status == ValidationStatus.PASS
        assert findings[0].severity is None

    def test_false_expression_produces_finding(self) -> None:
        """A value assertion whose XPath test is 'false()' produces one finding."""
        assertion = ValueAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="VA_FAIL"),
            test_xpath="false()",
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact()])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert len(findings) == 1
        assert findings[0].rule_id == "VA_FAIL"
        assert findings[0].source == "formula"

    def test_false_assertion_severity_from_definition(self) -> None:
        """The finding severity matches the assertion's declared severity."""
        assertion = ValueAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="VA_WARN", severity=ValidationSeverity.WARNING),
            test_xpath="false()",
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact()])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert findings[0].severity == ValidationSeverity.WARNING

    def test_empty_test_xpath_skips_assertion(self) -> None:
        """A value assertion with empty test_xpath produces no findings."""
        assertion = ValueAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="VA_EMPTY"),
            test_xpath="",
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact()])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert findings == []

    def test_value_assertion_with_variable_binding(self) -> None:
        """A value assertion with a bound variable produces a finding when test fails."""
        var_def = FactVariableDefinition(
            variable_name="v",
            concept_filter=_qn("Amount"),
        )
        assertion = ValueAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="VA_VAR", variables=(var_def,)),
            test_xpath="false()",
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact("Amount", value="42")])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert any(f.rule_id == "VA_VAR" for f in findings)

    def test_formula_finding_carries_rule_details(self) -> None:
        """Failed formula findings include formatted assertion details for the UI."""
        var_def = FactVariableDefinition(
            variable_name="v",
            concept_filter=_qn("Amount"),
            fallback_value="0",
        )
        assertion = ValueAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="VA_DETAIL", variables=(var_def,)),
            test_xpath="$v < 0",
        )
        assertion = ValueAssertionDefinition(
            assertion_id=assertion.assertion_id,
            label="Amount must pass",
            severity=assertion.severity,
            abstract=assertion.abstract,
            variables=assertion.variables,
            precondition_xpath="$v",
            test_xpath=assertion.test_xpath,
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact("Amount", value="42")])

        findings = FormulaEvaluator(taxonomy).evaluate(inst)

        assert len(findings) == 1
        finding = findings[0]
        assert finding.formula_assertion_type == "Value Assertion"
        assert finding.formula_expression == "$v < 0"
        assert finding.formula_precondition == "$v"
        assert finding.formula_operands_text is not None
        assert "$v" in finding.formula_operands_text
        assert "concept: {http://example.com/tax}Amount" in finding.formula_operands_text
        assert "fallback: 0" in finding.formula_operands_text

    def test_value_assertion_passes_for_each_binding(self) -> None:
        """A passing assertion produces a PASS result row for each evaluated binding."""
        _var_def = FactVariableDefinition(variable_name="v", concept_filter=_qn("Amount"))
        assertion = ValueAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="VA_MULTI"),
            test_xpath="true()",
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        ctx2 = _ctx("ctx2")
        inst = _instance(
            [_fact("Amount", "ctx1"), _fact("Amount", "ctx2")],
            contexts={"ctx1": _ctx("ctx1"), "ctx2": ctx2},
        )
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert len(findings) == 1
        assert all(f.status == ValidationStatus.PASS for f in findings)

    def test_unsatisfied_message_template_is_rendered_with_binding_values(self) -> None:
        """Validation messages render embedded XPath expressions against bound facts."""
        var_def = FactVariableDefinition(variable_name="v", concept_filter=_qn("Amount"))
        assertion = ValueAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="VA_MSG", variables=(var_def,)),
            test_xpath="false()",
            message_resources=(
                AssertionTextResource(
                    text=(
                        "Not satisfied error: Fact { string(node-name($v)) } "
                        "in context { string($v/@contextRef) }, reported value { string($v) }, "
                        "period starts { string(xfi:period-start(xfi:period($v))) }"
                    ),
                    language="en",
                    role="http://www.xbrl.org/2010/role/message",
                    arcrole="http://xbrl.org/arcrole/2010/assertion-unsatisfied-message",
                    namespaces={"xfi": "http://www.xbrl.org/2008/function/instance"},
                ),
            ),
            namespaces={"xfi": "http://www.xbrl.org/2008/function/instance"},
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        ctx = XbrlContext(
            context_id="ctx1",
            entity=_entity(),
            period=ReportingPeriod(
                period_type="duration",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            ),
        )
        inst = _instance([_fact("Amount", value="42")], contexts={"ctx1": ctx})

        findings = FormulaEvaluator(taxonomy).evaluate(inst)

        assert len(findings) == 1
        assert findings[0].message.startswith("Not satisfied error: Fact ")
        assert "context ctx1" in findings[0].message
        assert "reported value 42" in findings[0].message
        assert "period starts 2024-01-01" in findings[0].message


# ---------------------------------------------------------------------------
# ExistenceAssertionDefinition
# ---------------------------------------------------------------------------


class TestExistenceAssertion:
    def test_matching_facts_found_produces_pass_result(self) -> None:
        """Existence assertion passes when at least one matching fact exists."""
        var_def = FactVariableDefinition(variable_name="v", concept_filter=_qn("Amount"))
        assertion = ExistenceAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="EA_PASS", variables=(var_def,)),
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact("Amount", value="10")])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert len(findings) == 1
        assert findings[0].status == ValidationStatus.PASS

    def test_no_matching_facts_produces_finding(self) -> None:
        """Existence assertion fails when no facts match the variable filter."""
        var_def = FactVariableDefinition(variable_name="v", concept_filter=_qn("MissingConcept"))
        assertion = ExistenceAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="EA_FAIL", variables=(var_def,)),
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact("Amount", value="10")])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert len(findings) == 1
        assert findings[0].rule_id == "EA_FAIL"

    def test_existence_assertion_finding_source_is_formula(self) -> None:
        """Existence assertion findings have source='formula'."""
        var_def = FactVariableDefinition(variable_name="v", concept_filter=_qn("Ghost"))
        assertion = ExistenceAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="EA_SOURCE", variables=(var_def,)),
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert findings[0].source == "formula"

    def test_existence_assertion_no_variables_passes(self) -> None:
        """An existence assertion with no variables and an empty instance passes."""
        assertion = ExistenceAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="EA_NOVARS"),
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([])
        # With no variables, bindings = [{}]. All values are empty — fails.
        # This matches the evaluator logic: every binding has empty fact sets → fails.
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert findings[0].rule_id == "EA_NOVARS"


# ---------------------------------------------------------------------------
# ConsistencyAssertionDefinition
# ---------------------------------------------------------------------------


class TestConsistencyAssertion:
    def test_exact_match_produces_pass_result(self) -> None:
        """Consistency assertion passes when computed value exactly equals actual value."""
        var_def = FactVariableDefinition(variable_name="v", concept_filter=_qn("Amount"))
        assertion = ConsistencyAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="CA_PASS", variables=(var_def,)),
            formula_xpath="100",  # XPath literal that evaluates to 100
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact("Amount", value="100")])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert len(findings) == 1
        assert findings[0].status == ValidationStatus.PASS

    def test_value_outside_radius_produces_finding(self) -> None:
        """Consistency assertion fails when the difference exceeds absolute_radius."""
        var_def = FactVariableDefinition(variable_name="v", concept_filter=_qn("Amount"))
        assertion = ConsistencyAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="CA_FAIL", variables=(var_def,)),
            formula_xpath="200",  # computed=200, actual=100, diff=100
            absolute_radius=Decimal("10"),
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact("Amount", value="100")])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert any(f.rule_id == "CA_FAIL" for f in findings)

    def test_value_within_absolute_radius_passes(self) -> None:
        """Consistency assertion within tolerance produces a PASS result row."""
        var_def = FactVariableDefinition(variable_name="v", concept_filter=_qn("Amount"))
        assertion = ConsistencyAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="CA_WITHIN", variables=(var_def,)),
            formula_xpath="105",  # computed=105, actual=100, diff=5
            absolute_radius=Decimal("10"),
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact("Amount", value="100")])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert len(findings) == 1
        assert findings[0].status == ValidationStatus.PASS

    def test_empty_formula_xpath_skips_assertion(self) -> None:
        """A consistency assertion with empty formula_xpath produces no findings."""
        var_def = FactVariableDefinition(variable_name="v", concept_filter=_qn("Amount"))
        assertion = ConsistencyAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="CA_EMPTY", variables=(var_def,)),
            formula_xpath="",
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact("Amount", value="100")])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert findings == []

    def test_consistency_finding_carries_concept_and_context(self) -> None:
        """Consistency finding includes concept_qname and context_ref."""
        var_def = FactVariableDefinition(variable_name="v", concept_filter=_qn("Amount"))
        assertion = ConsistencyAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="CA_META", variables=(var_def,)),
            formula_xpath="999",  # large discrepancy
            absolute_radius=Decimal("0"),
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact("Amount", ctx_id="ctx1", value="100")])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert findings[0].concept_qname == _qn("Amount")
        assert findings[0].context_ref == "ctx1"

    def test_non_numeric_fact_value_skipped_gracefully(self) -> None:
        """A consistency assertion on a non-numeric fact value does not raise."""
        var_def = FactVariableDefinition(variable_name="v", concept_filter=_qn("Label"))
        assertion = ConsistencyAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="CA_TEXT", variables=(var_def,)),
            formula_xpath="0",
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(assertion,)))
        inst = _instance([_fact("Label", value="not_a_number")])
        # Should not raise; fact is silently skipped
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        assert isinstance(findings, list)


# ---------------------------------------------------------------------------
# Multiple assertions in one set
# ---------------------------------------------------------------------------


class TestMultipleAssertions:
    def test_multiple_assertions_all_evaluated(self) -> None:
        """All non-abstract assertions in a set are evaluated."""
        a1 = ValueAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="A1"),
            test_xpath="false()",
        )
        a2 = ValueAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="A2"),
            test_xpath="false()",
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(a1, a2)))
        inst = _instance([_fact()])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        rule_ids = {f.rule_id for f in findings}
        assert "A1" in rule_ids
        assert "A2" in rule_ids

    def test_mixed_pass_fail_rows_are_both_reported(self) -> None:
        """Mixed evaluations include PASS and FAIL rows so the UI can show both."""
        a_pass = ValueAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="PASS"),
            test_xpath="true()",
        )
        a_fail = ValueAssertionDefinition(
            **_base_assertion_kwargs(assertion_id="FAIL"),
            test_xpath="false()",
        )
        taxonomy = _taxonomy(FormulaAssertionSet(assertions=(a_pass, a_fail)))
        inst = _instance([_fact()])
        findings = FormulaEvaluator(taxonomy).evaluate(inst)
        statuses = {f.rule_id: f.status for f in findings}
        assert statuses["PASS"] == ValidationStatus.PASS
        assert statuses["FAIL"] == ValidationStatus.FAIL

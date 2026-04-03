"""Integration tests: InstanceValidator with known formula assertion failures.

These tests build synthetic TaxonomyStructure + XbrlInstance objects in memory
so they run without external files. Each test exercises a specific formula
assertion type and verifies the expected rule_id appears (or does not appear)
in the ValidationReport findings.
"""

from __future__ import annotations

from datetime import datetime
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
    ConsistencyAssertionDefinition,
    ExistenceAssertionDefinition,
    FactVariableDefinition,
    FormulaAssertionSet,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
    ValueAssertionDefinition,
)
from bde_xbrl_editor.validation import InstanceValidator, ValidationSeverity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NS = "http://example.com/test"
_CONCEPT = QName(namespace=_NS, local_name="Revenue", prefix="ex")


def _make_taxonomy(assertions: tuple) -> TaxonomyStructure:
    """Build a minimal TaxonomyStructure carrying the given formula assertions."""
    meta = TaxonomyMetadata(
        name="TestTaxonomy",
        version="1.0",
        publisher="Test",
        entry_point_path=Path("test.xsd"),
        loaded_at=datetime(2024, 1, 1),
        declared_languages=("en",),
    )
    return TaxonomyStructure(
        metadata=meta,
        concepts={},
        labels=None,
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
        formula_assertion_set=FormulaAssertionSet(
            assertions=assertions,
            abstract_count=0,
        ),
    )


def _make_instance(facts: list[Fact], contexts: dict, units: dict = None) -> XbrlInstance:
    """Build a minimal XbrlInstance with the given facts and contexts."""
    entity = ReportingEntity(identifier="TEST", scheme="http://example.com")
    period = ReportingPeriod(
        period_type="duration", start_date="2023-01-01", end_date="2023-12-31"
    )
    return XbrlInstance(
        taxonomy_entry_point=Path("test.xsd"),
        schema_ref_href="test.xsd",
        entity=entity,
        period=period,
        contexts=contexts,
        units=units or {},
        facts=facts,
    )


def _make_context(period_type: str = "duration") -> XbrlContext:
    entity = ReportingEntity(identifier="TEST", scheme="http://example.com")
    period = ReportingPeriod(
        period_type=period_type,
        start_date="2023-01-01" if period_type == "duration" else None,
        end_date="2023-12-31" if period_type == "duration" else None,
        instant_date="2023-12-31" if period_type == "instant" else None,
    )
    return XbrlContext(
        context_id="ctx1",
        entity=entity,
        period=period,
        dimensions={},
    )


# ---------------------------------------------------------------------------
# Value assertion tests
# ---------------------------------------------------------------------------


class TestValueAssertionIntegration:
    """ValueAssertionDefinition: @test XPath must evaluate to true for each binding."""

    def _make_assertion(self, test_xpath: str, var_name: str = "revenue") -> ValueAssertionDefinition:
        var = FactVariableDefinition(
            variable_name=var_name,
            concept_filter=_CONCEPT,
        )
        return ValueAssertionDefinition(
            assertion_id="va:revenue-positive",
            label="Revenue must be positive",
            severity="error",
            abstract=False,
            variables=(var,),
            precondition_xpath=None,
            test_xpath=test_xpath,
        )

    def test_passing_value_assertion_produces_no_findings(self):
        """true() expression always passes — no findings expected."""
        assertion = self._make_assertion("true()")
        taxonomy = _make_taxonomy((assertion,))
        ctx = _make_context()
        fact = Fact(concept=_CONCEPT, context_ref="ctx1", unit_ref=None, value="1000")
        instance = _make_instance([fact], {"ctx1": ctx})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        formula_findings = [f for f in report.findings if f.source == "formula"]
        assert len(formula_findings) == 0

    def test_failing_value_assertion_produces_finding(self):
        """false() expression always fails — one finding with the assertion's rule_id."""
        assertion = self._make_assertion("false()")
        taxonomy = _make_taxonomy((assertion,))
        ctx = _make_context()
        fact = Fact(concept=_CONCEPT, context_ref="ctx1", unit_ref=None, value="1000")
        instance = _make_instance([fact], {"ctx1": ctx})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        rule_ids = {f.rule_id for f in report.findings}
        assert "va:revenue-positive" in rule_ids

    def test_failing_value_assertion_severity_is_error(self):
        """Finding from a failed value assertion has ERROR severity."""
        assertion = self._make_assertion("false()")
        taxonomy = _make_taxonomy((assertion,))
        ctx = _make_context()
        fact = Fact(concept=_CONCEPT, context_ref="ctx1", unit_ref=None, value="-500")
        instance = _make_instance([fact], {"ctx1": ctx})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        matching = [f for f in report.findings if f.rule_id == "va:revenue-positive"]
        assert len(matching) >= 1
        assert all(f.severity == ValidationSeverity.ERROR for f in matching)

    def test_abstract_assertion_is_skipped(self):
        """Abstract assertions must never produce findings."""
        assertion = ValueAssertionDefinition(
            assertion_id="va:abstract-rule",
            label=None,
            severity="error",
            abstract=True,  # ← must be skipped
            variables=(),
            precondition_xpath=None,
            test_xpath="false()",  # would fail if evaluated
        )
        taxonomy = _make_taxonomy((assertion,))
        ctx = _make_context()
        fact = Fact(concept=_CONCEPT, context_ref="ctx1", unit_ref=None, value="100")
        instance = _make_instance([fact], {"ctx1": ctx})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        assert not any(f.rule_id == "va:abstract-rule" for f in report.findings)

    def test_multiple_bindings_each_evaluated(self):
        """Two facts matching the same variable → two binding evaluations."""
        assertion = self._make_assertion("false()")
        taxonomy = _make_taxonomy((assertion,))
        ctx1 = _make_context()
        ctx2 = XbrlContext(
            context_id="ctx2",
            entity=ctx1.entity,
            period=ctx1.period,
            dimensions={},
        )
        fact1 = Fact(concept=_CONCEPT, context_ref="ctx1", unit_ref=None, value="100")
        fact2 = Fact(concept=_CONCEPT, context_ref="ctx2", unit_ref=None, value="200")
        instance = _make_instance([fact1, fact2], {"ctx1": ctx1, "ctx2": ctx2})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        # Two bindings → two findings for the same rule
        matching = [f for f in report.findings if f.rule_id == "va:revenue-positive"]
        assert len(matching) == 2


# ---------------------------------------------------------------------------
# Existence assertion tests
# ---------------------------------------------------------------------------


class TestExistenceAssertionIntegration:
    """ExistenceAssertionDefinition: at least one binding must have a non-empty fact set."""

    def _make_assertion(self) -> ExistenceAssertionDefinition:
        var = FactVariableDefinition(
            variable_name="revenue",
            concept_filter=_CONCEPT,
        )
        return ExistenceAssertionDefinition(
            assertion_id="ea:revenue-must-exist",
            label="Revenue must be reported",
            severity="error",
            abstract=False,
            variables=(var,),
            precondition_xpath=None,
        )

    def test_fact_present_passes(self):
        """When matching fact exists, existence assertion passes — no findings."""
        assertion = self._make_assertion()
        taxonomy = _make_taxonomy((assertion,))
        ctx = _make_context()
        fact = Fact(concept=_CONCEPT, context_ref="ctx1", unit_ref=None, value="500")
        instance = _make_instance([fact], {"ctx1": ctx})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        assert not any(f.rule_id == "ea:revenue-must-exist" for f in report.findings)

    def test_no_matching_fact_fails(self):
        """When no matching fact exists, existence assertion produces a finding."""
        assertion = self._make_assertion()
        taxonomy = _make_taxonomy((assertion,))
        # Instance has a fact with a DIFFERENT concept — existence check should fail
        other_concept = QName(namespace=_NS, local_name="Cost", prefix="ex")
        ctx = _make_context()
        fact = Fact(concept=other_concept, context_ref="ctx1", unit_ref=None, value="100")
        instance = _make_instance([fact], {"ctx1": ctx})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        assert any(f.rule_id == "ea:revenue-must-exist" for f in report.findings)

    def test_empty_instance_fails_existence(self):
        """Empty facts list → existence assertion always fails."""
        assertion = self._make_assertion()
        taxonomy = _make_taxonomy((assertion,))
        instance = _make_instance([], {})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        assert any(f.rule_id == "ea:revenue-must-exist" for f in report.findings)

    def test_finding_source_is_formula(self):
        """Existence assertion findings must have source='formula'."""
        assertion = self._make_assertion()
        taxonomy = _make_taxonomy((assertion,))
        instance = _make_instance([], {})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        ea_findings = [f for f in report.findings if f.rule_id == "ea:revenue-must-exist"]
        assert len(ea_findings) == 1
        assert ea_findings[0].source == "formula"


# ---------------------------------------------------------------------------
# Consistency assertion tests
# ---------------------------------------------------------------------------


class TestConsistencyAssertionIntegration:
    """ConsistencyAssertionDefinition: formula XPath result must match fact value."""

    _COST = QName(namespace=_NS, local_name="Cost", prefix="ex")
    _TOTAL = QName(namespace=_NS, local_name="Total", prefix="ex")

    def _make_assertion(
        self,
        formula_xpath: str,
        absolute_radius: Decimal | None = None,
    ) -> ConsistencyAssertionDefinition:
        # The FIRST variable is the "target": its actual value is compared against the formula result.
        # Revenue and Cost are inputs; Total is what the formula should produce.
        var_total = FactVariableDefinition(
            variable_name="total",
            concept_filter=self._TOTAL,
        )
        var_revenue = FactVariableDefinition(
            variable_name="revenue",
            concept_filter=_CONCEPT,
        )
        var_cost = FactVariableDefinition(
            variable_name="cost",
            concept_filter=self._COST,
        )
        return ConsistencyAssertionDefinition(
            assertion_id="ca:total-equals-revenue-plus-cost",
            label="Total = Revenue + Cost",
            severity="error",
            abstract=False,
            variables=(var_total, var_revenue, var_cost),  # total FIRST → it is the target
            precondition_xpath=None,
            formula_xpath=formula_xpath,
            absolute_radius=absolute_radius,
        )

    def test_matching_values_produces_no_findings(self):
        """When formula result matches fact value exactly, no finding."""
        # total = 1000 + 500 = 1500 and fact.total = 1500 → passes
        assertion = self._make_assertion("$revenue + $cost")
        taxonomy = _make_taxonomy((assertion,))
        ctx = _make_context()
        facts = [
            Fact(concept=_CONCEPT, context_ref="ctx1", unit_ref=None, value="1000"),
            Fact(concept=self._COST, context_ref="ctx1", unit_ref=None, value="500"),
            Fact(concept=self._TOTAL, context_ref="ctx1", unit_ref=None, value="1500"),
        ]
        instance = _make_instance(facts, {"ctx1": ctx})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        assert not any(f.rule_id == "ca:total-equals-revenue-plus-cost" for f in report.findings)

    def test_mismatched_values_produces_finding(self):
        """When formula result differs from fact value, a finding is produced."""
        # total = 1000 + 500 = 1500 but fact.total = 2000 → fails
        assertion = self._make_assertion("$revenue + $cost")
        taxonomy = _make_taxonomy((assertion,))
        ctx = _make_context()
        facts = [
            Fact(concept=_CONCEPT, context_ref="ctx1", unit_ref=None, value="1000"),
            Fact(concept=self._COST, context_ref="ctx1", unit_ref=None, value="500"),
            Fact(concept=self._TOTAL, context_ref="ctx1", unit_ref=None, value="2000"),
        ]
        instance = _make_instance(facts, {"ctx1": ctx})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        rule_ids = {f.rule_id for f in report.findings}
        assert "ca:total-equals-revenue-plus-cost" in rule_ids

    def test_within_absolute_radius_passes(self):
        """Difference within absolute_radius → passes."""
        # formula = 1000 + 500 = 1500, fact = 1501, radius = 5 → |1501-1500| = 1 ≤ 5 → pass
        assertion = self._make_assertion("$revenue + $cost", absolute_radius=Decimal("5"))
        taxonomy = _make_taxonomy((assertion,))
        ctx = _make_context()
        facts = [
            Fact(concept=_CONCEPT, context_ref="ctx1", unit_ref=None, value="1000"),
            Fact(concept=self._COST, context_ref="ctx1", unit_ref=None, value="500"),
            Fact(concept=self._TOTAL, context_ref="ctx1", unit_ref=None, value="1501"),
        ]
        instance = _make_instance(facts, {"ctx1": ctx})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        assert not any(f.rule_id == "ca:total-equals-revenue-plus-cost" for f in report.findings)

    def test_outside_absolute_radius_fails(self):
        """Difference outside absolute_radius → finding."""
        # formula = 1000+500=1500, fact=1510, radius=5 → |1510-1500|=10 > 5 → fail
        assertion = self._make_assertion("$revenue + $cost", absolute_radius=Decimal("5"))
        taxonomy = _make_taxonomy((assertion,))
        ctx = _make_context()
        facts = [
            Fact(concept=_CONCEPT, context_ref="ctx1", unit_ref=None, value="1000"),
            Fact(concept=self._COST, context_ref="ctx1", unit_ref=None, value="500"),
            Fact(concept=self._TOTAL, context_ref="ctx1", unit_ref=None, value="1510"),
        ]
        instance = _make_instance(facts, {"ctx1": ctx})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        assert any(f.rule_id == "ca:total-equals-revenue-plus-cost" for f in report.findings)

    def test_finding_carries_concept_and_context(self):
        """Consistency finding must carry concept_qname and context_ref."""
        assertion = self._make_assertion("$revenue + $cost")
        taxonomy = _make_taxonomy((assertion,))
        ctx = _make_context()
        facts = [
            Fact(concept=_CONCEPT, context_ref="ctx1", unit_ref=None, value="100"),
            Fact(concept=self._COST, context_ref="ctx1", unit_ref=None, value="50"),
            Fact(concept=self._TOTAL, context_ref="ctx1", unit_ref=None, value="999"),
        ]
        instance = _make_instance(facts, {"ctx1": ctx})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        ca_findings = [
            f for f in report.findings if f.rule_id == "ca:total-equals-revenue-plus-cost"
        ]
        assert len(ca_findings) >= 1
        # The first fact in the binding yields the concept_qname and context_ref
        finding = ca_findings[0]
        assert finding.concept_qname is not None
        assert finding.context_ref is not None


# ---------------------------------------------------------------------------
# Mixed assertion set tests
# ---------------------------------------------------------------------------


class TestMixedAssertions:
    """Multiple assertions of different types evaluated together."""

    def test_mixed_pass_and_fail(self):
        """Value assertion passes while existence assertion fails → only ea finding."""
        va = ValueAssertionDefinition(
            assertion_id="va:always-pass",
            label=None,
            severity="error",
            abstract=False,
            variables=(),
            precondition_xpath=None,
            test_xpath="true()",
        )
        ea = ExistenceAssertionDefinition(
            assertion_id="ea:missing-concept",
            label=None,
            severity="warning",
            abstract=False,
            variables=(FactVariableDefinition(
                variable_name="rev",
                concept_filter=QName(namespace=_NS, local_name="NonExistent", prefix="ex"),
            ),),
            precondition_xpath=None,
        )
        taxonomy = _make_taxonomy((va, ea))
        instance = _make_instance([], {})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        rule_ids = {f.rule_id for f in report.findings}
        assert "va:always-pass" not in rule_ids
        assert "ea:missing-concept" in rule_ids

    def test_no_assertions_always_passes(self):
        """Empty FormulaAssertionSet → formula engine returns no findings."""
        taxonomy = _make_taxonomy(())
        instance = _make_instance([], {})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        formula_findings = [f for f in report.findings if f.source == "formula"]
        assert len(formula_findings) == 0

    def test_report_passed_requires_no_errors(self):
        """report.passed is False when any ERROR finding exists."""
        ea = ExistenceAssertionDefinition(
            assertion_id="ea:must-fail",
            label=None,
            severity="error",
            abstract=False,
            variables=(FactVariableDefinition(
                variable_name="x",
                concept_filter=QName(namespace=_NS, local_name="Ghost", prefix="ex"),
            ),),
            precondition_xpath=None,
        )
        taxonomy = _make_taxonomy((ea,))
        instance = _make_instance([], {})

        report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)

        assert not report.passed
        assert report.error_count >= 1

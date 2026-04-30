"""Structural conformance validator for XBRL 2.1 instances."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from lxml import etree

from bde_xbrl_editor.instance.constants import ISO4217_NS
from bde_xbrl_editor.instance.models import Fact, XbrlInstance, XbrlUnit
from bde_xbrl_editor.instance.s_equal import canonical_context_refs_by_s_equal
from bde_xbrl_editor.taxonomy.constants import NS_XBRLI
from bde_xbrl_editor.taxonomy.models import Concept, QName, TaxonomyStructure
from bde_xbrl_editor.taxonomy.schema import parse_schema_raw
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity

_NUMERIC_TYPE_KEYWORDS = ("monetary", "decimal", "integer", "float", "double")
_XBRLI_ITEM = QName(NS_XBRLI, "item")
_XBRLI_TUPLE = QName(NS_XBRLI, "tuple")
_ARCROLE_ESSENCE_ALIAS = "http://www.xbrl.org/2003/arcrole/essence-alias"


@dataclass
class _FactAnalysis:
    unresolved_context_refs: list[ValidationFinding]
    unresolved_unit_refs: list[ValidationFinding]
    monetary_iso_units: list[ValidationFinding]
    unit_consistency: list[ValidationFinding]
    decimals_precision: list[ValidationFinding]
    period_type_mismatches: list[ValidationFinding]
    duplicate_facts: list[ValidationFinding]


def _is_iso4217_currency_code(local_name: str) -> bool:
    """ISO 4217 alphabetic codes are three letters (case-insensitive)."""
    code = local_name.strip().upper()
    return len(code) == 3 and code.isalpha()


def _measure_text_to_qname(measure_uri: str) -> QName | None:
    """Best-effort QName from stored measure text (no in-scope XML namespaces)."""
    raw = (measure_uri or "").strip()
    if not raw:
        return None
    if raw.startswith("{"):
        return QName.from_clark(raw)
    if raw.startswith(ISO4217_NS + ":"):
        return QName(namespace=ISO4217_NS, local_name=raw[len(ISO4217_NS) + 1 :])
    if raw.startswith(f"{NS_XBRLI}:"):
        return QName(namespace=NS_XBRLI, local_name=raw[len(NS_XBRLI) + 1 :])
    if ":" in raw:
        prefix, local = raw.split(":", 1)
        if prefix.lower() == "iso4217":
            return QName(namespace=ISO4217_NS, local_name=local)
        if prefix == "ISO4217":
            return QName(namespace=ISO4217_NS, local_name=local)
        if prefix.lower() == "xbrli":
            return QName(namespace=NS_XBRLI, local_name=local)
    return QName(namespace="", local_name=raw)


def _resolved_unit_measure_qname(unit: XbrlUnit) -> QName | None:
    if unit.measure_qname is not None:
        return unit.measure_qname
    return _measure_text_to_qname(unit.measure_uri)


def _effective_simple_measure_count(unit: XbrlUnit) -> int:
    """Direct measure count, or 1 when a legacy unit clearly carries a single measure."""
    if unit.unit_form == "divide":
        return 0
    if unit.simple_measure_count != 0:
        return unit.simple_measure_count
    if _resolved_unit_measure_qname(unit) is not None or (unit.measure_uri or "").strip():
        return 1
    return 0


def _concept_requires_iso4217_unit(concept: Concept) -> bool:
    """True when *concept* is a monetary item (explicit flag or xbrli:monetaryItemType)."""
    if concept.monetary_item_type:
        return True
    return (
        concept.data_type.namespace == NS_XBRLI
        and concept.data_type.local_name == "monetaryItemType"
    )


def _iter_descendant_qnames(container_xml: bytes) -> list[QName]:
    """Return descendant element QNames from serialized segment/scenario XML."""
    root = etree.fromstring(container_xml)  # noqa: S320
    qnames: list[QName] = []
    for child in root.iterdescendants():
        if not isinstance(child.tag, str):
            continue
        qnames.append(QName.from_clark(child.tag))
    return qnames


def _substitution_root_for_concept(
    concept_qname: QName,
    taxonomy: TaxonomyStructure,
    schema_substitution_groups: dict[QName, QName] | None = None,
) -> QName | None:
    """Return xbrli:item or xbrli:tuple when the SG chain reaches one."""
    if schema_substitution_groups is None:
        schema_substitution_groups = {}
    concept = taxonomy.concepts.get(concept_qname)
    seen: set[QName] = set()
    if concept is not None:
        sg = concept.substitution_group
    else:
        sg = schema_substitution_groups.get(concept_qname)
    while sg is not None and sg not in seen:
        if sg in (_XBRLI_ITEM, _XBRLI_TUPLE):
            return sg
        seen.add(sg)
        sg_concept = taxonomy.concepts.get(sg)
        if sg_concept is not None:
            sg = sg_concept.substitution_group
            continue
        sg = schema_substitution_groups.get(sg)
    return None


def _is_numeric_concept(concept: Concept) -> bool:
    local_name_lower = concept.data_type.local_name.lower()
    return any(kw in local_name_lower for kw in _NUMERIC_TYPE_KEYWORDS)


class StructuralConformanceValidator:
    """Run XBRL 2.1 structural checks against an in-memory instance.

    All checks produce findings with source="structural", severity=ERROR.
    Never raises — exceptions are caught and returned as error findings.
    """

    def validate(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure | None = None,
    ) -> list[ValidationFinding]:
        """Run all structural checks and return the aggregated findings list."""
        findings: list[ValidationFinding] = []
        fact_analysis: _FactAnalysis | None = None
        try:
            fact_analysis = self._analyze_facts(instance, taxonomy)
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:fact-analysis", exc))

        try:
            findings.extend(self._check_missing_schemaref(instance))
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:missing-schemaref", exc))

        try:
            findings.extend(
                fact_analysis.unresolved_context_refs
                if fact_analysis is not None
                else self._check_unresolved_context_refs(instance)
            )
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:unresolved-context-ref", exc))

        try:
            findings.extend(
                fact_analysis.unresolved_unit_refs
                if fact_analysis is not None
                else self._check_unresolved_unit_refs(instance, taxonomy)
            )
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:unresolved-unit-ref", exc))

        try:
            findings.extend(
                fact_analysis.monetary_iso_units
                if fact_analysis is not None
                else self._check_monetary_iso_units(instance, taxonomy)
            )
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:monetary-unit-measure", exc))

        try:
            findings.extend(
                fact_analysis.unit_consistency
                if fact_analysis is not None
                else self._check_unit_consistency(instance, taxonomy)
            )
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:unit-consistency", exc))

        try:
            findings.extend(
                fact_analysis.decimals_precision
                if fact_analysis is not None
                else self._check_decimals_precision(instance, taxonomy)
            )
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:decimals-precision", exc))

        try:
            findings.extend(self._check_incomplete_contexts(instance))
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:incomplete-context", exc))

        try:
            findings.extend(
                fact_analysis.period_type_mismatches
                if fact_analysis is not None
                else self._check_period_type_mismatch(instance, taxonomy)
            )
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:period-type-mismatch", exc))

        try:
            findings.extend(
                fact_analysis.duplicate_facts
                if fact_analysis is not None
                else self._check_duplicate_facts(instance)
            )
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:duplicate-fact", exc))

        try:
            findings.extend(self._check_segment_scenario_substitutions(instance, taxonomy))
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:segment-scenario-substitution", exc))

        try:
            findings.extend(self._check_essence_alias_units(instance, taxonomy))
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:essence-alias-unit", exc))

        # Check 7 (structural:missing-namespace) is skipped — namespace info not
        # available on the in-memory instance model.
        # Check 8 (structural:root-element) is already covered by check 1.

        return findings

    def _analyze_facts(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure | None,
    ) -> _FactAnalysis:
        """Run fact-scoped structural checks in one pass over instance.facts."""
        unresolved_context_refs: list[ValidationFinding] = []
        unresolved_unit_refs: list[ValidationFinding] = []
        monetary_iso_units: list[ValidationFinding] = []
        unit_consistency: list[ValidationFinding] = []
        decimals_precision: list[ValidationFinding] = []
        period_type_mismatches: list[ValidationFinding] = []
        duplicate_facts: list[ValidationFinding] = []
        duplicate_key_values: dict[tuple, list[str]] = defaultdict(list)

        try:
            canonical_context_refs = canonical_context_refs_by_s_equal(instance)
        except Exception as exc:  # noqa: BLE001
            canonical_context_refs = None
            duplicate_facts.append(self._internal_error("structural:duplicate-fact", exc))

        concept_traits: dict[QName, tuple[Concept | None, bool, bool]] = {}

        def _traits_for_fact(fact: Fact) -> tuple[Concept | None, bool, bool]:
            if taxonomy is None:
                return None, False, False
            cached = concept_traits.get(fact.concept)
            if cached is not None:
                return cached
            concept = taxonomy.concepts.get(fact.concept)
            traits = (
                concept,
                _is_numeric_concept(concept) if concept is not None else False,
                _concept_requires_iso4217_unit(concept) if concept is not None else False,
            )
            concept_traits[fact.concept] = traits
            return traits

        for fact in instance.facts:
            concept, is_numeric, requires_iso4217 = _traits_for_fact(fact)
            ctx = instance.contexts.get(fact.context_ref)
            if ctx is None:
                unresolved_context_refs.append(
                    ValidationFinding(
                        rule_id="structural:unresolved-context-ref",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Fact for concept '{fact.concept}' references context "
                            f"'{fact.context_ref}' which is not declared in the instance."
                        ),
                        source="structural",
                        concept_qname=fact.concept,
                        context_ref=fact.context_ref,
                    )
                )
            elif (
                concept is not None
                and ctx.period is not None
                and concept.period_type != ctx.period.period_type
            ):
                period_type_mismatches.append(
                    ValidationFinding(
                        rule_id="structural:period-type-mismatch",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Fact for concept '{fact.concept}' uses context "
                            f"'{fact.context_ref}' with period_type "
                            f"'{ctx.period.period_type}', but the concept declares "
                            f"period_type '{concept.period_type}'."
                        ),
                        source="structural",
                        concept_qname=fact.concept,
                        context_ref=fact.context_ref,
                    )
                )

            if is_numeric and (fact.unit_ref is None or fact.unit_ref not in instance.units):
                unresolved_unit_refs.append(
                    ValidationFinding(
                        rule_id="structural:unresolved-unit-ref",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Numeric fact for concept '{fact.concept}' "
                            + (
                                f"references unit '{fact.unit_ref}' which is not declared "
                                "in the instance."
                                if fact.unit_ref is not None
                                else "is missing a required unit reference."
                            )
                        ),
                        source="structural",
                        concept_qname=fact.concept,
                        context_ref=fact.context_ref,
                    )
                )

            if requires_iso4217 and fact.unit_ref is not None and fact.unit_ref in instance.units:
                monetary_finding = self._monetary_unit_finding(
                    fact,
                    instance.units[fact.unit_ref],
                )
                if monetary_finding is not None:
                    monetary_iso_units.append(monetary_finding)

            if fact.unit_ref is not None and fact.unit_ref in instance.units:
                unit_consistency.extend(
                    self._unit_consistency_findings(
                        fact,
                        instance.units[fact.unit_ref],
                        concept,
                    )
                )

            if is_numeric or fact.unit_ref is not None:
                finding = self._decimals_precision_finding(fact, is_numeric=is_numeric)
                if finding is not None:
                    decimals_precision.append(finding)

            if canonical_context_refs is not None and ctx is not None:
                ctx_bind = canonical_context_refs.get(fact.context_ref, fact.context_ref)
                key = (fact.concept, ctx_bind, fact.unit_ref)
                duplicate_key_values[key].append(fact.value)

        duplicate_facts.extend(self._duplicate_findings_from_key_values(duplicate_key_values))
        return _FactAnalysis(
            unresolved_context_refs=unresolved_context_refs,
            unresolved_unit_refs=unresolved_unit_refs,
            monetary_iso_units=monetary_iso_units,
            unit_consistency=unit_consistency,
            decimals_precision=decimals_precision,
            period_type_mismatches=period_type_mismatches,
            duplicate_facts=duplicate_facts,
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_missing_schemaref(self, instance: XbrlInstance) -> list[ValidationFinding]:
        """Check 1: instance must declare a non-empty schemaRef href."""
        if not instance.schema_ref_href or not instance.schema_ref_href.strip():
            return [
                ValidationFinding(
                    rule_id="structural:missing-schemaref",
                    severity=ValidationSeverity.ERROR,
                    message=(
                        "Instance does not declare a schemaRef href. "
                        "XBRL 2.1 requires exactly one link:schemaRef element."
                    ),
                    source="structural",
                )
            ]
        return []

    def _check_unresolved_context_refs(self, instance: XbrlInstance) -> list[ValidationFinding]:
        """Check 2: every fact.context_ref must exist in instance.contexts."""
        findings: list[ValidationFinding] = []
        for fact in instance.facts:
            if fact.context_ref not in instance.contexts:
                findings.append(
                    ValidationFinding(
                        rule_id="structural:unresolved-context-ref",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Fact for concept '{fact.concept}' references context "
                            f"'{fact.context_ref}' which is not declared in the instance."
                        ),
                        source="structural",
                        concept_qname=fact.concept,
                        context_ref=fact.context_ref,
                    )
                )
        return findings

    def _check_unresolved_unit_refs(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure | None,
    ) -> list[ValidationFinding]:
        """Check 3: numeric facts must reference a unit declared in instance.units."""
        if taxonomy is None:
            return []

        findings: list[ValidationFinding] = []
        for fact in instance.facts:
            concept = taxonomy.concepts.get(fact.concept)
            if concept is None:
                continue
            local_name_lower = concept.data_type.local_name.lower()
            is_numeric = any(kw in local_name_lower for kw in _NUMERIC_TYPE_KEYWORDS)
            if not is_numeric:
                continue
            if fact.unit_ref is None or fact.unit_ref not in instance.units:
                findings.append(
                    ValidationFinding(
                        rule_id="structural:unresolved-unit-ref",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Numeric fact for concept '{fact.concept}' "
                            + (
                                f"references unit '{fact.unit_ref}' which is not declared "
                                "in the instance."
                                if fact.unit_ref is not None
                                else "is missing a required unit reference."
                            )
                        ),
                        source="structural",
                        concept_qname=fact.concept,
                        context_ref=fact.context_ref,
                    )
                )
        return findings

    def _check_monetary_iso_units(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure | None,
    ) -> list[ValidationFinding]:
        """Monetary facts must use a single ISO 4217 currency measure (XBRL 2.1 §4.8)."""
        if taxonomy is None:
            return []

        findings: list[ValidationFinding] = []
        for fact in instance.facts:
            concept = taxonomy.concepts.get(fact.concept)
            if concept is None or not _concept_requires_iso4217_unit(concept):
                continue
            if fact.unit_ref is None or fact.unit_ref not in instance.units:
                continue

            unit = instance.units[fact.unit_ref]
            finding = self._monetary_unit_finding(fact, unit)
            if finding is not None:
                findings.append(finding)
        return findings

    def _check_unit_consistency(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure | None,
    ) -> list[ValidationFinding]:
        """XBRL 2.1 unit-shape checks beyond monetary ISO validation."""
        findings: list[ValidationFinding] = []
        for fact in instance.facts:
            if fact.unit_ref is None or fact.unit_ref not in instance.units:
                continue
            concept = taxonomy.concepts.get(fact.concept) if taxonomy is not None else None
            findings.extend(
                self._unit_consistency_findings(
                    fact,
                    instance.units[fact.unit_ref],
                    concept,
                )
            )
        return findings

    def _check_decimals_precision(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure | None,
    ) -> list[ValidationFinding]:
        """Numeric facts must use exactly one of decimals/precision unless nil."""
        findings: list[ValidationFinding] = []
        for fact in instance.facts:
            concept = taxonomy.concepts.get(fact.concept) if taxonomy is not None else None
            is_numeric = _is_numeric_concept(concept) if concept is not None else False
            if not is_numeric and fact.unit_ref is None:
                continue
            finding = self._decimals_precision_finding(fact, is_numeric=is_numeric)
            if finding is not None:
                findings.append(finding)
        return findings

    def _check_incomplete_contexts(self, instance: XbrlInstance) -> list[ValidationFinding]:
        """Check 4: each context must have both an entity and a period."""
        findings: list[ValidationFinding] = []
        for ctx_id, ctx in instance.contexts.items():
            missing: list[str] = []
            if ctx.entity is None:
                missing.append("entity")
            if ctx.period is None:
                missing.append("period")
            if missing:
                findings.append(
                    ValidationFinding(
                        rule_id="structural:incomplete-context",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Context '{ctx_id}' is incomplete: missing {' and '.join(missing)}."
                        ),
                        source="structural",
                        context_ref=ctx_id,
                    )
                )
        return findings

    def _check_period_type_mismatch(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure | None,
    ) -> list[ValidationFinding]:
        """Check 5: fact's context period_type must match the concept's declared period_type."""
        if taxonomy is None:
            return []

        findings: list[ValidationFinding] = []
        for fact in instance.facts:
            concept = taxonomy.concepts.get(fact.concept)
            if concept is None:
                continue
            ctx = instance.contexts.get(fact.context_ref)
            if ctx is None or ctx.period is None:
                continue
            if concept.period_type != ctx.period.period_type:
                findings.append(
                    ValidationFinding(
                        rule_id="structural:period-type-mismatch",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Fact for concept '{fact.concept}' uses context "
                            f"'{fact.context_ref}' with period_type "
                            f"'{ctx.period.period_type}', but the concept declares "
                            f"period_type '{concept.period_type}'."
                        ),
                        source="structural",
                        concept_qname=fact.concept,
                        context_ref=fact.context_ref,
                    )
                )
        return findings

    def _check_duplicate_facts(self, instance: XbrlInstance) -> list[ValidationFinding]:
        """Check 6: conflicting duplicate facts (same concept/context/unit, unequal values).

        XBRL 2.1 allows multiple facts with the same dimension signature when the
        reported values are identical (redundant reporting); inconsistent values
        are an error.
        """
        canon_ctx = canonical_context_refs_by_s_equal(instance)
        key_values: dict[tuple, list[str]] = defaultdict(list)
        for fact in instance.facts:
            if fact.context_ref not in instance.contexts:
                continue
            ctx_bind = canon_ctx.get(fact.context_ref, fact.context_ref)
            key = (fact.concept, ctx_bind, fact.unit_ref)
            key_values[key].append(fact.value)

        return self._duplicate_findings_from_key_values(key_values)

    @staticmethod
    def _duplicate_findings_from_key_values(
        key_values: dict[tuple, list[str]],
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for key, vals in key_values.items():
            if len(set(vals)) <= 1:
                continue
            concept, ctx_bind, unit_ref = key
            findings.append(
                ValidationFinding(
                    rule_id="structural:duplicate-fact",
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"Inconsistent duplicate facts for concept '{concept}' "
                        f"in context '{ctx_bind}'"
                        + (f" with unit '{unit_ref}'" if unit_ref is not None else "")
                        + f": values {sorted(set(vals))!r}."
                    ),
                    source="structural",
                    concept_qname=concept,
                    context_ref=ctx_bind,
                )
            )
        return findings

    @staticmethod
    def _monetary_unit_finding(fact: Fact, unit: XbrlUnit) -> ValidationFinding | None:
        if unit.unit_form == "divide":
            return ValidationFinding(
                rule_id="structural:monetary-unit-measure",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"Fact for monetary concept '{fact.concept}' uses unit "
                    f"'{fact.unit_ref}' with xbrli:divide; monetary items require "
                    "a single ISO 4217 currency measure."
                ),
                source="structural",
                concept_qname=fact.concept,
                context_ref=fact.context_ref,
            )

        eff_measures = _effective_simple_measure_count(unit)
        if eff_measures != 1:
            return ValidationFinding(
                rule_id="structural:monetary-unit-measure",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"Fact for monetary concept '{fact.concept}' uses unit "
                    f"'{fact.unit_ref}' with {eff_measures} measure "
                    "element(s); exactly one ISO 4217 measure is required."
                ),
                source="structural",
                concept_qname=fact.concept,
                context_ref=fact.context_ref,
            )

        mq = _resolved_unit_measure_qname(unit)
        if mq is None or mq.namespace != ISO4217_NS or not _is_iso4217_currency_code(mq.local_name):
            got = str(mq) if mq is not None else repr(unit.measure_uri)
            return ValidationFinding(
                rule_id="structural:monetary-unit-measure",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"Fact for monetary concept '{fact.concept}' must use an "
                    f"ISO 4217 currency measure in namespace '{ISO4217_NS}' "
                    f"with a 3-letter currency code; got measure {got!r}."
                ),
                source="structural",
                concept_qname=fact.concept,
                context_ref=fact.context_ref,
            )
        return None

    @staticmethod
    def _unit_measure_qnames(unit: XbrlUnit) -> tuple[QName, ...]:
        if unit.unit_form == "divide":
            return tuple(unit.numerator_measure_qnames) + tuple(unit.denominator_measure_qnames)
        if unit.simple_measure_qnames:
            return unit.simple_measure_qnames
        mq = _resolved_unit_measure_qname(unit)
        return (mq,) if mq is not None else ()

    def _unit_consistency_findings(
        self,
        fact: Fact,
        unit: XbrlUnit,
        concept: Concept | None,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        findings.extend(self._xbrli_measure_findings(fact, unit))
        if self._concept_is_shares_item(concept):
            finding = self._shares_unit_finding(fact, unit)
            if finding is not None:
                findings.append(finding)
        finding = self._divide_cancellation_finding(fact, unit)
        if finding is not None:
            findings.append(finding)
        return findings

    def _xbrli_measure_findings(
        self,
        fact: Fact,
        unit: XbrlUnit,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for measure in self._unit_measure_qnames(unit):
            if measure.namespace == NS_XBRLI and measure.local_name not in {"pure", "shares"}:
                findings.append(
                    ValidationFinding(
                        rule_id="structural:unit-consistency",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Fact for concept '{fact.concept}' uses unit '{fact.unit_ref}' "
                            f"with xbrli measure '{measure.local_name}'. XBRL instance "
                            "measures are limited to xbrli:pure and xbrli:shares."
                        ),
                        source="structural",
                        concept_qname=fact.concept,
                        context_ref=fact.context_ref,
                    )
                )
        return findings

    @staticmethod
    def _concept_is_shares_item(concept: Concept | None) -> bool:
        return (
            concept is not None
            and concept.data_type.namespace == NS_XBRLI
            and concept.data_type.local_name == "sharesItemType"
        )

    @staticmethod
    def _shares_unit_finding(fact: Fact, unit: XbrlUnit) -> ValidationFinding | None:
        expected = QName(namespace=NS_XBRLI, local_name="shares")
        measure_count = (
            0 if unit.unit_form != "simple" else _effective_simple_measure_count(unit)
        )
        measures = (
            unit.simple_measure_qnames
            if unit.simple_measure_qnames
            else ((_resolved_unit_measure_qname(unit),) if _resolved_unit_measure_qname(unit) else ())
        )
        if unit.unit_form != "simple" or measure_count != 1 or tuple(measures) != (expected,):
            got = ", ".join(str(m) for m in measures) or unit.measure_uri or unit.unit_form
            return ValidationFinding(
                rule_id="structural:unit-consistency",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"Fact for shares concept '{fact.concept}' must use a unit "
                    f"with exactly one xbrli:shares measure; got {got!r}."
                ),
                source="structural",
                concept_qname=fact.concept,
                context_ref=fact.context_ref,
            )
        return None

    @staticmethod
    def _divide_cancellation_finding(fact: Fact, unit: XbrlUnit) -> ValidationFinding | None:
        if unit.unit_form != "divide":
            return None
        numerator = Counter(unit.numerator_measure_qnames)
        denominator = Counter(unit.denominator_measure_qnames)
        cancelled = numerator & denominator
        if not cancelled:
            return None
        cancelled_text = ", ".join(str(qn) for qn in sorted(cancelled, key=str))
        return ValidationFinding(
            rule_id="structural:unit-consistency",
            severity=ValidationSeverity.ERROR,
            message=(
                f"Unit '{fact.unit_ref}' for concept '{fact.concept}' is not in "
                f"simplest form; numerator and denominator both contain {cancelled_text}."
            ),
            source="structural",
            concept_qname=fact.concept,
            context_ref=fact.context_ref,
        )

    @staticmethod
    def _decimals_precision_finding(
        fact: Fact,
        *,
        is_numeric: bool,
    ) -> ValidationFinding | None:
        has_decimals = fact.decimals is not None
        has_precision = fact.precision is not None
        is_nil = getattr(fact, "is_nil", False)

        if is_nil:
            if has_decimals or has_precision:
                present = " and ".join(
                    name
                    for name, present_attr in (
                        ("decimals", has_decimals),
                        ("precision", has_precision),
                    )
                    if present_attr
                )
                return ValidationFinding(
                    rule_id="structural:decimals-precision",
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"Nil fact for concept '{fact.concept}' must not specify "
                        f"{present}."
                    ),
                    source="structural",
                    concept_qname=fact.concept,
                    context_ref=fact.context_ref,
                )
            if fact.unit_ref is not None and not is_numeric:
                return ValidationFinding(
                    rule_id="structural:decimals-precision",
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"Nil fact for concept '{fact.concept}' has unitRef "
                        f"'{fact.unit_ref}' but no explicit decimals or precision; "
                        "the item type may contribute fixed precision/decimals, which "
                        "is not allowed for nil facts."
                    ),
                    source="structural",
                    concept_qname=fact.concept,
                    context_ref=fact.context_ref,
                )
            return None

        if not is_numeric:
            return None
        if has_decimals and has_precision:
            return ValidationFinding(
                rule_id="structural:decimals-precision",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"Numeric fact for concept '{fact.concept}' specifies both "
                    "decimals and precision; XBRL 2.1 allows only one."
                ),
                source="structural",
                concept_qname=fact.concept,
                context_ref=fact.context_ref,
            )
        if not has_decimals and not has_precision:
            return ValidationFinding(
                rule_id="structural:decimals-precision",
                severity=ValidationSeverity.ERROR,
                message=(
                    f"Numeric fact for concept '{fact.concept}' must specify either "
                    "decimals or precision."
                ),
                source="structural",
                concept_qname=fact.concept,
                context_ref=fact.context_ref,
            )
        return None

    def _check_segment_scenario_substitutions(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure | None,
    ) -> list[ValidationFinding]:
        """Reject item/tuple-substituting elements inside context segment/scenario."""
        if taxonomy is None:
            return []

        findings: list[ValidationFinding] = []
        schema_substitution_groups: dict[QName, QName] = dict(
            getattr(taxonomy, "schema_substitution_groups", {}) or {}
        )
        if not schema_substitution_groups:
            for schema_path in taxonomy.schema_files:
                try:
                    raw_candidates, _target_ns = parse_schema_raw(schema_path)
                except Exception as exc:  # noqa: BLE001
                    findings.append(
                        ValidationFinding(
                            rule_id="structural:segment-scenario-substitution",
                            severity=ValidationSeverity.ERROR,
                            message=(
                                "Unable to load substitution-group declarations from "
                                f"schema '{schema_path}' while validating segment/scenario "
                                f"contents: {exc}"
                            ),
                            source="structural",
                        )
                    )
                    continue
                for qname, (_concept, substitution_group) in raw_candidates.items():
                    schema_substitution_groups[qname] = substitution_group

        for ctx_id, ctx in instance.contexts.items():
            for container_name, container_xml in (
                ("scenario", getattr(ctx, "scenario_xml", None)),
                ("segment", getattr(ctx, "segment_xml", None)),
            ):
                if not container_xml:
                    continue
                try:
                    descendant_qnames = _iter_descendant_qnames(container_xml)
                except Exception as exc:  # noqa: BLE001
                    findings.append(
                        ValidationFinding(
                            rule_id="structural:segment-scenario-substitution",
                            severity=ValidationSeverity.ERROR,
                            message=(
                                f"Context '{ctx_id}' has invalid serialized {container_name} "
                                f"content that could not be analyzed for substitution groups: {exc}"
                            ),
                            source="structural",
                            context_ref=ctx_id,
                        )
                    )
                    continue

                for element_qname in descendant_qnames:
                    sg_root = _substitution_root_for_concept(
                        element_qname,
                        taxonomy,
                        schema_substitution_groups=schema_substitution_groups,
                    )
                    if sg_root is None:
                        continue
                    findings.append(
                        ValidationFinding(
                            rule_id="structural:segment-scenario-substitution",
                            severity=ValidationSeverity.ERROR,
                            message=(
                                f"Context '{ctx_id}' contains element '{element_qname}' in "
                                f"xbrli:{container_name}. Its substitution-group chain reaches "
                                f"'{sg_root}', which is forbidden in segment/scenario."
                            ),
                            source="structural",
                            context_ref=ctx_id,
                            concept_qname=element_qname,
                        )
                    )
        return findings

    def _check_essence_alias_units(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure | None,
    ) -> list[ValidationFinding]:
        """Essence-alias fact pairs must use equivalent units."""
        if taxonomy is None:
            return []

        essence_alias_arcs = [
            arc
            for arcs in taxonomy.definition.values()
            for arc in arcs
            if arc.arcrole == _ARCROLE_ESSENCE_ALIAS
        ]
        if not essence_alias_arcs:
            return []

        try:
            canonical_context_refs = canonical_context_refs_by_s_equal(instance)
        except Exception:
            canonical_context_refs = {}

        facts_by_concept: dict[QName, list[Fact]] = defaultdict(list)
        for fact in instance.facts:
            facts_by_concept[fact.concept].append(fact)

        findings: list[ValidationFinding] = []
        seen_pairs: set[tuple[QName, QName, str, str | None, str | None]] = set()
        for arc in essence_alias_arcs:
            source_facts = facts_by_concept.get(arc.source, [])
            target_facts = facts_by_concept.get(arc.target, [])
            if not source_facts or not target_facts:
                continue

            for source_fact in source_facts:
                source_ctx = canonical_context_refs.get(
                    source_fact.context_ref,
                    source_fact.context_ref,
                )
                for target_fact in target_facts:
                    target_ctx = canonical_context_refs.get(
                        target_fact.context_ref,
                        target_fact.context_ref,
                    )
                    if source_ctx != target_ctx:
                        continue
                    key = (
                        arc.source,
                        arc.target,
                        source_ctx,
                        source_fact.unit_ref,
                        target_fact.unit_ref,
                    )
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)
                    if self._unit_signature_for_ref(
                        instance,
                        source_fact.unit_ref,
                    ) == self._unit_signature_for_ref(instance, target_fact.unit_ref):
                        continue
                    findings.append(
                        ValidationFinding(
                            rule_id="structural:essence-alias-unit",
                            severity=ValidationSeverity.ERROR,
                            message=(
                                f"Essence-alias concepts '{arc.source}' and '{arc.target}' "
                                f"report facts in context '{source_ctx}' with non-equivalent "
                                f"units '{source_fact.unit_ref}' and '{target_fact.unit_ref}'."
                            ),
                            source="structural",
                            concept_qname=arc.source,
                            context_ref=source_ctx,
                        )
                    )
        return findings

    @classmethod
    def _unit_signature_for_ref(
        cls,
        instance: XbrlInstance,
        unit_ref: str | None,
    ) -> tuple | None:
        if unit_ref is None or unit_ref not in instance.units:
            return None
        return cls._unit_signature(instance.units[unit_ref])

    @classmethod
    def _unit_signature(cls, unit: XbrlUnit) -> tuple:
        def _counter_key(values: tuple[QName, ...]) -> tuple[tuple[QName, int], ...]:
            return tuple(sorted(Counter(values).items(), key=lambda item: str(item[0])))

        if unit.unit_form == "divide":
            return (
                "divide",
                _counter_key(unit.numerator_measure_qnames),
                _counter_key(unit.denominator_measure_qnames),
            )
        return ("simple", _counter_key(cls._unit_measure_qnames(unit)))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _internal_error(rule_id: str, exc: Exception) -> ValidationFinding:
        """Wrap an unexpected exception as an error finding."""
        return ValidationFinding(
            rule_id=rule_id,
            severity=ValidationSeverity.ERROR,
            message=f"Internal error while running check '{rule_id}': {exc}",
            source="structural",
        )

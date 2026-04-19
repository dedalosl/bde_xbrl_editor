"""Structural conformance validator for XBRL 2.1 instances."""

from __future__ import annotations

from collections import defaultdict

from bde_xbrl_editor.instance.constants import ISO4217_NS
from bde_xbrl_editor.instance.models import XbrlInstance, XbrlUnit
from bde_xbrl_editor.instance.s_equal import canonical_context_refs_by_s_equal
from bde_xbrl_editor.taxonomy.constants import NS_XBRLI
from bde_xbrl_editor.taxonomy.models import Concept, QName, TaxonomyStructure
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity

_NUMERIC_TYPE_KEYWORDS = ("monetary", "decimal", "integer", "float", "double")


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
        try:
            findings.extend(self._check_missing_schemaref(instance))
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:missing-schemaref", exc))

        try:
            findings.extend(self._check_unresolved_context_refs(instance))
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:unresolved-context-ref", exc))

        try:
            findings.extend(self._check_unresolved_unit_refs(instance, taxonomy))
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:unresolved-unit-ref", exc))

        try:
            findings.extend(self._check_monetary_iso_units(instance, taxonomy))
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:monetary-unit-measure", exc))

        try:
            findings.extend(self._check_incomplete_contexts(instance))
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:incomplete-context", exc))

        try:
            findings.extend(self._check_period_type_mismatch(instance, taxonomy))
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:period-type-mismatch", exc))

        try:
            findings.extend(self._check_duplicate_facts(instance))
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_error("structural:duplicate-fact", exc))

        # Check 7 (structural:missing-namespace) is skipped — namespace info not
        # available on the in-memory instance model.
        # Check 8 (structural:root-element) is already covered by check 1.

        return findings

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

    def _check_unresolved_context_refs(
        self, instance: XbrlInstance
    ) -> list[ValidationFinding]:
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
            if unit.unit_form == "divide":
                findings.append(
                    ValidationFinding(
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
                )
                continue

            eff_measures = _effective_simple_measure_count(unit)
            if eff_measures != 1:
                findings.append(
                    ValidationFinding(
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
                )
                continue

            mq = _resolved_unit_measure_qname(unit)
            if mq is None or mq.namespace != ISO4217_NS or not _is_iso4217_currency_code(
                mq.local_name
            ):
                got = str(mq) if mq is not None else repr(unit.measure_uri)
                findings.append(
                    ValidationFinding(
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
                )
        return findings

    def _check_incomplete_contexts(
        self, instance: XbrlInstance
    ) -> list[ValidationFinding]:
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
                            f"Context '{ctx_id}' is incomplete: "
                            f"missing {' and '.join(missing)}."
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

    def _check_duplicate_facts(
        self, instance: XbrlInstance
    ) -> list[ValidationFinding]:
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
                        + (
                            f" with unit '{unit_ref}'"
                            if unit_ref is not None
                            else ""
                        )
                        + f": values {sorted(set(vals))!r}."
                    ),
                    source="structural",
                    concept_qname=concept,
                    context_ref=ctx_bind,
                )
            )
        return findings

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

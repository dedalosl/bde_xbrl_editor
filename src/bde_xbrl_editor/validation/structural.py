"""Structural conformance validator for XBRL 2.1 instances."""

from __future__ import annotations

from bde_xbrl_editor.instance.models import XbrlInstance
from bde_xbrl_editor.taxonomy.models import TaxonomyStructure
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity

_NUMERIC_TYPE_KEYWORDS = ("monetary", "decimal", "integer", "float", "double")


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
        """Check 6: no two facts may share the same (concept, context_ref, unit_ref) triple."""
        seen: dict[tuple, int] = {}  # key -> first occurrence index
        findings: list[ValidationFinding] = []
        for idx, fact in enumerate(instance.facts):
            key = (fact.concept, fact.context_ref, fact.unit_ref)
            if key in seen:
                findings.append(
                    ValidationFinding(
                        rule_id="structural:duplicate-fact",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Duplicate fact detected for concept '{fact.concept}' "
                            f"in context '{fact.context_ref}'"
                            + (
                                f" with unit '{fact.unit_ref}'"
                                if fact.unit_ref is not None
                                else ""
                            )
                            + f" (first occurrence at index {seen[key]}, "
                            f"duplicate at index {idx})."
                        ),
                        source="structural",
                        concept_qname=fact.concept,
                        context_ref=fact.context_ref,
                    )
                )
            else:
                seen[key] = idx
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

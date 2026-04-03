"""Dimensional constraint validator for XBRL instances."""

from __future__ import annotations

from bde_xbrl_editor.instance.models import XbrlInstance
from bde_xbrl_editor.taxonomy.models import TaxonomyStructure, HypercubeModel, QName
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity


class DimensionalConstraintValidator:
    """Validate each fact's dimensions against taxonomy hypercube constraints.

    Never raises. Exceptions are caught and returned as error findings.
    """

    def __init__(self, taxonomy: TaxonomyStructure) -> None:
        self._taxonomy = taxonomy

    def validate(self, instance: XbrlInstance) -> list[ValidationFinding]:
        """Run all dimensional constraint checks and return the findings list."""
        findings: list[ValidationFinding] = []

        try:
            # Build a lookup: primary_item QName -> list of covering HypercubeModels.
            # We build this once so the per-fact loop is O(1) per concept.
            primary_to_hcs: dict[QName, list[HypercubeModel]] = {}
            for hc in self._taxonomy.hypercubes:
                for pi in hc.primary_items:
                    primary_to_hcs.setdefault(pi, []).append(hc)

            for fact in instance.facts:
                try:
                    self._validate_fact(fact, instance, primary_to_hcs, findings)
                except Exception as exc:  # noqa: BLE001
                    findings.append(
                        ValidationFinding(
                            rule_id="dimensional.unexpected_error",
                            severity=ValidationSeverity.ERROR,
                            message=(
                                f"Unexpected error while validating dimensions for fact "
                                f"'{fact.concept}' in context '{fact.context_ref}': {exc}"
                            ),
                            source="dimensional",
                            concept_qname=fact.concept,
                            context_ref=fact.context_ref,
                            constraint_type="UNEXPECTED_ERROR",
                        )
                    )
        except Exception as exc:  # noqa: BLE001
            findings.append(
                ValidationFinding(
                    rule_id="dimensional.unexpected_error",
                    severity=ValidationSeverity.ERROR,
                    message=f"Unexpected error during dimensional validation setup: {exc}",
                    source="dimensional",
                    constraint_type="UNEXPECTED_ERROR",
                )
            )

        return findings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_fact(
        self,
        fact,
        instance: XbrlInstance,
        primary_to_hcs: dict[QName, list[HypercubeModel]],
        findings: list[ValidationFinding],
    ) -> None:
        """Validate one fact against all covering hypercubes."""
        covering_hcs = primary_to_hcs.get(fact.concept)
        if not covering_hcs:
            # Concept is not part of any hypercube — not dimensional, skip.
            return

        context = instance.contexts.get(fact.context_ref)
        context_dims: dict[QName, QName] = context.dimensions if context is not None else {}

        for hc in covering_hcs:
            try:
                self._check_hypercube(fact, context_dims, hc, findings)
            except Exception as exc:  # noqa: BLE001
                findings.append(
                    ValidationFinding(
                        rule_id="dimensional.unexpected_error",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Unexpected error checking hypercube '{hc.qname}' for fact "
                            f"'{fact.concept}' in context '{fact.context_ref}': {exc}"
                        ),
                        source="dimensional",
                        concept_qname=fact.concept,
                        context_ref=fact.context_ref,
                        hypercube_qname=hc.qname,
                        constraint_type="UNEXPECTED_ERROR",
                    )
                )

    def _check_hypercube(
        self,
        fact,
        context_dims: dict[QName, QName],
        hc: HypercubeModel,
        findings: list[ValidationFinding],
    ) -> None:
        """Apply all four constraint types for one (fact, hypercube) pair."""
        hc_dim_set: set[QName] = set(hc.dimensions)

        # --- 1. UNDECLARED_DIMENSION -----------------------------------------
        # A dimension present in the context is not declared in this hypercube.
        # Only closed hypercubes disallow extra (undeclared) dimensions.
        if hc.closed:
            for dim_qname in context_dims:
                if dim_qname not in hc_dim_set:
                    findings.append(
                        ValidationFinding(
                            rule_id="xbrldie:PrimaryItemDimensionallyInvalidError",
                            severity=ValidationSeverity.ERROR,
                            message=(
                                f"Fact '{fact.concept}' in context '{fact.context_ref}' "
                                f"uses dimension '{dim_qname}' which is not declared in "
                                f"closed hypercube '{hc.qname}'."
                            ),
                            source="dimensional",
                            concept_qname=fact.concept,
                            context_ref=fact.context_ref,
                            hypercube_qname=hc.qname,
                            dimension_qname=dim_qname,
                            constraint_type="UNDECLARED_DIMENSION",
                        )
                    )

        # --- 2. INVALID_MEMBER -----------------------------------------------
        # A member assigned to a dimension is not in the dimension's declared member list.
        for dim_qname, member_qname in context_dims.items():
            # Only check dimensions that are actually declared in this hypercube.
            if dim_qname not in hc_dim_set:
                continue

            dim_model = self._taxonomy.dimensions.get(dim_qname)
            if dim_model is None:
                # Cannot validate — dimension model not loaded; skip silently.
                continue

            declared_members: set[QName] = {m.qname for m in dim_model.members}

            # If the dimension has no members at all (e.g. typed), skip member check.
            if not declared_members:
                continue

            if member_qname not in declared_members:
                findings.append(
                    ValidationFinding(
                        rule_id="xbrldie:PrimaryItemDimensionallyInvalidError",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Fact '{fact.concept}' in context '{fact.context_ref}' "
                            f"uses member '{member_qname}' for dimension '{dim_qname}', "
                            f"which is not a declared member of that dimension "
                            f"(hypercube '{hc.qname}')."
                        ),
                        source="dimensional",
                        concept_qname=fact.concept,
                        context_ref=fact.context_ref,
                        hypercube_qname=hc.qname,
                        dimension_qname=dim_qname,
                        constraint_type="INVALID_MEMBER",
                    )
                )

        # --- 3. CLOSED_MISSING_DIMENSION -------------------------------------
        # Applies only to "all" (positive) hypercubes that are closed.
        # A required dimension (no default member) is missing from the context.
        if hc.arcrole == "all" and hc.closed:
            for dim_qname in hc.dimensions:
                if dim_qname in context_dims:
                    # Dimension is present — no violation.
                    continue

                dim_model = self._taxonomy.dimensions.get(dim_qname)
                has_default = (
                    dim_model is not None and dim_model.default_member is not None
                )
                if not has_default:
                    findings.append(
                        ValidationFinding(
                            rule_id="xbrldie:PrimaryItemDimensionallyInvalidError",
                            severity=ValidationSeverity.ERROR,
                            message=(
                                f"Fact '{fact.concept}' in context '{fact.context_ref}' "
                                f"is missing required dimension '{dim_qname}' in closed "
                                f"hypercube '{hc.qname}' (no default member defined)."
                            ),
                            source="dimensional",
                            concept_qname=fact.concept,
                            context_ref=fact.context_ref,
                            hypercube_qname=hc.qname,
                            dimension_qname=dim_qname,
                            constraint_type="CLOSED_MISSING_DIMENSION",
                        )
                    )

        # --- 4. PROHIBITED_COMBINATION ---------------------------------------
        # Applies to "notAll" (negative) hypercubes.
        # The fact violates the notAll constraint when ALL dimensions of the
        # hypercube are present in the context (the prohibited combination is
        # fully satisfied).
        if hc.arcrole == "notAll":
            # A notAll hypercube with zero dimensions has no discriminating
            # constraints; skip it (degenerate/incomplete model).
            if not hc.dimensions:
                return
            all_dims_present = all(d in context_dims for d in hc.dimensions)
            if all_dims_present:
                # Report once per hypercube; use the first dimension (or None) as
                # the representative dimension_qname.
                representative_dim = hc.dimensions[0] if hc.dimensions else None
                findings.append(
                    ValidationFinding(
                        rule_id="xbrldie:PrimaryItemDimensionallyInvalidError",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Fact '{fact.concept}' in context '{fact.context_ref}' "
                            f"satisfies all dimensions of notAll hypercube '{hc.qname}', "
                            f"which is a prohibited dimensional combination."
                        ),
                        source="dimensional",
                        concept_qname=fact.concept,
                        context_ref=fact.context_ref,
                        hypercube_qname=hc.qname,
                        dimension_qname=representative_dim,
                        constraint_type="PROHIBITED_COMBINATION",
                    )
                )

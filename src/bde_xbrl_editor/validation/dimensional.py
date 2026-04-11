"""Dimensional constraint validator for XBRL instances."""

from __future__ import annotations

from bde_xbrl_editor.instance.models import XbrlInstance
from bde_xbrl_editor.taxonomy.models import HypercubeModel, QName, TaxonomyStructure
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

            # Build set of all concept QNames for ExplicitMemberUndefinedQNameError check.
            all_concept_qnames: set[QName] = set(self._taxonomy.concepts.keys())

            # Build the set of namespaces known to the DTS.  We only fire
            # ExplicitMemberUndefinedQNameError when the member's namespace is
            # actually in the DTS — if we never loaded a schema for that
            # namespace (e.g. because the instance has multiple schemaRefs and
            # we only followed one), we cannot determine whether the element
            # exists and must stay silent.
            dts_namespaces: set[str] = {q.namespace for q in all_concept_qnames}

            # Build dimension → default member map for DefaultValueUsedInInstanceError.
            dim_defaults: dict[QName, QName] = {}
            for dim_qname, dim_model in self._taxonomy.dimensions.items():
                if dim_model.default_member is not None:
                    dim_defaults[dim_qname] = dim_model.default_member

            # Instance-level checks on each context's explicit member declarations.
            for ctx_ref, ctx in instance.contexts.items():
                for dim_qname, member_qname in ctx.dimensions.items():
                    # ExplicitMemberNotExplicitDimensionError: the dimension QName used in
                    # xbrldi:explicitMember must actually be an explicit dimension in the DTS.
                    # Only applies to explicit members (typed members store dim_qname as
                    # their own placeholder value, so member_qname == dim_qname for typed).
                    # We determine whether a concept is an explicit dimension by checking its
                    # substitution group: it must be xbrldt:dimensionItem.
                    if member_qname != dim_qname and dim_qname.namespace in dts_namespaces:
                        concept_for_dim = self._taxonomy.concepts.get(dim_qname)
                        if concept_for_dim is not None:
                            sg = concept_for_dim.substitution_group
                            is_dim_item = (
                                sg is not None
                                and sg.namespace == "http://xbrl.org/2005/xbrldt"
                                and sg.local_name == "dimensionItem"
                            )
                            if not is_dim_item:
                                findings.append(
                                    ValidationFinding(
                                        rule_id="xbrldie:ExplicitMemberNotExplicitDimensionError",
                                        severity=ValidationSeverity.ERROR,
                                        message=(
                                            f"Context '{ctx_ref}' uses xbrldi:explicitMember for "
                                            f"'{dim_qname}', which is not an explicit dimension "
                                            f"in the DTS (substitution group: {sg})."
                                        ),
                                        source="dimensional",
                                        context_ref=ctx_ref,
                                        dimension_qname=dim_qname,
                                        constraint_type="EXPLICIT_MEMBER_NOT_EXPLICIT_DIMENSION",
                                    )
                                )
                                continue  # Skip further checks for this dimension

                    # TypedMemberNotTypedDimensionError: xbrldi:typedMember must reference
                    # a dimension element (substitutionGroup="xbrldt:dimensionItem").
                    # Both explicit and typed dimensions share this substitution group;
                    # typed dimensions additionally have xbrldt:typedDomainRef.
                    # We fire this error when the concept is present in the DTS but has
                    # a substitution group other than xbrldt:dimensionItem (e.g. hypercubeItem).
                    # Typed members are identified by member_qname == dim_qname (placeholder).
                    if member_qname == dim_qname and dim_qname.namespace in dts_namespaces:
                        concept_for_dim = self._taxonomy.concepts.get(dim_qname)
                        if concept_for_dim is not None:
                            sg = concept_for_dim.substitution_group
                            is_dimension_item = (
                                sg is not None
                                and sg.namespace == "http://xbrl.org/2005/xbrldt"
                                and sg.local_name == "dimensionItem"
                            )
                            if not is_dimension_item:
                                findings.append(
                                    ValidationFinding(
                                        rule_id="xbrldie:TypedMemberNotTypedDimensionError",
                                        severity=ValidationSeverity.ERROR,
                                        message=(
                                            f"Context '{ctx_ref}' uses xbrldi:typedMember for "
                                            f"'{dim_qname}', which is not a dimension element "
                                            f"in the DTS (substitution group: {sg})."
                                        ),
                                        source="dimensional",
                                        context_ref=ctx_ref,
                                        dimension_qname=dim_qname,
                                        constraint_type="TYPED_MEMBER_NOT_TYPED_DIMENSION",
                                    )
                                )
                                continue  # Skip further checks for this dimension

                    # ExplicitMemberUndefinedQNameError: member must be a global element
                    # in the DTS (i.e. a known concept).  Skip for typed members
                    # (member_qname == dim_qname placeholder) since typed members don't
                    # reference a global element as their value.
                    # Guard: only fire when the dimension's own namespace was loaded into
                    # the DTS — if the dimension itself comes from a schema we didn't
                    # follow (e.g. instance references a second taxonomy), we cannot
                    # validate anything about that dimension and must stay silent.
                    if (
                        member_qname != dim_qname
                        and member_qname not in all_concept_qnames
                        and dim_qname.namespace in dts_namespaces
                    ):
                        findings.append(
                            ValidationFinding(
                                rule_id="xbrldie:ExplicitMemberUndefinedQNameError",
                                severity=ValidationSeverity.ERROR,
                                message=(
                                    f"Context '{ctx_ref}' uses member '{member_qname}' "
                                    f"for dimension '{dim_qname}', which is not a "
                                    f"globally declared element in the DTS."
                                ),
                                source="dimensional",
                                context_ref=ctx_ref,
                                dimension_qname=dim_qname,
                                constraint_type="EXPLICIT_MEMBER_UNDEFINED_QNAME",
                            )
                        )

                    # DefaultValueUsedInInstanceError: context must not explicitly state
                    # the default member of a dimension.
                    default_member = dim_defaults.get(dim_qname)
                    if default_member is not None and member_qname == default_member:
                        findings.append(
                            ValidationFinding(
                                rule_id="xbrldie:DefaultValueUsedInInstanceError",
                                severity=ValidationSeverity.ERROR,
                                message=(
                                    f"Context '{ctx_ref}' explicitly uses default member "
                                    f"'{member_qname}' for dimension '{dim_qname}'. "
                                    f"Default members must not appear in instance contexts."
                                ),
                                source="dimensional",
                                context_ref=ctx_ref,
                                dimension_qname=dim_qname,
                                constraint_type="DEFAULT_VALUE_USED_IN_INSTANCE",
                            )
                        )

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
        """Validate one fact against all covering hypercubes.

        Per XBRL Dimensions §2.3.1: within each ELR, a fact is valid if it
        satisfies **at least one** positive ("all") hypercube in that ELR.
        Negative ("notAll") hypercubes are each an independent prohibition.
        """
        covering_hcs = primary_to_hcs.get(fact.concept)
        if not covering_hcs:
            # Concept is not part of any hypercube — not dimensional, skip.
            return

        context = instance.contexts.get(fact.context_ref)
        context_dims: dict[QName, QName] = context.dimensions if context is not None else {}

        # Separate positive and negative hypercubes.
        all_hcs = [hc for hc in covering_hcs if hc.arcrole == "all"]
        not_all_hcs = [hc for hc in covering_hcs if hc.arcrole == "notAll"]

        # notAll: each prohibited combination is checked independently.
        for hc in not_all_hcs:
            try:
                self._check_notall_hypercube(fact, context_dims, hc, findings, context)
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

        # all: per XBRL Dimensions §2.3.2 a fact is dimensionally valid when it
        # satisfies the constraints in at least one ELR where its concept is a
        # primary item.  We therefore group 'all' hypercubes by ELR and require
        # the fact to pass at least one HC within each ELR it participates in.
        #
        # BDE-specific note: the Agrupacion dimension (es-be-cm-dim:Agrupacion)
        # is encoded in xbrli:segment as a standard xbrldi:explicitMember and
        # MUST be declared in the taxonomy's definition linkbase hypercube(s).
        # If UNDECLARED_DIMENSION errors appear for Agrupacion it means the
        # taxonomy loader is not including it in the relevant hypercubes — fix
        # the taxonomy loader, do not relax the validator here.
        if all_hcs:
            elr_to_hcs: dict[str, list[HypercubeModel]] = {}
            for hc in all_hcs:
                elr_to_hcs.setdefault(hc.extended_link_role, []).append(hc)

            for elr, elr_hcs in elr_to_hcs.items():
                try:
                    self._check_all_hypercubes_for_elr(fact, context_dims, elr_hcs, findings, context)
                except Exception as exc:  # noqa: BLE001
                    findings.append(
                        ValidationFinding(
                            rule_id="dimensional.unexpected_error",
                            severity=ValidationSeverity.ERROR,
                            message=(
                                f"Unexpected error checking ELR '{elr}' hypercubes for fact "
                                f"'{fact.concept}' in context '{fact.context_ref}': {exc}"
                            ),
                            source="dimensional",
                            concept_qname=fact.concept,
                            context_ref=fact.context_ref,
                            constraint_type="UNEXPECTED_ERROR",
                        )
                    )

            # --- contextElement check (per XBRL Dimensions §2.3.1.1) ---
            # For each dimension in the context, if ALL covering 'all' HCs that include
            # this dimension require a specific container (segment/scenario), and the
            # dimension is in the OTHER container, report an error.
            # "Bi-locatable" dimensions (covered by HCs in both containers) are valid
            # in either location.
            if context is not None and hasattr(context, "dim_containers"):
                dim_containers = context.dim_containers
                for dim_qname, actual_container in dim_containers.items():
                    # Find all 'all' HCs that include this dimension
                    relevant_hcs = [
                        hc for hc in all_hcs
                        if dim_qname in hc.dimensions
                    ]
                    if not relevant_hcs:
                        continue
                    # Check if ANY HC accepts the dimension in its actual container
                    any_accepts = any(
                        hc.context_element == actual_container
                        for hc in relevant_hcs
                    )
                    if not any_accepts:
                        # All HCs require a different container — violation
                        # Report using the first relevant HC for context
                        first_hc = relevant_hcs[0]
                        required = first_hc.context_element
                        findings.append(
                            ValidationFinding(
                                rule_id="xbrldie:PrimaryItemDimensionallyInvalidError",
                                severity=ValidationSeverity.ERROR,
                                message=(
                                    f"Fact '{fact.concept}' in context '{fact.context_ref}' "
                                    f"has dimension '{dim_qname}' in '{actual_container}' "
                                    f"but all covering hypercubes require it in "
                                    f"'{required}'."
                                ),
                                source="dimensional",
                                concept_qname=fact.concept,
                                context_ref=fact.context_ref,
                                hypercube_qname=first_hc.qname,
                                dimension_qname=dim_qname,
                                constraint_type="CONTEXT_ELEMENT_MISMATCH",
                            )
                        )

    def _check_all_hypercubes_for_elr(
        self,
        fact,
        context_dims: dict[QName, QName],
        hcs: list[HypercubeModel],
        findings: list[ValidationFinding],
        context=None,
    ) -> None:
        """Fact is valid within an ELR if it passes at least one 'all' HC in that ELR.

        If no HC in this ELR accepts the fact, reports findings from the HC with
        the fewest errors (most likely the intended table's hypercube).
        """
        per_hc: list[tuple[HypercubeModel, list[ValidationFinding]]] = []
        for hc in hcs:
            hc_findings: list[ValidationFinding] = []
            self._check_all_hypercube(fact, context_dims, hc, hc_findings, context)
            if not hc_findings:
                return  # Satisfied at least one HC in this ELR — ELR is valid.
            per_hc.append((hc, hc_findings))

        # No HC in this ELR accepted the fact — report from the HC with fewest errors.
        if per_hc:
            _, best_findings = min(per_hc, key=lambda t: len(t[1]))
            findings.extend(best_findings)

    def _check_all_hypercube(
        self,
        fact,
        context_dims: dict[QName, QName],
        hc: HypercubeModel,
        findings: list[ValidationFinding],
        context=None,
    ) -> None:
        """Check one positive ('all') hypercube for a fact. Appends findings on failure."""
        hc_dim_set: set[QName] = set(hc.dimensions)

        # --- 1. UNDECLARED_DIMENSION -----------------------------------------
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
        for dim_qname, member_qname in context_dims.items():
            if dim_qname not in hc_dim_set:
                continue

            dim_model = self._taxonomy.dimensions.get(dim_qname)
            if dim_model is None:
                continue

            # Only usable members can appear in instance contexts (xbrldt:usable="false"
            # marks a member as non-usable — it may still be used as a parent in the
            # domain hierarchy but MUST NOT appear in xbrldi:explicitMember elements).
            # Multiple arcs may exist for the same member (override pattern): usable=False
            # on ANY arc for a member overrides usable=True from other arcs.
            member_usability: dict[QName, bool] = {}
            for m in dim_model.members:
                if m.qname not in member_usability:
                    member_usability[m.qname] = m.usable
                else:
                    member_usability[m.qname] = member_usability[m.qname] and m.usable
            declared_members: set[QName] = {qn for qn, u in member_usability.items() if u}
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
        if hc.closed:
            for dim_qname in hc.dimensions:
                if dim_qname in context_dims:
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

    def _check_notall_hypercube(
        self,
        fact,
        context_dims: dict[QName, QName],
        hc: HypercubeModel,
        findings: list[ValidationFinding],
        context=None,
    ) -> None:
        """Check one negative ('notAll') hypercube — each is an independent prohibition.

        Per XBRL Dimensions §2.4.3, a notAll hypercube is violated only when every
        declared dimension of the hypercube is present in the context AND each member
        used is a valid (declared) member of that dimension's domain.  If any dimension
        is absent or its member is not a declared domain member, the prohibition does
        not apply.
        """
        # A notAll hypercube with zero dimensions has no discriminating constraints.
        if not hc.dimensions:
            return

        for dim_qname in hc.dimensions:
            if dim_qname not in context_dims:
                # Required dimension absent — prohibition not triggered.
                return

            member_qname = context_dims[dim_qname]
            dim_model = self._taxonomy.dimensions.get(dim_qname)
            if dim_model is None:
                # Dimension has no model — can't evaluate membership.
                return

            declared_members: set[QName] = {m.qname for m in dim_model.members}
            if not declared_members:
                # No declared domain — any value satisfies the dimension but the
                # notAll constraint requires a known member to be triggered.
                return

            if member_qname not in declared_members:
                # Member not in declared domain — prohibition not triggered.
                return

        # All dimensions present with valid members — prohibition applies.
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

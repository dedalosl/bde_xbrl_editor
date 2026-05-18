"""XBRL 2.1 summation-item (calculation linkbase) consistency validation.

Rounds numeric facts using inferred decimals from precision (XBRL 2.1 §4.6 /
§5.2.5.2, post-errata), compares the weighted sum of contributors to each
summation fact. Rounding behaviour matches the widely used Arelle
``ValidateXbrlCalcs`` implementation in ``XBRL_v2_1`` mode (infer decimals).
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

from bde_xbrl_editor.instance.models import Fact, XbrlInstance
from bde_xbrl_editor.instance.s_equal import (
    canonical_context_refs_by_s_equal,
    canonical_unit_refs_by_structure,
)
from bde_xbrl_editor.taxonomy.models import CalculationArc, Concept, QName, TaxonomyStructure
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity

_NUMERIC_TYPE_KEYWORDS = ("monetary", "decimal", "integer", "float", "double")

_ZERO = Decimal(0)
_ONE = Decimal(1)
_TEN = Decimal(10)
_NAN = Decimal("NaN")


_FactKey = tuple[QName, tuple[int, ...], str, str | None]
_BindKey = tuple[tuple[int, ...], str, str | None]


def _tuple_path_prefixes(path: tuple[int, ...]) -> list[tuple[int, ...]]:
    return [path[:i] for i in range(len(path) + 1)]


@dataclass
class _CalculationFactIndex:
    item_facts: dict[_FactKey, list[tuple[Fact, Decimal]]]
    sum_facts: dict[_FactKey, list[tuple[Fact, Decimal]]]
    sum_bind_keys: dict[QName, set[_BindKey]]
    item_bind_keys: dict[QName, set[_BindKey]]
    dup_bind_keys: set[_BindKey]
    duplicate_fact_ids: set[int]


def _concept_is_numeric(concept: Concept) -> bool:
    ln = concept.data_type.local_name.lower()
    return any(k in ln for k in _NUMERIC_TYPE_KEYWORDS)


def _decimal_round(x: Decimal, d: int, rounding: str = ROUND_HALF_EVEN) -> Decimal:
    """Round *x* to *d* fraction digits (``d`` may be negative)."""
    if not x.is_normal() or not (-28 <= d <= 28):
        return x
    if d >= 0:
        return x.quantize(_ONE.scaleb(-d), rounding)
    scaled = x.scaleb(d).quantize(_ONE, rounding)
    return scaled * (_TEN ** (-d))


def _round_fact(
    fact: Fact,
    *,
    infer_decimals: bool = True,
    v_decimal: Decimal | None = None,
    concept: Concept | None = None,
) -> Decimal:
    """Round a fact's value, or an explicit ``v_decimal`` using *fact*'s decimals/precision."""
    if v_decimal is None:
        v_str = fact.value
        try:
            v_dec = Decimal(v_str.strip())
        except (InvalidOperation, AttributeError):
            v_dec = _NAN
        v_float_fact = float(v_str) if v_str and v_str.strip() else float("nan")
    else:
        v_dec = v_decimal
        if v_dec.is_nan():
            return v_dec
        v_str = None
        try:
            v_float_fact = float(fact.value)
        except (ValueError, TypeError):
            v_float_fact = float("nan")

    d_str = (
        fact.decimals
        if fact.decimals is not None
        else (concept.default_decimals if concept is not None else None)
    )
    p_str = (
        fact.precision
        if fact.precision is not None
        else (concept.default_precision if concept is not None else None)
    )
    if d_str == "INF" or p_str == "INF":
        return v_dec

    if infer_decimals:
        if p_str is not None and str(p_str).strip() != "":
            p = int(p_str)
            if p == 0:
                return _NAN
            if v_dec == 0:
                return _ZERO
            v_abs = abs(v_float_fact)
            if v_abs == 0 or math.isnan(v_float_fact):
                return _NAN
            d_int = p - int(math.floor(math.log10(v_abs))) - 1
            return _decimal_round(v_dec, d_int, ROUND_HALF_EVEN)
        if d_str is not None and str(d_str).strip() != "":
            d_int = int(d_str)
            return _decimal_round(v_dec, d_int, ROUND_HALF_EVEN)
        return v_dec

    # Legacy infer-precision path (unused for XBRL 2.1 conformance)
    return v_dec


def _fact_is_nil_numeric(fact: Fact) -> bool:
    return fact.is_nil or not (fact.value or "").strip()


def _fact_has_zero_precision(fact: Fact) -> bool:
    return str(fact.precision or "").strip() == "0"


class CalculationConsistencyValidator:
    """Validate summation-item relationships against instance facts."""

    def validate(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = self.validate_taxonomy(taxonomy)
        if not taxonomy.calculation:
            return findings

        canon_ctx = canonical_context_refs_by_s_equal(instance)
        canon_unit = canonical_unit_refs_by_structure(instance)

        fact_index = self._build_fact_index(instance, taxonomy, canon_ctx, canon_unit)

        for elr, arcs in taxonomy.calculation.items():
            findings.extend(
                self._validate_elr(
                    elr,
                    arcs,
                    taxonomy,
                    fact_index,
                )
            )
        return findings

    def validate_taxonomy(self, taxonomy: TaxonomyStructure) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for elr, arcs in taxonomy.calculation.items():
            findings.extend(self._validate_arc_endpoint_constraints(elr, arcs, taxonomy))
            findings.extend(self._validate_arc_balance_constraints(elr, arcs, taxonomy))
        return findings

    @staticmethod
    def _build_fact_index(
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure,
        canon_ctx: dict[str, str],
        canon_unit: dict[str, str],
    ) -> _CalculationFactIndex:
        item_facts: dict[_FactKey, list[tuple[Fact, Decimal]]] = defaultdict(list)
        sum_facts: dict[_FactKey, list[tuple[Fact, Decimal]]] = defaultdict(list)
        sum_bind_keys: dict[QName, set[_BindKey]] = defaultdict(set)
        item_bind_keys: dict[QName, set[_BindKey]] = defaultdict(set)
        dup_bind_keys: set[_BindKey] = set()
        duplicate_fact_ids: set[int] = set()
        duplicate_sum_keys: dict[_FactKey, Fact] = {}
        duplicate_item_keys: dict[_FactKey, Fact] = {}
        numeric_concepts = {
            qname
            for qname, concept in taxonomy.concepts.items()
            if not concept.abstract and _concept_is_numeric(concept)
        }

        for fact in instance.facts:
            if fact.concept not in numeric_concepts:
                continue
            if fact.context_ref not in instance.contexts:
                continue
            if fact.unit_ref is None:
                continue
            bind_ctx = canon_ctx.get(fact.context_ref, fact.context_ref)
            bind_unit = canon_unit.get(fact.unit_ref, fact.unit_ref)
            parent_path = fact.tuple_path
            prefix_paths = _tuple_path_prefixes(parent_path)

            sum_key: _FactKey = (fact.concept, parent_path, bind_ctx, bind_unit)
            prior_sum = duplicate_sum_keys.get(sum_key)
            if prior_sum is not None and prior_sum is not fact:
                dup_bind_keys.add((parent_path, bind_ctx, bind_unit))
                duplicate_fact_ids.add(id(prior_sum))
                duplicate_fact_ids.add(id(fact))
            else:
                duplicate_sum_keys[sum_key] = fact

            item_immediate_key: _FactKey = (fact.concept, parent_path, bind_ctx, bind_unit)
            prior_item = duplicate_item_keys.get(item_immediate_key)
            if prior_item is not None and prior_item is not fact:
                dup_bind_keys.add((parent_path, bind_ctx, bind_unit))
                duplicate_fact_ids.add(id(prior_item))
                duplicate_fact_ids.add(id(fact))
            else:
                duplicate_item_keys[item_immediate_key] = fact

            if _fact_is_nil_numeric(fact):
                continue
            try:
                Decimal(fact.value.strip())
            except (InvalidOperation, AttributeError):
                continue
            rounded_value = _round_fact(
                fact, infer_decimals=True, concept=taxonomy.concepts.get(fact.concept)
            )

            for anc_path in prefix_paths:
                item_key: _FactKey = (fact.concept, anc_path, bind_ctx, bind_unit)
                item_facts[item_key].append((fact, rounded_value))
                item_bind_keys[fact.concept].add((anc_path, bind_ctx, bind_unit))

            sum_facts[sum_key].append((fact, rounded_value))
            for anc_path in prefix_paths:
                sum_bind_keys[fact.concept].add((anc_path, bind_ctx, bind_unit))

        return _CalculationFactIndex(
            item_facts=dict(item_facts),
            sum_facts=dict(sum_facts),
            sum_bind_keys=dict(sum_bind_keys),
            item_bind_keys=dict(item_bind_keys),
            dup_bind_keys=dup_bind_keys,
            duplicate_fact_ids=duplicate_fact_ids,
        )

    @staticmethod
    def _validate_arc_balance_constraints(
        elr: str,
        arcs: list[CalculationArc],
        taxonomy: TaxonomyStructure,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for arc in arcs:
            if arc.use == "prohibited":
                continue
            parent = taxonomy.concepts.get(arc.parent)
            child = taxonomy.concepts.get(arc.child)
            if parent is None or child is None:
                continue
            if arc.weight == 0:
                findings.append(
                    ValidationFinding(
                        rule_id="calculation:invalid-weight",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Calculation arc from '{arc.parent}' to '{arc.child}' in "
                            f"link role '{elr}' has weight 0; summation-item weights "
                            "must be non-zero."
                        ),
                        source="calculation",
                        concept_qname=arc.parent,
                    )
                )
                continue
            if parent.balance not in {"debit", "credit"} or child.balance not in {
                "debit",
                "credit",
            }:
                continue
            same_balance = parent.balance == child.balance
            sign_is_positive = arc.weight > 0
            if same_balance != sign_is_positive:
                findings.append(
                    ValidationFinding(
                        rule_id="calculation:balance-weight-inconsistent",
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"Calculation arc from '{arc.parent}' ({parent.balance}) to "
                            f"'{arc.child}' ({child.balance}) in link role '{elr}' has "
                            f"weight {arc.weight}; same balances require positive "
                            "weights and opposite balances require negative weights."
                        ),
                        source="calculation",
                        concept_qname=arc.parent,
                    )
                )
        return findings

    @staticmethod
    def _validate_arc_endpoint_constraints(
        elr: str,
        arcs: list[CalculationArc],
        taxonomy: TaxonomyStructure,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for arc in arcs:
            if arc.use == "prohibited":
                continue
            parent = taxonomy.concepts.get(arc.parent)
            child = taxonomy.concepts.get(arc.child)
            if parent is None or child is None:
                continue
            bad_endpoints: list[str] = []
            if parent.abstract or not _concept_is_numeric(parent):
                bad_endpoints.append(f"summation '{arc.parent}'")
            if child.abstract or not _concept_is_numeric(child):
                bad_endpoints.append(f"item '{arc.child}'")
            if not bad_endpoints:
                continue
            findings.append(
                ValidationFinding(
                    rule_id="calculation:invalid-endpoint",
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"Calculation arc in link role '{elr}' has non-numeric "
                        f"endpoint(s): {', '.join(bad_endpoints)}."
                    ),
                    source="calculation",
                    concept_qname=arc.parent,
                )
            )
        return findings

    @staticmethod
    def _effective_summation_arcs(arcs: list[CalculationArc]) -> list[CalculationArc]:
        """Resolve equivalent summation-item arcs inside one ELR (XBRL 2.1 arc overrides, 3.5.3.9).

        Arcs judged equivalent share the same ``equivalence_key``. Among each group only the arcs
        with the highest numeric ``priority`` survive; among that tier ``use=\"prohibited\"``
        arcs suppress the relationship whenever present (including ties with optional arcs).
        """
        keyed_groups: defaultdict[tuple[object, ...], list[CalculationArc]] = defaultdict(list)
        unkeyed_sets: list[list[CalculationArc]] = []

        for arc in arcs:
            if arc.equivalence_key:
                keyed_groups[tuple(arc.equivalence_key)].append(arc)
            else:
                unkeyed_sets.append([arc])

        def normalize_use(use: str | None) -> str:
            result = (use or "optional").strip() or "optional"
            return result

        effective: list[CalculationArc] = []

        def resolve_group(group: list[CalculationArc]) -> None:
            max_pri = max(a.priority for a in group)
            tier = [a for a in group if a.priority == max_pri]

            # Among highest-priority equivalent arcs any prohibition suppresses this relationship.
            if any(normalize_use(a.use) == "prohibited" for a in tier):
                return

            non_prohibited = [
                a for a in tier
                if normalize_use(a.use) != "prohibited"
            ]
            if non_prohibited:
                effective.append(non_prohibited[0])

        for group in keyed_groups.values():
            resolve_group(group)
        for group in unkeyed_sets:
            resolve_group(group)

        return effective

    def _validate_elr(
        self,
        elr: str,
        arcs: list[CalculationArc],
        taxonomy: TaxonomyStructure,
        fact_index: _CalculationFactIndex,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        if not arcs:
            return findings

        active_arcs = self._effective_summation_arcs(arcs)

        by_parent: dict[QName, list[CalculationArc]] = defaultdict(list)
        for arc in active_arcs:
            if arc.parent == arc.child:
                continue
            by_parent[arc.parent].append(arc)

        for sum_concept, rel_arcs in by_parent.items():
            if sum_concept not in taxonomy.concepts:
                continue
            sum_concept_def = taxonomy.concepts[sum_concept]
            if sum_concept_def.abstract or not _concept_is_numeric(sum_concept_def):
                continue

            bound_sum_keys: set[_BindKey] = set()
            for arc in rel_arcs:
                child = arc.child
                if child not in taxonomy.concepts:
                    continue
                bound_sum_keys |= fact_index.sum_bind_keys.get(
                    sum_concept, set()
                ) & fact_index.item_bind_keys.get(child, set())

            for anc_path, bind_ctx, bind_unit in bound_sum_keys:
                sum_key: _FactKey = (sum_concept, anc_path, bind_ctx, bind_unit)
                if (anc_path, bind_ctx, bind_unit) in fact_index.dup_bind_keys:
                    continue
                raw_sum_entries = fact_index.sum_facts.get(sum_key, ())
                if len(raw_sum_entries) > 1:
                    continue
                sum_entries = [
                    entry
                    for entry in raw_sum_entries
                    if not _fact_is_nil_numeric(entry[0])
                ]
                if not sum_entries:
                    continue

                bound_sum = _ZERO
                bound_items_have_zero_precision = False
                contributors_seen = False
                for arc in rel_arcs:
                    w = Decimal(str(arc.weight))
                    item_key: _FactKey = (arc.child, anc_path, bind_ctx, bind_unit)
                    for item_fact, rounded_item in fact_index.item_facts.get(item_key, ()):
                        if id(item_fact) in fact_index.duplicate_fact_ids:
                            continue
                        contributors_seen = True
                        bound_items_have_zero_precision = (
                            bound_items_have_zero_precision
                            or _fact_has_zero_precision(item_fact)
                        )
                        bound_sum += rounded_item * w

                if not contributors_seen:
                    continue

                for sum_fact, rounded_sum in sum_entries:

                    rounded_items_sum = _round_fact(
                        sum_fact,
                        infer_decimals=True,
                        v_decimal=bound_sum,
                        concept=taxonomy.concepts.get(sum_fact.concept),
                    )
                    if rounded_items_sum.is_nan() or rounded_sum.is_nan():
                        if not (
                            _fact_has_zero_precision(sum_fact) or bound_items_have_zero_precision
                        ):
                            continue
                    elif rounded_items_sum == rounded_sum:
                        continue

                    unreported: list[str] = []
                    for arc in rel_arcs:
                        item_key = (arc.child, anc_path, bind_ctx, bind_unit)
                        if not fact_index.item_facts.get(item_key):
                            unreported.append(str(arc.child))

                    findings.append(
                        ValidationFinding(
                            rule_id="calculation:summation-inconsistent",
                            severity=ValidationSeverity.ERROR,
                            message=(
                                f"Calculation inconsistent for summation concept "
                                f"'{sum_concept}' in link role '{elr}': reported rounded "
                                f"total {rounded_sum} vs computed {rounded_items_sum} "
                                f"(context '{bind_ctx}', unit '{bind_unit}'). "
                                f"Missing or nil contributing facts: "
                                f"{', '.join(unreported) if unreported else 'none'}."
                            ),
                            source="calculation",
                            concept_qname=sum_concept,
                            context_ref=bind_ctx,
                        )
                    )
                    break

        return findings

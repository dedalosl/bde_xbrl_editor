"""XBRL 2.1 summation-item (calculation linkbase) consistency validation.

Rounds numeric facts using inferred decimals from precision (XBRL 2.1 §4.6 /
§5.2.5.2, post-errata), compares the weighted sum of contributors to each
summation fact. Rounding behaviour matches the widely used Arelle
``ValidateXbrlCalcs`` implementation in ``XBRL_v2_1`` mode (infer decimals).
"""

from __future__ import annotations

import math
from collections import defaultdict
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation

from bde_xbrl_editor.instance.models import Fact, XbrlInstance
from bde_xbrl_editor.instance.s_equal import canonical_context_refs_by_s_equal
from bde_xbrl_editor.taxonomy.models import CalculationArc, Concept, QName, TaxonomyStructure
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity

_NUMERIC_TYPE_KEYWORDS = ("monetary", "decimal", "integer", "float", "double")

_ZERO = Decimal(0)
_ONE = Decimal(1)
_TEN = Decimal(10)
_NAN = Decimal("NaN")


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

    d_str = fact.decimals
    p_str = fact.precision
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
    return not (fact.value or "").strip()


def _calc_key(
    fact: Fact,
    canon_ctx: dict[str, str],
) -> tuple[QName, str, str | None] | None:
    if fact.unit_ref is None:
        return None
    ctx_bind = canon_ctx.get(fact.context_ref, fact.context_ref)
    return (fact.concept, ctx_bind, fact.unit_ref)


class CalculationConsistencyValidator:
    """Validate summation-item relationships against instance facts."""

    def validate(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        if not taxonomy.calculation:
            return findings

        canon_ctx = canonical_context_refs_by_s_equal(instance)

        # Index numeric facts by (concept, S-equal canonical context_ref, unit_ref)
        by_key: dict[tuple[QName, str, str | None], list[Fact]] = defaultdict(list)
        for fact in instance.facts:
            concept = taxonomy.concepts.get(fact.concept)
            if concept is None or concept.abstract or not _concept_is_numeric(concept):
                continue
            if fact.context_ref not in instance.contexts:
                continue
            key = _calc_key(fact, canon_ctx)
            if key is None:
                continue
            by_key[key].append(fact)

        duplicate_blocked: set[tuple[QName, str, str | None]] = set()
        for key, flist in by_key.items():
            if len(flist) > 1:
                duplicate_blocked.add(key)

        for elr, arcs in taxonomy.calculation.items():
            findings.extend(
                self._validate_elr(
                    elr,
                    arcs,
                    taxonomy,
                    by_key,
                    duplicate_blocked,
                )
            )
        return findings

    def _validate_elr(
        self,
        elr: str,
        arcs: list[CalculationArc],
        taxonomy: TaxonomyStructure,
        by_key: dict[tuple[QName, str, str | None], list[Fact]],
        duplicate_blocked: set[tuple[QName, str, str | None]],
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        if not arcs:
            return findings

        prohibited = {
            arc.equivalence_key
            for arc in arcs
            if arc.use == "prohibited" and arc.equivalence_key
        }
        active_arcs = [
            arc
            for arc in arcs
            if arc.use != "prohibited"
            and (not arc.equivalence_key or arc.equivalence_key not in prohibited)
        ]

        by_parent: dict[QName, list[CalculationArc]] = defaultdict(list)
        for arc in active_arcs:
            if arc.parent == arc.child:
                continue
            by_parent[arc.parent].append(arc)

        item_bind_keys: dict[QName, set[tuple[str, str | None]]] = defaultdict(set)
        sum_bind_keys: dict[QName, set[tuple[str, str | None]]] = defaultdict(set)

        for key in by_key:
            concept, ctx_ref, unit_ref = key
            item_bind_keys[concept].add((ctx_ref, unit_ref))
            sum_bind_keys[concept].add((ctx_ref, unit_ref))

        for sum_concept, rel_arcs in by_parent.items():
            if sum_concept not in taxonomy.concepts:
                continue
            sum_concept_def = taxonomy.concepts[sum_concept]
            if sum_concept_def.abstract or not _concept_is_numeric(sum_concept_def):
                continue

            bound_sum_keys: set[tuple[str, str | None]] = set()
            for arc in rel_arcs:
                child = arc.child
                if child not in taxonomy.concepts:
                    continue
                bound_sum_keys |= sum_bind_keys[sum_concept] & item_bind_keys[child]

            for ctx_ref, unit_ref in bound_sum_keys:
                key_sum = (sum_concept, ctx_ref, unit_ref)
                sum_facts = by_key.get(key_sum, [])
                if not sum_facts:
                    continue

                dup_row = key_sum in duplicate_blocked
                if not dup_row:
                    for arc in rel_arcs:
                        ik = (arc.child, ctx_ref, unit_ref)
                        if ik in duplicate_blocked:
                            dup_row = True
                            break

                bound_sum = _ZERO
                if not dup_row:
                    for arc in rel_arcs:
                        w = Decimal(str(arc.weight))
                        item_key = (arc.child, ctx_ref, unit_ref)
                        for item_fact in by_key.get(item_key, ()):
                            if _fact_is_nil_numeric(item_fact):
                                continue
                            try:
                                _ = Decimal(item_fact.value.strip())
                            except (InvalidOperation, AttributeError):
                                continue
                            rounded_item = _round_fact(item_fact, infer_decimals=True)
                            if rounded_item.is_nan():
                                continue
                            bound_sum += rounded_item * w

                for sum_fact in sum_facts:
                    if _fact_is_nil_numeric(sum_fact):
                        continue
                    if key_sum in duplicate_blocked:
                        continue
                    try:
                        _ = Decimal(sum_fact.value.strip())
                    except (InvalidOperation, AttributeError):
                        continue
                    if dup_row:
                        continue

                    rounded_sum = _round_fact(sum_fact, infer_decimals=True)
                    if rounded_sum.is_nan():
                        continue
                    rounded_items_sum = _round_fact(
                        sum_fact,
                        infer_decimals=True,
                        v_decimal=bound_sum,
                    )
                    if rounded_items_sum.is_nan():
                        continue
                    if rounded_items_sum != rounded_sum:
                        unreported: list[str] = []
                        for arc in rel_arcs:
                            ik = (arc.child, ctx_ref, unit_ref)
                            if ik not in by_key or not any(
                                not _fact_is_nil_numeric(f) for f in by_key[ik]
                            ):
                                unreported.append(str(arc.child))

                        findings.append(
                            ValidationFinding(
                                rule_id="calculation:summation-inconsistent",
                                severity=ValidationSeverity.ERROR,
                                message=(
                                    f"Calculation inconsistent for summation concept "
                                    f"'{sum_concept}' in link role '{elr}': reported rounded "
                                    f"total {rounded_sum} vs computed {rounded_items_sum} "
                                    f"(context '{ctx_ref}', unit '{unit_ref}'). "
                                    f"Missing or nil contributing facts: "
                                    f"{', '.join(unreported) if unreported else 'none'}."
                                ),
                                source="calculation",
                                concept_qname=sum_concept,
                                context_ref=ctx_ref,
                            )
                        )
                        break

        return findings

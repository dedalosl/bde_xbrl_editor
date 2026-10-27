"""XBRL 2.1 essence-alias closure validation (instance and taxonomy)."""

from __future__ import annotations

import threading
from collections import Counter, defaultdict
from decimal import InvalidOperation

from bde_xbrl_editor.instance.models import Fact, XbrlInstance, XbrlUnit
from bde_xbrl_editor.instance.s_equal import canonical_context_refs_by_s_equal
from bde_xbrl_editor.taxonomy.models import Concept, QName, TaxonomyStructure
from bde_xbrl_editor.taxonomy.type_traits import concept_is_numeric
from bde_xbrl_editor.validation.calculation import _fact_is_nil_numeric, _round_fact
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity

_ARCROLE_ESSENCE_ALIAS = "http://www.xbrl.org/2003/arcrole/essence-alias"


def _unit_signature(unit: XbrlUnit) -> tuple:
    def _counter_key(values: tuple) -> tuple:
        return tuple(sorted(Counter(values).items(), key=lambda item: str(item[0])))

    if unit.unit_form == "divide":
        return (
            "divide",
            _counter_key(unit.numerator_measure_qnames),
            _counter_key(unit.denominator_measure_qnames),
        )
    if unit.simple_measure_qnames:
        measures = unit.simple_measure_qnames
    elif unit.measure_qname is not None:
        measures = (unit.measure_qname,)
    else:
        measures = ()
    return ("simple", _counter_key(measures))


def _units_u_equal(instance: XbrlInstance, left_ref: str | None, right_ref: str | None) -> bool:
    if left_ref is None or right_ref is None:
        return left_ref == right_ref
    left = instance.units.get(left_ref)
    right = instance.units.get(right_ref)
    if left is None or right is None:
        return left_ref == right_ref
    return _unit_signature(left) == _unit_signature(right)


_EssenceKey = tuple[QName, tuple[int, ...], str]


def _concept_is_numeric(concept: Concept) -> bool:
    return concept_is_numeric(concept)


def _alias_values_equal(left: Fact, right: Fact, taxonomy: TaxonomyStructure) -> bool:
    concept = taxonomy.concepts.get(left.concept)
    if concept is not None and _concept_is_numeric(concept):
        return _numeric_values_equal(left, right, taxonomy)
    if _fact_is_nil_numeric(left) and _fact_is_nil_numeric(right):
        return True
    if _fact_is_nil_numeric(left) or _fact_is_nil_numeric(right):
        return False
    return (left.value or "").strip() == (right.value or "").strip()


def _numeric_values_equal(left: Fact, right: Fact, taxonomy: TaxonomyStructure) -> bool:
    if _fact_is_nil_numeric(left) and _fact_is_nil_numeric(right):
        return True
    if _fact_is_nil_numeric(left) or _fact_is_nil_numeric(right):
        return False
    try:
        left_dec = _round_fact(
            left,
            infer_decimals=True,
            concept=taxonomy.concepts.get(left.concept),
        )
        right_dec = _round_fact(
            right,
            infer_decimals=True,
            concept=taxonomy.concepts.get(right.concept),
        )
    except (InvalidOperation, AttributeError):
        return (left.value or "").strip() == (right.value or "").strip()
    return left_dec == right_dec


class EssenceAliasValidator:
    """Validate essence-alias relationships in taxonomy and instances."""

    def __init__(self, cancel_event: threading.Event | None = None) -> None:
        self._cancel_event = cancel_event

    def _cancelled(self) -> bool:
        return bool(self._cancel_event and self._cancel_event.is_set())

    def validate_taxonomy(self, taxonomy: TaxonomyStructure) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        if self._cancelled():
            return findings

        for elr, arcs in taxonomy.definition.items():
            if self._cancelled():
                break
            for arc in arcs:
                if self._cancelled():
                    return findings
                if arc.arcrole != _ARCROLE_ESSENCE_ALIAS:
                    continue
                essence = taxonomy.concepts.get(arc.source)
                alias = taxonomy.concepts.get(arc.target)
                if essence is None or alias is None:
                    continue
                if essence.data_type != alias.data_type:
                    findings.append(
                        ValidationFinding(
                            rule_id="essence-alias:incompatible-type",
                            severity=ValidationSeverity.ERROR,
                            message=(
                                f"Essence-alias from '{arc.source}' to '{arc.target}' in "
                                f"link role '{elr}' relates concepts with different item types."
                            ),
                            source="essence-alias",
                            concept_qname=arc.source,
                        )
                    )
                if essence.period_type != alias.period_type:
                    findings.append(
                        ValidationFinding(
                            rule_id="essence-alias:incompatible-period-type",
                            severity=ValidationSeverity.ERROR,
                            message=(
                                f"Essence-alias from '{arc.source}' to '{arc.target}' in "
                                f"link role '{elr}' relates concepts with different period types."
                            ),
                            source="essence-alias",
                            concept_qname=arc.source,
                        )
                    )
        return findings

    def validate(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        if self._cancelled():
            return findings

        essence_arcs = [
            arc
            for arcs in taxonomy.definition.values()
            for arc in arcs
            if arc.arcrole == _ARCROLE_ESSENCE_ALIAS
        ]
        if not essence_arcs:
            return findings

        canon_ctx = canonical_context_refs_by_s_equal(instance, taxonomy)
        es_facts: dict[_EssenceKey, list[Fact]] = defaultdict(list)
        for fact in instance.facts:
            if self._cancelled():
                return findings
            if fact.context_ref not in instance.contexts:
                continue
            bind_ctx = canon_ctx.get(fact.context_ref, fact.context_ref)
            es_facts[(fact.concept, fact.tuple_path, bind_ctx)].append(fact)

        essence_bind: dict[QName, set[tuple[tuple[int, ...], str]]] = defaultdict(set)
        for (concept, anc_path, bind_ctx), _facts in es_facts.items():
            essence_bind[concept].add((anc_path, bind_ctx))

        seen: set[tuple[QName, QName, str, tuple[int, ...], str, str]] = set()
        for arc in essence_arcs:
            if self._cancelled():
                return findings
            bound_keys = essence_bind.get(arc.source, set()) & essence_bind.get(arc.target, set())
            for anc_path, bind_ctx in bound_keys:
                if self._cancelled():
                    return findings
                essence_facts = es_facts.get((arc.source, anc_path, bind_ctx), ())
                alias_facts = es_facts.get((arc.target, anc_path, bind_ctx), ())
                if not essence_facts or not alias_facts:
                    continue
                essence_concept = taxonomy.concepts.get(arc.source)
                numeric_pair = essence_concept is not None and _concept_is_numeric(
                    essence_concept
                )
                for essence_fact in essence_facts:
                    if self._cancelled():
                        return findings
                    for alias_fact in alias_facts:
                        if self._cancelled():
                            return findings
                        pair_key = (arc.source, arc.target, bind_ctx, anc_path)
                        if pair_key in seen:
                            continue
                        seen.add(pair_key)
                        if numeric_pair:
                            if essence_fact.unit_ref is None or alias_fact.unit_ref is None:
                                continue
                            if not _units_u_equal(
                                instance,
                                essence_fact.unit_ref,
                                alias_fact.unit_ref,
                            ):
                                findings.append(
                                    ValidationFinding(
                                        rule_id="essence-alias:unit-inconsistent",
                                        severity=ValidationSeverity.ERROR,
                                        message=(
                                            f"Essence-alias '{arc.source}' and '{arc.target}' in "
                                            f"context '{bind_ctx}' use non-equivalent units."
                                        ),
                                        source="essence-alias",
                                        concept_qname=arc.source,
                                        context_ref=bind_ctx,
                                    )
                                )
                                continue
                        if not _alias_values_equal(essence_fact, alias_fact, taxonomy):
                            findings.append(
                                ValidationFinding(
                                    rule_id="essence-alias:value-inconsistent",
                                    severity=ValidationSeverity.ERROR,
                                    message=(
                                        f"Essence-alias '{arc.source}' and '{arc.target}' in "
                                        f"context '{bind_ctx}' report non-equivalent values."
                                    ),
                                    source="essence-alias",
                                    concept_qname=arc.source,
                                    context_ref=bind_ctx,
                                )
                            )
        return findings

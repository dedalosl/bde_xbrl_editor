"""Unit tests for context_builder — SHA-256 determinism, deduplication, filing context."""

from __future__ import annotations

from datetime import date

from bde_xbrl_editor.instance.context_builder import (
    build_filing_indicator_context,
    deduplicate_contexts,
    generate_context_id,
)
from bde_xbrl_editor.instance.models import ReportingEntity, ReportingPeriod
from bde_xbrl_editor.taxonomy.models import QName


def _entity() -> ReportingEntity:
    return ReportingEntity(identifier="ES0123456789", scheme="http://www.bde.es/")


def _instant_period() -> ReportingPeriod:
    return ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31))


def _duration_period() -> ReportingPeriod:
    return ReportingPeriod(
        period_type="duration",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )


class TestGenerateContextId:
    def test_same_inputs_produce_same_id(self):
        e, p = _entity(), _instant_period()
        id1 = generate_context_id(e, p)
        id2 = generate_context_id(e, p)
        assert id1 == id2

    def test_id_starts_with_ctx_prefix(self):
        ctx_id = generate_context_id(_entity(), _instant_period())
        assert ctx_id.startswith("ctx_")

    def test_id_has_8_hex_chars(self):
        ctx_id = generate_context_id(_entity(), _instant_period())
        # format: "ctx_<8 hex chars>"
        hex_part = ctx_id[4:]
        assert len(hex_part) == 8
        assert all(c in "0123456789abcdef" for c in hex_part)

    def test_different_entities_give_different_ids(self):
        p = _instant_period()
        e1 = ReportingEntity(identifier="AA", scheme="http://example.com/")
        e2 = ReportingEntity(identifier="BB", scheme="http://example.com/")
        assert generate_context_id(e1, p) != generate_context_id(e2, p)

    def test_different_periods_give_different_ids(self):
        e = _entity()
        p1 = ReportingPeriod(period_type="instant", instant_date=date(2023, 12, 31))
        p2 = ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31))
        assert generate_context_id(e, p1) != generate_context_id(e, p2)

    def test_different_dimensions_give_different_ids(self):
        e, p = _entity(), _instant_period()
        dim = QName("http://example.com/ns", "DimA")
        mem1 = QName("http://example.com/ns", "Mem1")
        mem2 = QName("http://example.com/ns", "Mem2")
        id1 = generate_context_id(e, p, {dim: mem1})
        id2 = generate_context_id(e, p, {dim: mem2})
        assert id1 != id2

    def test_no_dimensions_and_empty_dict_equivalent(self):
        e, p = _entity(), _instant_period()
        assert generate_context_id(e, p) == generate_context_id(e, p, {})

    def test_duration_period_deterministic(self):
        e, p = _entity(), _duration_period()
        assert generate_context_id(e, p) == generate_context_id(e, p)


class TestBuildFilingIndicatorContext:
    def test_returns_xbrl_context(self):
        ctx = build_filing_indicator_context(_entity(), _instant_period())
        assert ctx is not None
        assert ctx.context_id.startswith("ctx_")

    def test_no_dimensions(self):
        ctx = build_filing_indicator_context(_entity(), _instant_period())
        assert ctx.dimensions == {}

    def test_entity_and_period_preserved(self):
        e, p = _entity(), _instant_period()
        ctx = build_filing_indicator_context(e, p)
        assert ctx.entity is e
        assert ctx.period is p

    def test_default_context_element_is_scenario(self):
        ctx = build_filing_indicator_context(_entity(), _instant_period())
        assert ctx.context_element == "scenario"

    def test_can_override_context_element(self):
        ctx = build_filing_indicator_context(
            _entity(), _instant_period(), context_element="segment"
        )
        assert ctx.context_element == "segment"


class TestDeduplicateContexts:
    def test_same_id_deduplicated(self):
        e, p = _entity(), _instant_period()
        ctx1 = build_filing_indicator_context(e, p)
        ctx2 = build_filing_indicator_context(e, p)
        result = deduplicate_contexts([ctx1, ctx2])
        assert len(result) == 1

    def test_different_ids_kept(self):
        e = _entity()
        p1 = ReportingPeriod(period_type="instant", instant_date=date(2023, 12, 31))
        p2 = ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31))
        ctx1 = build_filing_indicator_context(e, p1)
        ctx2 = build_filing_indicator_context(e, p2)
        result = deduplicate_contexts([ctx1, ctx2])
        assert len(result) == 2

    def test_empty_list_returns_empty_dict(self):
        assert deduplicate_contexts([]) == {}

    def test_result_keyed_by_context_id(self):
        ctx = build_filing_indicator_context(_entity(), _instant_period())
        result = deduplicate_contexts([ctx])
        assert ctx.context_id in result

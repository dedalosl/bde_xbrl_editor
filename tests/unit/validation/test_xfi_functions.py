"""Unit tests for xfi: function implementations (validation/formula/xfi_functions.py)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from bde_xbrl_editor.instance.models import (
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlContext,
    XbrlUnit,
)
from bde_xbrl_editor.taxonomy.models import QName
from bde_xbrl_editor.validation.formula.xfi_functions import (
    clear_evaluation_context,
    set_evaluation_context,
    xfi_decimal,
    xfi_entity,
    xfi_period,
    xfi_unit,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entity(identifier: str = "ENT001", scheme: str = "http://www.example.com") -> ReportingEntity:
    return ReportingEntity(identifier=identifier, scheme=scheme)


def _instant_ctx(ctx_id: str = "ctx1", instant: date | None = None) -> XbrlContext:
    return XbrlContext(
        context_id=ctx_id,
        entity=_entity(),
        period=ReportingPeriod(
            period_type="instant",
            instant_date=instant or date(2024, 12, 31),
        ),
    )


def _duration_ctx(
    ctx_id: str = "ctx2",
    start: date | None = None,
    end: date | None = None,
) -> XbrlContext:
    return XbrlContext(
        context_id=ctx_id,
        entity=_entity(),
        period=ReportingPeriod(
            period_type="duration",
            start_date=start or date(2024, 1, 1),
            end_date=end or date(2024, 12, 31),
        ),
    )


def _fact(
    local: str = "Amount",
    ctx_id: str = "ctx1",
    value: str = "100",
    decimals: str | None = None,
) -> Fact:
    return Fact(
        concept=QName(namespace="http://example.com", local_name=local),
        context_ref=ctx_id,
        unit_ref=None,
        value=value,
        decimals=decimals,
    )


def _unit(measure: str = "iso4217:EUR") -> XbrlUnit:
    return XbrlUnit(unit_id="EUR", measure_uri=measure)


def _set_ctx(binding: dict) -> None:
    set_evaluation_context(binding)


# ---------------------------------------------------------------------------
# Ensure context is cleared between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_context():
    """Clear the evaluation context before and after each test."""
    clear_evaluation_context()
    yield
    clear_evaluation_context()


# ---------------------------------------------------------------------------
# xfi_period
# ---------------------------------------------------------------------------


class TestXfiPeriod:
    def test_instant_period_returns_date_string(self) -> None:
        """xfi_period returns the instant date string for an instant context."""
        ctx = _instant_ctx(instant=date(2024, 12, 31))
        _set_ctx({"_context": ctx})
        result = xfi_period()
        assert result == "2024-12-31"

    def test_duration_period_returns_range_string(self) -> None:
        """xfi_period returns 'start/end' for a duration context."""
        ctx = _duration_ctx(start=date(2024, 1, 1), end=date(2024, 12, 31))
        _set_ctx({"_context": ctx})
        result = xfi_period()
        assert result == "2024-01-01/2024-12-31"

    def test_no_context_returns_empty_string(self) -> None:
        """xfi_period returns '' when _context is not in the evaluation context."""
        _set_ctx({})
        result = xfi_period()
        assert result == ""

    def test_context_none_returns_empty_string(self) -> None:
        """xfi_period returns '' when _context is explicitly None."""
        _set_ctx({"_context": None})
        result = xfi_period()
        assert result == ""

    def test_instant_period_with_specific_date(self) -> None:
        """xfi_period returns the exact instant date set on the context."""
        ctx = _instant_ctx(instant=date(2020, 6, 30))
        _set_ctx({"_context": ctx})
        assert xfi_period() == "2020-06-30"


# ---------------------------------------------------------------------------
# xfi_entity
# ---------------------------------------------------------------------------


class TestXfiEntity:
    def test_returns_entity_identifier(self) -> None:
        """xfi_entity returns the entity identifier from the context."""
        ctx = _instant_ctx()
        ctx.entity.identifier = "BANK001"
        _set_ctx({"_context": ctx})
        result = xfi_entity()
        assert result == "BANK001"

    def test_no_context_returns_empty_string(self) -> None:
        """xfi_entity returns '' when _context is absent."""
        _set_ctx({})
        assert xfi_entity() == ""

    def test_context_none_returns_empty_string(self) -> None:
        """xfi_entity returns '' when _context is None."""
        _set_ctx({"_context": None})
        assert xfi_entity() == ""

    def test_entity_identifier_content_preserved(self) -> None:
        """xfi_entity returns the full identifier string including special chars."""
        ctx = _instant_ctx()
        ctx.entity.identifier = "LEI-12345-ABCDE"
        _set_ctx({"_context": ctx})
        assert xfi_entity() == "LEI-12345-ABCDE"


# ---------------------------------------------------------------------------
# xfi_unit
# ---------------------------------------------------------------------------


class TestXfiUnit:
    def test_returns_measure_uri(self) -> None:
        """xfi_unit returns the measure_uri of the current unit."""
        unit = _unit("iso4217:EUR")
        _set_ctx({"_unit": unit})
        assert xfi_unit() == "iso4217:EUR"

    def test_no_unit_returns_empty_string(self) -> None:
        """xfi_unit returns '' when _unit is absent from context."""
        _set_ctx({})
        assert xfi_unit() == ""

    def test_unit_none_returns_empty_string(self) -> None:
        """xfi_unit returns '' when _unit is explicitly None."""
        _set_ctx({"_unit": None})
        assert xfi_unit() == ""

    def test_pure_unit_measure_uri(self) -> None:
        """xfi_unit correctly returns the measure_uri for a pure (dimensionless) unit."""
        unit = XbrlUnit(unit_id="pure", measure_uri="xbrli:pure")
        _set_ctx({"_unit": unit})
        assert xfi_unit() == "xbrli:pure"


# ---------------------------------------------------------------------------
# xfi_decimal
# ---------------------------------------------------------------------------


class TestXfiDecimal:
    def test_returns_decimal_attribute_as_int(self) -> None:
        """xfi_decimal returns the decimals attribute of the current fact as an int."""
        fact = _fact(decimals="2")
        _set_ctx({"_current_fact": fact})
        assert xfi_decimal() == 2

    def test_no_fact_returns_zero(self) -> None:
        """xfi_decimal returns 0 when _current_fact is absent."""
        _set_ctx({})
        assert xfi_decimal() == 0

    def test_fact_none_returns_zero(self) -> None:
        """xfi_decimal returns 0 when _current_fact is None."""
        _set_ctx({"_current_fact": None})
        assert xfi_decimal() == 0

    def test_fact_decimals_none_returns_zero(self) -> None:
        """xfi_decimal returns 0 when the fact's decimals attribute is None."""
        fact = _fact(decimals=None)
        _set_ctx({"_current_fact": fact})
        assert xfi_decimal() == 0

    def test_invalid_decimals_string_returns_zero(self) -> None:
        """xfi_decimal returns 0 when the decimals attribute cannot be parsed as int."""
        fact = _fact(decimals="INF")
        # "INF" cannot be converted with int(), so should return 0
        _set_ctx({"_current_fact": fact})
        assert xfi_decimal() == 0

    def test_negative_decimals_value(self) -> None:
        """xfi_decimal handles negative decimals (e.g. -3 for thousands rounding)."""
        fact = _fact(decimals="-3")
        _set_ctx({"_current_fact": fact})
        assert xfi_decimal() == -3

    def test_zero_decimals(self) -> None:
        """xfi_decimal returns 0 when decimals is '0'."""
        fact = _fact(decimals="0")
        _set_ctx({"_current_fact": fact})
        assert xfi_decimal() == 0


# ---------------------------------------------------------------------------
# set_evaluation_context / clear_evaluation_context
# ---------------------------------------------------------------------------


class TestContextManagement:
    def test_set_then_clear(self) -> None:
        """After clear_evaluation_context, all xfi: functions return empty/zero defaults."""
        ctx = _instant_ctx()
        unit = _unit()
        fact = _fact(decimals="4")
        set_evaluation_context({"_context": ctx, "_unit": unit, "_current_fact": fact})
        # Confirm values are accessible
        assert xfi_period() != ""
        assert xfi_unit() != ""
        assert xfi_decimal() == 4
        # Clear and verify defaults restored
        clear_evaluation_context()
        assert xfi_period() == ""
        assert xfi_entity() == ""
        assert xfi_unit() == ""
        assert xfi_decimal() == 0

    def test_set_overwrites_previous_context(self) -> None:
        """set_evaluation_context replaces any previously set context."""
        ctx1 = _instant_ctx("ctx1", instant=date(2023, 12, 31))
        ctx2 = _instant_ctx("ctx2", instant=date(2024, 6, 30))
        set_evaluation_context({"_context": ctx1})
        assert xfi_period() == "2023-12-31"
        set_evaluation_context({"_context": ctx2})
        assert xfi_period() == "2024-06-30"

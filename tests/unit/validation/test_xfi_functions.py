"""Unit tests for xfi: function implementations (validation/formula/xfi_functions.py)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
import elementpath

from bde_xbrl_editor.instance.models import (
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlContext,
    XbrlUnit,
)
from bde_xbrl_editor.taxonomy.models import QName
from bde_xbrl_editor.validation.formula.xfi_functions import (
    build_formula_parser,
    clear_evaluation_context,
    iaf_numeric_add,
    iaf_sum,
    set_evaluation_context,
    xfi_decimal,          # backward-compat alias
    xfi_decimals,
    xfi_entity,
    xfi_is_instant_period,
    xfi_is_duration_period,
    xfi_period,
    xfi_period_instant,
    xfi_period_start,
    xfi_period_end,
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
# xfi_period / xfi_is_instant_period / xfi_period_instant
# ---------------------------------------------------------------------------


class TestXfiPeriod:
    def test_period_returns_reporting_period_for_instant_ctx(self) -> None:
        """xfi_period returns a ReportingPeriod for an instant context."""
        ctx = _instant_ctx(instant=date(2024, 12, 31))
        _set_ctx({"_context": ctx})
        result = xfi_period(None)
        assert isinstance(result, ReportingPeriod)
        assert result.period_type == "instant"
        assert result.instant_date == date(2024, 12, 31)

    def test_period_returns_reporting_period_for_duration_ctx(self) -> None:
        """xfi_period returns a ReportingPeriod for a duration context."""
        ctx = _duration_ctx(start=date(2024, 1, 1), end=date(2024, 12, 31))
        _set_ctx({"_context": ctx})
        result = xfi_period(None)
        assert isinstance(result, ReportingPeriod)
        assert result.period_type == "duration"

    def test_no_context_returns_empty_string(self) -> None:
        """xfi_period returns '' when _context is not in the evaluation context."""
        _set_ctx({})
        result = xfi_period(None)
        assert result == ""

    def test_context_none_returns_empty_string(self) -> None:
        """xfi_period returns '' when _context is explicitly None."""
        _set_ctx({"_context": None})
        result = xfi_period(None)
        assert result == ""

    def test_is_instant_period_true_for_instant(self) -> None:
        """xfi_is_instant_period returns True for an instant period."""
        ctx = _instant_ctx()
        _set_ctx({"_context": ctx})
        assert xfi_is_instant_period(None) is True

    def test_is_instant_period_false_for_duration(self) -> None:
        """xfi_is_instant_period returns False for a duration period."""
        ctx = _duration_ctx()
        _set_ctx({"_context": ctx})
        assert xfi_is_instant_period(None) is False

    def test_is_duration_period_true_for_duration(self) -> None:
        """xfi_is_duration_period returns True for a duration period."""
        ctx = _duration_ctx()
        _set_ctx({"_context": ctx})
        assert xfi_is_duration_period(None) is True

    def test_period_instant_returns_date_object(self) -> None:
        """xfi_period_instant returns an elementpath Date10 for an instant period."""
        ctx = _instant_ctx(instant=date(2024, 12, 31))
        period = ctx.period
        result = xfi_period_instant(period)
        assert result is not None
        assert str(result) == "2024-12-31"

    def test_period_start_returns_date_object(self) -> None:
        """xfi_period_start returns a Date10 for a duration period."""
        ctx = _duration_ctx(start=date(2024, 1, 1), end=date(2024, 12, 31))
        period = ctx.period
        result = xfi_period_start(period)
        assert result is not None
        assert str(result) == "2024-01-01"

    def test_period_end_returns_date_object(self) -> None:
        """xfi_period_end returns a Date10 for a duration period."""
        ctx = _duration_ctx(start=date(2024, 1, 1), end=date(2024, 12, 31))
        period = ctx.period
        result = xfi_period_end(period)
        assert result is not None
        assert str(result) == "2024-12-31"


# ---------------------------------------------------------------------------
# xfi_entity
# ---------------------------------------------------------------------------


class TestXfiEntity:
    def test_returns_entity_identifier(self) -> None:
        """xfi_entity returns the entity identifier from the context."""
        ctx = XbrlContext(
            context_id="ctx1",
            entity=_entity(identifier="BANK001"),
            period=ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31)),
        )
        _set_ctx({"_context": ctx})
        result = xfi_entity(None)
        assert result == "BANK001"

    def test_no_context_returns_empty_string(self) -> None:
        """xfi_entity returns '' when _context is absent."""
        _set_ctx({})
        assert xfi_entity(None) == ""

    def test_context_none_returns_empty_string(self) -> None:
        """xfi_entity returns '' when _context is None."""
        _set_ctx({"_context": None})
        assert xfi_entity(None) == ""

    def test_entity_identifier_content_preserved(self) -> None:
        """xfi_entity returns the full identifier string including special chars."""
        ctx = XbrlContext(
            context_id="ctx1",
            entity=_entity(identifier="LEI-12345-ABCDE"),
            period=ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31)),
        )
        _set_ctx({"_context": ctx})
        assert xfi_entity(None) == "LEI-12345-ABCDE"


# ---------------------------------------------------------------------------
# xfi_unit
# ---------------------------------------------------------------------------


class TestXfiUnit:
    def test_returns_measure_uri(self) -> None:
        """xfi_unit returns the measure_uri of the current unit."""
        unit = _unit("iso4217:EUR")
        _set_ctx({"_unit": unit})
        assert xfi_unit(None) == "iso4217:EUR"

    def test_no_unit_returns_empty_string(self) -> None:
        """xfi_unit returns '' when _unit is absent from context."""
        _set_ctx({})
        assert xfi_unit(None) == ""

    def test_unit_none_returns_empty_string(self) -> None:
        """xfi_unit returns '' when _unit is explicitly None."""
        _set_ctx({"_unit": None})
        assert xfi_unit(None) == ""

    def test_pure_unit_measure_uri(self) -> None:
        """xfi_unit correctly returns the measure_uri for a pure (dimensionless) unit."""
        unit = XbrlUnit(unit_id="pure", measure_uri="xbrli:pure")
        _set_ctx({"_unit": unit})
        assert xfi_unit(None) == "xbrli:pure"


# ---------------------------------------------------------------------------
# xfi_decimals / xfi_decimal (alias)
# ---------------------------------------------------------------------------


class TestXfiDecimal:
    def test_returns_decimal_attribute_as_int(self) -> None:
        """xfi_decimals returns the decimals attribute of the current fact as an int."""
        fact = _fact(decimals="2")
        _set_ctx({"_current_fact": fact})
        assert xfi_decimals(None) == 2

    def test_backward_compat_alias(self) -> None:
        """xfi_decimal() (old alias) works without arguments."""
        fact = _fact(decimals="3")
        _set_ctx({"_current_fact": fact})
        assert xfi_decimal() == 3

    def test_no_fact_returns_zero(self) -> None:
        """xfi_decimals returns 0 when _current_fact is absent."""
        _set_ctx({})
        assert xfi_decimals(None) == 0

    def test_fact_none_returns_zero(self) -> None:
        """xfi_decimals returns 0 when _current_fact is None."""
        _set_ctx({"_current_fact": None})
        assert xfi_decimals(None) == 0

    def test_fact_decimals_none_returns_zero(self) -> None:
        """xfi_decimals returns 0 when the fact's decimals attribute is None."""
        fact = _fact(decimals=None)
        _set_ctx({"_current_fact": fact})
        assert xfi_decimals(None) == 0

    def test_invalid_decimals_string_returns_zero(self) -> None:
        """xfi_decimals returns 0 when the decimals attribute cannot be parsed as int."""
        fact = _fact(decimals="INF")
        _set_ctx({"_current_fact": fact})
        assert xfi_decimals(None) == 0

    def test_negative_decimals_value(self) -> None:
        """xfi_decimals handles negative decimals (e.g. -3 for thousands rounding)."""
        fact = _fact(decimals="-3")
        _set_ctx({"_current_fact": fact})
        assert xfi_decimals(None) == -3

    def test_zero_decimals(self) -> None:
        """xfi_decimals returns 0 when decimals is '0'."""
        fact = _fact(decimals="0")
        _set_ctx({"_current_fact": fact})
        assert xfi_decimals(None) == 0


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
        assert xfi_period(None) != ""
        assert xfi_unit(None) != ""
        assert xfi_decimals(None) == 4
        # Clear and verify defaults restored
        clear_evaluation_context()
        assert xfi_period(None) == ""
        assert xfi_entity(None) == ""
        assert xfi_unit(None) == ""
        assert xfi_decimals(None) == 0

    def test_set_overwrites_previous_context(self) -> None:
        """set_evaluation_context replaces any previously set context."""
        ctx1 = _instant_ctx("ctx1", instant=date(2023, 12, 31))
        ctx2 = _instant_ctx("ctx2", instant=date(2024, 6, 30))
        set_evaluation_context({"_context": ctx1})
        p1 = xfi_period(None)
        assert isinstance(p1, ReportingPeriod) and p1.instant_date == date(2023, 12, 31)
        set_evaluation_context({"_context": ctx2})
        p2 = xfi_period(None)
        assert isinstance(p2, ReportingPeriod) and p2.instant_date == date(2024, 6, 30)


class TestIafFunctions:
    def test_iaf_sum_flattens_python_sequences(self) -> None:
        """iaf_sum handles a direct Python sequence of numeric values."""
        assert iaf_sum([Decimal("1.5"), "2.5", 3]) == Decimal("7.0")

    def test_iaf_sum_accepts_xpath_sequence_argument(self) -> None:
        """The registered iaf:sum function accepts a multi-item XPath sequence."""
        parser = build_formula_parser({})
        token = parser.parse("iaf:sum($values)")
        ctx = elementpath.XPathContext(root=None, item=Decimal("0"), variables={"values": [1, 2, 3]})

        result = list(token.select(ctx))

        assert result == [Decimal("6")]

    def test_iaf_numeric_add_adds_two_values(self) -> None:
        """iaf_numeric_add coerces and adds two scalar values."""
        assert iaf_numeric_add("1.25", Decimal("2.75")) == Decimal("4.00")

    def test_iaf_numeric_add_is_registered_in_xpath_parser(self) -> None:
        """The registered iaf:numeric-add function is available to XPath evaluation."""
        parser = build_formula_parser({})
        token = parser.parse("iaf:numeric-add($left, $right)")
        ctx = elementpath.XPathContext(
            root=None,
            item=Decimal("0"),
            variables={"left": Decimal("10.5"), "right": "2.25"},
        )

        result = list(token.select(ctx))

        assert result == [Decimal("12.75")]

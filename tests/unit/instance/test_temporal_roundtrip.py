"""Exact dateUnion semantics survive the public instance save/reopen path."""

from datetime import date

import pytest
from lxml import etree

from bde_xbrl_editor.instance.constants import XBRLI_NS
from bde_xbrl_editor.instance.context_builder import generate_context_id
from bde_xbrl_editor.instance.parser import _parse_context
from bde_xbrl_editor.instance.s_equal import context_s_equal_key
from bde_xbrl_editor.instance.serializer import InstanceSerializer
from bde_xbrl_editor.validation.formula.xfi_functions import xfi_period_instant


def context(instant):
    return _parse_context(
        etree.fromstring(
            f'<context xmlns="{XBRLI_NS}" id="time"><entity>'
            '<identifier scheme="urn:entity">entity</identifier></entity>'
            f"<period><instant>{instant}</instant></period></context>"
        )
    )


@pytest.mark.parametrize(
    "left,right,equal",
    [
        ("2025-01-01T12:00:00", "2025-01-01T13:00:00", False),
        ("2025-01-01T12:00:00Z", "2025-01-01T13:00:00+01:00", True),
        ("2025-01-01T00:00:00+01:00", "2024-12-31T23:00:00Z", True),
        ("2025-01-01T12:00:00", "2025-01-01T12:00:00Z", False),
        ("2025-01-01T12:00:00.123456789", "2025-01-01T12:00:00.123456788", False),
        ("2025-01-01T12:00:00.1234567890Z", "2025-01-01T13:00:00.123456789+01:00", True),
        ("2025-01-01", "2025-01-02T00:00:00", True),
        ("2025-01-01+01:00", "2025-01-01T23:00:00Z", True),
        ("2025-01-01T24:00:00", "2025-01-02T00:00:00", True),
    ],
)
def test_temporal_equality_and_context_ids(left, right, equal):
    a, b = context(left), context(right)
    assert (context_s_equal_key(a) == context_s_equal_key(b)) is equal
    assert (
        generate_context_id(a.entity, a.period) == generate_context_id(b.entity, b.period)
    ) is equal


@pytest.mark.parametrize(
    "lexical,expected",
    [
        ("2025-01-01T12:30:00Z", "2025-01-01T12:30:00Z"),
        ("2025-01-01T12:30:00.123456789+02:00", "2025-01-01T12:30:00.123456789+02:00"),
        ("2025-01-01+02:00", "2025-01-01+02:00"),
        ("2025-01-01T24:00:00Z", "2025-01-02T00:00:00Z"),
        ("2025-01-01", "2025-01-01"),
    ],
)
def test_public_temporal_roundtrip(tmp_path, lexical, expected):
    from tests.integration.instance.test_edit_roundtrip import (
        _make_parser,
        _make_taxonomy,
        _write_instance,
    )

    parser = _make_parser(_make_taxonomy())
    path = _write_instance(tmp_path)
    root = etree.parse(str(path))
    root.find(f".//{{{XBRLI_NS}}}instant").text = lexical
    root.write(str(path))
    instance, _ = parser.load(path)
    original = next(iter(instance.contexts.values()))
    saved = tmp_path / "saved.xbrl"
    InstanceSerializer().save(instance, saved)
    assert etree.parse(str(saved)).find(f".//{{{XBRLI_NS}}}instant").text == expected
    reopened, _ = parser.load(saved)
    assert context_s_equal_key(next(iter(reopened.contexts.values()))) == context_s_equal_key(
        original
    )


def test_xfi_keeps_time_offset_and_supported_precision():
    assert (
        str(xfi_period_instant(context("2025-01-01T12:30:00.123456+02:00").period))
        == "2025-01-01T12:30:00.123456+02:00"
    )


def test_xfi_rejects_precision_it_cannot_represent_without_changing_core():
    period = context("2025-01-01T12:30:00.123456789Z").period
    with pytest.raises(ValueError, match="precision"):
        xfi_period_instant(period)


def test_editing_calendar_date_does_not_restore_stale_source_date():
    ctx = context("2025-01-01T12:30:00Z")
    ctx.period.instant_date = date(2025, 2, 1)
    assert context_s_equal_key(ctx) == context_s_equal_key(context("2025-02-01T12:30:00Z"))


def duration(start, end):
    return _parse_context(
        etree.fromstring(
            f'<context xmlns="{XBRLI_NS}" id="time"><entity>'
            '<identifier scheme="urn:entity">entity</identifier></entity>'
            f"<period><startDate>{start}</startDate><endDate>{end}</endDate></period></context>"
        )
    )


def test_duration_boundaries_and_offsets():
    from bde_xbrl_editor.validation.formula.xfi_functions import xfi_period_end, xfi_period_start

    a = duration("2025-01-01+02:00", "2025-01-01+02:00")
    b = duration("2024-12-31T22:00:00Z", "2025-01-01T22:00:00Z")
    assert context_s_equal_key(a) == context_s_equal_key(b)
    assert str(xfi_period_start(a.period)) == "2025-01-01T00:00:00+02:00"
    assert str(xfi_period_end(a.period)) == "2025-01-02T00:00:00+02:00"


def test_public_duration_roundtrip(tmp_path):
    from tests.integration.instance.test_edit_roundtrip import (
        _make_parser,
        _make_taxonomy,
        _write_instance,
    )

    parser = _make_parser(_make_taxonomy())
    path = _write_instance(tmp_path)
    root = etree.parse(str(path))
    period = root.find(f".//{{{XBRLI_NS}}}period")
    period.remove(period[0])
    etree.SubElement(
        period, f"{{{XBRLI_NS}}}startDate"
    ).text = "2024-12-31T12:30:00.123456789+02:00"
    etree.SubElement(period, f"{{{XBRLI_NS}}}endDate").text = "2025-01-01+02:00"
    root.write(str(path))
    instance, _ = parser.load(path)
    saved = tmp_path / "duration.xbrl"
    InstanceSerializer().save(instance, saved)
    reopened, _ = parser.load(saved)
    assert context_s_equal_key(reopened.contexts["C1"]) == context_s_equal_key(
        instance.contexts["C1"]
    )
    result = etree.parse(str(saved))
    assert result.find(f".//{{{XBRLI_NS}}}startDate").text == period[0].text
    assert result.find(f".//{{{XBRLI_NS}}}endDate").text == period[1].text


def test_schema_default_equality_path_uses_current_exact_period():
    from bde_xbrl_editor.taxonomy.models import QName, SchemaElementDefaults

    a, b = context("2025-01-01T12:00:00Z"), context("2025-01-01T13:00:00+01:00")
    a.scenario_xml = b.scenario_xml = (
        f'<scenario xmlns="{XBRLI_NS}"><note xmlns="urn:test"/></scenario>'.encode()
    )
    defaults = {QName("urn:test", "note"): SchemaElementDefaults()}
    assert context_s_equal_key(a, defaults) == context_s_equal_key(b, defaults)
    b.period.instant_date = date(2025, 1, 2)
    assert context_s_equal_key(a, defaults) != context_s_equal_key(b, defaults)


def test_duration_with_reverse_clock_time_is_rejected():
    with pytest.raises(ValueError, match="later"):
        duration("2025-01-01T13:00:00Z", "2025-01-01T12:00:00Z")


def test_duration_cross_calendar_offsets_are_compared_as_instants():
    # Calendar dates appear reversed, but the end is 25 hours after the start.
    ctx = duration("2025-01-02T00:00:00+14:00", "2025-01-01T23:00:00-12:00")
    assert ctx.period.period_type == "duration"


def test_xfi_boundary_equality_uses_exact_instants():
    from types import SimpleNamespace

    from bde_xbrl_editor.instance.models import Fact
    from bde_xbrl_editor.taxonomy.models import QName
    from bde_xbrl_editor.validation.formula.xfi_functions import (
        clear_evaluation_context,
        set_evaluation_context,
        xfi_end_equal,
        xfi_start_equal,
    )

    a = duration("2025-01-01T12:00:00Z", "2025-01-02T12:00:00Z")
    b = duration("2025-01-01T13:00:00Z", "2025-01-02T13:00:00Z")
    facts = [Fact(QName("urn:test", "item"), key, None, "1") for key in ("a", "b")]
    set_evaluation_context({"_instance": SimpleNamespace(contexts={"a": a, "b": b})})
    try:
        assert not xfi_start_equal(*facts)
        assert not xfi_end_equal(*facts)
    finally:
        clear_evaluation_context()


@pytest.mark.parametrize(
    "kind,lexical",
    [
        ("instant", "2025-01-01T12:30:00.123456Z"),
        ("instant", "2025-01-01+02:00"),
        ("duration", "2025-01-01T12:30:00.123456+02:00"),
    ],
)
def test_formula_output_period_rule_preserves_temporal_value(kind, lexical):
    from types import SimpleNamespace

    from bde_xbrl_editor.instance.temporal import period_key
    from bde_xbrl_editor.taxonomy.models import FormulaAspectRule
    from bde_xbrl_editor.validation.formula.output_instance import FormulaOutputInstanceEvaluator

    child = (
        '<instant value="value"/>' if kind == "instant" else '<duration start="start" end="end"/>'
    )
    rule = FormulaAspectRule(aspect="period", raw_xml=f"<period>{child}</period>".encode())
    fake = SimpleNamespace(
        _evaluate_single=lambda expression, *args: (
            "2024-01-01" if expression == "start" else lexical
        )
    )
    expected = context(lexical) if kind == "instant" else duration("2024-01-01", lexical)
    actual = FormulaOutputInstanceEvaluator._period_from_rule(
        fake, None, rule, expected.period, {}, None, {}
    )
    assert period_key(actual) == period_key(expected.period)


@pytest.mark.parametrize("precision,unsupported", [("123456", False), ("123456789", True)])
def test_xfi_runtime_reports_unsupported_precision_instead_of_truncating(precision, unsupported):
    from bde_xbrl_editor.taxonomy.models import FactVariableDefinition, FormulaOutputDefinition
    from bde_xbrl_editor.validation.formula.output_runtime import OutputFormulaRuntimeEvaluator
    from tests.unit.validation.test_formula_output_runtime import _instance, _qn, _taxonomy

    instance = _instance()
    instance.contexts["ctx1"].period = context(f"2025-01-01T12:30:00.{precision}Z").period
    formula = FormulaOutputDefinition(
        formula_id="time",
        label=None,
        value_xpath="if (hours-from-dateTime(xfi:period-instant(xfi:period($a))) = 12) then 1 else 1 div 0",
        source=None,
        aspect_model=None,
        implicit_filtering=True,
        variables=(FactVariableDefinition(variable_name="a", concept_filter=_qn("Amount")),),
    )
    findings = OutputFormulaRuntimeEvaluator(_taxonomy(formula)).evaluate_runtime_errors(instance)
    if unsupported:
        assert findings
        assert "precision" in findings[0].message.lower()
    else:
        assert not findings

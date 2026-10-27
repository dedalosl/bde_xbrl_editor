"""Unit tests for XbrlTypeValidator."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bde_xbrl_editor.instance.validator import XbrlTypeValidator
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_XBRLI_NS = "http://www.xbrl.org/2003/instance"
_TEST_NS = "http://example.com/test"


def _qname(local: str, ns: str = _TEST_NS) -> QName:
    return QName(namespace=ns, local_name=local)


def _concept(local: str, type_local: str) -> Concept:
    return Concept(
        qname=_qname(local),
        data_type=QName(namespace=_XBRLI_NS, local_name=type_local),
        period_type="instant",
    )


def _make_validator(*concepts: Concept) -> XbrlTypeValidator:
    meta = TaxonomyMetadata(
        name="Test",
        version="1.0",
        publisher="Test",
        entry_point_path=Path("/tmp/e.xsd"),
        loaded_at=datetime.now(),
        declared_languages=("en",),
    )
    concept_map = {c.qname: c for c in concepts}
    taxonomy = TaxonomyStructure(
        metadata=meta,
        concepts=concept_map,
        labels=MagicMock(),
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
    )
    return XbrlTypeValidator(taxonomy)


# ---------------------------------------------------------------------------
# Monetary
# ---------------------------------------------------------------------------


def test_monetary_valid_simple() -> None:
    v = _make_validator(_concept("Amount", "monetaryItemType"))
    ok, msg = v.validate("1000.50", _qname("Amount"))
    assert ok
    assert msg == ""


def test_monetary_rejects_thousands_sep() -> None:
    v = _make_validator(_concept("Amount", "monetaryItemType"))
    ok, _ = v.validate("1,000.50", _qname("Amount"))
    assert not ok


def test_monetary_invalid() -> None:
    v = _make_validator(_concept("Amount", "monetaryItemType"))
    ok, msg = v.validate("not-a-number", _qname("Amount"))
    assert not ok
    assert msg != ""


def test_monetary_normalise_preserves_mixed_comma_dot_input() -> None:
    v = _make_validator(_concept("Amount", "monetaryItemType"))
    result = v.normalise("1,234.56", _qname("Amount"))
    assert result == "1,234.56"


def test_monetary_normalise_preserves_mixed_dot_comma_input() -> None:
    v = _make_validator(_concept("Amount", "monetaryItemType"))
    result = v.normalise("1.234,56", _qname("Amount"))
    assert result == "1.234,56"


# ---------------------------------------------------------------------------
# Decimal
# ---------------------------------------------------------------------------


def test_decimal_valid() -> None:
    v = _make_validator(_concept("Ratio", "decimalItemType"))
    ok, _ = v.validate("0.5432", _qname("Ratio"))
    assert ok


def test_decimal_invalid() -> None:
    v = _make_validator(_concept("Ratio", "decimalItemType"))
    ok, msg = v.validate("abc", _qname("Ratio"))
    assert not ok
    assert msg != ""


# ---------------------------------------------------------------------------
# Integer
# ---------------------------------------------------------------------------


def test_integer_valid() -> None:
    v = _make_validator(_concept("Count", "integerItemType"))
    ok, _ = v.validate("42", _qname("Count"))
    assert ok


@pytest.mark.parametrize(
    "value",
    [
        "12.9",
        "12.bad",
        "abc",
        "-1.5",
        "12,9",
        "1,234",
        "1,000,000",
        "1.000",
        "１２",
        "١٢",
        "1_000",
        "+",
        "",
    ],
)
def test_integer_rejects_non_integer_lexical_input(value: str) -> None:
    validator = _make_validator(_concept("Count", "integerItemType"))
    valid, message = validator.validate(value, _qname("Count"))
    assert not valid
    assert message
    assert validator.normalise(value, _qname("Count")) == value


@pytest.mark.parametrize(
    "value",
    ["+42", "-42", "00042", "0", "9" * 5000],
    ids=["positive-sign", "negative-sign", "leading-zeros", "zero", "5000-digits"],
)
def test_integer_preserves_signed_and_large_ascii_values(value: str) -> None:
    validator = _make_validator(_concept("Count", "integerItemType"))
    assert validator.validate(value, _qname("Count")) == (True, "")
    assert validator.normalise(value, _qname("Count")) == value


def test_integer_normalise_trims_only_valid_input() -> None:
    validator = _make_validator(_concept("Count", "integerItemType"))
    assert validator.validate("  +42  ", _qname("Count")) == (True, "")
    assert validator.normalise("  +42  ", _qname("Count")) == "+42"
    assert validator.normalise("  12.9  ", _qname("Count")) == "  12.9  "


# ---------------------------------------------------------------------------
# Date
# ---------------------------------------------------------------------------


def test_date_valid_iso() -> None:
    v = _make_validator(_concept("ReportDate", "dateItemType"))
    ok, _ = v.validate("2023-12-31", _qname("ReportDate"))
    assert ok


def test_date_invalid_format() -> None:
    v = _make_validator(_concept("ReportDate", "dateItemType"))
    ok, msg = v.validate("31/12/2023", _qname("ReportDate"))
    assert not ok
    assert "YYYY-MM-DD" in msg


def test_date_invalid_value() -> None:
    v = _make_validator(_concept("ReportDate", "dateItemType"))
    ok, msg = v.validate("2023-13-01", _qname("ReportDate"))
    assert not ok


# ---------------------------------------------------------------------------
# Boolean
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("val", ["true", "false", "1", "0", "True", "False"])
def test_boolean_valid(val: str) -> None:
    v = _make_validator(_concept("IsActive", "booleanItemType"))
    ok, _ = v.validate(val, _qname("IsActive"))
    assert ok


def test_boolean_invalid() -> None:
    v = _make_validator(_concept("IsActive", "booleanItemType"))
    ok, msg = v.validate("yes", _qname("IsActive"))
    assert not ok
    assert msg != ""


def test_boolean_normalise_true() -> None:
    v = _make_validator(_concept("IsActive", "booleanItemType"))
    assert v.normalise("1", _qname("IsActive")) == "true"
    assert v.normalise("True", _qname("IsActive")) == "true"


def test_boolean_normalise_false() -> None:
    v = _make_validator(_concept("IsActive", "booleanItemType"))
    assert v.normalise("0", _qname("IsActive")) == "false"
    assert v.normalise("False", _qname("IsActive")) == "false"


# ---------------------------------------------------------------------------
# String
# ---------------------------------------------------------------------------


def test_string_always_valid() -> None:
    v = _make_validator(_concept("Name", "stringItemType"))
    ok, _ = v.validate("anything goes here", _qname("Name"))
    assert ok


def test_string_normalise_returns_unchanged() -> None:
    v = _make_validator(_concept("Name", "stringItemType"))
    val = "  some text  "
    assert v.normalise(val, _qname("Name")) == val


# ---------------------------------------------------------------------------
# Unknown concept type — safe fallback
# ---------------------------------------------------------------------------


def test_unknown_concept_returns_true() -> None:
    v = _make_validator()  # empty taxonomy
    ok, msg = v.validate("anything", _qname("Unknown"))
    assert ok
    assert msg == ""

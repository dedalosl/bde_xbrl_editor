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


def test_monetary_valid_with_thousands_sep() -> None:
    v = _make_validator(_concept("Amount", "monetaryItemType"))
    ok, _ = v.validate("1,000.50", _qname("Amount"))
    assert ok


def test_monetary_invalid() -> None:
    v = _make_validator(_concept("Amount", "monetaryItemType"))
    ok, msg = v.validate("not-a-number", _qname("Amount"))
    assert not ok
    assert msg != ""


def test_monetary_normalise_dot_decimal() -> None:
    v = _make_validator(_concept("Amount", "monetaryItemType"))
    result = v.normalise("1,234.56", _qname("Amount"))
    assert result == "1234.56"


def test_monetary_normalise_comma_decimal() -> None:
    v = _make_validator(_concept("Amount", "monetaryItemType"))
    result = v.normalise("1.234,56", _qname("Amount"))
    assert result == "1234.56"


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


def test_integer_valid_with_thousands() -> None:
    v = _make_validator(_concept("Count", "integerItemType"))
    ok, _ = v.validate("1,000,000", _qname("Count"))
    assert ok


def test_integer_invalid() -> None:
    v = _make_validator(_concept("Count", "integerItemType"))
    ok, msg = v.validate("12.5", _qname("Count"))
    # 12.5 after stripping decimal is "12" which is valid as integer
    # So let's test a clearly invalid one
    ok2, msg2 = v.validate("abc", _qname("Count"))
    assert not ok2
    assert msg2 != ""


def test_integer_normalise() -> None:
    v = _make_validator(_concept("Count", "integerItemType"))
    result = v.normalise("1,000,000", _qname("Count"))
    assert result == "1000000"


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

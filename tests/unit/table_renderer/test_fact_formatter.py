"""Unit tests for FactFormatter — monetary, date, percent, string, fallback."""

from __future__ import annotations

from unittest.mock import MagicMock

from bde_xbrl_editor.table_renderer.fact_formatter import FactFormatter
from bde_xbrl_editor.taxonomy.models import QName


def _make_formatter(type_local: str = "") -> FactFormatter:
    taxonomy = MagicMock()
    concept_def = MagicMock()
    type_qn = MagicMock()
    type_qn.local_name = type_local
    concept_def.type_qname = type_qn
    taxonomy.concepts = {_CONCEPT: concept_def}
    return FactFormatter(taxonomy)


_CONCEPT = QName(namespace="http://example.com", local_name="Val", prefix="ex")


class TestFactFormatter:
    def test_monetary_no_decimals(self):
        f = _make_formatter("monetaryItemType")
        result = f.format("1234567", _CONCEPT)
        assert "1,234,567" in result

    def test_monetary_with_negative_decimals(self):
        """@decimals='-3' means round to thousands."""
        f = _make_formatter("monetaryItemType")
        result = f.format("1234567", _CONCEPT, decimals="-3")
        # 1234567 rounded to nearest thousand = 1,235,000
        assert "1,235,000" in result

    def test_percent(self):
        f = _make_formatter("percentItemType")
        result = f.format("0.1234", _CONCEPT)
        assert "12.34%" in result

    def test_date_passthrough(self):
        f = _make_formatter("dateItemType")
        result = f.format("2023-12-31", _CONCEPT)
        assert result == "2023-12-31"

    def test_string_passthrough(self):
        f = _make_formatter("stringItemType")
        result = f.format("hello world", _CONCEPT)
        assert result == "hello world"

    def test_fallback_on_malformed_value(self):
        """Malformed numeric value falls back to raw_value — never raises."""
        f = _make_formatter("monetaryItemType")
        result = f.format("not-a-number", _CONCEPT)
        assert result == "not-a-number"

    def test_never_raises(self):
        """FactFormatter.format() must never raise regardless of input."""
        f = _make_formatter("monetaryItemType")
        for val in ["", "N/A", "inf", "NaN", None.__class__.__name__]:
            result = f.format(val, _CONCEPT)
            assert isinstance(result, str)

    def test_unknown_type_falls_back_to_numeric(self):
        """Unknown concept type tries numeric formatting first."""
        f = _make_formatter("")
        result = f.format("42", _CONCEPT)
        assert "42" in result

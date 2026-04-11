"""FactFormatter — type-aware fact value formatting."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bde_xbrl_editor.taxonomy.models import QName, TaxonomyStructure

# XSD type local names for monetary concepts
_MONETARY_TYPES = frozenset({"monetaryItemType", "decimalItemType"})
_DATE_TYPES = frozenset({"dateItemType", "gYearItemType", "gYearMonthItemType"})
_PERCENT_TYPES = frozenset({"percentItemType"})
_PURE_TYPES = frozenset({"pureItemType", "integerItemType", "nonNegativeIntegerItemType"})


def _type_local(type_qname: TYPE_CHECKING) -> str:
    """Extract the local name from a QName-like object."""
    if type_qname is None:
        return ""
    if hasattr(type_qname, "local_name"):
        return type_qname.local_name
    return str(type_qname).split("}")[-1].split(":")[-1]


class FactFormatter:
    """Type-aware display string formatter for XBRL fact values. Never raises."""

    def __init__(self, taxonomy: TaxonomyStructure) -> None:
        self._taxonomy = taxonomy

    def format(self, raw_value: str, concept: QName, decimals: str | None = None) -> str:
        """Return a locale-appropriate display string. Never raises.

        Falls back to raw_value if concept type is unknown or value is malformed.
        """
        try:
            return self._format_inner(raw_value, concept, decimals)
        except Exception:  # noqa: BLE001
            return raw_value

    def _format_inner(self, raw_value: str, concept: QName, decimals: str | None) -> str:
        concept_def = self._taxonomy.concepts.get(concept)
        type_local = ""
        if concept_def is not None and hasattr(concept_def, "type_qname"):
            type_local = _type_local(concept_def.type_qname)

        if type_local in _MONETARY_TYPES:
            return self._format_decimal(raw_value, decimals)
        if type_local in _PERCENT_TYPES:
            return self._format_percent(raw_value, decimals)
        if type_local in _DATE_TYPES:
            return self._format_date(raw_value)
        if type_local in _PURE_TYPES:
            return self._format_decimal(raw_value, decimals)

        # Unknown type — try numeric, fall back to string
        try:
            return self._format_decimal(raw_value, decimals)
        except Exception:  # noqa: BLE001
            return raw_value

    @staticmethod
    def _format_decimal(raw_value: str, decimals: str | None) -> str:
        """Format a numeric value with optional precision from @decimals.

        @decimals=N (N>=1) means show N decimal places.
        @decimals=0 or negative means show as integer (no rounding to quantum —
        the stored value is the actual value; decimals only expresses accuracy).
        """
        d = Decimal(raw_value.strip())
        if decimals is not None and decimals.strip().upper() != "INF":
            try:
                precision = int(decimals)
                if precision <= 0:
                    # Display stored integer value without rounding to magnitude
                    return f"{int(d.to_integral_value(rounding=ROUND_HALF_UP)):,}"
                quantum = Decimal(f"1E{-precision}")
                d = d.quantize(quantum, rounding=ROUND_HALF_UP)
                return f"{d:,}"
            except (InvalidOperation, ValueError):
                pass
        # Default: show as-is with thousands separator
        return f"{d:,}"

    @staticmethod
    def _format_percent(raw_value: str, decimals: str | None) -> str:
        d = Decimal(raw_value.strip())
        pct = d * 100
        return f"{pct:.2f}%"

    @staticmethod
    def _format_date(raw_value: str) -> str:
        """Return ISO date format (already ISO in XBRL, just pass through)."""
        return raw_value.strip()

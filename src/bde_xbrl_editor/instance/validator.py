"""XbrlTypeValidator — type-aware validation and normalisation for XBRL fact values."""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bde_xbrl_editor.taxonomy.models import QName, TaxonomyStructure

# Map type local names → internal category
_MONETARY_TYPES = frozenset(["monetaryItemType"])
_DECIMAL_TYPES = frozenset(["decimalItemType", "percentItemType", "shareItemType", "perShareItemType"])
_INTEGER_TYPES = frozenset(["integerItemType", "nonNegativeIntegerItemType", "positiveIntegerItemType"])
_DATE_TYPES = frozenset(["dateItemType"])
_BOOLEAN_TYPES = frozenset(["booleanItemType"])

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _type_category(type_local: str) -> str:
    """Return a broad XBRL type category from the data_type local name."""
    if type_local in _MONETARY_TYPES:
        return "monetary"
    if type_local in _DECIMAL_TYPES:
        return "decimal"
    if type_local in _INTEGER_TYPES:
        return "integer"
    if type_local in _DATE_TYPES:
        return "date"
    if type_local in _BOOLEAN_TYPES:
        return "boolean"
    return "string"


def _normalise_numeric(value: str) -> str:
    """Strip thousands separators and normalise decimal separator to '.'."""
    # Support both . and , as thousands separator; both . and , as decimal separator
    stripped = value.strip()
    # Remove common thousands separators (space, non-breaking space, dot, comma)
    # Strategy: if the value has both . and , use rightmost as decimal
    # Otherwise use locale heuristic
    if "," in stripped and "." in stripped:
        # Assume rightmost of the two is decimal separator
        last_comma = stripped.rfind(",")
        last_dot = stripped.rfind(".")
        if last_comma > last_dot:
            # comma is decimal separator
            stripped = stripped.replace(".", "").replace(",", ".")
        else:
            # dot is decimal separator
            stripped = stripped.replace(",", "")
    elif "," in stripped:
        # Could be thousands (1,000) or decimal (1,5)
        parts = stripped.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2 and len(parts[0]) <= 3:
            # Likely decimal comma (e.g. "1,5" or "12,50")
            stripped = stripped.replace(",", ".")
        else:
            # Likely thousands separator (e.g. "1,000,000")
            stripped = stripped.replace(",", "")
    return stripped


class XbrlTypeValidator:
    """Pure Python type-aware validation and normalisation for XBRL fact values."""

    def __init__(self, taxonomy: TaxonomyStructure) -> None:
        self._taxonomy = taxonomy

    def _get_type_category(self, concept: QName) -> str:
        concepts = self._taxonomy.concepts
        if concept not in concepts:
            return "string"
        return _type_category(concepts[concept].data_type.local_name)

    def validate(self, value: str, concept: QName) -> tuple[bool, str]:
        """Return (is_valid, error_message). Never raises."""
        try:
            category = self._get_type_category(concept)
            stripped = value.strip()

            if category == "string":
                return True, ""

            if not stripped:
                return False, "Value must not be empty"

            if category in ("monetary", "decimal"):
                normalised = _normalise_numeric(stripped)
                try:
                    Decimal(normalised)
                except InvalidOperation:
                    return False, f"Not a valid decimal number: '{value}'"
                return True, ""

            if category == "integer":
                normalised = _normalise_numeric(stripped).split(".")[0]
                try:
                    int(normalised)
                except ValueError:
                    return False, f"Not a valid integer: '{value}'"
                return True, ""

            if category == "date":
                s = stripped
                if not _ISO_DATE_RE.match(s):
                    return False, f"Date must be in YYYY-MM-DD format, got '{value}'"
                try:
                    date.fromisoformat(s)
                except ValueError:
                    return False, f"Invalid date value: '{value}'"
                return True, ""

            if category == "boolean":
                if stripped.lower() not in ("true", "false", "1", "0"):
                    return False, f"Boolean must be true/false/1/0, got '{value}'"
                return True, ""

            return True, ""
        except Exception:  # noqa: BLE001
            return True, ""

    def normalise(self, value: str, concept: QName) -> str:
        """Convert locale-formatted user input to XBRL canonical form. Never raises."""
        try:
            category = self._get_type_category(concept)
            stripped = value.strip()

            if category in ("monetary", "decimal"):
                return _normalise_numeric(stripped)

            if category == "integer":
                normalised = _normalise_numeric(stripped)
                # Remove any fractional part
                if "." in normalised:
                    normalised = normalised.split(".")[0]
                return normalised

            if category == "boolean":
                if stripped in ("1", "true"):
                    return "true"
                if stripped in ("0", "false"):
                    return "false"
                return stripped.lower()

            return value
        except Exception:  # noqa: BLE001
            return value

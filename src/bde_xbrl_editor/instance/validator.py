"""XbrlTypeValidator — type-aware validation and normalisation for XBRL fact values."""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING

from bde_xbrl_editor.taxonomy.type_traits import concept_type_category

if TYPE_CHECKING:
    from bde_xbrl_editor.taxonomy.models import QName, TaxonomyStructure

_FLOAT_RE = re.compile(r"(?:[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?|-?INF|NaN)")

_INTEGER_RE = re.compile(r"[+-]?[0-9]+")

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _decimal_pattern(separator: str) -> re.Pattern[str]:
    if separator not in (".", ","):
        raise ValueError("Decimal separator must be '.' or ','")
    escaped = re.escape(separator)
    return re.compile(rf"[+-]?(?:[0-9]+(?:{escaped}[0-9]*)?|{escaped}[0-9]+)")


def display_decimal_value(value: str, separator: str = ".") -> str:
    """Localize canonical decimal text without parsing, grouping or rounding."""
    _decimal_pattern(separator)
    return value.replace(".", separator) if _decimal_pattern(".").fullmatch(value) else value


class XbrlTypeValidator:
    """Pure Python type-aware validation and normalisation for XBRL fact values."""

    def __init__(self, taxonomy: TaxonomyStructure, decimal_separator: str = ".") -> None:
        self._taxonomy = taxonomy
        self._decimal_separator = decimal_separator
        self._decimal_re = _decimal_pattern(decimal_separator)

    def _get_type_category(self, concept: QName) -> str:
        concepts = self._taxonomy.concepts
        if concept not in concepts:
            return "string"
        return concept_type_category(concepts[concept])

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
                if self._decimal_re.fullmatch(stripped) is None:
                    return False, f"Not a valid decimal number: '{value}'"
                return True, ""

            if category in ("float", "double"):
                if _FLOAT_RE.fullmatch(stripped) is None:
                    return False, f"Not a valid {category}: '{value}'"
                return True, ""

            if category == "integer":
                if _INTEGER_RE.fullmatch(stripped) is None:
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
                return (
                    stripped.replace(self._decimal_separator, ".")
                    if self._decimal_re.fullmatch(stripped) is not None
                    else value
                )

            if category == "integer":
                # Invalid input must never be transformed into a different number.
                return stripped if _INTEGER_RE.fullmatch(stripped) is not None else value

            if category == "boolean":
                if stripped in ("1", "true"):
                    return "true"
                if stripped in ("0", "false"):
                    return "false"
                return stripped.lower()

            return value
        except Exception:  # noqa: BLE001
            return value

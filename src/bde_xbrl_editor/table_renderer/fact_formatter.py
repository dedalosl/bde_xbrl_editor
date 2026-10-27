"""Exact, type-aware presentation of canonical fact strings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bde_xbrl_editor.instance.validator import display_decimal_value
from bde_xbrl_editor.taxonomy.type_traits import concept_type_category

if TYPE_CHECKING:
    from bde_xbrl_editor.taxonomy.models import QName, TaxonomyStructure


class FactFormatter:
    """Present decimals with an explicit separator without changing their precision."""

    def __init__(self, taxonomy: TaxonomyStructure, decimal_separator: str = ".") -> None:
        display_decimal_value("", decimal_separator)
        self._taxonomy = taxonomy
        self._decimal_separator = decimal_separator

    def format(self, raw_value: str, concept: QName, decimals: str | None = None) -> str:
        """Display raw values; @decimals describes accuracy, not display rounding."""
        definition = self._taxonomy.concepts.get(concept)
        if definition is None:
            return raw_value
        category = concept_type_category(definition)
        if category in ("monetary", "decimal"):
            return display_decimal_value(raw_value, self._decimal_separator)
        return raw_value

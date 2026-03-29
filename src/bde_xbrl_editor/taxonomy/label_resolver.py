"""LabelResolver — merges standard and generic labels with full arc algebra.

resolve() never raises; always returns a non-empty string (falls back to
str(qname) when no label is found).
"""

from __future__ import annotations

from bde_xbrl_editor.taxonomy.constants import LABEL_ROLE
from bde_xbrl_editor.taxonomy.models import Label, QName


class LabelResolver:
    """Runtime label lookup service built from all loaded label linkbases.

    Constructed by TaxonomyLoader after parsing all standard and generic
    label linkbases.  Immutable after construction.
    """

    def __init__(
        self,
        labels: dict[QName, list[Label]],
        default_language_preference: list[str] | None = None,
    ) -> None:
        self._labels: dict[QName, list[Label]] = labels
        self._default_lang_pref: list[str] = default_language_preference or ["es", "en"]

    # ------------------------------------------------------------------
    # Public API (contract)
    # ------------------------------------------------------------------

    def resolve(
        self,
        qname: QName,
        role: str = LABEL_ROLE,
        language_preference: list[str] | None = None,
    ) -> str:
        """Return the best-matching label text.

        Never raises.  Falls back through language_preference, then returns
        str(qname) if no label found.
        """
        try:
            lang_pref = language_preference or self._default_lang_pref
            all_labels = self._labels.get(qname, [])
            role_labels = [lb for lb in all_labels if lb.role == role]

            for lang in lang_pref:
                candidates = [lb for lb in role_labels if lb.language == lang]
                if candidates:
                    return self._best(candidates).text

            # Any language as last resort
            if role_labels:
                return self._best(role_labels).text

            # Final fallback: try with standard label role
            if role != LABEL_ROLE:
                return self.resolve(qname, LABEL_ROLE, language_preference)

            return str(qname)
        except Exception:  # noqa: BLE001
            return str(qname)

    def get_all_labels(self, qname: QName) -> list[Label]:
        """Return all labels for a concept across all roles and languages."""
        return list(self._labels.get(qname, []))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _best(candidates: list[Label]) -> Label:
        """Select the label with the highest priority; standard > generic on tie."""
        def sort_key(lb: Label) -> tuple[int, int]:
            source_rank = 1 if lb.source == "standard" else 0
            return (lb.priority, source_rank)

        return max(candidates, key=sort_key)

    # ------------------------------------------------------------------
    # Builder
    # ------------------------------------------------------------------

    @classmethod
    def build(
        cls,
        standard_labels: dict[QName, list[Label]],
        generic_labels: dict[QName, list[Label]],
        default_language_preference: list[str] | None = None,
    ) -> LabelResolver:
        """Merge standard and generic label dicts into a single resolver."""
        merged: dict[QName, list[Label]] = {}
        for qname, labels in standard_labels.items():
            merged.setdefault(qname, []).extend(labels)
        for qname, labels in generic_labels.items():
            merged.setdefault(qname, []).extend(labels)
        return cls(merged, default_language_preference)

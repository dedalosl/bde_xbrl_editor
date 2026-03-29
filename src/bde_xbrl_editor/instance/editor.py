"""InstanceEditor — mutation service for XbrlInstance with dirty-state tracking."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from bde_xbrl_editor.instance.models import (
    ContextId,
    DuplicateFactError,
    Fact,
    UnitId,
    XbrlInstance,
)

if TYPE_CHECKING:
    from bde_xbrl_editor.taxonomy.models import QName


class InstanceEditor(QObject):
    """Mutation service wrapping an XbrlInstance with dirty-state tracking.

    Emits `changes_made` after every successful mutation.
    """

    changes_made = Signal()

    def __init__(self, instance: XbrlInstance, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._instance = instance

    @property
    def instance(self) -> XbrlInstance:
        return self._instance

    def add_fact(
        self,
        concept: QName,
        context_ref: ContextId,
        value: str,
        unit_ref: UnitId | None = None,
        decimals: str | None = None,
    ) -> Fact:
        """Create and append a new Fact; emit changes_made.

        Raises:
            DuplicateFactError: if concept+context already has a fact.
        """
        for fact in self._instance.facts:
            if fact.concept == concept and fact.context_ref == context_ref:
                raise DuplicateFactError(concept, context_ref)

        fact = Fact(
            concept=concept,
            context_ref=context_ref,
            unit_ref=unit_ref,
            value=value,
            decimals=decimals,
        )
        self._instance.add_fact(fact)
        self.changes_made.emit()
        return fact

    def update_fact(self, fact_index: int, new_value: str) -> None:
        """Replace fact value at index; emit changes_made."""
        self._instance.update_fact(fact_index, new_value)
        self.changes_made.emit()

    def remove_fact(self, fact_index: int) -> None:
        """Remove fact at index; emit changes_made."""
        self._instance.remove_fact(fact_index)
        self.changes_made.emit()

    def mark_saved(self, path: Path) -> None:
        """Called by InstanceSerializer.save(). Sets source_path and clears dirty flag."""
        self._instance.mark_saved(path)

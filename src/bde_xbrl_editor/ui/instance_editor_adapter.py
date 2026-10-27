"""QObject adapter for the Qt-independent instance editing service."""

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from bde_xbrl_editor.instance.editor import InstanceEditor
from bde_xbrl_editor.instance.models import ContextId, Fact, UnitId, XbrlInstance
from bde_xbrl_editor.taxonomy.models import QName


class InstanceEditorAdapter(QObject):
    """Delegate mutations and notify the UI only after successful operations."""

    changes_made = Signal()
    filing_indicators_changed = Signal()

    def __init__(self, instance: XbrlInstance, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = InstanceEditor(instance)

    @property
    def instance(self) -> XbrlInstance:
        return self._service.instance

    def add_fact(
        self,
        concept: QName,
        context_ref: ContextId,
        value: str,
        unit_ref: UnitId | None = None,
        decimals: str | None = None,
    ) -> Fact:
        fact = self._service.add_fact(concept, context_ref, value, unit_ref, decimals)
        self.changes_made.emit()
        return fact

    def update_fact(self, fact_index: int, new_value: str) -> None:
        self._service.update_fact(fact_index, new_value)
        self.changes_made.emit()

    def remove_fact(self, fact_index: int) -> None:
        self._service.remove_fact(fact_index)
        self.changes_made.emit()

    def reassign_facts_context(self, fact_indexes: list[int], context_ref: ContextId) -> None:
        if self._service.reassign_facts_context(fact_indexes, context_ref):
            self.changes_made.emit()

    def mark_saved(self, path: Path) -> None:
        self._service.mark_saved(path)

    def set_filing_indicator(
        self, template_id: str, filed: bool, *, context_ref: ContextId = ""
    ) -> None:
        self._service.set_filing_indicator(template_id, filed, context_ref=context_ref)
        self.filing_indicators_changed.emit()

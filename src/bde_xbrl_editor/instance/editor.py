"""InstanceEditor — mutation service for XbrlInstance with dirty-state tracking."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bde_xbrl_editor.instance.constants import is_bde_schema_ref
from bde_xbrl_editor.instance.models import (
    BdeEstadoReportado,
    BdePreambulo,
    ContextId,
    DuplicateFactError,
    Fact,
    FilingIndicator,
    UnitId,
    XbrlInstance,
)

if TYPE_CHECKING:
    from bde_xbrl_editor.taxonomy.models import QName


class InstanceEditor:
    """Qt-independent mutation service with dirty-state tracking."""

    def __init__(self, instance: XbrlInstance) -> None:
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
        """Create and append a new Fact.

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
        return fact

    def update_fact(self, fact_index: int, new_value: str) -> None:
        """Replace fact value at index."""
        self._instance.update_fact(fact_index, new_value)

    def remove_fact(self, fact_index: int) -> None:
        """Remove fact at index."""
        self._instance.remove_fact(fact_index)

    def reassign_facts_context(self, fact_indexes: list[int], context_ref: ContextId) -> bool:
        """Move facts to a context; return whether a non-empty operation completed."""
        unique_indexes = sorted(set(fact_indexes))
        if not unique_indexes:
            return False

        moving = set(unique_indexes)
        for fact_index in unique_indexes:
            fact = self._instance.facts[fact_index]
            for other_index, other_fact in enumerate(self._instance.facts):
                if other_index in moving:
                    continue
                if other_fact.concept == fact.concept and other_fact.context_ref == context_ref:
                    raise DuplicateFactError(fact.concept, context_ref)

        for fact_index in unique_indexes:
            self._instance.facts[fact_index].context_ref = context_ref
        self._instance._dirty = True  # noqa: SLF001
        return True

    def mark_saved(self, path: Path) -> None:
        """Called by InstanceSerializer.save(). Sets source_path and clears dirty flag."""
        self._instance.mark_saved(path)

    def set_filing_indicator(
        self,
        template_id: str,
        filed: bool,
        *,
        context_ref: ContextId = "",
    ) -> None:
        """Update or create a filing indicator and keep BDE estado metadata in sync."""
        indicator = next(
            (fi for fi in self._instance.filing_indicators if fi.template_id == template_id),
            None,
        )
        effective_context = (
            context_ref or getattr(indicator, "context_ref", "") or self._default_context_ref()
        )
        if indicator is None:
            self._instance.filing_indicators.append(
                FilingIndicator(
                    template_id=template_id,
                    filed=filed,
                    context_ref=effective_context,
                )
            )
        else:
            indicator.filed = filed
            if effective_context:
                indicator.context_ref = effective_context

        self._sync_bde_estado_reportado(template_id, filed, effective_context)
        self._instance.included_table_ids = [
            fi.template_id for fi in self._instance.filing_indicators if fi.filed
        ]
        self._instance._dirty = True  # noqa: SLF001

    def _sync_bde_estado_reportado(
        self,
        template_id: str,
        filed: bool,
        context_ref: ContextId,
    ) -> None:
        instance = self._instance
        if not (instance.bde_preambulo is not None or is_bde_schema_ref(instance.schema_ref_href)):
            return

        if instance.bde_preambulo is None:
            instance.bde_preambulo = BdePreambulo(context_ref=context_ref)

        estados = instance.bde_preambulo.estados_reportados
        estado = next((entry for entry in estados if entry.codigo == template_id), None)
        if estado is None:
            estados.append(
                BdeEstadoReportado(
                    codigo=template_id,
                    blanco=not filed,
                    context_ref=context_ref or instance.bde_preambulo.context_ref,
                )
            )
        else:
            estado.blanco = not filed
            if context_ref:
                estado.context_ref = context_ref

        if context_ref and not instance.bde_preambulo.context_ref:
            instance.bde_preambulo.context_ref = context_ref

    def _default_context_ref(self) -> ContextId:
        if self._instance.bde_preambulo is not None and self._instance.bde_preambulo.context_ref:
            return self._instance.bde_preambulo.context_ref
        if self._instance.filing_indicators:
            return self._instance.filing_indicators[0].context_ref
        return next(iter(self._instance.contexts), "")

"""InstanceFactory — creates validated XbrlInstance objects from taxonomy + user input."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from bde_xbrl_editor.instance.constants import ISO4217_NS, XBRLDI_CONTEXT_ELEMENT, XBRLI_NS
from bde_xbrl_editor.instance.context_builder import (
    build_dimensional_context,
    build_filing_indicator_context,
    deduplicate_contexts,
)
from bde_xbrl_editor.instance.models import (
    DimensionalConfiguration,
    FilingIndicator,
    InstanceCreationError,
    InvalidDimensionMemberError,
    MissingDimensionValueError,
    ReportingEntity,
    ReportingPeriod,
    UnitId,
    XbrlContext,
    XbrlInstance,
    XbrlUnit,
)
from bde_xbrl_editor.taxonomy.models import QName, TaxonomyStructure

_PURE_MEASURE = f"{XBRLI_NS}:pure"
_SHARES_MEASURE = f"{XBRLI_NS}:shares"


def unit_prepopulation(
    taxonomy: TaxonomyStructure,
    table_ids: list[str],
) -> dict[UnitId, XbrlUnit]:
    """Collect standard units for the selected tables.

    Pre-populates EUR (monetary) and pure (dimensionless ratio) units as a
    sensible default for BDE regulatory taxonomies. Future enhancement: walk
    concept types in selected tables when BreakdownNode carries concept refs.
    """
    units: dict[UnitId, XbrlUnit] = {
        "EUR": XbrlUnit(unit_id="EUR", measure_uri=f"{ISO4217_NS}:EUR"),
        "pure": XbrlUnit(unit_id="pure", measure_uri=_PURE_MEASURE),
    }
    return units


def _get_context_element_for_table(
    taxonomy: TaxonomyStructure,
    table_elr: str,
) -> Literal["scenario", "segment"]:
    """Return the context element declared by the hypercube arc for this table's ELR."""
    for hc in taxonomy.hypercubes:
        if hc.extended_link_role == table_elr and hc.context_element:
            return hc.context_element  # type: ignore[return-value]
    return XBRLDI_CONTEXT_ELEMENT  # type: ignore[return-value]


def _get_z_dimensions_for_table(
    taxonomy: TaxonomyStructure,
    table_elr: str,
) -> list[QName]:
    """Return the dimension QNames declared in hypercubes for this table's ELR."""
    dims: list[QName] = []
    for hc in taxonomy.hypercubes:
        if hc.extended_link_role == table_elr:
            dims.extend(hc.dimensions)
    return dims


class InstanceFactory:
    """Creates validated XbrlInstance objects from a bound taxonomy."""

    def __init__(self, taxonomy: TaxonomyStructure) -> None:
        self._taxonomy = taxonomy

    def create(
        self,
        entity: ReportingEntity,
        period: ReportingPeriod,
        included_table_ids: list[str],
        dimensional_configs: dict[str, DimensionalConfiguration],
    ) -> XbrlInstance:
        """Create a new empty XbrlInstance.

        Validates:
          - included_table_ids is non-empty
          - all table IDs exist in the taxonomy
          - all mandatory dimensions have assigned values (per hypercube model)
          - all assigned members are in the allowed member list

        Returns a new XbrlInstance with ``_dirty=True``, ``source_path=None``, ``facts=[]``.

        Raises:
          InstanceCreationError — no tables selected or unknown table ID
          InvalidReportingPeriodError — period validation (raised by ReportingPeriod constructor)
          InvalidEntityIdentifierError — entity validation (raised by ReportingEntity constructor)
          MissingDimensionValueError — mandatory Z-axis dimension has no value
          InvalidDimensionMemberError — assigned member not in allowed list
        """
        taxonomy = self._taxonomy

        # Guard: at least one table
        if not included_table_ids:
            raise InstanceCreationError(
                "No tables selected — at least one table must be included"
            )

        # Validate all table IDs exist
        known_table_ids = {t.table_id for t in taxonomy.tables}
        for tid in included_table_ids:
            if tid not in known_table_ids:
                raise InstanceCreationError(
                    f"Table '{tid}' not found in the loaded taxonomy"
                )

        # Validate dimensional configs against dimension model
        self._validate_dimensional_configs(included_table_ids, dimensional_configs)

        # Determine context_element (take the first hypercube's declaration or default)
        context_element: Literal["scenario", "segment"] = XBRLDI_CONTEXT_ELEMENT  # type: ignore[assignment]
        if taxonomy.hypercubes:
            context_element = taxonomy.hypercubes[0].context_element or XBRLDI_CONTEXT_ELEMENT  # type: ignore[assignment]

        # Build schema_ref_href
        schema_ref_href = str(taxonomy.metadata.entry_point_path)

        # Generate contexts
        all_contexts: list[XbrlContext] = []

        # 1. Filing-indicator context (always present, no dimensions)
        fi_ctx = build_filing_indicator_context(entity, period, context_element)
        all_contexts.append(fi_ctx)

        # 2. Per-table dimensional contexts
        for tid in included_table_ids:
            dim_cfg = dimensional_configs.get(tid)
            dims = dim_cfg.dimension_assignments if dim_cfg else {}
            if dims:
                table = taxonomy.get_table(tid)
                tbl_ctx_el = (
                    _get_context_element_for_table(taxonomy, table.extended_link_role)
                    if table
                    else context_element
                )
                ctx = build_dimensional_context(entity, period, dims, tbl_ctx_el)
                all_contexts.append(ctx)

        contexts = deduplicate_contexts(all_contexts)

        # Build filing indicators
        filing_indicators: list[FilingIndicator] = [
            FilingIndicator(template_id=tid, filed=True, context_ref=fi_ctx.context_id)
            for tid in included_table_ids
        ]

        # Pre-populate units
        units = unit_prepopulation(taxonomy, included_table_ids)

        return XbrlInstance(
            taxonomy_entry_point=Path(taxonomy.metadata.entry_point_path),
            schema_ref_href=schema_ref_href,
            entity=entity,
            period=period,
            filing_indicators=filing_indicators,
            included_table_ids=list(included_table_ids),
            dimensional_configs=dict(dimensional_configs),
            contexts=contexts,
            units=units,
            facts=[],
            source_path=None,
            _dirty=True,
        )

    def _validate_dimensional_configs(
        self,
        included_table_ids: list[str],
        dimensional_configs: dict[str, DimensionalConfiguration],
    ) -> None:
        """Validate dimensional assignments against the taxonomy's dimension models."""
        taxonomy = self._taxonomy

        for tid in included_table_ids:
            table = taxonomy.get_table(tid)
            if table is None:
                continue

            dim_cfg = dimensional_configs.get(tid)
            assignments = dim_cfg.dimension_assignments if dim_cfg else {}

            # Get Z-axis dimensions for this table via hypercube model
            z_dims = _get_z_dimensions_for_table(taxonomy, table.extended_link_role)

            for dim_qname in z_dims:
                dim_model = taxonomy.dimensions.get(dim_qname)
                if dim_model is None:
                    continue

                # A dimension is mandatory if it has no default member
                is_mandatory = dim_model.default_member is None

                assigned = assignments.get(dim_qname)
                if assigned is None and is_mandatory:
                    raise MissingDimensionValueError(
                        table_id=tid,
                        dimension_qname=dim_qname,
                    )

                if assigned is not None and dim_model.members:
                    allowed = [m.qname for m in dim_model.members]
                    if allowed and assigned not in allowed:
                        raise InvalidDimensionMemberError(
                            table_id=tid,
                            dimension_qname=dim_qname,
                            provided_member=assigned,
                            allowed_members=allowed,
                        )

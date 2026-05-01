"""Context builder — generates deterministic XbrlContext IDs and deduplicates contexts."""

from __future__ import annotations

import hashlib
from typing import Literal

from bde_xbrl_editor.instance.models import (
    ContextId,
    ReportingEntity,
    ReportingPeriod,
    XbrlContext,
)
from bde_xbrl_editor.instance.s_equal import build_s_equal_key_from_model
from bde_xbrl_editor.taxonomy.models import QName


def generate_context_id(
    entity: ReportingEntity,
    period: ReportingPeriod,
    dimensions: dict[QName, QName] | None = None,
    typed_dimensions: dict[QName, str] | None = None,
    dim_containers: dict[QName, Literal["segment", "scenario"]] | None = None,
) -> ContextId:
    """Generate a deterministic, stable context ID from its components.

    Format: ``ctx_<sha256[:8]>``

    The hash is computed over the canonical string representation of
    (scheme, identifier, period_type, dates, sorted dimension pairs).
    Same inputs always produce the same ID.
    """
    dims = dimensions or {}
    typed_dims = typed_dimensions or {}
    containers = dim_containers or {}
    # Canonical representation — sort dimension pairs for determinism
    dim_str = "|".join(
        f"{str(k)}={str(v)}" for k, v in sorted(dims.items(), key=lambda kv: str(kv[0]))
    )
    typed_dim_str = "|".join(
        f"{str(k)}={str(v)}" for k, v in sorted(typed_dims.items(), key=lambda kv: str(kv[0]))
    )
    container_str = "|".join(
        f"{str(k)}={v}" for k, v in sorted(containers.items(), key=lambda kv: str(kv[0]))
    )
    period_str = (
        str(period.instant_date)
        if period.period_type == "instant"
        else "forever"
        if period.period_type == "forever"
        else f"{period.start_date}/{period.end_date}"
    )
    canonical = (
        f"{entity.scheme}|{entity.identifier}|{period.period_type}|{period_str}|"
        f"{dim_str}|{typed_dim_str}|{container_str}"
    )
    digest = hashlib.sha256(canonical.encode()).hexdigest()[:8]
    return f"ctx_{digest}"


def build_filing_indicator_context(
    entity: ReportingEntity,
    period: ReportingPeriod,
    context_element: Literal["scenario", "segment"] = "scenario",
    dimensions: dict[QName, QName] | None = None,
    dim_containers: dict[QName, Literal["segment", "scenario"]] | None = None,
) -> XbrlContext:
    """Build the base filing-indicator context (entity + period, no dimensions)."""
    explicit_dimensions = dict(dimensions or {})
    containers = dict(dim_containers or {})
    ctx_id = generate_context_id(entity, period, explicit_dimensions, dim_containers=containers)
    ctx = XbrlContext(
        context_id=ctx_id,
        entity=entity,
        period=period,
        dimensions=explicit_dimensions,
        context_element=context_element,
        dim_containers=containers,
    )
    ctx.s_equal_key = build_s_equal_key_from_model(ctx)
    return ctx


def build_dimensional_context(
    entity: ReportingEntity,
    period: ReportingPeriod,
    dimensions: dict[QName, QName],
    context_element: Literal["scenario", "segment"] = "scenario",
    typed_dimensions: dict[QName, str] | None = None,
    typed_dimension_elements: dict[QName, QName] | None = None,
    dim_containers: dict[QName, Literal["segment", "scenario"]] | None = None,
) -> XbrlContext:
    """Build a context for a specific dimensional combination."""
    explicit_dimensions = dict(dimensions)
    typed_dims = dict(typed_dimensions or {})
    typed_elements = dict(typed_dimension_elements or {})
    containers = dict(dim_containers or {})
    merged_dimensions = dict(explicit_dimensions)
    for dim_qname in typed_dims:
        merged_dimensions.setdefault(dim_qname, dim_qname)
        containers.setdefault(dim_qname, context_element)

    for dim_qname in explicit_dimensions:
        containers.setdefault(dim_qname, context_element)

    ctx_id = generate_context_id(
        entity,
        period,
        explicit_dimensions,
        typed_dims,
        containers,
    )
    ctx = XbrlContext(
        context_id=ctx_id,
        entity=entity,
        period=period,
        dimensions=merged_dimensions,
        typed_dimensions=typed_dims,
        typed_dimension_elements=typed_elements,
        context_element=context_element,
        dim_containers=containers,
    )
    ctx.s_equal_key = build_s_equal_key_from_model(ctx)
    return ctx


def deduplicate_contexts(contexts: list[XbrlContext]) -> dict[ContextId, XbrlContext]:
    """Merge a list of contexts, keeping only one per unique context ID.

    Because context IDs are deterministic hashes, identical (entity, period,
    dimensions) tuples always produce the same ID, so deduplication is a
    simple dict construction.
    """
    result: dict[ContextId, XbrlContext] = {}
    for ctx in contexts:
        result[ctx.context_id] = ctx
    return result

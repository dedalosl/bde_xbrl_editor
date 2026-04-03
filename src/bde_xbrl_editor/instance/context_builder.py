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
from bde_xbrl_editor.taxonomy.models import QName


def generate_context_id(
    entity: ReportingEntity,
    period: ReportingPeriod,
    dimensions: dict[QName, QName] | None = None,
) -> ContextId:
    """Generate a deterministic, stable context ID from its components.

    Format: ``ctx_<sha256[:8]>``

    The hash is computed over the canonical string representation of
    (scheme, identifier, period_type, dates, sorted dimension pairs).
    Same inputs always produce the same ID.
    """
    dims = dimensions or {}
    # Canonical representation — sort dimension pairs for determinism
    dim_str = "|".join(
        f"{str(k)}={str(v)}"
        for k, v in sorted(dims.items(), key=lambda kv: str(kv[0]))
    )
    period_str = (
        str(period.instant_date)
        if period.period_type == "instant"
        else f"{period.start_date}/{period.end_date}"
    )
    canonical = (
        f"{entity.scheme}|{entity.identifier}|{period.period_type}|{period_str}|{dim_str}"
    )
    digest = hashlib.sha256(canonical.encode()).hexdigest()[:8]
    return f"ctx_{digest}"


def build_filing_indicator_context(
    entity: ReportingEntity,
    period: ReportingPeriod,
    context_element: Literal["scenario", "segment"] = "scenario",
) -> XbrlContext:
    """Build the base filing-indicator context (entity + period, no dimensions)."""
    ctx_id = generate_context_id(entity, period, {})
    return XbrlContext(
        context_id=ctx_id,
        entity=entity,
        period=period,
        dimensions={},
        context_element=context_element,
    )


def build_dimensional_context(
    entity: ReportingEntity,
    period: ReportingPeriod,
    dimensions: dict[QName, QName],
    context_element: Literal["scenario", "segment"] = "scenario",
) -> XbrlContext:
    """Build a context for a specific dimensional combination."""
    ctx_id = generate_context_id(entity, period, dimensions)
    return XbrlContext(
        context_id=ctx_id,
        entity=entity,
        period=period,
        dimensions=dict(dimensions),
        context_element=context_element,
    )


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

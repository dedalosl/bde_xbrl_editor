"""XBRL S-equality helpers for contexts (entity, period, segment/scenario XML).

Used for duplicate-fact grouping and calculation binding when two context
elements differ only lexically (e.g. ``xsd:decimal`` attributes) but are
S-equal per XBRL 2.1 (conformance 302.11 / 302.12).
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from lxml import etree

from bde_xbrl_editor.instance.constants import XBRLDI_NS
from bde_xbrl_editor.instance.models import ReportingEntity, ReportingPeriod, XbrlContext
from bde_xbrl_editor.taxonomy.models import QName

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.models import XbrlInstance

_XBRLDI_EXPLICIT = f"{{{XBRLDI_NS}}}explicitMember"
_XBRLDI_TYPED = f"{{{XBRLDI_NS}}}typedMember"
_DIM_ATTR = f"{{{XBRLDI_NS}}}dimension"


def _qname_clark_from_model(qn: QName) -> str:
    if not qn.namespace:
        return qn.local_name
    return f"{{{qn.namespace}}}{qn.local_name}"


def _period_key(period: ReportingPeriod) -> tuple:
    if period.period_type == "instant":
        assert period.instant_date is not None
        return ("instant", period.instant_date.isoformat())
    if period.period_type == "forever":
        return ("forever",)
    assert period.start_date is not None and period.end_date is not None
    return ("duration", period.start_date.isoformat(), period.end_date.isoformat())


def _resolve_prefixed_qname(el: etree._Element, prefixed: str) -> str:
    if prefixed.startswith("{"):
        return prefixed
    if ":" in prefixed:
        prefix, local = prefixed.split(":", 1)
        nsmap = el.nsmap or {}
        ns = nsmap.get(prefix, "")
        return f"{{{ns}}}{local}" if ns else local
    return prefixed


def _normalize_lexical(el: etree._Element, raw: str) -> tuple[str, str]:
    """Return a hashable (kind, payload) token for attribute or text S-equality."""
    s = raw.strip()
    if not s:
        return ("empty", "")
    low = s.lower()
    if low == "true":
        return ("dec", "1")
    if low == "false":
        return ("dec", "0")
    try:
        d = Decimal(s)
        if d.is_nan():
            # XML Schema NaN is not equal to itself, so it must not collapse
            # otherwise-identical segment/scenario fragments into one S-equal key.
            return ("nan", str(id(el)))
        if d.is_zero():
            return ("dec", "0")
        return ("dec", format(d.normalize(), "f"))
    except InvalidOperation:
        pass
    if s.startswith("{") or ":" in s:
        return ("qname", _resolve_prefixed_qname(el, s))
    return ("str", s)


def _element_s_equal_key(el: etree._Element) -> tuple:
    tag = el.tag
    if not isinstance(tag, str):
        return ("__non_element__", (), None, ())
    attrs: list[tuple[str, tuple[str, str]]] = []
    for attr_name in sorted(el.attrib.keys()):
        attrs.append(
            (attr_name, _normalize_lexical(el, el.attrib[attr_name])),
        )
    text_raw = el.text if el.text is not None else ""
    text_tok = _normalize_lexical(el, text_raw) if text_raw.strip() else None
    children = tuple(_element_s_equal_key(c) for c in el if isinstance(c.tag, str))
    return (tag, tuple(attrs), text_tok, children)


def _container_children_key(container: etree._Element | None) -> tuple:
    if container is None:
        return ()
    return tuple(_element_s_equal_key(c) for c in container if isinstance(c.tag, str))


def build_s_equal_key_from_xml_fragments(
    entity: ReportingEntity,
    period: ReportingPeriod,
    scenario_el: etree._Element | None,
    segment_el: etree._Element | None,
    period_key: tuple | None = None,
) -> tuple:
    """Full context S-equal signature from parsed XML (segment/scenario subtrees)."""
    sch = entity.scheme.strip()
    ident = entity.identifier.strip()
    return (
        "ctxseq1",
        sch,
        ident,
        period_key if period_key is not None else _period_key(period),
        _container_children_key(scenario_el),
        _container_children_key(segment_el),
    )


def build_s_equal_key_from_model(ctx: XbrlContext) -> tuple:
    """S-equal signature for in-memory contexts (no raw segment/scenario XML).

    Dimension members are emitted as ``xbrldi:explicitMember`` in **sorted**
    dimension order, matching :func:`bde_xbrl_editor.instance.serializer._build_context_el`.
    """
    sch = ctx.entity.scheme.strip()
    ident = ctx.entity.identifier.strip()
    pk = _period_key(ctx.period)
    scenario_members: list[tuple] = []
    segment_members: list[tuple] = []
    typed_dims = ctx.typed_dimensions or {}
    dim_containers = ctx.dim_containers or {}
    for dim, mem in sorted(ctx.dimensions.items(), key=lambda kv: str(kv[0])):
        if dim in typed_dims:
            continue
        dim_clark = _qname_clark_from_model(dim)
        mem_clark = _qname_clark_from_model(mem)
        member_tuple = (
            _XBRLDI_EXPLICIT,
            ((_DIM_ATTR, ("qname", dim_clark)),),
            ("qname", mem_clark),
            (),
        )
        target = (
            segment_members
            if dim_containers.get(dim, ctx.context_element) == "segment"
            else scenario_members
        )
        target.append(member_tuple)
    for dim, value in sorted(typed_dims.items(), key=lambda kv: str(kv[0])):
        dim_clark = _qname_clark_from_model(dim)
        typed_element = (ctx.typed_dimension_elements or {}).get(dim, dim)
        typed_child_tag = _qname_clark_from_model(typed_element)
        member_tuple = (
            _XBRLDI_TYPED,
            ((_DIM_ATTR, ("qname", dim_clark)),),
            None,
            ((typed_child_tag, (), ("str", value.strip()), ()),),
        )
        target = (
            segment_members
            if dim_containers.get(dim, ctx.context_element) == "segment"
            else scenario_members
        )
        target.append(member_tuple)
    return ("ctxseq1", sch, ident, pk, tuple(scenario_members), tuple(segment_members))


def effective_s_equal_key(ctx: XbrlContext) -> tuple:
    if ctx.s_equal_key is not None:
        return ctx.s_equal_key
    return build_s_equal_key_from_model(ctx)


def canonical_context_refs_by_s_equal(instance: XbrlInstance) -> dict[str, str]:
    """Map each context ``id`` to a canonical id (lexicographic min within each S-equal class)."""
    groups: dict[tuple, list[str]] = defaultdict(list)
    for cid, ctx in instance.contexts.items():
        groups[effective_s_equal_key(ctx)].append(cid)
    out: dict[str, str] = {}
    for ids in groups.values():
        rep = min(ids)
        for cid in ids:
            out[cid] = rep
    return out

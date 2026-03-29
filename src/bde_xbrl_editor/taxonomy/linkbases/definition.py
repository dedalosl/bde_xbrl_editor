"""Definition linkbase parser — builds HypercubeModel, DimensionModel, DomainMember."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import (
    ARCROLE_ALL,
    ARCROLE_DIMENSION_DEFAULT,
    ARCROLE_DIMENSION_DOMAIN,
    ARCROLE_DOMAIN_MEMBER,
    ARCROLE_HYPERCUBE_DIMENSION,
    ARCROLE_NOT_ALL,
    NS_LINK,
    NS_XBRLDT,
    NS_XLINK,
)
from bde_xbrl_editor.taxonomy.models import (
    DefinitionArc,
    DimensionModel,
    DomainMember,
    HypercubeModel,
    QName,
    TaxonomyParseError,
)

_DEF_LINK = f"{{{NS_LINK}}}definitionLink"
_LOC = f"{{{NS_LINK}}}loc"
_DEF_ARC = f"{{{NS_LINK}}}definitionArc"
_XLINK_HREF = f"{{{NS_XLINK}}}href"
_XLINK_LABEL = f"{{{NS_XLINK}}}label"
_XLINK_FROM = f"{{{NS_XLINK}}}from"
_XLINK_TO = f"{{{NS_XLINK}}}to"
_XLINK_ARCROLE = f"{{{NS_XLINK}}}arcrole"
_XLINK_ROLE = f"{{{NS_XLINK}}}role"
_CLOSED = f"{{{NS_XBRLDT}}}closed"
_CONTEXT_ELEMENT = f"{{{NS_XBRLDT}}}contextElement"
_USABLE = f"{{{NS_XBRLDT}}}usable"


def parse_definition_linkbase(
    linkbase_path: Path,
    concept_map: dict[str, QName],
) -> tuple[
    dict[str, list[DefinitionArc]],
    list[HypercubeModel],
    dict[QName, DimensionModel],
]:
    """Parse a definition linkbase.

    Returns:
        (arcs_by_elr, hypercubes, dimensions)

    Raises:
        TaxonomyParseError: If the file is not well-formed XML.
    """
    try:
        tree = etree.parse(str(linkbase_path))  # noqa: S320
    except etree.XMLSyntaxError as exc:
        raise TaxonomyParseError(
            file_path=str(linkbase_path),
            message=str(exc),
            line=exc.lineno,
            column=exc.offset,
        ) from exc

    root = tree.getroot()

    arcs_by_elr: dict[str, list[DefinitionArc]] = {}

    # Per-ELR accumulators for dimensional model construction
    # elr → set of (primary_item, hypercube, arcrole, closed, context_element)
    hc_primary: dict[str, list[tuple[QName, QName, str, bool, str]]] = {}
    # elr → list of (hypercube, dimension)
    hc_dims: dict[str, list[tuple[QName, QName]]] = {}
    # dimension → list of (domain, member, parent, order, usable)
    dim_domain: dict[QName, QName] = {}
    dim_members: dict[QName, list[tuple[QName, QName | None, float, bool]]] = {}
    dim_defaults: dict[QName, QName] = {}

    for link_el in root.iter(_DEF_LINK):
        elr = link_el.get(_XLINK_ROLE, "http://www.xbrl.org/2003/role/link")

        loc_map: dict[str, QName] = {}
        for loc in link_el.iter(_LOC):
            href = loc.get(_XLINK_HREF, "")
            xlink_label = loc.get(_XLINK_LABEL, "")
            if "#" in href:
                fragment = href.rsplit("#", 1)[1]
                qname = concept_map.get(fragment)
                if qname:
                    loc_map[xlink_label] = qname

        for arc in link_el.iter(_DEF_ARC):
            arcrole = arc.get(_XLINK_ARCROLE, "")
            frm = arc.get(_XLINK_FROM, "")
            to = arc.get(_XLINK_TO, "")
            source = loc_map.get(frm)
            target = loc_map.get(to)
            if not source or not target:
                continue

            try:
                order = float(arc.get("order", "1"))
            except ValueError:
                order = 1.0

            closed_raw = arc.get(_CLOSED)
            closed = (closed_raw.lower() == "true") if closed_raw else None
            context_element = arc.get(_CONTEXT_ELEMENT)
            usable_raw = arc.get(_USABLE)
            usable = (usable_raw.lower() != "false") if usable_raw else None

            def_arc = DefinitionArc(
                arcrole=arcrole,
                source=source,
                target=target,
                order=order,
                extended_link_role=elr,
                closed=closed,
                context_element=context_element,
                usable=usable,
            )
            arcs_by_elr.setdefault(elr, []).append(def_arc)

            # Collect dimensional structure
            if arcrole in (ARCROLE_ALL, ARCROLE_NOT_ALL):
                hc_primary.setdefault(elr, []).append((
                    source, target, arcrole,
                    bool(closed), context_element or "segment",
                ))
            elif arcrole == ARCROLE_HYPERCUBE_DIMENSION:
                hc_dims.setdefault(elr, []).append((source, target))
            elif arcrole == ARCROLE_DIMENSION_DOMAIN:
                dim_domain[source] = target
                dim_members.setdefault(source, []).append((target, None, order, True))
            elif arcrole == ARCROLE_DOMAIN_MEMBER:
                # source is the parent member/domain, target is the member
                # We need to track which dimension owns these — done via dim_domain
                # Find which dimension owns this source
                for dim_q, _dom_q in dim_domain.items():
                    # This is a heuristic; proper resolution needs ELR scoping
                    dim_members.setdefault(dim_q, []).append(
                        (target, source, order, usable if usable is not None else True)
                    )
            elif arcrole == ARCROLE_DIMENSION_DEFAULT:
                dim_defaults[source] = target

    # Build HypercubeModel objects
    hypercubes: list[HypercubeModel] = []
    for elr, prim_list in hc_primary.items():
        # Group by hypercube
        hc_map: dict[QName, tuple[str, bool, str]] = {}  # hc → (arcrole, closed, ctx)
        primary_by_hc: dict[QName, list[QName]] = {}
        for primary, hc, arcrole, closed, ctx in prim_list:
            hc_map[hc] = (arcrole, closed, ctx)
            primary_by_hc.setdefault(hc, []).append(primary)

        dims_by_hc: dict[QName, list[QName]] = {}
        for hc, dim in hc_dims.get(elr, []):
            dims_by_hc.setdefault(hc, []).append(dim)

        for hc, (arcrole, closed, ctx) in hc_map.items():
            arcrole_short: str = "all" if arcrole == ARCROLE_ALL else "notAll"
            ctx_el = "segment" if ctx == "segment" else "scenario"
            hypercubes.append(HypercubeModel(
                qname=hc,
                arcrole=arcrole_short,
                closed=closed,
                context_element=ctx_el,
                primary_items=tuple(primary_by_hc.get(hc, [])),
                dimensions=tuple(dims_by_hc.get(hc, [])),
                extended_link_role=elr,
            ))

    # Build DimensionModel objects
    dimensions: dict[QName, DimensionModel] = {}
    all_dim_qnames: set[QName] = set()
    for elr_dims in hc_dims.values():
        for _, dim_q in elr_dims:
            all_dim_qnames.add(dim_q)

    for dim_q in all_dim_qnames:
        members_raw = dim_members.get(dim_q, [])
        members = tuple(
            DomainMember(qname=m, parent=p, order=o, usable=u)
            for m, p, o, u in members_raw
        )
        dimensions[dim_q] = DimensionModel(
            qname=dim_q,
            dimension_type="explicit",
            default_member=dim_defaults.get(dim_q),
            domain=dim_domain.get(dim_q),
            members=members,
        )

    return arcs_by_elr, hypercubes, dimensions

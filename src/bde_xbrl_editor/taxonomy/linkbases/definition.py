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


def _resolve_locator_href(
    href: str,
    linkbase_path: Path,
    concept_map: dict[str, QName],
    ns_qualified_map: dict[str, QName],
    schema_ns_map: dict[str, str],
) -> QName | None:
    """Resolve a locator href to a QName using the most precise method available.

    Priority:
    1. Namespace-qualified lookup: derive targetNamespace from the href schema URL
       (either via schema_ns_map for absolute URLs, or by resolving relative paths
       against the linkbase directory), then look up "{namespace}#{fragment}".
    2. Fall back to bare fragment lookup in concept_map (may collide when two
       schemas declare elements with the same xml:id).
    """
    if "#" not in href:
        return None
    schema_url, fragment = href.rsplit("#", 1)
    if not fragment:
        return None

    # Attempt 1: resolve schema URL to its targetNamespace and do a full lookup
    ns: str | None = None
    if schema_url.startswith("http://") or schema_url.startswith("https://"):
        ns = schema_ns_map.get(schema_url)
    else:
        # Relative href — resolve against linkbase directory
        try:
            resolved = str((linkbase_path.parent / schema_url).resolve())
            ns = schema_ns_map.get(resolved)
        except Exception:  # noqa: BLE001
            pass

    if ns:
        qname = ns_qualified_map.get(f"{ns}#{fragment}")
        if qname:
            return qname

    # Attempt 2: bare fragment fallback (backward compat, may have collisions)
    return concept_map.get(fragment)


def parse_definition_linkbase(
    linkbase_path: Path,
    concept_map: dict[str, QName],
    *,
    ns_qualified_map: dict[str, QName] | None = None,
    schema_ns_map: dict[str, str] | None = None,
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

    # Normalise optional maps so inner code can always call dict.get()
    _ns_qmap: dict[str, QName] = ns_qualified_map or {}
    _schema_ns: dict[str, str] = schema_ns_map or {}

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
            qname = _resolve_locator_href(
                href, linkbase_path, concept_map, _ns_qmap, _schema_ns,
            )
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
            target_role = arc.get(f"{{{NS_XBRLDT}}}targetRole") or None

            def_arc = DefinitionArc(
                arcrole=arcrole,
                source=source,
                target=target,
                order=order,
                extended_link_role=elr,
                closed=closed,
                context_element=context_element,
                usable=usable,
                target_role=target_role,
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
        # Expand primary items through domain-member arcs within this ELR.
        #
        # In EBA/BDE taxonomy a "concept group" pattern is used: one concept
        # is the explicit source of the all-arc, and the remaining primary
        # items of that table are declared as domain-members of that source
        # concept within the SAME ELR.  We BFS-expand so every such concept
        # is also recorded as a primary item of the same hypercube.
        dm_children_in_elr: dict[QName, list[QName]] = {}
        for arc in arcs_by_elr.get(elr, []):
            if arc.arcrole == ARCROLE_DOMAIN_MEMBER:
                dm_children_in_elr.setdefault(arc.source, []).append(arc.target)

        expanded_primaries: set[QName] = {p for p, *_ in prim_list}
        bfs_queue: list[tuple[QName, QName, str, bool, str]] = list(prim_list)
        for primary, hc, arcrole, closed, ctx in bfs_queue:
            for child in dm_children_in_elr.get(primary, []):
                if child not in expanded_primaries:
                    expanded_primaries.add(child)
                    new_entry = (child, hc, arcrole, closed, ctx)
                    prim_list.append(new_entry)
                    bfs_queue.append(new_entry)

        # Group by hypercube
        hc_map: dict[QName, tuple[str, bool, str]] = {}  # hc → (arcrole, closed, ctx)
        primary_by_hc: dict[QName, list[QName]] = {}
        for primary, hc, arcrole, closed, ctx in prim_list:
            hc_map[hc] = (arcrole, closed, ctx)
            primary_by_hc.setdefault(hc, []).append(primary)

        # Only use hypercube-dimension arcs from THIS ELR.
        # xbrldt:targetRole on those arcs controls where members are looked up,
        # not which dimensions belong to the hypercube — scoping to the current
        # ELR prevents dimensions from other tables' ELRs leaking into this one.
        dims_by_hc: dict[QName, list[QName]] = {}
        for hc_q, dim_q in hc_dims.get(elr, []):
            dims_by_hc.setdefault(hc_q, []).append(dim_q)

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

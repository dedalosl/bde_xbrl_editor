"""Definition linkbase parser — builds HypercubeModel, DimensionModel, DomainMember."""

from __future__ import annotations

from collections import deque
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
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file

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
    2. For fragment-only hrefs like "#concept", fall back to bare fragment lookup
       in concept_map.

    IMPORTANT: when the locator explicitly names a schema document
    ("other.xsd#concept"), do not fall back to concept_map if that schema cannot
    be resolved to a namespace. Bare-fragment lookup is ambiguous when two
    schemas declare the same xml:id (for example met.xsd#eba_GXI vs dim.xsd#eba_GXI)
    and can create false xbrldte:* validation errors.
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

    if schema_url:
        return None

    # Attempt 2: bare fragment fallback for fragment-only locators.
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
        tree = parse_xml_file(linkbase_path)
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
    # elr → list of (primary_item, hypercube, arcrole, closed, context_element, target_role)
    hc_primary: dict[str, list[tuple[QName, QName, str, bool, str, str | None]]] = {}
    # elr → list of (hypercube, dimension)
    hc_dims: dict[str, list[tuple[QName, QName]]] = {}
    # dimension → default domain root (kept for compatibility in DimensionModel.domain)
    dim_domain: dict[QName, QName] = {}
    # dimension-domain arcs with ELR scoping for downstream member expansion
    dim_domain_arcs: list[tuple[QName, QName, str, float, bool]] = []
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

            use = arc.get("use", "optional")
            if use == "prohibited":
                # Prohibited arcs cancel arcs with the same from/to/arcrole in the
                # same ELR across all extended links — skip adding the arc itself.
                arcs_by_elr.setdefault(elr, [])  # ensure key exists
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
                    bool(closed), context_element or "segment", target_role,
                ))
            elif arcrole == ARCROLE_HYPERCUBE_DIMENSION:
                hc_dims.setdefault(elr, []).append((source, target))
            elif arcrole == ARCROLE_DIMENSION_DOMAIN:
                dim_domain[source] = target
                domain_usable = usable if usable is not None else True
                dim_members.setdefault(source, []).append(
                    (target, None, order, domain_usable)
                )
                dm_start_elr = target_role if target_role else elr
                dim_domain_arcs.append(
                    (source, target, dm_start_elr, order, domain_usable)
                )
            elif arcrole == ARCROLE_DOMAIN_MEMBER:
                # Domain-member relationships are resolved after all arcs are parsed.
                # Keep the DefinitionArc in arcs_by_elr; no eager dimension binding.
                pass
            elif arcrole == ARCROLE_DIMENSION_DEFAULT:
                dim_defaults[source] = target

    # Resolve dimension members using each dimension-domain root and ELR scope.
    # This avoids the previous over-broad heuristic that attached every
    # domain-member arc to every known dimension.
    seen_dim_members: dict[QName, set[tuple[QName, QName | None, float, bool]]] = {}
    for dim_q, domain_q, start_elr, dm_order, dm_usable in dim_domain_arcs:
        members = dim_members.setdefault(dim_q, [])
        member_keys = seen_dim_members.setdefault(dim_q, set())

        root_key = (domain_q, None, dm_order, dm_usable)
        if root_key not in member_keys:
            member_keys.add(root_key)
            members.append(root_key)

        for child_q in _collect_domain_member_descendants(domain_q, start_elr, arcs_by_elr):
            child_key = (child_q, domain_q, 1.0, True)
            if child_key not in member_keys:
                member_keys.add(child_key)
                members.append(child_key)

    # Build HypercubeModel objects
    hypercubes: list[HypercubeModel] = []
    for elr, prim_list in hc_primary.items():
        expanded_primaries: set[QName] = {p for p, *_ in prim_list}
        bfs_queue: list[tuple[QName, QName, str, bool, str, str | None]] = list(prim_list)
        for primary, hc, arcrole, closed, ctx, tgt_role in bfs_queue:
            # Primary-item inheritance follows domain-member relationships.
            # Some taxonomies keep those relationships in the has-hypercube ELR,
            # others in the targetRole ELR. Traverse both to avoid missing
            # inherited primary items.
            start_elrs = [elr]
            if tgt_role and tgt_role != elr:
                start_elrs.append(tgt_role)
            for start_elr in start_elrs:
                for child in _collect_domain_member_descendants(
                    primary,
                    start_elr,
                    arcs_by_elr,
                ):
                    if child not in expanded_primaries:
                        expanded_primaries.add(child)
                        new_entry = (child, hc, arcrole, closed, ctx, tgt_role)
                        prim_list.append(new_entry)
                        bfs_queue.append(new_entry)

        # Group by hypercube, tracking the targetRole of each hypercube's all/notAll arc.
        # hc → (arcrole, closed, ctx, target_role)
        hc_map: dict[QName, tuple[str, bool, str, str | None]] = {}
        primary_by_hc: dict[QName, list[QName]] = {}
        for primary, hc, arcrole, closed, ctx, tgt_role in prim_list:
            hc_map[hc] = (arcrole, closed, ctx, tgt_role)
            primary_by_hc.setdefault(hc, []).append(primary)

        # Build dims_by_hc: for each hypercube, look up hypercube-dimension arcs in
        # the ELR pointed to by xbrldt:targetRole on the all/notAll arc (if present),
        # otherwise fall back to the current ELR.  This implements XBRL Dimensions
        # §2.3 DRS targetRole semantics for the hypercube-dimension relationship.
        dims_by_hc: dict[QName, list[QName]] = {}
        for hc, (_arcrole, _closed, _ctx, tgt_role) in hc_map.items():
            lookup_elr = tgt_role if tgt_role else elr
            for hc_q, dim_q in hc_dims.get(lookup_elr, []):
                if hc_q == hc:
                    dims_by_hc.setdefault(hc, []).append(dim_q)

        for hc, (arcrole, closed, ctx, _tgt_role) in hc_map.items():
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


def _collect_domain_member_descendants(
    source: QName,
    start_elr: str,
    arcs_by_elr: dict[str, list[DefinitionArc]],
) -> list[QName]:
    """Follow domain-member relationships across targetRole boundaries.

    XBRL Dimensions allows a dimensional relationship set to continue in the
    base set named by ``xbrldt:targetRole``. For primary-item inheritance we
    therefore cannot limit the traversal to the ELR that contains the
    has-hypercube arc.
    """
    descendants: list[QName] = []
    queue: deque[tuple[QName, str]] = deque([(source, start_elr)])
    seen_states: set[tuple[QName, str]] = {(source, start_elr)}
    seen_targets: set[QName] = set()

    while queue:
        current, current_elr = queue.popleft()
        for arc in arcs_by_elr.get(current_elr, []):
            if arc.arcrole != ARCROLE_DOMAIN_MEMBER or arc.source != current:
                continue

            if arc.target not in seen_targets:
                seen_targets.add(arc.target)
                descendants.append(arc.target)

            next_elr = arc.target_role or current_elr
            state = (arc.target, next_elr)
            if state not in seen_states:
                seen_states.add(state)
                queue.append(state)

    return descendants

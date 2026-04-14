"""PWD Table Linkbase parser.

Parses table:table, table:breakdown, table:ruleNode, table:aspectNode, and
table:conceptRelationshipNode elements using the PWD namespace
http://xbrl.org/PWD/2013-05-17/table, producing TableDefinitionPWD and
BreakdownNode trees.  RC-codes are extracted from the Eurofiling label role.

BDE linkbases use formula-namespace child elements inside ruleNode to express
aspect constraints:

    <table:ruleNode xlink:label="...">
        <formula:concept>
            <formula:qname>prefix:localName</formula:qname>
        </formula:concept>
        <formula:explicitDimension dimension="prefix:dimLocal">
            <formula:member>
                <formula:qname>prefix:memberLocal</formula:qname>
            </formula:member>
        </formula:explicitDimension>
        ...
    </table:ruleNode>

All QNames in the XML use prefix:local notation and must be resolved to
Clark notation ({namespace}local) using the element's nsmap.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import (
    NS_FORMULA,
    NS_LINK,
    NS_TABLE_PWD,
    NS_XBRLDT,
    NS_XLINK,
    ROLE_DEFINITION_LINKBASE_REF,
)
from bde_xbrl_editor.taxonomy.models import (
    BreakdownNode,
    QName,
    TableDefinitionPWD,
    TaxonomyParseError,
)
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file

# PWD namespace tags
_TABLE = f"{{{NS_TABLE_PWD}}}table"
_BREAKDOWN = f"{{{NS_TABLE_PWD}}}breakdown"
_RULE_NODE = f"{{{NS_TABLE_PWD}}}ruleNode"
_ASPECT_NODE = f"{{{NS_TABLE_PWD}}}aspectNode"
_CONCEPT_REL_NODE = f"{{{NS_TABLE_PWD}}}conceptRelationshipNode"
_DIMENSION_REL_NODE = f"{{{NS_TABLE_PWD}}}dimensionRelationshipNode"
_TABLE_BREAKDOWN_ARC = f"{{{NS_TABLE_PWD}}}tableBreakdownArc"
_BREAKDOWN_TREE_ARC = f"{{{NS_TABLE_PWD}}}breakdownTreeArc"
_DEFINITION_NODE_SUBTREE_ARC = f"{{{NS_TABLE_PWD}}}definitionNodeSubtreeArc"

# Formula namespace tags (used inside ruleNode for aspect constraints)
_F_CONCEPT = f"{{{NS_FORMULA}}}concept"
_F_QNAME = f"{{{NS_FORMULA}}}qname"
_F_EXPLICIT_DIM = f"{{{NS_FORMULA}}}explicitDimension"
_F_TYPED_DIM = f"{{{NS_FORMULA}}}typedDimension"
_F_MEMBER = f"{{{NS_FORMULA}}}member"
_F_PERIOD = f"{{{NS_FORMULA}}}period"
_DF_NS = "http://xbrl.org/2008/filter/dimension"
_DF_EXPLICIT_DIM = f"{{{_DF_NS}}}explicitDimension"
_DF_DIMENSION = f"{{{_DF_NS}}}dimension"
_DF_MEMBER = f"{{{_DF_NS}}}member"
_DF_QNAME = f"{{{_DF_NS}}}qname"
_DF_LINKROLE = f"{{{_DF_NS}}}linkrole"
_DF_ARCROLE = f"{{{_DF_NS}}}arcrole"
_DF_AXIS = f"{{{_DF_NS}}}axis"
_DIMENSION_ASPECT = f"{{{NS_TABLE_PWD}}}dimensionAspect"

_XLINK_HREF = f"{{{NS_XLINK}}}href"
_XLINK_LABEL_ATTR = f"{{{NS_XLINK}}}label"
_XLINK_FROM = f"{{{NS_XLINK}}}from"
_XLINK_TO = f"{{{NS_XLINK}}}to"
_XLINK_ROLE = f"{{{NS_XLINK}}}role"
_XLINK_ARCROLE = f"{{{NS_XLINK}}}arcrole"
_XBRLDT_USABLE = f"{{{NS_XBRLDT}}}usable"

# Axis values as they appear in the XML tableBreakdownArc/@axis attribute
_AXIS_X = "x"
_AXIS_Y = "y"
_AXIS_Z = "z"


def _prefix_to_clark(text: str, nsmap: dict) -> str | None:
    """Resolve 'prefix:local' notation to Clark '{namespace}local' using element nsmap."""
    text = text.strip()
    if not text:
        return None
    if ":" in text:
        prefix, local = text.split(":", 1)
        ns = nsmap.get(prefix)
        if ns:
            return f"{{{ns}}}{local}"
        # prefix not found in map — return as-is; QName.from_clark will reject it
        return None
    return text


def _node_type_from_tag(tag: str) -> str:
    local = tag.split("}")[-1] if "}" in tag else tag
    mapping = {
        "ruleNode": "rule",
        "aspectNode": "aspect",
        "conceptRelationshipNode": "conceptRelationship",
        "dimensionRelationshipNode": "dimensionRelationship",
    }
    return mapping.get(local, "rule")


_VALID_PCO = frozenset(("parent-first", "children-first"))


def _build_breakdown_node(
    el: etree._Element,
    label_map: dict[str, str],  # xlink:label → display label
    rc_map: dict[str, str],     # xlink:label → rc_code (eurofiling roles)
    fin_map: dict[str, str],    # xlink:label → fin_code (bde fin-code role)
    child_map: dict[str, list[etree._Element]],  # xlink:label → child elements
    filter_map: dict[str, list[dict[str, Any]]],  # xlink:label → parsed aspect-node filters
    inherited_pco: str = "parent-first",  # effective parentChildOrder from ancestor
) -> BreakdownNode:
    xlink_label = el.get(_XLINK_LABEL_ATTR, "")
    node_type = _node_type_from_tag(el.tag)
    label = label_map.get(xlink_label)
    rc_code = rc_map.get(xlink_label)
    fin_code = fin_map.get(xlink_label)
    is_abstract = el.get("abstract", "false").lower() == "true"
    merge = el.get("merge", "false").lower() == "true"
    own_pco = el.get("parentChildOrder")
    effective_pco = own_pco if own_pco in _VALID_PCO else inherited_pco

    aspect_constraints: dict[str, Any] = {}
    # explicit_dims accumulates across multiple <formula:explicitDimension> children
    explicit_dims: dict[str, str] = {}  # dim_clark → member_clark

    for child_el in el:
        if not isinstance(child_el.tag, str):
            continue
        tag = child_el.tag

        if tag == _DIMENSION_ASPECT:
            if child_el.text:
                dim_clark = _prefix_to_clark(child_el.text, child_el.nsmap)
                if dim_clark:
                    aspect_constraints["dimensionAspect"] = dim_clark

        if tag == _F_CONCEPT:
            # <formula:concept><formula:qname>prefix:local</formula:qname></formula:concept>
            qname_el = child_el.find(_F_QNAME)
            if qname_el is not None and qname_el.text:
                clark = _prefix_to_clark(qname_el.text, child_el.nsmap)
                if clark:
                    aspect_constraints["concept"] = clark

        elif tag == _F_EXPLICIT_DIM:
            # <formula:explicitDimension dimension="prefix:dim">
            #   <formula:member><formula:qname>prefix:mem</formula:qname></formula:member>
            # </formula:explicitDimension>
            dim_attr = child_el.get("dimension", "")
            if dim_attr:
                dim_clark = _prefix_to_clark(dim_attr, child_el.nsmap)
                if dim_clark:
                    # member qname is nested two levels deep
                    member_el = child_el.find(_F_MEMBER)
                    if member_el is not None:
                        qname_el = member_el.find(_F_QNAME)
                    else:
                        qname_el = child_el.find(_F_QNAME)
                    if qname_el is not None and qname_el.text:
                        mem_clark = _prefix_to_clark(qname_el.text, qname_el.nsmap)
                        if mem_clark:
                            explicit_dims[dim_clark] = mem_clark

        elif tag == _F_TYPED_DIM:
            # typed dimensions — store dimension QName only for now
            dim_attr = child_el.get("dimension", "")
            if dim_attr:
                dim_clark = _prefix_to_clark(dim_attr, child_el.nsmap)
                if dim_clark:
                    aspect_constraints["typedDimension"] = dim_clark

    if explicit_dims:
        aspect_constraints["explicitDimension"] = explicit_dims
    if xlink_label in filter_map:
        aspect_constraints["explicitDimensionFilters"] = list(filter_map[xlink_label])

    # Build children recursively, propagating effective_pco as the inherited value
    children: list[BreakdownNode] = []
    for child_el in child_map.get(xlink_label, []):
        children.append(
            _build_breakdown_node(
                child_el,
                label_map,
                rc_map,
                fin_map,
                child_map,
                filter_map,
                effective_pco,
            )
        )

    return BreakdownNode(
        node_type=node_type,
        label=label,
        rc_code=rc_code,
        fin_code=fin_code,
        is_abstract=is_abstract,
        merge=merge,
        children=children,
        aspect_constraints=aspect_constraints,
        parent_child_order=effective_pco,
    )


_RC_CODE_ROLES = {
    "http://www.eurofiling.info/xbrl/role/rc-code",
    "http://www.eurofiling.info/xbrl/role/row-code",
    "http://www.eurofiling.info/xbrl/role/col-code",
}
_FIN_CODE_ROLE = "http://www.bde.es/xbrl/role/fin-code"

_NS_GEN = "http://xbrl.org/2008/generic"
_NS_GENLAB = "http://xbrl.org/2008/label"
_ARC_ELEMENT_LABEL = "http://xbrl.org/arcrole/2008/element-label"

_F_LOC = f"{{{NS_LINK}}}loc"
_F_LABEL_EL = f"{{{_NS_GENLAB}}}label"
_F_GEN_ARC = f"{{{_NS_GEN}}}arc"
_XLINK_HREF_ATTR = f"{{{NS_XLINK}}}href"
_LINKBASE_REF = f"{{{NS_LINK}}}linkbaseRef"
_ROLE_REF = f"{{{NS_LINK}}}roleRef"


def _cache_root_for(path: Path) -> Path | None:
    for parent in (path, *path.parents):
        if parent.name == "cache":
            return parent
    return None


def _resolve_href_to_local_path(href: str, *, base_path: Path) -> Path | None:
    href = (href or "").strip()
    if not href:
        return None
    href_no_fragment = href.split("#", 1)[0]
    if not href_no_fragment:
        return None
    if href_no_fragment.startswith(("http://", "https://")):
        parsed = urlparse(href_no_fragment)
        cache_root = _cache_root_for(base_path)
        if cache_root is None:
            return None
        return cache_root / parsed.netloc / parsed.path.lstrip("/")
    return (base_path.parent / href_no_fragment).resolve()


def _schema_id_qname_map(schema_path: Path) -> dict[str, str]:
    if not schema_path.is_file():
        return {}
    try:
        tree = parse_xml_file(schema_path)
    except Exception:  # noqa: BLE001
        return {}

    root = tree.getroot()
    target_ns = root.get("targetNamespace", "")
    id_map: dict[str, str] = {}
    for el in root.iter("{http://www.w3.org/2001/XMLSchema}element"):
        elem_id = el.get("id")
        elem_name = el.get("name")
        if elem_id and elem_name and target_ns:
            id_map[elem_id] = f"{{{target_ns}}}{elem_name}"
    return id_map


def _descendant_members_from_role(
    *,
    role_uri: str | None,
    seed_member_clark: str,
    role_href_map: dict[str, str],
    base_path: Path,
) -> list[str]:
    if not role_uri:
        return []

    role_href = role_href_map.get(role_uri)
    if not role_href:
        return []

    schema_path = _resolve_href_to_local_path(role_href, base_path=base_path)
    if schema_path is None or not schema_path.is_file():
        return []

    try:
        schema_tree = parse_xml_file(schema_path)
    except Exception:  # noqa: BLE001
        return []
    schema_root = schema_tree.getroot()

    def_linkbases: list[Path] = []
    for lb_ref in schema_root.iter(_LINKBASE_REF):
        if lb_ref.get(_XLINK_ROLE) != ROLE_DEFINITION_LINKBASE_REF:
            continue
        lb_href = lb_ref.get(_XLINK_HREF_ATTR, "")
        lb_path = _resolve_href_to_local_path(lb_href, base_path=schema_path)
        if lb_path is not None and lb_path.is_file():
            def_linkbases.append(lb_path)

    if not def_linkbases:
        sibling_def = schema_path.with_name(schema_path.stem + "-def.xml")
        if sibling_def.is_file():
            def_linkbases.append(sibling_def)
        else:
            hier_def = schema_path.with_name("hier-def.xml")
            if hier_def.is_file():
                def_linkbases.append(hier_def)

    descendants: list[str] = []
    seen: set[str] = {seed_member_clark}

    for def_linkbase in def_linkbases:
        try:
            def_tree = parse_xml_file(def_linkbase)
        except Exception:  # noqa: BLE001
            continue
        id_cache: dict[Path, dict[str, str]] = {}
        for def_link in def_tree.getroot().iter(f"{{{NS_LINK}}}definitionLink"):
            if def_link.get(_XLINK_ROLE) != role_uri:
                continue
            loc_map: dict[str, str] = {}
            for loc in def_link.iter(f"{{{NS_LINK}}}loc"):
                loc_label = loc.get(_XLINK_LABEL_ATTR, "")
                loc_href = loc.get(_XLINK_HREF_ATTR, "")
                target_path = _resolve_href_to_local_path(loc_href, base_path=def_linkbase)
                if target_path is None:
                    continue
                fragment = loc_href.split("#", 1)[1] if "#" in loc_href else ""
                if not fragment:
                    continue
                if target_path not in id_cache:
                    id_cache[target_path] = _schema_id_qname_map(target_path)
                qname_clark = id_cache[target_path].get(fragment)
                if qname_clark:
                    loc_map[loc_label] = qname_clark

            adjacency: dict[str, list[str]] = {}
            for arc in def_link.iter(f"{{{NS_LINK}}}definitionArc"):
                if arc.get(_XLINK_ARCROLE) != "http://xbrl.org/int/dim/arcrole/domain-member":
                    continue
                if arc.get(_XBRLDT_USABLE, "true").lower() == "false":
                    continue
                frm = loc_map.get(arc.get(_XLINK_FROM, ""))
                to = loc_map.get(arc.get(_XLINK_TO, ""))
                if frm and to:
                    adjacency.setdefault(frm, []).append(to)

            queue = list(adjacency.get(seed_member_clark, []))
            while queue:
                candidate = queue.pop(0)
                if candidate in seen:
                    continue
                seen.add(candidate)
                queue.extend(adjacency.get(candidate, []))
                if not adjacency.get(candidate):
                    descendants.append(candidate)
            if descendants:
                return descendants

    return descendants


def _parse_explicit_dimension_filter_resource(
    filter_el: etree._Element,
    *,
    complement: bool,
    role_href_map: dict[str, str],
    base_path: Path,
) -> dict[str, Any] | None:
    """Parse a df:explicitDimension resource attached through aspectNodeFilterArc."""
    if filter_el.tag != _DF_EXPLICIT_DIM:
        return None

    dim_el = filter_el.find(_DF_DIMENSION)
    dim_qname_el = dim_el.find(_DF_QNAME) if dim_el is not None else None
    dim_text = (
        (dim_qname_el.text or "").strip()
        if dim_qname_el is not None
        else (dim_el.text or "").strip() if dim_el is not None else ""
    )
    dim_clark = _prefix_to_clark(dim_text, filter_el.nsmap) if dim_text else None
    if not dim_clark:
        return None

    members: list[dict[str, str | None]] = []
    for member_el in filter_el.findall(_DF_MEMBER):
        qname_el = member_el.find(_DF_QNAME)
        member_text = (qname_el.text or "").strip() if qname_el is not None else ""
        member_clark = _prefix_to_clark(member_text, member_el.nsmap) if member_text else None
        if not member_clark:
            continue
        linkrole = (member_el.findtext(_DF_LINKROLE) or "").strip() or None
        arcrole = (member_el.findtext(_DF_ARCROLE) or "").strip() or None
        axis = (member_el.findtext(_DF_AXIS) or "").strip() or None
        members.append({
            "member": member_clark,
            "linkrole": linkrole,
            "arcrole": arcrole,
            "axis": axis,
            "resolved_members": _descendant_members_from_role(
                role_uri=linkrole,
                seed_member_clark=member_clark,
                role_href_map=role_href_map,
                base_path=base_path,
            ) if axis == "descendant" and arcrole == "http://xbrl.org/int/dim/arcrole/domain-member" else [],
        })

    return {
        "dimension": dim_clark,
        "members": members,
        "complement": complement,
    }


def _parse_node_label_file(
    lb_path: Path,
    id_label_map: dict[str, str],  # node id → display label (first language wins)
    id_rc_map: dict[str, str],     # node id → rc-code (eurofiling rc/row/col-code roles)
    id_fin_map: dict[str, str],    # node id → fin-code (bde fin-code role only)
    language_preference: tuple[str, ...] = ("es", "en"),
) -> None:
    """Parse a generic label linkbase (e.g. *-lab-es.xml, *-lab-codes.xml) and
    populate the id → label / rc / fin maps.

    The linkbase structure is:
      <link:loc xlink:href="rend.xml#nodeId" xlink:label="loc_..."/>
      <label:label xlink:label="label_..." xlink:role="..." xml:lang="...">text</label:label>
      <gen:arc xlink:arcrole="http://xbrl.org/arcrole/2008/element-label"
               xlink:from="loc_..." xlink:to="label_..."/>
    """
    if not lb_path.is_file():
        return
    try:
        tree = parse_xml_file(lb_path)
    except Exception:  # noqa: BLE001
        return

    root = tree.getroot()

    for gen_link in root.iter(f"{{{_NS_GEN}}}link"):
        # Build loc → fragment-id map
        loc_to_id: dict[str, str] = {}
        for loc_el in gen_link.iter(f"{{{NS_LINK}}}loc"):
            xl = loc_el.get(_XLINK_LABEL_ATTR)
            href = loc_el.get(_XLINK_HREF_ATTR, "")
            if xl and "#" in href:
                fragment = href.split("#", 1)[1]
                loc_to_id[xl] = fragment

        # Build label_xlink → (text, lang, role) map
        label_res: dict[str, tuple[str, str, str]] = {}
        for lbl_el in gen_link.iter(_F_LABEL_EL):
            xl = lbl_el.get(_XLINK_LABEL_ATTR)
            if xl and lbl_el.text:
                lang = lbl_el.get("{http://www.w3.org/XML/1998/namespace}lang", "")
                role = lbl_el.get(_XLINK_ROLE, "")
                label_res[xl] = (lbl_el.text.strip(), lang, role)

        # Follow arcs: from=loc_xl → to=label_xl
        for arc_el in gen_link.iter(_F_GEN_ARC):
            frm = arc_el.get(_XLINK_FROM, "")
            to = arc_el.get(_XLINK_TO, "")
            node_id = loc_to_id.get(frm)
            entry = label_res.get(to)
            if not node_id or not entry:
                continue
            text, lang, role = entry
            if role == _FIN_CODE_ROLE:
                if node_id not in id_fin_map:
                    id_fin_map[node_id] = text
            elif role in _RC_CODE_ROLES:
                if node_id not in id_rc_map:
                    id_rc_map[node_id] = text
            elif node_id not in id_label_map or (
                language_preference and lang == language_preference[0]
            ):
                id_label_map[node_id] = text


def parse_table_linkbase(
    linkbase_path: Path,
    label_lookup: dict[QName, list] | None = None,  # QName → list[Label]
) -> list[TableDefinitionPWD]:
    """Parse a PWD Table Linkbase file and return all table definitions.

    Args:
        linkbase_path: Absolute path to the table linkbase XML file.
        label_lookup: Optional label dictionary from the LabelResolver to
            populate BreakdownNode.label and .rc_code fields.

    Returns:
        List of TableDefinitionPWD objects.

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
    tables: list[TableDefinitionPWD] = []

    # Load sibling label/rc-code linkbase files (e.g. *-lab-es.xml, *-lab-codes.xml)
    id_label_map: dict[str, str] = {}
    id_rc_map: dict[str, str] = {}
    id_fin_map: dict[str, str] = {}
    stem = linkbase_path.stem  # e.g. "fi_31-2-rend"
    base = stem[: -len("-rend")] if stem.endswith("-rend") else stem
    lb_dir = linkbase_path.parent
    for candidate in lb_dir.glob(f"{base}-lab*.xml"):
        _parse_node_label_file(candidate, id_label_map, id_rc_map, id_fin_map)

    role_href_map: dict[str, str] = {
        role_ref.get("roleURI", ""): role_ref.get(_XLINK_HREF_ATTR, "")
        for role_ref in root.iter(_ROLE_REF)
        if role_ref.get("roleURI") and role_ref.get(_XLINK_HREF_ATTR)
    }

    for lb_el in root:
        _parse_linkbase_element(
            lb_el,
            tables,
            id_label_map,
            id_rc_map,
            id_fin_map,
            role_href_map,
            linkbase_path,
        )

    # If the root is itself a linkbase or directly contains tables
    if not tables:
        _parse_linkbase_element(
            root,
            tables,
            id_label_map,
            id_rc_map,
            id_fin_map,
            role_href_map,
            linkbase_path,
        )

    return tables


def _parse_linkbase_element(
    container: etree._Element,
    tables: list[TableDefinitionPWD],
    id_label_map: dict[str, str] | None = None,
    id_rc_map: dict[str, str] | None = None,
    id_fin_map: dict[str, str] | None = None,
    role_href_map: dict[str, str] | None = None,
    linkbase_path: Path | None = None,
) -> None:
    """Parse table elements from within a linkbase or linkbase container."""
    for table_el in container.iter(_TABLE):
        table_id = table_el.get("id", "")
        table_pco_raw = table_el.get("parentChildOrder")
        table_pco = table_pco_raw if table_pco_raw in _VALID_PCO else "parent-first"

        # The gen:link parent holds all sibling nodes/arcs for this table.
        # The xlink:role (ELR) is on the gen:link container, not on table:table itself.
        parent = table_el.getparent() if table_el.getparent() is not None else container
        elr = table_el.get(_XLINK_ROLE, "") or parent.get(_XLINK_ROLE, "")

        # Index all elements with xlink:label in this scope
        all_nodes: dict[str, etree._Element] = {}
        for el in parent.iter():
            xl = el.get(_XLINK_LABEL_ATTR)
            if xl:
                all_nodes[xl] = el

        table_xl = table_el.get(_XLINK_LABEL_ATTR, "")

        # Build arc maps by inspecting local tag names (namespace-agnostic).
        # Children are stored as (order, child_xl) and sorted by order before use.
        breakdown_arcs: dict[str, tuple[float, str]] = {}  # breakdown_xl → (order, axis)
        node_children_ordered: dict[str, list[tuple[float, str]]] = {}  # parent → [(order, child_xl)]
        aspect_node_filters: dict[str, list[dict[str, Any]]] = {}

        for el in parent.iter():
            if not isinstance(el.tag, str):
                continue
            local = el.tag.split("}")[-1] if "}" in el.tag else el.tag
            try:
                arc_order = float(el.get("order", "1"))
            except (TypeError, ValueError):
                arc_order = 1.0
            if local == "tableBreakdownArc":
                frm = el.get(_XLINK_FROM, "")
                to = el.get(_XLINK_TO, "")
                axis = el.get("axis", _AXIS_X)
                if frm == table_xl and to:
                    # Keep only the lowest-order arc if duplicates exist
                    if to not in breakdown_arcs or arc_order < breakdown_arcs[to][0]:
                        breakdown_arcs[to] = (arc_order, axis)
            elif local in ("breakdownTreeArc", "definitionNodeSubtreeArc"):
                frm = el.get(_XLINK_FROM, "")
                to = el.get(_XLINK_TO, "")
                if frm and to:
                    node_children_ordered.setdefault(frm, []).append((arc_order, to))
            elif local == "aspectNodeFilterArc":
                frm = el.get(_XLINK_FROM, "")
                to = el.get(_XLINK_TO, "")
                filter_el = all_nodes.get(to)
                if not frm or filter_el is None:
                    continue
                parsed_filter = _parse_explicit_dimension_filter_resource(
                    filter_el,
                    complement=el.get("complement", "false").lower() == "true",
                    role_href_map=role_href_map or {},
                    base_path=linkbase_path or Path("."),
                )
                if parsed_filter is not None:
                    aspect_node_filters.setdefault(frm, []).append(parsed_filter)

        # Sort children by arc order and build the final axis → breakdown map
        node_children: dict[str, list[str]] = {
            parent_xl: [child_xl for _, child_xl in sorted(pairs)]
            for parent_xl, pairs in node_children_ordered.items()
        }
        # Sort breakdown arcs by order to get consistent breakdown ordering per axis
        breakdown_arcs_sorted: dict[str, str] = {
            bd_xl: axis
            for bd_xl, (_, axis) in sorted(breakdown_arcs.items(), key=lambda kv: kv[1][0])
        }

        # Build label/rc/fin maps keyed by xlink:label.
        # Primary source: sibling *-lab-*.xml files, keyed by element id attribute.
        # We build a id→xlink:label reverse map first, then translate.
        label_map: dict[str, str] = {}
        rc_map: dict[str, str] = {}
        fin_map: dict[str, str] = {}
        if id_label_map or id_rc_map or id_fin_map:
            id_to_xl: dict[str, str] = {}
            for xl, el in all_nodes.items():
                elem_id = el.get("id")
                if elem_id:
                    id_to_xl[elem_id] = xl
            for elem_id, lbl in (id_label_map or {}).items():
                xl = id_to_xl.get(elem_id)
                if xl:
                    label_map[xl] = lbl
            for elem_id, rc in (id_rc_map or {}).items():
                xl = id_to_xl.get(elem_id)
                if xl:
                    rc_map[xl] = rc
            for elem_id, fin in (id_fin_map or {}).items():
                xl = id_to_xl.get(elem_id)
                if xl:
                    fin_map[xl] = fin
        # Fallback: inline label/rc attributes on the elements themselves
        for xl, el in all_nodes.items():
            if xl not in label_map:
                lbl = el.get("label") or el.get(f"{{{NS_TABLE_PWD}}}label")
                if lbl:
                    label_map[xl] = lbl

        # Build child element map for recursion
        child_elem_map: dict[str, list[etree._Element]] = {}
        for parent_xl, child_xls in node_children.items():
            child_elem_map[parent_xl] = [
                all_nodes[c] for c in child_xls if c in all_nodes
            ]

        # Separate breakdown root nodes by axis, also resolving each breakdown's PCO.
        # breakdown_pco[bd_xl] = effective parentChildOrder for that breakdown
        x_nodes: list[tuple[etree._Element, str]] = []  # (element, pco)
        y_nodes: list[tuple[etree._Element, str]] = []
        z_nodes: list[tuple[etree._Element, str]] = []

        for bd_xl, axis in breakdown_arcs_sorted.items():
            bd_el = all_nodes.get(bd_xl)
            if bd_el is not None:
                bd_pco_raw = bd_el.get("parentChildOrder")
                bd_pco = bd_pco_raw if bd_pco_raw in _VALID_PCO else table_pco
            else:
                bd_pco = table_pco
            # Root nodes are children of the breakdown node via breakdownTreeArc,
            # already ordered by arc @order via node_children.
            root_nodes = [
                (all_nodes[c], bd_pco)
                for c in node_children.get(bd_xl, [])
                if c in all_nodes
            ]
            if axis == _AXIS_X:
                x_nodes.extend(root_nodes)
            elif axis == _AXIS_Y:
                y_nodes.extend(root_nodes)
            else:
                z_nodes.extend(root_nodes)

        def make_root_node(
            node_pco_pairs: list[tuple[etree._Element, str]],
            _lm: dict[str, str] = label_map,
            _rm: dict[str, str] = rc_map,
            _fm: dict[str, str] = fin_map,
            _cem: dict[str, list[etree._Element]] = child_elem_map,
            _afm: dict[str, list[dict[str, Any]]] = aspect_node_filters,
        ) -> BreakdownNode:
            if not node_pco_pairs:
                return BreakdownNode(node_type="rule", label=None)
            if len(node_pco_pairs) == 1:
                n, pco = node_pco_pairs[0]
                return _build_breakdown_node(n, _lm, _rm, _fm, _cem, _afm, pco)
            # Multiple root nodes — wrap in abstract parent
            root = BreakdownNode(node_type="rule", is_abstract=True)
            root.children = [
                _build_breakdown_node(n, _lm, _rm, _fm, _cem, _afm, pco)
                for n, pco in node_pco_pairs
            ]
            return root

        x_bd = make_root_node(x_nodes)
        y_bd = make_root_node(y_nodes)
        z_bds = tuple(
            _build_breakdown_node(
                n,
                label_map,
                rc_map,
                fin_map,
                child_elem_map,
                aspect_node_filters,
                pco,
            )
            for n, pco in z_nodes
        )

        table_label = label_map.get(table_xl, table_id)
        table_code = fin_map.get(table_xl)

        tables.append(TableDefinitionPWD(
            table_id=table_id,
            label=table_label,
            extended_link_role=elr,
            x_breakdown=x_bd,
            y_breakdown=y_bd,
            table_code=table_code,
            z_breakdowns=z_bds,
        ))

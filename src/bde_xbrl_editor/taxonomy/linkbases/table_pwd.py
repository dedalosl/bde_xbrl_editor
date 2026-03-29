"""PWD Table Linkbase parser.

Parses table:table, table:breakdown, table:ruleNode, table:aspectNode, and
table:conceptRelationshipNode elements using the PWD namespace
http://xbrl.org/PWD/2013-05-17/table, producing TableDefinitionPWD and
BreakdownNode trees.  RC-codes are extracted from the Eurofiling label role.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import NS_TABLE_PWD, NS_XLINK
from bde_xbrl_editor.taxonomy.models import (
    BreakdownNode,
    QName,
    TableDefinitionPWD,
    TaxonomyParseError,
)

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

_XLINK_HREF = f"{{{NS_XLINK}}}href"
_XLINK_LABEL_ATTR = f"{{{NS_XLINK}}}label"
_XLINK_FROM = f"{{{NS_XLINK}}}from"
_XLINK_TO = f"{{{NS_XLINK}}}to"
_XLINK_ROLE = f"{{{NS_XLINK}}}role"
_XLINK_ARCROLE = f"{{{NS_XLINK}}}arcrole"

# Arcrole URIs for table linkbase
_ARCROLE_TABLE_BREAKDOWN = f"{NS_TABLE_PWD}/arcrole/table-breakdown"
_ARCROLE_BREAKDOWN_TREE = f"{NS_TABLE_PWD}/arcrole/breakdown-tree"
_ARCROLE_DEF_NODE_SUBTREE = f"{NS_TABLE_PWD}/arcrole/definition-node-subtree"

_AXIS_X = "xAxis"
_AXIS_Y = "yAxis"
_AXIS_Z = "zAxis"


def _node_type_from_tag(tag: str) -> str:
    local = tag.split("}")[-1] if "}" in tag else tag
    mapping = {
        "ruleNode": "rule",
        "aspectNode": "aspect",
        "conceptRelationshipNode": "conceptRelationship",
        "dimensionRelationshipNode": "dimensionRelationship",
    }
    return mapping.get(local, "rule")


def _build_breakdown_node(
    el: etree._Element,
    label_map: dict[str, str],  # xlink:label → display label
    rc_map: dict[str, str],     # xlink:label → rc_code
    child_map: dict[str, list[etree._Element]],  # xlink:label → child elements
) -> BreakdownNode:
    xlink_label = el.get(_XLINK_LABEL_ATTR, "")
    node_type = _node_type_from_tag(el.tag)
    label = label_map.get(xlink_label)
    rc_code = rc_map.get(xlink_label)
    is_abstract = el.get("abstract", "false").lower() == "true"
    merge = el.get("merge", "false").lower() == "true"

    aspect_constraints: dict[str, Any] = {}
    # Extract aspect constraints from child elements
    for child_el in el:
        if not isinstance(child_el.tag, str):  # skip comments / PIs
            continue
        local = child_el.tag.split("}")[-1] if "}" in child_el.tag else child_el.tag
        if local == "ruleSet":
            # Rule nodes have ruleSets with aspect values
            for aspect_el in child_el:
                if not isinstance(aspect_el.tag, str):
                    continue
                aspect_local = aspect_el.tag.split("}")[-1] if "}" in aspect_el.tag else aspect_el.tag
                aspect_constraints[aspect_local] = aspect_el.text or aspect_el.get("value")
        elif local in ("concept", "period", "unit", "explicitDimension", "typedDimension"):
            aspect_constraints[local] = aspect_el.text or aspect_el.get("value")

    # Build children recursively
    children: list[BreakdownNode] = []
    for child_el in child_map.get(xlink_label, []):
        children.append(_build_breakdown_node(child_el, label_map, rc_map, child_map))

    return BreakdownNode(
        node_type=node_type,
        label=label,
        rc_code=rc_code,
        is_abstract=is_abstract,
        merge=merge,
        children=children,
        aspect_constraints=aspect_constraints,
    )


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
        tree = etree.parse(str(linkbase_path))  # noqa: S320
    except etree.XMLSyntaxError as exc:
        raise TaxonomyParseError(
            file_path=str(linkbase_path),
            message=str(exc),
            line=exc.lineno,
            column=exc.offset,
        ) from exc

    root = tree.getroot()
    tables: list[TableDefinitionPWD] = []

    for lb_el in root:
        # The linkbase element may contain a linkbase wrapper or be a linkbase itself
        _parse_linkbase_element(lb_el, tables)

    # If the root is itself a linkbase or directly contains tables
    if not tables:
        _parse_linkbase_element(root, tables)

    return tables


def _parse_linkbase_element(container: etree._Element, tables: list[TableDefinitionPWD]) -> None:
    """Parse table elements from within a linkbase or linkbase container."""
    # Collect all table elements
    for table_el in container.iter(_TABLE):
        table_id = table_el.get("id", "")
        elr = table_el.get(_XLINK_ROLE, "")

        # Collect all named nodes in this linkbase (table + all breakdown nodes)
        all_nodes: dict[str, etree._Element] = {}

        # Index all elements with xlink:label in this table's scope
        # We use the parent linkbase container scope
        parent = table_el.getparent() if table_el.getparent() is not None else container
        for el in parent.iter():
            xl = el.get(_XLINK_LABEL_ATTR)
            if xl:
                all_nodes[xl] = el

        # Build arc maps
        # breakdown_arcs: table xlink:label → list of breakdown xlink:labels (with axis)
        table_xl = table_el.get(_XLINK_LABEL_ATTR, "")
        breakdown_arcs: dict[str, tuple[str, str]] = {}  # breakdown_xl → (axis, elr)
        node_children: dict[str, list[str]] = {}  # parent_xl → [child_xl]

        for el in parent.iter():
            if not isinstance(el.tag, str):  # skip comments / PIs
                continue
            tag_local = el.tag.split("}")[-1] if "}" in el.tag else el.tag
            if tag_local == "tableBreakdownArc":
                frm = el.get(_XLINK_FROM, "")
                to = el.get(_XLINK_TO, "")
                axis = el.get("axis", _AXIS_X)
                if frm == table_xl:
                    breakdown_arcs[to] = (axis, elr)
            elif tag_local in ("breakdownTreeArc", "definitionNodeSubtreeArc"):
                frm = el.get(_XLINK_FROM, "")
                to = el.get(_XLINK_TO, "")
                if frm and to:
                    node_children.setdefault(frm, []).append(to)

        # Build label/rc maps (placeholder — labels resolved by loader)
        label_map: dict[str, str] = {}
        rc_map: dict[str, str] = {}
        for xl, el in all_nodes.items():
            lbl = el.get("label") or el.get(f"{{{NS_TABLE_PWD}}}label")
            if lbl:
                label_map[xl] = lbl

        # Build child element map for recursion
        child_elem_map: dict[str, list[etree._Element]] = {}
        for parent_xl, child_xls in node_children.items():
            child_elem_map[parent_xl] = [
                all_nodes[c] for c in child_xls if c in all_nodes
            ]

        # Separate breakdowns by axis
        x_nodes: list[etree._Element] = []
        y_nodes: list[etree._Element] = []
        z_nodes: list[etree._Element] = []

        for bd_xl, (axis, _) in breakdown_arcs.items():
            bd_el = all_nodes.get(bd_xl)
            if bd_el is None:
                continue
            # Get root nodes under this breakdown
            root_nodes = [
                all_nodes[c]
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
            node_els: list[etree._Element],
            _lm: dict[str, str] = label_map,
            _rm: dict[str, str] = rc_map,
            _cem: dict[str, list[etree._Element]] = child_elem_map,
        ) -> BreakdownNode:
            if not node_els:
                return BreakdownNode(node_type="rule", label=None)
            if len(node_els) == 1:
                return _build_breakdown_node(node_els[0], _lm, _rm, _cem)
            # Multiple root nodes — wrap in abstract parent
            root = BreakdownNode(node_type="rule", is_abstract=True)
            root.children = [
                _build_breakdown_node(n, _lm, _rm, _cem)
                for n in node_els
            ]
            return root

        x_bd = make_root_node(x_nodes)
        y_bd = make_root_node(y_nodes)
        z_bds = tuple(
            _build_breakdown_node(n, label_map, rc_map, child_elem_map)
            for n in z_nodes
        )

        table_label = label_map.get(table_xl, table_id)

        tables.append(TableDefinitionPWD(
            table_id=table_id,
            label=table_label,
            extended_link_role=elr,
            x_breakdown=x_bd,
            y_breakdown=y_bd,
            z_breakdowns=z_bds,
        ))

"""Presentation linkbase parser — builds PresentationNetwork objects per ELR."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import ARCROLE_PRESENTATION, NS_LINK, NS_XLINK
from bde_xbrl_editor.taxonomy.models import (
    PresentationArc,
    PresentationNetwork,
    QName,
    TaxonomyParseError,
)

_PRES_LINK = f"{{{NS_LINK}}}presentationLink"
_LOC = f"{{{NS_LINK}}}loc"
_PRES_ARC = f"{{{NS_LINK}}}presentationArc"
_XLINK_HREF = f"{{{NS_XLINK}}}href"
_XLINK_LABEL = f"{{{NS_XLINK}}}label"
_XLINK_FROM = f"{{{NS_XLINK}}}from"
_XLINK_TO = f"{{{NS_XLINK}}}to"
_XLINK_ARCROLE = f"{{{NS_XLINK}}}arcrole"
_XLINK_ROLE = f"{{{NS_XLINK}}}role"
_ARCROLE_GROUP_TABLE = "http://www.eurofiling.info/xbrl/arcrole/group-table"


@dataclass
class PresentationLinkbaseParseResult:
    """Parsed presentation linkbase payload plus table-order metadata."""

    networks: dict[str, PresentationNetwork]
    group_table_children: dict[str, list[tuple[float, str]]] = field(default_factory=dict)
    group_table_rend_fragments: set[str] = field(default_factory=set)
    group_table_root_fragment: str | None = None


def parse_presentation_linkbase(
    linkbase_path: Path,
    concept_map: dict[str, QName],
) -> PresentationLinkbaseParseResult:
    """Parse a presentation linkbase and return PresentationNetworks keyed by ELR.

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
    networks: dict[str, PresentationNetwork] = {}
    group_table_children: dict[str, list[tuple[float, str]]] = {}
    group_table_root_fragment: str | None = None

    local_label_to_fragment: dict[str, str] = {}
    local_label_is_rend: set[str] = set()
    for loc in root.iter(_LOC):
        label = loc.get(_XLINK_LABEL, "")
        href = loc.get(_XLINK_HREF, "")
        if label and "#" in href:
            fragment = href.split("#", 1)[1]
            local_label_to_fragment[label] = fragment
            if "-rend.xml" in href:
                local_label_is_rend.add(label)

    for arc in root.iter():
        if not isinstance(arc.tag, str):
            continue
        if arc.tag.split("}")[-1] != "arc":
            continue
        if arc.get(_XLINK_ARCROLE) != _ARCROLE_GROUP_TABLE:
            continue
        from_label = arc.get(_XLINK_FROM, "")
        to_label = arc.get(_XLINK_TO, "")
        from_frag = local_label_to_fragment.get(from_label, from_label)
        to_frag = local_label_to_fragment.get(to_label)
        if not to_frag:
            continue
        try:
            arc_order = float(arc.get("order", "1"))
        except ValueError:
            arc_order = 1.0
        group_table_children.setdefault(from_frag, []).append((arc_order, to_frag))
        if group_table_root_fragment is None and from_label not in local_label_is_rend:
            group_table_root_fragment = from_frag

    for link_el in root.iter(_PRES_LINK):
        elr = link_el.get(_XLINK_ROLE, "http://www.xbrl.org/2003/role/link")

        # Build locator map: xlink:label → QName
        loc_map: dict[str, QName] = {}
        for loc in link_el.iter(_LOC):
            href = loc.get(_XLINK_HREF, "")
            xlink_label = loc.get(_XLINK_LABEL, "")
            if "#" in href:
                fragment = href.rsplit("#", 1)[1]
                qname = concept_map.get(fragment)
                if qname:
                    loc_map[xlink_label] = qname

        network = networks.setdefault(elr, PresentationNetwork(extended_link_role=elr))

        for arc in link_el.iter(_PRES_ARC):
            arcrole = arc.get(_XLINK_ARCROLE, "")
            if arcrole != ARCROLE_PRESENTATION:
                continue
            frm = arc.get(_XLINK_FROM, "")
            to = arc.get(_XLINK_TO, "")
            parent = loc_map.get(frm)
            child = loc_map.get(to)
            if not parent or not child:
                continue
            try:
                order = float(arc.get("order", "1"))
            except ValueError:
                order = 1.0
            preferred_label = arc.get("preferredLabel")
            network.arcs.append(
                PresentationArc(
                    parent=parent,
                    child=child,
                    order=order,
                    extended_link_role=elr,
                    preferred_label=preferred_label,
                )
            )

    return PresentationLinkbaseParseResult(
        networks=networks,
        group_table_children=group_table_children,
        group_table_rend_fragments=set(local_label_to_fragment[label] for label in local_label_is_rend),
        group_table_root_fragment=group_table_root_fragment,
    )

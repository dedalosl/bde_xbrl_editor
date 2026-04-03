"""Presentation linkbase parser — builds PresentationNetwork objects per ELR."""

from __future__ import annotations

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


def parse_presentation_linkbase(
    linkbase_path: Path,
    concept_map: dict[str, QName],
) -> dict[str, PresentationNetwork]:
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

    return networks

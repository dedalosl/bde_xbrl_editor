"""Standard label linkbase parser.

Parses link:labelLink arcs producing Label objects with full priority and
@use='prohibited' arc algebra support.
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import (
    ARCROLE_LABEL,
    NS_LINK,
    NS_XLINK,
)
from bde_xbrl_editor.taxonomy.models import Label, QName, TaxonomyParseError

_LABEL_LINK = f"{{{NS_LINK}}}labelLink"
_LOC = f"{{{NS_LINK}}}loc"
_LABEL_ARC = f"{{{NS_LINK}}}labelArc"
_LABEL_EL = f"{{{NS_LINK}}}label"
_XLINK_HREF = f"{{{NS_XLINK}}}href"
_XLINK_LABEL = f"{{{NS_XLINK}}}label"
_XLINK_FROM = f"{{{NS_XLINK}}}from"
_XLINK_TO = f"{{{NS_XLINK}}}to"
_XLINK_ARCROLE = f"{{{NS_XLINK}}}arcrole"
_XLINK_ROLE = f"{{{NS_XLINK}}}role"


def _concept_qname_from_href(href: str) -> QName | None:
    """Extract concept QName from an XLink locator href like schema.xsd#concept_id."""
    if "#" not in href:
        return None
    base, fragment = href.rsplit("#", 1)
    # fragment is the @id attribute value — typically "prefix_localName" or just localName
    # We return a bare QName with no namespace (namespace is resolved later against schema)
    return QName(namespace="", local_name=fragment)


def parse_label_linkbase(
    linkbase_path: Path,
    concept_map: dict[str, QName],  # @id → QName (built from schema QNames)
) -> dict[QName, list[Label]]:
    """Parse a standard label linkbase file.

    Args:
        linkbase_path: Absolute path to the label linkbase XML file.
        concept_map: Maps XML id fragments (e.g. ``"bde_Assets"``) to
            their canonical QName.  Built by the loader from all parsed schemas.

    Returns:
        Dict mapping QName → list[Label] (all labels, all roles + languages).

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
    result: dict[QName, list[Label]] = {}

    for link_el in root.iter(_LABEL_LINK):
        # Step 1: build locator map (xlink:label → concept QName)
        loc_map: dict[str, QName] = {}
        for loc in link_el.iter(_LOC):
            href = loc.get(_XLINK_HREF, "")
            xlink_label = loc.get(_XLINK_LABEL, "")
            if "#" in href:
                fragment = href.rsplit("#", 1)[1]
                qname = concept_map.get(fragment)
                if qname:
                    loc_map[xlink_label] = qname

        # Step 2: build label element map (xlink:label → Label)
        label_map: dict[str, list[Label]] = {}
        for lab_el in link_el.iter(_LABEL_EL):
            xlink_label = lab_el.get(_XLINK_LABEL, "")
            role = lab_el.get(_XLINK_ROLE, "http://www.xbrl.org/2003/role/label")
            lang = lab_el.get("{http://www.w3.org/XML/1998/namespace}lang", "")
            text = (lab_el.text or "").strip()
            priority_str = lab_el.get("priority", "0")
            try:
                priority = int(priority_str)
            except ValueError:
                priority = 0
            label_map.setdefault(xlink_label, []).append(
                Label(text=text, language=lang, role=role, source="standard", priority=priority)
            )

        # Step 3: traverse arcs to build concept → labels mapping
        prohibited: set[tuple[str, str]] = set()  # (from_loc, to_label) pairs with use=prohibited
        arcs: list[tuple[str, str, int]] = []  # (from_loc, to_label, priority)

        for arc in link_el.iter(_LABEL_ARC):
            arcrole = arc.get(_XLINK_ARCROLE, "")
            if arcrole != ARCROLE_LABEL:
                continue
            frm = arc.get(_XLINK_FROM, "")
            to = arc.get(_XLINK_TO, "")
            use = arc.get("use", "optional")
            priority_str = arc.get("priority", "0")
            try:
                priority = int(priority_str)
            except ValueError:
                priority = 0

            if use == "prohibited":
                prohibited.add((frm, to))
            else:
                arcs.append((frm, to, priority))

        for frm, to, priority in arcs:
            if (frm, to) in prohibited:
                continue
            qname = loc_map.get(frm)
            if not qname:
                continue
            for label in label_map.get(to, []):
                # Override label priority from arc if higher
                effective_priority = max(label.priority, priority)
                final_label = Label(
                    text=label.text,
                    language=label.language,
                    role=label.role,
                    source="standard",
                    priority=effective_priority,
                )
                result.setdefault(qname, []).append(final_label)

    return result

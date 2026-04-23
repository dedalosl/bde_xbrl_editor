"""Generic label linkbase parser (XBRL 2.1 generic link spec).

Parses gen:link / gen:arc / genlab:label structures using the same priority
and @use='prohibited' arc algebra as standard labels.
"""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import (
    ARCROLE_ELEMENT_LABEL,
    NS_GEN,
    NS_GENLAB,
    NS_XLINK,
)
from bde_xbrl_editor.taxonomy.linkbases.label import _resolve_locator_href
from bde_xbrl_editor.taxonomy.models import Label, QName, TaxonomyParseError
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file

_GEN_LINK = f"{{{NS_GEN}}}link"
_GEN_ARC = f"{{{NS_GEN}}}arc"
_GENLAB_LABEL = f"{{{NS_GENLAB}}}label"
_XLINK_HREF = f"{{{NS_XLINK}}}href"
_XLINK_LABEL = f"{{{NS_XLINK}}}label"
_XLINK_FROM = f"{{{NS_XLINK}}}from"
_XLINK_TO = f"{{{NS_XLINK}}}to"
_XLINK_ARCROLE = f"{{{NS_XLINK}}}arcrole"
_XLINK_ROLE = f"{{{NS_XLINK}}}role"
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def parse_generic_label_linkbase(
    linkbase_path: Path,
    concept_map: dict[str, QName],
    *,
    ns_qualified_map: dict[str, QName] | None = None,
    schema_ns_map: dict[str, str] | None = None,
) -> dict[QName, list[Label]]:
    """Parse a generic label linkbase file.

    Args:
        linkbase_path: Absolute path to the generic label linkbase XML.
        concept_map: Maps XML id fragments to canonical QName (same as
            used by the standard label parser).

    Returns:
        Dict mapping QName → list[Label] with ``source="generic"``.

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
    result: dict[QName, list[Label]] = {}
    ns_qmap = ns_qualified_map or {}
    schema_map = schema_ns_map or {}

    for link_el in root.iter(_GEN_LINK):
        # Build locator map: xlink:label → QName
        loc_map: dict[str, QName] = {}
        for loc in link_el:
            href = loc.get(_XLINK_HREF, "")
            xlink_label = loc.get(_XLINK_LABEL, "")
            qname = _resolve_locator_href(
                href,
                linkbase_path,
                concept_map,
                ns_qmap,
                schema_map,
            )
            if qname:
                loc_map[xlink_label] = qname

        # Build label element map: xlink:label → Label list
        label_map: dict[str, list[Label]] = {}
        for lab_el in link_el.iter(_GENLAB_LABEL):
            xlink_label = lab_el.get(_XLINK_LABEL, "")
            role = lab_el.get(_XLINK_ROLE, "http://www.xbrl.org/2003/role/label")
            lang = lab_el.get(_XML_LANG, "")
            text = (lab_el.text or "").strip()
            try:
                priority = int(lab_el.get("priority", "0"))
            except ValueError:
                priority = 0
            label_map.setdefault(xlink_label, []).append(
                Label(text=text, language=lang, role=role, source="generic", priority=priority)
            )

        # Traverse arcs
        prohibited: set[tuple[str, str]] = set()
        arcs: list[tuple[str, str, int]] = []

        for arc in link_el.iter(_GEN_ARC):
            arcrole = arc.get(_XLINK_ARCROLE, "")
            if arcrole != ARCROLE_ELEMENT_LABEL:
                continue
            frm = arc.get(_XLINK_FROM, "")
            to = arc.get(_XLINK_TO, "")
            use = arc.get("use", "optional")
            try:
                priority = int(arc.get("priority", "0"))
            except ValueError:
                priority = 0
            if use == "prohibited":
                prohibited.add((frm, to))
            else:
                arcs.append((frm, to, priority))

        for frm, to, arc_priority in arcs:
            if (frm, to) in prohibited:
                continue
            qname = loc_map.get(frm)
            if not qname:
                continue
            for label in label_map.get(to, []):
                effective_priority = max(label.priority, arc_priority)
                final_label = Label(
                    text=label.text,
                    language=label.language,
                    role=label.role,
                    source="generic",
                    priority=effective_priority,
                )
                result.setdefault(qname, []).append(final_label)

    return result

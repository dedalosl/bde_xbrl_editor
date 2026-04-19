"""Parse label and message resources attached to formula assertions."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import (
    ARCROLE_ASSERTION_SATISFIED_MESSAGE,
    ARCROLE_ASSERTION_UNSATISFIED_MESSAGE,
    ARCROLE_ELEMENT_LABEL,
    NS_GEN,
    NS_GENLAB,
    NS_MSG,
    NS_XLINK,
)
from bde_xbrl_editor.taxonomy.models import AssertionTextResource
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file

_GEN_LINK = f"{{{NS_GEN}}}link"
_GEN_ARC = f"{{{NS_GEN}}}arc"
_GENLAB_LABEL = f"{{{NS_GENLAB}}}label"
_MESSAGE = f"{{{NS_MSG}}}message"

_XLINK_HREF = f"{{{NS_XLINK}}}href"
_XLINK_LABEL = f"{{{NS_XLINK}}}label"
_XLINK_FROM = f"{{{NS_XLINK}}}from"
_XLINK_TO = f"{{{NS_XLINK}}}to"
_XLINK_ARCROLE = f"{{{NS_XLINK}}}arcrole"
_XLINK_ROLE = f"{{{NS_XLINK}}}role"
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"

_SUPPORTED_ARCROLES = frozenset({
    ARCROLE_ELEMENT_LABEL,
    ARCROLE_ASSERTION_UNSATISFIED_MESSAGE,
    ARCROLE_ASSERTION_SATISFIED_MESSAGE,
})


def parse_assertion_resource_linkbase(
    linkbase_path: Path,
) -> dict[str, list[AssertionTextResource]]:
    """Return assertion-id -> attached label/message resources.

    Detection is structural: locator/arc/resource relationships are resolved
    through XLink arcroles and resource roles, not from file names.
    """
    if not linkbase_path.exists():
        return {}

    try:
        tree = parse_xml_file(linkbase_path)
    except etree.XMLSyntaxError:
        return {}

    root = tree.getroot()
    result: dict[str, list[AssertionTextResource]] = {}

    for link_el in root.iter(_GEN_LINK):
        loc_map: dict[str, str] = {}
        for loc in link_el:
            href = (loc.get(_XLINK_HREF) or "").strip()
            xlink_label = (loc.get(_XLINK_LABEL) or "").strip()
            if not href or not xlink_label or "#" not in href:
                continue
            fragment = href.split("#", 1)[1].strip()
            if fragment:
                loc_map[xlink_label] = fragment

        resource_map: dict[str, list[AssertionTextResource]] = {}
        for resource_el in link_el.iter():
            if resource_el.tag not in (_GENLAB_LABEL, _MESSAGE):
                continue
            xlink_label = (resource_el.get(_XLINK_LABEL) or "").strip()
            if not xlink_label:
                continue
            text = "".join(resource_el.itertext()).strip()
            if not text:
                continue
            try:
                priority = int(resource_el.get("priority", "0"))
            except ValueError:
                priority = 0
            resource_map.setdefault(xlink_label, []).append(
                AssertionTextResource(
                    text=text,
                    language=(resource_el.get(_XML_LANG) or "").strip(),
                    role=(
                        resource_el.get(_XLINK_ROLE)
                        or ""
                    ).strip(),
                    arcrole="",
                    priority=priority,
                )
            )

        for arc in link_el.iter(_GEN_ARC):
            arcrole = (arc.get(_XLINK_ARCROLE) or "").strip()
            if arcrole not in _SUPPORTED_ARCROLES:
                continue
            frm = (arc.get(_XLINK_FROM) or "").strip()
            to = (arc.get(_XLINK_TO) or "").strip()
            assertion_id = loc_map.get(frm)
            if assertion_id is None:
                continue
            for resource in resource_map.get(to, []):
                result.setdefault(assertion_id, []).append(
                    AssertionTextResource(
                        text=resource.text,
                        language=resource.language,
                        role=resource.role,
                        arcrole=arcrole,
                        priority=resource.priority,
                    )
                )

    return result

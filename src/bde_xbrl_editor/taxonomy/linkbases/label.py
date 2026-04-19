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
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file

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

def _resolve_locator_href(
    href: str,
    linkbase_path: Path,
    concept_map: dict[str, QName],
    ns_qualified_map: dict[str, QName],
    schema_ns_map: dict[str, str],
) -> QName | None:
    """Resolve a label locator href to a QName.

    Fragment-only hrefs such as "#concept_id" still fall back to ``concept_map``.
    When the href explicitly names a schema document, require namespace-qualified
    resolution so duplicate xml:id values across different namespaces cannot steal
    each other's labels.
    """
    if "#" not in href:
        return None
    schema_url, fragment = href.rsplit("#", 1)
    if not fragment:
        return None

    ns: str | None = None
    if schema_url.startswith("http://") or schema_url.startswith("https://"):
        ns = schema_ns_map.get(schema_url)
    elif schema_url:
        try:
            ns = schema_ns_map.get(str((linkbase_path.parent / schema_url).resolve()))
        except Exception:  # noqa: BLE001
            ns = None

    if ns:
        qname = ns_qualified_map.get(f"{ns}#{fragment}")
        if qname:
            return qname

    if schema_url:
        return None

    return concept_map.get(fragment)


def parse_label_linkbase(
    linkbase_path: Path,
    concept_map: dict[str, QName],  # @id → QName (built from schema QNames)
    *,
    ns_qualified_map: dict[str, QName] | None = None,
    schema_ns_map: dict[str, str] | None = None,
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

    for link_el in root.iter(_LABEL_LINK):
        # Step 1: build locator map (xlink:label → concept QName)
        loc_map: dict[str, QName] = {}
        for loc in link_el.iter(_LOC):
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

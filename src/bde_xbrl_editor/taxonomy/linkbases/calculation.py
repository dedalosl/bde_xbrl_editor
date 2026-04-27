"""Calculation linkbase parser — builds CalculationArc lists per ELR."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import unquote

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import ARCROLE_CALCULATION, NS_LINK, NS_XLINK
from bde_xbrl_editor.taxonomy.models import CalculationArc, QName, TaxonomyParseError
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file

_CALC_LINK = f"{{{NS_LINK}}}calculationLink"
_LOC = f"{{{NS_LINK}}}loc"
_CALC_ARC = f"{{{NS_LINK}}}calculationArc"
_XLINK_HREF = f"{{{NS_XLINK}}}href"
_XLINK_LABEL = f"{{{NS_XLINK}}}label"
_XLINK_FROM = f"{{{NS_XLINK}}}from"
_XLINK_TO = f"{{{NS_XLINK}}}to"
_XLINK_ARCROLE = f"{{{NS_XLINK}}}arcrole"
_XLINK_ROLE = f"{{{NS_XLINK}}}role"
_XLINK_TYPE = f"{{{NS_XLINK}}}type"
_XLINK_TITLE = f"{{{NS_XLINK}}}title"

_RELATIONSHIP_EQUIVALENCE_EXCLUDED_ATTRS = frozenset(
    {
        _XLINK_TYPE,
        _XLINK_TITLE,
        "use",
        "priority",
    }
)


def _normalise_equivalence_value(raw: str) -> tuple[str, str]:
    s = raw.strip()
    low = s.lower()
    if low == "true":
        return ("dec", "1")
    if low == "false":
        return ("dec", "0")
    try:
        d = Decimal(s)
        if d.is_nan():
            return ("nan", s)
        if d.is_zero():
            return ("dec", "0")
        return ("dec", format(d.normalize(), "f"))
    except InvalidOperation:
        return ("str", s)


def _relationship_equivalence_key(arc: etree._Element) -> tuple:
    attrs = []
    for name in sorted(arc.attrib):
        if name in _RELATIONSHIP_EQUIVALENCE_EXCLUDED_ATTRS:
            continue
        attrs.append((name, _normalise_equivalence_value(arc.attrib[name])))
    return tuple(attrs)


def parse_calculation_linkbase(
    linkbase_path: Path,
    concept_map: dict[str, QName],
) -> dict[str, list[CalculationArc]]:
    """Parse a calculation linkbase and return CalculationArcs grouped by ELR.

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
    result: dict[str, list[CalculationArc]] = {}

    for link_el in root.iter(_CALC_LINK):
        elr = link_el.get(_XLINK_ROLE, "http://www.xbrl.org/2003/role/link")

        loc_map: dict[str, QName] = {}
        for loc in link_el.iter(_LOC):
            href = loc.get(_XLINK_HREF, "")
            xlink_label = loc.get(_XLINK_LABEL, "")
            if "#" in href:
                fragment = unquote(href.rsplit("#", 1)[1])
                qname = concept_map.get(fragment)
                if qname:
                    loc_map[xlink_label] = qname

        for arc in link_el.iter(_CALC_ARC):
            arcrole = arc.get(_XLINK_ARCROLE, "")
            if arcrole != ARCROLE_CALCULATION:
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
            try:
                weight = float(arc.get("weight", "1"))
            except ValueError:
                weight = 1.0
            use = arc.get("use", "optional")
            result.setdefault(elr, []).append(
                CalculationArc(
                    parent=parent,
                    child=child,
                    order=order,
                    weight=weight,
                    extended_link_role=elr,
                    use=use,
                    equivalence_key=_relationship_equivalence_key(arc),
                )
            )

    return result

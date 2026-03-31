"""XML Schema parser — extracts Concept objects from XSD element declarations."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import NS_XBRLI, NS_XSD, NS_XBRLDT
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    QName,
    TaxonomyParseError,
)

_ELEMENT = f"{{{NS_XSD}}}element"
_COMPLEX_TYPE = f"{{{NS_XSD}}}complexType"

# XBRL substitution groups that mark items and tuples
_SG_ITEM = QName(NS_XBRLI, "item", prefix="xbrli")
_SG_TUPLE = QName(NS_XBRLI, "tuple", prefix="xbrli")

# Mapping from XSD built-in / XBRL type local names to canonical QNames
_XBRLI_NS = NS_XBRLI
_XBRLI_TYPES = {
    "monetaryItemType", "decimalItemType", "floatItemType", "doubleItemType",
    "integerItemType", "nonNegativeIntegerItemType", "positiveIntegerItemType",
    "nonPositiveIntegerItemType", "negativeIntegerItemType",
    "longItemType", "intItemType", "shortItemType", "byteItemType",
    "unsignedLongItemType", "unsignedIntItemType", "unsignedShortItemType",
    "unsignedByteItemType", "stringItemType", "booleanItemType",
    "hexBinaryItemType", "base64BinaryItemType", "anyURIItemType",
    "QNameItemType", "durationItemType", "dateTimeItemType", "timeItemType",
    "dateItemType", "gYearMonthItemType", "gYearItemType",
    "gMonthDayItemType", "gDayItemType", "gMonthItemType",
    "normalizedStringItemType", "tokenItemType", "languageItemType",
    "NameItemType", "NCNameItemType", "sharesItemType", "pureItemType",
    "fractionItemType", "nonNumericItemType", "numericItemType",
}


def _resolve_qname(raw: str | None, ns_map: dict[str, str], file_path: str) -> QName | None:
    """Resolve a prefixed or Clark-notation type name to a QName."""
    if not raw:
        return None
    if raw.startswith("{"):
        return QName.from_clark(raw)
    if ":" in raw:
        prefix, local = raw.split(":", 1)
        ns = ns_map.get(prefix, "")
        return QName(namespace=ns, local_name=local, prefix=prefix)
    # No prefix — might be built-in XSD type
    return QName(namespace=NS_XSD, local_name=raw)


def parse_schema(schema_path: Path) -> dict[QName, Concept]:
    """Parse a single XSD file and return all XBRL item/tuple Concept objects.

    Args:
        schema_path: Absolute path to the .xsd file.

    Returns:
        Dict mapping QName → Concept for all declared elements that are
        XBRL items or tuples (have xbrli:item/xbrli:tuple substitutionGroup).

    Raises:
        TaxonomyParseError: If the file is not well-formed XML.
    """
    try:
        tree = etree.parse(str(schema_path))  # noqa: S320
    except etree.XMLSyntaxError as exc:
        raise TaxonomyParseError(
            file_path=str(schema_path),
            message=str(exc),
            line=exc.lineno,
            column=exc.offset,
        ) from exc

    root = tree.getroot()
    target_ns = root.get("targetNamespace", "")
    ns_map: dict[str, str] = {k or "": v for k, v in root.nsmap.items()}

    concepts: dict[QName, Concept] = {}

    for el in root.iter(_ELEMENT):
        name = el.get("name")
        if not name:
            continue

        # Determine substitution group
        sg_raw = el.get("substitutionGroup")
        sg = _resolve_qname(sg_raw, ns_map, str(schema_path))

        # Only collect XBRL items, tuples, and dimensional concepts.
        # xbrldt:hypercubeItem and xbrldt:dimensionItem extend xbrli:item
        # transitively, so taxonomies that declare only dimensional concepts
        # (no regular items) are still valid XBRL taxonomies.
        if sg is None:
            continue
        is_xbrli_direct = sg.namespace == NS_XBRLI and sg.local_name in ("item", "tuple")
        is_dimensional = sg.namespace == NS_XBRLDT and sg.local_name in (
            "hypercubeItem", "dimensionItem"
        )
        if not is_xbrli_direct and not is_dimensional:
            continue

        qname = QName(namespace=target_ns, local_name=name)

        # Data type
        type_raw = el.get("type")
        if type_raw:
            data_type = _resolve_qname(type_raw, ns_map, str(schema_path)) or QName(NS_XSD, "anyType")
        else:
            data_type = QName(NS_XSD, "anyType")

        # Period type (xbrli:periodType attribute)
        period_raw = el.get(f"{{{NS_XBRLI}}}periodType", "duration")
        period_type = "instant" if period_raw == "instant" else "duration"

        # Balance
        balance_raw = el.get(f"{{{NS_XBRLI}}}balance")
        balance = balance_raw if balance_raw in ("debit", "credit") else None

        # Abstract / nillable
        abstract = el.get("abstract", "false").lower() == "true"
        nillable = el.get("nillable", "false").lower() == "true"

        # id attribute (used as XLink href fragment in linkbases)
        xml_id = el.get("id") or None

        concepts[qname] = Concept(
            qname=qname,
            data_type=data_type,
            period_type=period_type,
            balance=balance,
            abstract=abstract,
            nillable=nillable,
            substitution_group=sg,
            xml_id=xml_id,
        )

    return concepts

"""XML Schema parser — extracts Concept objects from XSD element declarations."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import NS_XBRLDT, NS_XBRLI, NS_XSD
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

# Root SG QNames that definitively make an element an XBRL concept
XBRL_SG_ROOTS: frozenset[QName] = frozenset({
    QName(NS_XBRLI, "item"),
    QName(NS_XBRLI, "tuple"),
    QName(NS_XBRLDT, "hypercubeItem"),
    QName(NS_XBRLDT, "dimensionItem"),
})

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


def _build_concept(
    el: etree._Element,
    target_ns: str,
    ns_map: dict[str, str],
    schema_path_str: str,
) -> tuple[QName, Concept, QName] | None:
    """Build a (qname, concept, sg_qname) triple from an xs:element node.

    Returns None if the element has no name or no substitutionGroup.
    """
    name = el.get("name")
    if not name:
        return None
    sg_raw = el.get("substitutionGroup")
    sg = _resolve_qname(sg_raw, ns_map, schema_path_str)
    if sg is None:
        return None

    qname = QName(namespace=target_ns, local_name=name)

    type_raw = el.get("type")
    if type_raw:
        data_type = _resolve_qname(type_raw, ns_map, schema_path_str) or QName(NS_XSD, "anyType")
    else:
        data_type = QName(NS_XSD, "anyType")

    period_raw = el.get(f"{{{NS_XBRLI}}}periodType", "duration")
    period_type = "instant" if period_raw == "instant" else "duration"

    balance_raw = el.get(f"{{{NS_XBRLI}}}balance")
    balance = balance_raw if balance_raw in ("debit", "credit") else None

    abstract = el.get("abstract", "false").lower() == "true"
    nillable = el.get("nillable", "false").lower() == "true"
    xml_id = el.get("id") or None

    concept = Concept(
        qname=qname,
        data_type=data_type,
        period_type=period_type,
        balance=balance,
        abstract=abstract,
        nillable=nillable,
        substitution_group=sg,
        xml_id=xml_id,
    )
    return qname, concept, sg


def parse_schema_raw(
    schema_path: Path,
    namespace_override: str | None = None,
) -> tuple[dict[QName, tuple[Concept, QName]], str]:
    """Parse a single XSD and return ALL xs:element declarations that have a
    substitutionGroup, regardless of whether that SG is a known XBRL root.

    Returns:
        Tuple of (candidates, target_ns) where:
        - candidates: Dict mapping QName → (Concept, sg_qname).  The sg_qname is
          the raw substitutionGroup value and may point to a concept in another schema.
        - target_ns: The targetNamespace declared by this schema file.

    Use this when you need the full candidate set for cross-schema transitive
    closure (see TaxonomyLoader._do_load).

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
    # namespace_override is supplied for xs:include'd schemas that lack their
    # own targetNamespace but inherit it from the including schema.
    target_ns = namespace_override if namespace_override is not None else root.get("targetNamespace", "")
    ns_map: dict[str, str] = {k or "": v for k, v in root.nsmap.items()}

    candidates: dict[QName, tuple[Concept, QName]] = {}
    for el in root.iter(_ELEMENT):
        result = _build_concept(el, target_ns, ns_map, str(schema_path))
        if result is not None:
            qname, concept, sg = result
            candidates[qname] = (concept, sg)
    return candidates, target_ns


def parse_schema(
    schema_path: Path,
    namespace_override: str | None = None,
) -> dict[QName, Concept]:
    """Parse a single XSD file and return all XBRL item/tuple Concept objects.

    Performs within-file transitive substitution group resolution: a concept
    whose substitutionGroup points to another concept in the same file (which
    itself substitutes for xbrli:item etc.) is included correctly.

    For cross-schema transitive chains use parse_schema_raw + the transitive
    closure logic in TaxonomyLoader.

    Args:
        schema_path: Absolute path to the .xsd file.
        namespace_override: If set, use this as targetNamespace instead of
            the value in the file (needed for xs:include'd schemas that have
            no targetNamespace of their own).

    Returns:
        Dict mapping QName → Concept for all XBRL items/tuples/dimensions.

    Raises:
        TaxonomyParseError: If the file is not well-formed XML.
    """
    raw, _target_ns = parse_schema_raw(schema_path, namespace_override)

    # Phase 1: accept concepts whose SG is a known XBRL root
    resolved: dict[QName, Concept] = {
        qn: c for qn, (c, sg) in raw.items() if sg in XBRL_SG_ROOTS
    }

    # Phase 2: within-file transitive closure
    pending = [(qn, c, sg) for qn, (c, sg) in raw.items() if sg not in XBRL_SG_ROOTS]
    prev = -1
    while prev != len(resolved):
        prev = len(resolved)
        still_pending = []
        for qn, c, sg in pending:
            if sg in resolved:
                resolved[qn] = c
            else:
                still_pending.append((qn, c, sg))
        pending = still_pending

    return resolved

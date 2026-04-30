"""XML Schema parser — extracts Concept objects from XSD element declarations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import (
    NS_EXTENSIBLE_ENUM,
    NS_EXTENSIBLE_ENUM_2,
    NS_XBRLDT,
    NS_XBRLI,
    NS_XLINK,
    NS_XSD,
)
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    QName,
    TaxonomyParseError,
)
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file

_ELEMENT = f"{{{NS_XSD}}}element"
_ATTRIBUTE = f"{{{NS_XSD}}}attribute"
_SIMPLE_TYPE = f"{{{NS_XSD}}}simpleType"
_COMPLEX_TYPE = f"{{{NS_XSD}}}complexType"
_SIMPLE_CONTENT = f"{{{NS_XSD}}}simpleContent"
_COMPLEX_CONTENT = f"{{{NS_XSD}}}complexContent"
_RESTRICTION = f"{{{NS_XSD}}}restriction"
_EXTENSION = f"{{{NS_XSD}}}extension"
_SEQUENCE = f"{{{NS_XSD}}}sequence"
_ENUMERATION = f"{{{NS_XSD}}}enumeration"
_UNION = f"{{{NS_XSD}}}union"

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
    typed_domain_ref = el.get(f"{{{NS_XBRLDT}}}typedDomainRef") or None

    enum_domain_raw = el.get(f"{{{NS_EXTENSIBLE_ENUM_2}}}domain") or el.get(
        f"{{{NS_EXTENSIBLE_ENUM}}}domain"
    )
    enum_linkrole = el.get(f"{{{NS_EXTENSIBLE_ENUM_2}}}linkrole") or el.get(
        f"{{{NS_EXTENSIBLE_ENUM}}}linkrole"
    )
    enum_head_raw = el.get(f"{{{NS_EXTENSIBLE_ENUM_2}}}headUsable") or el.get(
        f"{{{NS_EXTENSIBLE_ENUM}}}headUsable"
    )
    enumeration_domain = (
        _resolve_qname(enum_domain_raw, ns_map, schema_path_str) if enum_domain_raw else None
    )
    if enum_domain_raw and enumeration_domain is None:
        enum_linkrole = None
    enumeration_head_usable = (
        enum_head_raw is not None and str(enum_head_raw).strip().lower() in ("true", "1", "yes")
    )

    concept = Concept(
        qname=qname,
        data_type=data_type,
        period_type=period_type,
        balance=balance,
        abstract=abstract,
        nillable=nillable,
        substitution_group=sg,
        xml_id=xml_id,
        typed_domain_ref=typed_domain_ref,
        schema_path=schema_path_str,
        enumeration_domain=enumeration_domain,
        enumeration_linkrole=enum_linkrole if enum_linkrole else None,
        enumeration_head_usable=enumeration_head_usable,
    )
    return qname, concept, sg


def _schema_constraint_error(
    schema_path_str: str,
    message: str,
    el: etree._Element | None = None,
) -> TaxonomyParseError:
    return TaxonomyParseError(
        file_path=schema_path_str,
        message=f"xbrl:schema-validation-error: {message}",
        line=el.sourceline if el is not None else None,
    )


def _is_true(raw: str | None) -> bool:
    return (raw or "").strip().lower() in {"true", "1"}


def _validate_xbrl_item_and_tuple_constraints(
    root: etree._Element,
    ns_map: dict[str, str],
    schema_path_str: str,
) -> None:
    """Validate XBRL 2.1 schema constraints for directly declared items/tuples."""
    for el in root.iter(_ELEMENT):
        if el.getparent() is not root:
            continue

        name = el.get("name", "<anonymous>")
        sg = _resolve_qname(el.get("substitutionGroup"), ns_map, schema_path_str)
        has_period_type = el.get(f"{{{NS_XBRLI}}}periodType") is not None

        if sg == _SG_ITEM:
            if not has_period_type:
                raise _schema_constraint_error(
                    schema_path_str,
                    f"Item '{name}' is missing required xbrli:periodType",
                    el,
                )
            continue

        if sg != _SG_TUPLE:
            continue

        if has_period_type:
            raise _schema_constraint_error(
                schema_path_str,
                f"Tuple '{name}' must not declare xbrli:periodType",
                el,
            )

        complex_type = next((child for child in el if child.tag == _COMPLEX_TYPE), None)
        if complex_type is None:
            continue

        if _is_true(complex_type.get("mixed")):
            raise _schema_constraint_error(
                schema_path_str,
                f"Tuple '{name}' must not declare mixed content",
                complex_type,
            )

        for complex_content in complex_type.iter(_COMPLEX_CONTENT):
            if _is_true(complex_content.get("mixed")):
                raise _schema_constraint_error(
                    schema_path_str,
                    f"Tuple '{name}' must not declare mixed content",
                    complex_content,
                )

        for attr_el in complex_type.iter(_ATTRIBUTE):
            attr_ref = _resolve_qname(attr_el.get("ref"), ns_map, schema_path_str)
            if attr_ref is not None and attr_ref.namespace in {NS_XBRLI, NS_XLINK}:
                raise _schema_constraint_error(
                    schema_path_str,
                    f"Tuple '{name}' must not allow attribute '{attr_ref}'",
                    attr_el,
                )

        for sequence_el in complex_type.iter(_SEQUENCE):
            for child_el in sequence_el:
                if child_el.tag != _ELEMENT:
                    continue
                if _resolve_qname(child_el.get("ref"), ns_map, schema_path_str) is None:
                    raise _schema_constraint_error(
                        schema_path_str,
                        f"Tuple '{name}' child declarations must reference global item "
                        "or tuple elements",
                        child_el,
                    )


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
        tree = parse_xml_file(schema_path)
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
    _validate_xbrl_item_and_tuple_constraints(root, ns_map, str(schema_path))

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

    registry = build_global_named_type_registry(
        [schema_path],
        {schema_path: namespace_override} if namespace_override is not None else {},
    )
    enums = extract_concept_enumerations_for_schema(schema_path, namespace_override, registry)
    return {
        qn: replace(c, enumeration_values=enums.get(qn, ())) for qn, c in resolved.items()
    }


_MONETARY_ITEM_TYPE = QName(NS_XBRLI, "monetaryItemType")


def _type_def_bases_monetary(
    type_el: etree._Element,
    ns_map: dict[str, str],
    schema_path_str: str,
) -> bool:
    """True when *type_el* (xs:simpleType or xs:complexType) derives from monetaryItemType."""
    for child in type_el:
        if child.tag == _RESTRICTION:
            base_raw = child.get("base")
            if base_raw:
                base_qn = _resolve_qname(base_raw, ns_map, schema_path_str)
                if base_qn == _MONETARY_ITEM_TYPE:
                    return True
        elif child.tag == _SIMPLE_CONTENT:
            for sc_child in child:
                if sc_child.tag != _RESTRICTION:
                    continue
                base_raw = sc_child.get("base")
                if base_raw:
                    base_qn = _resolve_qname(base_raw, ns_map, schema_path_str)
                    if base_qn == _MONETARY_ITEM_TYPE:
                        return True
        elif child.tag == _EXTENSION:
            base_raw = child.get("base")
            if base_raw:
                base_qn = _resolve_qname(base_raw, ns_map, schema_path_str)
                if base_qn == _MONETARY_ITEM_TYPE:
                    return True
    return False


def extract_monetary_value_type_qnames(
    schema_path: Path,
    namespace_override: str | None = None,
) -> frozenset[QName]:
    """Return QNames of XSD types (in *targetNamespace*) that derive from monetaryItemType.

    Covers xs:simpleType restrictions and xs:complexType/xs:simpleContent restrictions
    as used by XBRL 2.1 conformance (e.g. ``assetsItemType`` in 304-03).
    """
    try:
        tree = parse_xml_file(schema_path)
    except etree.XMLSyntaxError as exc:
        raise TaxonomyParseError(
            file_path=str(schema_path),
            message=str(exc),
            line=exc.lineno,
            column=exc.offset,
        ) from exc

    root = tree.getroot()
    target_ns = (
        namespace_override if namespace_override is not None else root.get("targetNamespace", "")
    )
    ns_map: dict[str, str] = {k or "": v for k, v in root.nsmap.items()}

    out: set[QName] = set()
    path_str = str(schema_path)
    for el in root.iter(_SIMPLE_TYPE):
        name = el.get("name")
        if not name or not target_ns:
            continue
        if _type_def_bases_monetary(el, ns_map, path_str):
            out.add(QName(namespace=target_ns, local_name=name))

    for el in root.iter(_COMPLEX_TYPE):
        name = el.get("name")
        if not name or not target_ns:
            continue
        if _type_def_bases_monetary(el, ns_map, path_str):
            out.add(QName(namespace=target_ns, local_name=name))

    return frozenset(out)


# ---------------------------------------------------------------------------
# XSD enumeration facets on item types (QNameItemType, string item types, …)
# ---------------------------------------------------------------------------

_ENUM_BASE_TYPES: frozenset[QName] = frozenset(
    {
        QName(NS_XBRLI, "QNameItemType"),
        QName(NS_XBRLI, "stringItemType"),
        QName(NS_XBRLI, "tokenItemType"),
        QName(NS_XBRLI, "normalizedStringItemType"),
        QName(NS_XSD, "string"),
        QName(NS_XSD, "token"),
        QName(NS_XSD, "normalizedString"),
        QName(NS_XSD, "QName"),
    }
)


@dataclass(frozen=True)
class _NamedXsdType:
    """Named xs:simpleType or xs:complexType (simpleContent) usable as an element @type."""

    target_ns: str
    ns_map: dict[str, str]
    schema_path_str: str
    kind: Literal["simple", "complex_simple"]
    element: etree._Element


def _restriction_enumeration_lexicals(restriction_el: etree._Element) -> list[str]:
    return [
        str(v)
        for v in (child.get("value") for child in restriction_el if child.tag == _ENUMERATION)
        if v
    ]


def _enums_from_restriction(
    restriction_el: etree._Element,
    ns_map: dict[str, str],
    schema_path_str: str,
    registry: dict[QName, _NamedXsdType],
    visited: frozenset[QName],
) -> tuple[str, ...] | None:
    base_raw = restriction_el.get("base")
    if not base_raw:
        return None
    base_qn = _resolve_qname(base_raw, ns_map, schema_path_str)
    if base_qn is None:
        return None
    local_vals = _restriction_enumeration_lexicals(restriction_el)

    if base_qn in _ENUM_BASE_TYPES:
        return tuple(local_vals) if local_vals else None

    if base_qn in visited:
        return None
    if base_qn in registry:
        visited_next = visited | {base_qn}
        parent = _enums_for_named_type(registry[base_qn], registry, visited_next)
        if local_vals:
            if parent:
                allowed = set(parent)
                narrowed = tuple(v for v in local_vals if v in allowed)
                return narrowed or None
            return tuple(local_vals)
        return parent
    return None


def _enums_from_simple_type_el(
    st_el: etree._Element,
    ns_map: dict[str, str],
    schema_path_str: str,
    registry: dict[QName, _NamedXsdType],
    visited: frozenset[QName],
) -> tuple[str, ...] | None:
    for child in st_el:
        if child.tag == _RESTRICTION:
            return _enums_from_restriction(child, ns_map, schema_path_str, registry, visited)
        if child.tag == _UNION:
            return _enums_from_union(child, ns_map, schema_path_str, registry, visited)
    return None


def _enums_from_union(
    union_el: etree._Element,
    ns_map: dict[str, str],
    schema_path_str: str,
    registry: dict[QName, _NamedXsdType],
    visited: frozenset[QName],
) -> tuple[str, ...] | None:
    members_raw = union_el.get("memberTypes")
    merged: list[str] = []
    if members_raw:
        for token in members_raw.split():
            tq = _resolve_qname(token, ns_map, schema_path_str)
            if tq is None:
                continue
            if tq in registry:
                part = _enums_for_named_type(registry[tq], registry, visited)
                if part:
                    merged.extend(part)
    else:
        for child in union_el:
            if child.tag == _SIMPLE_TYPE:
                part = _enums_from_simple_type_el(child, ns_map, schema_path_str, registry, visited)
                if part:
                    merged.extend(part)
    if not merged:
        return None
    return tuple(dict.fromkeys(merged))


def _enums_for_named_type(
    named: _NamedXsdType,
    registry: dict[QName, _NamedXsdType],
    visited: frozenset[QName],
) -> tuple[str, ...] | None:
    if named.kind == "simple":
        return _enums_from_simple_type_el(
            named.element, named.ns_map, named.schema_path_str, registry, visited
        )
    ct = named.element
    sc = next((c for c in ct if c.tag == _SIMPLE_CONTENT), None)
    if sc is None:
        return None
    restriction = next((c for c in sc if c.tag == _RESTRICTION), None)
    if restriction is None:
        return None
    return _enums_from_restriction(
        restriction, named.ns_map, named.schema_path_str, registry, visited
    )


def _element_enumeration_display_values(
    el: etree._Element,
    ns_map: dict[str, str],
    schema_path_str: str,
    registry: dict[QName, _NamedXsdType],
) -> tuple[str, ...] | None:
    type_raw = el.get("type")
    if type_raw:
        tq = _resolve_qname(type_raw, ns_map, schema_path_str)
        if tq is not None and tq in registry:
            return _enums_for_named_type(registry[tq], registry, frozenset())
        return None
    for child in el:
        if child.tag == _SIMPLE_TYPE:
            return _enums_from_simple_type_el(child, ns_map, schema_path_str, registry, frozenset())
        if child.tag == _COMPLEX_TYPE:
            for cc in child:
                if cc.tag != _SIMPLE_CONTENT:
                    continue
                for r in cc:
                    if r.tag == _RESTRICTION:
                        return _enums_from_restriction(r, ns_map, schema_path_str, registry, frozenset())
    return None


def build_global_named_type_registry(
    schema_paths: list[Path],
    include_ns_map: Mapping[Path, str | None],
) -> dict[QName, _NamedXsdType]:
    """Index named XSD types across the DTS for cross-schema @type resolution."""
    registry: dict[QName, _NamedXsdType] = {}
    for schema_path in schema_paths:
        try:
            tree = parse_xml_file(schema_path)
        except etree.XMLSyntaxError:
            continue
        root = tree.getroot()
        override = include_ns_map.get(schema_path)
        target_ns = override if override is not None else root.get("targetNamespace", "")
        ns_map: dict[str, str] = {k or "": v for k, v in root.nsmap.items()}
        path_str = str(schema_path)
        for el in root.iter(_SIMPLE_TYPE):
            name = el.get("name")
            if name and target_ns:
                qn = QName(namespace=target_ns, local_name=name)
                registry[qn] = _NamedXsdType(target_ns, ns_map, path_str, "simple", el)
        for el in root.iter(_COMPLEX_TYPE):
            name = el.get("name")
            if not name or not target_ns:
                continue
            sc = next((c for c in el if c.tag == _SIMPLE_CONTENT), None)
            if sc is None:
                continue
            if next((c for c in sc if c.tag == _RESTRICTION), None) is None:
                continue
            qn = QName(namespace=target_ns, local_name=name)
            registry[qn] = _NamedXsdType(target_ns, ns_map, path_str, "complex_simple", el)
    return registry


def extract_concept_enumerations_for_schema(
    schema_path: Path,
    namespace_override: str | None,
    registry: dict[QName, _NamedXsdType],
) -> dict[QName, tuple[str, ...]]:
    """Map concept QName → enumeration lexical values declared for that element's type."""
    try:
        tree = parse_xml_file(schema_path)
    except etree.XMLSyntaxError:
        return {}

    root = tree.getroot()
    target_ns = namespace_override if namespace_override is not None else root.get("targetNamespace", "")
    ns_map: dict[str, str] = {k or "": v for k, v in root.nsmap.items()}
    path_str = str(schema_path)
    out: dict[QName, tuple[str, ...]] = {}
    for el in root.iter(_ELEMENT):
        if not el.get("substitutionGroup"):
            continue
        name = el.get("name")
        if not name or not target_ns:
            continue
        vals = _element_enumeration_display_values(el, ns_map, path_str, registry)
        if vals:
            out[QName(namespace=target_ns, local_name=name)] = vals
    return out

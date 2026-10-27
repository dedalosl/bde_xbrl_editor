"""Pure type classification from expanded QNames and already-discovered ancestry."""

from __future__ import annotations

from bde_xbrl_editor.taxonomy.models import Concept, QName

_XBRLI = "http://www.xbrl.org/2003/instance"
_XSD = "http://www.w3.org/2001/XMLSchema"
_INTEGER_NAMES = (
    "integer",
    "nonPositiveInteger",
    "negativeInteger",
    "long",
    "int",
    "short",
    "byte",
    "nonNegativeInteger",
    "unsignedLong",
    "unsignedInt",
    "unsignedShort",
    "unsignedByte",
    "positiveInteger",
)
_CATEGORIES = {QName(_XSD, name): "integer" for name in _INTEGER_NAMES}
_CATEGORIES.update({QName(_XBRLI, name + "ItemType"): "integer" for name in _INTEGER_NAMES})
for _name, _category in (
    ("decimal", "decimal"),
    ("float", "float"),
    ("double", "double"),
    ("boolean", "boolean"),
    ("date", "date"),
    ("dateTime", "dateTime"),
    ("QName", "qname"),
):
    _CATEGORIES[QName(_XSD, _name)] = _category
    _CATEGORIES[QName(_XBRLI, _name + "ItemType")] = _category
for _name in (
    "string",
    "normalizedString",
    "token",
    "language",
    "Name",
    "NCName",
    "NMTOKEN",
    "ID",
    "IDREF",
    "ENTITY",
    "anyURI",
):
    _CATEGORIES[QName(_XSD, _name)] = "string"
    _CATEGORIES[QName(_XBRLI, _name + "ItemType")] = "string"
for _name in ("shares", "pure"):
    _CATEGORIES[QName(_XBRLI, _name)] = "decimal"
    _CATEGORIES[QName(_XBRLI, _name + "ItemType")] = "decimal"
_CATEGORIES[QName(_XBRLI, "monetary")] = "monetary"
_CATEGORIES[QName(_XBRLI, "monetaryItemType")] = "monetary"
# Fractions have child elements and distinct accuracy rules, not scalar decimal text.
_CATEGORIES[QName(_XBRLI, "fractionItemType")] = "fraction"
_NUMERIC_CATEGORIES = frozenset({"monetary", "decimal", "integer", "float", "double"})


def concept_type_chain(concept: Concept) -> tuple[QName, ...]:
    """Return declaration then nearest-to-root bases; tolerate old missing metadata."""
    return (concept.data_type, *(getattr(concept, "data_type_ancestry", ()) or ()))


def concept_type_category(concept: Concept | None) -> str:
    """Choose the nearest recognized exact QName, never a local-name/value guess."""
    if concept is None:
        return "string"
    for qname in concept_type_chain(concept):
        category = _CATEGORIES.get(qname)
        if category is not None:
            return category
    # Older loaders already establish this explicit flag for monetary derivations.
    if getattr(concept, "monetary_item_type", False):
        return "monetary"
    return "string"


def concept_is_numeric(concept: Concept | None) -> bool:
    """Scalar numeric classification; structured fractions retain separate handling."""
    return concept_type_category(concept) in _NUMERIC_CATEGORIES


def concept_is_monetary(concept: Concept | None) -> bool:
    return concept_type_category(concept) == "monetary"


def concept_is_shares(concept: Concept | None) -> bool:
    return concept is not None and any(
        qname in (QName(_XBRLI, "sharesItemType"), QName(_XBRLI, "shares"))
        for qname in concept_type_chain(concept)
    )


def concept_is_pure(concept: Concept | None) -> bool:
    return concept is not None and any(
        qname in (QName(_XBRLI, "pureItemType"), QName(_XBRLI, "pure"))
        for qname in concept_type_chain(concept)
    )

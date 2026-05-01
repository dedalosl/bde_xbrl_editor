"""Formula linkbase parser — builds a FormulaAssertionSet from an XBRL formula linkbase XML file."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal
from urllib.parse import urldefrag

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import NS_ASSERTION_SETS_20_PWD, NS_VALIDATION_V10
from bde_xbrl_editor.taxonomy.models import (
    BooleanFilterDefinition,
    ConsistencyAssertionDefinition,
    DimensionFilter,
    ExistenceAssertionDefinition,
    FactVariableDefinition,
    FormulaAspectRule,
    FormulaAssertion,
    FormulaAssertionSet,
    FormulaOutputDefinition,
    QName,
    TypedDimensionFilter,
    ValueAssertionDefinition,
    XPathFilterDefinition,
)
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file

# ---------------------------------------------------------------------------
# Namespace constants
# ---------------------------------------------------------------------------

# The XBRL Formula 1.0 spec places assertion elements in namespace-per-type,
# NOT in the generic formula namespace (http://xbrl.org/2008/formula).
_NS_FORMULA = "http://xbrl.org/2008/formula"
_NS_VA = "http://xbrl.org/2008/assertion/value"
_NS_EA = "http://xbrl.org/2008/assertion/existence"
_NS_CA = "http://xbrl.org/2008/assertion/consistency"
_NS_VARIABLE = "http://xbrl.org/2008/variable"
_NS_CF = "http://xbrl.org/2008/filter/concept"
_NS_PF = "http://xbrl.org/2008/filter/period"
_NS_DF = "http://xbrl.org/2008/filter/dimension"
_NS_UF = "http://xbrl.org/2008/filter/unit"
_NS_GF = "http://xbrl.org/2008/filter/general"
_NS_BF = "http://xbrl.org/2008/filter/boolean"
_NS_LINK = "http://www.xbrl.org/2003/linkbase"
_NS_XLINK = "http://www.w3.org/1999/xlink"

# Clark-notation element tags — each assertion type lives in its own namespace
_TAG_VALUE_ASSERTION = f"{{{_NS_VA}}}valueAssertion"
_TAG_FORMULA = f"{{{_NS_FORMULA}}}formula"
_TAG_FORMULA_ASPECTS = f"{{{_NS_FORMULA}}}aspects"
_TAG_FORMULA_CONCEPT = f"{{{_NS_FORMULA}}}concept"
_TAG_FORMULA_QNAME = f"{{{_NS_FORMULA}}}qname"
_TAG_FORMULA_ENTITY_IDENTIFIER = f"{{{_NS_FORMULA}}}entityIdentifier"
_TAG_FORMULA_PERIOD = f"{{{_NS_FORMULA}}}period"
_TAG_FORMULA_UNIT = f"{{{_NS_FORMULA}}}unit"
_TAG_FORMULA_INSTANT = f"{{{_NS_FORMULA}}}instant"
_TAG_FORMULA_DURATION = f"{{{_NS_FORMULA}}}duration"
_TAG_FORMULA_FOREVER = f"{{{_NS_FORMULA}}}forever"
_TAG_FORMULA_EXPLICIT_DIMENSION = f"{{{_NS_FORMULA}}}explicitDimension"
_TAG_FORMULA_TYPED_DIMENSION = f"{{{_NS_FORMULA}}}typedDimension"
_TAG_EXISTENCE_ASSERTION = f"{{{_NS_EA}}}existenceAssertion"
_TAG_CONSISTENCY_ASSERTION = f"{{{_NS_CA}}}consistencyAssertion"
_TAG_FACT_VARIABLE = f"{{{_NS_VARIABLE}}}factVariable"
_TAG_VARIABLE_ARC = f"{{{_NS_VARIABLE}}}variableArc"
_TAG_VARIABLE_FILTER_ARC = f"{{{_NS_VARIABLE}}}variableFilterArc"
_TAG_CF_CONCEPT_NAME = f"{{{_NS_CF}}}conceptName"
_TAG_CF_CONCEPT = f"{{{_NS_CF}}}concept"
_TAG_CF_QNAME = f"{{{_NS_CF}}}qname"
_TAG_PF_INSTANT = f"{{{_NS_PF}}}instant"
_TAG_PF_DURATION = f"{{{_NS_PF}}}duration"
_TAG_PF_PERIOD = f"{{{_NS_PF}}}period"  # pf:period test="..." — XPath period filter
_TAG_DF_EXPLICIT_DIMENSION = f"{{{_NS_DF}}}explicitDimension"
_TAG_DF_TYPED_DIMENSION = f"{{{_NS_DF}}}typedDimension"
_TAG_DF_DIMENSION = f"{{{_NS_DF}}}dimension"
_TAG_DF_MEMBER = f"{{{_NS_DF}}}member"
_TAG_DF_QNAME = f"{{{_NS_DF}}}qname"
_TAG_GF_GENERAL = f"{{{_NS_GF}}}general"  # gf:general test="..." — XPath general filter
_TAG_BF_AND_FILTER = f"{{{_NS_BF}}}andFilter"
_TAG_BF_OR_FILTER = f"{{{_NS_BF}}}orFilter"
_BOOLEAN_FILTER_TAGS = (_TAG_BF_AND_FILTER, _TAG_BF_OR_FILTER)

# XLink attribute names (Clark notation)
_ATTR_XLINK_TYPE = f"{{{_NS_XLINK}}}type"
_ATTR_XLINK_LABEL = f"{{{_NS_XLINK}}}label"
_ATTR_XLINK_FROM = f"{{{_NS_XLINK}}}from"
_ATTR_XLINK_TO = f"{{{_NS_XLINK}}}to"
_ATTR_XLINK_ARCROLE = f"{{{_NS_XLINK}}}arcrole"

# Arcrole URIs
_ARCROLE_VARIABLE_SET = "http://xbrl.org/arcrole/2008/variable-set"
_ARCROLE_VARIABLE_FILTER = "http://xbrl.org/arcrole/2008/variable-filter"
_ARCROLE_VARIABLE_SET_FILTER = "http://xbrl.org/arcrole/2008/variable-set-filter"
_ARCROLE_BOOLEAN_FILTER = "http://xbrl.org/arcrole/2008/boolean-filter"
_ARCROLE_ASSERTION_SET = "http://xbrl.org/arcrole/2008/assertion-set"
_ARCROLE_APPLIES_TO_TABLE = "http://www.eurofiling.info/xbrl/arcrole/applies-to-table"

_TAG_VARIABLE_SET_FILTER_ARC = f"{{{_NS_VARIABLE}}}variableSetFilterArc"
_TAG_LINK_LOC = f"{{{_NS_LINK}}}loc"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_severity(value: str | None) -> str:
    """Return 'warning' or 'error' string. The evaluator converts this to ValidationSeverity."""
    if value and value.lower() == "warning":
        return "warning"
    return "error"


def _parse_abstract(value: str | None) -> bool:
    """Interpret the @abstract attribute string as a bool."""
    return (value or "").lower() == "true"


def _clark_to_qname(clark: str, nsmap: dict[str, str] | None = None) -> QName | None:
    """Parse a Clark-notation ``{ns}local`` string or a prefixed ``prefix:local`` string.

    Returns None if the string is empty or unparseable.
    """
    clark = (clark or "").strip()
    if not clark:
        return None
    if clark.startswith("{"):
        try:
            return QName.from_clark(clark)
        except (ValueError, IndexError):
            return None
    # Prefixed QName — resolve via the element's nsmap if available
    if ":" in clark:
        prefix, local = clark.split(":", 1)
        ns = (nsmap or {}).get(prefix, "")
        return QName(namespace=ns, local_name=local, prefix=prefix)
    return None


def _element_nsmap(el: etree._Element) -> dict[str, str]:
    """Return the namespace map (str → URI) for an element, filtering None keys."""
    return {k: v for k, v in el.nsmap.items() if k is not None}


def _parse_qname_element(parent: etree._Element, tag: str) -> QName | None:
    """Find a child element with *tag* and return a QName from its text content."""
    child = parent.find(tag)
    if child is None:
        return None
    text = (child.text or "").strip()
    if not text:
        return None
    return _clark_to_qname(text, _element_nsmap(child))


# ---------------------------------------------------------------------------
# Filter extraction
# ---------------------------------------------------------------------------


def _extract_concept_filter(filter_el: etree._Element) -> QName | None:
    """Extract the concept QName from a cf:conceptName or cf:concept element."""
    tag = filter_el.tag
    nsmap = _element_nsmap(filter_el)

    if tag == _TAG_CF_CONCEPT_NAME:
        # @name attribute holds a Clark-notation or prefixed QName
        name_attr = filter_el.get("name", "")
        if name_attr:
            return _clark_to_qname(name_attr, nsmap)
        # Direct cf:qname child
        qname_el = filter_el.find(_TAG_CF_QNAME)
        if qname_el is not None:
            return _clark_to_qname((qname_el.text or "").strip(), nsmap)
        # Nested cf:concept/cf:qname — pattern used by BDE/EBA formulas
        concept_el = filter_el.find(_TAG_CF_CONCEPT)
        if concept_el is not None:
            qname_el = concept_el.find(_TAG_CF_QNAME)
            if qname_el is not None:
                return _clark_to_qname((qname_el.text or "").strip(), _element_nsmap(concept_el))

    if tag == _TAG_CF_CONCEPT:
        qname_el = filter_el.find(_TAG_CF_QNAME)
        if qname_el is not None:
            return _clark_to_qname((qname_el.text or "").strip(), nsmap)

    return None


def _extract_period_filter(filter_el: etree._Element) -> Literal["instant", "duration"] | None:
    """Derive the period filter type from the element tag."""
    tag = filter_el.tag
    if tag == _TAG_PF_INSTANT:
        return "instant"
    if tag == _TAG_PF_DURATION:
        return "duration"
    return None


def _extract_dimension_filter(filter_el: etree._Element) -> DimensionFilter | None:
    """Extract a DimensionFilter from a df:explicitDimension element."""
    if filter_el.tag != _TAG_DF_EXPLICIT_DIMENSION:
        return None

    nsmap = _element_nsmap(filter_el)

    # Dimension QName — from df:dimension/df:qname text
    dim_el = filter_el.find(_TAG_DF_DIMENSION)
    if dim_el is None:
        return None
    dimension_qname = _parse_qname_element(dim_el, _TAG_DF_QNAME)
    if dimension_qname is None:
        # Try text directly on df:dimension
        dimension_qname = _clark_to_qname((dim_el.text or "").strip(), nsmap)
    if dimension_qname is None:
        return None

    # Member QNames — from df:member/df:qname text (zero or more)
    member_qnames: list[QName] = []
    for member_el in filter_el.findall(_TAG_DF_MEMBER):
        qn = _parse_qname_element(member_el, _TAG_DF_QNAME)
        if qn is None:
            qn = _clark_to_qname((member_el.text or "").strip(), nsmap)
        if qn is not None:
            member_qnames.append(qn)

    return DimensionFilter(
        dimension_qname=dimension_qname,
        member_qnames=tuple(member_qnames),
    )


def _extract_typed_dimension_filter(filter_el: etree._Element) -> TypedDimensionFilter | None:
    """Extract a TypedDimensionFilter from a df:typedDimension element."""
    if filter_el.tag != _TAG_DF_TYPED_DIMENSION:
        return None

    nsmap = _element_nsmap(filter_el)
    dim_el = filter_el.find(_TAG_DF_DIMENSION)
    if dim_el is None:
        return None
    dimension_qname = _parse_qname_element(dim_el, _TAG_DF_QNAME)
    if dimension_qname is None:
        dimension_qname = _clark_to_qname((dim_el.text or "").strip(), nsmap)
    if dimension_qname is None:
        return None
    return TypedDimensionFilter(dimension_qname=dimension_qname)


# ---------------------------------------------------------------------------
# Variable extraction
# ---------------------------------------------------------------------------


def _build_label_to_element(root: etree._Element, tag: str) -> dict[str, etree._Element]:
    """Index all *tag* elements in the document by their @xlink:label attribute."""
    index: dict[str, etree._Element] = {}
    for el in root.iter(tag):
        lbl = el.get(_ATTR_XLINK_LABEL, "")
        if lbl:
            index[lbl] = el
    return index


def _build_arc_map(root: etree._Element, arc_tags: list[str]) -> dict[str, list[str]]:
    """Build a from→[to, …] mapping for all arcs matching *arc_tags*."""
    arc_map: dict[str, list[str]] = {}
    for tag in arc_tags:
        for arc in root.iter(tag):
            _arcrole = arc.get(_ATTR_XLINK_ARCROLE, "")
            frm = arc.get(_ATTR_XLINK_FROM, "")
            to = arc.get(_ATTR_XLINK_TO, "")
            if frm and to:
                arc_map.setdefault(frm, []).append(to)
    return arc_map


def _build_filter_arc_map(root: etree._Element) -> dict[str, list[str]]:
    """Build a variable-label→[filter-label, …] mapping from variableFilterArc elements."""
    arc_map: dict[str, list[str]] = {}
    for arc in root.iter(_TAG_VARIABLE_FILTER_ARC):
        frm = arc.get(_ATTR_XLINK_FROM, "")
        to = arc.get(_ATTR_XLINK_TO, "")
        if frm and to:
            arc_map.setdefault(frm, []).append(to)
    return arc_map


def _build_variable_set_filter_arc_map(root: etree._Element) -> dict[str, list[str]]:
    """Build an assertion-label→[filter-label, …] mapping from variableSetFilterArc elements.

    These filters apply at the assertion level (to all variables in the set).
    """
    arc_map: dict[str, list[str]] = {}
    for arc in root.iter(_TAG_VARIABLE_SET_FILTER_ARC):
        frm = arc.get(_ATTR_XLINK_FROM, "")
        to = arc.get(_ATTR_XLINK_TO, "")
        if frm and to:
            arc_map.setdefault(frm, []).append(to)
    return arc_map


def _build_boolean_filter_arc_map(root: etree._Element) -> dict[str, list[tuple[str, bool]]]:
    """Build a parent-label → [(child-label, complement), …] map from boolean-filter arcs.

    Both variableFilterArc and variableSetFilterArc elements can carry arcrole
    ``boolean-filter`` when they connect boolean filter nodes to their children.
    Each entry carries the complement flag from the arc.
    """
    arc_map: dict[str, list[tuple[str, bool]]] = {}
    for arc_tag in (_TAG_VARIABLE_FILTER_ARC, _TAG_VARIABLE_SET_FILTER_ARC):
        for arc in root.iter(arc_tag):
            if arc.get(_ATTR_XLINK_ARCROLE, "") != _ARCROLE_BOOLEAN_FILTER:
                continue
            frm = arc.get(_ATTR_XLINK_FROM, "")
            to = arc.get(_ATTR_XLINK_TO, "")
            complement = arc.get("complement", "false").lower() == "true"
            if frm and to:
                arc_map.setdefault(frm, []).append((to, complement))
    return arc_map


def _build_boolean_filter(
    label: str,
    filter_index: dict[str, etree._Element],
    bool_arc_map: dict[str, list[tuple[str, bool]]],
    complement: bool = False,
    _seen: frozenset[str] | None = None,
) -> BooleanFilterDefinition | None:
    """Recursively build a BooleanFilterDefinition from the arc/filter indexes.

    *_seen* prevents infinite loops from cyclic arc graphs (should not occur in
    valid linkbases, but guarded defensively).
    """
    seen = _seen or frozenset()
    if label in seen:
        return None
    seen = seen | {label}

    filter_el = filter_index.get(label)
    if filter_el is None:
        return None
    if filter_el.tag not in _BOOLEAN_FILTER_TAGS:
        return None

    filter_type: str = "and" if filter_el.tag == _TAG_BF_AND_FILTER else "or"
    children: list[object] = []

    for child_label, child_complement in bool_arc_map.get(label, []):
        child_el = filter_index.get(child_label)
        if child_el is None:
            continue

        if child_el.tag in _BOOLEAN_FILTER_TAGS:
            # Nested boolean filter — recurse
            nested = _build_boolean_filter(
                child_label,
                filter_index,
                bool_arc_map,
                complement=child_complement,
                _seen=seen,
            )
            if nested is not None:
                children.append(nested)

        elif child_el.tag == _TAG_DF_EXPLICIT_DIMENSION:
            df = _extract_dimension_filter(child_el)
            if df is not None:
                if child_complement:
                    # Wrap as an exclude filter
                    df = DimensionFilter(
                        dimension_qname=df.dimension_qname,
                        member_qnames=df.member_qnames,
                        exclude=True,
                    )
                children.append(df)

        elif child_el.tag == _TAG_DF_TYPED_DIMENSION:
            tf = _extract_typed_dimension_filter(child_el)
            if tf is not None:
                if child_complement:
                    tf = TypedDimensionFilter(
                        dimension_qname=tf.dimension_qname,
                        exclude=True,
                    )
                children.append(tf)

        elif child_el.tag == _TAG_GF_GENERAL:
            test_expr = (child_el.get("test") or "").strip()
            if test_expr:
                children.append(
                    XPathFilterDefinition(
                        xpath_expr=test_expr,
                        namespaces=_element_nsmap(child_el),
                    )
                )

        elif child_el.tag in (_TAG_CF_CONCEPT_NAME, _TAG_CF_CONCEPT):
            # Concept filter inside a boolean filter is unusual but possible
            qn = _extract_concept_filter(child_el)
            if qn is not None:
                # Store as a 1-element XPathFilterDefinition wrapping the concept check
                # (simpler than adding a concept-filter type to the children union)
                # We represent it as a dimension-less DimensionFilter sentinel — not ideal,
                # so skip for now; concept-inside-boolean is very rare in BDE taxonomies.
                pass

    return BooleanFilterDefinition(
        filter_type=filter_type,  # type: ignore[arg-type]
        children=tuple(children),
        complement=complement,
    )


_FILTER_TAGS = [
    _TAG_CF_CONCEPT_NAME,
    _TAG_CF_CONCEPT,
    _TAG_PF_INSTANT,
    _TAG_PF_DURATION,
    _TAG_PF_PERIOD,
    _TAG_DF_EXPLICIT_DIMENSION,
    _TAG_DF_TYPED_DIMENSION,
    _TAG_GF_GENERAL,
    _TAG_BF_AND_FILTER,
    _TAG_BF_OR_FILTER,
]


def _build_filter_label_index(root: etree._Element) -> dict[str, etree._Element]:
    """Index all known filter elements by their @xlink:label."""
    index: dict[str, etree._Element] = {}
    for tag in _FILTER_TAGS:
        for el in root.iter(tag):
            lbl = el.get(_ATTR_XLINK_LABEL, "")
            if lbl:
                index[lbl] = el
    return index


def _parse_fact_variable(
    var_el: etree._Element,
    filter_arc_map: dict[str, list[str]],
    filter_index: dict[str, etree._Element],
    bool_arc_map: dict[str, list[tuple[str, bool]]],
    arc_name: str = "",
    global_concept_filter: QName | None = None,
    global_dimension_filters: list[DimensionFilter] | None = None,
    global_typed_dimension_filters: list[TypedDimensionFilter] | None = None,
    global_boolean_filters: list[BooleanFilterDefinition] | None = None,
) -> FactVariableDefinition:
    """Build a FactVariableDefinition from a variable:factVariable element.

    *arc_name* is the ``name`` attribute from the ``variable:variableArc`` that
    connects the assertion to this variable — that is the XPath variable name
    used in test/formula expressions (e.g. ``$a``).  If absent, fall back to
    any element-level ``name`` attribute or the ``xlink:label``.
    """
    variable_name = arc_name or var_el.get("name", "") or var_el.get(_ATTR_XLINK_LABEL, "")
    var_label = var_el.get(_ATTR_XLINK_LABEL, variable_name)

    concept_filter: QName | None = None
    period_filter: Literal["instant", "duration"] | None = None
    dimension_filters: list[DimensionFilter] = []
    typed_dimension_filters: list[TypedDimensionFilter] = []
    xpath_filters: list[XPathFilterDefinition] = []
    boolean_filters: list[BooleanFilterDefinition] = []

    for filter_label in filter_arc_map.get(var_label, []):
        filter_el = filter_index.get(filter_label)
        if filter_el is None:
            continue

        # Concept filter
        if filter_el.tag in (_TAG_CF_CONCEPT_NAME, _TAG_CF_CONCEPT):
            qn = _extract_concept_filter(filter_el)
            if qn is not None and concept_filter is None:
                concept_filter = qn

        # Period type filter (simple instant/duration)
        elif filter_el.tag in (_TAG_PF_INSTANT, _TAG_PF_DURATION):
            pf = _extract_period_filter(filter_el)
            if pf is not None and period_filter is None:
                period_filter = pf

        # Period filter with XPath test expression
        elif filter_el.tag == _TAG_PF_PERIOD:
            test_expr = (filter_el.get("test") or "").strip()
            if test_expr:
                xpath_filters.append(
                    XPathFilterDefinition(
                        xpath_expr=test_expr,
                        namespaces=_element_nsmap(filter_el),
                    )
                )

        # Dimension filter
        elif filter_el.tag == _TAG_DF_EXPLICIT_DIMENSION:
            df = _extract_dimension_filter(filter_el)
            if df is not None:
                dimension_filters.append(df)

        elif filter_el.tag == _TAG_DF_TYPED_DIMENSION:
            tf = _extract_typed_dimension_filter(filter_el)
            if tf is not None:
                typed_dimension_filters.append(tf)

        # Boolean filter (bf:andFilter / bf:orFilter)
        elif filter_el.tag in _BOOLEAN_FILTER_TAGS:
            bf = _build_boolean_filter(filter_label, filter_index, bool_arc_map)
            if bf is not None:
                boolean_filters.append(bf)

        # General XPath filter
        elif filter_el.tag == _TAG_GF_GENERAL:
            test_expr = (filter_el.get("test") or "").strip()
            if test_expr:
                xpath_filters.append(
                    XPathFilterDefinition(
                        xpath_expr=test_expr,
                        namespaces=_element_nsmap(filter_el),
                    )
                )

    # Append assertion-level filters (from variableSetFilterArc)
    if global_concept_filter is not None and concept_filter is None:
        concept_filter = global_concept_filter

    if global_dimension_filters:
        for gdf in global_dimension_filters:
            # Only add if not already covered by a variable-specific filter for the same dimension
            if not any(df.dimension_qname == gdf.dimension_qname for df in dimension_filters):
                dimension_filters.append(gdf)

    if global_typed_dimension_filters:
        for gtf in global_typed_dimension_filters:
            if not any(tf.dimension_qname == gtf.dimension_qname for tf in typed_dimension_filters):
                typed_dimension_filters.append(gtf)

    # Append assertion-level boolean filters
    if global_boolean_filters:
        boolean_filters.extend(global_boolean_filters)

    fallback_value: str | None = var_el.get("fallbackValue")

    return FactVariableDefinition(
        variable_name=variable_name,
        bind_as_sequence=(var_el.get("bindAsSequence") or "false").lower() == "true",
        matches=(var_el.get("matches") or "false").lower() == "true",
        concept_filter=concept_filter,
        period_filter=period_filter,
        dimension_filters=tuple(dimension_filters),
        typed_dimension_filters=tuple(typed_dimension_filters),
        fallback_value=fallback_value,
        xpath_filters=tuple(xpath_filters),
        boolean_filters=tuple(boolean_filters),
    )


# ---------------------------------------------------------------------------
# Assertion extraction
# ---------------------------------------------------------------------------

_ASSERTION_TAGS = (
    _TAG_VALUE_ASSERTION,
    _TAG_EXISTENCE_ASSERTION,
    _TAG_CONSISTENCY_ASSERTION,
)

# ``{…}assertionSet`` — only Table-1 namespace URIs from Validation 1.0 REC and Assertion Sets 2.0 PWD.
_ASSERTION_SET_NAMESPACES = frozenset({NS_VALIDATION_V10, NS_ASSERTION_SETS_20_PWD})
_ASSERTION_SET_TAGS: tuple[str, ...] = (
    f"{{{NS_VALIDATION_V10}}}assertionSet",
    f"{{{NS_ASSERTION_SETS_20_PWD}}}assertionSet",
)

# QName filter for ``iterparse(..., tag=…)`` — jumps straight to matching elements so
# huge FINREP-style linkbases (many filters/locs before the first assertion) are still found.
_LINKBASE_FORMULA_SCAN_TAGS: tuple[str, ...] = (
    _ASSERTION_TAGS + (_TAG_FORMULA,) + _ASSERTION_SET_TAGS
)


def linkbase_contains_formula_assertions(path: Path) -> bool:
    """Return True when *path* contains Formula 1.0 assertions or a normative ``assertionSet``.

    Detection is structural (element QName), not filename-based. Uses
    ``iterparse`` with an element ``tag`` filter so the first assertion is found
    without scanning tens of thousands of unrelated nodes (typical FINREP
    formula linkbases).

    Only ``end`` events are used; each matched element is cleared after inspection.
    Clearing on ``start`` events is unsafe for libxml2. Returns False on errors.
    """
    if not path.exists() or path.suffix.lower() not in (".xml", ".xbrl"):
        return False
    try:
        for _evt, el in etree.iterparse(
            str(path), events=("end",), tag=_LINKBASE_FORMULA_SCAN_TAGS
        ):
            el.clear()
            return True
    except Exception:  # noqa: BLE001
        return False
    return False


def _parse_assertion(
    assertion_el: etree._Element,
    variable_arc_map: dict[str, list[tuple[str, str]]],
    fact_variable_index: dict[str, etree._Element],
    filter_arc_map: dict[str, list[str]],
    filter_index: dict[str, etree._Element],
    variable_set_filter_arc_map: dict[str, list[str]] | None = None,
    bool_arc_map: dict[str, list[tuple[str, bool]]] | None = None,
) -> FormulaAssertion | None:
    """Build a typed assertion definition from an assertion element."""
    _id = (assertion_el.get("id") or "").strip()
    _xlabel = (assertion_el.get(_ATTR_XLINK_LABEL) or "").strip()
    assertion_id = _id or _xlabel
    if not assertion_id:
        return None

    abstract = _parse_abstract(assertion_el.get("abstract"))
    severity = _parse_severity(assertion_el.get("severity"))
    label = _xlabel or _id or None
    precondition_xpath: str | None = None  # preconditions not yet parsed

    # Collect bound fact variables via variable arcs (from=assertion_id or from=xlink:label)
    # variable_arc_map values are (to_label, arc_name) tuples where arc_name is the XPath
    # variable name (the ``name`` attribute on variable:variableArc).
    assertion_label = _xlabel or assertion_id
    variable_entries = variable_arc_map.get(assertion_id, []) + (
        variable_arc_map.get(assertion_label, []) if assertion_label != assertion_id else []
    )

    # Collect assertion-level filters from variableSetFilterArc
    global_concept_filter: QName | None = None
    global_dimension_filters: list[DimensionFilter] = []
    global_typed_dimension_filters: list[TypedDimensionFilter] = []
    global_boolean_filters: list[BooleanFilterDefinition] = []
    if variable_set_filter_arc_map is not None:
        _bool_arc = bool_arc_map or {}
        # Deduplicate when assertion_id == assertion_label (both map to the same list)
        _seen_set_labels: set[str] = set()
        _set_filter_labels = variable_set_filter_arc_map.get(assertion_id, []) + (
            variable_set_filter_arc_map.get(assertion_label, [])
            if assertion_label != assertion_id
            else []
        )
        for set_filter_label in _set_filter_labels:
            if set_filter_label in _seen_set_labels:
                continue
            _seen_set_labels.add(set_filter_label)
            filter_el = filter_index.get(set_filter_label)
            if filter_el is None:
                continue
            if filter_el.tag in (_TAG_CF_CONCEPT_NAME, _TAG_CF_CONCEPT):
                qn = _extract_concept_filter(filter_el)
                if qn is not None and global_concept_filter is None:
                    global_concept_filter = qn
            elif filter_el.tag == _TAG_DF_EXPLICIT_DIMENSION:
                df = _extract_dimension_filter(filter_el)
                if df is not None:
                    global_dimension_filters.append(df)
            elif filter_el.tag == _TAG_DF_TYPED_DIMENSION:
                tf = _extract_typed_dimension_filter(filter_el)
                if tf is not None:
                    global_typed_dimension_filters.append(tf)
            elif filter_el.tag in _BOOLEAN_FILTER_TAGS:
                bf = _build_boolean_filter(set_filter_label, filter_index, _bool_arc)
                if bf is not None:
                    global_boolean_filters.append(bf)

    variables: list[FactVariableDefinition] = []
    seen_var_labels: set[str] = set()
    for var_label, arc_name in variable_entries:
        if var_label in seen_var_labels:
            continue
        seen_var_labels.add(var_label)
        var_el = fact_variable_index.get(var_label)
        if var_el is not None:
            variables.append(
                _parse_fact_variable(
                    var_el,
                    filter_arc_map,
                    filter_index,
                    bool_arc_map=bool_arc_map or {},
                    arc_name=arc_name,
                    global_concept_filter=global_concept_filter,
                    global_dimension_filters=global_dimension_filters or None,
                    global_typed_dimension_filters=global_typed_dimension_filters or None,
                    global_boolean_filters=global_boolean_filters or None,
                )
            )

    tag = assertion_el.tag

    namespaces = _element_nsmap(assertion_el)

    common: dict = dict(
        assertion_id=assertion_id,
        label=label,
        severity=severity,
        abstract=abstract,
        variables=tuple(variables),
        precondition_xpath=precondition_xpath,
        namespaces=namespaces,
    )

    if tag == _TAG_VALUE_ASSERTION:
        return ValueAssertionDefinition(
            **common,
            test_xpath=assertion_el.get("test", ""),
        )

    if tag == _TAG_EXISTENCE_ASSERTION:
        return ExistenceAssertionDefinition(
            **common,
            test_xpath=assertion_el.get("test"),
        )

    if tag == _TAG_CONSISTENCY_ASSERTION:
        formula_xpath = assertion_el.get("formula", "")
        absolute_radius: Decimal | None = None
        relative_radius: Decimal | None = None
        try:
            ar = assertion_el.get("absoluteRadius")
            if ar is not None:
                absolute_radius = Decimal(ar)
        except InvalidOperation:
            pass
        try:
            rr = assertion_el.get("relativeRadius")
            if rr is not None:
                relative_radius = Decimal(rr)
        except InvalidOperation:
            pass
        return ConsistencyAssertionDefinition(
            **common,
            formula_xpath=formula_xpath,
            absolute_radius=absolute_radius,
            relative_radius=relative_radius,
        )

    return None  # unknown assertion type


def _formula_rule_source(rule_el: etree._Element, inherited_source: str | None) -> str | None:
    return (rule_el.get("source") or inherited_source or "").strip() or None


def _parse_formula_period_kind(
    period_el: etree._Element,
) -> Literal["instant", "duration", "forever"] | None:
    if period_el.find(_TAG_FORMULA_INSTANT) is not None:
        return "instant"
    if period_el.find(_TAG_FORMULA_DURATION) is not None:
        return "duration"
    if period_el.find(_TAG_FORMULA_FOREVER) is not None:
        return "forever"
    return None


def _parse_formula_aspect_rules(formula_el: etree._Element) -> tuple[FormulaAspectRule, ...]:
    rules: list[FormulaAspectRule] = []
    for aspects_el in formula_el.findall(_TAG_FORMULA_ASPECTS):
        inherited_source = (aspects_el.get("source") or "").strip() or None
        for child in aspects_el:
            if not isinstance(child.tag, str):
                continue
            source = _formula_rule_source(child, inherited_source)
            if child.tag == _TAG_FORMULA_CONCEPT:
                qname_el = child.find(_TAG_FORMULA_QNAME)
                qname = _clark_to_qname(
                    (qname_el.text if qname_el is not None else "") or "",
                    _element_nsmap(child),
                )
                rules.append(
                    FormulaAspectRule(
                        aspect="concept",
                        source=source,
                        qname=qname,
                        has_child_rules=len(child) > 0,
                        inherited_source=inherited_source,
                    )
                )
            elif child.tag == _TAG_FORMULA_ENTITY_IDENTIFIER:
                rules.append(
                    FormulaAspectRule(
                        aspect="entityIdentifier",
                        source=source,
                        has_scheme=bool((child.get("scheme") or "").strip()),
                        has_value=bool((child.get("value") or "").strip()),
                        inherited_source=inherited_source,
                    )
                )
            elif child.tag == _TAG_FORMULA_PERIOD:
                rules.append(
                    FormulaAspectRule(
                        aspect="period",
                        source=source,
                        has_child_rules=len(child) > 0,
                        period_kind=_parse_formula_period_kind(child),
                        inherited_source=inherited_source,
                    )
                )
            elif child.tag == _TAG_FORMULA_UNIT:
                rules.append(
                    FormulaAspectRule(
                        aspect="unit",
                        source=source,
                        has_child_rules=len(child) > 0,
                        inherited_source=inherited_source,
                    )
                )
            elif child.tag == _TAG_FORMULA_EXPLICIT_DIMENSION:
                rules.append(
                    FormulaAspectRule(
                        aspect="explicitDimension",
                        source=source,
                        dimension=_clark_to_qname(
                            child.get("dimension") or "", _element_nsmap(child)
                        ),
                        has_child_rules=len(child) > 0,
                        inherited_source=inherited_source,
                    )
                )
            elif child.tag == _TAG_FORMULA_TYPED_DIMENSION:
                rules.append(
                    FormulaAspectRule(
                        aspect="typedDimension",
                        source=source,
                        dimension=_clark_to_qname(
                            child.get("dimension") or "", _element_nsmap(child)
                        ),
                        has_child_rules=len(child) > 0,
                        inherited_source=inherited_source,
                    )
                )
    return tuple(rules)


def _parse_output_formula(
    formula_el: etree._Element,
    variable_arc_map: dict[str, list[tuple[str, str]]],
    fact_variable_index: dict[str, etree._Element],
    filter_arc_map: dict[str, list[str]],
    filter_index: dict[str, etree._Element],
    variable_set_filter_arc_map: dict[str, list[str]] | None = None,
    bool_arc_map: dict[str, list[tuple[str, bool]]] | None = None,
    source_path: Path | None = None,
) -> FormulaOutputDefinition | None:
    _id = (formula_el.get("id") or "").strip()
    _xlabel = (formula_el.get(_ATTR_XLINK_LABEL) or "").strip()
    formula_id = _id or _xlabel
    if not formula_id:
        return None

    variable_entries = variable_arc_map.get(formula_id, []) + (
        variable_arc_map.get(_xlabel, []) if _xlabel and _xlabel != formula_id else []
    )
    variables: list[FactVariableDefinition] = []
    seen_var_labels: set[str] = set()
    for var_label, arc_name in variable_entries:
        if var_label in seen_var_labels:
            continue
        seen_var_labels.add(var_label)
        var_el = fact_variable_index.get(var_label)
        if var_el is None:
            continue
        variables.append(
            _parse_fact_variable(
                var_el,
                filter_arc_map,
                filter_index,
                bool_arc_map=bool_arc_map or {},
                arc_name=arc_name,
            )
        )

    return FormulaOutputDefinition(
        formula_id=formula_id,
        label=_xlabel or _id or None,
        value_xpath=formula_el.get("value", ""),
        source=(formula_el.get("source") or "").strip() or None,
        aspect_model=(formula_el.get("aspectModel") or "").strip() or None,
        implicit_filtering=(formula_el.get("implicitFiltering") or "true").lower() != "false",
        variables=tuple(variables),
        aspect_rules=_parse_formula_aspect_rules(formula_el),
        namespaces=_element_nsmap(formula_el),
        source_path=str(source_path) if source_path is not None else None,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_formula_linkbase(path: Path) -> FormulaAssertionSet:
    """Parse a formula / validation linkbase and return a FormulaAssertionSet.

    Assertions may live directly under ``link:linkbase`` or inside generic
    packaging (e.g. ``gen:link`` with ``{http://xbrl.org/2008/validation}assertionSet``).
    DTS discovery uses :func:`linkbase_contains_formula_assertions` (no filename rules).

    Returns an empty FormulaAssertionSet if the file is missing, malformed,
    or contains no assertions. Never raises.
    """
    try:
        return _parse(path)
    except Exception:  # noqa: BLE001
        return FormulaAssertionSet()


def parse_assertion_table_mappings(path: Path) -> dict[str, str]:
    """Return assertion-id -> table-id mappings from assertion-set linkbases.

    BDE taxonomies relate a group of assertions to a table through
    ``applies-to-table`` arcs on ``validation:assertionSet`` resources. This
    helper resolves those arcs plus the downstream ``assertion-set`` arcs to
    recover the table associated with each assertion.
    """
    try:
        return _parse_assertion_table_mappings(path)
    except Exception:  # noqa: BLE001
        return {}


def _parse(path: Path) -> FormulaAssertionSet:
    """Internal parser — may raise; callers must wrap in try/except."""
    if not path.exists():
        return FormulaAssertionSet()

    try:
        tree = parse_xml_file(path)
    except etree.XMLSyntaxError:
        return FormulaAssertionSet()

    return _parse_formula_root(tree.getroot(), source_path=path)


def _parse_assertion_table_mappings(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    try:
        tree = parse_xml_file(path)
    except etree.XMLSyntaxError:
        return {}

    return _parse_assertion_table_mappings_root(tree.getroot())


def _parse_assertion_table_mappings_root(root: etree._Element) -> dict[str, str]:
    locator_targets: dict[str, str] = {}
    for locator in root.iter(_TAG_LINK_LOC):
        label = (locator.get(_ATTR_XLINK_LABEL) or "").strip()
        href = (locator.get(f"{{{_NS_XLINK}}}href") or "").strip()
        fragment = _href_fragment(href)
        if label and fragment:
            locator_targets[label] = fragment

    assertion_set_labels: set[str] = set()
    for tag in _ASSERTION_SET_TAGS:
        for assertion_set in root.iter(tag):
            label = (assertion_set.get(_ATTR_XLINK_LABEL) or "").strip()
            if label:
                assertion_set_labels.add(label)

    table_by_assertion_set: dict[str, str] = {}
    assertions_by_set: dict[str, list[str]] = {}
    for generic_arc in root.iter():
        if generic_arc.get(_ATTR_XLINK_TYPE) != "arc":
            continue
        arcrole = (generic_arc.get(_ATTR_XLINK_ARCROLE) or "").strip()
        frm = (generic_arc.get(_ATTR_XLINK_FROM) or "").strip()
        to = (generic_arc.get(_ATTR_XLINK_TO) or "").strip()
        if not frm or not to or frm not in assertion_set_labels:
            continue

        target_fragment = locator_targets.get(to)
        if not target_fragment:
            continue

        if arcrole == _ARCROLE_APPLIES_TO_TABLE:
            table_by_assertion_set[frm] = target_fragment
        elif arcrole == _ARCROLE_ASSERTION_SET:
            assertions_by_set.setdefault(frm, []).append(target_fragment)

    assertion_table_map: dict[str, str] = {}
    for assertion_set_label, assertion_ids in assertions_by_set.items():
        table_id = table_by_assertion_set.get(assertion_set_label)
        if not table_id:
            continue
        for assertion_id in assertion_ids:
            assertion_table_map.setdefault(assertion_id, table_id)

    return assertion_table_map


def _href_fragment(href: str) -> str:
    """Return the fragment identifier from an xlink:href, if any."""
    _path, fragment = urldefrag(href)
    return fragment.strip()


def _parse_formula_root(
    root: etree._Element, source_path: Path | None = None
) -> FormulaAssertionSet:
    """Parse assertions from a link:linkbase root (including under gen:link / assertionSet)."""
    fact_variable_index = _build_label_to_element(root, _TAG_FACT_VARIABLE)
    filter_index = _build_filter_label_index(root)
    filter_arc_map = _build_filter_arc_map(root)
    variable_set_filter_arc_map = _build_variable_set_filter_arc_map(root)
    bool_arc_map = _build_boolean_filter_arc_map(root)

    variable_arc_map: dict[str, list[tuple[str, str]]] = {}
    for arc in root.iter(_TAG_VARIABLE_ARC):
        frm = arc.get(_ATTR_XLINK_FROM, "")
        to = arc.get(_ATTR_XLINK_TO, "")
        arc_name = arc.get("name", "")
        if frm and to:
            variable_arc_map.setdefault(frm, []).append((to, arc_name))

    assertions: list[FormulaAssertion] = []
    output_formulas: list[FormulaOutputDefinition] = []
    abstract_count = 0

    for tag in _ASSERTION_TAGS:
        for assertion_el in root.iter(tag):
            result = _parse_assertion(
                assertion_el,
                variable_arc_map,
                fact_variable_index,
                filter_arc_map,
                filter_index,
                variable_set_filter_arc_map=variable_set_filter_arc_map,
                bool_arc_map=bool_arc_map,
            )
            if result is not None:
                assertions.append(result)
                if result.abstract:
                    abstract_count += 1

    for formula_el in root.iter(_TAG_FORMULA):
        result = _parse_output_formula(
            formula_el,
            variable_arc_map,
            fact_variable_index,
            filter_arc_map,
            filter_index,
            variable_set_filter_arc_map=variable_set_filter_arc_map,
            bool_arc_map=bool_arc_map,
            source_path=source_path,
        )
        if result is not None:
            output_formulas.append(result)

    return FormulaAssertionSet(
        assertions=tuple(assertions),
        output_formulas=tuple(output_formulas),
        abstract_count=abstract_count,
    )

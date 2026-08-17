"""Formula linkbase parser — builds a FormulaAssertionSet from an XBRL formula linkbase XML file."""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal
from urllib.parse import urldefrag

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import (
    FORMULA_XPATH_DEFAULT_PREFIXES,
    NS_ASSERTION_SETS_20_PWD,
    NS_VALIDATION_V10,
)
from bde_xbrl_editor.taxonomy.models import (
    AssertionTextResource,
    BooleanFilterDefinition,
    ConsistencyAssertionDefinition,
    DimensionFilter,
    ExistenceAssertionDefinition,
    FactVariableDefinition,
    FormulaArc,
    FormulaAspectRule,
    FormulaAssertion,
    FormulaAssertionSet,
    FormulaCustomRelationship,
    FormulaFilterResource,
    FormulaOutputDefinition,
    GeneralVariableDefinition,
    ParameterDefinition,
    PreconditionDefinition,
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
_NS_SSF = "http://xbrl.org/2008/filter/segment-scenario"
_NS_TF = "http://xbrl.org/2008/filter/tuple"
_NS_VF = "http://xbrl.org/2008/filter/value"
_NS_MF = "http://xbrl.org/2008/filter/match"
_NS_ACF = "http://xbrl.org/2010/filter/aspect-cover"
_NS_CRF = "http://xbrl.org/2010/filter/concept-relation"
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
_TAG_FORMULA_DECIMALS = f"{{{_NS_FORMULA}}}decimals"
_TAG_FORMULA_PRECISION = f"{{{_NS_FORMULA}}}precision"
_TAG_EXISTENCE_ASSERTION = f"{{{_NS_EA}}}existenceAssertion"
_TAG_CONSISTENCY_ASSERTION = f"{{{_NS_CA}}}consistencyAssertion"
_TAG_FACT_VARIABLE = f"{{{_NS_VARIABLE}}}factVariable"
_TAG_GENERAL_VARIABLE = f"{{{_NS_VARIABLE}}}generalVariable"
_TAG_PARAMETER = f"{{{_NS_VARIABLE}}}parameter"
_TAG_PRECONDITION = f"{{{_NS_VARIABLE}}}precondition"
_TAG_VARIABLE_ARC = f"{{{_NS_VARIABLE}}}variableArc"
_TAG_PARAMETER_ARC = f"{{{_NS_VARIABLE}}}parameterArc"
_TAG_PRECONDITION_ARC = f"{{{_NS_VARIABLE}}}preconditionArc"
_TAG_VARIABLE_FILTER_ARC = f"{{{_NS_VARIABLE}}}variableFilterArc"
_TAG_GENERIC_ARC = "{http://xbrl.org/2008/generic}arc"
_TAG_CF_CONCEPT_NAME = f"{{{_NS_CF}}}conceptName"
_TAG_CF_CONCEPT = f"{{{_NS_CF}}}concept"
_TAG_CF_QNAME = f"{{{_NS_CF}}}qname"
_TAG_CF_QNAME_EXPRESSION = f"{{{_NS_CF}}}qnameExpression"
_TAG_PF_INSTANT = f"{{{_NS_PF}}}instant"
_TAG_PF_DURATION = f"{{{_NS_PF}}}duration"
_TAG_PF_PERIOD = f"{{{_NS_PF}}}period"  # pf:period test="..." — XPath period filter
_TAG_DF_EXPLICIT_DIMENSION = f"{{{_NS_DF}}}explicitDimension"
_TAG_DF_TYPED_DIMENSION = f"{{{_NS_DF}}}typedDimension"
_TAG_DF_DIMENSION = f"{{{_NS_DF}}}dimension"
_TAG_DF_MEMBER = f"{{{_NS_DF}}}member"
_TAG_DF_QNAME = f"{{{_NS_DF}}}qname"
_TAG_GF_GENERAL = f"{{{_NS_GF}}}general"  # gf:general test="..." — XPath general filter
_NS_EF = "http://xbrl.org/2008/filter/entity"
_TAG_EF_IDENTIFIER = f"{{{_NS_EF}}}identifier"
_TAG_SSF_SEGMENT = f"{{{_NS_SSF}}}segment"
_TAG_SSF_SCENARIO = f"{{{_NS_SSF}}}scenario"
_TAG_UF_GENERAL_MEASURES = f"{{{_NS_UF}}}generalMeasures"
_TAG_UF_SINGLE_MEASURE = f"{{{_NS_UF}}}singleMeasure"
_TAG_UF_MEASURE = f"{{{_NS_UF}}}measure"
_TAG_UF_QNAME = f"{{{_NS_UF}}}qname"
_TAG_VF_NIL = f"{{{_NS_VF}}}nil"
_TAG_VF_PRECISION = f"{{{_NS_VF}}}precision"
_TAG_EQUALITY_DEFINITION = f"{{{_NS_VARIABLE}}}equalityDefinition"
_TAG_BF_AND_FILTER = f"{{{_NS_BF}}}andFilter"
_TAG_BF_OR_FILTER = f"{{{_NS_BF}}}orFilter"
_BOOLEAN_FILTER_TAGS = (_TAG_BF_AND_FILTER, _TAG_BF_OR_FILTER)
_FILTER_NAMESPACES = frozenset(
    {
        _NS_CF,
        _NS_PF,
        _NS_DF,
        _NS_UF,
        _NS_GF,
        _NS_BF,
        _NS_EF,
        _NS_SSF,
        _NS_TF,
        _NS_VF,
        _NS_MF,
        _NS_ACF,
        _NS_CRF,
    }
)

# XLink attribute names (Clark notation)
_ATTR_XLINK_TYPE = f"{{{_NS_XLINK}}}type"
_ATTR_XLINK_LABEL = f"{{{_NS_XLINK}}}label"
_ATTR_XLINK_HREF = f"{{{_NS_XLINK}}}href"
_ATTR_XLINK_FROM = f"{{{_NS_XLINK}}}from"
_ATTR_XLINK_TO = f"{{{_NS_XLINK}}}to"
_ATTR_XLINK_ARCROLE = f"{{{_NS_XLINK}}}arcrole"

# Arcrole URIs
_ARCROLE_VARIABLE_SET = "http://xbrl.org/arcrole/2008/variable-set"
_ARCROLE_VARIABLE_FILTER = "http://xbrl.org/arcrole/2008/variable-filter"
_ARCROLE_VARIABLE_SET_FILTER = "http://xbrl.org/arcrole/2008/variable-set-filter"
_ARCROLE_BOOLEAN_FILTER = "http://xbrl.org/arcrole/2008/boolean-filter"
_ARCROLE_VARIABLE_SET_PRECONDITION = "http://xbrl.org/arcrole/2008/variable-set-precondition"
_ARCROLE_VARIABLE_SET_PARAMETER = "http://xbrl.org/arcrole/2008/variable-set"
_ARCROLE_ASSERTION_SET = "http://xbrl.org/arcrole/2008/assertion-set"
_ARCROLE_CONSISTENCY_ASSERTION_FORMULA = (
    "http://xbrl.org/arcrole/2008/consistency-assertion-formula"
)
_ARCROLE_APPLIES_TO_TABLE = "http://www.eurofiling.info/xbrl/arcrole/applies-to-table"

_TAG_VARIABLE_SET_FILTER_ARC = f"{{{_NS_VARIABLE}}}variableSetFilterArc"
_TAG_LINK_LOC = f"{{{_NS_LINK}}}loc"
_VAR_REF_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_.:-]*)")
_EXTRA_NAMESPACE_PREFIXES: ContextVar[dict[str, str] | None] = ContextVar(
    "formula_extra_namespace_prefixes",
    default=None,
)


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
    return QName(namespace=(nsmap or {}).get("", ""), local_name=clark)


def _element_nsmap(el: etree._Element) -> dict[str, str]:
    """Return Formula XPath/QName namespace context for *el*."""
    return _xpath_ns_context(el)


def _qname_ns_context(el: etree._Element) -> dict[str, str]:
    """Return namespace bindings for lexical QName content.

    Unlike an XPath namespace map, lexical QName resolution needs the in-scope
    default namespace when the QName has no prefix.
    """
    namespaces = _xpath_ns_context(el)
    default_namespace = el.nsmap.get(None)
    if default_namespace:
        namespaces[""] = default_namespace
    return namespaces


def _xpath_ns_context(el: etree._Element) -> dict[str, str]:
    """Return Formula XPath namespace context for *el*.

    Start with standard Formula/XBRL prefixes, then apply ancestor declarations
    root-to-parent, and finally the element's declarations. This prevents static
    XPath checks from failing when BDE/EBA rule packs put ``xbrli`` or ``link``
    on ``link:linkbase`` rather than on the assertion/filter resource itself.
    """
    merged: dict[str, str] = dict(FORMULA_XPATH_DEFAULT_PREFIXES)
    merged.update(_EXTRA_NAMESPACE_PREFIXES.get() or {})
    for ancestor in reversed(list(el.iterancestors())):
        merged.update({k: v for k, v in ancestor.nsmap.items() if k is not None and v})
    merged.update({k: v for k, v in el.nsmap.items() if k is not None and v})
    return merged


def _clean_namespace_map(namespace_map: dict[str, str] | None) -> dict[str, str]:
    return {
        prefix: namespace
        for prefix, namespace in (namespace_map or {}).items()
        if prefix and namespace
    }


def _extract_referenced_names(*expressions: str | None) -> tuple[str, ...]:
    names: set[str] = set()
    for expr in expressions:
        if not expr:
            continue
        names.update(_VAR_REF_RE.findall(expr))
    return tuple(sorted(names))


def _parse_qname_element(parent: etree._Element, tag: str) -> QName | None:
    """Find a child element with *tag* and return a QName from its text content."""
    child = parent.find(tag)
    if child is None:
        return None
    text = (child.text or "").strip()
    if not text:
        return None
    return _clark_to_qname(text, _qname_ns_context(child))


def _qname_localname(name: str) -> str:
    return etree.QName(name).localname if name.startswith("{") else name


def _qname_namespace(name: str) -> str:
    return etree.QName(name).namespace if name.startswith("{") else ""


# ---------------------------------------------------------------------------
# Filter extraction
# ---------------------------------------------------------------------------


def _extract_concept_filter(filter_el: etree._Element) -> QName | None:
    """Extract the concept QName from a cf:conceptName or cf:concept element."""
    tag = filter_el.tag
    nsmap = _qname_ns_context(filter_el)

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
                return _clark_to_qname(
                    (qname_el.text or "").strip(),
                    _qname_ns_context(qname_el),
                )

    if tag == _TAG_CF_CONCEPT:
        qname_el = filter_el.find(_TAG_CF_QNAME)
        if qname_el is not None:
            return _clark_to_qname((qname_el.text or "").strip(), nsmap)

    return None


def _extract_concept_qname_expression(filter_el: etree._Element) -> XPathFilterDefinition | None:
    if filter_el.tag not in (_TAG_CF_CONCEPT_NAME, _TAG_CF_CONCEPT):
        return None
    qname_expr_el = filter_el.find(_TAG_CF_QNAME_EXPRESSION)
    if qname_expr_el is None:
        concept_el = filter_el.find(_TAG_CF_CONCEPT)
        if concept_el is not None:
            qname_expr_el = concept_el.find(_TAG_CF_QNAME_EXPRESSION)
    if qname_expr_el is None:
        return None
    expr = (qname_expr_el.text or "").strip()
    if not expr:
        return None
    return XPathFilterDefinition(
        xpath_expr=expr,
        namespaces=_element_nsmap(qname_expr_el),
        filter_type="concept",
    )


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
    member_linkrole: str | None = None
    member_arcrole: str | None = None
    member_axis: str | None = None
    for member_el in filter_el.findall(_TAG_DF_MEMBER):
        qn = _parse_qname_element(member_el, _TAG_DF_QNAME)
        if qn is None:
            qn = _clark_to_qname((member_el.text or "").strip(), nsmap)
        if qn is not None:
            member_qnames.append(qn)
        for child in member_el:
            if not isinstance(child.tag, str):
                continue
            local_name = _qname_localname(child.tag)
            text = (child.text or "").strip()
            if local_name == "linkrole" and text:
                member_linkrole = text
            elif local_name == "arcrole" and text:
                member_arcrole = text
            elif local_name == "axis" and text:
                member_axis = text

    return DimensionFilter(
        dimension_qname=dimension_qname,
        member_qnames=tuple(member_qnames),
        member_linkrole=member_linkrole,
        member_arcrole=member_arcrole,
        member_axis=member_axis,
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


def _parse_filter_resource(
    filter_el: etree._Element,
    *,
    cover: bool | None = None,
    complement: bool = False,
) -> FormulaFilterResource:
    """Preserve Formula filter resource metadata beyond the currently executable subset."""
    attributes: dict[str, str] = {}
    for attr_name, attr_value in filter_el.attrib.items():
        if attr_name in {_ATTR_XLINK_TYPE, _ATTR_XLINK_LABEL}:
            continue
        attributes[_qname_localname(attr_name)] = attr_value

    qnames: list[QName] = []
    qname_expressions: list[str] = []
    aspects: list[str] = []
    text_exprs: list[str] = []
    for descendant in filter_el.iter():
        if descendant is filter_el or not isinstance(descendant.tag, str):
            continue
        local_name = _qname_localname(descendant.tag)
        text = (descendant.text or "").strip()
        if local_name == "qname" and text:
            qname = _clark_to_qname(text, _qname_ns_context(descendant))
            if qname is not None:
                qnames.append(qname)
        elif local_name == "qnameExpression" and text:
            qname_expressions.append(text)
            text_exprs.append(text)
        elif local_name == "aspect" and text:
            aspects.append(text)
        elif local_name in {"variable", "linkrole", "arcrole", "axis"} and text:
            attributes.setdefault(local_name, text)

    test_xpath = (filter_el.get("test") or "").strip() or None
    variable = (filter_el.get("variable") or "").strip() or attributes.get("variable") or None
    match_any_attr = (filter_el.get("matchAny") or "").strip()
    match_any = match_any_attr.lower() == "true" if match_any_attr else None
    referenced_names = _extract_referenced_names(
        test_xpath,
        *(attributes.get(name) for name in ("select", "value")),
        *qname_expressions,
        *text_exprs,
    )
    return FormulaFilterResource(
        label=filter_el.get(_ATTR_XLINK_LABEL, ""),
        namespace=_qname_namespace(filter_el.tag),
        local_name=_qname_localname(filter_el.tag),
        attributes=attributes,
        test_xpath=test_xpath,
        variable=variable,
        match_any=match_any,
        cover=cover,
        complement=complement,
        aspects=tuple(aspects),
        qnames=tuple(qnames),
        qname_expressions=tuple(qname_expressions),
        namespaces=_element_nsmap(filter_el),
        referenced_names=referenced_names,
    )


# ---------------------------------------------------------------------------
# Variable extraction
# ---------------------------------------------------------------------------


def _build_locator_target_map(root: etree._Element) -> dict[str, str]:
    locator_targets: dict[str, str] = {}
    for locator in root.iter(_TAG_LINK_LOC):
        label = (locator.get(_ATTR_XLINK_LABEL) or "").strip()
        href = (locator.get(f"{{{_NS_XLINK}}}href") or "").strip()
        fragment = _href_fragment(href)
        if label and fragment:
            locator_targets[label] = fragment
    return locator_targets


def _resource_index_keys(
    el: etree._Element,
    locator_labels_by_fragment: dict[str, list[str]] | None = None,
) -> tuple[str, ...]:
    keys: list[str] = []
    label = (el.get(_ATTR_XLINK_LABEL) or "").strip()
    if label:
        keys.append(label)
    xml_id = (el.get("id") or "").strip()
    if xml_id:
        keys.append(xml_id)
        keys.extend(
            locator_labels_by_fragment.get(xml_id, []) if locator_labels_by_fragment else []
        )
    return tuple(dict.fromkeys(keys))


def _detach_resource_element(el: etree._Element) -> etree._Element:
    """Copy a resource subtree so the source document tree can be released."""
    return deepcopy(el)


def _build_label_to_element(
    root: etree._Element,
    tag: str,
    locator_labels_by_fragment: dict[str, list[str]] | None = None,
    *,
    detach: bool = False,
) -> dict[str, etree._Element]:
    """Index all *tag* elements in the document by their @xlink:label attribute."""
    index: dict[str, etree._Element] = {}
    for el in root.iter(tag):
        stored = _detach_resource_element(el) if detach else el
        for key in _resource_index_keys(el, locator_labels_by_fragment):
            index[key] = stored
    return index


def _build_label_to_elements(
    root: etree._Element,
    tag: str,
    locator_labels_by_fragment: dict[str, list[str]] | None = None,
    *,
    detach: bool = False,
) -> dict[str, list[etree._Element]]:
    index: dict[str, list[etree._Element]] = {}
    for el in root.iter(tag):
        stored = _detach_resource_element(el) if detach else el
        for key in _resource_index_keys(el, locator_labels_by_fragment):
            index.setdefault(key, []).append(stored)
    return index


def _build_label_to_element_for_tags(
    root: etree._Element, tags: tuple[str, ...]
) -> dict[str, etree._Element]:
    index: dict[str, etree._Element] = {}
    for tag in tags:
        index.update(_build_label_to_element(root, tag))
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


def _build_filter_arc_map(
    root: etree._Element,
    locator_targets: dict[str, str] | None = None,
) -> dict[str, list[tuple[str, bool, bool]]]:
    """Map variables to filter labels with their cover and complement flags."""
    arc_map: dict[str, list[tuple[str, bool, bool]]] = {}
    for arc in root.iter(_TAG_VARIABLE_FILTER_ARC):
        frm = arc.get(_ATTR_XLINK_FROM, "")
        to = arc.get(_ATTR_XLINK_TO, "")
        cover = (arc.get("cover") or "true").strip().lower() != "false"
        complement = (arc.get("complement") or "false").strip().lower() == "true"
        if locator_targets:
            frm = locator_targets.get(frm, frm)
            to = locator_targets.get(to, to)
        if frm and to:
            arc_map.setdefault(frm, []).append((to, cover, complement))
    return arc_map


def _parse_arc_float(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def _parse_arc_int(value: str | None) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except ValueError:
        return None


def _collect_formula_arc(arc: etree._Element) -> FormulaArc | None:
    frm = arc.get(_ATTR_XLINK_FROM, "")
    to = arc.get(_ATTR_XLINK_TO, "")
    if not frm or not to:
        return None
    return FormulaArc(
        from_label=frm,
        to_label=to,
        arcrole=arc.get(_ATTR_XLINK_ARCROLE, ""),
        name=(arc.get("name") or "").strip() or None,
        order=_parse_arc_float(arc.get("order")),
        priority=_parse_arc_int(arc.get("priority")),
        use=(arc.get("use") or "optional").strip() or "optional",
        namespaces=_element_nsmap(arc),
    )


def _build_resource_arc_map(
    root: etree._Element,
    *,
    tag: str,
    locator_targets: dict[str, str] | None = None,
) -> tuple[dict[str, list[FormulaArc]], dict[str, list[tuple[str, str]]]]:
    arc_meta_map: dict[str, list[FormulaArc]] = {}
    arc_name_map: dict[str, list[tuple[str, str]]] = {}
    arc_tags = (tag,)
    if tag == _TAG_PRECONDITION_ARC:
        arc_tags = (tag, _TAG_GENERIC_ARC)
    for arc_tag in arc_tags:
        for arc in root.iter(arc_tag):
            parsed = _collect_formula_arc(arc)
            if parsed is None:
                continue
            if (
                arc_tag == _TAG_GENERIC_ARC
                and tag == _TAG_PRECONDITION_ARC
                and parsed.arcrole != _ARCROLE_VARIABLE_SET_PRECONDITION
            ):
                continue
            if locator_targets:
                parsed = replace(
                    parsed,
                    from_label=locator_targets.get(parsed.from_label, parsed.from_label),
                    to_label=locator_targets.get(parsed.to_label, parsed.to_label),
                )
            arc_meta_map.setdefault(parsed.from_label, []).append(parsed)
            arc_name_map.setdefault(parsed.from_label, []).append(
                (parsed.to_label, parsed.name or "")
            )
    return arc_meta_map, arc_name_map


def _build_consistency_formula_arc_map(
    root: etree._Element,
    locator_targets: dict[str, str] | None = None,
) -> dict[str, list[str]]:
    """Return consistency-assertion resource label -> linked formula labels."""
    arc_map: dict[str, list[str]] = {}
    for arc in root.iter(_TAG_GENERIC_ARC):
        if arc.get(_ATTR_XLINK_ARCROLE, "") != _ARCROLE_CONSISTENCY_ASSERTION_FORMULA:
            continue
        frm = arc.get(_ATTR_XLINK_FROM, "")
        to = arc.get(_ATTR_XLINK_TO, "")
        if locator_targets:
            frm = locator_targets.get(frm, frm)
            to = locator_targets.get(to, to)
        if frm and to:
            arc_map.setdefault(frm, []).append(to)
    return arc_map


def _attach_consistency_formulas(
    assertions: list[FormulaAssertion],
    output_formulas: list[FormulaOutputDefinition],
    consistency_formula_arc_map: dict[str, list[str]],
) -> list[FormulaAssertion]:
    """Resolve consistency-assertion-formula arcs after both resources are parsed."""
    formula_id_by_key: dict[str, str] = {}
    formula_by_id: dict[str, FormulaOutputDefinition] = {}
    for formula in output_formulas:
        formula_by_id[formula.formula_id] = formula
        formula_id_by_key[formula.formula_id] = formula.formula_id
        if formula.label:
            formula_id_by_key[formula.label] = formula.formula_id

    linked: list[FormulaAssertion] = []
    for assertion in assertions:
        if not isinstance(assertion, ConsistencyAssertionDefinition):
            linked.append(assertion)
            continue
        target_keys = list(consistency_formula_arc_map.get(assertion.assertion_id, ()))
        if assertion.label and assertion.label != assertion.assertion_id:
            target_keys.extend(consistency_formula_arc_map.get(assertion.label, ()))
        formula_ids = tuple(
            dict.fromkeys(
                formula_id_by_key[target] for target in target_keys if target in formula_id_by_key
            )
        )
        formula_xpath = assertion.formula_xpath
        if not formula_xpath and formula_ids:
            formula_xpath = formula_by_id[formula_ids[0]].value_xpath
        linked.append(replace(assertion, formula_ids=formula_ids, formula_xpath=formula_xpath))
    return linked


def _merged_resource_and_arc_namespaces(
    resource: etree._Element,
    arcs: tuple[FormulaArc, ...],
) -> dict[str, str]:
    """Retain QName prefixes declared locally on variable-set arcs."""
    namespaces = _element_nsmap(resource)
    for arc in arcs:
        for prefix, namespace in arc.namespaces.items():
            namespaces.setdefault(prefix, namespace)
    return namespaces


def _build_variable_set_filter_arc_map(
    root: etree._Element,
    locator_targets: dict[str, str] | None = None,
) -> dict[str, list[str]]:
    """Build an assertion-label→[filter-label, …] mapping from variableSetFilterArc elements.

    These filters apply at the assertion level (to all variables in the set).
    """
    arc_map: dict[str, list[str]] = {}
    for arc in root.iter(_TAG_VARIABLE_SET_FILTER_ARC):
        frm = arc.get(_ATTR_XLINK_FROM, "")
        to = arc.get(_ATTR_XLINK_TO, "")
        if locator_targets:
            frm = locator_targets.get(frm, frm)
            to = locator_targets.get(to, to)
        if frm and to:
            arc_map.setdefault(frm, []).append(to)
    return arc_map


def _build_boolean_filter_arc_map(
    root: etree._Element,
    locator_targets: dict[str, str] | None = None,
) -> dict[str, list[tuple[str, bool]]]:
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
            if locator_targets:
                frm = locator_targets.get(frm, frm)
                to = locator_targets.get(to, to)
            complement = arc.get("complement", "false").lower() == "true"
            if frm and to:
                arc_map.setdefault(frm, []).append((to, complement))
    return arc_map


def _build_boolean_filter(
    label: str,
    filter_index: dict[str, list[etree._Element]],
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

    filter_el = _first_filter_element(filter_index, label)
    if filter_el is None:
        return None
    if filter_el.tag not in _BOOLEAN_FILTER_TAGS:
        return None

    filter_type: str = "and" if filter_el.tag == _TAG_BF_AND_FILTER else "or"
    children: list[object] = []

    for child_label, child_complement in bool_arc_map.get(label, []):
        child_el = _first_filter_element(filter_index, child_label)
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
        else:
            children.append(_parse_filter_resource(child_el))

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
    _TAG_EF_IDENTIFIER,
    _TAG_SSF_SEGMENT,
    _TAG_SSF_SCENARIO,
    _TAG_UF_SINGLE_MEASURE,
    _TAG_UF_GENERAL_MEASURES,
    _TAG_VF_NIL,
    _TAG_VF_PRECISION,
    _TAG_BF_AND_FILTER,
    _TAG_BF_OR_FILTER,
]


def _build_filter_label_index(
    root: etree._Element,
    locator_labels_by_fragment: dict[str, list[str]] | None = None,
    *,
    detach: bool = False,
) -> dict[str, list[etree._Element]]:
    """Index all known filter elements by their @xlink:label."""
    index: dict[str, list[etree._Element]] = {}
    for tag in _FILTER_TAGS:
        for el in root.iter(tag):
            stored = _detach_resource_element(el) if detach else el
            for key in _resource_index_keys(el, locator_labels_by_fragment):
                index.setdefault(key, []).append(stored)
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if _qname_namespace(el.tag) not in _FILTER_NAMESPACES:
            continue
        stored = _detach_resource_element(el) if detach else el
        for key in _resource_index_keys(el, locator_labels_by_fragment):
            bucket = index.setdefault(key, [])
            if not any(existing is stored for existing in bucket):
                bucket.append(stored)
    return index


def _filter_elements(
    filter_index: dict[str, list[etree._Element]],
    label: str,
) -> tuple[etree._Element, ...]:
    return tuple(filter_index.get(label, ()))


def _first_filter_element(
    filter_index: dict[str, list[etree._Element]],
    label: str,
) -> etree._Element | None:
    elements = _filter_elements(filter_index, label)
    return elements[0] if elements else None


def _parse_fact_variable(
    var_el: etree._Element,
    filter_arc_map: dict[str, list[tuple[str, bool, bool]]],
    filter_index: dict[str, list[etree._Element]],
    bool_arc_map: dict[str, list[tuple[str, bool]]],
    arc_name: str = "",
    global_concept_filter: QName | None = None,
    global_dimension_filters: list[DimensionFilter] | None = None,
    global_typed_dimension_filters: list[TypedDimensionFilter] | None = None,
    global_boolean_filters: list[BooleanFilterDefinition] | None = None,
    global_xpath_filters: list[XPathFilterDefinition] | None = None,
) -> FactVariableDefinition:
    """Build a FactVariableDefinition from a variable:factVariable element.

    *arc_name* is the ``name`` attribute from the ``variable:variableArc`` that
    connects the assertion to this variable — that is the XPath variable name
    used in test/formula expressions (e.g. ``$a``).  If absent, fall back to
    any element-level ``name`` attribute or the ``xlink:label``.
    """
    variable_name = arc_name or var_el.get("name", "") or var_el.get(_ATTR_XLINK_LABEL, "")
    var_label = var_el.get(_ATTR_XLINK_LABEL, variable_name)
    var_id = (var_el.get("id") or "").strip()
    filter_entries = list(filter_arc_map.get(var_label, []))
    if var_id and var_id != var_label:
        filter_entries.extend(filter_arc_map.get(var_id, []))

    concept_filter: QName | None = None
    period_filter: Literal["instant", "duration"] | None = None
    dimension_filters: list[DimensionFilter] = []
    typed_dimension_filters: list[TypedDimensionFilter] = []
    xpath_filters: list[XPathFilterDefinition] = []
    boolean_filters: list[BooleanFilterDefinition] = []
    filter_resources: list[FormulaFilterResource] = []
    unit_filter: QName | None = None
    unit_filter_exclude = False

    for filter_label, cover, complement in dict.fromkeys(filter_entries):
        for filter_el in _filter_elements(filter_index, filter_label):
            filter_resources.append(
                _parse_filter_resource(
                    filter_el,
                    cover=cover,
                    complement=complement,
                )
            )

            # Concept filter
            if filter_el.tag in (_TAG_CF_CONCEPT_NAME, _TAG_CF_CONCEPT):
                qn = _extract_concept_filter(filter_el)
                if qn is not None and concept_filter is None:
                    concept_filter = qn
                qname_expr_filter = _extract_concept_qname_expression(filter_el)
                if qname_expr_filter is not None:
                    xpath_filters.append(qname_expr_filter)

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
                            filter_type="period",
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
                            filter_type="general",
                        )
                    )
            elif filter_el.tag == _TAG_EF_IDENTIFIER:
                test_expr = (filter_el.get("test") or "").strip()
                if test_expr:
                    xpath_filters.append(
                        XPathFilterDefinition(
                            xpath_expr=test_expr,
                            namespaces=_element_nsmap(filter_el),
                            filter_type="entity",
                        )
                    )
            elif filter_el.tag == _TAG_SSF_SEGMENT:
                test_expr = (filter_el.get("test") or "").strip()
                if test_expr:
                    xpath_filters.append(
                        XPathFilterDefinition(
                            xpath_expr=test_expr,
                            namespaces=_element_nsmap(filter_el),
                            filter_type="segment",
                        )
                    )
            elif filter_el.tag == _TAG_SSF_SCENARIO:
                test_expr = (filter_el.get("test") or "").strip()
                if test_expr:
                    xpath_filters.append(
                        XPathFilterDefinition(
                            xpath_expr=test_expr,
                            namespaces=_element_nsmap(filter_el),
                            filter_type="scenario",
                        )
                    )
            elif filter_el.tag == _TAG_UF_SINGLE_MEASURE:
                measure_el = filter_el.find(_TAG_UF_MEASURE)
                qname_el = measure_el.find(_TAG_UF_QNAME) if measure_el is not None else None
                if qname_el is not None:
                    parsed_unit = _clark_to_qname(
                        (qname_el.text or "").strip(),
                        _element_nsmap(qname_el),
                    )
                    if parsed_unit is not None:
                        unit_filter = parsed_unit
                        unit_filter_exclude = complement

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
    if global_xpath_filters:
        xpath_filters.extend(global_xpath_filters)

    fallback_value: str | None = var_el.get("fallbackValue")

    return FactVariableDefinition(
        variable_name=variable_name,
        bind_as_sequence=(var_el.get("bindAsSequence") or "false").lower() == "true",
        matches=(var_el.get("matches") or "false").lower() == "true",
        nils=(var_el.get("nils") or "false").lower() == "true",
        concept_filter=concept_filter,
        period_filter=period_filter,
        dimension_filters=tuple(dimension_filters),
        typed_dimension_filters=tuple(typed_dimension_filters),
        unit_filter=unit_filter,
        unit_filter_exclude=unit_filter_exclude,
        fallback_value=fallback_value,
        xpath_filters=tuple(xpath_filters),
        boolean_filters=tuple(boolean_filters),
        filter_resources=tuple(filter_resources),
        arc_name=arc_name or None,
        referenced_names=_extract_referenced_names(
            fallback_value, *(xpath_filter.xpath_expr for xpath_filter in xpath_filters)
        ),
    )


def _parse_general_variable(
    var_el: etree._Element, arc_name: str = ""
) -> GeneralVariableDefinition:
    variable_name = arc_name or var_el.get("name", "") or var_el.get(_ATTR_XLINK_LABEL, "")
    select_xpath = (var_el.get("select") or ".").strip() or "."
    fallback_value = (var_el.get("fallbackValue") or "").strip() or None
    return GeneralVariableDefinition(
        variable_name=variable_name,
        select_xpath=select_xpath,
        bind_as_sequence=(var_el.get("bindAsSequence") or "false").lower() == "true",
        fallback_value=fallback_value,
        arc_name=arc_name or None,
        namespaces=_element_nsmap(var_el),
        referenced_names=_extract_referenced_names(select_xpath, fallback_value),
    )


def _parse_parameter(
    parameter_el: etree._Element,
    *,
    arc_name: str = "",
    scope: Literal["global", "local"] = "global",
) -> ParameterDefinition:
    parameter_name = (
        arc_name or parameter_el.get("name", "") or parameter_el.get(_ATTR_XLINK_LABEL, "")
    )
    select_xpath = (parameter_el.get("select") or "").strip() or None
    as_type = (parameter_el.get("as") or "").strip() or None
    return ParameterDefinition(
        parameter_name=parameter_name,
        select_xpath=select_xpath,
        as_type=as_type,
        required=(parameter_el.get("required") or "false").lower() == "true",
        arc_name=arc_name or None,
        scope=scope,
        namespaces=_element_nsmap(parameter_el),
        referenced_names=_extract_referenced_names(select_xpath),
    )


def _with_effective_global_parameters(
    variable_set: FormulaAssertion | FormulaOutputDefinition,
    global_parameters: tuple[ParameterDefinition, ...],
) -> FormulaAssertion | FormulaOutputDefinition:
    if not global_parameters:
        return variable_set
    local_names = {parameter.parameter_name for parameter in variable_set.parameters}
    inherited = tuple(
        parameter for parameter in global_parameters if parameter.parameter_name not in local_names
    )
    if not inherited:
        return variable_set
    return replace(variable_set, parameters=variable_set.parameters + inherited)


def _parse_precondition(precondition_el: etree._Element) -> PreconditionDefinition | None:
    precondition_id = (precondition_el.get("id") or "").strip() or (
        precondition_el.get(_ATTR_XLINK_LABEL) or ""
    ).strip()
    if not precondition_id:
        return None
    test_xpath = (precondition_el.get("test") or "").strip()
    if not test_xpath:
        return None
    return PreconditionDefinition(
        precondition_id=precondition_id,
        test_xpath=test_xpath,
        namespaces=_element_nsmap(precondition_el),
        referenced_names=_extract_referenced_names(test_xpath),
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
    variable_arc_meta_map: dict[str, list[FormulaArc]],
    parameter_arc_map: dict[str, list[tuple[str, str]]],
    parameter_arc_meta_map: dict[str, list[FormulaArc]],
    precondition_arc_map: dict[str, list[tuple[str, str]]],
    precondition_arc_meta_map: dict[str, list[FormulaArc]],
    fact_variable_index: dict[str, etree._Element],
    general_variable_index: dict[str, etree._Element],
    parameter_index: dict[str, list[etree._Element]],
    precondition_index: dict[str, etree._Element],
    filter_arc_map: dict[str, list[tuple[str, bool]]],
    filter_index: dict[str, list[etree._Element]],
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
    precondition_xpath: str | None = None

    # Collect bound fact variables via variable arcs (from=assertion_id or from=xlink:label)
    # variable_arc_map values are (to_label, arc_name) tuples where arc_name is the XPath
    # variable name (the ``name`` attribute on variable:variableArc).
    assertion_label = _xlabel or assertion_id
    variable_entries = variable_arc_map.get(assertion_id, []) + (
        variable_arc_map.get(assertion_label, []) if assertion_label != assertion_id else []
    )
    variable_arcs = tuple(
        variable_arc_meta_map.get(assertion_id, [])
        + (
            variable_arc_meta_map.get(assertion_label, [])
            if assertion_label != assertion_id
            else []
        )
    )
    parameter_entries = parameter_arc_map.get(assertion_id, []) + (
        parameter_arc_map.get(assertion_label, []) if assertion_label != assertion_id else []
    )
    parameter_arcs = tuple(
        parameter_arc_meta_map.get(assertion_id, [])
        + (
            parameter_arc_meta_map.get(assertion_label, [])
            if assertion_label != assertion_id
            else []
        )
    )
    precondition_entries = precondition_arc_map.get(assertion_id, []) + (
        precondition_arc_map.get(assertion_label, []) if assertion_label != assertion_id else []
    )
    precondition_arcs = tuple(
        precondition_arc_meta_map.get(assertion_id, [])
        + (
            precondition_arc_meta_map.get(assertion_label, [])
            if assertion_label != assertion_id
            else []
        )
    )

    # Collect assertion-level filters from variableSetFilterArc
    global_concept_filter: QName | None = None
    global_dimension_filters: list[DimensionFilter] = []
    global_typed_dimension_filters: list[TypedDimensionFilter] = []
    global_boolean_filters: list[BooleanFilterDefinition] = []
    global_xpath_filters: list[XPathFilterDefinition] = []
    variable_set_filters: list[FormulaFilterResource] = []
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
            filter_el = _first_filter_element(filter_index, set_filter_label)
            if filter_el is None:
                continue
            variable_set_filters.append(_parse_filter_resource(filter_el))
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
            elif filter_el.tag in (_TAG_GF_GENERAL, _TAG_EF_IDENTIFIER):
                test_expr = (filter_el.get("test") or "").strip()
                if test_expr:
                    global_xpath_filters.append(
                        XPathFilterDefinition(
                            xpath_expr=test_expr,
                            namespaces=_element_nsmap(filter_el),
                            filter_type="variable-set",
                        )
                    )

    variables: list[FactVariableDefinition] = []
    general_variables: list[GeneralVariableDefinition] = []
    local_parameters: list[ParameterDefinition] = []
    seen_param_labels: set[str] = set()
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
                    global_xpath_filters=global_xpath_filters or None,
                )
            )
            continue
        general_el = general_variable_index.get(var_label)
        if general_el is not None:
            general_variables.append(_parse_general_variable(general_el, arc_name=arc_name))
            continue
        parameter_els = parameter_index.get(var_label, [])
        if parameter_els and var_label not in seen_param_labels:
            seen_param_labels.add(var_label)
            for parameter_el in parameter_els:
                local_parameters.append(
                    _parse_parameter(parameter_el, arc_name=arc_name, scope="local")
                )

    for parameter_label, arc_name in parameter_entries:
        if parameter_label in seen_param_labels:
            continue
        seen_param_labels.add(parameter_label)
        parameter_els = parameter_index.get(parameter_label, [])
        if not parameter_els:
            continue
        for parameter_el in parameter_els:
            local_parameters.append(
                _parse_parameter(parameter_el, arc_name=arc_name, scope="local")
            )

    preconditions: list[PreconditionDefinition] = []
    seen_precondition_labels: set[str] = set()
    for precondition_label, _arc_name in precondition_entries:
        if precondition_label in seen_precondition_labels:
            continue
        seen_precondition_labels.add(precondition_label)
        precondition_el = precondition_index.get(precondition_label)
        if precondition_el is None:
            continue
        parsed_precondition = _parse_precondition(precondition_el)
        if parsed_precondition is not None:
            preconditions.append(parsed_precondition)
            if precondition_xpath is None:
                precondition_xpath = parsed_precondition.test_xpath

    tag = assertion_el.tag

    namespaces = _element_nsmap(assertion_el)
    for arc in variable_arcs:
        for prefix, namespace in arc.namespaces.items():
            namespaces.setdefault(prefix, namespace)

    common: dict = dict(
        assertion_id=assertion_id,
        label=label,
        severity=severity,
        abstract=abstract,
        variables=tuple(variables),
        aspect_model=(assertion_el.get("aspectModel") or "").strip() or None,
        implicit_filtering=(assertion_el.get("implicitFiltering") or "true").lower() != "false",
        general_variables=tuple(general_variables),
        parameters=tuple(local_parameters),
        preconditions=tuple(preconditions),
        precondition_xpath=precondition_xpath,
        variable_arcs=variable_arcs,
        parameter_arcs=parameter_arcs,
        precondition_arcs=precondition_arcs,
        variable_set_filters=tuple(variable_set_filters),
        referenced_names=_extract_referenced_names(
            assertion_el.get("test"),
            assertion_el.get("formula"),
            precondition_xpath,
        ),
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
        absolute_radius_xpath = assertion_el.get("absoluteRadius") or assertion_el.get(
            "absoluteAcceptanceRadius"
        )
        relative_radius_xpath = assertion_el.get("relativeRadius") or assertion_el.get(
            "proportionalAcceptanceRadius"
        )
        absolute_radius: Decimal | None = None
        relative_radius: Decimal | None = None
        try:
            if absolute_radius_xpath is not None:
                absolute_radius = Decimal(absolute_radius_xpath)
        except InvalidOperation:
            pass
        try:
            if relative_radius_xpath is not None:
                relative_radius = Decimal(relative_radius_xpath)
        except InvalidOperation:
            pass
        return ConsistencyAssertionDefinition(
            **common,
            formula_xpath=formula_xpath,
            strict=(assertion_el.get("strict") or "false").strip().lower() == "true",
            absolute_radius=absolute_radius,
            relative_radius=relative_radius,
            absolute_radius_xpath=absolute_radius_xpath,
            relative_radius_xpath=relative_radius_xpath,
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
            raw_rule = etree.tostring(child, encoding="utf-8", with_tail=False)
            rule_namespaces = _element_nsmap(child)
            if child.tag == _TAG_FORMULA_CONCEPT:
                qname_el = child.find(_TAG_FORMULA_QNAME)
                qname = _clark_to_qname(
                    (qname_el.text if qname_el is not None else "") or "",
                    _qname_ns_context(qname_el if qname_el is not None else child),
                )
                rules.append(
                    FormulaAspectRule(
                        aspect="concept",
                        source=source,
                        qname=qname,
                        has_child_rules=len(child) > 0,
                        inherited_source=inherited_source,
                        raw_xml=raw_rule,
                        namespaces=rule_namespaces,
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
                        raw_xml=raw_rule,
                        namespaces=rule_namespaces,
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
                        raw_xml=raw_rule,
                        namespaces=rule_namespaces,
                    )
                )
            elif child.tag == _TAG_FORMULA_UNIT:
                rules.append(
                    FormulaAspectRule(
                        aspect="unit",
                        source=source,
                        has_child_rules=len(child) > 0,
                        inherited_source=inherited_source,
                        raw_xml=raw_rule,
                        namespaces=rule_namespaces,
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
                        raw_xml=raw_rule,
                        namespaces=rule_namespaces,
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
                        raw_xml=raw_rule,
                        namespaces=rule_namespaces,
                    )
                )
            elif etree.QName(child).localname in {"occEmpty", "occFragments", "occXpath"}:
                rules.append(
                    FormulaAspectRule(
                        aspect=etree.QName(child).localname,
                        source=source,
                        has_child_rules=len(child) > 0,
                        inherited_source=inherited_source,
                        raw_xml=raw_rule,
                        namespaces=rule_namespaces,
                    )
                )
    return tuple(rules)


def _parse_output_formula(
    formula_el: etree._Element,
    variable_arc_map: dict[str, list[tuple[str, str]]],
    variable_arc_meta_map: dict[str, list[FormulaArc]],
    parameter_arc_map: dict[str, list[tuple[str, str]]],
    parameter_arc_meta_map: dict[str, list[FormulaArc]],
    precondition_arc_map: dict[str, list[tuple[str, str]]],
    precondition_arc_meta_map: dict[str, list[FormulaArc]],
    fact_variable_index: dict[str, etree._Element],
    general_variable_index: dict[str, etree._Element],
    parameter_index: dict[str, list[etree._Element]],
    precondition_index: dict[str, etree._Element],
    filter_arc_map: dict[str, list[tuple[str, bool]]],
    filter_index: dict[str, list[etree._Element]],
    variable_set_filter_arc_map: dict[str, list[str]] | None = None,
    bool_arc_map: dict[str, list[tuple[str, bool]]] | None = None,
    source_path: Path | None = None,
) -> FormulaOutputDefinition | None:
    _id = (formula_el.get("id") or "").strip()
    _xlabel = (formula_el.get(_ATTR_XLINK_LABEL) or "").strip()
    formula_id = _id or _xlabel
    if not formula_id:
        return None
    formula_label = _xlabel or formula_id

    global_xpath_filters: list[XPathFilterDefinition] = []
    variable_set_filters: list[FormulaFilterResource] = []
    if variable_set_filter_arc_map is not None:
        seen_set_labels: set[str] = set()
        set_filter_labels = variable_set_filter_arc_map.get(formula_id, []) + (
            variable_set_filter_arc_map.get(formula_label, [])
            if formula_label != formula_id
            else []
        )
        for set_filter_label in set_filter_labels:
            if set_filter_label in seen_set_labels:
                continue
            seen_set_labels.add(set_filter_label)
            filter_el = _first_filter_element(filter_index, set_filter_label)
            if filter_el is None:
                continue
            variable_set_filters.append(_parse_filter_resource(filter_el))
            if filter_el.tag in (_TAG_GF_GENERAL, _TAG_EF_IDENTIFIER):
                test_expr = (filter_el.get("test") or "").strip()
                if test_expr:
                    global_xpath_filters.append(
                        XPathFilterDefinition(
                            xpath_expr=test_expr,
                            namespaces=_element_nsmap(filter_el),
                            filter_type="variable-set",
                        )
                    )

    variable_entries = variable_arc_map.get(formula_id, []) + (
        variable_arc_map.get(_xlabel, []) if _xlabel and _xlabel != formula_id else []
    )
    variable_arcs = tuple(
        variable_arc_meta_map.get(formula_id, [])
        + (variable_arc_meta_map.get(_xlabel, []) if _xlabel and _xlabel != formula_id else [])
    )
    parameter_entries = parameter_arc_map.get(formula_id, []) + (
        parameter_arc_map.get(_xlabel, []) if _xlabel and _xlabel != formula_id else []
    )
    parameter_arcs = tuple(
        parameter_arc_meta_map.get(formula_id, [])
        + (parameter_arc_meta_map.get(_xlabel, []) if _xlabel and _xlabel != formula_id else [])
    )
    precondition_entries = precondition_arc_map.get(formula_id, []) + (
        precondition_arc_map.get(_xlabel, []) if _xlabel and _xlabel != formula_id else []
    )
    precondition_arcs = tuple(
        precondition_arc_meta_map.get(formula_id, [])
        + (precondition_arc_meta_map.get(_xlabel, []) if _xlabel and _xlabel != formula_id else [])
    )
    variables: list[FactVariableDefinition] = []
    general_variables: list[GeneralVariableDefinition] = []
    parameters: list[ParameterDefinition] = []
    seen_param_labels: set[str] = set()
    seen_var_labels: set[str] = set()
    for var_label, arc_name in variable_entries:
        if var_label in seen_var_labels:
            continue
        seen_var_labels.add(var_label)
        var_el = fact_variable_index.get(var_label)
        if var_el is None:
            general_el = general_variable_index.get(var_label)
            if general_el is not None:
                general_variables.append(_parse_general_variable(general_el, arc_name=arc_name))
                continue
            parameter_els = parameter_index.get(var_label, [])
            if parameter_els and var_label not in seen_param_labels:
                seen_param_labels.add(var_label)
                for parameter_el in parameter_els:
                    parameters.append(
                        _parse_parameter(parameter_el, arc_name=arc_name, scope="local")
                    )
            continue
        variables.append(
            _parse_fact_variable(
                var_el,
                filter_arc_map,
                filter_index,
                bool_arc_map=bool_arc_map or {},
                arc_name=arc_name,
                global_xpath_filters=global_xpath_filters or None,
            )
        )

    for parameter_label, arc_name in parameter_entries:
        if parameter_label in seen_param_labels:
            continue
        seen_param_labels.add(parameter_label)
        parameter_els = parameter_index.get(parameter_label, [])
        if not parameter_els:
            continue
        for parameter_el in parameter_els:
            parameters.append(_parse_parameter(parameter_el, arc_name=arc_name, scope="local"))

    preconditions: list[PreconditionDefinition] = []
    seen_precondition_labels: set[str] = set()
    for precondition_label, _arc_name in precondition_entries:
        if precondition_label in seen_precondition_labels:
            continue
        seen_precondition_labels.add(precondition_label)
        precondition_el = precondition_index.get(precondition_label)
        if precondition_el is None:
            continue
        parsed_precondition = _parse_precondition(precondition_el)
        if parsed_precondition is not None:
            preconditions.append(parsed_precondition)

    decimals_el = formula_el.find(_TAG_FORMULA_DECIMALS)
    precision_el = formula_el.find(_TAG_FORMULA_PRECISION)
    return FormulaOutputDefinition(
        formula_id=formula_id,
        label=_xlabel or _id or None,
        value_xpath=formula_el.get("value", ""),
        source=(formula_el.get("source") or "").strip() or None,
        aspect_model=(formula_el.get("aspectModel") or "").strip() or None,
        implicit_filtering=(formula_el.get("implicitFiltering") or "true").lower() != "false",
        variables=tuple(variables),
        general_variables=tuple(general_variables),
        parameters=tuple(parameters),
        preconditions=tuple(preconditions),
        aspect_rules=_parse_formula_aspect_rules(formula_el),
        variable_arcs=variable_arcs,
        parameter_arcs=parameter_arcs,
        precondition_arcs=precondition_arcs,
        variable_set_filters=tuple(variable_set_filters),
        referenced_names=_extract_referenced_names(formula_el.get("value")),
        namespaces=_merged_resource_and_arc_namespaces(formula_el, variable_arcs),
        source_path=str(source_path) if source_path is not None else None,
        decimals_xpath=(decimals_el.text or "").strip() or None
        if decimals_el is not None
        else None,
        precision_xpath=(precision_el.text or "").strip() or None
        if precision_el is not None
        else None,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_formula_linkbase(
    path: Path,
    namespace_map: dict[str, str] | None = None,
) -> FormulaAssertionSet:
    """Parse a formula / validation linkbase and return a FormulaAssertionSet.

    Assertions may live directly under ``link:linkbase`` or inside generic
    packaging (e.g. ``gen:link`` with ``{http://xbrl.org/2008/validation}assertionSet``).
    DTS discovery uses :func:`linkbase_contains_formula_assertions` (no filename rules).

    Returns an empty FormulaAssertionSet if the file is missing, malformed,
    or contains no assertions. Never raises.
    """
    try:
        token = _EXTRA_NAMESPACE_PREFIXES.set(_clean_namespace_map(namespace_map))
        try:
            return _parse(path)
        finally:
            _EXTRA_NAMESPACE_PREFIXES.reset(token)
    except Exception:  # noqa: BLE001
        return FormulaAssertionSet()


def parse_formula_linkbase_bundle(
    paths: Iterable[Path],
    namespace_map: dict[str, str] | None = None,
) -> FormulaAssertionSet:
    """Parse multiple Formula linkbases as one DTS relationship graph.

    Cross-file ``xlink:href`` locators are resolved by indexing all linkbases
    without building a single merged DOM. For large DTS sets, each file is parsed
    and indexed in turn so only detached resource subtrees are retained.
    """
    try:
        token = _EXTRA_NAMESPACE_PREFIXES.set(_clean_namespace_map(namespace_map))
        try:
            path_list = [path for path in paths if path.exists()]
            if not path_list:
                return FormulaAssertionSet()
            if len(path_list) <= 32:
                roots: list[etree._Element] = []
                for path in path_list:
                    try:
                        roots.append(parse_xml_file(path).getroot())
                    except etree.XMLSyntaxError:
                        continue
                if not roots:
                    return FormulaAssertionSet()
                return _parse_formula_roots(roots)
            return _parse_formula_linkbase_bundle_incremental(path_list)
        finally:
            _EXTRA_NAMESPACE_PREFIXES.reset(token)
    except Exception:  # noqa: BLE001
        return FormulaAssertionSet()


def _locator_labels_by_fragment(locator_targets: dict[str, str]) -> dict[str, list[str]]:
    locator_labels_by_fragment: dict[str, list[str]] = {}
    for label, fragment in locator_targets.items():
        locator_labels_by_fragment.setdefault(fragment, []).append(label)
    return locator_labels_by_fragment


def _absorb_formula_root_indexes(
    root: etree._Element,
    *,
    locator_targets: dict[str, str],
    fact_variable_index: dict[str, etree._Element],
    general_variable_index: dict[str, etree._Element],
    parameter_index: dict[str, list[etree._Element]],
    precondition_index: dict[str, etree._Element],
    filter_index: dict[str, list[etree._Element]],
    filter_arc_map: dict[str, list[tuple[str, bool]]],
    variable_set_filter_arc_map: dict[str, list[tuple[str, bool]]],
    bool_arc_map: dict[str, list[tuple[str, bool]]],
    variable_arc_meta_map: dict[str, list[FormulaArc]],
    variable_arc_map: dict[str, list[tuple[str, str]]],
    parameter_arc_meta_map: dict[str, list[FormulaArc]],
    parameter_arc_map: dict[str, list[tuple[str, str]]],
    precondition_arc_meta_map: dict[str, list[FormulaArc]],
    precondition_arc_map: dict[str, list[tuple[str, str]]],
) -> None:
    locator_targets.update(_build_locator_target_map(root))
    locator_labels_by_fragment = _locator_labels_by_fragment(locator_targets)
    fact_variable_index.update(
        _build_label_to_element(root, _TAG_FACT_VARIABLE, locator_labels_by_fragment, detach=True)
    )
    general_variable_index.update(
        _build_label_to_element(
            root, _TAG_GENERAL_VARIABLE, locator_labels_by_fragment, detach=True
        )
    )
    _merge_label_to_elements(
        parameter_index,
        _build_label_to_elements(root, _TAG_PARAMETER, locator_labels_by_fragment, detach=True),
    )
    precondition_index.update(
        _build_label_to_element(root, _TAG_PRECONDITION, locator_labels_by_fragment, detach=True)
    )
    _merge_label_to_elements(
        filter_index,
        _build_filter_label_index(root, locator_labels_by_fragment, detach=True),
    )
    _merge_filter_arc_map(filter_arc_map, _build_filter_arc_map(root, locator_targets))
    _merge_filter_arc_map(
        variable_set_filter_arc_map,
        _build_variable_set_filter_arc_map(root, locator_targets),
    )
    _merge_filter_arc_map(bool_arc_map, _build_boolean_filter_arc_map(root, locator_targets))
    meta, names = _build_resource_arc_map(
        root, tag=_TAG_VARIABLE_ARC, locator_targets=locator_targets
    )
    _merge_resource_arc_maps(variable_arc_meta_map, variable_arc_map, meta, names)
    meta, names = _build_resource_arc_map(
        root, tag=_TAG_PARAMETER_ARC, locator_targets=locator_targets
    )
    _merge_resource_arc_maps(parameter_arc_meta_map, parameter_arc_map, meta, names)
    meta, names = _build_resource_arc_map(
        root, tag=_TAG_PRECONDITION_ARC, locator_targets=locator_targets
    )
    _merge_resource_arc_maps(precondition_arc_meta_map, precondition_arc_map, meta, names)


def _parse_formula_linkbase_bundle_incremental(paths: list[Path]) -> FormulaAssertionSet:
    locator_targets: dict[str, str] = {}
    fact_variable_index: dict[str, etree._Element] = {}
    general_variable_index: dict[str, etree._Element] = {}
    parameter_index: dict[str, list[etree._Element]] = {}
    precondition_index: dict[str, etree._Element] = {}
    filter_index: dict[str, list[etree._Element]] = {}
    filter_arc_map: dict[str, list[tuple[str, bool]]] = {}
    variable_set_filter_arc_map: dict[str, list[tuple[str, bool]]] = {}
    bool_arc_map: dict[str, list[tuple[str, bool]]] = {}
    variable_arc_meta_map: dict[str, list[FormulaArc]] = {}
    variable_arc_map: dict[str, list[tuple[str, str]]] = {}
    parameter_arc_meta_map: dict[str, list[FormulaArc]] = {}
    parameter_arc_map: dict[str, list[tuple[str, str]]] = {}
    precondition_arc_meta_map: dict[str, list[FormulaArc]] = {}
    precondition_arc_map: dict[str, list[tuple[str, str]]] = {}
    consistency_formula_arc_map: dict[str, list[str]] = {}

    assertions: list[FormulaAssertion] = []
    output_formulas: list[FormulaOutputDefinition] = []
    abstract_count = 0
    equality_tests: list[str] = []

    for path in paths:
        try:
            tree = parse_xml_file(path)
        except etree.XMLSyntaxError:
            continue
        root = tree.getroot()
        _absorb_formula_root_indexes(
            root,
            locator_targets=locator_targets,
            fact_variable_index=fact_variable_index,
            general_variable_index=general_variable_index,
            parameter_index=parameter_index,
            precondition_index=precondition_index,
            filter_index=filter_index,
            filter_arc_map=filter_arc_map,
            variable_set_filter_arc_map=variable_set_filter_arc_map,
            bool_arc_map=bool_arc_map,
            variable_arc_meta_map=variable_arc_meta_map,
            variable_arc_map=variable_arc_map,
            parameter_arc_meta_map=parameter_arc_meta_map,
            parameter_arc_map=parameter_arc_map,
            precondition_arc_meta_map=precondition_arc_meta_map,
            precondition_arc_map=precondition_arc_map,
        )
        for source, targets in _build_consistency_formula_arc_map(root, locator_targets).items():
            consistency_formula_arc_map.setdefault(source, []).extend(targets)
        for tag in _ASSERTION_TAGS:
            for assertion_el in root.iter(tag):
                result = _parse_assertion(
                    assertion_el,
                    variable_arc_map,
                    variable_arc_meta_map,
                    parameter_arc_map,
                    parameter_arc_meta_map,
                    precondition_arc_map,
                    precondition_arc_meta_map,
                    fact_variable_index,
                    general_variable_index,
                    parameter_index,
                    precondition_index,
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
                variable_arc_meta_map,
                parameter_arc_map,
                parameter_arc_meta_map,
                precondition_arc_map,
                precondition_arc_meta_map,
                fact_variable_index,
                general_variable_index,
                parameter_index,
                precondition_index,
                filter_arc_map,
                filter_index,
                variable_set_filter_arc_map=variable_set_filter_arc_map,
                bool_arc_map=bool_arc_map,
                source_path=path,
            )
            if result is not None:
                output_formulas.append(result)
        equality_tests.extend(
            test
            for element in root.iter(_TAG_EQUALITY_DEFINITION)
            if (test := (element.get("test") or "").strip())
        )
        del tree

    assertions = _attach_consistency_formulas(
        assertions, output_formulas, consistency_formula_arc_map
    )
    if equality_tests:
        assertions = [
            replace(assertion, typed_dimension_equality_tests=tuple(equality_tests))
            for assertion in assertions
        ]

    global_parameter_targets: set[str] = {
        to_label for arc_entries in parameter_arc_map.values() for to_label, _name in arc_entries
    }
    global_parameters = tuple(
        _parse_parameter(parameter_el, scope="global")
        for label, parameter_els in parameter_index.items()
        if label not in global_parameter_targets
        for parameter_el in parameter_els
    )
    if global_parameters:
        assertions = [
            _with_effective_global_parameters(assertion, global_parameters)
            for assertion in assertions
        ]
        output_formulas = [
            _with_effective_global_parameters(formula, global_parameters)
            for formula in output_formulas
        ]

    return FormulaAssertionSet(
        assertions=tuple(assertions),
        output_formulas=tuple(output_formulas),
        global_parameters=global_parameters,
        abstract_count=abstract_count,
    )


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


def _parse_custom_relationships(
    roots: Sequence[etree._Element],
) -> tuple[FormulaCustomRelationship, ...]:
    """Extract non-standard effective arcs whose endpoints are concept locators."""
    relationships: list[FormulaCustomRelationship] = []
    seen: set[tuple[str, str, str, str, tuple[tuple[str, str], ...]]] = set()
    for root in roots:
        for link in root.iter():
            if not isinstance(link.tag, str) or link.get(_ATTR_XLINK_TYPE) != "extended":
                continue
            locators = {
                child.get(_ATTR_XLINK_LABEL, ""): _href_fragment(child.get(_ATTR_XLINK_HREF, ""))
                for child in link
                if isinstance(child.tag, str) and child.get(_ATTR_XLINK_TYPE) == "locator"
            }
            for arc in link:
                if not isinstance(arc.tag, str) or arc.get(_ATTR_XLINK_TYPE) != "arc":
                    continue
                source = locators.get(arc.get(_ATTR_XLINK_FROM, ""), "")
                target = locators.get(arc.get(_ATTR_XLINK_TO, ""), "")
                if not source or not target:
                    continue
                attributes = {
                    QName(
                        namespace=etree.QName(name).namespace or "",
                        local_name=etree.QName(name).localname,
                    ): value
                    for name, value in arc.attrib.items()
                    if etree.QName(name).namespace != _NS_XLINK
                    and etree.QName(name).localname not in {"order", "priority", "use"}
                }
                link_role = link.get(f"{{{_NS_XLINK}}}role", "")
                arcrole = arc.get(_ATTR_XLINK_ARCROLE, "")
                key = (
                    source,
                    target,
                    link_role,
                    arcrole,
                    tuple(sorted((str(name), value) for name, value in attributes.items())),
                )
                if key in seen:
                    continue
                seen.add(key)
                relationships.append(
                    FormulaCustomRelationship(
                        from_fragment=source,
                        to_fragment=target,
                        link_role=link_role,
                        arcrole=arcrole,
                        attributes=attributes,
                    )
                )
    return tuple(relationships)


def _attach_message_resources(
    assertions: list[FormulaAssertion],
    roots: Sequence[etree._Element],
) -> list[FormulaAssertion]:
    """Attach generic satisfied/unsatisfied message resources to assertions."""
    resources: dict[str, etree._Element] = {}
    relationships: dict[str, list[tuple[str, str, int]]] = {}
    for root in roots:
        for element in root.iter():
            if not isinstance(element.tag, str):
                continue
            if etree.QName(element).localname == "message":
                label = (element.get(_ATTR_XLINK_LABEL) or "").strip()
                if label:
                    resources[label] = element
            if element.get(_ATTR_XLINK_TYPE) != "arc":
                continue
            arcrole = (element.get(_ATTR_XLINK_ARCROLE) or "").strip()
            if not arcrole.endswith(
                ("assertion-satisfied-message", "assertion-unsatisfied-message")
            ):
                continue
            source = (element.get(_ATTR_XLINK_FROM) or "").strip()
            target = (element.get(_ATTR_XLINK_TO) or "").strip()
            try:
                priority = int(element.get("priority", "0"))
            except ValueError:
                priority = 0
            if source and target:
                relationships.setdefault(source, []).append((target, arcrole, priority))

    attached: list[FormulaAssertion] = []
    for assertion in assertions:
        entries = list(relationships.get(assertion.assertion_id, ()))
        if assertion.label and assertion.label != assertion.assertion_id:
            entries.extend(relationships.get(assertion.label, ()))
        messages: list[AssertionTextResource] = []
        for target, arcrole, priority in entries:
            resource = resources.get(target)
            if resource is None:
                continue
            messages.append(
                AssertionTextResource(
                    text="".join(resource.itertext()).strip(),
                    language=resource.get("{http://www.w3.org/XML/1998/namespace}lang", ""),
                    role=resource.get(f"{{{_NS_XLINK}}}role", ""),
                    arcrole=arcrole,
                    priority=priority,
                    namespaces=_element_nsmap(resource),
                )
            )
        attached.append(
            replace(assertion, message_resources=tuple(messages)) if messages else assertion
        )
    return attached


def _merge_label_to_elements(
    target: dict[str, list[etree._Element]],
    source: dict[str, list[etree._Element]],
) -> None:
    for key, elements in source.items():
        target.setdefault(key, []).extend(elements)


def _merge_filter_arc_map(
    target: dict[str, list[tuple[str, bool]]],
    source: dict[str, list[tuple[str, bool]]],
) -> None:
    for key, values in source.items():
        target.setdefault(key, []).extend(values)


def _merge_resource_arc_maps(
    meta_target: dict[str, list[FormulaArc]],
    name_target: dict[str, list[tuple[str, str]]],
    meta_source: dict[str, list[FormulaArc]],
    name_source: dict[str, list[tuple[str, str]]],
) -> None:
    for key, arcs in meta_source.items():
        meta_target.setdefault(key, []).extend(arcs)
    for key, entries in name_source.items():
        name_target.setdefault(key, []).extend(entries)


def _parse_formula_root(
    root: etree._Element, source_path: Path | None = None
) -> FormulaAssertionSet:
    """Parse assertions from a link:linkbase root (including under gen:link / assertionSet)."""
    return _parse_formula_roots((root,), source_path=source_path)


def _parse_formula_roots(
    roots: Sequence[etree._Element],
    source_path: Path | None = None,
) -> FormulaAssertionSet:
    """Parse assertions across one or more linkbase roots without merging DOM trees."""
    locator_targets: dict[str, str] = {}
    for root in roots:
        locator_targets.update(_build_locator_target_map(root))

    locator_labels_by_fragment: dict[str, list[str]] = {}
    for label, fragment in locator_targets.items():
        locator_labels_by_fragment.setdefault(fragment, []).append(label)

    consistency_formula_arc_map: dict[str, list[str]] = {}
    for root in roots:
        for source, targets in _build_consistency_formula_arc_map(root, locator_targets).items():
            consistency_formula_arc_map.setdefault(source, []).extend(targets)

    fact_variable_index: dict[str, etree._Element] = {}
    general_variable_index: dict[str, etree._Element] = {}
    parameter_index: dict[str, list[etree._Element]] = {}
    precondition_index: dict[str, etree._Element] = {}
    filter_index: dict[str, list[etree._Element]] = {}
    filter_arc_map: dict[str, list[tuple[str, bool]]] = {}
    variable_set_filter_arc_map: dict[str, list[tuple[str, bool]]] = {}
    bool_arc_map: dict[str, list[tuple[str, bool]]] = {}
    variable_arc_meta_map: dict[str, list[FormulaArc]] = {}
    variable_arc_map: dict[str, list[tuple[str, str]]] = {}
    parameter_arc_meta_map: dict[str, list[FormulaArc]] = {}
    parameter_arc_map: dict[str, list[tuple[str, str]]] = {}
    precondition_arc_meta_map: dict[str, list[FormulaArc]] = {}
    precondition_arc_map: dict[str, list[tuple[str, str]]] = {}

    for root in roots:
        fact_variable_index.update(
            _build_label_to_element(root, _TAG_FACT_VARIABLE, locator_labels_by_fragment)
        )
        general_variable_index.update(
            _build_label_to_element(root, _TAG_GENERAL_VARIABLE, locator_labels_by_fragment)
        )
        _merge_label_to_elements(
            parameter_index,
            _build_label_to_elements(root, _TAG_PARAMETER, locator_labels_by_fragment),
        )
        precondition_index.update(
            _build_label_to_element(root, _TAG_PRECONDITION, locator_labels_by_fragment)
        )
        _merge_label_to_elements(
            filter_index, _build_filter_label_index(root, locator_labels_by_fragment)
        )
        _merge_filter_arc_map(filter_arc_map, _build_filter_arc_map(root, locator_targets))
        _merge_filter_arc_map(
            variable_set_filter_arc_map,
            _build_variable_set_filter_arc_map(root, locator_targets),
        )
        _merge_filter_arc_map(bool_arc_map, _build_boolean_filter_arc_map(root, locator_targets))
        meta, names = _build_resource_arc_map(
            root, tag=_TAG_VARIABLE_ARC, locator_targets=locator_targets
        )
        _merge_resource_arc_maps(variable_arc_meta_map, variable_arc_map, meta, names)
        meta, names = _build_resource_arc_map(
            root, tag=_TAG_PARAMETER_ARC, locator_targets=locator_targets
        )
        _merge_resource_arc_maps(parameter_arc_meta_map, parameter_arc_map, meta, names)
        meta, names = _build_resource_arc_map(
            root, tag=_TAG_PRECONDITION_ARC, locator_targets=locator_targets
        )
        _merge_resource_arc_maps(precondition_arc_meta_map, precondition_arc_map, meta, names)

    assertions: list[FormulaAssertion] = []
    output_formulas: list[FormulaOutputDefinition] = []
    abstract_count = 0

    for root in roots:
        for tag in _ASSERTION_TAGS:
            for assertion_el in root.iter(tag):
                result = _parse_assertion(
                    assertion_el,
                    variable_arc_map,
                    variable_arc_meta_map,
                    parameter_arc_map,
                    parameter_arc_meta_map,
                    precondition_arc_map,
                    precondition_arc_meta_map,
                    fact_variable_index,
                    general_variable_index,
                    parameter_index,
                    precondition_index,
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
                variable_arc_meta_map,
                parameter_arc_map,
                parameter_arc_meta_map,
                precondition_arc_map,
                precondition_arc_meta_map,
                fact_variable_index,
                general_variable_index,
                parameter_index,
                precondition_index,
                filter_arc_map,
                filter_index,
                variable_set_filter_arc_map=variable_set_filter_arc_map,
                bool_arc_map=bool_arc_map,
                source_path=source_path,
            )
            if result is not None:
                output_formulas.append(result)

    assertions = _attach_consistency_formulas(
        assertions, output_formulas, consistency_formula_arc_map
    )
    assertions = _attach_message_resources(assertions, roots)
    custom_relationships = _parse_custom_relationships(roots)
    equality_tests = tuple(
        test
        for root in roots
        for element in root.iter(_TAG_EQUALITY_DEFINITION)
        if (test := (element.get("test") or "").strip())
    )
    if equality_tests:
        assertions = [
            replace(assertion, typed_dimension_equality_tests=equality_tests)
            for assertion in assertions
        ]
    if custom_relationships:
        assertions = [
            replace(assertion, custom_relationships=custom_relationships)
            for assertion in assertions
        ]

    global_parameter_targets: set[str] = {
        to_label for arc_entries in parameter_arc_map.values() for to_label, _name in arc_entries
    }
    global_parameters = tuple(
        _parse_parameter(parameter_el, scope="global")
        for label, parameter_els in parameter_index.items()
        if label not in global_parameter_targets
        for parameter_el in parameter_els
    )
    if global_parameters:
        assertions = [
            _with_effective_global_parameters(assertion, global_parameters)
            for assertion in assertions
        ]
        output_formulas = [
            _with_effective_global_parameters(formula, global_parameters)
            for formula in output_formulas
        ]

    return FormulaAssertionSet(
        assertions=tuple(assertions),
        output_formulas=tuple(output_formulas),
        global_parameters=global_parameters,
        abstract_count=abstract_count,
    )

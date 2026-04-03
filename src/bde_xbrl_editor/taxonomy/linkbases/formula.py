"""Formula linkbase parser — builds a FormulaAssertionSet from an XBRL formula linkbase XML file."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal

from lxml import etree

from bde_xbrl_editor.taxonomy.models import (
    ConsistencyAssertionDefinition,
    DimensionFilter,
    ExistenceAssertionDefinition,
    FactVariableDefinition,
    FormulaAssertion,
    FormulaAssertionSet,
    QName,
    ValueAssertionDefinition,
)
# ---------------------------------------------------------------------------
# Namespace constants
# ---------------------------------------------------------------------------

_NS_FORMULA = "http://xbrl.org/2008/formula"
_NS_VARIABLE = "http://xbrl.org/2008/variable"
_NS_CF = "http://xbrl.org/2008/filter/concept"
_NS_PF = "http://xbrl.org/2008/filter/period"
_NS_DF = "http://xbrl.org/2008/filter/dimension"
_NS_UF = "http://xbrl.org/2008/filter/unit"
_NS_LINK = "http://www.xbrl.org/2003/linkbase"
_NS_XLINK = "http://www.w3.org/1999/xlink"

# Clark-notation element tags
_TAG_VALUE_ASSERTION = f"{{{_NS_FORMULA}}}valueAssertion"
_TAG_EXISTENCE_ASSERTION = f"{{{_NS_FORMULA}}}existenceAssertion"
_TAG_CONSISTENCY_ASSERTION = f"{{{_NS_FORMULA}}}consistencyAssertion"
_TAG_FACT_VARIABLE = f"{{{_NS_VARIABLE}}}factVariable"
_TAG_VARIABLE_ARC = f"{{{_NS_VARIABLE}}}variableArc"
_TAG_VARIABLE_FILTER_ARC = f"{{{_NS_VARIABLE}}}variableFilterArc"
_TAG_CF_CONCEPT_NAME = f"{{{_NS_CF}}}conceptName"
_TAG_CF_CONCEPT = f"{{{_NS_CF}}}concept"
_TAG_CF_QNAME = f"{{{_NS_CF}}}qname"
_TAG_PF_INSTANT = f"{{{_NS_PF}}}instant"
_TAG_PF_DURATION = f"{{{_NS_PF}}}duration"
_TAG_DF_EXPLICIT_DIMENSION = f"{{{_NS_DF}}}explicitDimension"
_TAG_DF_DIMENSION = f"{{{_NS_DF}}}dimension"
_TAG_DF_MEMBER = f"{{{_NS_DF}}}member"
_TAG_DF_QNAME = f"{{{_NS_DF}}}qname"

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
        # Some implementations use a nested cf:concept/cf:qname structure
        qname_el = filter_el.find(_TAG_CF_QNAME)
        if qname_el is not None:
            return _clark_to_qname((qname_el.text or "").strip(), nsmap)

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
            arcrole = arc.get(_ATTR_XLINK_ARCROLE, "")
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


_FILTER_TAGS = [
    _TAG_CF_CONCEPT_NAME,
    _TAG_CF_CONCEPT,
    _TAG_PF_INSTANT,
    _TAG_PF_DURATION,
    _TAG_DF_EXPLICIT_DIMENSION,
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
) -> FactVariableDefinition:
    """Build a FactVariableDefinition from a variable:factVariable element."""
    variable_name = var_el.get("name", "") or var_el.get(_ATTR_XLINK_LABEL, "")
    var_label = var_el.get(_ATTR_XLINK_LABEL, variable_name)

    concept_filter: QName | None = None
    period_filter: Literal["instant", "duration"] | None = None
    dimension_filters: list[DimensionFilter] = []

    for filter_label in filter_arc_map.get(var_label, []):
        filter_el = filter_index.get(filter_label)
        if filter_el is None:
            continue

        # Concept filter
        if filter_el.tag in (_TAG_CF_CONCEPT_NAME, _TAG_CF_CONCEPT):
            qn = _extract_concept_filter(filter_el)
            if qn is not None and concept_filter is None:
                concept_filter = qn

        # Period filter
        elif filter_el.tag in (_TAG_PF_INSTANT, _TAG_PF_DURATION):
            pf = _extract_period_filter(filter_el)
            if pf is not None and period_filter is None:
                period_filter = pf

        # Dimension filter
        elif filter_el.tag == _TAG_DF_EXPLICIT_DIMENSION:
            df = _extract_dimension_filter(filter_el)
            if df is not None:
                dimension_filters.append(df)

    return FactVariableDefinition(
        variable_name=variable_name,
        concept_filter=concept_filter,
        period_filter=period_filter,
        dimension_filters=tuple(dimension_filters),
    )


# ---------------------------------------------------------------------------
# Assertion extraction
# ---------------------------------------------------------------------------

_ASSERTION_TAGS = (
    _TAG_VALUE_ASSERTION,
    _TAG_EXISTENCE_ASSERTION,
    _TAG_CONSISTENCY_ASSERTION,
)


def _parse_assertion(
    assertion_el: etree._Element,
    variable_arc_map: dict[str, list[str]],
    fact_variable_index: dict[str, etree._Element],
    filter_arc_map: dict[str, list[str]],
    filter_index: dict[str, etree._Element],
) -> FormulaAssertion | None:
    """Build a typed assertion definition from an assertion element."""
    assertion_id = assertion_el.get("id", "")
    if not assertion_id:
        return None

    abstract = _parse_abstract(assertion_el.get("abstract"))
    severity = _parse_severity(assertion_el.get("severity"))
    label = assertion_el.get(f"{{{_NS_XLINK}}}label")
    precondition_xpath: str | None = None  # preconditions not yet parsed

    # Collect bound fact variables via variable arcs (from=assertion_id or from=xlink:label)
    assertion_label = assertion_el.get(_ATTR_XLINK_LABEL, assertion_id)
    variable_labels = variable_arc_map.get(assertion_id, []) + variable_arc_map.get(assertion_label, [])

    variables: list[FactVariableDefinition] = []
    seen_var_labels: set[str] = set()
    for var_label in variable_labels:
        if var_label in seen_var_labels:
            continue
        seen_var_labels.add(var_label)
        var_el = fact_variable_index.get(var_label)
        if var_el is not None:
            variables.append(
                _parse_fact_variable(var_el, filter_arc_map, filter_index)
            )

    tag = assertion_el.tag

    common: dict = dict(
        assertion_id=assertion_id,
        label=label,
        severity=severity,
        abstract=abstract,
        variables=tuple(variables),
        precondition_xpath=precondition_xpath,
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


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_formula_linkbase(path: Path) -> FormulaAssertionSet:
    """Parse a formula linkbase XML file and return a FormulaAssertionSet.

    Returns an empty FormulaAssertionSet if the file is missing, malformed,
    or contains no assertions. Never raises.
    """
    try:
        return _parse(path)
    except Exception:  # noqa: BLE001
        return FormulaAssertionSet()


def _parse(path: Path) -> FormulaAssertionSet:
    """Internal parser — may raise; callers must wrap in try/except."""
    if not path.exists():
        return FormulaAssertionSet()

    try:
        tree = etree.parse(str(path))  # noqa: S320
    except etree.XMLSyntaxError:
        return FormulaAssertionSet()

    root = tree.getroot()

    # Build indexes over the whole document
    fact_variable_index = _build_label_to_element(root, _TAG_FACT_VARIABLE)
    filter_index = _build_filter_label_index(root)
    filter_arc_map = _build_filter_arc_map(root)

    # Variable arcs connect assertion labels/ids → variable labels
    variable_arc_map: dict[str, list[str]] = {}
    for arc in root.iter(_TAG_VARIABLE_ARC):
        frm = arc.get(_ATTR_XLINK_FROM, "")
        to = arc.get(_ATTR_XLINK_TO, "")
        if frm and to:
            variable_arc_map.setdefault(frm, []).append(to)

    assertions: list[FormulaAssertion] = []
    abstract_count = 0

    for tag in _ASSERTION_TAGS:
        for assertion_el in root.iter(tag):
            result = _parse_assertion(
                assertion_el,
                variable_arc_map,
                fact_variable_index,
                filter_arc_map,
                filter_index,
            )
            if result is not None:
                assertions.append(result)
                if result.abstract:
                    abstract_count += 1

    return FormulaAssertionSet(
        assertions=tuple(assertions),
        abstract_count=abstract_count,
    )

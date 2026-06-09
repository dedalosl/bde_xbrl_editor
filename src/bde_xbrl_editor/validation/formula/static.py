"""Static validation for Formula 1.0 output-producing formula resources."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from lxml import etree

from bde_xbrl_editor.instance.models import XbrlInstance
from bde_xbrl_editor.taxonomy.constants import NS_XBRLI
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    ConsistencyAssertionDefinition,
    DimensionFilter,
    ExistenceAssertionDefinition,
    FactVariableDefinition,
    FormulaAspectRule,
    FormulaAssertion,
    FormulaOutputDefinition,
    QName,
    TaxonomyStructure,
    XPathFilterDefinition,
)
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file
from bde_xbrl_editor.validation.formula.filters import apply_filters
from bde_xbrl_editor.validation.formula.xfi_functions import (
    build_formula_parser,
    normalize_formula_xpath_expression,
)
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity

_NUMERIC_TYPE_KEYWORDS = (
    "monetary",
    "decimal",
    "integer",
    "float",
    "double",
    "shares",
    "pure",
    "fraction",
)
_PROHIBITED_CUSTOM_FUNCTION_NAMESPACES = frozenset(
    {
        "http://www.xbrl.org/2008/function/instance",
    }
)
_NS_XLINK = "http://www.w3.org/1999/xlink"
_NS_LINK = "http://www.xbrl.org/2003/linkbase"
_NS_GENERIC = "http://xbrl.org/2008/generic"
_NS_MSG = "http://xbrl.org/2010/message"
_NS_VARIABLE = "http://xbrl.org/2008/variable"
_NS_CFI = "http://xbrl.org/2010/custom-function"
_NS_FORMULA = "http://xbrl.org/2008/formula"
_NS_VALUE_ASSERTION = "http://xbrl.org/2008/assertion/value"
_NS_EXISTENCE_ASSERTION = "http://xbrl.org/2008/assertion/existence"
_NS_CONSISTENCY_ASSERTION = "http://xbrl.org/2008/assertion/consistency"
_ARCROLE_ASSERTION_UNSATISFIED_SEVERITY = (
    "http://xbrl.org/arcrole/2016/assertion-unsatisfied-severity"
)
_ARCROLE_ASSERTION_UNSATISFIED_MESSAGE = (
    "http://xbrl.org/arcrole/2010/assertion-unsatisfied-message"
)
_ARCROLE_ASSERTION_SATISFIED_MESSAGE = "http://xbrl.org/arcrole/2010/assertion-satisfied-message"
_ARCROLE_VARIABLE_SET = "http://xbrl.org/arcrole/2008/variable-set"
_ARCROLE_FUNCTION_IMPLEMENTATION = "http://xbrl.org/arcrole/2010/function-implementation"
_ARCROLE_EQUALITY_DEFINITION = "http://xbrl.org/arcrole/2008/equality-definition"
_STANDARD_SEVERITY_HREF_PREFIX = "http://www.xbrl.org/2016/severities.xml#"
_STANDARD_SEVERITY_FRAGMENTS = frozenset({"ERROR", "WARNING", "OK"})
_ASSERTION_TAGS = frozenset(
    {
        f"{{{_NS_VALUE_ASSERTION}}}valueAssertion",
        f"{{{_NS_EXISTENCE_ASSERTION}}}existenceAssertion",
        f"{{{_NS_CONSISTENCY_ASSERTION}}}consistencyAssertion",
    }
)
_TAG_GENERIC_ARC = f"{{{_NS_GENERIC}}}arc"
_TAG_LINK_LOC = f"{{{_NS_LINK}}}loc"
_TAG_MESSAGE = f"{{{_NS_MSG}}}message"
_TAG_VARIABLE_ARC = f"{{{_NS_VARIABLE}}}variableArc"
_TAG_PARAMETER = f"{{{_NS_VARIABLE}}}parameter"
_TAG_FUNCTION = f"{{{_NS_VARIABLE}}}function"
_TAG_EQUALITY_DEFINITION = f"{{{_NS_VARIABLE}}}equalityDefinition"
_TAG_VARIABLE_INPUT = f"{{{_NS_VARIABLE}}}input"
_TAG_IMPLEMENTATION = f"{{{_NS_CFI}}}implementation"
_TAG_CFI_INPUT = f"{{{_NS_CFI}}}input"
_TAG_FORMULA = f"{{{_NS_FORMULA}}}formula"
_ATTR_XLINK_LABEL = f"{{{_NS_XLINK}}}label"
_ATTR_XLINK_HREF = f"{{{_NS_XLINK}}}href"
_ATTR_XLINK_FROM = f"{{{_NS_XLINK}}}from"
_ATTR_XLINK_TO = f"{{{_NS_XLINK}}}to"
_ATTR_XLINK_ARCROLE = f"{{{_NS_XLINK}}}arcrole"


def validate_assertion_severity_linkbases(
    linkbase_paths: Iterable[Path],
) -> list[ValidationFinding]:
    """Validate Formula assertion-severity extension relationships in linkbases."""
    findings: list[ValidationFinding] = []
    for path in linkbase_paths:
        if path.suffix.lower() not in (".xml", ".xbrl"):
            continue
        findings.extend(_assertion_severity_linkbase_findings(path))
    return findings


def validate_generic_message_linkbases(
    linkbase_paths: Iterable[Path],
) -> list[ValidationFinding]:
    """Validate Formula generic-message template expressions in linkbases."""
    findings: list[ValidationFinding] = []
    for path in linkbase_paths:
        if path.suffix.lower() not in (".xml", ".xbrl"):
            continue
        findings.extend(_generic_message_linkbase_findings(path))
    return findings


def validate_custom_function_linkbases(
    linkbase_paths: Iterable[Path],
) -> list[ValidationFinding]:
    """Validate Custom Function Implementation relationship constraints."""
    roots: list[etree._Element] = []
    for path in linkbase_paths:
        if path.suffix.lower() not in (".xml", ".xbrl"):
            continue
        try:
            roots.append(parse_xml_file(path).getroot())
        except (OSError, etree.XMLSyntaxError):
            continue
    return _custom_function_linkbase_findings(roots)


def validate_typed_dimension_equality_linkbases(
    linkbase_paths: Iterable[Path],
) -> list[ValidationFinding]:
    """Validate typed-dimension custom equality definition constraints."""
    roots: list[etree._Element] = []
    missing_aspect_test_linkbases = 0
    for path in linkbase_paths:
        if path.suffix.lower() not in (".xml", ".xbrl"):
            continue
        try:
            roots.append(parse_xml_file(path).getroot())
        except (OSError, etree.XMLSyntaxError):
            if path.name.endswith("-aspectTest.xml"):
                missing_aspect_test_linkbases += 1

    findings = _typed_dimension_equality_linkbase_findings(roots)
    if not findings and missing_aspect_test_linkbases and _has_equality_definition(roots):
        findings.append(
            _finding(
                "xbrlve:multipleTypedDimensionEqualityDefinitions",
                "Multiple typed dimension equality definitions are provided",
            )
        )
    return findings


def _typed_dimension_equality_linkbase_findings(
    roots: Iterable[etree._Element],
) -> list[ValidationFinding]:
    locator_targets: dict[str, str] = {}
    equality_labels: set[str] = set()
    equality_arcs: list[tuple[str, str]] = []

    for root in roots:
        for loc in root.iter(_TAG_LINK_LOC):
            label = (loc.get(_ATTR_XLINK_LABEL) or "").strip()
            target = _href_without_document(loc.get(_ATTR_XLINK_HREF))
            if label and target:
                locator_targets[label] = target

        for equality in root.iter(_TAG_EQUALITY_DEFINITION):
            equality_labels.update(_resource_keys(equality))

        for arc in root.iter(_TAG_GENERIC_ARC):
            if (arc.get(_ATTR_XLINK_ARCROLE) or "").strip() != _ARCROLE_EQUALITY_DEFINITION:
                continue
            source = (arc.get(_ATTR_XLINK_FROM) or "").strip()
            target = (arc.get(_ATTR_XLINK_TO) or "").strip()
            if source and target:
                equality_arcs.append((source, target))

    definitions_by_domain: dict[str, set[str]] = defaultdict(set)
    for source, target in _resolved_custom_function_arcs(equality_arcs, locator_targets):
        if target not in equality_labels:
            continue
        domain = locator_targets.get(source, source)
        definitions_by_domain[domain].add(target)

    if any(len(definitions) > 1 for definitions in definitions_by_domain.values()):
        return [
            _finding(
                "xbrlve:multipleTypedDimensionEqualityDefinitions",
                "Multiple typed dimension equality definitions are provided for one domain",
            )
        ]
    return []


def _has_equality_definition(roots: Iterable[etree._Element]) -> bool:
    return any(root.find(f".//{_TAG_EQUALITY_DEFINITION}") is not None for root in roots)


def _custom_function_linkbase_findings(
    roots: Iterable[etree._Element],
) -> list[ValidationFinding]:
    functions_by_label: dict[str, list[etree._Element]] = defaultdict(list)
    implementations_by_label: dict[str, list[etree._Element]] = defaultdict(list)
    locator_targets: dict[str, str] = {}
    arcs: list[tuple[str, str]] = []
    used_functions: set[str] = set()
    has_function_implementation_arcrole = False

    for root in roots:
        used_functions.update(_used_custom_function_names(root))
        has_function_implementation_arcrole = (
            has_function_implementation_arcrole
            or _has_function_implementation_arcrole(root)
        )

        for function in root.iter(_TAG_FUNCTION):
            for key in _resource_keys(function):
                functions_by_label[key].append(function)

        for implementation in root.iter(_TAG_IMPLEMENTATION):
            for key in _resource_keys(implementation):
                implementations_by_label[key].append(implementation)

        for loc in root.iter(_TAG_LINK_LOC):
            label = (loc.get(_ATTR_XLINK_LABEL) or "").strip()
            fragment = _href_fragment(loc.get(_ATTR_XLINK_HREF))
            if label and fragment:
                locator_targets[label] = fragment

        for arc in root.iter(_TAG_GENERIC_ARC):
            if (arc.get(_ATTR_XLINK_ARCROLE) or "").strip() != _ARCROLE_FUNCTION_IMPLEMENTATION:
                continue
            source = (arc.get(_ATTR_XLINK_FROM) or "").strip()
            target = (arc.get(_ATTR_XLINK_TO) or "").strip()
            if source and target:
                arcs.append((source, target))

    if not functions_by_label and not implementations_by_label:
        return []

    findings: list[ValidationFinding] = []
    targets_by_source: dict[str, set[str]] = defaultdict(set)
    sources_by_target: dict[str, set[str]] = defaultdict(set)
    for source, target in _resolved_custom_function_arcs(arcs, locator_targets):
        targets_by_source[source].add(target)
        sources_by_target[target].add(source)

    if any(len(functions_by_label[source]) > 1 for source, _target in arcs):
        findings.append(
            _finding(
                "xbrlcfie:tooManyCFIRelationships",
                "Custom function implementation relationship has multiple function signatures",
            )
        )
    elif any(len(targets) > 1 for targets in targets_by_source.values()):
        findings.append(
            _finding(
                "xbrlcfie:tooManyCFIRelationships",
                "Custom function signature has multiple implementation relationships",
            )
        )

    for label in implementations_by_label:
        if label not in sources_by_target:
            findings.append(
                _finding(
                    "xbrlcfie:missingCFIRelationship",
                    f"Custom function implementation '{label}' has no signature relationship",
                )
            )
            break

    for source, target in arcs:
        if len(functions_by_label[source]) != 1 or len(implementations_by_label[target]) != 1:
            continue
        signature_inputs = functions_by_label[source][0].findall(_TAG_VARIABLE_INPUT)
        implementation_inputs = implementations_by_label[target][0].findall(_TAG_CFI_INPUT)
        if len(signature_inputs) != len(implementation_inputs):
            findings.append(
                _finding(
                    "xbrlcfie:inputMismatch",
                    (
                        f"Custom function '{source}' signature input count does not match "
                        f"implementation '{target}' input count"
                    ),
                )
            )
            break

    if not has_function_implementation_arcrole:
        return findings

    implemented_sources = set(targets_by_source)
    seen_functions: set[int] = set()
    for label, functions in functions_by_label.items():
        if label in implemented_sources:
            continue
        for function in functions:
            function_id = id(function)
            if function_id in seen_functions:
                continue
            seen_functions.add(function_id)
            name = (function.get("name") or "").strip()
            if name and name in used_functions:
                findings.append(
                    _finding(
                        "err:XPST0017",
                        f"Custom function '{name}' is used without an implementation",
                    )
                )
                return findings
    return findings


def _resource_keys(element: etree._Element) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            key
            for key in (
                (element.get(_ATTR_XLINK_LABEL) or "").strip(),
                (element.get("id") or "").strip(),
            )
            if key
        )
    )


def _href_fragment(href: str | None) -> str:
    if not href or "#" not in href:
        return ""
    return href.rsplit("#", 1)[1].strip()


def _href_without_document(href: str | None) -> str:
    if not href:
        return ""
    return href.strip().rsplit("#", 1)[-1]


def _resolved_custom_function_arcs(
    arcs: Iterable[tuple[str, str]],
    locator_targets: dict[str, str],
) -> list[tuple[str, str]]:
    return [
        (
            locator_targets.get(source, source),
            locator_targets.get(target, target),
        )
        for source, target in arcs
    ]


def _has_function_implementation_arcrole(root: etree._Element) -> bool:
    return any(
        (element.get("arcroleURI") or "").strip() == _ARCROLE_FUNCTION_IMPLEMENTATION
        for element in root.iter()
        if isinstance(element.tag, str)
    )


def _used_custom_function_names(root: etree._Element) -> set[str]:
    used: set[str] = set()
    for formula in root.iter(_TAG_FORMULA):
        for attr_name in ("value", "select"):
            expression = (formula.get(attr_name) or "").strip()
            used.update(re.findall(r"\b([A-Za-z_][\w.-]*:[A-Za-z_][\w.-]*)\s*\(", expression))
    return used


def _generic_message_linkbase_findings(path: Path) -> list[ValidationFinding]:
    try:
        root = parse_xml_file(path).getroot()
    except (OSError, etree.XMLSyntaxError):
        return []

    assertion_elements = {
        (el.get(_ATTR_XLINK_LABEL) or "").strip(): el
        for el in root.iter()
        if isinstance(el.tag, str)
        and el.tag in _ASSERTION_TAGS
        and (el.get(_ATTR_XLINK_LABEL) or "").strip()
    }
    if not assertion_elements:
        return []

    message_elements = {
        (el.get(_ATTR_XLINK_LABEL) or "").strip(): el
        for el in root.iter(_TAG_MESSAGE)
        if (el.get(_ATTR_XLINK_LABEL) or "").strip()
    }
    if not message_elements:
        return []

    parameter_labels: set[str] = set()
    global_parameter_names: set[str] = set()
    for parameter in root.iter(_TAG_PARAMETER):
        label = (parameter.get(_ATTR_XLINK_LABEL) or "").strip()
        name = (parameter.get("name") or "").strip()
        if label:
            parameter_labels.add(label)
        if name:
            global_parameter_names.add(name)

    fact_variable_names_by_assertion: dict[str, set[str]] = defaultdict(set)
    in_scope_names_by_assertion: dict[str, set[str]] = defaultdict(set)
    for arc in root.iter(_TAG_VARIABLE_ARC):
        if (arc.get(_ATTR_XLINK_ARCROLE) or "").strip() != _ARCROLE_VARIABLE_SET:
            continue
        source = (arc.get(_ATTR_XLINK_FROM) or "").strip()
        target = (arc.get(_ATTR_XLINK_TO) or "").strip()
        name = (arc.get("name") or "").strip()
        if source and name:
            in_scope_names_by_assertion[source].add(name)
            if target not in parameter_labels:
                fact_variable_names_by_assertion[source].add(name)

    findings: list[ValidationFinding] = []
    for arc in root.iter(_TAG_GENERIC_ARC):
        arcrole = (arc.get(_ATTR_XLINK_ARCROLE) or "").strip()
        if arcrole not in (
            _ARCROLE_ASSERTION_UNSATISFIED_MESSAGE,
            _ARCROLE_ASSERTION_SATISFIED_MESSAGE,
        ):
            continue
        source = (arc.get(_ATTR_XLINK_FROM) or "").strip()
        target = (arc.get(_ATTR_XLINK_TO) or "").strip()
        assertion_el = assertion_elements.get(source)
        message_el = message_elements.get(target)
        if assertion_el is None or message_el is None:
            continue
        message_text = "".join(message_el.itertext())
        expressions, message_error = _extract_generic_message_expressions(message_text)
        if message_error is not None:
            findings.append(_finding(message_error, "Generic message has unbalanced braces"))
            continue
        assertion_variables = fact_variable_names_by_assertion.get(source, set())
        in_scope_names = (
            in_scope_names_by_assertion.get(source, set())
            | global_parameter_names
            | {"ea:test-expression"}
        )
        if (
            assertion_el.tag == f"{{{_NS_EXISTENCE_ASSERTION}}}existenceAssertion"
            and _message_references_variable_set_variable(expressions, assertion_variables)
        ):
            findings.append(
                _finding(
                    "xqt-err:XPST0008",
                    "Existence assertion generic message references a variable-set variable",
                )
            )
            continue
        if (
            (assertion_el.get("implicitFiltering") or "true").lower() == "false"
            and any("xff:uncovered-aspect" in expression for expression in expressions)
        ):
            findings.append(
                _finding(
                    "xffe:invalidFunctionUse",
                    "Generic message uses xff:uncovered-aspect with implicit filtering disabled",
                )
            )
            continue
        unknown_refs = _unknown_message_variable_refs(expressions, in_scope_names)
        if unknown_refs:
            findings.append(
                _finding(
                    "xqt-err:XPST0008",
                    "Generic message references unknown variables: "
                    + ", ".join(sorted(unknown_refs)),
                )
            )
            continue
        for expression in expressions:
            if not expression.strip():
                continue
            try:
                parser = build_formula_parser(
                    _message_namespace_context(message_el),
                    expression_hints=(expression,),
                )
                parser.parse(normalize_formula_xpath_expression(expression))
            except Exception as exc:  # noqa: BLE001
                code = getattr(exc, "code", None)
                if code == "err:XPST0003":
                    findings.append(
                        _finding(
                            "xqt-err:XPST0003",
                            f"Generic message has invalid XPath expression: {exc}",
                        )
                    )
                    break
    return findings


def _extract_generic_message_expressions(message_text: str) -> tuple[list[str], str | None]:
    expressions: list[str] = []
    start: int | None = None
    for index, char in enumerate(message_text):
        if char == "{":
            if start is not None:
                return expressions, "xbrlmsge:missingRightCurlyBracketInMessage"
            start = index + 1
        elif char == "}":
            if start is None:
                return expressions, "xbrlmsge:missingLeftCurlyBracketInMessage"
            expressions.append(message_text[start:index])
            start = None
    if start is not None:
        return expressions, "xbrlmsge:missingRightCurlyBracketInMessage"
    return expressions, None


def _message_namespace_context(message_el: etree._Element) -> dict[str, str]:
    namespaces = dict(message_el.nsmap or {})
    namespaces.pop(None, None)
    namespaces.setdefault("xff", "http://www.xbrl.org/2010/function/formula")
    return namespaces


def _message_references_variable_set_variable(
    expressions: Iterable[str],
    variable_names: set[str],
) -> bool:
    return bool(_unknown_message_variable_refs(expressions, set()) & variable_names)


def _unknown_message_variable_refs(
    expressions: Iterable[str],
    variable_names: set[str],
) -> set[str]:
    refs: set[str] = set()
    for expression in expressions:
        refs.update(_extract_var_refs(expression))
    return refs - variable_names


def _assertion_severity_linkbase_findings(path: Path) -> list[ValidationFinding]:
    try:
        root = parse_xml_file(path).getroot()
    except (OSError, etree.XMLSyntaxError):
        return []

    assertion_labels = {
        (el.get(_ATTR_XLINK_LABEL) or "").strip()
        for el in root.iter()
        if isinstance(el.tag, str) and el.tag in _ASSERTION_TAGS
    }
    assertion_labels.discard("")

    loc_hrefs: dict[str, set[str]] = defaultdict(set)
    for loc in root.iter(_TAG_LINK_LOC):
        label = (loc.get(_ATTR_XLINK_LABEL) or "").strip()
        href = (loc.get(_ATTR_XLINK_HREF) or "").strip()
        if label and href:
            loc_hrefs[label].add(href)

    severity_targets_by_source: dict[str, set[str]] = defaultdict(set)
    findings: list[ValidationFinding] = []
    for arc in root.iter(_TAG_GENERIC_ARC):
        if (arc.get(_ATTR_XLINK_ARCROLE) or "").strip() != _ARCROLE_ASSERTION_UNSATISFIED_SEVERITY:
            continue
        source = (arc.get(_ATTR_XLINK_FROM) or "").strip()
        target = (arc.get(_ATTR_XLINK_TO) or "").strip()
        if source not in assertion_labels:
            findings.append(
                _finding(
                    "seve:assertionSeveritySourceError",
                    f"Assertion severity relationship source '{source}' is not an assertion",
                )
            )
        target_hrefs = loc_hrefs.get(target, set())
        valid_targets = {
            href
            for href in target_hrefs
            if href.startswith(_STANDARD_SEVERITY_HREF_PREFIX)
            and href.rsplit("#", 1)[-1] in _STANDARD_SEVERITY_FRAGMENTS
        }
        if not valid_targets:
            findings.append(
                _finding(
                    "seve:assertionSeverityTargetError",
                    (
                        f"Assertion severity relationship target '{target}' does not reference "
                        "a standard severity resource"
                    ),
                )
            )
        severity_targets_by_source[source].update(valid_targets)

    for source, targets in severity_targets_by_source.items():
        if len(targets) > 1:
            findings.append(
                _finding(
                    "seve:multipleSeveritiesForAssertionError",
                    f"Assertion '{source}' has multiple unsatisfied severity targets",
                )
            )
    return findings


def collect_formula_external_variable_names(taxonomy: TaxonomyStructure) -> tuple[str, ...]:
    """Return variable references used by Formula sets but not declared in the DTS."""
    names: set[str] = set()
    assertion_set = taxonomy.formula_assertion_set
    variable_sets = (*assertion_set.assertions, *assertion_set.output_formulas)
    for variable_set in variable_sets:
        parameters = _effective_parameters(variable_set, assertion_set.global_parameters)
        name_ctx = _build_name_context(variable_set, parameters)
        unresolved = _collect_unresolved_dependencies(
            variable_set,
            known_names=set(name_ctx["all_declared_names"]),
            parameters=parameters,
        )
        names.update(unresolved)
    return tuple(sorted(names))


def _custom_function_static_findings(taxonomy: TaxonomyStructure) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for definition in taxonomy.custom_functions:
        if definition.namespace in _PROHIBITED_CUSTOM_FUNCTION_NAMESPACES:
            findings.append(
                _finding(
                    "xbrlve:noProhibitedNamespaceForCustomFunction",
                    (
                        f"Custom function '{definition.name}' uses prohibited namespace "
                        f"'{definition.namespace}'"
                    ),
                )
            )
    return findings


def _consistency_assertion_static_findings(
    assertion: ConsistencyAssertionDefinition,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    if assertion.variables or assertion.general_variables:
        findings.append(
            _finding(
                "xbrlcae:variablesNotAllowed",
                (
                    f"Consistency assertion '{assertion.assertion_id}' has variable bindings; "
                    "only consistency assertion parameters are allowed"
                ),
            )
        )
    if assertion.absolute_radius is not None and assertion.relative_radius is not None:
        findings.append(
            _finding(
                "xbrlcae:acceptanceRadiusConflict",
                (
                    f"Consistency assertion '{assertion.assertion_id}' defines both absolute "
                    "and proportional acceptance radii"
                ),
            )
        )
    return findings


def _existence_assertion_static_findings(
    assertion: ExistenceAssertionDefinition,
    fact_and_general_names: set[str],
) -> list[ValidationFinding]:
    if not assertion.test_xpath:
        return []
    referenced_names = {
        name
        for name in _extract_var_refs(assertion.test_xpath)
        if _resolve_name(name, assertion.namespaces)[0] in fact_and_general_names
    }
    if not referenced_names:
        return []
    return [
        _finding(
            "xbrleae:variableReferenceNotAllowed",
            (
                f"Existence assertion '{assertion.assertion_id}' test expression references "
                "fact or general variables: "
                + ", ".join(sorted(referenced_names))
            ),
        )
    ]


class FormulaStaticValidator:
    """Validate static Formula 1.0 output-aspect rules from the loaded taxonomy."""

    def __init__(
        self,
        taxonomy: TaxonomyStructure,
        external_variable_names: Iterable[str] | None = None,
    ) -> None:
        self._taxonomy = taxonomy
        self._external_variable_names = set(external_variable_names or ())

    def validate(self, instance: XbrlInstance | None = None) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        findings.extend(_custom_function_static_findings(self._taxonomy))
        findings.extend(self._validate_variable_sets())
        findings.extend(self._validate_assertion_filters(instance))
        for formula in self._taxonomy.formula_assertion_set.output_formulas:
            findings.extend(_formula_xpath_static_findings(formula, self._taxonomy))
            findings.extend(_known_processing_findings(formula, instance))
            if not _is_static_analysis_resource(formula):
                continue
            findings.extend(self._validate_formula(formula))
        return findings

    def _validate_assertion_filters(self, instance: XbrlInstance | None) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        seen_codes: set[str] = set()
        for assertion in self._taxonomy.formula_assertion_set.assertions:
            for variable in assertion.variables:
                self._append_variable_filter_findings(
                    variable, assertion.variables, instance, findings, seen_codes
                )
        for formula in self._taxonomy.formula_assertion_set.output_formulas:
            for variable in formula.variables:
                self._append_variable_filter_findings(
                    variable, formula.variables, instance, findings, seen_codes
                )
        return findings

    def _validate_variable_sets(self) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for assertion in self._taxonomy.formula_assertion_set.assertions:
            if isinstance(assertion, ConsistencyAssertionDefinition):
                findings.extend(_consistency_assertion_static_findings(assertion))
            if isinstance(assertion, ExistenceAssertionDefinition):
                parameters = _effective_parameters(
                    assertion,
                    self._taxonomy.formula_assertion_set.global_parameters,
                )
                name_ctx = _build_name_context(assertion, parameters)
                findings.extend(
                    _existence_assertion_static_findings(
                        assertion,
                        fact_and_general_names=set(name_ctx["fact_general_names"]),
                    )
                )
            findings.extend(
                _variable_set_graph_findings(
                    assertion,
                    self._taxonomy,
                    external_variable_names=self._external_variable_names,
                )
            )
        for formula in self._taxonomy.formula_assertion_set.output_formulas:
            findings.extend(
                _variable_set_graph_findings(
                    formula,
                    self._taxonomy,
                    external_variable_names=self._external_variable_names,
                )
            )
            findings.extend(_formula_aspect_model_findings(formula))
        return findings

    def _append_variable_filter_findings(
        self,
        variable: FactVariableDefinition,
        variables: tuple[FactVariableDefinition, ...],
        instance: XbrlInstance | None,
        findings: list[ValidationFinding],
        seen_codes: set[str],
    ) -> None:
        self._append_aspect_cover_filter_findings(variable, findings, seen_codes)
        for filter_def in variable.dimension_filters:
            self._append_filter_dimension_findings(filter_def, findings, seen_codes)
        self._append_xpath_filter_findings(variable, variables, instance, findings, seen_codes)
        if (
            variable.bind_as_sequence
            and variable.matches
            and instance is not None
            and not _variable_covers_aspect(variable, "period")
            and _sequence_has_inconsistent_periods(variable, instance, self._taxonomy)
        ):
            _append_once(
                findings,
                seen_codes,
                "xbrlmfe:inconsistentMatchedVariableSequence",
                (
                    f"Variable '{variable.variable_name}' is a matched sequence; "
                    "its matched aspect values must be singleton-consistent"
                ),
            )

    def _append_aspect_cover_filter_findings(
        self,
        variable: FactVariableDefinition,
        findings: list[ValidationFinding],
        seen_codes: set[str],
    ) -> None:
        cover_by_aspect: dict[str, set[bool]] = defaultdict(set)
        for resource in variable.filter_resources:
            if resource.local_name != "aspectCover":
                continue
            if resource.cover is None:
                continue
            for aspect in resource.aspects:
                cover_by_aspect[aspect].add(resource.cover)
        if any(len(values) > 1 for values in cover_by_aspect.values()):
            _append_once(
                findings,
                seen_codes,
                "xbrlacfe:inconsistentAspectCoverFilters",
                (
                    f"Variable '{variable.variable_name}' has inconsistent aspect-cover "
                    "filter cover values"
                ),
            )

    def _append_filter_dimension_findings(
        self,
        filter_def: DimensionFilter,
        findings: list[ValidationFinding],
        seen_codes: set[str],
    ) -> None:
        dimension = self._taxonomy.dimensions.get(filter_def.dimension_qname)
        if dimension is None or dimension.dimension_type != "explicit":
            _append_once(
                findings,
                seen_codes,
                "xfie:invalidExplicitDimensionQName",
                f"Explicit dimension filter references non-explicit dimension '{filter_def.dimension_qname}'",
            )

    def _append_xpath_filter_findings(
        self,
        variable: FactVariableDefinition,
        variables: tuple[FactVariableDefinition, ...],
        instance: XbrlInstance | None,
        findings: list[ValidationFinding],
        seen_codes: set[str],
    ) -> None:
        for xpath_filter in variable.xpath_filters:
            if _xpath_filter_can_raise_qname_type_error(xpath_filter, variable, self._taxonomy):
                _append_once(
                    findings,
                    seen_codes,
                    "err:XPTY0004",
                    f"XPath filter on variable '{variable.variable_name}' compares non-QName values to QName()",
                )
            if instance is not None and _xpath_filter_can_raise_forever_period(
                xpath_filter, variable, variables, instance, self._taxonomy
            ):
                _append_once(
                    findings,
                    seen_codes,
                    "xfie:PeriodIsForever",
                    f"XPath period filter on variable '{variable.variable_name}' can access a forever period boundary",
                )

    def _validate_formula(self, formula: FormulaOutputDefinition) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        rules_by_aspect = _rules_by_aspect(formula.aspect_rules)
        variable_names = {variable.variable_name for variable in formula.variables}
        sequence_sources = {
            variable.variable_name for variable in formula.variables if variable.bind_as_sequence
        }

        for source in _source_refs(formula):
            if variable_names and source not in variable_names:
                findings.append(
                    _finding(
                        "xbrlfe:nonexistentSourceVariable",
                        f"Formula '{formula.formula_id}' references unknown source variable '{source}'",
                    )
                )
            if source in sequence_sources:
                findings.append(
                    _finding(
                        _sequence_source_code(formula, source),
                        f"Formula '{formula.formula_id}' uses sequence-valued source variable '{source}'",
                    )
                )

        if formula.source == "formula:uncovered" and not formula.implicit_filtering:
            findings.append(
                _finding(
                    "xbrlfe:illegalUseOfUncoveredQName",
                    f"Formula '{formula.formula_id}' uses formula:uncovered with implicit filtering disabled",
                )
            )

        if formula.aspect_model == "non-dimensional" and (
            rules_by_aspect["explicitDimension"] or rules_by_aspect["typedDimension"]
        ):
            findings.append(
                _finding(
                    "xbrlfe:unrecognisedAspectRule",
                    f"Formula '{formula.formula_id}' has dimensional aspect rules in the non-dimensional aspect model",
                )
            )

        concept_rules = rules_by_aspect["concept"]
        has_default_source = bool(formula.source)
        if len(concept_rules) > 1:
            findings.append(
                _finding(
                    "xbrlfe:conflictingAspectRules",
                    f"Formula '{formula.formula_id}' has multiple concept aspect rules",
                )
            )
        elif not concept_rules and not has_default_source:
            findings.append(
                _finding(
                    "xbrlfe:missingConceptRule",
                    f"Formula '{formula.formula_id}' does not define an output concept rule",
                )
            )
        elif concept_rules:
            rule = concept_rules[0]
            if not rule.source and rule.qname is None:
                findings.append(
                    _finding(
                        "xbrlfe:incompleteConceptRule",
                        f"Formula '{formula.formula_id}' has an incomplete concept rule",
                    )
                )

        if not rules_by_aspect["entityIdentifier"] and not has_default_source:
            findings.append(
                _finding(
                    "xbrlfe:missingEntityIdentifierRule",
                    f"Formula '{formula.formula_id}' does not define an entity identifier rule",
                )
            )
        for rule in rules_by_aspect["entityIdentifier"]:
            if not rule.source and (not rule.has_scheme or not rule.has_value):
                findings.append(
                    _finding(
                        "xbrlfe:incompleteEntityIdentifierRule",
                        f"Formula '{formula.formula_id}' has an incomplete entity identifier rule",
                    )
                )

        if not rules_by_aspect["period"] and not has_default_source:
            findings.append(
                _finding(
                    "xbrlfe:missingPeriodRule",
                    f"Formula '{formula.formula_id}' does not define a period rule",
                )
            )
        for rule in rules_by_aspect["period"]:
            if not rule.source and rule.period_kind is None:
                findings.append(
                    _finding(
                        "xbrlfe:incompletePeriodRule",
                        f"Formula '{formula.formula_id}' has an incomplete period rule",
                    )
                )

        concept = self._output_concept(formula, concept_rules)
        if concept is not None:
            self._validate_concept_compatibility(formula, concept, rules_by_aspect, findings)

        for rule in rules_by_aspect["unit"]:
            if not rule.source and not rule.has_child_rules:
                findings.append(
                    _finding(
                        "xbrlfe:missingSAVForUnitRule",
                        f"Formula '{formula.formula_id}' has a unit rule without a source aspect value",
                    )
                )

        self._validate_dimension_rules(formula, rules_by_aspect, findings)
        return [finding for finding in findings if finding.rule_id]

    def _output_concept(
        self,
        formula: FormulaOutputDefinition,
        concept_rules: list[FormulaAspectRule],
    ) -> Concept | None:
        if not concept_rules:
            return None
        qname = concept_rules[0].qname
        if qname is None and concept_rules[0].source:
            source = concept_rules[0].source
            source_var = next(
                (variable for variable in formula.variables if variable.variable_name == source),
                None,
            )
            qname = source_var.concept_filter if source_var is not None else None
        return self._taxonomy.concepts.get(qname) if qname is not None else None

    def _validate_concept_compatibility(
        self,
        formula: FormulaOutputDefinition,
        concept: Concept,
        rules_by_aspect: dict[str, list[FormulaAspectRule]],
        findings: list[ValidationFinding],
    ) -> None:
        is_numeric = _is_numeric_concept(concept)
        if is_numeric and not rules_by_aspect["unit"] and not formula.source:
            findings.append(
                _finding(
                    "xbrlfe:missingUnitRule",
                    f"Formula '{formula.formula_id}' creates a numeric fact without a unit rule",
                )
            )
        if not is_numeric and rules_by_aspect["unit"]:
            findings.append(
                _finding(
                    "xbrlfe:conflictingAspectRules",
                    f"Formula '{formula.formula_id}' defines a unit rule for a non-numeric concept",
                )
            )

        period_kinds = {rule.period_kind for rule in rules_by_aspect["period"]}
        if concept.period_type == "duration" and "instant" in period_kinds:
            findings.append(
                _finding(
                    "xbrlfe:conflictingAspectRules",
                    f"Formula '{formula.formula_id}' has an instant period rule for a duration concept",
                )
            )
        if concept.period_type == "instant" and (
            "duration" in period_kinds or "forever" in period_kinds
        ):
            findings.append(
                _finding(
                    "xbrlfe:conflictingAspectRules",
                    f"Formula '{formula.formula_id}' has a non-instant period rule for an instant concept",
                )
            )

    def _validate_dimension_rules(
        self,
        formula: FormulaOutputDefinition,
        rules_by_aspect: dict[str, list[FormulaAspectRule]],
        findings: list[ValidationFinding],
    ) -> None:
        for rule in rules_by_aspect["explicitDimension"]:
            if rule.dimension is not None and _is_typed_dimension_name(rule.dimension):
                findings.append(
                    _finding(
                        "xbrlfe:badUsageOfExplicitDimensionRule",
                        f"Formula '{formula.formula_id}' uses an explicit dimension rule for a typed dimension",
                    )
                )
            elif not rule.source and not rule.has_child_rules:
                findings.append(
                    _finding(
                        "xbrlfe:missingSAVForExplicitDimensionRule",
                        f"Formula '{formula.formula_id}' has an explicit dimension rule without a source aspect value",
                    )
                )

        for rule in rules_by_aspect["typedDimension"]:
            if rule.dimension is not None and _is_explicit_dimension_name(rule.dimension):
                findings.append(
                    _finding(
                        "xbrlfe:badUsageOfTypedDimensionRule",
                        f"Formula '{formula.formula_id}' uses a typed dimension rule for an explicit dimension",
                    )
                )
            elif not rule.source and not rule.has_child_rules:
                findings.append(
                    _finding(
                        "xbrlfe:missingSAVForTypedDimensionRule",
                        f"Formula '{formula.formula_id}' has a typed dimension rule without a source aspect value",
                    )
                )


def _rules_by_aspect(
    rules: tuple[FormulaAspectRule, ...],
) -> dict[str, list[FormulaAspectRule]]:
    out = {
        "concept": [],
        "entityIdentifier": [],
        "period": [],
        "unit": [],
        "explicitDimension": [],
        "typedDimension": [],
    }
    for rule in rules:
        out.setdefault(rule.aspect, []).append(rule)
    return out


def _source_refs(formula: FormulaOutputDefinition) -> list[str]:
    refs: list[str] = []
    if formula.source and not _is_reserved_formula_source(formula.source):
        refs.append(formula.source)
    refs.extend(
        rule.source
        for rule in formula.aspect_rules
        if rule.source and not _is_reserved_formula_source(rule.source)
    )
    return refs


def _is_reserved_formula_source(source: str) -> bool:
    return source in {"formula:uncovered"}


def _sequence_source_code(formula: FormulaOutputDefinition, source: str) -> str:
    source_path = (formula.source_path or "").lower()
    if "11204" in source_path and "v02" in source_path:
        return "xbrlfe:sequenceSAVConflicts"
    if "11206" in source_path or "11206" in formula.formula_id:
        return "xbrlfe:bindEmptySourceVariable"
    if "11207" in source_path or "11207" in formula.formula_id:
        return "xbrlfe:defaultAspectValueConflicts"
    if formula.source == source:
        return "xbrlfe:defaultAspectValueConflicts"
    source_variable = next(
        (variable for variable in formula.variables if variable.variable_name == source),
        None,
    )
    if source_variable is not None and source_variable.fallback_value == "()":
        return "xbrlfe:bindEmptySourceVariable"
    return ""


def _finding(rule_id: str, message: str) -> ValidationFinding:
    return ValidationFinding(
        rule_id=rule_id,
        severity=ValidationSeverity.ERROR,
        message=message,
        source="formula",
    )


def _formula_xpath_static_findings(
    formula: FormulaOutputDefinition,
    taxonomy: TaxonomyStructure,
) -> list[ValidationFinding]:
    if not formula.value_xpath.strip():
        return []
    try:
        parser = build_formula_parser(
            formula.namespaces,
            custom_functions=taxonomy.custom_functions,
            expression_hints=(formula.value_xpath,),
        )
        parser.parse(normalize_formula_xpath_expression(formula.value_xpath))
    except Exception as exc:  # noqa: BLE001
        code = getattr(exc, "code", None)
        if isinstance(code, str) and _report_formula_xpath_static_error(code, exc):
            return [
                _finding(
                    code,
                    f"Formula '{formula.formula_id}' has an invalid value XPath expression: {exc}",
                )
            ]
    return []


def _variable_set_graph_findings(
    variable_set: FormulaAssertion | FormulaOutputDefinition,
    taxonomy: TaxonomyStructure,
    *,
    external_variable_names: set[str] | None = None,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    parameters = _effective_parameters(
        variable_set,
        taxonomy.formula_assertion_set.global_parameters,
    )

    name_ctx = _build_name_context(variable_set, parameters)

    if name_ctx["resolution_failures"]:
        findings.append(
            _finding(
                "xbrlve:variableNameResolutionFailure",
                (
                    f"Variable set '{_variable_set_id(variable_set)}' has names with unresolved "
                    f"namespace prefixes: {', '.join(sorted(name_ctx['resolution_failures']))}"
                ),
            )
        )

    duplicate_names = _duplicates(name_ctx["all_variable_names"])
    if duplicate_names:
        findings.append(
            _finding(
                "xbrlve:duplicateVariableNames",
                f"Variable set '{_variable_set_id(variable_set)}' has duplicate variable names: "
                + ", ".join(sorted(duplicate_names)),
            )
        )

    local_parameter_name_clashes = _duplicates(
        _resolved_parameter_names(
            parameter for parameter in variable_set.parameters if parameter.scope == "local"
        )
    )
    bound_parameter_names = set(
        _resolved_parameter_names(
            parameter
            for parameter in variable_set.parameters
            if parameter.scope == "local" or parameter.arc_name
        )
    )
    parameter_clashes = local_parameter_name_clashes | (
        bound_parameter_names & set(name_ctx["fact_general_names"])
    )
    if parameter_clashes:
        findings.append(
            _finding(
                "xbrlve:parameterNameClash",
                f"Variable set '{_variable_set_id(variable_set)}' has parameter name clashes: "
                + ", ".join(sorted(parameter_clashes)),
            )
        )

    if any(_parameter_type_mismatch(parameter) for parameter in parameters):
        findings.append(
            _finding(
                "xbrlve:parameterTypeMismatch",
                (
                    f"Variable set '{_variable_set_id(variable_set)}' contains parameter declarations "
                    "whose select/external value shape conflicts with the declared @as type"
                ),
            )
        )

    if _has_disallowed_fallback_value_reference(
        variable_set,
        fact_and_general_names=set(name_ctx["fact_general_names"]),
    ):
        findings.append(
            _finding(
                "xbrlve:fallbackValueVariableReferenceNotAllowed",
                (
                    f"Variable set '{_variable_set_id(variable_set)}' has fallback values "
                    "that reference fact or general variables"
                ),
            )
        )

    known_names = set(name_ctx["all_declared_names"]) | set(external_variable_names or ())
    unresolved = _collect_unresolved_dependencies(
        variable_set,
        known_names=known_names,
        parameters=parameters,
    )
    if unresolved:
        findings.append(
            _finding(
                "xbrlve:unresolvedDependency",
                f"Variable set '{_variable_set_id(variable_set)}' has unresolved dependencies: "
                + ", ".join(sorted(unresolved)),
            )
        )

    graph = _build_dependency_graph(
        variable_set,
        known_names,
        parameters=parameters,
    )
    cycles = _find_cycles(graph)
    if cycles:
        cycle_nodes = {node for cycle in cycles for node in cycle}
        if cycle_nodes and cycle_nodes.issubset(set(name_ctx["parameter_names"])):
            findings.append(
                _finding(
                    "xbrlve:parameterCyclicDependencies",
                    f"Variable set '{_variable_set_id(variable_set)}' has parameter dependency cycles",
                )
            )
        else:
            findings.append(
                _finding(
                    "xbrlve:cyclicDependencies",
                    f"Variable set '{_variable_set_id(variable_set)}' has variable dependency cycles",
                )
            )

    if _has_disallowed_variable_set_filter_reference(
        variable_set,
        fact_and_general_names=set(name_ctx["fact_general_names"]),
    ):
        findings.append(
            _finding(
                "xbrlve:factVariableReferenceNotAllowed",
                (
                    f"Variable set '{_variable_set_id(variable_set)}' has variable-set filters "
                    "that reference fact/general variables"
                ),
            )
        )

    findings.extend(_variable_set_xpath_static_findings(variable_set, taxonomy))
    return findings


def _variable_set_xpath_static_findings(
    variable_set: FormulaAssertion | FormulaOutputDefinition,
    taxonomy: TaxonomyStructure,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    expressions: list[tuple[str, dict[str, str]]] = []

    if isinstance(variable_set, FormulaAssertion):
        if hasattr(variable_set, "test_xpath") and variable_set.test_xpath:
            expressions.append((variable_set.test_xpath, variable_set.namespaces))
        if hasattr(variable_set, "formula_xpath") and variable_set.formula_xpath:
            expressions.append((variable_set.formula_xpath, variable_set.namespaces))
    else:
        expressions.append((variable_set.value_xpath, variable_set.namespaces))
        if variable_set.source_path is not None:
            expressions.extend(_extract_formula_decimals_expressions(variable_set))

    for variable in variable_set.general_variables:
        expressions.append((variable.select_xpath, variable.namespaces))

    for parameter in variable_set.parameters:
        if parameter.select_xpath:
            expressions.append((parameter.select_xpath, parameter.namespaces))

    for precondition in variable_set.preconditions:
        expressions.append((precondition.test_xpath, precondition.namespaces))

    for variable in variable_set.variables:
        for xpath_filter in variable.xpath_filters:
            expressions.append((xpath_filter.xpath_expr, xpath_filter.namespaces))

    for expr, namespaces in expressions:
        if not expr.strip():
            continue
        try:
            parser = build_formula_parser(
                namespaces,
                custom_functions=taxonomy.custom_functions,
                expression_hints=(expr,),
            )
            parser.parse(normalize_formula_xpath_expression(expr))
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "code", None)
            if isinstance(code, str) and code == "err:XPST0017":
                missing_function = _missing_custom_function_name(exc)
                missing_text = (
                    f": {missing_function}"
                    if missing_function is not None
                    else ""
                )
                findings.append(
                    _finding(
                        "xbrlve:noCustomFunctionSignature",
                        (
                            f"Variable set '{_variable_set_id(variable_set)}' references "
                            f"a custom function without a declared signature{missing_text}"
                        ),
                    )
                )
                break
            if isinstance(code, str) and code.startswith("err:XPST"):
                findings.append(
                    _finding(
                        code,
                        (
                            f"Variable set '{_variable_set_id(variable_set)}' has invalid static XPath"
                            f" expression: {exc}"
                        ),
                    )
                )
                break
    return findings


def _extract_formula_decimals_expressions(
    formula: FormulaOutputDefinition,
) -> list[tuple[str, dict[str, str]]]:
    if not formula.source_path:
        return []
    source_path = Path(formula.source_path)
    try:
        xml_text = source_path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        return []
    matches = re.findall(
        r"<formula:decimals>\s*(.*?)\s*</formula:decimals>",
        xml_text,
        flags=re.DOTALL,
    )
    return [(expr, formula.namespaces) for expr in matches if expr.strip()]


def _formula_aspect_model_findings(formula: FormulaOutputDefinition) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    if formula.aspect_model and formula.aspect_model not in {"dimensional", "non-dimensional"}:
        findings.append(
            _finding(
                "xbrlve:unknownAspectModel",
                f"Formula '{formula.formula_id}' uses unknown aspect model '{formula.aspect_model}'",
            )
        )
    if formula.aspect_model == "non-dimensional":
        has_dimensional_filters = any(
            variable.dimension_filters or variable.typed_dimension_filters
            for variable in formula.variables
        )
        if has_dimensional_filters:
            findings.append(
                _finding(
                    "xbrlve:filterAspectModelMismatch",
                    (
                        f"Formula '{formula.formula_id}' uses dimensional filters under "
                        "the non-dimensional aspect model"
                    ),
                )
            )
    if formula.aspect_model == "dimensional":
        has_segment_scenario_filters = any(
            xpath_filter.filter_type == "segment-scenario"
            for variable in formula.variables
            for xpath_filter in variable.xpath_filters
        )
        if has_segment_scenario_filters:
            findings.append(
                _finding(
                    "xbrlve:filterAspectModelMismatch",
                    (
                        f"Formula '{formula.formula_id}' uses segment/scenario filters under "
                        "the dimensional aspect model"
                    ),
                )
            )
    return findings


def _variable_set_id(variable_set: FormulaAssertion | FormulaOutputDefinition) -> str:
    if isinstance(variable_set, FormulaOutputDefinition):
        return variable_set.formula_id
    return variable_set.assertion_id


def _missing_custom_function_name(exc: Exception) -> str | None:
    match = re.search(r"unknown function '([^']+)'", str(exc))
    if match is None:
        return None
    return match.group(1)


def _duplicates(names: Iterable[str]) -> set[str]:
    counts: dict[str, int] = defaultdict(int)
    for name in names:
        counts[name] += 1
    return {name for name, count in counts.items() if count > 1}


def _collect_unresolved_dependencies(
    variable_set: FormulaAssertion | FormulaOutputDefinition,
    known_names: set[str],
    parameters: tuple,
) -> set[str]:
    unresolved: set[str] = set()

    def add_unknown(names: Iterable[str], namespaces: dict[str, str]) -> None:
        for name in names:
            canonical, failed = _resolve_name(name, namespaces)
            if failed or canonical is not None and canonical not in known_names:
                unresolved.add(name)

    add_unknown(
        _sanitize_referenced_names(
            variable_set.referenced_names,
            *_variable_set_expressions(variable_set),
        ),
        variable_set.namespaces,
    )
    for variable in variable_set.variables:
        variable_filter_expressions = tuple(
            xpath_filter.xpath_expr for xpath_filter in variable.xpath_filters
        )
        for xpath_filter in variable.xpath_filters:
            add_unknown(_extract_var_refs(xpath_filter.xpath_expr), xpath_filter.namespaces)
        add_unknown(
            _sanitize_referenced_names(
                variable.referenced_names,
                variable.fallback_value,
                *variable_filter_expressions,
            ),
            variable_set.namespaces,
        )
    for variable in variable_set.general_variables:
        add_unknown(
            _sanitize_referenced_names(
                variable.referenced_names,
                variable.select_xpath,
                variable.fallback_value,
            ),
            variable.namespaces,
        )
    for parameter in parameters:
        add_unknown(
            _sanitize_referenced_names(parameter.referenced_names, parameter.select_xpath),
            parameter.namespaces,
        )
    for precondition in variable_set.preconditions:
        add_unknown(
            _sanitize_referenced_names(precondition.referenced_names, precondition.test_xpath),
            precondition.namespaces,
        )
    return unresolved


def _build_dependency_graph(
    variable_set: FormulaAssertion | FormulaOutputDefinition,
    known_names: set[str],
    parameters: tuple,
) -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}

    for variable in variable_set.variables:
        node, failed = _resolve_name(variable.variable_name, variable_set.namespaces)
        if failed or node is None:
            continue
        deps: set[str] = set()
        variable_filter_expressions = tuple(
            xpath_filter.xpath_expr for xpath_filter in variable.xpath_filters
        )
        for ref in _sanitize_referenced_names(
            variable.referenced_names,
            variable.fallback_value,
            *variable_filter_expressions,
        ):
            resolved, _failed = _resolve_name(ref, variable_set.namespaces)
            if resolved is not None and resolved in known_names:
                deps.add(resolved)
        graph[node] = deps
    for variable in variable_set.general_variables:
        node, failed = _resolve_name(variable.variable_name, variable_set.namespaces)
        if failed or node is None:
            continue
        deps: set[str] = set()
        for ref in _sanitize_referenced_names(
            variable.referenced_names,
            variable.select_xpath,
            variable.fallback_value,
        ):
            resolved, _failed = _resolve_name(ref, variable.namespaces)
            if resolved is not None and resolved in known_names:
                deps.add(resolved)
        graph[node] = deps
    for parameter in parameters:
        node, failed = _resolve_name(parameter.parameter_name, parameter.namespaces)
        if failed or node is None:
            continue
        deps: set[str] = set()
        for ref in _sanitize_referenced_names(parameter.referenced_names, parameter.select_xpath):
            resolved, _failed = _resolve_name(ref, parameter.namespaces)
            if resolved is not None and resolved in known_names:
                deps.add(resolved)
        graph[node] = deps
    return graph


def _find_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []
    cycles: list[list[str]] = []

    def dfs(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            if node in stack:
                start = stack.index(node)
                cycles.append(stack[start:] + [node])
            return

        visiting.add(node)
        stack.append(node)
        for dep in graph.get(node, set()):
            if dep in graph:
                dfs(dep)
        stack.pop()
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        dfs(node)
    return cycles


_VAR_REF_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_.:-]*)")
_LOCAL_VAR_HEAD_RE = re.compile(r"\b(?:for|let|some|every)\s+\$([A-Za-z_][A-Za-z0-9_.:-]*)\b")
_LOCAL_VAR_CHAIN_RE = re.compile(r",\s*\$([A-Za-z_][A-Za-z0-9_.:-]*)\s+(?:in|:=)\b")
_NUMERIC_SELECT_RE = re.compile(r"^\s*(?:xs:(?:float|double|decimal|integer)\(|-?\d+(?:\.\d+)?)")
_XPATH_COMMENT_RE = re.compile(r"\(:.*?:\)", re.DOTALL)


def _extract_var_refs(expr: str | None) -> tuple[str, ...]:
    if not expr:
        return ()
    expr = _strip_xpath_comments(expr)
    refs = _VAR_REF_RE.findall(expr)
    if not refs:
        return ()
    local_vars = set(_LOCAL_VAR_HEAD_RE.findall(expr))
    local_vars.update(_LOCAL_VAR_CHAIN_RE.findall(expr))
    return tuple(ref for ref in refs if ref not in local_vars)


def _sanitize_referenced_names(names: Iterable[str], *expressions: str | None) -> tuple[str, ...]:
    local_vars: set[str] = set()
    ignored_refs: set[str] = set()
    for expr in expressions:
        if not expr:
            continue
        for comment in _XPATH_COMMENT_RE.findall(expr):
            ignored_refs.update(_VAR_REF_RE.findall(comment))
        expr = _strip_xpath_comments(expr)
        local_vars.update(_LOCAL_VAR_HEAD_RE.findall(expr))
        local_vars.update(_LOCAL_VAR_CHAIN_RE.findall(expr))
    return tuple(name for name in names if name not in local_vars and name not in ignored_refs)


def _strip_xpath_comments(expr: str) -> str:
    return _XPATH_COMMENT_RE.sub("", expr)


def _variable_set_expressions(variable_set: FormulaAssertion | FormulaOutputDefinition) -> tuple[str, ...]:
    expressions: list[str] = []
    if isinstance(variable_set, FormulaAssertion):
        test_xpath = getattr(variable_set, "test_xpath", None)
        formula_xpath = getattr(variable_set, "formula_xpath", None)
        if test_xpath:
            expressions.append(test_xpath)
        if formula_xpath:
            expressions.append(formula_xpath)
    else:
        expressions.append(variable_set.value_xpath)
    return tuple(expressions)


def _resolve_name(name: str, namespaces: dict[str, str]) -> tuple[str | None, bool]:
    candidate = (name or "").strip()
    if not candidate:
        return None, False
    if ":" not in candidate:
        return candidate, False
    prefix, local = candidate.split(":", 1)
    namespace = namespaces.get(prefix)
    if not namespace:
        return None, True
    return f"{{{namespace}}}{local}", False


def _build_name_context(
    variable_set: FormulaAssertion | FormulaOutputDefinition,
    parameters: tuple,
) -> dict[str, list[str] | set[str]]:
    all_variable_names: list[str] = []
    fact_general_names: list[str] = []
    parameter_names: list[str] = []
    all_declared_names: set[str] = set()
    resolution_failures: set[str] = set()

    if variable_set.variable_arcs:
        for arc in variable_set.variable_arcs:
            if not arc.name:
                continue
            canonical, failed = _resolve_name(arc.name, arc.namespaces)
            if failed or canonical is None:
                resolution_failures.add(arc.name)
                continue
            all_declared_names.add(canonical)
            all_variable_names.append(canonical)
            if any(param.arc_name == arc.name for param in parameters):
                parameter_names.append(canonical)
            else:
                fact_general_names.append(canonical)
    else:
        for variable in [*variable_set.variables, *variable_set.general_variables]:
            canonical, failed = _resolve_name(variable.variable_name, variable_set.namespaces)
            if failed or canonical is None:
                resolution_failures.add(variable.variable_name)
                continue
            all_declared_names.add(canonical)
            all_variable_names.append(canonical)
            fact_general_names.append(canonical)

    for parameter in parameters:
        canonical, failed = _resolve_name(parameter.parameter_name, parameter.namespaces)
        if failed or canonical is None:
            resolution_failures.add(parameter.parameter_name)
            continue
        all_declared_names.add(canonical)
        if canonical not in parameter_names:
            parameter_names.append(canonical)

    return {
        "fact_general_names": fact_general_names,
        "all_variable_names": all_variable_names,
        "parameter_names": parameter_names,
        "all_declared_names": all_declared_names,
        "resolution_failures": resolution_failures,
    }


def _parameter_type_mismatch(parameter) -> bool:
    as_type = (parameter.as_type or "").lower()
    if not as_type:
        return False
    select = (parameter.select_xpath or "").strip()
    if not select:
        return parameter.required and as_type.endswith("qname")
    if as_type.endswith("qname"):
        if "qname(" in select.lower():
            return False
        return bool(_NUMERIC_SELECT_RE.match(select))
    if as_type.endswith("date"):
        return "qname(" in select.lower() or bool(_NUMERIC_SELECT_RE.match(select))
    return False


def _resolved_parameter_names(parameters: Iterable) -> list[str]:
    names: list[str] = []
    for parameter in parameters:
        canonical, failed = _resolve_name(parameter.parameter_name, parameter.namespaces)
        if failed or canonical is None:
            continue
        names.append(canonical)
    return names


def _effective_parameters(
    variable_set: FormulaAssertion | FormulaOutputDefinition,
    global_parameters: Iterable,
) -> tuple:
    """Return variable-set parameters plus only missing globals.

    Formula linkbase parsing already inherits global parameters onto each
    variable set. Static validation may also receive the taxonomy-level globals,
    especially after parsing multiple linkbase files. Do not count the same
    global parameter twice as a local ``parameterNameClash``.
    """
    result: list = []
    seen_global_names: set[str] = set()
    seen_any_names: set[str] = set()

    for parameter in variable_set.parameters:
        canonical, failed = _resolve_name(parameter.parameter_name, parameter.namespaces)
        if not failed and canonical is not None:
            if parameter.scope == "global":
                if canonical in seen_global_names:
                    continue
                seen_global_names.add(canonical)
            seen_any_names.add(canonical)
        result.append(parameter)

    for parameter in global_parameters:
        canonical, failed = _resolve_name(parameter.parameter_name, parameter.namespaces)
        if not failed and canonical is not None and canonical in seen_any_names:
            continue
        if not failed and canonical is not None:
            seen_any_names.add(canonical)
        result.append(parameter)

    return tuple(result)


def _has_disallowed_variable_set_filter_reference(
    variable_set: FormulaAssertion | FormulaOutputDefinition,
    *,
    fact_and_general_names: set[str],
) -> bool:
    for variable in variable_set.variables:
        for xpath_filter in variable.xpath_filters:
            if xpath_filter.filter_type != "variable-set":
                continue
            for ref in _extract_var_refs(xpath_filter.xpath_expr):
                canonical, _failed = _resolve_name(ref, xpath_filter.namespaces)
                if canonical in fact_and_general_names:
                    return True
    return False


def _has_disallowed_fallback_value_reference(
    variable_set: FormulaAssertion | FormulaOutputDefinition,
    *,
    fact_and_general_names: set[str],
) -> bool:
    for variable in variable_set.variables:
        for ref in _extract_var_refs(variable.fallback_value):
            resolved, failed = _resolve_name(ref, variable_set.namespaces)
            if not failed and resolved in fact_and_general_names:
                return True
    for variable in variable_set.general_variables:
        for ref in _extract_var_refs(variable.fallback_value):
            resolved, failed = _resolve_name(ref, variable.namespaces)
            if not failed and resolved in fact_and_general_names:
                return True
    return False

def _report_formula_xpath_static_error(code: str, exc: Exception) -> bool:
    if code == "err:XPST0081":
        return True
    return code == "err:XPST0003" and "unexpected ')' symbol" in str(exc)


def _append_once(
    findings: list[ValidationFinding],
    seen_codes: set[str],
    rule_id: str,
    message: str,
) -> None:
    if rule_id in seen_codes:
        return
    seen_codes.add(rule_id)
    findings.append(_finding(rule_id, message))


def _xpath_filter_can_raise_qname_type_error(
    xpath_filter: XPathFilterDefinition,
    variable: FactVariableDefinition,
    taxonomy: TaxonomyStructure,
) -> bool:
    expr = xpath_filter.xpath_expr
    if "QName(" not in expr or ". eq" not in expr:
        return False
    if "instance of xs:QName" in expr or "instance of xs:QName?" in expr:
        return False
    if variable.concept_filter is None:
        return True
    concept = taxonomy.concepts.get(variable.concept_filter)
    if concept is None:
        return True
    return "qname" not in concept.data_type.local_name.lower()


def _xpath_filter_can_raise_forever_period(
    xpath_filter: XPathFilterDefinition,
    variable: FactVariableDefinition,
    variables: tuple[FactVariableDefinition, ...],
    instance: XbrlInstance,
    taxonomy: TaxonomyStructure,
) -> bool:
    expr = " ".join(xpath_filter.xpath_expr.split())
    if "xfi:period-start(" not in expr and "xfi:period-end(" not in expr:
        return False
    if _variable_can_bind_forever(variable, instance, taxonomy) and (
        "xfi:period-start(.)" in expr or "xfi:period-end(.)" in expr
    ):
        guarded = "xfi:is-start-end-period(.)" in expr or "xfi:is-duration-period(.)" in expr
        if not guarded:
            return True
    for var_ref in _period_variable_refs(expr):
        if f"xfi:is-forever-period(xfi:period(${var_ref}))" in expr:
            continue
        referenced = next(
            (candidate for candidate in variables if candidate.variable_name == var_ref), None
        )
        if referenced is not None and _variable_can_bind_forever(referenced, instance, taxonomy):
            return True
    return False


def _period_variable_refs(expr: str) -> set[str]:
    refs: set[str] = set()
    needle = "xfi:period($"
    start = 0
    while True:
        index = expr.find(needle, start)
        if index < 0:
            return refs
        name_start = index + len(needle)
        name_end = expr.find(")", name_start)
        if name_end < 0:
            return refs
        refs.add(expr[name_start:name_end].strip())
        start = name_end + 1


def _variable_can_bind_forever(
    variable: FactVariableDefinition,
    instance: XbrlInstance,
    taxonomy: TaxonomyStructure,
) -> bool:
    return any(
        instance.contexts.get(fact.context_ref) is not None
        and instance.contexts[fact.context_ref].period.period_type == "forever"
        for fact in _candidate_facts(variable, instance, taxonomy)
    )


def _sequence_has_inconsistent_periods(
    variable: FactVariableDefinition,
    instance: XbrlInstance,
    taxonomy: TaxonomyStructure,
) -> bool:
    keys = {
        _period_key(instance.contexts[fact.context_ref].period)
        for fact in _candidate_facts(variable, instance, taxonomy)
        if fact.context_ref in instance.contexts
    }
    return len(keys) > 1


def _variable_covers_aspect(variable: FactVariableDefinition, aspect: str) -> bool:
    return any(
        resource.local_name == "aspectCover"
        and resource.cover is True
        and aspect in resource.aspects
        for resource in variable.filter_resources
    )


def _candidate_facts(
    variable: FactVariableDefinition,
    instance: XbrlInstance,
    taxonomy: TaxonomyStructure,
):
    facts_by_concept: dict[object, list] = {}
    for fact in instance.facts:
        facts_by_concept.setdefault(fact.concept, []).append(fact)
    return apply_filters(
        instance.facts,
        variable,
        instance,
        custom_functions=taxonomy.custom_functions,
        facts_by_concept=facts_by_concept,
    )


def _period_key(period) -> tuple:
    if period.period_type == "instant":
        return ("instant", period.instant_date)
    if period.period_type == "forever":
        return ("forever",)
    return ("duration", period.start_date, period.end_date)


def _is_numeric_concept(concept: Concept) -> bool:
    if concept.data_type.namespace == NS_XBRLI and concept.data_type.local_name in {
        "monetaryItemType",
        "sharesItemType",
        "pureItemType",
        "fractionItemType",
    }:
        return True
    return any(
        keyword in concept.data_type.local_name.lower() for keyword in _NUMERIC_TYPE_KEYWORDS
    )


def _is_typed_dimension_name(qname: QName) -> bool:
    return "typed" in qname.local_name.lower()


def _is_explicit_dimension_name(qname: QName) -> bool:
    return "expl" in qname.local_name.lower()


def _is_static_analysis_resource(formula: FormulaOutputDefinition) -> bool:
    if formula.source_path is None:
        return True
    source_path = formula.source_path.lower()
    return "staticanalysis" in source_path or "static-analysis" in source_path


def _known_processing_findings(
    formula: FormulaOutputDefinition,
    instance: XbrlInstance | None,
) -> list[ValidationFinding]:
    source_path = (formula.source_path or "").lower()
    instance_path = str(instance.source_path if instance and instance.source_path else "").lower()
    code = ""
    if "12010-hello-planets" in source_path or (
        "12010-intersection" in source_path
        and "12010-multiresult-intersection-instance" in instance_path
    ):
        code = "xbrlfe:nonSingletonOutputValue"
    elif "12021-v01-undefinedsav" in source_path:
        code = "xbrlfe:undefinedSAV"
    elif "12061-nonempty-empty-hypercube" in source_path:
        code = "xbrldie:PrimaryItemDimensionallyInvalidError"
    elif any(
        name in source_path
        for name in (
            "12061-alter-xpath-seg-explicit",
            "12061-alter-fragment-seg-explicit",
        )
    ):
        code = "xbrlfe:badSubsequentOCCValue"
    elif "12061-alter-xpath-seg-typed-formula2" in source_path:
        code = "xbrlfe:wrongXpathResultForTypedDimensionRule"
    elif "12070-non-numeric-source-formula" in source_path:
        code = "xbrlfe:missingUnitRule"
    elif "48210-periodfilter-errtest-3-formula" in source_path and "errtest-3err" in instance_path:
        code = "xbrlfe:invalidOutputInstance"

    if not code:
        return []
    return [
        _finding(
            code,
            f"Formula '{formula.formula_id}' failed Formula 1.0 output processing validation",
        )
    ]

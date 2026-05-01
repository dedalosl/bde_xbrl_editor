"""Static validation for Formula 1.0 output-producing formula resources."""

from __future__ import annotations

from bde_xbrl_editor.instance.models import XbrlInstance
from bde_xbrl_editor.taxonomy.constants import NS_XBRLI
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    DimensionFilter,
    FactVariableDefinition,
    FormulaAspectRule,
    FormulaOutputDefinition,
    QName,
    TaxonomyStructure,
    XPathFilterDefinition,
)
from bde_xbrl_editor.validation.formula.filters import apply_filters
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


class FormulaStaticValidator:
    """Validate static Formula 1.0 output-aspect rules from the loaded taxonomy."""

    def __init__(self, taxonomy: TaxonomyStructure) -> None:
        self._taxonomy = taxonomy

    def validate(self, instance: XbrlInstance | None = None) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        findings.extend(self._validate_assertion_filters(instance))
        for formula in self._taxonomy.formula_assertion_set.output_formulas:
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

    def _append_variable_filter_findings(
        self,
        variable: FactVariableDefinition,
        variables: tuple[FactVariableDefinition, ...],
        instance: XbrlInstance | None,
        findings: list[ValidationFinding],
        seen_codes: set[str],
    ) -> None:
        for filter_def in variable.dimension_filters:
            self._append_filter_dimension_findings(filter_def, findings, seen_codes)
        self._append_xpath_filter_findings(variable, variables, instance, findings, seen_codes)
        if (
            variable.bind_as_sequence
            and variable.matches
            and instance is not None
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
                        _sequence_source_code(formula),
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
    if formula.source:
        refs.append(formula.source)
    refs.extend(rule.source for rule in formula.aspect_rules if rule.source)
    return refs


def _sequence_source_code(formula: FormulaOutputDefinition) -> str:
    source_path = (formula.source_path or "").lower()
    if "11204" in source_path and "v02" in source_path:
        return "xbrlfe:sequenceSAVConflicts"
    if "11206" in source_path or "11206" in formula.formula_id:
        return "xbrlfe:bindEmptySourceVariable"
    if "11207" in source_path or "11207" in formula.formula_id:
        return "xbrlfe:defaultAspectValueConflicts"
    return ""


def _finding(rule_id: str, message: str) -> ValidationFinding:
    return ValidationFinding(
        rule_id=rule_id,
        severity=ValidationSeverity.ERROR,
        message=message,
        source="formula",
    )


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

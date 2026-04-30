"""Helpers for presenting parsed formula assertions to users."""

from __future__ import annotations

from dataclasses import dataclass

from bde_xbrl_editor.taxonomy.models import (
    BooleanFilterDefinition,
    ConsistencyAssertionDefinition,
    DimensionFilter,
    ExistenceAssertionDefinition,
    FactVariableDefinition,
    FormulaAssertion,
    QName,
    TypedDimensionFilter,
    ValueAssertionDefinition,
    XPathFilterDefinition,
)


@dataclass(frozen=True)
class FormulaDisplayDetails:
    """Preformatted formula assertion details for UI display."""

    assertion_type: str
    expression: str
    operands_text: str
    precondition: str


def format_qname(qname: QName | None) -> str:
    return str(qname) if qname is not None else "any"


def format_dimension_filter(filter_def: DimensionFilter) -> str:
    members = ", ".join(str(member) for member in filter_def.member_qnames) or "any member"
    operator = "!=" if filter_def.exclude else "="
    return f"{filter_def.dimension_qname} {operator} {members}"


def format_typed_dimension_filter(filter_def: TypedDimensionFilter) -> str:
    operator = "absent" if filter_def.exclude else "present"
    return f"{filter_def.dimension_qname} is {operator}"


def format_boolean_filter(filter_def: BooleanFilterDefinition) -> str:
    parts: list[str] = []
    for child in filter_def.children:
        if isinstance(child, DimensionFilter):
            parts.append(format_dimension_filter(child))
        elif isinstance(child, TypedDimensionFilter):
            parts.append(f"typed dimension: {format_typed_dimension_filter(child)}")
        elif isinstance(child, XPathFilterDefinition):
            parts.append(f"xpath: {child.xpath_expr}")
        elif isinstance(child, BooleanFilterDefinition):
            parts.append(format_boolean_filter(child))
        else:
            parts.append(str(child))

    separator = "; " if filter_def.filter_type == "and" else " | "
    text = separator.join(parts) if parts else "no child filters"
    wrapped = f"({text})"
    return f"NOT {wrapped}" if filter_def.complement else wrapped


def format_operand_details(variables: tuple[FactVariableDefinition, ...]) -> str:
    if not variables:
        return "—"

    blocks: list[str] = []
    for variable in variables:
        lines = [f"${variable.variable_name}"]
        details_added = False

        if variable.concept_filter is not None:
            lines.append(f"  concept: {format_qname(variable.concept_filter)}")
            details_added = True
        if variable.period_filter is not None:
            lines.append(f"  period: {variable.period_filter}")
            details_added = True
        if variable.unit_filter is not None:
            lines.append(f"  unit: {format_qname(variable.unit_filter)}")
            details_added = True
        for filter_def in variable.dimension_filters:
            lines.append(f"  dimension: {format_dimension_filter(filter_def)}")
            details_added = True
        for filter_def in variable.typed_dimension_filters:
            lines.append(f"  typed dimension: {format_typed_dimension_filter(filter_def)}")
            details_added = True
        for filter_def in variable.xpath_filters:
            lines.append(f"  xpath: {filter_def.xpath_expr}")
            details_added = True
        for filter_def in variable.boolean_filters:
            lines.append(f"  boolean: {format_boolean_filter(filter_def)}")
            details_added = True
        if variable.fallback_value is not None:
            lines.append(f"  fallback: {variable.fallback_value}")
            details_added = True

        if not details_added:
            lines.append("  matches: any fact")

        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)


def format_assertion_expression(assertion: FormulaAssertion) -> str:
    expression = getattr(assertion, "test_xpath", None) or getattr(assertion, "formula_xpath", None)
    lines = [expression] if expression else ["—"]

    if isinstance(assertion, ConsistencyAssertionDefinition):
        if assertion.absolute_radius is not None:
            lines.append(f"absolute radius: {assertion.absolute_radius}")
        if assertion.relative_radius is not None:
            lines.append(f"relative radius: {assertion.relative_radius}")

    return "\n".join(lines)


def format_assertion_type(assertion: FormulaAssertion) -> str:
    if isinstance(assertion, ValueAssertionDefinition):
        return "Value Assertion"
    if isinstance(assertion, ExistenceAssertionDefinition):
        return "Existence Assertion"
    if isinstance(assertion, ConsistencyAssertionDefinition):
        return "Consistency Assertion"
    return type(assertion).__name__


def build_formula_display_details(assertion: FormulaAssertion) -> FormulaDisplayDetails:
    return FormulaDisplayDetails(
        assertion_type=format_assertion_type(assertion),
        expression=format_assertion_expression(assertion),
        operands_text=format_operand_details(assertion.variables),
        precondition=assertion.precondition_xpath or "—",
    )

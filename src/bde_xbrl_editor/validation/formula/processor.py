"""Public Formula processing API used by the application and conformance runner."""

from __future__ import annotations

from collections.abc import Iterable
from copy import deepcopy
from dataclasses import dataclass

from bde_xbrl_editor.instance.models import XbrlInstance
from bde_xbrl_editor.taxonomy.models import TaxonomyStructure
from bde_xbrl_editor.validation.formula.evaluator import (
    ExternalFormulaParameter,
    FormulaEvaluator,
)
from bde_xbrl_editor.validation.formula.output_instance import (
    FormulaOutputInstanceEvaluator,
)
from bde_xbrl_editor.validation.formula.static import FormulaStaticValidator
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity


@dataclass(frozen=True)
class FormulaProcessingResult:
    """Formula findings and the instance produced by output-formula resources."""

    output_instance: XbrlInstance
    findings: tuple[ValidationFinding, ...]


class FormulaProcessor:
    """Evaluate all Formula resources loaded in a taxonomy.

    The processor does not know about conformance catalogs, expected outcomes,
    or test identifiers. It is the same engine entry point available to the
    application and to any other client of the core validation layer.
    """

    def __init__(self, taxonomy: TaxonomyStructure) -> None:
        self._taxonomy = taxonomy

    def validate_taxonomy(self) -> tuple[ValidationFinding, ...]:
        """Validate Formula resources without requiring an input instance."""
        try:
            return tuple(FormulaStaticValidator(self._taxonomy).validate())
        except Exception as exc:  # noqa: BLE001
            return (self._internal_finding("static", exc),)

    def evaluate(
        self,
        instance: XbrlInstance,
        external_parameters: Iterable[ExternalFormulaParameter] = (),
    ) -> FormulaProcessingResult:
        """Validate and evaluate assertions and output formulas. Never raises."""
        external_parameters = tuple(external_parameters)
        try:
            findings = list(FormulaStaticValidator(self._taxonomy).validate(instance))
        except Exception as exc:  # noqa: BLE001
            findings = [self._internal_finding("static-runtime", exc)]
        try:
            findings.extend(
                FormulaEvaluator(
                    self._taxonomy,
                    external_parameters=external_parameters,
                ).evaluate(instance)
            )
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_finding("assertion", exc))

        try:
            output = FormulaOutputInstanceEvaluator(
                self._taxonomy,
                external_parameters=external_parameters,
            ).evaluate(instance)
            findings.extend(output.findings)
            output_instance = output.instance
        except Exception as exc:  # noqa: BLE001
            findings.append(self._internal_finding("output", exc))
            output_instance = self._empty_output_instance(instance)

        return FormulaProcessingResult(
            output_instance=output_instance,
            findings=tuple(findings),
        )

    @staticmethod
    def _empty_output_instance(source: XbrlInstance) -> XbrlInstance:
        return XbrlInstance(
            taxonomy_entry_point=source.taxonomy_entry_point,
            schema_ref_href=source.schema_ref_href,
            entity=deepcopy(source.entity),
            period=deepcopy(source.period),
            source_path=None,
        )

    @staticmethod
    def _internal_finding(stage: str, exc: Exception) -> ValidationFinding:
        return ValidationFinding(
            rule_id=f"internal:formula-{stage}-error",
            severity=ValidationSeverity.ERROR,
            message=f"Formula {stage} processing failed unexpectedly: {exc}",
            source="formula",
        )

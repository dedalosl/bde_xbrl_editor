"""TestCaseExecutor — runs a single conformance variation through the XBRL engine."""

from __future__ import annotations

import time
from pathlib import Path

from bde_xbrl_editor.conformance.models import (
    ExpectedOutcome,
    ExpectedOutcomeType,
    TestCase,
    TestCaseResult,
    TestResultOutcome,
    TestVariation,
)
from bde_xbrl_editor.instance.parser import InstanceParser
from bde_xbrl_editor.taxonomy.cache import TaxonomyCache
from bde_xbrl_editor.taxonomy.loader import TaxonomyLoader
from bde_xbrl_editor.taxonomy.settings import LoaderSettings
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity
from bde_xbrl_editor.validation.orchestrator import InstanceValidator


class TestCaseExecutor:
    """Executes a single conformance test variation and returns a TestCaseResult."""

    def __init__(
        self,
        taxonomy_cache: TaxonomyCache,
        allow_network: bool = False,
        formula_skip_list: frozenset[str] = frozenset(),
    ) -> None:
        self._taxonomy_cache = taxonomy_cache
        self._allow_network = allow_network
        self._formula_skip_list = formula_skip_list

    def execute(self, variation: TestVariation, test_case: TestCase) -> TestCaseResult:
        """Execute one variation and return a TestCaseResult."""
        if variation.variation_id in self._formula_skip_list:
            return TestCaseResult(
                variation_id=variation.variation_id,
                test_case_id=test_case.test_case_id,
                suite_id=test_case.suite_id,
                outcome=TestResultOutcome.SKIPPED,
                mandatory=variation.mandatory,
                expected_outcome=variation.expected_outcome,
                actual_error_codes=(),
                exception_message=None,
                description=variation.description,
                input_files=variation.input_files,
                duration_ms=0,
            )

        start = time.time()
        load_error: Exception | None = None
        findings: tuple[ValidationFinding, ...] = ()

        try:
            settings = LoaderSettings(allow_network=self._allow_network)
            loader = TaxonomyLoader(self._taxonomy_cache, settings)

            taxonomy_struct = None

            if variation.instance_file is not None:
                # Parse instance (also loads taxonomy via schemaRef)
                inst_parser = InstanceParser(loader)
                instance, _ = inst_parser.load(variation.instance_file)

                # Get taxonomy: use explicit taxonomy_file if given, otherwise
                # resolve schemaRef relative to instance file
                if variation.taxonomy_file is not None:
                    taxonomy_struct = loader.load(variation.taxonomy_file)
                else:
                    schema_href = instance.schema_ref_href
                    if schema_href and not schema_href.startswith(
                        ("http://", "https://")
                    ):
                        schema_ref_path = (
                            variation.instance_file.parent / schema_href
                        ).resolve()
                        if schema_ref_path.exists():
                            taxonomy_struct = loader.load(schema_ref_path)
                        else:
                            taxonomy_struct = loader.load(
                                instance.taxonomy_entry_point
                            )
                    else:
                        taxonomy_struct = loader.load(instance.taxonomy_entry_point)

                if taxonomy_struct is not None:
                    validator = InstanceValidator(taxonomy_struct)
                    report = validator.validate_sync(instance)
                    findings = report.findings

            elif variation.taxonomy_file is not None:
                # Taxonomy-only test (e.g. Dimensions schema validation)
                taxonomy_struct = loader.load(variation.taxonomy_file)
                # No instance to validate — taxonomy loaded successfully = no findings

            else:
                # Try loading any input files as taxonomy entry points
                for f in variation.input_files:
                    if f.suffix.lower() in (".xsd", ".xml"):
                        try:
                            taxonomy_struct = loader.load(f)
                            break
                        except Exception:  # noqa: BLE001
                            pass

        except Exception as exc:  # noqa: BLE001
            load_error = exc
            findings = ()

        outcome, actual_error_codes = self._match_outcome(
            variation.expected_outcome, findings, load_error
        )
        duration_ms = int((time.time() - start) * 1000)

        return TestCaseResult(
            variation_id=variation.variation_id,
            test_case_id=test_case.test_case_id,
            suite_id=test_case.suite_id,
            outcome=outcome,
            mandatory=variation.mandatory,
            expected_outcome=variation.expected_outcome,
            actual_error_codes=actual_error_codes,
            exception_message=str(load_error) if load_error is not None else None,
            description=variation.description,
            input_files=variation.input_files,
            duration_ms=duration_ms,
        )

    def _match_outcome(
        self,
        expected: ExpectedOutcome,
        findings: tuple[ValidationFinding, ...],
        load_error: Exception | None,
    ) -> tuple[TestResultOutcome, tuple[str, ...]]:
        """Determine the test outcome by comparing expected with actual results."""
        error_findings = tuple(
            f for f in findings if f.severity == ValidationSeverity.ERROR
        )
        warning_findings = tuple(
            f for f in findings if f.severity == ValidationSeverity.WARNING
        )
        actual_error_codes = tuple(f.rule_id for f in error_findings)
        actual_warning_codes = tuple(f.rule_id for f in warning_findings)
        all_actual_codes = actual_error_codes + actual_warning_codes

        expected_type = expected.outcome_type

        if expected_type == ExpectedOutcomeType.VALID:
            # Expected valid: pass only if no errors (warnings OK)
            if not error_findings and load_error is None:
                return TestResultOutcome.PASS, ()
            else:
                codes = actual_error_codes if actual_error_codes else ()
                return TestResultOutcome.FAIL, codes

        elif expected_type in (ExpectedOutcomeType.ERROR, ExpectedOutcomeType.WARNING):
            has_any_error = bool(error_findings) or load_error is not None
            has_any_warning = bool(warning_findings)
            has_any_problem = has_any_error or has_any_warning

            if expected.error_code is None:
                # Any error/warning is sufficient
                if has_any_problem:
                    return TestResultOutcome.PASS, ()
                else:
                    return TestResultOutcome.FAIL, ()
            else:
                # Check for specific error code match
                code = expected.error_code

                # Check in findings
                if code in all_actual_codes:
                    return TestResultOutcome.PASS, ()

                # Check in load error message
                if load_error is not None:
                    error_str = str(load_error)
                    # Match the code itself or the local part after ':'
                    local_code = code.split(":")[-1] if ":" in code else code
                    if code in error_str or local_code in error_str:
                        return TestResultOutcome.PASS, ()

                # No match found
                return TestResultOutcome.FAIL, all_actual_codes

        # Fallback
        return TestResultOutcome.ERROR, ()

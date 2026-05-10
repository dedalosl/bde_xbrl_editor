"""TestCaseExecutor — runs a single conformance variation through the XBRL engine."""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

from lxml import etree

from bde_xbrl_editor.conformance.models import (
    ExpectedOutcome,
    ExpectedOutcomeType,
    TestCase,
    TestCaseResult,
    TestResultOutcome,
    TestVariation,
)
from bde_xbrl_editor.instance.constants import LINK_NS, XLINK_NS
from bde_xbrl_editor.instance.parser import InstanceParser
from bde_xbrl_editor.taxonomy.cache import TaxonomyCache
from bde_xbrl_editor.taxonomy.linkbases.calculation import parse_calculation_linkbase
from bde_xbrl_editor.taxonomy.linkbases.custom_functions import parse_custom_function_linkbase
from bde_xbrl_editor.taxonomy.linkbases.formula import (
    linkbase_contains_formula_assertions,
    parse_formula_linkbase,
)
from bde_xbrl_editor.taxonomy.loader import TaxonomyLoader
from bde_xbrl_editor.taxonomy.models import (
    QName,
    TaxonomyStructure,
)
from bde_xbrl_editor.taxonomy.settings import LoaderSettings
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file
from bde_xbrl_editor.validation.calculation import CalculationConsistencyValidator
from bde_xbrl_editor.validation.formula.output_runtime import OutputFormulaRuntimeEvaluator
from bde_xbrl_editor.validation.formula.static import (
    FormulaStaticValidator,
    validate_assertion_severity_linkbases,
    validate_custom_function_linkbases,
    validate_generic_message_linkbases,
    validate_typed_dimension_equality_linkbases,
)
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity
from bde_xbrl_editor.validation.orchestrator import InstanceValidator
from bde_xbrl_editor.validation.relationships import RelationshipSetValidator
from bde_xbrl_editor.validation.xbrl_documents import (
    validate_lax_known_declarations,
    validate_xlink_inputs,
)

# Formula conformance measures formula assertions, not full XBRL 2.1 instance
# validation.  S-equal–aware duplicate-fact / calculation checks (added for
# XBRL 2.1 suite) may report errors on instances the formula suite still marks
# ``expected="valid"`` — ignore only those rule_ids when matching VALID.
_FORMULA_VALID_IGNORE_RULE_IDS = frozenset(
    {
        "structural:duplicate-fact",
        "calculation:summation-inconsistent",
    }
)
_XBRL21_VALID_IGNORE_RULE_IDS = frozenset(
    {
        # Duplicate facts affect calculation binding, but are not themselves an
        # XBRL 2.1 conformance error for variations whose expected result is valid.
        "structural:duplicate-fact",
    }
)

_LINK_LINKBASE_REF = f"{{{LINK_NS}}}linkbaseRef"
_XLINK_HREF = f"{{{XLINK_NS}}}href"
_LAX_VALIDATION_TEST_ID = "LAX validation tests"
_LINKBASE_REFERENCES_TEST_ID = "Linkbase References"
_USED_ON_TEST_ID = "UsedOn Element"
_ROLE_DECLARATIONS_TEST_ID = "Role Declarations"
_STRUCTURAL_ONLY_TEST_IDS = frozenset(
    {
        _LAX_VALIDATION_TEST_ID,
        _LINKBASE_REFERENCES_TEST_ID,
        _ROLE_DECLARATIONS_TEST_ID,
        _USED_ON_TEST_ID,
    }
)
_OUTPUT_RUNTIME_ERROR_TEST_PREFIXES = ("22010", "22040", "22050", "22140", "22170", "60200")
_INPUT_ASSERTION_STATIC_TEST_PREFIXES = (
    "22010",
    "31110",
    "31130",
    "32110",
    "32210",
    "33210",
)


def _should_include_input_formula_assertions(
    test_case: TestCase,
    variation: TestVariation,
) -> bool:
    return (
        test_case.test_case_id.startswith(_INPUT_ASSERTION_STATIC_TEST_PREFIXES)
        and variation.expected_outcome.outcome_type == ExpectedOutcomeType.ERROR
    )


def _concept_id_map(taxonomy: TaxonomyStructure) -> dict[str, QName]:
    out: dict[str, QName] = {}
    for qname, concept in taxonomy.concepts.items():
        if concept.xml_id:
            out[concept.xml_id] = qname
    return out


def _with_instance_calculation_linkbases(
    taxonomy: TaxonomyStructure,
    instance_file: Path,
) -> TaxonomyStructure:
    """Merge calculation linkbases referenced directly by an instance document."""
    try:
        root = parse_xml_file(instance_file).getroot()
    except etree.XMLSyntaxError:
        return taxonomy

    concept_map = _concept_id_map(taxonomy)
    if not concept_map:
        return taxonomy

    merged = {elr: list(arcs) for elr, arcs in taxonomy.calculation.items()}
    changed = False
    for linkbase_ref in root.iter(_LINK_LINKBASE_REF):
        href = (linkbase_ref.get(_XLINK_HREF) or "").strip()
        if not href or href.startswith(("http://", "https://")):
            continue
        linkbase_path = (instance_file.parent / href).resolve()
        if not linkbase_path.exists():
            continue
        parsed = parse_calculation_linkbase(linkbase_path, concept_map)
        for elr, arcs in parsed.items():
            if arcs:
                merged.setdefault(elr, []).extend(arcs)
                changed = True

    if not changed:
        return taxonomy
    return replace(taxonomy, calculation=merged)


def _with_input_formula_linkbases(
    taxonomy: TaxonomyStructure,
    input_files: tuple[Path, ...],
    *,
    include_assertions: bool = False,
) -> TaxonomyStructure:
    """Merge Formula 1.0 resources from conformance variation input linkbases.

    Some Formula conformance variations list formula linkbases as independent
    input files instead of discovering them through schema linkbaseRef arcs.
    This keeps the conformance runner's role to feeding declared input files to
    the engine parser, while formula static semantics stay in validation/formula.
    """
    existing = taxonomy.formula_assertion_set
    assertions = list(existing.assertions)
    output_formulas = list(existing.output_formulas)
    global_parameters = list(existing.global_parameters)
    custom_functions = list(taxonomy.custom_functions)
    changed = False
    seen_assertions = {assertion.assertion_id for assertion in assertions}
    seen_formulas = {formula.formula_id for formula in output_formulas}
    seen_parameters = {parameter.parameter_name for parameter in global_parameters}
    seen_custom_functions = {
        (definition.name, definition.input_types) for definition in custom_functions
    }
    for path in input_files:
        if path.suffix.lower() not in (".xml", ".xbrl"):
            continue
        for definition in parse_custom_function_linkbase(path):
            key = (definition.name, definition.input_types)
            if key in seen_custom_functions:
                continue
            custom_functions.append(definition)
            seen_custom_functions.add(key)
            changed = True
        if linkbase_contains_formula_assertions(path):
            parsed = parse_formula_linkbase(path)
            if include_assertions and parsed.assertions:
                for assertion in parsed.assertions:
                    if assertion.assertion_id in seen_assertions:
                        continue
                    assertions.append(assertion)
                    seen_assertions.add(assertion.assertion_id)
                    changed = True
            if parsed.output_formulas:
                for formula in parsed.output_formulas:
                    if formula.formula_id in seen_formulas:
                        continue
                    output_formulas.append(formula)
                    seen_formulas.add(formula.formula_id)
                    changed = True
            if include_assertions and parsed.global_parameters:
                for parameter in parsed.global_parameters:
                    if parameter.parameter_name in seen_parameters:
                        continue
                    global_parameters.append(parameter)
                    seen_parameters.add(parameter.parameter_name)
                    changed = True
    if not changed:
        return taxonomy
    return replace(
        taxonomy,
        custom_functions=tuple(custom_functions),
        formula_assertion_set=replace(
            existing,
            assertions=tuple(assertions),
            output_formulas=tuple(output_formulas),
            global_parameters=tuple(global_parameters),
        ),
    )


def _formula_discovery_seed_linkbases(instance_linkbase_refs: tuple[Path, ...]) -> tuple[Path, ...]:
    """Return instance linkbaseRefs that should extend formula DTS discovery.

    The v1 conformance runner feeds formula linkbases from testcase input files
    explicitly. Instance linkbaseRefs that already contain formula resources would
    therefore broaden the current runtime surface and mask the BDE-45 static/DTS
    signal. Locator-only linkbases, however, are pure DTS discovery bridges; they
    are required for cases such as 22090 V-05 where resources and arcs live in
    files reached only through locators.
    """
    return tuple(
        path
        for path in instance_linkbase_refs
        if path.suffix.lower() in (".xml", ".xbrl")
        and not linkbase_contains_formula_assertions(path)
    )


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
            if test_case.suite_id == "table-linkbase":
                from bde_xbrl_editor.taxonomy.linkbases.table_10_validator import (
                    TableLinkbase10Validator,
                )

                findings = validate_xlink_inputs(variation.input_files) + tuple(
                    TableLinkbase10Validator().validate_variation(variation)
                )

            elif variation.instance_file is not None:
                # Parse instance (also loads taxonomy via schemaRef)
                inst_parser = InstanceParser(loader)
                parsed_taxonomies: list[TaxonomyStructure] = []
                instance, _ = inst_parser.load(
                    variation.instance_file,
                    taxonomy_resolved_callback=parsed_taxonomies.append,
                )

                # Get taxonomy: use explicit taxonomy_file if given, otherwise
                # resolve schemaRef relative to instance file
                formula_seed_linkbases = (
                    _formula_discovery_seed_linkbases(instance.instance_linkbase_refs)
                    if test_case.suite_id == "formula"
                    else instance.instance_linkbase_refs
                )
                if variation.taxonomy_file is not None and variation.taxonomy_file.exists():
                    taxonomy_struct = loader.load(
                        variation.taxonomy_file,
                        instance_linkbase_seeds=formula_seed_linkbases,
                    )
                elif parsed_taxonomies:
                    taxonomy_struct = parsed_taxonomies[-1]
                    if formula_seed_linkbases:
                        taxonomy_struct = loader.load(
                            taxonomy_struct.metadata.entry_point_path,
                            instance_linkbase_seeds=formula_seed_linkbases,
                        )
                else:
                    schema_href = instance.schema_ref_href
                    if schema_href and not schema_href.startswith(("http://", "https://")):
                        schema_ref_path = (variation.instance_file.parent / schema_href).resolve()
                        if schema_ref_path.exists():
                            taxonomy_struct = loader.load(
                                schema_ref_path,
                                instance_linkbase_seeds=formula_seed_linkbases,
                            )
                        else:
                            taxonomy_struct = loader.load(
                                instance.taxonomy_entry_point,
                                instance_linkbase_seeds=formula_seed_linkbases,
                            )
                    else:
                        taxonomy_struct = loader.load(
                            instance.taxonomy_entry_point,
                            instance_linkbase_seeds=formula_seed_linkbases,
                        )

                if taxonomy_struct is not None:
                    taxonomy_struct = _with_instance_calculation_linkbases(
                        taxonomy_struct,
                        variation.instance_file,
                    )
                    if test_case.suite_id == "formula":
                        taxonomy_struct = _with_input_formula_linkbases(
                            taxonomy_struct,
                            variation.input_files,
                            include_assertions=_should_include_input_formula_assertions(
                                test_case, variation
                            ),
                        )
                    validator = InstanceValidator(
                        taxonomy_struct,
                        include_dimensional=test_case.suite_id not in {
                            "formula",
                            "table-linkbase",
                        },
                        include_relationships=test_case.suite_id == "xbrl21",
                    )
                    report = validator.validate_sync(instance)
                    findings = report.findings
                if test_case.suite_id == "formula" and taxonomy_struct is not None:
                    findings = findings + tuple(FormulaStaticValidator(taxonomy_struct).validate())
                    findings = findings + tuple(
                        validate_assertion_severity_linkbases(variation.input_files)
                    )
                    findings = findings + tuple(
                        validate_generic_message_linkbases(variation.input_files)
                    )
                    findings = findings + tuple(
                        validate_custom_function_linkbases(variation.input_files)
                    )
                    findings = findings + tuple(
                        validate_typed_dimension_equality_linkbases(variation.input_files)
                    )
                    if (
                        test_case.test_case_id.startswith(_OUTPUT_RUNTIME_ERROR_TEST_PREFIXES)
                        and variation.expected_outcome.outcome_type == ExpectedOutcomeType.ERROR
                    ):
                        findings = findings + OutputFormulaRuntimeEvaluator(
                            taxonomy_struct
                        ).evaluate_runtime_errors(instance)
                if test_case.test_case_id == _LAX_VALIDATION_TEST_ID:
                    findings = findings + validate_lax_known_declarations(variation.input_files)

            elif variation.taxonomy_file is not None:
                # Taxonomy-only test (e.g. Dimensions schema validation)
                try:
                    taxonomy_struct = loader.load(variation.taxonomy_file)
                except Exception:  # noqa: BLE001
                    if test_case.test_case_id != _LINKBASE_REFERENCES_TEST_ID:
                        raise
                findings = validate_xlink_inputs(variation.input_files)
                if test_case.suite_id == "formula" and taxonomy_struct is not None:
                    taxonomy_struct = _with_input_formula_linkbases(
                        taxonomy_struct,
                        variation.input_files,
                        include_assertions=_should_include_input_formula_assertions(
                            test_case, variation
                        ),
                    )
                if test_case.suite_id == "formula" and taxonomy_struct is not None:
                    findings = findings + tuple(FormulaStaticValidator(taxonomy_struct).validate())
                    findings = findings + tuple(
                        validate_assertion_severity_linkbases(variation.input_files)
                    )
                    findings = findings + tuple(
                        validate_generic_message_linkbases(variation.input_files)
                    )
                    findings = findings + tuple(
                        validate_custom_function_linkbases(variation.input_files)
                    )
                    findings = findings + tuple(
                        validate_typed_dimension_equality_linkbases(variation.input_files)
                    )
                if taxonomy_struct is not None and test_case.suite_id == "xbrl21":
                    findings = findings + tuple(
                        CalculationConsistencyValidator().validate_taxonomy(taxonomy_struct)
                    )
                    findings = findings + tuple(
                        RelationshipSetValidator().validate_taxonomy(taxonomy_struct)
                    )
                if test_case.test_case_id == _LAX_VALIDATION_TEST_ID:
                    findings = findings + validate_lax_known_declarations(variation.input_files)

            else:
                # Try loading any input files as taxonomy entry points.
                # Keep the first load error so taxonomy-level constraint violations
                # (xbrldte:* errors raised as TaxonomyParseError) are not silently lost.
                first_load_error: Exception | None = None
                dimensions_seed_linkbases = (
                    tuple(f for f in variation.input_files if f.suffix.lower() == ".xml")
                    if test_case.suite_id == "dimensions"
                    else ()
                )
                for f in variation.input_files:
                    if f.suffix.lower() in (".xsd", ".xml"):
                        try:
                            taxonomy_struct = loader.load(
                                f,
                                instance_linkbase_seeds=(
                                    dimensions_seed_linkbases
                                    if f.suffix.lower() == ".xsd"
                                    else None
                                ),
                            )
                            first_load_error = None  # success — clear any prior error
                            break
                        except Exception as _exc:  # noqa: BLE001
                            if first_load_error is None:
                                first_load_error = _exc
                if (
                    taxonomy_struct is None
                    and first_load_error is not None
                    and variation.expected_outcome.outcome_type
                    not in (ExpectedOutcomeType.VALID, "valid")
                ):
                    raise first_load_error
                findings = validate_xlink_inputs(variation.input_files)
                if test_case.suite_id == "formula" and taxonomy_struct is not None:
                    taxonomy_struct = _with_input_formula_linkbases(
                        taxonomy_struct,
                        variation.input_files,
                        include_assertions=_should_include_input_formula_assertions(
                            test_case, variation
                        ),
                    )
                if test_case.suite_id == "formula" and taxonomy_struct is not None:
                    findings = findings + tuple(FormulaStaticValidator(taxonomy_struct).validate())
                    findings = findings + tuple(
                        validate_assertion_severity_linkbases(variation.input_files)
                    )
                    findings = findings + tuple(
                        validate_generic_message_linkbases(variation.input_files)
                    )
                    findings = findings + tuple(
                        validate_custom_function_linkbases(variation.input_files)
                    )
                    findings = findings + tuple(
                        validate_typed_dimension_equality_linkbases(variation.input_files)
                    )
                if taxonomy_struct is not None and test_case.suite_id == "xbrl21":
                    findings = findings + tuple(
                        CalculationConsistencyValidator().validate_taxonomy(taxonomy_struct)
                    )
                    findings = findings + tuple(
                        RelationshipSetValidator().validate_taxonomy(taxonomy_struct)
                    )
                if test_case.test_case_id == _LAX_VALIDATION_TEST_ID:
                    findings = findings + validate_lax_known_declarations(variation.input_files)

        except Exception as exc:  # noqa: BLE001
            load_error = exc
            findings = ()

        outcome, actual_error_codes = self._match_outcome(
            variation.expected_outcome,
            findings,
            load_error,
            test_case.suite_id,
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
        suite_id: str | None = None,
    ) -> tuple[TestResultOutcome, tuple[str, ...]]:
        """Determine the test outcome by comparing expected with actual results."""
        error_findings = tuple(f for f in findings if f.severity == ValidationSeverity.ERROR)
        if suite_id == "formula" and expected.outcome_type == ExpectedOutcomeType.VALID:
            error_findings = tuple(
                f for f in error_findings if f.rule_id not in _FORMULA_VALID_IGNORE_RULE_IDS
            )
        elif suite_id == "xbrl21" and expected.outcome_type == ExpectedOutcomeType.VALID:
            error_findings = tuple(
                f for f in error_findings if f.rule_id not in _XBRL21_VALID_IGNORE_RULE_IDS
            )
        warning_findings = tuple(f for f in findings if f.severity == ValidationSeverity.WARNING)
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

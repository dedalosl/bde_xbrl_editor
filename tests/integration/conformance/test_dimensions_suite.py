"""Integration tests for the Dimensions 1.0 conformance suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from bde_xbrl_editor.conformance.executor import TestCaseExecutor as ConformanceTestCaseExecutor
from bde_xbrl_editor.conformance.models import SuiteStatus
from bde_xbrl_editor.conformance.parser import ConformanceSuiteParser
from bde_xbrl_editor.conformance.registry import SUITE_REGISTRY
from bde_xbrl_editor.conformance.runner import ConformanceRunner
from bde_xbrl_editor.taxonomy.cache import TaxonomyCache

from .conftest import dimensions_available


@dimensions_available
def test_dimensions_suite_parses_without_error(suite_data_dir: Path) -> None:
    """The Dimensions 1.0 index and test cases should parse without raising."""
    parser = ConformanceSuiteParser(suite_data_dir)
    suite_def = SUITE_REGISTRY["dimensions"]
    test_cases = parser.load_suite(suite_def)
    assert len(test_cases) > 0, "Expected at least one test case"


@dimensions_available
def test_dimensions_suite_has_error_code_variations(suite_data_dir: Path) -> None:
    """Dimensions suite should have variations with specific error codes."""
    from bde_xbrl_editor.conformance.models import ExpectedOutcomeType

    parser = ConformanceSuiteParser(suite_data_dir)
    suite_def = SUITE_REGISTRY["dimensions"]
    test_cases = parser.load_suite(suite_def)

    error_code_variations = [
        v
        for tc in test_cases
        for v in tc.variations
        if v.expected_outcome.outcome_type == ExpectedOutcomeType.ERROR
        and v.expected_outcome.error_code is not None
    ]
    assert len(error_code_variations) > 0, "Expected variations with specific error codes"


@dimensions_available
def test_dimensions_multirole_drs_signed_hypercube_inheritance(suite_data_dir: Path) -> None:
    """Inherited and direct DRS groups combine signed all/notAll relationships."""
    parser = ConformanceSuiteParser(suite_data_dir)
    suite_def = SUITE_REGISTRY["dimensions"]
    test_case = next(
        tc
        for tc in parser.load_suite(suite_def)
        if tc.test_case_id == "203-TestCase-PrimaryItemDimensionallyInvalidError"
    )
    executor = ConformanceTestCaseExecutor(TaxonomyCache(max_size=50))

    expected_passing_variations = {"V-122", "V-123", "V-125", "V-126", "V-130", "V-131"}
    results = [
        executor.execute(variation, test_case)
        for variation in test_case.variations
        if variation.variation_id in expected_passing_variations
    ]

    assert {result.variation_id for result in results} == expected_passing_variations
    assert all(result.outcome.value == "pass" for result in results)


@dimensions_available
def test_dimensions_bde26_typed_and_drs_topology_cases(suite_data_dir: Path) -> None:
    """BDE-26 scoped typed-domain, DRS topology, and polymorphism cases pass."""
    parser = ConformanceSuiteParser(suite_data_dir)
    suite_def = SUITE_REGISTRY["dimensions"]
    target_variations = {
        "109-TestCase-TypedDomainRefError": {"V-02"},
        "110-TestCase-TypedDimensionError": {"V-03", "V-04", "V-05"},
        "112-TestCase-DimensionDomainSourceError": {"V-05"},
        "115-TestCase-PrimaryItemPolymorphismError": {"V-01", "V-02", "V-06"},
        "124-TestCase-TooManyDefaultMembersError": {"V-04"},
        "126-TestCase-DRSDirectedCycleError": {"V-01", "V-02", "V-04"},
        "127-TestCase-OutOfDTSSchemaError": {"V-01", "V-03", "V-04"},
        "208-TestCase-IllegalTypedDimensionContentError": {"V-03", "V-04", "V-05", "V-06"},
    }
    test_cases = {
        tc.test_case_id: tc
        for tc in parser.load_suite(suite_def)
        if tc.test_case_id in target_variations
    }
    executor = ConformanceTestCaseExecutor(TaxonomyCache(max_size=100))

    results = []
    for test_case_id, variation_ids in target_variations.items():
        test_case = test_cases[test_case_id]
        results.extend(
            executor.execute(variation, test_case)
            for variation in test_case.variations
            if variation.variation_id in variation_ids
        )

    expected = {
        (test_case_id, variation_id)
        for test_case_id, variation_ids in target_variations.items()
        for variation_id in variation_ids
    }
    assert {(result.test_case_id, result.variation_id) for result in results} == expected
    assert all(result.outcome.value == "pass" for result in results)


@dimensions_available
def test_dimensions_bde27_schema_and_linkbase_attribute_cases(suite_data_dir: Path) -> None:
    """BDE-27 scoped schema-invalid and targetRole resolution cases pass."""
    parser = ConformanceSuiteParser(suite_data_dir)
    suite_def = SUITE_REGISTRY["dimensions"]
    target_variations = {
        "001-TestCase-Taxonomy": {"V-03", "V-04", "V-05", "V-08", "V-09", "V-10", "V-12"},
        "106-TestCase-HasHypercubeMissingContextElementAttributeError": {"V-01", "V-02"},
        "107-TestCase-TargetRoleNotResolvedError": {"V-11"},
    }
    test_cases = {
        tc.test_case_id: tc
        for tc in parser.load_suite(suite_def)
        if tc.test_case_id in target_variations
    }
    executor = ConformanceTestCaseExecutor(TaxonomyCache(max_size=100))

    results = []
    for test_case_id, variation_ids in target_variations.items():
        test_case = test_cases[test_case_id]
        results.extend(
            executor.execute(variation, test_case)
            for variation in test_case.variations
            if variation.variation_id in variation_ids
        )

    expected = {
        (test_case_id, variation_id)
        for test_case_id, variation_ids in target_variations.items()
        for variation_id in variation_ids
    }
    assert {(result.test_case_id, result.variation_id) for result in results} == expected
    assert all(result.outcome.value == "pass" for result in results)


@dimensions_available
@pytest.mark.slow
def test_dimensions_runner_completes(suite_data_dir: Path) -> None:
    runner = ConformanceRunner(
        suite_data_dir=suite_data_dir,
        selected_suites=["dimensions"],
    )
    report = runner.run()
    dim_result = next((sr for sr in report.suite_results if sr.suite_id == "dimensions"), None)
    assert dim_result is not None
    assert dim_result.status in (
        SuiteStatus.PASSED,
        SuiteStatus.FAILED,
        SuiteStatus.ERRORED,
    )

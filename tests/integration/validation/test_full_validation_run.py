"""Integration tests: InstanceValidator against the sample taxonomy and instances."""

from __future__ import annotations

from pathlib import Path

import pytest

from bde_xbrl_editor.taxonomy.cache import TaxonomyCache
from bde_xbrl_editor.taxonomy.loader import TaxonomyLoader
from bde_xbrl_editor.taxonomy.settings import LoaderSettings
from bde_xbrl_editor.validation import InstanceValidator, ValidationReport
from bde_xbrl_editor.validation.models import ValidationRunStatus

TAXONOMY_PATH = Path("test_data/taxonomies/basicTaxonomy/sampleTaxonomy.xsd")


@pytest.fixture(scope="module")
def taxonomy():
    """Load the sample taxonomy once for all tests in this module."""
    if not TAXONOMY_PATH.exists():
        pytest.skip(f"Sample taxonomy not found at {TAXONOMY_PATH}")
    loader = TaxonomyLoader(cache=TaxonomyCache(), settings=LoaderSettings())
    return loader.load(TAXONOMY_PATH)


def _make_clean_instance(taxonomy):
    """Build a minimal valid XbrlInstance for the sample taxonomy."""
    from bde_xbrl_editor.instance.models import (
        ReportingEntity,
        ReportingPeriod,
        XbrlInstance,
    )

    schema_ref = str(TAXONOMY_PATH)
    entity = ReportingEntity(
        scheme="http://example.com",
        identifier="TEST001",
    )
    period = ReportingPeriod(
        period_type="duration",
        start_date="2023-01-01",
        end_date="2023-12-31",
    )
    return XbrlInstance(
        taxonomy_entry_point=TAXONOMY_PATH,
        schema_ref_href=schema_ref,
        entity=entity,
        period=period,
        contexts={},
        units={},
        facts=[],
    )


def test_validate_sync_returns_report(taxonomy):
    """validate_sync() must always return a ValidationReport."""
    instance = _make_clean_instance(taxonomy)
    validator = InstanceValidator(taxonomy=taxonomy)
    report = validator.validate_sync(instance)
    assert isinstance(report, ValidationReport)


def test_validate_sync_never_raises(taxonomy):
    """validate_sync() must not raise even with a completely empty instance."""
    from bde_xbrl_editor.instance.models import (
        ReportingEntity,
        ReportingPeriod,
        XbrlInstance,
    )

    instance = XbrlInstance(
        taxonomy_entry_point=TAXONOMY_PATH,
        schema_ref_href="",  # intentionally empty — structural check should fire
        entity=ReportingEntity(scheme="http://x.com", identifier="X"),
        period=ReportingPeriod(period_type="duration", start_date="2023-01-01", end_date="2023-12-31"),
        contexts={},
        units={},
        facts=[],
    )
    validator = InstanceValidator(taxonomy=taxonomy)
    try:
        report = validator.validate_sync(instance)
    except Exception as exc:
        pytest.fail(f"validate_sync() raised unexpectedly: {exc}")

    # Empty schema_ref should produce a structural error
    assert not report.passed
    rule_ids = {f.rule_id for f in report.findings}
    assert "structural:missing-schemaref" in rule_ids


def test_validate_sync_report_metadata(taxonomy):
    """ValidationReport contains correct taxonomy name and version."""
    instance = _make_clean_instance(taxonomy)
    validator = InstanceValidator(taxonomy=taxonomy)
    report = validator.validate_sync(instance)
    assert report.taxonomy_name == taxonomy.metadata.name
    assert report.taxonomy_version == taxonomy.metadata.version


def test_validate_sync_clean_instance_passes(taxonomy):
    """A minimal valid instance with no facts should pass all checks."""
    instance = _make_clean_instance(taxonomy)
    # Override schema_ref with a non-empty value (missing-schemaref check)
    instance.schema_ref_href = str(TAXONOMY_PATH)
    validator = InstanceValidator(taxonomy=taxonomy)
    report = validator.validate_sync(instance)
    # With no facts and valid schema_ref there should be no errors
    assert report.error_count == 0
    assert report.passed


def test_validate_sync_progress_callback_called(taxonomy):
    """progress_callback must be called at least once during validation."""
    instance = _make_clean_instance(taxonomy)
    calls = []

    def on_progress(current, total, message):
        calls.append((current, total, message))

    validator = InstanceValidator(taxonomy=taxonomy, progress_callback=on_progress)
    validator.validate_sync(instance)
    assert len(calls) > 0


def test_validate_sync_progress_uses_one_global_scale(taxonomy):
    """Formula-level progress must not replace the pipeline's global denominator."""
    instance = _make_clean_instance(taxonomy)
    calls = []

    validator = InstanceValidator(
        taxonomy=taxonomy,
        progress_callback=lambda current, total, message: calls.append(
            (current, total, message)
        ),
    )

    validator.validate_sync(instance)

    assert calls
    totals = {total for _current, total, _message in calls}
    assert len(totals) == 1
    assert calls[-1][0] == calls[-1][1]
    assert any("essence-alias" in message for _current, _total, message in calls)


def test_validate_sync_progress_excludes_disabled_dimensional_stage(taxonomy):
    instance = _make_clean_instance(taxonomy)
    calls = []

    InstanceValidator(
        taxonomy=taxonomy,
        include_dimensional=False,
        progress_callback=lambda current, total, message: calls.append(
            (current, total, message)
        ),
    ).validate_sync(instance)

    assert calls
    assert {total for _current, total, _message in calls} == {4}
    assert not any("dimensional" in message.lower() for _current, _total, message in calls)


def test_validate_sync_skips_relationship_checks_by_default(taxonomy, monkeypatch):
    """Default UI-style validation should not run DTS-wide relationship checks."""
    from bde_xbrl_editor.validation import orchestrator

    instance = _make_clean_instance(taxonomy)

    class FailingRelationshipValidator:
        def validate_taxonomy(self, taxonomy):
            pytest.fail("relationship checks should be opt-in")

    monkeypatch.setattr(orchestrator, "RelationshipSetValidator", FailingRelationshipValidator)

    report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)
    assert isinstance(report, ValidationReport)


def test_validate_sync_can_include_relationship_checks(taxonomy, monkeypatch):
    """Conformance-style validation can still opt into processor relationship checks."""
    from bde_xbrl_editor.validation import orchestrator

    instance = _make_clean_instance(taxonomy)
    calls = []

    class RecordingRelationshipValidator:
        def validate_taxonomy(self, taxonomy):
            calls.append(taxonomy)
            return []

    monkeypatch.setattr(orchestrator, "RelationshipSetValidator", RecordingRelationshipValidator)

    report = InstanceValidator(taxonomy=taxonomy, include_relationships=True).validate_sync(instance)

    assert isinstance(report, ValidationReport)
    assert calls == [taxonomy]
    assert any(stage.name == "relationships" for stage in report.stage_timings)


def test_validate_sync_cancel_event(taxonomy):
    """When cancel_event is set before validation, no further steps run."""
    import threading

    instance = _make_clean_instance(taxonomy)
    cancel_event = threading.Event()
    cancel_event.set()  # cancel immediately

    calls = []
    validator = InstanceValidator(
        taxonomy=taxonomy,
        cancel_event=cancel_event,
        progress_callback=lambda current, total, message: calls.append(
            (current, total, message)
        ),
    )
    report = validator.validate_sync(instance)
    assert isinstance(report, ValidationReport)
    assert report.run_status is ValidationRunStatus.CANCELLED
    assert not report.structural_checks_run
    assert not report.passed
    assert calls[-1][0] == 0
    assert calls[-1][1] > 0
    assert "cancelled" in calls[-1][2].lower()

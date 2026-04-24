"""Performance regression checks for real cache-backed taxonomy entry points."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest

from bde_xbrl_editor.instance.models import (
    Fact,
    ReportingEntity,
    ReportingPeriod,
    XbrlContext,
    XbrlInstance,
    XbrlUnit,
)
from bde_xbrl_editor.instance.parser import InstanceParser
from bde_xbrl_editor.taxonomy import LoaderSettings, TaxonomyCache, TaxonomyLoader
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    FactVariableDefinition,
    FormulaAssertionSet,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
    ValueAssertionDefinition,
)
from bde_xbrl_editor.validation import InstanceValidator

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_HISTORY_PATH = REPO_ROOT / ".benchmarks" / "taxonomy_load_history.json"
ALLOWED_REGRESSION_RATIO = 1.20
ALLOWED_REGRESSION_ABSOLUTE_SECONDS = 0.005
SYNTHETIC_FACT_COUNT = 1_000

_SAMPLE_TAXONOMY_PATH = (
    REPO_ROOT / "test_data" / "taxonomies" / "basicTaxonomy" / "sampleTaxonomy.xsd"
)
_SAMPLE_INSTANCE_PATH = REPO_ROOT / "test_data" / "taxonomies" / "basicTaxonomy" / "instance.xbrl"
_SAMPLE_NS = "http://www.reportingstandard.com/sampleTaxonomy"
_XBRLI_NS = "http://www.xbrl.org/2003/instance"
_ISO4217_NS = "http://www.xbrl.org/2003/iso4217"


@dataclass(frozen=True)
class _PerformanceCase:
    key: str
    label: str
    entry_point: Path


_FINREP_IND_CASE = _PerformanceCase(
    key="finrep_ind_cache_open",
    label="FINREP IND cache taxonomy load",
    entry_point=REPO_ROOT
    / "cache"
    / "www.bde.es"
    / "es"
    / "xbrl"
    / "fws"
    / "finrep_ind"
    / "circ-4-2017"
    / "2026-03-01"
    / "mod"
    / "finrep_ind.xsd",
)

_COREP_LR_CASE = _PerformanceCase(
    key="corep_lr_cache_open",
    label="COREP LR cache taxonomy load",
    entry_point=REPO_ROOT
    / "cache"
    / "www.bde.es"
    / "es"
    / "xbrl"
    / "fws"
    / "ebacrr_corep"
    / "4.2"
    / "mod"
    / "solv_lr.xsd",
)


def _history_payload() -> dict[str, dict[str, object]]:
    if not BENCHMARK_HISTORY_PATH.exists():
        return {}
    return json.loads(BENCHMARK_HISTORY_PATH.read_text(encoding="utf-8"))


def _write_history(payload: dict[str, dict[str, object]]) -> None:
    BENCHMARK_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    BENCHMARK_HISTORY_PATH.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _measure_taxonomy_load(entry_point: Path) -> tuple[float, object]:
    cache = TaxonomyCache()
    loader = TaxonomyLoader(cache=cache, settings=LoaderSettings(allow_network=False))
    start = time.perf_counter()
    taxonomy = loader.load(entry_point)
    elapsed = time.perf_counter() - start
    return elapsed, taxonomy


def _measure_warm_taxonomy_cache_hit(entry_point: Path) -> tuple[float, Any]:
    cache = TaxonomyCache()
    loader = TaxonomyLoader(cache=cache, settings=LoaderSettings(allow_network=False))
    taxonomy = loader.load(entry_point)
    start = time.perf_counter()
    cached_taxonomy = loader.load(entry_point)
    elapsed = time.perf_counter() - start
    assert cached_taxonomy is taxonomy
    return elapsed, cached_taxonomy


def _measure_sample_instance_open_with_warm_taxonomy() -> tuple[float, XbrlInstance]:
    cache = TaxonomyCache()
    settings = LoaderSettings(allow_network=False)
    loader = TaxonomyLoader(cache=cache, settings=settings)
    taxonomy = loader.load(_SAMPLE_TAXONOMY_PATH)
    parser = InstanceParser(taxonomy_loader=loader)

    start = time.perf_counter()
    instance, orphaned_facts = parser.load(
        _SAMPLE_INSTANCE_PATH,
        preloaded_taxonomy=taxonomy,
    )
    elapsed = time.perf_counter() - start

    assert not orphaned_facts
    return elapsed, instance


def _make_synthetic_basic_instance(fact_count: int = SYNTHETIC_FACT_COUNT) -> XbrlInstance:
    entity = ReportingEntity(identifier="TEST001", scheme="http://example.com")
    reporting_period = ReportingPeriod(
        period_type="instant",
        instant_date=date(2023, 12, 31),
    )
    unit = XbrlUnit(
        unit_id="EUR",
        measure_uri="iso4217:EUR",
        measure_qname=QName(namespace=_ISO4217_NS, local_name="EUR", prefix="iso4217"),
        simple_measure_count=1,
    )
    concept = QName(namespace=_SAMPLE_NS, local_name="B", prefix="tx")
    contexts: dict[str, XbrlContext] = {}
    facts: list[Fact] = []
    for index in range(fact_count):
        context_id = f"ctx{index}"
        contexts[context_id] = XbrlContext(
            context_id=context_id,
            entity=entity,
            period=reporting_period,
        )
        facts.append(
            Fact(
                concept=concept,
                context_ref=context_id,
                unit_ref="EUR",
                value=str(index + 1),
                decimals="0",
            )
        )

    return XbrlInstance(
        taxonomy_entry_point=_SAMPLE_TAXONOMY_PATH,
        schema_ref_href=str(_SAMPLE_TAXONOMY_PATH),
        entity=entity,
        period=reporting_period,
        contexts=contexts,
        units={"EUR": unit},
        facts=facts,
    )


def _measure_basic_validation_large_instance() -> tuple[float, Any]:
    loader = TaxonomyLoader(cache=TaxonomyCache(), settings=LoaderSettings(allow_network=False))
    taxonomy = loader.load(_SAMPLE_TAXONOMY_PATH)
    instance = _make_synthetic_basic_instance()

    start = time.perf_counter()
    report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)
    elapsed = time.perf_counter() - start
    return elapsed, report


def _make_formula_validation_taxonomy() -> TaxonomyStructure:
    concept = QName(namespace=_SAMPLE_NS, local_name="B", prefix="tx")
    assertion = ValueAssertionDefinition(
        assertion_id="perf:positive-b",
        label="B must be positive",
        severity="error",
        abstract=False,
        variables=(
            FactVariableDefinition(
                variable_name="amount",
                concept_filter=concept,
            ),
        ),
        precondition_xpath=None,
        test_xpath="$amount gt 0",
    )
    metadata = TaxonomyMetadata(
        name="SyntheticFormulaPerformanceTaxonomy",
        version="1.0",
        publisher="tests",
        entry_point_path=_SAMPLE_TAXONOMY_PATH,
        loaded_at=datetime(2024, 1, 1),
        declared_languages=("en",),
    )
    item_type = QName(namespace=_XBRLI_NS, local_name="monetaryItemType", prefix="xbrli")
    item_sg = QName(namespace=_XBRLI_NS, local_name="item", prefix="xbrli")
    return TaxonomyStructure(
        metadata=metadata,
        concepts={
            concept: Concept(
                qname=concept,
                data_type=item_type,
                substitution_group=item_sg,
                period_type="instant",
                nillable=True,
                abstract=False,
                monetary_item_type=True,
            )
        },
        labels=None,
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
        formula_assertion_set=FormulaAssertionSet(assertions=(assertion,)),
    )


def _measure_formula_validation_large_instance() -> tuple[float, Any]:
    taxonomy = _make_formula_validation_taxonomy()
    instance = _make_synthetic_basic_instance()

    start = time.perf_counter()
    report = InstanceValidator(taxonomy=taxonomy).validate_sync(instance)
    elapsed = time.perf_counter() - start
    return elapsed, report


def _record_and_assert_performance(
    *,
    key: str,
    label: str,
    elapsed: float,
    metadata: dict[str, object],
) -> None:
    previous_history = _history_payload()
    previous_run = previous_history.get(key)

    updated_history = dict(previous_history)
    updated_history[key] = {
        "label": label,
        "elapsed_seconds": elapsed,
        "recorded_at": datetime.now(UTC).isoformat(),
        **metadata,
    }
    _write_history(updated_history)

    if previous_run is None:
        return

    previous_elapsed = float(previous_run["elapsed_seconds"])
    allowed_elapsed = max(
        previous_elapsed * ALLOWED_REGRESSION_RATIO,
        previous_elapsed + ALLOWED_REGRESSION_ABSOLUTE_SECONDS,
    )
    delta = elapsed - previous_elapsed

    assert elapsed <= allowed_elapsed, (
        f"{label} regressed from {previous_elapsed:.3f}s to {elapsed:.3f}s "
        f"(delta {delta:+.3f}s, allowed up to {allowed_elapsed:.3f}s based on "
        f"{ALLOWED_REGRESSION_RATIO:.0%} ratio / "
        f"{ALLOWED_REGRESSION_ABSOLUTE_SECONDS:.0e}s absolute tolerance)."
    )


def _assert_performance(case: _PerformanceCase) -> None:
    entry_point = case.entry_point.resolve()
    if not entry_point.exists():
        pytest.skip(f"Taxonomy cache entry point not found: {entry_point}")

    elapsed, taxonomy = _measure_taxonomy_load(entry_point)

    assert len(taxonomy.concepts) > 0, f"{case.label} produced no concepts"

    _record_and_assert_performance(
        key=case.key,
        label=case.label,
        elapsed=elapsed,
        metadata={
            "entry_point": str(entry_point),
            "concept_count": len(taxonomy.concepts),
            "table_count": len(taxonomy.tables),
        },
    )


@pytest.mark.skipif(
    not _FINREP_IND_CASE.entry_point.exists(), reason="FINREP IND cache taxonomy not present"
)
def test_finrep_ind_cache_taxonomy_load_time_is_not_slower_than_last_run() -> None:
    _assert_performance(_FINREP_IND_CASE)


@pytest.mark.skipif(
    not _COREP_LR_CASE.entry_point.exists(), reason="COREP LR cache taxonomy not present"
)
def test_corep_lr_cache_taxonomy_load_time_is_not_slower_than_last_run() -> None:
    _assert_performance(_COREP_LR_CASE)


@pytest.mark.skipif(
    not _FINREP_IND_CASE.entry_point.exists(), reason="FINREP IND cache taxonomy not present"
)
def test_finrep_ind_warm_taxonomy_cache_hit_time_is_not_slower_than_last_run() -> None:
    elapsed, taxonomy = _measure_warm_taxonomy_cache_hit(_FINREP_IND_CASE.entry_point)
    _record_and_assert_performance(
        key="finrep_ind_warm_cache_hit",
        label="FINREP IND warm taxonomy cache hit",
        elapsed=elapsed,
        metadata={
            "entry_point": str(_FINREP_IND_CASE.entry_point.resolve()),
            "concept_count": len(taxonomy.concepts),
            "table_count": len(taxonomy.tables),
        },
    )


@pytest.mark.skipif(
    not _COREP_LR_CASE.entry_point.exists(), reason="COREP LR cache taxonomy not present"
)
def test_corep_lr_warm_taxonomy_cache_hit_time_is_not_slower_than_last_run() -> None:
    elapsed, taxonomy = _measure_warm_taxonomy_cache_hit(_COREP_LR_CASE.entry_point)
    _record_and_assert_performance(
        key="corep_lr_warm_cache_hit",
        label="COREP LR warm taxonomy cache hit",
        elapsed=elapsed,
        metadata={
            "entry_point": str(_COREP_LR_CASE.entry_point.resolve()),
            "concept_count": len(taxonomy.concepts),
            "table_count": len(taxonomy.tables),
        },
    )


@pytest.mark.skipif(
    not (_SAMPLE_TAXONOMY_PATH.exists() and _SAMPLE_INSTANCE_PATH.exists()),
    reason="Sample taxonomy instance data not present",
)
def test_sample_instance_open_with_warm_taxonomy_time_is_not_slower_than_last_run() -> None:
    elapsed, instance = _measure_sample_instance_open_with_warm_taxonomy()
    _record_and_assert_performance(
        key="sample_instance_open_warm_taxonomy",
        label="Sample instance open with warm taxonomy",
        elapsed=elapsed,
        metadata={
            "instance_path": str(_SAMPLE_INSTANCE_PATH),
            "fact_count": len(instance.facts),
            "context_count": len(instance.contexts),
        },
    )


@pytest.mark.skipif(not _SAMPLE_TAXONOMY_PATH.exists(), reason="Sample taxonomy not present")
def test_basic_large_instance_validation_time_is_not_slower_than_last_run() -> None:
    elapsed, report = _measure_basic_validation_large_instance()
    _record_and_assert_performance(
        key="basic_large_instance_validation",
        label="Basic taxonomy large synthetic instance validation",
        elapsed=elapsed,
        metadata={
            "fact_count": SYNTHETIC_FACT_COUNT,
            "finding_count": len(report.findings),
            "stage_timings": {stage.name: stage.elapsed_seconds for stage in report.stage_timings},
        },
    )


@pytest.mark.skipif(not _SAMPLE_TAXONOMY_PATH.exists(), reason="Sample taxonomy not present")
def test_formula_large_instance_validation_time_is_not_slower_than_last_run() -> None:
    elapsed, report = _measure_formula_validation_large_instance()
    _record_and_assert_performance(
        key="formula_large_instance_validation",
        label="Formula large synthetic instance validation",
        elapsed=elapsed,
        metadata={
            "fact_count": SYNTHETIC_FACT_COUNT,
            "finding_count": len(report.findings),
            "stage_timings": {stage.name: stage.elapsed_seconds for stage in report.stage_timings},
        },
    )

"""Performance regression checks for real cache-backed taxonomy entry points."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from bde_xbrl_editor.taxonomy import LoaderSettings, TaxonomyCache, TaxonomyLoader

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_HISTORY_PATH = REPO_ROOT / ".benchmarks" / "taxonomy_load_history.json"
ALLOWED_REGRESSION_RATIO = 1.20


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


def _assert_performance(case: _PerformanceCase) -> None:
    entry_point = case.entry_point.resolve()
    if not entry_point.exists():
        pytest.skip(f"Taxonomy cache entry point not found: {entry_point}")

    previous_history = _history_payload()
    previous_run = previous_history.get(case.key)
    elapsed, taxonomy = _measure_taxonomy_load(entry_point)

    updated_history = dict(previous_history)
    updated_history[case.key] = {
        "label": case.label,
        "entry_point": str(entry_point),
        "elapsed_seconds": elapsed,
        "concept_count": len(taxonomy.concepts),
        "table_count": len(taxonomy.tables),
        "recorded_at": datetime.now(UTC).isoformat(),
    }
    _write_history(updated_history)

    assert len(taxonomy.concepts) > 0, f"{case.label} produced no concepts"

    if previous_run is None:
        return

    previous_elapsed = float(previous_run["elapsed_seconds"])
    allowed_elapsed = previous_elapsed * ALLOWED_REGRESSION_RATIO
    delta = elapsed - previous_elapsed

    assert elapsed <= allowed_elapsed, (
        f"{case.label} regressed from {previous_elapsed:.3f}s to {elapsed:.3f}s "
        f"(delta {delta:+.3f}s, allowed up to {allowed_elapsed:.3f}s based on "
        f"{ALLOWED_REGRESSION_RATIO:.0%} tolerance)."
    )


@pytest.mark.skipif(not _FINREP_IND_CASE.entry_point.exists(), reason="FINREP IND cache taxonomy not present")
def test_finrep_ind_cache_taxonomy_load_time_is_not_slower_than_last_run() -> None:
    _assert_performance(_FINREP_IND_CASE)


@pytest.mark.skipif(not _COREP_LR_CASE.entry_point.exists(), reason="COREP LR cache taxonomy not present")
def test_corep_lr_cache_taxonomy_load_time_is_not_slower_than_last_run() -> None:
    _assert_performance(_COREP_LR_CASE)

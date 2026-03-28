"""Performance benchmarks for taxonomy loading — SC-001 (≤50s) and SC-002 (<1s cached)."""

from __future__ import annotations

from pathlib import Path

import pytest

BDE_ENTRY_POINT = Path(__file__).parent.parent.parent.parent / "test_data" / "taxonomies" / "bde_sample" / "entry_point.xsd"


def _is_real_taxonomy() -> bool:
    if not BDE_ENTRY_POINT.exists():
        return False
    content = BDE_ENTRY_POINT.read_text()
    return "bde.es" in content


@pytest.mark.skipif(not _is_real_taxonomy(), reason="Real BDE taxonomy required for benchmarks")
def test_first_load_under_50_seconds(benchmark):
    """SC-001: First load of BDE taxonomy must complete in ≤50 seconds."""
    from bde_xbrl_editor.taxonomy import LoaderSettings, TaxonomyCache, TaxonomyLoader

    def load_fresh():
        cache = TaxonomyCache()
        loader = TaxonomyLoader(cache=cache, settings=LoaderSettings(allow_network=False))
        return loader.load(BDE_ENTRY_POINT)

    result = benchmark.pedantic(load_fresh, rounds=1, iterations=1)
    assert result is not None
    # pytest-benchmark will report the time; we also assert it directly
    assert benchmark.stats["mean"] < 50.0, (
        f"First load took {benchmark.stats['mean']:.1f}s — must be ≤50s (SC-001)"
    )


@pytest.mark.skipif(not _is_real_taxonomy(), reason="Real BDE taxonomy required for benchmarks")
def test_cached_access_under_1_second(benchmark):
    """SC-002: Cached access must complete in <1 second."""
    from bde_xbrl_editor.taxonomy import LoaderSettings, TaxonomyCache, TaxonomyLoader

    cache = TaxonomyCache()
    loader = TaxonomyLoader(cache=cache, settings=LoaderSettings(allow_network=False))
    # Pre-load to populate cache
    loader.load(BDE_ENTRY_POINT)

    def load_cached():
        return loader.load(BDE_ENTRY_POINT)

    result = benchmark(load_cached)
    assert result is not None
    assert benchmark.stats["mean"] < 1.0, (
        f"Cached access took {benchmark.stats['mean']:.3f}s — must be <1s (SC-002)"
    )

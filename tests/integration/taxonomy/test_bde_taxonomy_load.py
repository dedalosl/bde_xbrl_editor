"""Integration tests: load BDE sample taxonomy end-to-end.

These tests skip automatically when the BDE sample taxonomy is not present
in test_data/taxonomies/bde_sample/. Populate that directory with a real
(or trimmed) BDE taxonomy to run the full integration suite.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from bde_xbrl_editor.taxonomy import (
    LoaderSettings,
    TaxonomyCache,
    TaxonomyLoader,
    TaxonomyStructure,
)

BDE_ENTRY_POINT = Path(__file__).parent.parent.parent.parent / "test_data" / "taxonomies" / "bde_sample" / "entry_point.xsd"


@pytest.fixture(scope="module")
def bde_taxonomy() -> TaxonomyStructure:
    """Load BDE sample taxonomy once per test module."""
    if not BDE_ENTRY_POINT.exists():
        pytest.skip("BDE sample taxonomy not present — skipping integration test")
    # Check the minimal stub XSD has real XBRL content
    content = BDE_ENTRY_POINT.read_text()
    if "bde.es" not in content:
        pytest.skip("BDE sample taxonomy is a stub only — skipping full integration test")

    cache = TaxonomyCache()
    settings = LoaderSettings(allow_network=False, language_preference=["es", "en"])
    loader = TaxonomyLoader(cache=cache, settings=settings)
    return loader.load(BDE_ENTRY_POINT)


class TestBdeTaxonomyLoad:
    def test_taxonomy_loads_successfully(self, bde_taxonomy):
        assert bde_taxonomy is not None

    def test_has_concepts(self, bde_taxonomy):
        assert len(bde_taxonomy.concepts) > 0

    def test_has_tables(self, bde_taxonomy):
        assert len(bde_taxonomy.tables) > 0

    def test_at_least_one_label(self, bde_taxonomy):
        """At least one concept has a label in any language."""
        for qname in bde_taxonomy.concepts:
            label = bde_taxonomy.labels.resolve(qname)
            if qname.local_name in label:
                # label resolver returned QName fallback — not a real label; keep searching
                continue
            assert len(label) > 0
            return
        pytest.skip("No labelled concepts found — BDE sample taxonomy may be too minimal")

    def test_at_least_one_rc_code(self, bde_taxonomy):
        """At least one leaf BreakdownNode has an RC-code."""
        from bde_xbrl_editor.taxonomy.models import BreakdownNode

        def find_rc(node: BreakdownNode) -> bool:
            if node.rc_code:
                return True
            return any(find_rc(child) for child in node.children)

        for table in bde_taxonomy.tables:
            if find_rc(table.x_breakdown) or find_rc(table.y_breakdown):
                return
        pytest.skip("No RC-codes found — BDE sample taxonomy may not include them")

    def test_metadata_has_name(self, bde_taxonomy):
        assert bde_taxonomy.metadata.name
        assert len(bde_taxonomy.metadata.name) > 0

    def test_progress_callback_called(self):
        """Progress callback must be called ≥5 times during a full taxonomy load (FR-010)."""
        if not BDE_ENTRY_POINT.exists():
            pytest.skip("BDE sample taxonomy not present")
        content = BDE_ENTRY_POINT.read_text()
        if "bde.es" not in content:
            pytest.skip("BDE sample taxonomy is a stub only")

        cache = TaxonomyCache()
        loader = TaxonomyLoader(cache=cache, settings=LoaderSettings(allow_network=False))

        call_count = 0

        def counting_callback(msg: str, current: int, total: int) -> None:
            nonlocal call_count
            call_count += 1

        loader.load(BDE_ENTRY_POINT, progress_callback=counting_callback)
        assert call_count >= 5, (
            f"Expected ≥5 progress events, got {call_count}. "
            "TaxonomyLoader must emit at least one event per major loading phase."
        )


class TestBdeCacheIntegration:
    def test_second_load_uses_cache(self):
        """Second load of same path returns cached object (same identity) in <1 second."""
        if not BDE_ENTRY_POINT.exists():
            pytest.skip("BDE sample taxonomy not present")
        content = BDE_ENTRY_POINT.read_text()
        if "bde.es" not in content:
            pytest.skip("BDE sample taxonomy is a stub only")

        cache = TaxonomyCache()
        loader = TaxonomyLoader(cache=cache, settings=LoaderSettings(allow_network=False))

        first = loader.load(BDE_ENTRY_POINT)

        start = time.perf_counter()
        second = loader.load(BDE_ENTRY_POINT)
        elapsed = time.perf_counter() - start

        assert second is first, "Second load must return the same cached object"
        assert elapsed < 1.0, f"Cached access took {elapsed:.3f}s (must be <1 second)"

    def test_reload_returns_fresh_object(self):
        """reload() bypasses cache and returns a different object instance."""
        if not BDE_ENTRY_POINT.exists():
            pytest.skip("BDE sample taxonomy not present")
        content = BDE_ENTRY_POINT.read_text()
        if "bde.es" not in content:
            pytest.skip("BDE sample taxonomy is a stub only")

        cache = TaxonomyCache()
        loader = TaxonomyLoader(cache=cache, settings=LoaderSettings(allow_network=False))

        first = loader.load(BDE_ENTRY_POINT)
        second = loader.reload(BDE_ENTRY_POINT)

        assert second is not first, "reload() must return a fresh object, not the cached one"

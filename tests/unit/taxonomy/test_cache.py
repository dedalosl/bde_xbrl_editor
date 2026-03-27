"""Unit tests for TaxonomyCache — LRU eviction, invalidate, clear, list_cached, multi-version."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from bde_xbrl_editor.taxonomy.cache import TaxonomyCache
from bde_xbrl_editor.taxonomy.models import TaxonomyMetadata, TaxonomyStructure


def make_structure(name: str) -> TaxonomyStructure:
    """Build a minimal TaxonomyStructure for cache testing."""
    meta = TaxonomyMetadata(
        name=name,
        version="1.0",
        publisher="Test",
        entry_point_path=Path(f"/tmp/{name}.xsd"),
        loaded_at=datetime.now(),
        declared_languages=("es",),
    )
    resolver = MagicMock()
    return TaxonomyStructure(
        metadata=meta,
        concepts={},
        labels=resolver,
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
        formula_linkbase_path=None,
    )


class TestCacheBasicOperations:
    def test_put_and_get(self):
        cache = TaxonomyCache()
        s = make_structure("Taxonomy_A")
        cache.put("/a/entry.xsd", s)
        result = cache.get("/a/entry.xsd")
        assert result is s

    def test_get_missing_returns_none(self):
        cache = TaxonomyCache()
        assert cache.get("/nonexistent.xsd") is None

    def test_is_cached_true(self):
        cache = TaxonomyCache()
        cache.put("/a.xsd", make_structure("A"))
        assert cache.is_cached("/a.xsd") is True

    def test_is_cached_false(self):
        cache = TaxonomyCache()
        assert cache.is_cached("/missing.xsd") is False

    def test_invalidate_removes_entry(self):
        cache = TaxonomyCache()
        cache.put("/a.xsd", make_structure("A"))
        cache.invalidate("/a.xsd")
        assert cache.get("/a.xsd") is None

    def test_invalidate_missing_is_noop(self):
        cache = TaxonomyCache()
        cache.invalidate("/nonexistent.xsd")  # Should not raise

    def test_clear_removes_all(self):
        cache = TaxonomyCache()
        cache.put("/a.xsd", make_structure("A"))
        cache.put("/b.xsd", make_structure("B"))
        cache.clear()
        assert cache.get("/a.xsd") is None
        assert cache.get("/b.xsd") is None

    def test_list_cached_returns_metadata(self):
        cache = TaxonomyCache()
        s = make_structure("TaxA")
        cache.put("/a.xsd", s)
        listed = cache.list_cached()
        assert len(listed) == 1
        assert listed[0].name == "TaxA"

    def test_list_cached_empty(self):
        cache = TaxonomyCache()
        assert cache.list_cached() == []


class TestLRUEviction:
    def test_max_size_respected(self):
        cache = TaxonomyCache(max_size=3)
        for i in range(5):
            cache.put(f"/tax{i}.xsd", make_structure(f"Tax{i}"))
        # Only 3 most recent should be cached
        assert sum(1 for i in range(5) if cache.is_cached(f"/tax{i}.xsd")) == 3

    def test_lru_evicts_oldest(self):
        cache = TaxonomyCache(max_size=2)
        cache.put("/a.xsd", make_structure("A"))
        cache.put("/b.xsd", make_structure("B"))
        # Access A to make it recently used
        cache.get("/a.xsd")
        # Add C — should evict B (oldest unused)
        cache.put("/c.xsd", make_structure("C"))
        assert cache.is_cached("/a.xsd")
        assert cache.is_cached("/c.xsd")
        assert not cache.is_cached("/b.xsd")

    def test_max_size_property(self):
        cache = TaxonomyCache(max_size=7)
        assert cache.max_size == 7


class TestMultiVersionIsolation:
    def test_different_keys_independent(self):
        cache = TaxonomyCache()
        s1 = make_structure("V1")
        s2 = make_structure("V2")
        cache.put("/v1/entry.xsd", s1)
        cache.put("/v2/entry.xsd", s2)
        assert cache.get("/v1/entry.xsd") is s1
        assert cache.get("/v2/entry.xsd") is s2

    def test_overwrite_same_key(self):
        cache = TaxonomyCache()
        s1 = make_structure("Old")
        s2 = make_structure("New")
        cache.put("/a.xsd", s1)
        cache.put("/a.xsd", s2)
        assert cache.get("/a.xsd") is s2

    def test_list_cached_shows_two_versions(self):
        cache = TaxonomyCache()
        cache.put("/v1/entry.xsd", make_structure("TaxV1"))
        cache.put("/v2/entry.xsd", make_structure("TaxV2"))
        names = {m.name for m in cache.list_cached()}
        assert "TaxV1" in names
        assert "TaxV2" in names

"""TaxonomyCache — in-memory LRU session cache for loaded taxonomies."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from cachetools import LRUCache

from bde_xbrl_editor.taxonomy.models import TaxonomyCacheEntry, TaxonomyMetadata, TaxonomyStructure


class TaxonomyCache:
    """Session-scoped in-memory store for loaded taxonomies.

    LRU eviction at configurable max_size (default: 5).
    Not thread-safe in v1 — all access must be on the main thread.
    """

    def __init__(self, max_size: int = 5) -> None:
        self._cache: LRUCache[str, TaxonomyCacheEntry] = LRUCache(maxsize=max_size)

    def get(self, entry_point: str) -> TaxonomyStructure | None:
        """Retrieve a cached taxonomy, or None if not present."""
        entry = self._cache.get(entry_point)
        return entry.structure if entry else None

    def put(self, entry_point: str, structure: TaxonomyStructure) -> None:
        """Store a taxonomy under the given entry-point key."""
        entry = TaxonomyCacheEntry(
            entry_point_key=entry_point,
            structure=structure,
            cached_at=datetime.now(),
            source_path=Path(entry_point).parent,
        )
        self._cache[entry_point] = entry

    def invalidate(self, entry_point: str) -> None:
        """Remove a specific taxonomy from the cache (no-op if absent)."""
        self._cache.pop(entry_point, None)

    def clear(self) -> None:
        """Remove all entries from the cache."""
        self._cache.clear()

    def is_cached(self, entry_point: str) -> bool:
        """Return True if a taxonomy for this entry point is currently cached."""
        return entry_point in self._cache

    def list_cached(self) -> list[TaxonomyMetadata]:
        """Return TaxonomyMetadata for all currently cached taxonomies."""
        return [entry.structure.metadata for entry in self._cache.values()]

    @property
    def max_size(self) -> int:
        """Maximum number of taxonomies held simultaneously."""
        return self._cache.maxsize

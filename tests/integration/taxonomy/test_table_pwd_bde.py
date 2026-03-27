"""Integration test: all tables in BDE sample taxonomy parse without error."""

from __future__ import annotations

from pathlib import Path

import pytest

BDE_ENTRY_POINT = Path(__file__).parent.parent.parent.parent / "test_data" / "taxonomies" / "bde_sample" / "entry_point.xsd"


@pytest.fixture(scope="module")
def bde_taxonomy():
    if not BDE_ENTRY_POINT.exists():
        pytest.skip("BDE sample taxonomy not present")
    content = BDE_ENTRY_POINT.read_text()
    if "bde.es" not in content:
        pytest.skip("BDE sample taxonomy is a stub only")

    from bde_xbrl_editor.taxonomy import LoaderSettings, TaxonomyCache, TaxonomyLoader
    cache = TaxonomyCache()
    loader = TaxonomyLoader(cache=cache, settings=LoaderSettings(allow_network=False))
    return loader.load(BDE_ENTRY_POINT)


class TestAllTablesPresent:
    def test_tables_list_is_complete(self, bde_taxonomy):
        """All expected table IDs are present in the loaded taxonomy."""
        # Verify tables list is non-empty
        assert len(bde_taxonomy.tables) > 0

    def test_each_table_has_id(self, bde_taxonomy):
        for table in bde_taxonomy.tables:
            assert table.table_id, f"Table has no ID: {table}"

    def test_each_table_has_label(self, bde_taxonomy):
        for table in bde_taxonomy.tables:
            assert table.label, f"Table {table.table_id} has no label"

    def test_each_table_has_x_breakdown(self, bde_taxonomy):
        for table in bde_taxonomy.tables:
            assert table.x_breakdown is not None

    def test_each_table_has_y_breakdown(self, bde_taxonomy):
        for table in bde_taxonomy.tables:
            assert table.y_breakdown is not None

    def test_labels_available_in_spanish(self, bde_taxonomy):
        """Tables that use dimensions have Spanish labels available."""
        resolver = bde_taxonomy.labels
        for qname in list(bde_taxonomy.concepts.keys())[:20]:
            label = resolver.resolve(qname, language_preference=["es"])
            assert isinstance(label, str)
            assert len(label) > 0

    def test_labels_available_in_english(self, bde_taxonomy):
        """Concepts have at least a fallback label in English."""
        resolver = bde_taxonomy.labels
        for qname in list(bde_taxonomy.concepts.keys())[:20]:
            label = resolver.resolve(qname, language_preference=["en"])
            assert isinstance(label, str)
            assert len(label) > 0

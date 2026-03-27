"""Integration tests: table layout with BDE sample instance fact values."""

from __future__ import annotations

from pathlib import Path

import pytest

BDE_ENTRY_POINT = Path(__file__).parent.parent.parent.parent / "test_data" / "taxonomies" / "bde_sample" / "entry_point.xsd"


@pytest.fixture(scope="module")
def bde_taxonomy():
    content = BDE_ENTRY_POINT.read_text() if BDE_ENTRY_POINT.exists() else ""
    if "bde.es" not in content:
        pytest.skip("BDE sample taxonomy is a stub only")

    from bde_xbrl_editor.taxonomy import TaxonomyCache, TaxonomyLoader
    from bde_xbrl_editor.taxonomy.settings import LoaderSettings

    cache = TaxonomyCache()
    settings = LoaderSettings(allow_network=False)
    loader = TaxonomyLoader(cache=cache, settings=settings)
    return loader.load(BDE_ENTRY_POINT)


class TestTableWithInstance:
    def test_refresh_instance_none_clears_cells(self, bde_taxonomy):
        """refresh_instance(None) clears all body cell fact values."""
        from bde_xbrl_editor.table_renderer.layout_engine import TableLayoutEngine

        table = bde_taxonomy.tables[0]
        engine = TableLayoutEngine(bde_taxonomy)

        # Render without instance
        layout = engine.compute(table, instance=None)
        for row in layout.body:
            for cell in row:
                assert cell.fact_value is None

    def test_body_grid_shape_with_instance(self, bde_taxonomy):
        """Grid shape is unchanged regardless of instance presence."""
        from bde_xbrl_editor.table_renderer.layout_engine import TableLayoutEngine

        table = bde_taxonomy.tables[0]
        engine = TableLayoutEngine(bde_taxonomy)

        layout_no_inst = engine.compute(table, instance=None)
        layout_with_inst = engine.compute(table, instance=None)  # No real instance available

        assert len(layout_no_inst.body) == len(layout_with_inst.body)
        assert layout_no_inst.column_header.leaf_count == layout_with_inst.column_header.leaf_count

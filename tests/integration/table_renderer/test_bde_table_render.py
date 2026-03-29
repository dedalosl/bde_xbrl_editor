"""Integration tests: BDE sample taxonomy table → ComputedTableLayout."""

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


class TestBdeTableRender:
    def test_first_table_renders(self, bde_taxonomy):
        """First table in BDE taxonomy renders without error."""
        from bde_xbrl_editor.table_renderer.layout_engine import TableLayoutEngine

        assert len(bde_taxonomy.tables) > 0
        table = bde_taxonomy.tables[0]
        engine = TableLayoutEngine(bde_taxonomy)
        layout = engine.compute(table)

        assert layout.column_header.leaf_count > 0
        assert layout.row_header.leaf_count > 0
        assert len(layout.body) == layout.row_header.leaf_count
        assert all(len(row) == layout.column_header.leaf_count for row in layout.body)

    def test_all_body_cells_no_fact_value(self, bde_taxonomy):
        """Without an instance all body cells have fact_value=None."""
        from bde_xbrl_editor.table_renderer.layout_engine import TableLayoutEngine

        table = bde_taxonomy.tables[0]
        engine = TableLayoutEngine(bde_taxonomy)
        layout = engine.compute(table)

        for row in layout.body:
            for cell in row:
                assert cell.fact_value is None

    def test_render_performance(self, bde_taxonomy):
        """BDE table renders in <3 seconds (SC-001)."""
        import time

        from bde_xbrl_editor.table_renderer.layout_engine import TableLayoutEngine

        table = bde_taxonomy.tables[0]
        engine = TableLayoutEngine(bde_taxonomy)
        start = time.perf_counter()
        engine.compute(table)
        elapsed = time.perf_counter() - start

        assert elapsed < 3.0, f"Table render took {elapsed:.2f}s (limit 3s)"

    def test_z_axis_switch_performance(self, bde_taxonomy):
        """Z-axis switch completes in <1 second (SC-006)."""
        import time

        from bde_xbrl_editor.table_renderer.layout_engine import TableLayoutEngine

        # Find a table with multiple Z members
        table_with_z = next(
            (t for t in bde_taxonomy.tables if t.z_breakdowns),
            bde_taxonomy.tables[0],
        )
        engine = TableLayoutEngine(bde_taxonomy)
        layout = engine.compute(table_with_z, z_index=0)

        if len(layout.z_members) > 1:
            start = time.perf_counter()
            engine.compute(table_with_z, z_index=1)
            elapsed = time.perf_counter() - start
            assert elapsed < 1.0, f"Z-axis switch took {elapsed:.2f}s (limit 1s)"

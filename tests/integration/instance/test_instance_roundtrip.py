"""Integration test: InstanceFactory → InstanceSerializer → round-trip XML verification."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from lxml import etree

BDE_ENTRY_POINT = (
    Path(__file__).parent.parent.parent.parent
    / "test_data"
    / "taxonomies"
    / "bde_sample"
    / "entry_point.xsd"
)


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


class TestInstanceRoundtrip:
    def test_factory_create_and_serialize(self, bde_taxonomy, tmp_path):
        from bde_xbrl_editor.instance import (
            InstanceFactory,
            InstanceSerializer,
            ReportingEntity,
            ReportingPeriod,
        )
        from bde_xbrl_editor.instance.constants import BDE_PBLO_NS, FILING_IND_NS, LINK_NS, XBRLI_NS

        entity = ReportingEntity(
            identifier="ES0123456789", scheme="http://www.bde.es/"
        )
        period = ReportingPeriod(
            period_type="instant", instant_date=date(2024, 12, 31)
        )

        factory = InstanceFactory(bde_taxonomy)
        table_ids = [t.table_id for t in bde_taxonomy.tables[:2]] or ["T1"]
        instance = factory.create(entity, period, table_ids, {})

        path = tmp_path / "test_output.xbrl"
        InstanceSerializer().save(instance, path)

        # Reload and verify structure
        tree = etree.parse(str(path))  # noqa: S320
        root = tree.getroot()

        assert root.tag == f"{{{XBRLI_NS}}}xbrl"
        assert root.find(f"{{{LINK_NS}}}schemaRef") is not None
        assert len(root.findall(f"{{{XBRLI_NS}}}context")) >= 1
        fi_indicators = root.findall(f".//{{{FILING_IND_NS}}}filingIndicator")
        estados = root.findall(f".//{{{BDE_PBLO_NS}}}CodigoEstado")
        assert fi_indicators == []
        assert len(estados) == len(bde_taxonomy.tables)
        assert len(root.findall(f"{{{XBRLI_NS}}}item")) == 0  # no facts yet

    def test_mark_saved_after_serialization(self, bde_taxonomy, tmp_path):
        from bde_xbrl_editor.instance import (
            InstanceFactory,
            InstanceSerializer,
            ReportingEntity,
            ReportingPeriod,
        )

        entity = ReportingEntity(identifier="ES123", scheme="http://www.bde.es/")
        period = ReportingPeriod(
            period_type="instant", instant_date=date(2024, 12, 31)
        )
        table_ids = [bde_taxonomy.tables[0].table_id]
        instance = InstanceFactory(bde_taxonomy).create(entity, period, table_ids, {})

        path = tmp_path / "saved.xbrl"
        InstanceSerializer().save(instance, path)

        assert instance.source_path == path
        assert instance.has_unsaved_changes is False

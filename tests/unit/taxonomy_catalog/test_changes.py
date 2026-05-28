"""Tests for catalog change detection."""

from __future__ import annotations

from bde_xbrl_editor.taxonomy_catalog.changes import (
    build_file_snapshot,
    detect_catalog_changes,
)
from bde_xbrl_editor.taxonomy_catalog.models import (
    CatalogMetadata,
    EntryPoint,
    Taxonomy,
    TaxonomyCatalogData,
)


def _sample_data(*, last_run: str, etag: str = "v1") -> TaxonomyCatalogData:
    return TaxonomyCatalogData(
        metadata=CatalogMetadata(last_run=last_run, total_count=1),
        taxonomies=(
            Taxonomy(
                id="t1",
                name="Tax One",
                category="C",
                subcategory="",
                status="vigente",
                owner="BDE",
                date="",
                spec_version="",
                comments="",
                url_base="",
                entry_points=(
                    EntryPoint(
                        name="ep",
                        url="https://example.com/a.xsd",
                        etag=etag,
                        is_updated_since_last_check=True,
                    ),
                ),
                source_url="",
                scraped_at="",
                has_entry_point_updates=True,
            ),
        ),
    )


def test_detect_flagged_updates_on_first_run() -> None:
    data = _sample_data(last_run="2026-01-01T00:00:00.000Z")
    report = detect_catalog_changes(data, previous_last_run=None, previous_snapshot=None)
    assert report.updated_files
    assert report.updated_files[0].url == "https://example.com/a.xsd"


def test_detect_signature_change() -> None:
    data = _sample_data(last_run="2026-01-02T00:00:00.000Z", etag="v2")
    snapshot = build_file_snapshot(_sample_data(last_run="2026-01-01T00:00:00.000Z", etag="v1"))
    report = detect_catalog_changes(
        data,
        previous_last_run="2026-01-01T00:00:00.000Z",
        previous_snapshot=snapshot,
    )
    assert report.scrape_is_newer
    assert any(ref.url == "https://example.com/a.xsd" for ref in report.updated_files)

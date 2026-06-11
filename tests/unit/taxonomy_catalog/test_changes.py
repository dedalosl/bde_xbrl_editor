"""Tests for catalog change detection."""

from __future__ import annotations

from bde_xbrl_editor.taxonomy_catalog.changes import (
    build_file_snapshot,
    collect_flagged_updates,
    detect_catalog_changes,
    detect_catalog_delta,
)
from bde_xbrl_editor.taxonomy_catalog.models import (
    CatalogMetadata,
    EntryPoint,
    ModuleFile,
    Taxonomy,
    TaxonomyCatalogData,
)


def _sample_data(
    *,
    last_run: str,
    etag: str = "v1",
    last_modified: str | None = None,
    content_length: int | None = 100,
) -> TaxonomyCatalogData:
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
                        last_modified=last_modified,
                        etag=etag,
                        content_length=content_length,
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


def test_delta_ignores_new_scrape_timestamp_when_files_are_same() -> None:
    previous = _sample_data(last_run="2026-01-01T00:00:00.000Z", etag="v1")
    current = _sample_data(last_run="2026-01-02T00:00:00.000Z", etag="v1")

    report = detect_catalog_delta(previous, current)

    assert report.scrape_is_newer
    assert not report.updated_files
    assert not report.has_updates


def test_delta_reports_changed_file_signature() -> None:
    previous = _sample_data(last_run="2026-01-01T00:00:00.000Z", etag="v1")
    current = _sample_data(last_run="2026-01-02T00:00:00.000Z", etag="v2")

    report = detect_catalog_delta(previous, current)

    assert any(ref.url == "https://example.com/a.xsd" for ref in report.updated_files)


def test_delta_ignores_one_second_bde_header_drift_when_file_size_is_same() -> None:
    previous = _sample_data(
        last_run="2026-01-01T00:00:00.000Z",
        last_modified="Thu, 17 Jun 2021 15:49:38 GMT",
        etag='"247db-5c4f8279282c3"',
        content_length=149467,
    )
    current = _sample_data(
        last_run="2026-01-02T00:00:00.000Z",
        last_modified="Thu, 17 Jun 2021 15:49:39 GMT",
        etag='"247db-5c4f8279e3a53"',
        content_length=149467,
    )

    report = detect_catalog_delta(previous, current)

    assert not report.updated_files


def test_delta_reports_content_length_change_even_when_last_modified_is_same() -> None:
    previous = _sample_data(
        last_run="2026-01-01T00:00:00.000Z",
        last_modified="Thu, 17 Jun 2021 15:49:38 GMT",
        etag='"v1"',
        content_length=149467,
    )
    current = _sample_data(
        last_run="2026-01-02T00:00:00.000Z",
        last_modified="Thu, 17 Jun 2021 15:49:38 GMT",
        etag='"v1"',
        content_length=149468,
    )

    report = detect_catalog_delta(previous, current)

    assert any(ref.url == "https://example.com/a.xsd" for ref in report.updated_files)


def test_delta_ignores_existing_file_when_metadata_temporarily_missing() -> None:
    previous = _sample_data(last_run="2026-01-01T00:00:00.000Z", etag="v1")
    current = _sample_data(last_run="2026-01-02T00:00:00.000Z", etag="")

    report = detect_catalog_delta(previous, current)

    assert not report.updated_files


def test_delta_ignores_non_file_related_link_header_changes() -> None:
    previous = TaxonomyCatalogData(
        metadata=CatalogMetadata(last_run="2026-01-01T00:00:00.000Z", total_count=0),
        taxonomies=(),
        taxonomy_related_links=(
            ModuleFile(
                label="Taxonomías del SRB",
                url="https://srb.europa.eu/en/content/reporting",
                last_modified="Wed, 10 Jun 2026 17:56:24 GMT",
                etag='"1781114184"',
            ),
        ),
    )
    current = TaxonomyCatalogData(
        metadata=CatalogMetadata(last_run="2026-01-02T00:00:00.000Z", total_count=0),
        taxonomies=(),
        taxonomy_related_links=(
            ModuleFile(
                label="Taxonomías del SRB",
                url="https://srb.europa.eu/en/content/reporting",
                last_modified="Wed, 10 Jun 2026 21:30:00 GMT",
                etag='"1781128200"',
            ),
        ),
    )

    report = detect_catalog_delta(previous, current)

    assert not report.updated_files


def test_collect_flagged_updates_ignores_non_file_related_links() -> None:
    data = TaxonomyCatalogData(
        metadata=CatalogMetadata(last_run="2026-01-01T00:00:00.000Z", total_count=0),
        taxonomies=(),
        taxonomy_related_links=(
            ModuleFile(
                label="Taxonomías del SRB",
                url="https://srb.europa.eu/en/content/reporting",
                is_updated_since_last_check=True,
            ),
        ),
    )

    assert collect_flagged_updates(data) == ()

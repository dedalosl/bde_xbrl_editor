"""Tests for taxonomy catalog JSON loading."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bde_xbrl_editor.taxonomy_catalog.loader import load_catalog, parse_catalog_document
from bde_xbrl_editor.taxonomy_catalog.models import TaxonomyCatalogData


def test_parse_minimal_catalog() -> None:
    raw = {
        "metadata": {
            "lastRun": "2026-01-01T00:00:00.000Z",
            "totalCount": 1,
            "taxonomiesWithUpdates": 1,
            "entryPointsWithUpdates": 1,
            "filesWithUpdates": 2,
        },
        "taxonomies": [
            {
                "id": "t1",
                "name": "Test Taxonomy",
                "category": "Cat",
                "subcategory": "",
                "status": "vigente",
                "owner": "BDE",
                "date": "2026-01-01",
                "specVersion": "XBRL 2.1",
                "comments": "",
                "urlBase": "",
                "entryPoints": [
                    {
                        "name": "http://example.com/tax.xsd",
                        "url": "https://example.com/tax.xsd",
                        "isUpdatedSinceLastCheck": True,
                    }
                ],
                "sourceUrl": "https://example.com/page",
                "scrapedAt": "2026-01-01T00:00:00.000Z",
                "hasEntryPointUpdates": True,
            }
        ],
    }
    data = parse_catalog_document(raw)
    assert isinstance(data, TaxonomyCatalogData)
    assert data.metadata.total_count == 1
    assert data.metadata.taxonomies_with_updates == 1
    assert data.metadata.entry_points_with_updates == 1
    assert data.metadata.files_with_updates == 2
    assert len(data.taxonomies) == 1
    tax = data.taxonomies[0]
    assert tax.name == "Test Taxonomy"
    assert tax.entry_points[0].is_updated_since_last_check is True
    assert tax.has_updates is True


def test_load_catalog_from_file(tmp_path: Path) -> None:
    raw = {
        "metadata": {"lastRun": "2026-01-02T00:00:00.000Z", "totalCount": 0},
        "taxonomies": [],
    }
    path = tmp_path / "taxonomies.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    data = load_catalog(path)
    assert data.metadata.last_run == "2026-01-02T00:00:00.000Z"


def test_load_catalog_missing_file(tmp_path: Path) -> None:
    from bde_xbrl_editor.taxonomy_catalog.loader import TaxonomyCatalogError

    with pytest.raises(TaxonomyCatalogError):
        load_catalog(tmp_path / "missing.json")

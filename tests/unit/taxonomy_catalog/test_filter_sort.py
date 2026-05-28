"""Tests for catalog filter and sort helpers."""

from __future__ import annotations

from bde_xbrl_editor.taxonomy_catalog.filter_sort import filter_taxonomies, sort_taxonomies
from bde_xbrl_editor.taxonomy_catalog.models import Taxonomy


def _tax(name: str, *, status: str = "vigente", category: str = "A", date: str = "") -> Taxonomy:
    return Taxonomy(
        id=name,
        name=name,
        category=category,
        subcategory="",
        status=status,  # type: ignore[arg-type]
        owner="",
        date=date,
        spec_version="",
        comments="",
        url_base="",
        entry_points=(),
        source_url="",
        scraped_at="",
    )


def test_filter_by_search_and_status() -> None:
    items = (_tax("Alpha", status="vigente"), _tax("Beta", status="no-vigente"))
    filtered = filter_taxonomies(items, search="alpha", status="vigente", category="")
    assert len(filtered) == 1
    assert filtered[0].name == "Alpha"


def test_sort_by_name() -> None:
    items = (_tax("Zeta"), _tax("Alpha"))
    sorted_items = sort_taxonomies(items, "name-asc")
    assert [t.name for t in sorted_items] == ["Alpha", "Zeta"]

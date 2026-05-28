"""Tests for entry-point URL resolution."""

from __future__ import annotations

from pathlib import Path

from bde_xbrl_editor.taxonomy_catalog.resolve import (
    catalog_path_candidates,
    merge_local_catalogs,
    resolve_entry_point_path,
)


def test_resolve_local_file(tmp_path: Path) -> None:
    xsd = tmp_path / "tax.xsd"
    xsd.write_text("<schema/>", encoding="utf-8")
    assert resolve_entry_point_path(str(xsd)) == xsd.resolve()


def test_resolve_via_catalog_prefix(tmp_path: Path) -> None:
    root = tmp_path / "mirror"
    sub = root / "es/fr/xbrl"
    sub.mkdir(parents=True)
    xsd = sub / "tax.xsd"
    xsd.write_text("<schema/>", encoding="utf-8")
    url = "https://www.bde.es/es/fr/xbrl/tax.xsd"
    catalog = {"https://www.bde.es/": root}
    resolved = resolve_entry_point_path(url, local_catalog=catalog)
    assert resolved == xsd.resolve()


def test_catalog_path_candidates_strips_fr_segment(tmp_path: Path) -> None:
    root = tmp_path / "mirror"
    without_fr = root / "es/xbrl/mod/tax.xsd"
    without_fr.parent.mkdir(parents=True)
    without_fr.write_text("<schema/>", encoding="utf-8")
    candidates = catalog_path_candidates(root, "es/fr/xbrl/mod/tax.xsd")
    assert without_fr.resolve() in candidates


def test_resolve_http_alternate_url(tmp_path: Path) -> None:
    root = tmp_path / "mirror"
    xsd = root / "es/fr/xbrl/fws/tax.xsd"
    xsd.parent.mkdir(parents=True)
    xsd.write_text("<schema/>", encoding="utf-8")
    catalog = merge_local_catalogs({"https://www.bde.es/": root})
    resolved = resolve_entry_point_path(
        "https://www.bde.es/es/fr/xbrl/fws/tax.xsd",
        local_catalog=catalog,
        alternate_urls=("http://www.bde.es/es/fr/xbrl/fws/tax.xsd",),
    )
    assert resolved == xsd.resolve()

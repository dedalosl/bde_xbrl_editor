"""Regression tests for the catalog loader update indicators."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6", reason="PySide6 not available - UI tests skipped")

from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QScrollArea

from bde_xbrl_editor.taxonomy_catalog.models import (
    CatalogChangeReport,
    CatalogFileRef,
)
from bde_xbrl_editor.ui.widgets.taxonomy_catalog_loader_widget import (
    TaxonomyCatalogLoaderWidget,
)


def _write_empty_catalog(path: Path) -> None:
    path.write_text(
        json.dumps({
            "metadata": {
                "lastRun": "2026-06-12T00:00:00.000Z",
                "totalCount": 0,
            },
            "taxonomies": [],
            "generalDocuments": [],
            "taxonomyRelatedLinks": [],
        }),
        encoding="utf-8",
    )


def _global_resources() -> list[dict[str, str]]:
    return [
        {
            "label": "Guía",
            "url": "https://www.bde.es/guia.pdf",
            "fileType": "pdf",
        }
    ]


def _write_catalog_with_taxonomies(path: Path) -> None:
    path.write_text(
        json.dumps({
            "metadata": {
                "lastRun": "2026-06-12T00:00:00.000Z",
                "totalCount": 2,
            },
            "taxonomies": [
                {
                    "id": "alpha",
                    "name": "Alpha",
                    "category": "A",
                    "subcategory": "",
                    "status": "vigente",
                    "owner": "BDE",
                    "date": "2026-01-01",
                    "specVersion": "XBRL 2.1",
                    "comments": "",
                    "urlBase": "",
                    "entryPoints": [],
                    "sourceUrl": "",
                    "scrapedAt": "2026-06-12T00:00:00.000Z",
                },
                {
                    "id": "beta",
                    "name": "Beta",
                    "category": "B",
                    "subcategory": "",
                    "status": "vigente",
                    "owner": "BDE",
                    "date": "2025-01-01",
                    "specVersion": "XBRL 2.1",
                    "comments": "",
                    "urlBase": "",
                    "entryPoints": [],
                    "sourceUrl": "",
                    "scrapedAt": "2026-06-12T00:00:00.000Z",
                },
            ],
            "generalDocuments": _global_resources(),
            "taxonomyRelatedLinks": [
                {
                    "label": "Taxonomías BDE",
                    "url": "https://www.bde.es/taxonomias.pdf",
                    "fileType": "pdf",
                }
            ],
        }),
        encoding="utf-8",
    )


def test_change_report_counts_general_document_without_taxonomy() -> None:
    report = CatalogChangeReport(
        catalog_last_run="2026-06-12T00:00:00.000Z",
        previous_last_run="2026-06-11T00:00:00.000Z",
        updated_files=(
            CatalogFileRef(
                label="Guía",
                url="https://www.bde.es/guia.pdf",
                taxonomy_name="Documentos generales",
                resource_kind="general_document",
            ),
        ),
        scrape_is_newer=True,
    )

    assert TaxonomyCatalogLoaderWidget._change_report_counts(report) == (0, 0, 1)


@pytest.mark.qt
def test_global_resources_render_in_own_panel_outside_taxonomy_list(
    qtbot,
    qapp,
    tmp_path: Path,
) -> None:
    catalog_path = tmp_path / "taxonomies.json"
    _write_catalog_with_taxonomies(catalog_path)
    widget = TaxonomyCatalogLoaderWidget(catalog_path=catalog_path)
    qtbot.addWidget(widget)

    widget._sort_combo.setCurrentIndex(widget._sort_combo.findData("name-desc"))
    widget._refresh_cards()
    object_names = [
        widget._cards_layout.itemAt(index).widget().objectName()
        for index in range(widget._cards_layout.count() - 1)
    ]
    assert object_names == ["TaxonomyCatalogCard", "TaxonomyCatalogCard"]
    assert not widget._global_resources_panel.isHidden()
    assert any(
        label.text() == "Global resources"
        for label in widget._global_resources_panel.findChildren(QLabel)
    )
    assert any(
        label.text() == "General document · Guía"
        for label in widget._global_resources_panel.findChildren(QLabel)
    )
    global_scroll = widget._global_resources_panel.findChildren(
        QScrollArea,
        "GlobalResourcesScroll",
    )
    assert len(global_scroll) == 1
    assert "background: #FFFFFF" in global_scroll[0].viewport().styleSheet()
    assert widget._global_resources_panel.parent().objectName() == "CatalogSidePanel"
    assert widget._side_panel_layout.itemAt(0).widget().objectName() == "OpenInstanceButton"
    assert widget._side_panel_layout.stretch(0) == 0
    assert widget._side_panel_layout.stretch(1) == 1

    widget._status_combo.setCurrentIndex(widget._status_combo.findData("no-vigente"))
    widget._refresh_cards()
    object_names = [
        widget._cards_layout.itemAt(index).widget().objectName()
        for index in range(widget._cards_layout.count() - 1)
    ]
    assert object_names == []
    assert not widget._global_resources_panel.isHidden()


@pytest.mark.qt
def test_instance_panel_has_no_reload_catalog_button(qtbot, qapp, tmp_path: Path) -> None:
    catalog_path = tmp_path / "taxonomies.json"
    _write_empty_catalog(catalog_path)
    widget = TaxonomyCatalogLoaderWidget(catalog_path=catalog_path)
    qtbot.addWidget(widget)

    assert not widget.findChildren(QFrame, "InstanceOpenPanel")
    assert widget._open_instance_btn.text() == "Abrir instancia…"
    assert "Recargar catálogo" not in [
        button.text() for button in widget.findChildren(QPushButton)
    ]


@pytest.mark.qt
def test_recent_instances_scroll_inside_instance_dialog(
    qtbot,
    qapp,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "bde_xbrl_editor.ui.widgets.loader_settings_dialog.load_recent_instances",
        lambda: [f"/tmp/sample-{index}.xbrl" for index in range(8)],
    )
    catalog_path = tmp_path / "taxonomies.json"
    _write_catalog_with_taxonomies(catalog_path)
    widget = TaxonomyCatalogLoaderWidget(catalog_path=catalog_path)
    qtbot.addWidget(widget)
    dialog = widget._build_instance_dialog()
    qtbot.addWidget(dialog)

    assert dialog.isModal()
    assert any(
        label.text() == "Abrir instancia existente"
        for label in dialog.findChildren(QLabel)
    )
    scroll_areas = dialog.findChildren(QScrollArea)
    assert len(scroll_areas) == 1
    assert "background: #FFFFFF" in scroll_areas[0].viewport().styleSheet()
    assert widget._side_panel_layout.stretch(0) == 0
    assert widget._side_panel_layout.stretch(1) == 1


@pytest.mark.qt
def test_update_tooltips_list_global_documents(qtbot, qapp, tmp_path: Path) -> None:
    catalog_path = tmp_path / "taxonomies.json"
    _write_catalog_with_taxonomies(catalog_path)
    widget = TaxonomyCatalogLoaderWidget(catalog_path=catalog_path)
    qtbot.addWidget(widget)

    widget._visible_catalog_update_refs = (
        CatalogFileRef(
            label="Guía",
            url="https://www.bde.es/guia.pdf",
            taxonomy_name="Documentos generales",
            resource_kind="general_document",
        ),
    )
    widget._catalog_header_update_counts = (0, 0, 1)
    widget._refresh_global_resources()
    widget._update_catalog_meta_label()
    widget._update_catalog_check_ui()

    assert "Archivos actualizados:" in widget._meta_label.toolTip()
    assert "Documentos generales: Guía" in widget._meta_label.toolTip()
    assert "Documentos generales: Guía" in widget._catalog_check_label.toolTip()
    assert any(
        "#FFFBEB" in row.styleSheet() and "#F59E0B" in row.styleSheet()
        for row in widget._global_resources_panel.findChildren(QFrame, "GlobalResourceRow")
    )
    assert any(
        label.text() == "Actualizado"
        for label in widget._global_resources_panel.findChildren(QLabel)
    )

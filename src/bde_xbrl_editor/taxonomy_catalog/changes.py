"""Detect taxonomy catalog updates since the user last opened the editor."""

from __future__ import annotations

from bde_xbrl_editor.taxonomy_catalog.models import (
    CatalogChangeReport,
    CatalogFileRef,
    TaxonomyCatalogData,
)


def _file_signature(last_modified: str | None, etag: str | None) -> str:
    return f"{last_modified or ''}|{etag or ''}"


def build_file_snapshot(data: TaxonomyCatalogData) -> dict[str, dict[str, str]]:
    """Map resource URL to display metadata and HTTP signature."""
    snapshot: dict[str, dict[str, str]] = {}

    def add(
        *,
        url: str,
        label: str,
        taxonomy_name: str,
        resource_kind: str,
        last_modified: str | None,
        etag: str | None,
    ) -> None:
        if not url:
            return
        snapshot[url] = {
            "label": label,
            "taxonomy_name": taxonomy_name,
            "resource_kind": resource_kind,
            "signature": _file_signature(last_modified, etag),
        }

    for tax in data.taxonomies:
        for ep in tax.entry_points:
            add(
                url=ep.url,
                label=ep.name or ep.url,
                taxonomy_name=tax.name,
                resource_kind="entry_point",
                last_modified=ep.last_modified,
                etag=ep.etag,
            )
        for doc in tax.reporting_files:
            add(
                url=doc.url,
                label=doc.label,
                taxonomy_name=tax.name,
                resource_kind="reporting_file",
                last_modified=doc.last_modified,
                etag=doc.etag,
            )
    for doc in data.general_documents:
        add(
            url=doc.url,
            label=doc.label,
            taxonomy_name="Documentos generales",
            resource_kind="general_document",
            last_modified=doc.last_modified,
            etag=doc.etag,
        )
    for link in data.taxonomy_related_links:
        add(
            url=link.url,
            label=link.label,
            taxonomy_name="Enlaces relacionados",
            resource_kind="related_link",
            last_modified=link.last_modified,
            etag=link.etag,
        )
    return snapshot


def collect_flagged_updates(data: TaxonomyCatalogData) -> tuple[CatalogFileRef, ...]:
    """Resources marked updated by the scraper since its last run."""
    refs: list[CatalogFileRef] = []
    for tax in data.taxonomies:
        for ep in tax.entry_points:
            if ep.is_updated_since_last_check:
                refs.append(
                    CatalogFileRef(
                        label=ep.name or ep.url,
                        url=ep.url,
                        taxonomy_name=tax.name,
                        resource_kind="entry_point",
                    )
                )
        for doc in tax.reporting_files:
            if doc.is_updated_since_last_check:
                refs.append(
                    CatalogFileRef(
                        label=doc.label,
                        url=doc.url,
                        taxonomy_name=tax.name,
                        resource_kind="reporting_file",
                    )
                )
    for doc in data.general_documents:
        if doc.is_updated_since_last_check:
            refs.append(
                CatalogFileRef(
                    label=doc.label,
                    url=doc.url,
                    taxonomy_name="Documentos generales",
                    resource_kind="general_document",
                )
            )
    for link in data.taxonomy_related_links:
        if link.is_updated_since_last_check:
            refs.append(
                CatalogFileRef(
                    label=link.label,
                    url=link.url,
                    taxonomy_name="Enlaces relacionados",
                    resource_kind="related_link",
                )
            )
    return tuple(refs)


def detect_catalog_changes(
    data: TaxonomyCatalogData,
    *,
    previous_last_run: str | None,
    previous_snapshot: dict[str, dict[str, str]] | None,
) -> CatalogChangeReport:
    """Compare current catalog data with the last acknowledged state."""
    current_run = data.metadata.last_run
    scrape_is_newer = bool(previous_last_run and current_run and current_run != previous_last_run)

    updated: dict[str, CatalogFileRef] = {}
    for ref in collect_flagged_updates(data):
        updated[ref.url] = ref

    current_snapshot = build_file_snapshot(data)
    if previous_snapshot:
        for url, meta in current_snapshot.items():
            prev = previous_snapshot.get(url)
            if prev is None:
                continue
            if meta.get("signature") != prev.get("signature"):
                updated.setdefault(
                    url,
                    CatalogFileRef(
                        label=meta.get("label", url),
                        url=url,
                        taxonomy_name=meta.get("taxonomy_name", ""),
                        resource_kind=meta.get("resource_kind", "file"),
                    ),
                )

    if scrape_is_newer and not updated:
        for tax in data.taxonomies:
            if tax.has_updates:
                for ep in tax.entry_points:
                    updated.setdefault(
                        ep.url,
                        CatalogFileRef(
                            label=ep.name or ep.url,
                            url=ep.url,
                            taxonomy_name=tax.name,
                            resource_kind="entry_point",
                        ),
                    )
                for doc in tax.reporting_files:
                    updated.setdefault(
                        doc.url,
                        CatalogFileRef(
                            label=doc.label,
                            url=doc.url,
                            taxonomy_name=tax.name,
                            resource_kind="reporting_file",
                        ),
                    )

    ordered = sorted(updated.values(), key=lambda r: (r.taxonomy_name.lower(), r.label.lower()))
    return CatalogChangeReport(
        catalog_last_run=current_run,
        previous_last_run=previous_last_run,
        updated_files=tuple(ordered),
        scrape_is_newer=scrape_is_newer,
    )

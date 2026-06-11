"""Detect taxonomy catalog updates since the user last opened the editor."""

from __future__ import annotations

from email.utils import parsedate_to_datetime

from bde_xbrl_editor.taxonomy_catalog.models import (
    CatalogChangeReport,
    CatalogFileRef,
    TaxonomyCatalogData,
)

_TRACKED_FILE_EXTENSIONS = (
    ".csv",
    ".doc",
    ".docx",
    ".pdf",
    ".xls",
    ".xlsx",
    ".xsd",
    ".zip",
)
_LAST_MODIFIED_DRIFT_TOLERANCE_SECONDS = 2


def _file_signature(
    last_modified: str | None,
    etag: str | None,
    content_length: int | None,
) -> str:
    return f"{last_modified or ''}|{etag or ''}|{content_length or ''}"


def _is_tracked_file_url(url: str) -> bool:
    """Return whether a URL represents a stable downloadable catalog resource."""
    lowered = url.lower().split("?", 1)[0].split("#", 1)[0]
    return lowered.endswith(_TRACKED_FILE_EXTENSIONS)


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
        content_length: int | None,
    ) -> None:
        if not url or not _is_tracked_file_url(url):
            return
        snapshot[url] = {
            "label": label,
            "taxonomy_name": taxonomy_name,
            "resource_kind": resource_kind,
            "last_modified": last_modified or "",
            "etag": etag or "",
            "content_length": str(content_length or ""),
            "signature": _file_signature(last_modified, etag, content_length),
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
                content_length=ep.content_length,
            )
        for doc in tax.reporting_files:
            add(
                url=doc.url,
                label=doc.label,
                taxonomy_name=tax.name,
                resource_kind="reporting_file",
                last_modified=doc.last_modified,
                etag=doc.etag,
                content_length=doc.content_length,
            )
    for doc in data.general_documents:
        add(
            url=doc.url,
            label=doc.label,
            taxonomy_name="Documentos generales",
            resource_kind="general_document",
            last_modified=doc.last_modified,
            etag=doc.etag,
            content_length=doc.content_length,
        )
    for link in data.taxonomy_related_links:
        add(
            url=link.url,
            label=link.label,
            taxonomy_name="Enlaces relacionados",
            resource_kind="related_link",
            last_modified=link.last_modified,
            etag=link.etag,
            content_length=link.content_length,
        )
    return snapshot


def _metadata_changed(
    previous_meta: dict[str, str],
    current_meta: dict[str, str],
) -> bool:
    previous_content_length = previous_meta.get("content_length", "")
    current_content_length = current_meta.get("content_length", "")
    if (
        previous_content_length
        and current_content_length
        and previous_content_length != current_content_length
    ):
        return True

    previous_last_modified = previous_meta.get("last_modified", "")
    current_last_modified = current_meta.get("last_modified", "")
    if previous_last_modified and current_last_modified:
        return _last_modified_changed(previous_last_modified, current_last_modified)

    previous_etag = previous_meta.get("etag", "")
    current_etag = current_meta.get("etag", "")
    if previous_etag and current_etag:
        return previous_etag != current_etag

    return False


def _last_modified_changed(previous: str, current: str) -> bool:
    if previous == current:
        return False

    try:
        previous_dt = parsedate_to_datetime(previous)
        current_dt = parsedate_to_datetime(current)
    except (TypeError, ValueError, IndexError):
        return previous != current

    drift_seconds = abs((current_dt - previous_dt).total_seconds())
    return drift_seconds > _LAST_MODIFIED_DRIFT_TOLERANCE_SECONDS


def collect_flagged_updates(data: TaxonomyCatalogData) -> tuple[CatalogFileRef, ...]:
    """Resources marked updated by the scraper since its last run."""
    refs: list[CatalogFileRef] = []

    def add_ref(*, label: str, url: str, taxonomy_name: str, resource_kind: str) -> None:
        if not _is_tracked_file_url(url):
            return
        refs.append(
            CatalogFileRef(
                label=label,
                url=url,
                taxonomy_name=taxonomy_name,
                resource_kind=resource_kind,
            )
        )

    for tax in data.taxonomies:
        for ep in tax.entry_points:
            if ep.is_updated_since_last_check:
                add_ref(
                    label=ep.name or ep.url,
                    url=ep.url,
                    taxonomy_name=tax.name,
                    resource_kind="entry_point",
                )
        for doc in tax.reporting_files:
            if doc.is_updated_since_last_check:
                add_ref(
                    label=doc.label,
                    url=doc.url,
                    taxonomy_name=tax.name,
                    resource_kind="reporting_file",
                )
    for doc in data.general_documents:
        if doc.is_updated_since_last_check:
            add_ref(
                label=doc.label,
                url=doc.url,
                taxonomy_name="Documentos generales",
                resource_kind="general_document",
            )
    for link in data.taxonomy_related_links:
        if link.is_updated_since_last_check:
            add_ref(
                label=link.label,
                url=link.url,
                taxonomy_name="Enlaces relacionados",
                resource_kind="related_link",
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
            if _metadata_changed(prev, meta):
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


def detect_catalog_delta(
    previous: TaxonomyCatalogData | None,
    current: TaxonomyCatalogData,
) -> CatalogChangeReport:
    """Compare two catalog JSON documents and report file-level changes.

    Unlike :func:`detect_catalog_changes`, this ignores scraper update flags and
    scrape timestamps by themselves. It is intended for background refreshes
    where the user should only be interrupted when the freshly downloaded JSON
    differs from the catalog currently loaded in the app.
    """
    previous_snapshot = build_file_snapshot(previous) if previous is not None else {}
    current_snapshot = build_file_snapshot(current)

    updated: list[CatalogFileRef] = []
    for url, meta in current_snapshot.items():
        previous_meta = previous_snapshot.get(url)
        if previous_meta is not None and not _metadata_changed(previous_meta, meta):
            continue
        updated.append(
            CatalogFileRef(
                label=meta.get("label", url),
                url=url,
                taxonomy_name=meta.get("taxonomy_name", ""),
                resource_kind=meta.get("resource_kind", "file"),
            )
        )

    ordered = sorted(updated, key=lambda r: (r.taxonomy_name.lower(), r.label.lower()))
    previous_last_run = previous.metadata.last_run if previous is not None else None
    return CatalogChangeReport(
        catalog_last_run=current.metadata.last_run,
        previous_last_run=previous_last_run,
        updated_files=tuple(ordered),
        scrape_is_newer=bool(
            previous_last_run
            and current.metadata.last_run
            and current.metadata.last_run != previous_last_run
        ),
    )

"""Load taxonomy catalog JSON from disk."""

from __future__ import annotations

import json
import os
from pathlib import Path

from bde_xbrl_editor.taxonomy_catalog.models import (
    CatalogMetadata,
    EntryPoint,
    ModuleFile,
    ReportingModule,
    Taxonomy,
    TaxonomyCatalogData,
)


class TaxonomyCatalogError(Exception):
    """Raised when catalog JSON cannot be loaded or parsed."""


def default_catalog_paths() -> tuple[Path, ...]:
    """Candidate locations for taxonomies.json, most preferred first."""
    from bde_xbrl_editor.taxonomy_catalog.scraper import (
        bundled_catalog_path,
        default_generated_catalog_path,
    )

    candidates: list[Path] = []
    env_path = os.environ.get("BDE_TAXONOMIES_CATALOG_PATH", "").strip()
    if env_path:
        candidates.append(Path(env_path).expanduser())
    candidates.extend(
        (
            default_generated_catalog_path(),
            bundled_catalog_path(),
            Path.home() / "git" / "bde_taxonomies_checker" / "scraper" / "data" / "taxonomies.json",
            Path.home()
            / "git"
            / "bde_taxonomies_checker"
            / "frontend"
            / "public"
            / "data"
            / "taxonomies.json",
        )
    )
    return tuple(candidates)


def resolve_catalog_path(explicit: str | Path | None = None) -> Path | None:
    """Return the first existing catalog path, or None."""
    if explicit:
        path = Path(explicit).expanduser()
        return path if path.is_file() else None
    for candidate in default_catalog_paths():
        if candidate.is_file():
            return candidate
    return None


def _file_metadata(raw: dict) -> dict:
    return {
        "last_modified": raw.get("lastModified"),
        "content_length": raw.get("contentLength"),
        "etag": raw.get("etag"),
        "is_updated_since_last_check": bool(raw.get("isUpdatedSinceLastCheck", False)),
    }


def _parse_entry_point(raw: dict) -> EntryPoint:
    return EntryPoint(
        name=str(raw.get("name", "")),
        url=str(raw.get("url", "")),
        **_file_metadata(raw),
    )


def _parse_module_file(raw: dict) -> ModuleFile:
    file_type = raw.get("fileType")
    return ModuleFile(
        label=str(raw.get("label", "")),
        url=str(raw.get("url", "")),
        file_type=str(file_type) if file_type else None,
        **_file_metadata(raw),
    )


def _parse_taxonomy(raw: dict) -> Taxonomy:
    entry_points = tuple(_parse_entry_point(ep) for ep in raw.get("entryPoints", []))
    reporting_files = tuple(_parse_module_file(rf) for rf in raw.get("reportingFiles", []))
    return Taxonomy(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", "")),
        category=str(raw.get("category", "")),
        subcategory=str(raw.get("subcategory", "")),
        status=raw.get("status", "vigente"),  # type: ignore[arg-type]
        owner=str(raw.get("owner", "")),
        date=str(raw.get("date", "")),
        spec_version=str(raw.get("specVersion", "")),
        comments=str(raw.get("comments", "")),
        url_base=str(raw.get("urlBase", "")),
        entry_points=entry_points,
        reporting_files=reporting_files,
        reporting_module_url=raw.get("reportingModuleUrl"),
        source_url=str(raw.get("sourceUrl", "")),
        scraped_at=str(raw.get("scrapedAt", "")),
        has_entry_point_updates=bool(raw.get("hasEntryPointUpdates", False)),
        has_reporting_file_updates=bool(raw.get("hasReportingFileUpdates", False)),
    )


def _parse_reporting_module(raw: dict) -> ReportingModule:
    return ReportingModule(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", "")),
        category=str(raw.get("category", "")),
        section=raw.get("section"),
        files=tuple(_parse_module_file(f) for f in raw.get("files", [])),
        source_url=str(raw.get("sourceUrl", "")),
        scraped_at=str(raw.get("scrapedAt", "")),
        has_updates=bool(raw.get("hasUpdates", False)),
    )


def parse_catalog_document(raw: dict) -> TaxonomyCatalogData:
    meta_raw = raw.get("metadata") or {}
    metadata = CatalogMetadata(
        last_run=str(meta_raw.get("lastRun", "")),
        total_count=int(meta_raw.get("totalCount", 0)),
        reporting_module_count=meta_raw.get("reportingModuleCount"),
        taxonomies_with_updates=meta_raw.get("taxonomiesWithUpdates"),
        entry_points_with_updates=meta_raw.get("entryPointsWithUpdates"),
        files_with_updates=meta_raw.get("filesWithUpdates"),
    )
    taxonomies = tuple(_parse_taxonomy(t) for t in raw.get("taxonomies", []))
    reporting_modules = tuple(
        _parse_reporting_module(m) for m in raw.get("reportingModules", [])
    )
    general_documents = tuple(
        _parse_module_file(d) for d in raw.get("generalDocuments", [])
    )
    taxonomy_related_links = tuple(
        _parse_module_file(link) for link in raw.get("taxonomyRelatedLinks", [])
    )
    return TaxonomyCatalogData(
        metadata=metadata,
        taxonomies=taxonomies,
        reporting_modules=reporting_modules,
        general_documents=general_documents,
        taxonomy_related_links=taxonomy_related_links,
    )


def load_catalog(path: str | Path) -> TaxonomyCatalogData:
    """Load and parse taxonomies.json from *path*."""
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        msg = f"Taxonomy catalog not found: {file_path}"
        raise TaxonomyCatalogError(msg)
    try:
        raw = json.loads(file_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise TaxonomyCatalogError(f"Cannot read catalog: {file_path}") from exc
    except json.JSONDecodeError as exc:
        raise TaxonomyCatalogError(f"Invalid JSON in catalog: {file_path}") from exc
    if not isinstance(raw, dict):
        raise TaxonomyCatalogError("Catalog root must be a JSON object")
    return parse_catalog_document(raw)

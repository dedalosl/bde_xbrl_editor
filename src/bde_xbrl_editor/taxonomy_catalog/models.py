"""Immutable models for BDE taxonomy catalog JSON (taxonomies.json)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CatalogStatus = Literal["vigente", "no-vigente"]
SortOption = Literal["date-desc", "date-asc", "name-asc", "name-desc"]
FilterStatus = Literal["all", "vigente", "no-vigente"]
GroupBy = Literal["category", "status", "timeline"]
LoaderPageMode = Literal["classic", "catalog"]


@dataclass(frozen=True, slots=True)
class FileResourceMetadata:
    last_modified: str | None = None
    content_length: int | None = None
    etag: str | None = None
    is_updated_since_last_check: bool = False


@dataclass(frozen=True, slots=True)
class EntryPoint(FileResourceMetadata):
    name: str = ""
    url: str = ""


@dataclass(frozen=True, slots=True)
class ModuleFile(FileResourceMetadata):
    label: str = ""
    url: str = ""
    file_type: str | None = None


@dataclass(frozen=True, slots=True)
class Taxonomy:
    id: str
    name: str
    category: str
    subcategory: str
    status: CatalogStatus
    owner: str
    date: str
    spec_version: str
    comments: str
    url_base: str
    entry_points: tuple[EntryPoint, ...]
    source_url: str
    scraped_at: str
    reporting_files: tuple[ModuleFile, ...] = ()
    reporting_module_url: str | None = None
    has_entry_point_updates: bool = False
    has_reporting_file_updates: bool = False

    @property
    def has_updates(self) -> bool:
        return self.has_entry_point_updates or self.has_reporting_file_updates


@dataclass(frozen=True, slots=True)
class ReportingModule:
    id: str
    name: str
    category: str
    files: tuple[ModuleFile, ...]
    source_url: str
    scraped_at: str
    section: str | None = None
    has_updates: bool = False


@dataclass(frozen=True, slots=True)
class CatalogMetadata:
    last_run: str
    total_count: int
    reporting_module_count: int | None = None
    taxonomies_with_updates: int | None = None
    entry_points_with_updates: int | None = None
    files_with_updates: int | None = None


@dataclass(frozen=True, slots=True)
class TaxonomyCatalogData:
    metadata: CatalogMetadata
    taxonomies: tuple[Taxonomy, ...]
    reporting_modules: tuple[ReportingModule, ...] = ()
    general_documents: tuple[ModuleFile, ...] = ()
    taxonomy_related_links: tuple[ModuleFile, ...] = ()


@dataclass(frozen=True, slots=True)
class CatalogFileRef:
    label: str
    url: str
    taxonomy_name: str
    resource_kind: str


@dataclass(frozen=True, slots=True)
class CatalogChangeReport:
    """Summary of catalog changes since the user last acknowledged updates."""

    catalog_last_run: str
    previous_last_run: str | None
    updated_files: tuple[CatalogFileRef, ...]
    scrape_is_newer: bool

    @property
    def has_updates(self) -> bool:
        return bool(self.updated_files)

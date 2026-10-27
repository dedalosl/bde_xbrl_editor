"""BDE taxonomy catalog loading and bundled scraper support."""

from bde_xbrl_editor.taxonomy_catalog.changes import (
    build_file_snapshot,
    detect_catalog_changes,
)
from bde_xbrl_editor.taxonomy_catalog.loader import (
    TaxonomyCatalogError,
    default_catalog_paths,
    load_catalog,
    resolve_catalog_path,
)
from bde_xbrl_editor.taxonomy_catalog.models import (
    CatalogChangeReport,
    LoaderPageMode,
    TaxonomyCatalogData,
)

__all__ = [
    "CatalogChangeReport",
    "LoaderPageMode",
    "TaxonomyCatalogData",
    "TaxonomyCatalogError",
    "build_file_snapshot",
    "default_catalog_paths",
    "detect_catalog_changes",
    "load_catalog",
    "resolve_catalog_path",
]

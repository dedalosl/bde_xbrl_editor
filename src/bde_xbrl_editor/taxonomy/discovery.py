"""DTS (Discoverable Taxonomy Set) discovery algorithm.

Performs recursive traversal of xs:import, xs:include, and linkbaseRef
elements to collect the complete set of schema and linkbase file paths that
constitute a taxonomy's DTS.

Network resolution is blocked by default (LoaderSettings.allow_network=False).
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from urllib.parse import urlparse

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import NS_LINK, NS_XLINK, NS_XSD
from bde_xbrl_editor.taxonomy.models import (
    TaxonomyDiscoveryError,
    TaxonomyParseError,
    UnsupportedTaxonomyFormatError,
)
from bde_xbrl_editor.taxonomy.settings import LoaderSettings

# Linkbase reference element QName
_LINKBASE_REF = f"{{{NS_LINK}}}linkbaseRef"
_ROLE_REF = f"{{{NS_LINK}}}roleRef"
_ARCROLE_REF = f"{{{NS_LINK}}}arcroleRef"
_LOC = f"{{{NS_LINK}}}loc"
_ANNOTATION = f"{{{NS_XSD}}}annotation"
_APPINFO = f"{{{NS_XSD}}}appinfo"
_IMPORT = f"{{{NS_XSD}}}import"
_INCLUDE = f"{{{NS_XSD}}}include"
_XLINK_HREF = f"{{{NS_XLINK}}}href"

# Known XBRL / XSD namespace imports to skip (standard schemaLocation URLs)
_SKIP_NS = {
    "http://www.xbrl.org/2003/instance",
    "http://www.xbrl.org/2003/linkbase",
    "http://www.w3.org/1999/xlink",
    "http://www.w3.org/2001/XMLSchema",
    "http://xbrl.org/2005/xbrldt",
    "http://xbrl.org/2008/generic",
    "http://xbrl.org/2008/label",
    "http://xbrl.org/2008/formula",
    "http://xbrl.org/PWD/2013-05-17/table",
}


def _is_remote(href: str) -> bool:
    """Return True if href is an http/https/ftp URL."""
    scheme = urlparse(href).scheme
    return scheme in ("http", "https", "ftp")


def _resolve_href(href: str, base_dir: Path, settings: LoaderSettings) -> Path | None:
    """Resolve an href relative to base_dir, applying local_catalog overrides.

    Returns the resolved absolute Path, or None if the reference should be skipped
    (e.g. it points to a known standard schema URL with no local override).
    Raises TaxonomyDiscoveryError if network is blocked and no local mapping exists.
    """
    if _is_remote(href):
        # Try local_catalog override first
        if settings.local_catalog:
            for prefix, local_root in settings.local_catalog.items():
                if href.startswith(prefix):
                    rel = href[len(prefix):].lstrip("/")
                    return (local_root / rel).resolve()
        if not settings.allow_network:
            return None  # caller will record as failing URI
        # network allowed — cannot resolve without HTTP client; skip gracefully
        return None

    # Relative path — resolve against base_dir
    resolved = (base_dir / href).resolve()
    return resolved


def discover_dts(
    entry_point: Path,
    settings: LoaderSettings,
    progress_callback=None,
    extra_entry_points: list[Path] | None = None,
) -> tuple[list[Path], list[Path], list[str], dict[Path, str], set[str]]:
    """Discover all schema and linkbase files reachable from entry_point.

    Args:
        entry_point: Primary taxonomy entry-point XSD (or XML) file.
        settings: Loader settings (network policy, local catalog, etc.).
        progress_callback: Optional progress callback.
        extra_entry_points: Additional schemas to seed the BFS queue alongside
            entry_point.  Use this to load multi-entry-point taxonomies such as
            BDE's, where tax.xsd (the version marker) is disconnected from the
            module schemas (mod/pc_con1.xsd, etc.) and both need to be seeded.

    Returns:
        (schema_paths, linkbase_paths, skipped_remote_urls, include_ns_map, declared_roles)
        - schema_paths / linkbase_paths: deduplicated lists of absolute Paths
        - skipped_remote_urls: remote URLs skipped (informational, not an error)
        - include_ns_map: maps xs:include'd schema Path → the parent schema's
          targetNamespace.  Used by the loader to supply the correct namespace
          when parsing schemas that have no targetNamespace of their own.
        - declared_roles: role URI values collected from link:roleRef elements
          encountered while traversing linkbase files.

    Raises:
        UnsupportedTaxonomyFormatError — entry_point is not a valid XBRL XSD.
        TaxonomyDiscoveryError — a LOCAL file reference could not be resolved.
        TaxonomyParseError — a file in the DTS is not well-formed XML.
    """
    entry_point = entry_point.resolve()

    if not entry_point.exists():
        raise UnsupportedTaxonomyFormatError(
            entry_point=str(entry_point),
            reason="File does not exist",
        )
    if entry_point.suffix.lower() not in (".xsd", ".xml"):
        raise UnsupportedTaxonomyFormatError(
            entry_point=str(entry_point),
            reason="Entry point must be an .xsd or .xml file",
        )

    visited_schemas: set[Path] = set()
    visited_linkbases: set[Path] = set()
    failing_uris: list[tuple[str, str]] = []
    skipped_remote: list[str] = []  # informational only
    # xs:include'd schema path → parent's targetNamespace
    include_ns_map: dict[Path, str] = {}
    declared_roles: set[str] = set()

    # Queue: (file_path, is_linkbase)
    queue = deque([(entry_point, False)])
    for ep in (extra_entry_points or []):
        ep = ep.resolve()
        if ep.exists() and ep.suffix.lower() in (".xsd", ".xml"):
            queue.append((ep, False))

    while queue:
        current, is_linkbase = queue.popleft()

        if is_linkbase:
            if current in visited_linkbases:
                continue
            visited_linkbases.add(current)
        else:
            if current in visited_schemas:
                continue
            visited_schemas.add(current)

        if not current.exists():
            failing_uris.append((str(current), "File not found on local filesystem"))
            continue

        try:
            tree = etree.parse(str(current))  # noqa: S320
        except etree.XMLSyntaxError as exc:
            raise TaxonomyParseError(
                file_path=str(current),
                message=str(exc),
                line=exc.lineno,
                column=exc.offset,
            ) from exc

        root = tree.getroot()
        base_dir = current.parent
        current_target_ns = root.get("targetNamespace", "")

        if is_linkbase:
            # Linkbases can reference additional schemas via roleRef/arcroleRef
            # (for role/arcrole type definitions) and additional linkbases via
            # linkbaseRef (e.g. a master linkbase that aggregates others).
            for ref_el in root.iter(_ROLE_REF, _ARCROLE_REF):
                href = ref_el.get(_XLINK_HREF)
                if ref_el.tag == _ROLE_REF:
                    role_uri = ref_el.get("roleURI")
                    if role_uri:
                        declared_roles.add(role_uri)
                if not href:
                    continue
                href = href.split("#")[0]
                if not href:
                    continue
                resolved = _resolve_href(href, base_dir, settings)
                if resolved is None:
                    if _is_remote(href):
                        skipped_remote.append(href)
                    continue
                queue.append((resolved, False))

            for lb_ref in root.iter(_LINKBASE_REF):
                href = lb_ref.get(_XLINK_HREF)
                if not href:
                    continue
                href = href.split("#")[0]
                if not href:
                    continue
                resolved = _resolve_href(href, base_dir, settings)
                if resolved is None:
                    if _is_remote(href):
                        skipped_remote.append(href)
                    continue
                queue.append((resolved, True))

            # loc elements reference resources in the DTS by href.
            # In standard XBRL those resources are already discoverable via
            # xs:import, but taxonomies like BDE's use loc to reference
            # rendering linkbases (.xml) and schemas (.xsd) in sibling
            # directories that have no xs:import path.  Follow them so we get
            # the complete file set.
            for loc_el in root.iter(_LOC):
                href = loc_el.get(_XLINK_HREF)
                if not href or _is_remote(href.split("#")[0]):
                    continue
                file_part = href.split("#")[0]
                if not file_part:
                    continue
                resolved = _resolve_href(file_part, base_dir, settings)
                if resolved is None:
                    continue
                suffix = resolved.suffix.lower()
                if suffix == ".xsd":
                    queue.append((resolved, False))
                elif suffix == ".xml":
                    queue.append((resolved, True))
            continue

        # --- xs:import ---
        for el in root.iter(_IMPORT):
            ns = el.get("namespace", "")
            if ns in _SKIP_NS:
                continue
            schema_loc = el.get("schemaLocation")
            if not schema_loc:
                continue
            resolved = _resolve_href(schema_loc, base_dir, settings)
            if resolved is None:
                if _is_remote(schema_loc):
                    skipped_remote.append(schema_loc)
                continue
            queue.append((resolved, False))

        # --- xs:include (shares parent's targetNamespace) ---
        for el in root.iter(_INCLUDE):
            schema_loc = el.get("schemaLocation")
            if not schema_loc:
                continue
            resolved = _resolve_href(schema_loc, base_dir, settings)
            if resolved is None:
                if _is_remote(schema_loc):
                    skipped_remote.append(schema_loc)
                continue
            # Record the parent's namespace so the schema parser can use it
            if current_target_ns and resolved not in include_ns_map:
                include_ns_map[resolved] = current_target_ns
            queue.append((resolved, False))

        # --- Annotation/appinfo linkbaseRef ---
        for appinfo in root.iter(_APPINFO):
            for lb_ref in appinfo.iter(_LINKBASE_REF):
                href = lb_ref.get(_XLINK_HREF)
                if not href:
                    continue
                # Strip fragment identifier
                href = href.split("#")[0]
                if not href:
                    continue
                resolved = _resolve_href(href, base_dir, settings)
                if resolved is None:
                    if _is_remote(href):
                        skipped_remote.append(href)
                    continue
                queue.append((resolved, True))

        # --- linkbase elements directly in the XSD (e.g. embedded) ---
        for lb_ref in root.iter(_LINKBASE_REF):
            # Skip ones already processed inside appinfo
            if lb_ref.getparent() is not None and lb_ref.getparent().tag == _APPINFO:
                continue
            href = lb_ref.get(_XLINK_HREF)
            if not href:
                continue
            href = href.split("#")[0]
            if not href:
                continue
            resolved = _resolve_href(href, base_dir, settings)
            if resolved is None:
                if _is_remote(href):
                    skipped_remote.append(href)
                continue
            queue.append((resolved, True))

    if failing_uris:
        raise TaxonomyDiscoveryError(
            entry_point=str(entry_point),
            failing_uris=failing_uris,
        )

    if progress_callback:
        progress_callback(
            f"DTS discovery complete: {len(visited_schemas)} schemas, "
            f"{len(visited_linkbases)} linkbases",
            1,
            6,
        )

    # De-duplicate skipped remote URLs (preserve order)
    seen: set[str] = set()
    unique_skipped = [u for u in skipped_remote if not (u in seen or seen.add(u))]  # type: ignore[func-returns-value]

    return (
        list(visited_schemas),
        list(visited_linkbases),
        unique_skipped,
        include_ns_map,
        declared_roles,
    )

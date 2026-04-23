"""DTS (Discoverable Taxonomy Set) discovery algorithm.

Performs recursive traversal of xs:import, xs:include, and linkbaseRef
elements to collect the complete set of schema and linkbase file paths that
constitute a taxonomy's DTS.

Network resolution is blocked by default (LoaderSettings.allow_network=False).
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
from urllib.parse import unquote, urlparse

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import NS_LINK, NS_XLINK, NS_XSD
from bde_xbrl_editor.taxonomy.models import (
    TaxonomyDiscoveryError,
    TaxonomyParseError,
    UnsupportedTaxonomyFormatError,
)
from bde_xbrl_editor.taxonomy.settings import LoaderSettings
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file

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
_DISCOVERY_PROGRESS_EVERY = 50

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
    "http://xbrl.org/2014/table",
}


def _is_remote(href: str) -> bool:
    """Return True if href is an http/https/ftp URL."""
    scheme = urlparse(href).scheme
    return scheme in ("http", "https", "ftp")


def _should_skip_linkbase(path: Path) -> bool:
    """Return True when a linkbase should be excluded from the DTS.

    Validation message linkbases are now consumed by the formula loader in
    order to render taxonomy-defined validation messages, so they must remain
    part of the discovered DTS.
    """
    return False


def _should_follow_locators(path: Path) -> bool:
    """Return True when link:loc traversal is useful for discovery.

    Label/error linkbases can contain hundreds of locators that only point back
    to resources already linked directly from their owning XSD or validation
    schema. Expanding those locators makes discovery dramatically slower
    without surfacing additional files we consume later.
    """
    name = path.name.lower()
    return "-lab-" not in name and "-err-" not in name


def _should_parse_linkbase_for_discovery(path: Path) -> bool:
    """Return True when the linkbase may contribute more DTS edges.

    Validation linkbases under ``.../val/...`` must still be inspected during
    discovery: BDE / Eurofiling validation packages reference assertion-set
    aggregator linkbases (``aset-*.xml``) from the entry-point XSD, and those
    aggregators only point to the actual rule files (``vr-*.xml`` containing
    ``va:valueAssertion`` resources) via ``link:loc`` locators. Skipping the
    locator traversal here would leave the formula assertions out of the DTS
    and surface them as "No formula assertions in this taxonomy" in the UI.

    Per-rule message linkbases (``vr-*-err-*.xml`` / ``vr-*-lab-*.xml``) are
    still not traversed through their locators by ``_should_follow_locators``
    to keep discovery fast, but they remain in the DTS so their resources can
    be parsed later by the taxonomy loader.
    """
    return _should_follow_locators(path)


def _catalog_path_candidates(local_root: Path, rel: str) -> list[Path]:
    """Return local-catalog candidate paths for a remote href suffix.

    Banco de España taxonomy URLs sometimes include an extra ``/fr/`` segment
    (for example ``/es/fr/xbrl/...`` or ``/es/fr/esrs/...``) while the local
    cache stores the same files without that segment (``/es/xbrl/...`` or
    ``/es/esrs/...``).  Try the direct mapping first, then a normalized
    variant with the ``/fr/`` segment removed as a fallback.
    """
    rel = rel.lstrip("/")
    candidates = [(local_root / rel).resolve()]

    parts = Path(rel).parts
    if len(parts) >= 3 and parts[1] == "fr":
        alt_rel = Path(parts[0], *parts[2:])
        alt_candidate = (local_root / alt_rel).resolve()
        if alt_candidate not in candidates:
            candidates.append(alt_candidate)

    return candidates


def _resolve_href(href: str, base_dir: Path, settings: LoaderSettings) -> Path | None:
    """Resolve an href relative to base_dir, applying local_catalog overrides.

    Returns the resolved absolute Path, or None if the reference should be skipped
    (e.g. it points to a known standard schema URL with no local override).
    Raises TaxonomyDiscoveryError if network is blocked and no local mapping exists.
    """
    href = href.split("#", 1)[0]
    if not href:
        return None

    if _is_remote(href):
        # Try local_catalog override first
        if settings.local_catalog:
            for prefix, local_root in settings.local_catalog.items():
                if href.startswith(prefix):
                    rel = href[len(prefix):].lstrip("/")
                    for candidate in _catalog_path_candidates(local_root, rel):
                        if candidate.exists():
                            return candidate
                    return _catalog_path_candidates(local_root, rel)[0]
        if not settings.allow_network:
            return None  # caller will record as failing URI
        # network allowed — cannot resolve without HTTP client; skip gracefully
        return None

    # Relative path — resolve against base_dir
    resolved = (base_dir / href).resolve()
    return resolved


def _element_base_dir(el: etree._Element, fallback: Path) -> Path:
    """Return the XML Base-aware directory for resolving attributes on *el*."""
    if not el.base:
        return fallback
    raw_base = el.base
    parsed = urlparse(raw_base)
    if parsed.scheme == "file":
        # lxml exposes percent-encoded file URIs (e.g. "%20" for spaces).
        # Convert back to a local filesystem path before Path resolution.
        base_value = unquote(parsed.path)
    else:
        base_value = unquote(raw_base)

    base_path = Path(base_value)
    if not base_path.is_absolute():
        base_path = (fallback / base_path).resolve()
    return base_path if raw_base.endswith("/") else base_path.parent


def _enqueue_if_new(
    queue: deque[tuple[Path, bool]],
    path: Path,
    *,
    is_linkbase: bool,
    pending_schemas: set[Path],
    pending_linkbases: set[Path],
    visited_schemas: set[Path],
    visited_linkbases: set[Path],
) -> bool:
    """Add a discovery target only if it isn't already queued or visited."""
    if is_linkbase and _should_skip_linkbase(path):
        return False
    if is_linkbase:
        if path in visited_linkbases or path in pending_linkbases:
            return False
        pending_linkbases.add(path)
    else:
        if path in visited_schemas or path in pending_schemas:
            return False
        pending_schemas.add(path)
    queue.append((path, is_linkbase))
    return True


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
    queue: deque[tuple[Path, bool]] = deque()
    pending_schemas: set[Path] = set()
    pending_linkbases: set[Path] = set()
    _enqueue_if_new(
        queue,
        entry_point,
        is_linkbase=False,
        pending_schemas=pending_schemas,
        pending_linkbases=pending_linkbases,
        visited_schemas=visited_schemas,
        visited_linkbases=visited_linkbases,
    )
    for ep in (extra_entry_points or []):
        ep = ep.resolve()
        if ep.exists() and ep.suffix.lower() in (".xsd", ".xml"):
            _enqueue_if_new(
                queue,
                ep,
                is_linkbase=False,
                pending_schemas=pending_schemas,
                pending_linkbases=pending_linkbases,
                visited_schemas=visited_schemas,
                visited_linkbases=visited_linkbases,
            )

    while queue:
        current, is_linkbase = queue.popleft()

        if is_linkbase:
            pending_linkbases.discard(current)
            if current in visited_linkbases:
                continue
            visited_linkbases.add(current)
        else:
            pending_schemas.discard(current)
            if current in visited_schemas:
                continue
            visited_schemas.add(current)

        if not current.exists():
            failing_uris.append((str(current), "File not found on local filesystem"))
            continue

        # Label/error linkbases are terminal for our discovery purposes:
        # we do not follow their locators, and they do not contribute extra
        # schema/linkbase edges needed by the loader.
        if is_linkbase and not _should_parse_linkbase_for_discovery(current):
            continue

        try:
            tree = parse_xml_file(current)
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
                resolved = _resolve_href(href, _element_base_dir(ref_el, base_dir), settings)
                if resolved is None:
                    if _is_remote(href):
                        skipped_remote.append(href)
                    continue
                _enqueue_if_new(
                    queue,
                    resolved,
                    is_linkbase=False,
                    pending_schemas=pending_schemas,
                    pending_linkbases=pending_linkbases,
                    visited_schemas=visited_schemas,
                    visited_linkbases=visited_linkbases,
                )

            for lb_ref in root.iter(_LINKBASE_REF):
                href = lb_ref.get(_XLINK_HREF)
                if not href:
                    continue
                href = href.split("#")[0]
                if not href:
                    continue
                resolved = _resolve_href(href, _element_base_dir(lb_ref, base_dir), settings)
                if resolved is None:
                    if _is_remote(href):
                        skipped_remote.append(href)
                    continue
                _enqueue_if_new(
                    queue,
                    resolved,
                    is_linkbase=True,
                    pending_schemas=pending_schemas,
                    pending_linkbases=pending_linkbases,
                    visited_schemas=visited_schemas,
                    visited_linkbases=visited_linkbases,
                )

            # loc elements reference resources in the DTS by href.
            # In standard XBRL those resources are already discoverable via
            # xs:import, but taxonomies like BDE's use loc to reference
            # rendering linkbases (.xml) and schemas (.xsd) in sibling
            # directories that have no xs:import path.  Follow them so we get
            # the complete file set.
            if _should_follow_locators(current):
                for loc_el in root.iter(_LOC):
                    href = loc_el.get(_XLINK_HREF)
                    if not href:
                        continue
                    file_part = href.split("#")[0]
                    if not file_part:
                        continue
                    resolved = _resolve_href(
                        file_part,
                        _element_base_dir(loc_el, base_dir),
                        settings,
                    )
                    if resolved is None:
                        if _is_remote(file_part):
                            skipped_remote.append(file_part)
                        continue
                    suffix = resolved.suffix.lower()
                    if suffix == ".xsd":
                        _enqueue_if_new(
                            queue,
                            resolved,
                            is_linkbase=False,
                            pending_schemas=pending_schemas,
                            pending_linkbases=pending_linkbases,
                            visited_schemas=visited_schemas,
                            visited_linkbases=visited_linkbases,
                        )
                    elif suffix == ".xml":
                        _enqueue_if_new(
                            queue,
                            resolved,
                            is_linkbase=True,
                            pending_schemas=pending_schemas,
                            pending_linkbases=pending_linkbases,
                            visited_schemas=visited_schemas,
                            visited_linkbases=visited_linkbases,
                        )
            continue

        # --- xs:import ---
        for el in root.iter(_IMPORT):
            ns = el.get("namespace", "")
            if ns in _SKIP_NS:
                continue
            schema_loc = el.get("schemaLocation")
            if not schema_loc:
                continue
            resolved = _resolve_href(schema_loc, _element_base_dir(el, base_dir), settings)
            if resolved is None:
                if _is_remote(schema_loc):
                    skipped_remote.append(schema_loc)
                continue
            _enqueue_if_new(
                queue,
                resolved,
                is_linkbase=False,
                pending_schemas=pending_schemas,
                pending_linkbases=pending_linkbases,
                visited_schemas=visited_schemas,
                visited_linkbases=visited_linkbases,
            )

        # --- xs:include (shares parent's targetNamespace) ---
        for el in root.iter(_INCLUDE):
            schema_loc = el.get("schemaLocation")
            if not schema_loc:
                continue
            resolved = _resolve_href(schema_loc, _element_base_dir(el, base_dir), settings)
            if resolved is None:
                if _is_remote(schema_loc):
                    skipped_remote.append(schema_loc)
                continue
            # Record the parent's namespace so the schema parser can use it
            if current_target_ns and resolved not in include_ns_map:
                include_ns_map[resolved] = current_target_ns
            _enqueue_if_new(
                queue,
                resolved,
                is_linkbase=False,
                pending_schemas=pending_schemas,
                pending_linkbases=pending_linkbases,
                visited_schemas=visited_schemas,
                visited_linkbases=visited_linkbases,
            )

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
                resolved = _resolve_href(href, _element_base_dir(lb_ref, base_dir), settings)
                if resolved is None:
                    if _is_remote(href):
                        skipped_remote.append(href)
                    continue
                _enqueue_if_new(
                    queue,
                    resolved,
                    is_linkbase=True,
                    pending_schemas=pending_schemas,
                    pending_linkbases=pending_linkbases,
                    visited_schemas=visited_schemas,
                    visited_linkbases=visited_linkbases,
                )

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
            resolved = _resolve_href(href, _element_base_dir(lb_ref, base_dir), settings)
            if resolved is None:
                if _is_remote(href):
                    skipped_remote.append(href)
                continue
            _enqueue_if_new(
                queue,
                resolved,
                is_linkbase=True,
                pending_schemas=pending_schemas,
                pending_linkbases=pending_linkbases,
                visited_schemas=visited_schemas,
                visited_linkbases=visited_linkbases,
            )

        if (
            progress_callback
            and (len(visited_schemas) + len(visited_linkbases)) % _DISCOVERY_PROGRESS_EVERY == 0
        ):
            progress_callback(
                f"Discovering DTS… {len(visited_schemas)} schemas, "
                f"{len(visited_linkbases)} linkbases",
                1,
                6,
            )

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

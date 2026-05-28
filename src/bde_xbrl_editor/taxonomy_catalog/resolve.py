"""Resolve catalog entry-point URLs to local filesystem paths."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from bde_xbrl_editor.taxonomy.discovery import _catalog_path_candidates


def catalog_path_candidates(local_root: Path, rel: str) -> list[Path]:
    """Return local-catalog candidate paths for a remote href suffix."""
    return _catalog_path_candidates(local_root, rel)


def discover_mirror_catalog() -> dict[str, Path]:
    """Build URL-prefix mappings from on-disk taxonomy mirrors under ``cache/``."""
    catalog: dict[str, Path] = {}
    roots = (
        Path.cwd() / "cache",
        Path(__file__).resolve().parents[3] / "cache",
        Path.home() / "git" / "bde_xbrl_editor" / "cache",
    )
    seen_hosts: set[str] = set()
    for cache_root in roots:
        if not cache_root.is_dir():
            continue
        for host_dir in sorted(cache_root.iterdir()):
            if not host_dir.is_dir():
                continue
            host = host_dir.name.strip()
            if not host or host in seen_hosts:
                continue
            seen_hosts.add(host)
            for scheme in ("http", "https", "ftp"):
                catalog[f"{scheme}://{host}/"] = host_dir
                catalog[f"{scheme}://{host}"] = host_dir
    return catalog


def merge_local_catalogs(
    *catalogs: dict[str, Path] | None,
) -> dict[str, Path]:
    """Merge catalog dicts; earlier entries win on duplicate prefixes."""
    merged: dict[str, Path] = {}
    for catalog in catalogs:
        if not catalog:
            continue
        for prefix, root in catalog.items():
            merged[prefix] = root
            if not prefix.endswith("/"):
                merged[f"{prefix}/"] = root
    return merged


def _url_variants(url: str) -> tuple[str, ...]:
    """Return URL strings to try when resolving an entry point."""
    trimmed = url.strip()
    if not trimmed:
        return ()
    variants: list[str] = [trimmed]
    parsed = urlparse(trimmed)
    if parsed.scheme in {"http", "https"}:
        alt_scheme = "https" if parsed.scheme == "http" else "http"
        alt = f"{alt_scheme}://{parsed.netloc}{parsed.path}"
        if parsed.query:
            alt = f"{alt}?{parsed.query}"
        if alt not in variants:
            variants.append(alt)
    return tuple(variants)


def resolve_entry_point_path(
    url: str,
    *,
    local_catalog: dict[str, Path] | None = None,
    alternate_urls: tuple[str, ...] = (),
) -> Path | None:
    """Map an entry-point URL to a local .xsd path when possible."""
    # User-configured mappings override auto-discovered cache mirrors.
    effective_catalog = merge_local_catalogs(discover_mirror_catalog(), local_catalog)

    for candidate_url in (*_url_variants(url), *alternate_urls):
        trimmed = candidate_url.strip()
        if not trimmed:
            continue

        if trimmed.startswith("file:"):
            parsed = urlparse(trimmed)
            if parsed.path:
                path_candidate = Path(parsed.path)
                if path_candidate.is_file():
                    return path_candidate.resolve()
            continue

        path_candidate = Path(trimmed).expanduser()
        if path_candidate.is_file():
            return path_candidate.resolve()

        if trimmed.startswith(("http://", "https://", "ftp://")):
            for prefix, local_root in sorted(
                effective_catalog.items(),
                key=lambda item: len(item[0]),
                reverse=True,
            ):
                if not trimmed.startswith(prefix):
                    continue
                rel = trimmed[len(prefix) :].lstrip("/")
                for candidate in catalog_path_candidates(local_root, rel):
                    if candidate.is_file():
                        return candidate.resolve()

        if path_candidate.exists():
            return path_candidate.resolve()
    return None

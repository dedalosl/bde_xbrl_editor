"""Runtime path helpers for source and bundled application layouts."""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator
from pathlib import Path


def _candidate_cache_roots() -> Iterator[Path]:
    env_cache = os.environ.get("BDE_XBRL_CACHE_DIR")
    if env_cache:
        yield Path(env_cache).expanduser()

    yield Path.cwd() / "cache"

    executable = Path(sys.executable).resolve()
    for parent in (executable.parent, *executable.parents):
        yield parent / "cache"

    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        root = Path(bundle_root).resolve()
        yield root / "cache"
        for parent in root.parents:
            yield parent / "cache"

    package_root = Path(__file__).resolve().parents[2]
    yield package_root / "cache"

    yield Path.home() / "git" / "bde_xbrl_editor" / "cache"


def iter_existing_cache_roots() -> Iterator[Path]:
    """Yield existing cache roots in runtime priority order."""
    seen: set[Path] = set()
    for candidate in _candidate_cache_roots():
        resolved = candidate.resolve()
        if resolved in seen or not resolved.is_dir():
            continue
        seen.add(resolved)
        yield resolved


def first_existing_cache_root() -> Path | None:
    """Return the first existing cache root for this runtime."""
    return next(iter_existing_cache_roots(), None)


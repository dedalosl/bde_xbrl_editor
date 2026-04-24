"""Repository hygiene checks for accidental copy artifacts."""

from __future__ import annotations

import re
from pathlib import Path

_ACCIDENTAL_COPY_RE = re.compile(r" \d+$")
_CHECKED_SUFFIXES = {".py", ".toml", ".md"}


def test_no_accidental_numbered_copy_artifacts() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    roots = (repo_root / "src", repo_root / "tests")

    offenders = sorted(
        path.relative_to(repo_root)
        for root in roots
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in _CHECKED_SUFFIXES
        and _ACCIDENTAL_COPY_RE.search(path.stem)
    )

    assert offenders == []

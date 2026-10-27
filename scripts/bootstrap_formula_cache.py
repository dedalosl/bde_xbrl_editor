"""Fetch the pinned public linkbases needed by the fast regression suite.

Run this before pytest on a fresh checkout. The runtime cache remains ignored;
upstream taxonomy documents are downloaded, not redistributed in this repository.
"""

from __future__ import annotations

import argparse
import hashlib
import tempfile
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

# SHA256 of the original upstream bytes, verified on 2026-10-27.
LINKBASES = (
    (
        "https://www.bde.es/es/fr/xbrl/func/error-formatting.xml",
        "c234508d890f68bd233817b3f22b26f040e56da4baccaedd12c2f5203efc874e",
    ),
    (
        "https://www.bde.es/es/fr/xbrl/func/external-attributes.xml",
        "03e4c32be76c0b356b3119a0b88bb85352213bfb3e4b90cb94e25fcd6639af69",
    ),
    (
        "https://www.eurofiling.info/eu/fr/xbrl/func/interval-arithmetics.xml",
        "90ec39def20f5f48d22e07adcd91e2a77ee403355efaa13424a5df63fc7a332e",
    ),
)
MAX_DOWNLOAD_BYTES = 1024 * 1024


class HTTPSRedirectHandler(HTTPRedirectHandler):
    """Do not allow an upstream redirect to downgrade transport security."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https":
            raise URLError(f"Refusing non-HTTPS redirect: {newurl}")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def bootstrap(cache_dir: Path) -> None:
    """Populate only the three pinned resources, preserving verified cache hits."""
    opener = build_opener(HTTPSRedirectHandler())
    for url, expected_hash in LINKBASES:
        parsed = urlsplit(url)
        destination = cache_dir / parsed.netloc / parsed.path.lstrip("/")
        if destination.is_file():
            if hashlib.sha256(destination.read_bytes()).hexdigest() == expected_hash:
                print(f"Verified {destination}")
                continue
            raise ValueError(f"Cached linkbase checksum mismatch: {destination}")

        request = Request(url, headers={"User-Agent": "bde-xbrl-editor-cache-bootstrap/1"})
        with opener.open(request, timeout=30) as response:
            content = response.read(MAX_DOWNLOAD_BYTES + 1)
        if len(content) > MAX_DOWNLOAD_BYTES:
            raise ValueError(f"Linkbase exceeds download size limit: {url}")
        if hashlib.sha256(content).hexdigest() != expected_hash:
            raise ValueError(f"Upstream linkbase checksum mismatch: {url}")

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as temporary:
                temporary_path = Path(temporary.name)
                temporary.write(content)
            temporary_path.replace(destination)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        print(f"Downloaded and verified {destination}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-dir", type=Path, default=Path(__file__).resolve().parents[1] / "cache"
    )
    args = parser.parse_args()
    try:
        bootstrap(args.cache_dir)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Formula cache bootstrap failed: {exc}\n")


if __name__ == "__main__":
    main()

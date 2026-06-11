"""Run the external BDE taxonomy checker scraper."""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Callable
from pathlib import Path


class TaxonomyCatalogScrapeError(Exception):
    """Raised when the external BDE taxonomy scraper cannot complete."""


def default_checker_root() -> Path:
    """Return the configured bde_taxonomies_checker project directory."""
    env_path = os.environ.get("BDE_TAXONOMIES_CHECKER_ROOT", "").strip()
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / "git" / "bde_taxonomies_checker"


def scraper_catalog_path(root: str | Path | None = None) -> Path:
    checker_root = Path(root).expanduser() if root is not None else default_checker_root()
    return checker_root / "scraper" / "data" / "taxonomies.json"


def run_catalog_scrape(
    root: str | Path | None = None,
    *,
    timeout_seconds: int = 900,
    should_cancel: Callable[[], bool] | None = None,
) -> Path:
    """Run the checker scraper and return the generated taxonomies.json path."""
    checker_root = Path(root).expanduser() if root is not None else default_checker_root()
    package_json = checker_root / "package.json"
    if not package_json.is_file():
        raise TaxonomyCatalogScrapeError(
            f"bde_taxonomies_checker project not found at {checker_root}"
        )

    try:
        started_at = time.monotonic()
        process = subprocess.Popen(
            ["npm", "run", "scrape"],
            cwd=checker_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout = ""
        stderr = ""
        while True:
            if should_cancel is not None and should_cancel():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise TaxonomyCatalogScrapeError("BDE scraper was cancelled")
            try:
                stdout, stderr = process.communicate(timeout=0.25)
                break
            except subprocess.TimeoutExpired:
                if time.monotonic() - started_at > timeout_seconds:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                    raise TaxonomyCatalogScrapeError("BDE scraper timed out") from None
    except FileNotFoundError as exc:
        raise TaxonomyCatalogScrapeError("npm was not found; cannot run BDE scraper") from exc

    if process.returncode != 0:
        details = (stderr or stdout or "").strip()
        if len(details) > 1200:
            details = f"{details[:1200]}..."
        raise TaxonomyCatalogScrapeError(
            "BDE scraper failed"
            + (f":\n{details}" if details else f" with exit code {process.returncode}")
        )

    output_path = scraper_catalog_path(checker_root)
    if not output_path.is_file():
        raise TaxonomyCatalogScrapeError(
            f"BDE scraper finished but did not create {output_path}"
        )
    return output_path

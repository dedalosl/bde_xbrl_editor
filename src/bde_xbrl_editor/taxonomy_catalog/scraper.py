"""Run the bundled BDE taxonomy catalog scraper."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path


class TaxonomyCatalogScrapeError(Exception):
    """Raised when the BDE taxonomy scraper cannot complete."""


def bundled_scraper_root() -> Path:
    """Return the scraper source directory bundled inside this Python package."""
    return Path(__file__).resolve().parent / "bde_taxonomies_scraper"


def bundled_catalog_path() -> Path:
    """Return the catalog JSON shipped with the installed package."""
    return scraper_catalog_path(bundled_scraper_root())


def default_generated_catalog_path() -> Path:
    """Return the writable default path for catalogs generated at runtime."""
    return Path.home() / ".bde_xbrl_editor" / "taxonomies.json"


def default_runtime_scraper_root() -> Path:
    """Return the writable runtime copy used for bundled scraper dependencies."""
    return Path.home() / ".bde_xbrl_editor" / "bde_taxonomies_scraper"


def _offline_scraper_candidates() -> tuple[Path, ...]:
    candidates: list[Path] = []
    env_path = os.environ.get("BDE_XBRL_OFFLINE_RUNTIME_DIR", "").strip()
    if env_path:
        root = Path(env_path).expanduser()
        candidates.extend((root / "bde_taxonomies_scraper", root))

    executable = Path(sys.executable).resolve()
    for parent in (executable.parent, *executable.parents):
        candidates.append(parent / "offline-runtime" / "bde_taxonomies_scraper")

    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        root = Path(bundle_root).resolve()
        candidates.append(root / "offline-runtime" / "bde_taxonomies_scraper")
        for parent in root.parents:
            candidates.append(parent / "offline-runtime" / "bde_taxonomies_scraper")

    return tuple(candidates)


def default_offline_scraper_root() -> Path | None:
    """Return a packaged offline scraper runtime, if one is available."""
    seen: set[Path] = set()
    for candidate in _offline_scraper_candidates():
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / "package.json").is_file() and _node_dependencies_installed(resolved):
            return resolved
    return None


def default_scraper_root() -> Path:
    """Return the configured scraper project directory."""
    env_path = os.environ.get("BDE_TAXONOMIES_SCRAPER_ROOT", "").strip()
    if not env_path:
        env_path = os.environ.get("BDE_TAXONOMIES_CHECKER_ROOT", "").strip()
    if env_path:
        return Path(env_path).expanduser()
    offline_root = default_offline_scraper_root()
    if offline_root is not None:
        return offline_root
    return bundled_scraper_root()


def default_checker_root() -> Path:
    """Return the configured scraper root.

    Kept for compatibility with callers that used the previous external-checker
    name.
    """
    return default_scraper_root()


def _scraper_package_root(root: str | Path | None = None) -> Path:
    candidate = Path(root).expanduser() if root is not None else default_scraper_root()
    legacy_scraper = candidate / "scraper"
    if (legacy_scraper / "package.json").is_file():
        return legacy_scraper
    if (candidate / "package.json").is_file():
        return candidate
    return candidate


def scraper_catalog_path(root: str | Path | None = None) -> Path:
    scraper_root = _scraper_package_root(root)
    return scraper_root / "data" / "taxonomies.json"


def prepare_runtime_scraper(source_root: str | Path | None = None) -> Path:
    """Copy the bundled scraper into a writable runtime directory."""
    source = _scraper_package_root(source_root or bundled_scraper_root())
    runtime = default_runtime_scraper_root()
    runtime.mkdir(parents=True, exist_ok=True)

    for filename in (
        "package.json",
        "package-lock.json",
        "tsconfig.json",
        "playwright.config.ts",
    ):
        source_file = source / filename
        if source_file.is_file():
            shutil.copy2(source_file, runtime / filename)

    src_dest = runtime / "src"
    if src_dest.exists():
        shutil.rmtree(src_dest)
    shutil.copytree(source / "src", src_dest)

    data_source = source / "data"
    if data_source.is_dir():
        shutil.copytree(data_source, runtime / "data", dirs_exist_ok=True)

    return runtime


def _node_dependencies_installed(scraper_root: Path) -> bool:
    node_modules = scraper_root / "node_modules"
    bin_dir = node_modules / ".bin"
    return (
        (node_modules / "playwright").is_dir()
        and (node_modules / "ts-node" / "dist" / "bin.js").is_file()
        and ((bin_dir / "ts-node").exists() or (bin_dir / "ts-node.cmd").exists())
    )


def _node_executable(scraper_root: Path) -> str:
    env_path = os.environ.get("BDE_TAXONOMIES_NODE_BINARY", "").strip()
    if env_path:
        return str(Path(env_path).expanduser())

    for candidate in (
        scraper_root / "node" / "node.exe",
        scraper_root / "node" / "bin" / "node.exe",
        scraper_root / "node" / "bin" / "node",
        scraper_root / "node.exe",
        scraper_root / "node",
    ):
        if candidate.is_file():
            return str(candidate)
    return "node"


def _bundled_playwright_browsers_path(scraper_root: Path) -> Path | None:
    for candidate in (
        scraper_root / "playwright-browsers",
        scraper_root / "ms-playwright",
    ):
        if candidate.is_dir():
            return candidate
    return None


def _scraper_process_env(scraper_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    browsers_path = _bundled_playwright_browsers_path(scraper_root)
    if browsers_path is not None:
        env.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(browsers_path))

    node_path = Path(_node_executable(scraper_root))
    if node_path.is_file() and node_path.parent.is_dir():
        env["PATH"] = str(node_path.parent) + os.pathsep + env.get("PATH", "")
    return env


def _scrape_command(scraper_root: Path) -> list[str]:
    ts_node_entry = scraper_root / "node_modules" / "ts-node" / "dist" / "bin.js"
    if _node_dependencies_installed(scraper_root) and ts_node_entry.is_file():
        return [str(_node_executable(scraper_root)), str(ts_node_entry), "src/index.ts"]
    return ["npm", "run", "scrape"]


def _run_process(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout_seconds: int,
    should_cancel: Callable[[], bool] | None,
    action: str,
) -> tuple[str, str]:
    try:
        started_at = time.monotonic()
        process = subprocess.Popen(
            args,
            cwd=cwd,
            env=env,
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
                raise TaxonomyCatalogScrapeError(f"{action} was cancelled")
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
                    raise TaxonomyCatalogScrapeError(f"{action} timed out") from None
    except FileNotFoundError as exc:
        program = Path(args[0]).name
        raise TaxonomyCatalogScrapeError(f"{program} was not found; cannot run {action}") from exc

    if process.returncode != 0:
        details = (stderr or stdout or "").strip()
        if len(details) > 1200:
            details = f"{details[:1200]}..."
        raise TaxonomyCatalogScrapeError(
            f"{action} failed"
            + (f":\n{details}" if details else f" with exit code {process.returncode}")
        )
    return stdout, stderr


def _ensure_node_dependencies(
    scraper_root: Path,
    *,
    timeout_seconds: int,
    should_cancel: Callable[[], bool] | None,
) -> None:
    if _node_dependencies_installed(scraper_root):
        return

    command = (
        ["npm", "ci"] if (scraper_root / "package-lock.json").is_file() else ["npm", "install"]
    )
    install_env = _scraper_process_env(scraper_root)
    install_env["NODE_ENV"] = "development"
    install_env["npm_config_production"] = "false"
    _run_process(
        command,
        cwd=scraper_root,
        env=install_env,
        timeout_seconds=timeout_seconds,
        should_cancel=should_cancel,
        action="BDE scraper dependency installation",
    )


def _runtime_scraper_root(root: str | Path | None) -> Path:
    scraper_root = _scraper_package_root(root)
    try:
        if scraper_root.resolve() == bundled_scraper_root().resolve():
            if _node_dependencies_installed(scraper_root):
                return scraper_root
            return prepare_runtime_scraper(scraper_root)
    except OSError:
        pass
    return scraper_root


def run_catalog_scrape(
    root: str | Path | None = None,
    *,
    output_path: str | Path | None = None,
    timeout_seconds: int = 900,
    setup_timeout_seconds: int = 900,
    should_cancel: Callable[[], bool] | None = None,
) -> Path:
    """Run the bundled scraper and return the generated taxonomies.json path."""
    scraper_root = _runtime_scraper_root(root)
    package_json = scraper_root / "package.json"
    if not package_json.is_file():
        raise TaxonomyCatalogScrapeError(
            f"BDE taxonomies scraper project not found at {scraper_root}"
        )
    catalog_output_path = (
        Path(output_path).expanduser()
        if output_path is not None
        else default_generated_catalog_path()
    )
    catalog_output_path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_node_dependencies(
        scraper_root,
        timeout_seconds=setup_timeout_seconds,
        should_cancel=should_cancel,
    )

    env = _scraper_process_env(scraper_root)
    env["BDE_TAXONOMIES_OUTPUT_PATH"] = str(catalog_output_path)
    _run_process(
        _scrape_command(scraper_root),
        cwd=scraper_root,
        env=env,
        timeout_seconds=timeout_seconds,
        should_cancel=should_cancel,
        action="BDE scraper",
    )

    if not catalog_output_path.is_file():
        raise TaxonomyCatalogScrapeError(
            f"BDE scraper finished but did not create {catalog_output_path}"
        )
    return catalog_output_path


def setup_catalog_scraper(
    root: str | Path | None = None,
    *,
    setup_timeout_seconds: int = 900,
    should_cancel: Callable[[], bool] | None = None,
) -> Path:
    """Prepare the bundled scraper runtime and install its Node dependencies."""
    scraper_root = _runtime_scraper_root(root)
    package_json = scraper_root / "package.json"
    if not package_json.is_file():
        raise TaxonomyCatalogScrapeError(
            f"BDE taxonomies scraper project not found at {scraper_root}"
        )
    _ensure_node_dependencies(
        scraper_root,
        timeout_seconds=setup_timeout_seconds,
        should_cancel=should_cancel,
    )
    return scraper_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the BDE taxonomy catalog scraper.")
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Scraper package directory. Defaults to the bundled scraper.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path for generated taxonomies.json. Defaults to ~/.bde_xbrl_editor/taxonomies.json.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=900,
        help="Maximum scrape time in seconds.",
    )
    parser.add_argument(
        "--setup-timeout",
        type=int,
        default=900,
        help="Maximum dependency setup time in seconds.",
    )
    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Install scraper dependencies without running a catalog scrape.",
    )
    args = parser.parse_args(argv)
    try:
        if args.setup_only:
            path = setup_catalog_scraper(
                args.root,
                setup_timeout_seconds=args.setup_timeout,
            )
        else:
            path = run_catalog_scrape(
                args.root,
                output_path=args.output,
                timeout_seconds=args.timeout,
                setup_timeout_seconds=args.setup_timeout,
            )
    except TaxonomyCatalogScrapeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

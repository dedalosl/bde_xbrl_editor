#!/usr/bin/env python3
"""Build a portable offline PyInstaller package for BDE XBRL Editor."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

APP_NAME = "BDE XBRL Editor"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRAPER_SOURCE = (
    PROJECT_ROOT
    / "src"
    / "bde_xbrl_editor"
    / "taxonomy_catalog"
    / "bde_taxonomies_scraper"
)
PYINSTALLER_SPEC = PROJECT_ROOT / "installer" / "pyinstaller" / f"{APP_NAME}.spec"


def _run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(args), flush=True)
    subprocess.run(args, cwd=cwd, env=env, check=True)


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _copy_required_scraper_files(target: Path) -> None:
    _remove(target)
    target.mkdir(parents=True)

    for filename in (
        "package.json",
        "package-lock.json",
        "tsconfig.json",
        "playwright.config.ts",
    ):
        shutil.copy2(SCRAPER_SOURCE / filename, target / filename)

    shutil.copytree(SCRAPER_SOURCE / "src", target / "src")
    shutil.copytree(SCRAPER_SOURCE / "data", target / "data")


def _node_executable_source() -> Path:
    """Return the Node executable to include in the offline runtime.

    The scraper invokes Node directly with its bundled ``ts-node`` entry
    point, so npm, headers, documentation, and global packages are not needed
    by the distributed application.
    """
    node_path = shutil.which("node")
    if node_path is None:
        raise RuntimeError("node was not found in PATH; install Node.js before building")

    node = Path(node_path).resolve()
    if not node.is_file():
        raise RuntimeError(f"Node executable does not exist: {node}")
    return node


def _copy_node_runtime(target: Path) -> None:
    source = _node_executable_source()
    destination = target / ("node.exe" if os.name == "nt" else "bin/node")
    print(f"Copying Node executable from {source}")
    _remove(target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if not destination.is_file():
        raise RuntimeError(f"Could not copy Node executable from {source}")


def prepare_offline_scraper_runtime(build_root: Path) -> Path:
    scraper_target = build_root / "bde_taxonomies_scraper"
    _copy_required_scraper_files(scraper_target)

    env = os.environ.copy()
    env["NODE_ENV"] = "development"
    env["npm_config_production"] = "false"
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(scraper_target / "playwright-browsers")

    _run(["npm", "ci"], cwd=scraper_target, env=env)
    _run(["npx", "playwright", "install", "chromium"], cwd=scraper_target, env=env)
    _copy_node_runtime(scraper_target / "node")
    return scraper_target


def _platform_slug() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower().replace(" ", "-")
    return f"{system}-{machine}" if machine else system


def _copy_cache(dist_dir: Path) -> None:
    cache_source = PROJECT_ROOT / "cache"
    if not cache_source.is_dir():
        return
    cache_target = dist_dir / "cache"
    _remove(cache_target)
    shutil.copytree(cache_source, cache_target)


def _remove_duplicate_macos_onedir(dist_dir: Path) -> None:
    app_bundle = dist_dir / f"{APP_NAME}.app"
    onedir_bundle = dist_dir / APP_NAME
    if app_bundle.is_dir() and onedir_bundle.is_dir():
        _remove(onedir_bundle)


def _zip_dir(source: Path, archive: Path) -> None:
    _remove(archive)
    archive.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in source.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(source.parent))


def build_pyinstaller_package(
    scraper_runtime: Path,
    dist_dir: Path,
    *,
    include_cache: bool,
) -> None:
    _remove(dist_dir)
    dist_dir.mkdir(parents=True)

    _run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            str(PYINSTALLER_SPEC),
            "--noconfirm",
            "--clean",
            "--distpath",
            str(dist_dir),
            "--workpath",
            str(PROJECT_ROOT / "build" / "pyinstaller-offline"),
        ],
        cwd=PROJECT_ROOT,
    )
    _remove_duplicate_macos_onedir(dist_dir)
    offline_target = dist_dir / "offline-runtime" / "bde_taxonomies_scraper"
    _remove(offline_target)
    offline_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(scraper_runtime, offline_target)
    if include_cache:
        _copy_cache(dist_dir)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a portable offline package with Python, Node, npm deps, and Playwright.",
    )
    parser.add_argument(
        "--build-root",
        type=Path,
        default=PROJECT_ROOT / "build" / "offline-runtime",
        help="Temporary build directory for the prepared scraper runtime.",
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=PROJECT_ROOT / "dist" / "offline" / _platform_slug(),
        help="Output directory for the PyInstaller bundle.",
    )
    parser.add_argument(
        "--skip-runtime",
        action="store_true",
        help="Reuse the prepared scraper runtime already present under --build-root.",
    )
    parser.add_argument(
        "--skip-pyinstaller",
        action="store_true",
        help="Only prepare the offline scraper runtime.",
    )
    parser.add_argument(
        "--no-zip",
        action="store_true",
        help="Do not create the final zip archive.",
    )
    parser.add_argument(
        "--include-cache",
        action="store_true",
        help="Copy the local cache/ directory into the offline package.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    build_root = args.build_root.resolve()
    dist_dir = args.dist_dir.resolve()

    try:
        if args.skip_runtime:
            scraper_runtime = build_root / "bde_taxonomies_scraper"
            if not scraper_runtime.is_dir():
                raise RuntimeError(f"Prepared scraper runtime not found: {scraper_runtime}")
        else:
            scraper_runtime = prepare_offline_scraper_runtime(build_root)

        if not args.skip_pyinstaller:
            build_pyinstaller_package(
                scraper_runtime,
                dist_dir,
                include_cache=args.include_cache,
            )
            if not args.no_zip:
                archive = dist_dir.parent / f"bde-xbrl-editor-{_platform_slug()}-offline.zip"
                _zip_dir(dist_dir, archive)
                print(f"Offline package archive: {archive}")
            print(f"Offline package directory: {dist_dir}")
        else:
            print(f"Offline scraper runtime prepared at: {scraper_runtime}")
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

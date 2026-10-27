#!/usr/bin/env python3
"""Build the Windows lite package without an offline Node/Chromium runtime."""

from __future__ import annotations

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_SCRIPT = Path(__file__).with_name("build_offline_package.py")
PYINSTALLER_SPEC = (
    PROJECT_ROOT / "installer" / "pyinstaller" / "BDE XBRL Editor Lite.spec"
)

_SPEC = importlib.util.spec_from_file_location("build_offline_package", BASE_SCRIPT)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"Could not load build helpers: {BASE_SCRIPT}")
_base = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_base)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a Windows package without bundled Node.js or Chromium.",
    )
    parser.add_argument(
        "--dist-dir",
        type=Path,
        default=PROJECT_ROOT / "dist" / "lite" / "windows-amd64",
        help="Output directory for the PyInstaller bundle.",
    )
    parser.add_argument(
        "--no-zip",
        action="store_true",
        help="Do not create the final zip archive.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    dist_dir = args.dist_dir.resolve()

    try:
        _base._remove(dist_dir)
        dist_dir.mkdir(parents=True)
        _base._run(
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
                str(PROJECT_ROOT / "build" / "pyinstaller-lite-windows"),
            ],
            cwd=PROJECT_ROOT,
        )
        if not args.no_zip:
            archive = dist_dir.parent / "bde-xbrl-editor-windows-amd64-lite.zip"
            _base._zip_dir(dist_dir, archive)
            print(f"Lite package archive: {archive}")
        print(f"Lite package directory: {dist_dir}")
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

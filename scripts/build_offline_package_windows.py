#!/usr/bin/env python3
"""Windows wrapper for the portable offline package builder."""

from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path

_BASE_SCRIPT = Path(__file__).with_name("build_offline_package.py")
_SPEC = importlib.util.spec_from_file_location("build_offline_package", _BASE_SCRIPT)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - import machinery failure
    raise RuntimeError(f"Could not load build script: {_BASE_SCRIPT}")

_base = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_base)
_base_run = _base._run


def _node_package_command(command: str) -> str:
    """Resolve npm or npx to the Windows ``.cmd`` launcher."""
    launcher = f"{command}.cmd"
    resolved = shutil.which(launcher)
    if resolved is None:
        raise RuntimeError(f"{launcher} was not found in PATH; reinstall Node.js with npm")
    return resolved


def _run(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    windows_args = list(args)
    if windows_args and windows_args[0] in {"npm", "npx"}:
        windows_args[0] = _node_package_command(windows_args[0])
    _base_run(windows_args, cwd=cwd, env=env)


def main(argv: list[str] | None = None) -> int:
    _base._run = _run
    return _base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())

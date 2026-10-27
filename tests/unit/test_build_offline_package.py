"""Tests for the portable offline package builder."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path


def _load_build_module(script_name: str = "build_offline_package.py"):
    script = Path(__file__).resolve().parents[2] / "scripts" / script_name
    spec = importlib.util.spec_from_file_location("build_offline_package", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_copy_node_runtime_copies_only_the_node_executable(monkeypatch, tmp_path: Path) -> None:
    build = _load_build_module()
    node_install = tmp_path / "node-install"
    node_executable = node_install / "bin" / "node"
    node_executable.parent.mkdir(parents=True)
    node_executable.write_text("node executable", encoding="utf-8")
    node_executable.chmod(0o755)
    (node_install / "lib" / "node_modules").mkdir(parents=True)
    (node_install / "lib" / "node_modules" / "unrelated-package").write_text(
        "must not be packaged",
        encoding="utf-8",
    )
    target = tmp_path / "offline-node"

    monkeypatch.setattr(build.shutil, "which", lambda _name: str(node_executable))

    build._copy_node_runtime(target)

    copied_node = target / ("node.exe" if os.name == "nt" else "bin/node")
    assert copied_node.read_text(encoding="utf-8") == "node executable"
    assert copied_node.stat().st_mode & 0o111
    assert not (target / "lib").exists()


def test_node_package_command_uses_cmd_launcher_on_windows(monkeypatch) -> None:
    build = _load_build_module("build_offline_package_windows.py")
    monkeypatch.setattr(
        build.shutil,
        "which",
        lambda command: f"C:/Program Files/nodejs/{command}" if command.endswith(".cmd") else None,
    )

    assert build._node_package_command("npm") == "C:/Program Files/nodejs/npm.cmd"
    assert build._node_package_command("npx") == "C:/Program Files/nodejs/npx.cmd"


def test_lite_package_defaults_to_separate_distribution() -> None:
    build = _load_build_module("build_lite_package_windows.py")

    args = build.parse_args([])

    assert args.dist_dir == build.PROJECT_ROOT / "dist" / "lite" / "windows-amd64"
    assert args.no_zip is False

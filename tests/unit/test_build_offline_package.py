"""Tests for the portable offline package builder."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_build_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "build_offline_package.py"
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

    copied_node = target / "bin" / "node"
    assert copied_node.read_text(encoding="utf-8") == "node executable"
    assert copied_node.stat().st_mode & 0o111
    assert not (target / "lib").exists()

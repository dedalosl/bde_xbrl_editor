"""Tests for the bundled taxonomy catalog scraper wrapper."""

from __future__ import annotations

from pathlib import Path

from bde_xbrl_editor.taxonomy_catalog import scraper


def _write_scraper_project(root: Path) -> None:
    (root / "src").mkdir(parents=True)
    (root / "data").mkdir()
    (root / "package.json").write_text('{"scripts": {"scrape": "ts-node src/index.ts"}}')
    (root / "package-lock.json").write_text('{"lockfileVersion": 3}')
    (root / "tsconfig.json").write_text("{}")
    (root / "playwright.config.ts").write_text("export default {};")
    (root / "src" / "index.ts").write_text("console.log('scrape');")
    (root / "data" / "taxonomies.json").write_text("{}")


def test_bundled_scraper_root_exists() -> None:
    root = scraper.bundled_scraper_root()
    assert (root / "package.json").is_file()
    assert (root / "src" / "index.ts").is_file()


def test_scraper_catalog_path_accepts_legacy_checker_root(tmp_path: Path) -> None:
    legacy_root = tmp_path / "bde_taxonomies_checker"
    scraper_root = legacy_root / "scraper"
    scraper_root.mkdir(parents=True)
    (legacy_root / "package.json").write_text("{}", encoding="utf-8")
    (scraper_root / "package.json").write_text("{}", encoding="utf-8")

    assert scraper.scraper_catalog_path(legacy_root) == scraper_root / "data" / "taxonomies.json"


def test_run_catalog_scrape_prepares_runtime_copy_and_installs_dependencies(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bundled_root = tmp_path / "bundled"
    runtime_root = tmp_path / "runtime"
    _write_scraper_project(bundled_root)
    output_path = tmp_path / "generated" / "taxonomies.json"
    calls: list[tuple[list[str], Path]] = []
    install_env: dict[str, str] = {}

    class FakeProcess:
        returncode = 0

        def __init__(self, args, *, cwd, env, **_kwargs) -> None:
            self.args = args
            self.cwd = Path(cwd)
            self.env = env
            calls.append((args, self.cwd))

        def communicate(self, timeout: float) -> tuple[str, str]:
            if self.args == ["npm", "ci"]:
                install_env.update(self.env)
                (self.cwd / "node_modules" / ".bin").mkdir(parents=True)
                (self.cwd / "node_modules" / ".bin" / "ts-node").write_text("")
                (self.cwd / "node_modules" / "playwright").mkdir()
            if self.args == ["npm", "run", "scrape"]:
                Path(self.env["BDE_TAXONOMIES_OUTPUT_PATH"]).write_text(
                    "{}",
                    encoding="utf-8",
                )
            return "", ""

    monkeypatch.setattr(scraper, "bundled_scraper_root", lambda: bundled_root)
    monkeypatch.setattr(scraper, "default_runtime_scraper_root", lambda: runtime_root)
    monkeypatch.setattr(scraper.subprocess, "Popen", FakeProcess)

    result = scraper.run_catalog_scrape(output_path=output_path)

    assert result == output_path
    assert calls == [
        (["npm", "ci"], runtime_root),
        (["npm", "run", "scrape"], runtime_root),
    ]
    assert install_env["NODE_ENV"] == "development"
    assert install_env["npm_config_production"] == "false"
    assert (runtime_root / "src" / "index.ts").is_file()
    assert (runtime_root / "package-lock.json").is_file()

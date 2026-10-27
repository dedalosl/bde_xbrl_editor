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
    chromium_calls: list[tuple[Path, dict[str, str]]] = []

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
                (self.cwd / "node_modules" / "ts-node" / "dist").mkdir(parents=True)
                (self.cwd / "node_modules" / "ts-node" / "dist" / "bin.js").write_text("")
                (self.cwd / "node_modules" / "playwright").mkdir()
            if self.args[0] == "node":
                Path(self.env["BDE_TAXONOMIES_OUTPUT_PATH"]).write_text(
                    "{}",
                    encoding="utf-8",
                )
            return "", ""

    monkeypatch.setattr(scraper, "bundled_scraper_root", lambda: bundled_root)
    monkeypatch.setattr(scraper, "default_runtime_scraper_root", lambda: runtime_root)
    monkeypatch.setattr(
        scraper,
        "default_runtime_playwright_browsers_path",
        lambda: tmp_path / "runtime" / "playwright-browsers",
    )
    monkeypatch.setattr(scraper.sys, "platform", "win32")
    monkeypatch.setattr(scraper, "_npm_executable", lambda: "npm")
    monkeypatch.setattr(scraper.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(
        scraper,
        "_ensure_playwright_chromium",
        lambda root, **kwargs: chromium_calls.append((root, kwargs["env"])),
    )

    result = scraper.run_catalog_scrape(output_path=output_path)

    assert result == output_path
    assert calls == [
        (["npm", "ci"], runtime_root),
        (
            [
                "node",
                str(runtime_root / "node_modules" / "ts-node" / "dist" / "bin.js"),
                "src/index.ts",
            ],
            runtime_root,
        ),
    ]
    assert install_env["NODE_ENV"] == "development"
    assert install_env["npm_config_production"] == "false"
    assert install_env["PLAYWRIGHT_BROWSERS_PATH"] == str(
        tmp_path / "runtime" / "playwright-browsers"
    )
    assert len(chromium_calls) == 1
    assert chromium_calls[0][0] == runtime_root
    assert (
        chromium_calls[0][1]["PLAYWRIGHT_BROWSERS_PATH"] == install_env["PLAYWRIGHT_BROWSERS_PATH"]
    )
    assert (runtime_root / "src" / "index.ts").is_file()
    assert (runtime_root / "package-lock.json").is_file()


def test_setup_catalog_scraper_prepares_runtime_without_running_scrape(
    monkeypatch,
    tmp_path: Path,
) -> None:
    bundled_root = tmp_path / "bundled"
    runtime_root = tmp_path / "runtime"
    _write_scraper_project(bundled_root)
    calls: list[tuple[list[str], Path]] = []
    chromium_calls: list[tuple[Path, dict[str, str]]] = []

    class FakeProcess:
        returncode = 0

        def __init__(self, args, *, cwd, **_kwargs) -> None:
            self.args = args
            self.cwd = Path(cwd)
            calls.append((args, self.cwd))

        def communicate(self, timeout: float) -> tuple[str, str]:
            assert self.args != ["npm", "run", "scrape"]
            (self.cwd / "node_modules" / ".bin").mkdir(parents=True)
            (self.cwd / "node_modules" / ".bin" / "ts-node").write_text("")
            (self.cwd / "node_modules" / "ts-node" / "dist").mkdir(parents=True)
            (self.cwd / "node_modules" / "ts-node" / "dist" / "bin.js").write_text("")
            (self.cwd / "node_modules" / "playwright").mkdir()
            return "", ""

    monkeypatch.setattr(scraper, "bundled_scraper_root", lambda: bundled_root)
    monkeypatch.setattr(scraper, "default_runtime_scraper_root", lambda: runtime_root)
    monkeypatch.setattr(scraper, "_npm_executable", lambda: "npm")
    monkeypatch.setattr(scraper.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(
        scraper,
        "_ensure_playwright_chromium",
        lambda root, **kwargs: chromium_calls.append((root, kwargs["env"])),
    )

    result = scraper.setup_catalog_scraper()

    assert result == runtime_root
    assert calls == [(["npm", "ci"], runtime_root)]
    assert chromium_calls == [(runtime_root, scraper._scraper_process_env(runtime_root))]
    assert (runtime_root / "src" / "index.ts").is_file()


def test_npm_executable_uses_cmd_launcher_on_windows(monkeypatch) -> None:
    monkeypatch.setattr(scraper.os, "name", "nt")
    monkeypatch.setattr(
        scraper.shutil,
        "which",
        lambda command: "C:/Program Files/nodejs/npm.cmd" if command == "npm.cmd" else None,
    )

    assert scraper._npm_executable() == "C:/Program Files/nodejs/npm.cmd"


def test_missing_playwright_chromium_is_installed_in_persistent_runtime_path(
    monkeypatch,
    tmp_path: Path,
) -> None:
    scraper_root = tmp_path / "runtime" / "bde_taxonomies_scraper"
    cli = scraper_root / "node_modules" / "playwright" / "cli.js"
    cli.parent.mkdir(parents=True)
    cli.write_text("", encoding="utf-8")
    browser_root = tmp_path / "runtime" / "playwright-browsers"
    browser_executable = (
        browser_root
        / "chromium_headless_shell-1223"
        / "chrome-headless-shell-win64"
        / "chrome-headless-shell.exe"
    )
    calls: list[tuple[list[str], Path, dict[str, str]]] = []

    def fake_run_process(args, *, cwd, env, **_kwargs):
        calls.append((args, Path(cwd), env))
        if args[1] == "-e":
            return str(browser_executable), ""
        assert args[1:] == [str(cli), "install", "chromium"]
        browser_executable.parent.mkdir(parents=True)
        browser_executable.write_text("installed", encoding="utf-8")
        return "", ""

    monkeypatch.setattr(scraper, "default_runtime_playwright_browsers_path", lambda: browser_root)
    monkeypatch.setattr(scraper.sys, "platform", "win32")
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    monkeypatch.setattr(scraper, "_node_executable", lambda _root: "node")
    monkeypatch.setattr(scraper, "_run_process", fake_run_process)

    env = scraper._scraper_process_env(scraper_root)
    scraper._ensure_playwright_chromium(
        scraper_root,
        env=env,
        timeout_seconds=60,
        should_cancel=None,
    )

    assert env["PLAYWRIGHT_BROWSERS_PATH"] == str(browser_root)
    assert [call[0][1] for call in calls] == ["-e", str(cli)]
    assert all(call[1] == scraper_root for call in calls)
    assert all(call[2]["PLAYWRIGHT_BROWSERS_PATH"] == str(browser_root) for call in calls)
    assert browser_executable.is_file()


def test_existing_playwright_chromium_is_not_downloaded(
    monkeypatch,
    tmp_path: Path,
) -> None:
    scraper_root = tmp_path / "runtime" / "scraper"
    browser_executable = tmp_path / "browsers" / "chromium.exe"
    browser_executable.parent.mkdir(parents=True)
    browser_executable.write_text("installed", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run_process(args, **_kwargs):
        calls.append(args)
        return str(browser_executable), ""

    monkeypatch.setattr(scraper, "_node_executable", lambda _root: "node")
    monkeypatch.setattr(scraper, "_run_process", fake_run_process)

    scraper._ensure_playwright_chromium(
        scraper_root,
        env={"PLAYWRIGHT_BROWSERS_PATH": str(browser_executable.parent)},
        timeout_seconds=60,
        should_cancel=None,
    )

    assert len(calls) == 1
    assert calls[0][1] == "-e"


def test_run_catalog_scrape_uses_prepared_offline_runtime_without_npm(
    monkeypatch,
    tmp_path: Path,
) -> None:
    scraper_root = tmp_path / "offline-scraper"
    _write_scraper_project(scraper_root)
    output_path = tmp_path / "taxonomies.json"
    node_path = scraper_root / "node" / "bin" / "node"
    ts_node = scraper_root / "node_modules" / "ts-node" / "dist" / "bin.js"
    (scraper_root / "node_modules" / ".bin").mkdir(parents=True)
    (scraper_root / "node_modules" / ".bin" / "ts-node").write_text("")
    ts_node.parent.mkdir(parents=True)
    ts_node.write_text("")
    (scraper_root / "node_modules" / "playwright").mkdir()
    node_path.parent.mkdir(parents=True)
    node_path.write_text("")
    (scraper_root / "playwright-browsers").mkdir()
    calls: list[tuple[list[str], Path]] = []
    scrape_env: dict[str, str] = {}
    chromium_calls: list[tuple[Path, dict[str, str]]] = []

    class FakeProcess:
        returncode = 0

        def __init__(self, args, *, cwd, env, **_kwargs) -> None:
            self.args = args
            self.cwd = Path(cwd)
            self.env = env
            calls.append((args, self.cwd))

        def communicate(self, timeout: float) -> tuple[str, str]:
            assert self.args[0] == str(node_path)
            scrape_env.update(self.env)
            Path(self.env["BDE_TAXONOMIES_OUTPUT_PATH"]).write_text(
                "{}",
                encoding="utf-8",
            )
            return "", ""

    monkeypatch.setattr(scraper.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(
        scraper,
        "_ensure_playwright_chromium",
        lambda root, **kwargs: chromium_calls.append((root, kwargs["env"])),
    )

    result = scraper.run_catalog_scrape(root=scraper_root, output_path=output_path)

    assert result == output_path
    assert calls == [([str(node_path), str(ts_node), "src/index.ts"], scraper_root)]
    assert len(chromium_calls) == 1
    assert chromium_calls[0][0] == scraper_root
    assert scrape_env["PLAYWRIGHT_BROWSERS_PATH"] == str(scraper_root / "playwright-browsers")


def test_default_scraper_root_prefers_adjacent_offline_runtime(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app_root = tmp_path / "dist" / "offline" / "test-platform"
    executable = app_root / "BDE XBRL Editor" / "BDE XBRL Editor"
    scraper_root = app_root / "offline-runtime" / "bde_taxonomies_scraper"
    _write_scraper_project(scraper_root)
    (scraper_root / "node_modules" / ".bin").mkdir(parents=True)
    (scraper_root / "node_modules" / ".bin" / "ts-node").write_text("")
    (scraper_root / "node_modules" / "ts-node" / "dist").mkdir(parents=True)
    (scraper_root / "node_modules" / "ts-node" / "dist" / "bin.js").write_text("")
    (scraper_root / "node_modules" / "playwright").mkdir()
    executable.parent.mkdir(parents=True)
    executable.write_text("")

    monkeypatch.delenv("BDE_TAXONOMIES_SCRAPER_ROOT", raising=False)
    monkeypatch.delenv("BDE_TAXONOMIES_CHECKER_ROOT", raising=False)
    monkeypatch.delenv("BDE_XBRL_OFFLINE_RUNTIME_DIR", raising=False)
    monkeypatch.setattr(scraper.sys, "executable", str(executable))

    assert scraper.default_scraper_root() == scraper_root

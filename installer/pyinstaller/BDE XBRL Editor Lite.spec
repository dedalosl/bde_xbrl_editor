# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

project_root = Path(SPECPATH).resolve().parents[1]
scraper_source = (
    project_root
    / "src"
    / "bde_xbrl_editor"
    / "taxonomy_catalog"
    / "bde_taxonomies_scraper"
)

datas = [
    (
        str(scraper_source),
        "bde_xbrl_editor/taxonomy_catalog/bde_taxonomies_scraper",
    )
]
binaries = []
hiddenimports = []

# These libraries contain schemas, package data, and extension modules that
# are not all discoverable from static imports. PySide6 is intentionally not
# collected wholesale; its standard hooks include only the Qt modules used by
# the application.
for package in ("lxml", "xmlschema", "elementpath"):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

a = Analysis(
    [str(project_root / "src" / "bde_xbrl_editor" / "__main__.py")],
    pathex=[str(project_root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# Qt on Windows links against the ICU API supplied by Windows. A build
# environment may also expose an unrelated unversioned icuuc.dll (for example
# via Poppler on PATH), which PyInstaller can mistakenly collect. Bundling that
# DLL shadows the compatible system library and makes Qt6Core fail with Windows
# error 127 ("procedure not found"). Its large data companion is then unused.
if os.name == "nt":
    incompatible_icu_names = {"icuuc.dll", "icudt78.dll"}
    a.binaries = [
        entry for entry in a.binaries if Path(entry[0]).name.lower() not in incompatible_icu_names
    ]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BDE XBRL Editor",
    debug=os.environ.get("BDE_XBRL_DEBUG_CONSOLE") == "1",
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=os.environ.get("BDE_XBRL_DEBUG_CONSOLE") == "1",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="BDE XBRL Editor",
)

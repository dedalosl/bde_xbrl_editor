# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

project_root = Path(SPECPATH).resolve().parents[1]
scraper_source = os.environ.get("BDE_XBRL_OFFLINE_SCRAPER_DIR")
if scraper_source:
    scraper_source = str(Path(scraper_source).resolve())
else:
    scraper_source = str(
        project_root
        / "src"
        / "bde_xbrl_editor"
        / "taxonomy_catalog"
        / "bde_taxonomies_scraper"
    )

datas = []
binaries = []
hiddenimports = []
tmp_ret = collect_all("PySide6")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
tmp_ret = collect_all("lxml")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
tmp_ret = collect_all("xmlschema")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]
tmp_ret = collect_all("elementpath")
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

datas += [
    (
        scraper_source,
        "bde_xbrl_editor/taxonomy_catalog/bde_taxonomies_scraper",
    )
]

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
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BDE XBRL Editor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
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
app = BUNDLE(
    coll,
    name="BDE XBRL Editor.app",
    icon=None,
    bundle_identifier=None,
)

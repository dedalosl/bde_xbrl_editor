"""Shared test fixtures for bde_xbrl_editor tests."""

from __future__ import annotations

import os
from pathlib import Path

# Qt must be configured before any PySide6 import. Without this, headless
# collection can abort before pytest has a chance to run fixtures.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

BDE_SAMPLE_DIR = Path(__file__).parent.parent / "test_data" / "taxonomies" / "bde_sample"
BDE_ENTRY_POINT = BDE_SAMPLE_DIR / "entry_point.xsd"


@pytest.fixture(scope="session")
def bde_sample_taxonomy_path() -> Path:
    """Return path to the BDE sample taxonomy entry-point XSD."""
    return BDE_ENTRY_POINT


@pytest.fixture(scope="session")
def loaded_taxonomy(bde_sample_taxonomy_path):
    """Load and cache the BDE sample taxonomy once per test session."""
    if not bde_sample_taxonomy_path.exists():
        pytest.skip("BDE sample taxonomy not present in test_data/")
    from bde_xbrl_editor.taxonomy import LoaderSettings, TaxonomyCache, TaxonomyLoader

    cache = TaxonomyCache()
    settings = LoaderSettings()
    loader = TaxonomyLoader(cache=cache, settings=settings)
    return loader.load(bde_sample_taxonomy_path)

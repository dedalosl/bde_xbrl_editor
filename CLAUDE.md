# bde_xbrl_editor Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-25

## Active Technologies

- Python 3.11+ + PySide6 (UI), lxml (XML parsing and tree manipulation), xmlschema (XSD schema validation and DTS graph), elementpath (XPath 2.0 for formula/table expressions), cachetools (LRU cache) (001-taxonomy-loading-cache)

## Project Structure

```text
src/
tests/
```

## Commands

```bash
# Install in editable mode
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check .
```

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes

- 001-taxonomy-loading-cache: Added Python 3.11+ + PySide6 (UI), lxml (XML parsing and tree manipulation), xmlschema (XSD schema validation and DTS graph), elementpath (XPath 2.0 for formula/table expressions), cachetools (LRU cache)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

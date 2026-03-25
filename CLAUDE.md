# bde_xbrl_editor Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-25

## Active Technologies

- **Language**: Python 3.11+
- **UI**: PySide6 (QWizard, QTableView, QAbstractTableModel)
- **XML parsing**: lxml + xmlschema
- **XPath 2.0**: elementpath
- **Caching**: cachetools (LRUCache)
- **Data model**: Python dataclasses (stdlib)
- **Serialisation**: lxml etree (XBRL 2.1 XML output)

## Project Structure

```text
src/
└── bde_xbrl_editor/
    ├── taxonomy/      # Feature 001: DTS discovery, schema parsing, linkbases, table PWD, cache
    ├── instance/      # Feature 002: XbrlInstance model, InstanceFactory, InstanceSerializer
    ├── validation/    # Feature 005 (planned)
    └── ui/            # PySide6 main window + widgets

tests/
├── unit/
├── integration/
└── conformance/       # Feature 006 (planned)

test_data/
└── taxonomies/        # Minimal BDE taxonomy samples
```

## Commands

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run only unit tests (no BDE taxonomy needed)
pytest tests/unit/

# Lint
ruff check .

# Type check
mypy src/
```

## Code Style

- Follow PEP 8 and use `ruff` for linting
- All public module APIs documented in `specs/<feature>/contracts/`
- Business logic classes must have zero PySide6 imports (testable without Qt)
- Use `QName` from `bde_xbrl_editor.taxonomy.models` as the canonical concept identifier type
- No network calls during taxonomy loading by default (`LoaderSettings.allow_network=False`)

## Feature Dependencies

```
001-taxonomy-loading-cache   ← foundational; all other features depend on this
002-xbrl-instance-creation   ← depends on 001 (TaxonomyStructure)
003-table-rendering-pwd      ← depends on 001 (TableDefinitionPWD, LabelResolver)
004-instance-editing         ← depends on 001 + 002/003 (XbrlInstance + table renderer)
005-instance-validation      ← depends on 001 + 002/004 (formula linkbase, XbrlInstance)
006-conformance-suite-runner ← depends on 001 (same processing engine, CLI-only)
```

## Recent Changes

- 001-taxonomy-loading-cache: Established Python + PySide6 + lxml + xmlschema + elementpath + cachetools stack; `TaxonomyStructure` API
- 002-xbrl-instance-creation: Added `instance/` sub-package; `InstanceFactory` + `InstanceSerializer`; `QWizard` UI; filing indicators (Eurofiling namespace); deterministic context ID generation

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

# bde_xbrl_editor Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-25

## Active Technologies

- **Language**: Python 3.11+
- **UI**: PySide6 — `QMainWindow`, `QWizard`, `QTableView`, `QHeaderView`, `QAbstractTableModel`, `QFrame`, `QTabBar`, `QComboBox`, `QPainter`, `QColor`
- **XML parsing**: lxml + xmlschema
- **XPath 2.0**: elementpath
- **Caching**: cachetools (`LRUCache`)
- **Data model**: Python dataclasses (stdlib)
- **Serialisation**: lxml etree (XBRL 2.1 XML output)

## Project Structure

```text
src/
└── bde_xbrl_editor/
    ├── taxonomy/          # Feature 001: DTS, schema, linkbases, table PWD, cache
    ├── instance/          # Feature 002: XbrlInstance, InstanceFactory, InstanceSerializer
    ├── table_renderer/    # Feature 003: TableLayoutEngine, FactFormatter, models
    ├── validation/        # Feature 005 (planned)
    └── ui/
        └── widgets/       # PySide6 widgets (wizard, table view, headers, Z-selector)

tests/
├── unit/
├── integration/
└── conformance/           # Feature 006 (planned)

test_data/
└── taxonomies/            # Minimal BDE taxonomy samples
```

## Commands

```bash
# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run only unit tests (no BDE taxonomy / display server needed)
pytest tests/unit/

# Lint
ruff check .

# Type check
mypy src/
```

## Code Style

- Follow PEP 8; use `ruff` for linting
- All public module APIs documented in `specs/<feature>/contracts/`
- **Business logic classes must have zero PySide6 imports** — testable without Qt
- Use `QName` from `bde_xbrl_editor.taxonomy.models` as the canonical concept identifier
- No network calls during taxonomy loading by default (`LoaderSettings.allow_network=False`)
- `LabelResolver.resolve()` never raises — always returns a non-empty string
- `FactFormatter.format()` never raises — falls back to raw value on error

## Feature Dependencies

```
001-taxonomy-loading-cache   ← foundational; all other features depend on this
002-xbrl-instance-creation   ← depends on 001 (TaxonomyStructure)
003-table-rendering-pwd      ← depends on 001 (TableDefinitionPWD) + optionally 002 (XbrlInstance)
004-instance-editing         ← depends on 001 + 002 + 003
005-instance-validation      ← depends on 001 + 002/004
006-conformance-suite-runner ← depends on 001 (same engine, CLI-only)
```

## Recent Changes

- 001: Established stack; `TaxonomyStructure` + `TaxonomyCache` API; `LabelResolver`; `TableDefinitionPWD` PWD parser
- 002: `instance/` sub-package; `InstanceFactory` + `InstanceSerializer`; `QWizard` 4-step UI; filing indicators (Eurofiling ns); deterministic context IDs
- 003: `table_renderer/` sub-package; `TableLayoutEngine` (pure Python PWD layout); custom `QHeaderView` spanning paint; two-`QTableView` frozen-pane; adaptive `ZAxisSelector`; `FactFormatter`

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

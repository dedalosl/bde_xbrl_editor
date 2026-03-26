# bde_xbrl_editor Development Guidelines

## Project Overview

BDE XBRL Editor — a Python + PySide6 desktop application for creating, editing, and validating XBRL financial reporting documents for Banco de España (BDE) taxonomies.

## Tech Stack

- **Language**: Python 3.11+
- **UI**: PySide6 (LGPL) — NOT PyQt6
- **XML/XSD**: lxml + xmlschema
- **XPath 2.0**: elementpath (with custom xfi: function registration for formula evaluation)
- **Build**: pyproject.toml (setuptools src-layout)
- **Tests**: pytest + pytest-qt
- **Linting**: ruff

## Project Structure

```text
src/
└── bde_xbrl_editor/
    ├── taxonomy/          # Feature 001: taxonomy loading, caching, all linkbases
    │   ├── discovery.py
    │   ├── schema.py
    │   ├── models.py      # TaxonomyStructure, Concept, QName, HypercubeModel, etc.
    │   ├── cache.py
    │   ├── loader.py
    │   ├── constants.py
    │   └── linkbases/
    │       ├── label.py, generic_label.py, presentation.py
    │       ├── calculation.py, definition.py, table_pwd.py
    │       └── formula.py  # Feature 005 addition
    ├── instance/          # Features 002 + 004
    │   ├── models.py      # XbrlInstance, Fact, XbrlContext, XbrlUnit, FilingIndicator
    │   ├── factory.py, serializer.py, context_builder.py, constants.py
    │   ├── parser.py      # Feature 004: InstanceParser
    │   ├── editor.py      # Feature 004: InstanceEditor
    │   └── validator.py   # Feature 004: XbrlTypeValidator
    ├── table_renderer/    # Feature 003
    │   ├── engine.py      # TableLayoutEngine
    │   ├── models.py      # HeaderCell, BodyCell, ComputedTableLayout, etc.
    │   └── widgets/       # XbrlTableView, MultiLevelColumnHeader, ZAxisSelector
    ├── validation/        # Feature 005
    │   ├── models.py      # ValidationFinding, ValidationReport, ValidationSeverity
    │   ├── structural.py, dimensional.py, orchestrator.py, exporter.py
    │   └── formula/
    │       ├── evaluator.py, filters.py, xfi_functions.py
    └── ui/
        ├── main_window.py
        └── widgets/
            ├── cell_edit_delegate.py
            ├── instance_info_panel.py
            ├── validation_panel.py
            ├── validation_results_model.py
            └── instance_creation_wizard/
tests/
└── unit/ + integration/
```

## Commands

```bash
# Install (editable)
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=bde_xbrl_editor

# Lint
ruff check .

# Format
ruff format .
```

## Key Conventions

- **Fact values**: Always stored as raw `str`. Never `float`. Use `decimal.Decimal` only transiently at edit-time normalisation.
- **QName**: Clark notation `{namespace}local_name` throughout.
- **Immutability**: All domain models (`TaxonomyStructure`, `ValidationReport`, `ValidationFinding`, `HeaderCell`) are immutable after construction (`frozen=True` dataclasses).
- **No PySide6 in core layers**: `taxonomy/`, `instance/`, `validation/` have zero PySide6 imports — fully testable without Qt.
- **Never raise from validators**: All validator methods return results or empty lists; exceptions are caught and converted to error findings/messages.
- **Eurofiling filing indicators**: namespace `http://www.eurofiling.info/xbrl/ext/filing-indicators`
- **Table Linkbase**: BDE uses PWD version (not final 1.0)

## Feature Dependency Graph

```
001 (taxonomy) ← 002 (instance creation) ← 004 (instance editing)
001 (taxonomy) ← 003 (table rendering)   ← 004 (instance editing)
001 + 002/004  ← 005 (validation)
001            ← 006 (conformance suite runner)
```

## Architecture Layers (strict — dependencies flow downward only)

1. **XBRL Processor Core**: taxonomy/, instance/ — no BDE specifics
2. **BDE Abstraction Layer**: BDE taxonomy customisation (Eurofiling, PWD table linkbase, formula evaluation)
3. **Application Services**: validation orchestration, instance editing services
4. **UI / API Layer**: PySide6 widgets, main window

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

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
The actual conformance data lives at conformance/ (not the default tests/conformance/suite-data/), so you need to pass --suite-data-dir. The registry maps suite IDs to subdirectory names, so you need a directory that contains xbrl-2.1/, dimensions-1.0/, etc.                                             

The integration test conftest creates those symlinks dynamically. For manual use, the easiest approach is to point directly at the existing data. However, the registry subdirectory names (xbrl-2.1, dimensions-1.0, etc.) don't match the actual directory names (XBRL-CONF-2025-07-16, etc.).

The simplest way to run it:                
  # Run a single suite (e.g. XBRL 2.1) using the pytest integration tests                              
  python -m pytest tests/integration/conformance/test_xbrl21_suite.py -v -k "not slow"                 

  # Or run all suites at once via pytest (parser-level, fast)                                          
  python -m pytest tests/integration/conformance/ -v -k "not slow"                                     
                
  For the full CLI runner against the actual data, you first need to set up the suite-data directory   
  with properly named subdirectories. Create symlinks once:
    
    mkdir -p tests/conformance/suite-data                      
    ln -sfn "$(pwd)/conformance/XBRL-CONF-2025-07-16"              tests/conformance/suite-data/xbrl-2.1
    ln -sfn "$(pwd)/conformance/XBRL-XDT-CONF-2025-09-09"
    tests/conformance/suite-data/dimensions-1.0
    ln -sfn "$(pwd)/conformance/table-linkbase-conformance-2024-12-17"
    tests/conformance/suite-data/table-linkbase-1.0
    ln -sfn "$(pwd)/conformance/formula-conformance-2022-07-21"
    tests/conformance/suite-data/formula-1.0   

  Then run:
  # All suites
  python -m bde_xbrl_editor.conformance

  # Single suite
  python -m bde_xbrl_editor.conformance --suite xbrl21
                                                                                                       
  # With verbose output and JSON report
  python -m bde_xbrl_editor.conformance --suite xbrl21 --verbose --output-format json --output-file    
  report.json                                                                                          
   
  The exit code will be 0 if all blocking suites (XBRL 2.1, Dimensions 1.0, Formula 1.0) pass, 1 if any
   mandatory case fails
<!-- MANUAL ADDITIONS END -->

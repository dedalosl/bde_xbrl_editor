# bde_xbrl_editor Development Guidelines

## Project Overview

BDE XBRL Editor — a Python + PySide6 desktop application for creating, editing, and validating XBRL financial reporting documents for Banco de España (BDE) taxonomies. Includes a headless CLI conformance suite runner for CI integration.

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
    │   ├── discovery.py, schema.py, models.py, cache.py, loader.py, constants.py
    │   └── linkbases/
    │       ├── label.py, generic_label.py, presentation.py
    │       ├── calculation.py, definition.py, table_pwd.py
    │       └── formula.py  # Feature 005 addition
    ├── instance/          # Features 002 + 004
    │   ├── models.py      # XbrlInstance, Fact, XbrlContext, XbrlUnit, FilingIndicator
    │   ├── factory.py, serializer.py, context_builder.py, constants.py
    │   └── parser.py, editor.py, validator.py  # Feature 004
    ├── table_renderer/    # Feature 003
    │   ├── engine.py, models.py
    │   └── widgets/
    ├── validation/        # Feature 005
    │   ├── models.py      # ValidationFinding, ValidationReport, ValidationSeverity
    │   ├── structural.py, dimensional.py, orchestrator.py, exporter.py
    │   └── formula/
    │       ├── evaluator.py, filters.py, xfi_functions.py
    ├── conformance/       # Feature 006: CLI conformance suite runner
    │   ├── __init__.py, __main__.py  # python -m bde_xbrl_editor.conformance
    │   ├── registry.py    # SUITE_REGISTRY: 4 suites (TL 1.0 non-blocking)
    │   ├── models.py      # TestCase, TestVariation, TestCaseResult, SuiteResult, SuiteRunReport
    │   ├── parser.py      # ConformanceSuiteParser (lxml)
    │   ├── executor.py    # TestCaseExecutor (drives Features 001+004+005)
    │   ├── runner.py      # ConformanceRunner (orchestrator)
    │   └── reporters/     # ConsoleReporter, JsonReporter
    └── ui/
        ├── main_window.py
        └── widgets/
            ├── cell_edit_delegate.py, instance_info_panel.py
            ├── validation_panel.py, validation_results_model.py
            └── instance_creation_wizard/
tests/
├── conformance/
│   ├── suite-data/        # XBRL.org suite test data (see quickstart.md for setup)
│   └── formula_skip_list.py
└── unit/ + integration/
```

## Commands

```bash
# Install (editable)
pip install -e ".[dev]"

# Run all tests
pytest

# Run with coverage
pytest --cov=bde_xbrl_editor

# Lint / format
ruff check .
ruff format .

# Run conformance suites (all)
python -m bde_xbrl_editor.conformance

# Run single suite
python -m bde_xbrl_editor.conformance --suite dimensions

# CI: conformance with JSON output
python -m bde_xbrl_editor.conformance --output-format json --output-file report.json
```

## Key Conventions

- **Fact values**: Always stored as raw `str`. Never `float`. Use `decimal.Decimal` only transiently at edit-time normalisation.
- **QName**: Clark notation `{namespace}local_name` throughout.
- **Immutability**: All domain models (`TaxonomyStructure`, `ValidationReport`, `ValidationFinding`, `SuiteRunReport`, `HeaderCell`) are immutable after construction (`frozen=True` dataclasses).
- **No PySide6 in core layers**: `taxonomy/`, `instance/`, `validation/`, `conformance/` have zero PySide6 imports — fully testable without Qt.
- **Never raise from validators/runner**: `InstanceValidator.validate_sync()` and `ConformanceRunner.run()` never raise; exceptions are caught and converted to findings/ERROR results.
- **Eurofiling filing indicators**: namespace `http://www.eurofiling.info/xbrl/ext/filing-indicators`
- **Table Linkbase**: BDE uses PWD version (not final 1.0)
- **ValidationFinding.rule_id**: Uses XBRL spec error codes (`xbrl.4.9.1`, `xdt.D01`, `formula.F01`) for spec-mandated rules; internal `structural:`/`dimensional:` prefix only for BDE-specific checks.
- **Conformance exit code**: 0 only if XBRL 2.1 + Dimensions 1.0 + Formula 1.0 blocking suites all pass. Table Linkbase 1.0 is informational/non-blocking in v1.

## Feature Dependency Graph

```
001 (taxonomy) ← 002 (instance creation) ← 004 (instance editing)
001 (taxonomy) ← 003 (table rendering)   ← 004 (instance editing)
001 + 002/004  ← 005 (validation)
001 + 004 + 005 ← 006 (conformance suite runner)
```

## Architecture Layers (strict — dependencies flow downward only)

1. **XBRL Processor Core**: taxonomy/, instance/ — no BDE specifics
2. **BDE Abstraction Layer**: BDE taxonomy customisation (Eurofiling, PWD table linkbase, formula evaluation)
3. **Application Services**: validation orchestration, instance editing, conformance running
4. **UI / API Layer**: PySide6 widgets, main window, CLI entry points

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

---
title: "BDE XBRL Editor Overview"
source: "src/CLAUDE.md, src/pyproject.toml"
author:
published: 2024-01-01
created: 2026-04-20
description: >
  Project overview for BDE XBRL Editor, a Python + PySide6 desktop application
  for creating, editing, and validating XBRL financial reporting documents for
  Banco de España taxonomies.
tags:
  - "project"
  - "overview"
---

# BDE XBRL Editor

## Project Overview

BDE XBRL Editor is a Python + PySide6 desktop application for creating, editing, and validating
XBRL financial reporting documents for Banco de España (BDE) taxonomies.

## Tech Stack

- **Language**: Python 3.11+
- **UI**: PySide6 (LGPL) — NOT PyQt6
- **XML/XSD**: lxml + xmlschema
- **XPath 2.0**: elementpath (with custom xfi: function registration for formula evaluation)
- **Build**: pyproject.toml (setuptools src-layout)
- **Tests**: pytest + pytest-qt
- **Linting**: ruff

## Architecture

The project follows a strict layer dependency model where dependencies flow downward only:

1. **XBRL Processor Core**: `taxonomy/`, `instance/` — no BDE specifics
2. **BDE Abstraction Layer**: BDE taxonomy customisation (Eurofiling, PWD table linkbase, formula evaluation)
3. **Application Services**: validation orchestration, instance editing services
4. **UI / API Layer**: PySide6 widgets, main window

## Feature Dependency Graph

```
001 (taxonomy) ← 002 (instance creation) ← 004 (instance editing)
001 (taxonomy) ← 003 (table rendering)   ← 004 (instance editing)
001 + 002/004  ← 005 (validation)
001            ← 006 (conformance suite runner)
```

## Project Structure

```
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
```

## Key Conventions

- **Fact values**: Always stored as raw `str`. Never `float`. Use `decimal.Decimal` only transiently at edit-time normalisation.
- **QName**: Clark notation `{namespace}local_name` throughout.
- **Immutability**: All domain models (`TaxonomyStructure`, `ValidationReport`, `ValidationFinding`, `HeaderCell`) are immutable after construction (`frozen=True` dataclasses).
- **No PySide6 in core layers**: `taxonomy/`, `instance/`, `validation/` have zero PySide6 imports — fully testable without Qt.
- **Never raise from validators**: All validator methods return results or empty lists; exceptions are caught and converted to error findings/messages.
- **Eurofiling filing indicators**: namespace `http://www.eurofiling.info/xbrl/ext/filing-indicators`
- **Table Linkbase**: BDE uses PWD version (not final 1.0)

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

## Conformance Suite

The project includes a conformance suite runner (`bde-xbrl-conformance`) that validates the
XBRL processor against official XBRL conformance test suites:

- XBRL 2.1
- Dimensions 1.0 (XDT)
- Table Linkbase 1.0
- Formula 1.0

See [[XBRL 2.1]] and [[XBRL Formula Overview 1.0]] for related specification details.

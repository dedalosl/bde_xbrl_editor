# Implementation Plan: Instance Validation

**Branch**: `005-instance-validation` | **Date**: 2026-03-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/005-instance-validation/spec.md`

## Summary

Implement a three-layer XBRL instance validation system: (1) structural conformance checks (XML well-formedness, context/unit reference integrity, duplicate facts, period-type consistency), (2) dimensional hypercube constraint validation (closed hypercube membership, prohibited combinations, invalid members), and (3) formula linkbase assertion evaluation (value, existence, and consistency assertions via XPath 2.0 using `elementpath` with custom `xfi:` function registration). Validation runs in a `QThread` worker; results are presented in a `ValidationPanel` with severity/table filtering, navigate-to-cell, and file export (plain text + JSON). Previous results stay visible during re-validation.

**Tech stack**: Python 3.11+ · PySide6 (`QTreeView`, `QSortFilterProxyModel`, `QThread`, `QProgressBar`) · lxml · elementpath (XPath 2.0 + custom `xfi:` functions) · dataclasses · threading.Event

---

## Technical Context

**Language/Version**: Python 3.11+
**New dependencies**: none — all required libraries already in the stack (`elementpath` for XPath 2.0, `lxml` for XML, `PySide6` for UI)
**Storage**: `ValidationReport` in memory; optional export to `.txt` or `.json` via `ValidationReportExporter`
**Testing**: pytest + pytest-qt; unit tests for each validator independently; integration tests using BDE sample taxonomy formula linkbase + known-failing instance
**Performance goals**: Validation of 10,000-fact instance with 200+ formula assertions completes in <60 seconds (SC-001); 100% assertions evaluated — none silently skipped (SC-002)
**Constraints**: Validators have zero PySide6 dependency (testable without Qt); `ValidationFinding` and `ValidationReport` are immutable dataclasses; validators never raise (exceptions converted to ERROR findings); abstract assertions are never evaluated (FR-013)
**Scale/Scope**: Instances up to 10,000 facts; up to 200+ formula assertions; single validation run at a time

---

## Constitution Check

**Gates applied**:
- ✅ `StructuralConformanceValidator`, `DimensionalConstraintValidator`, `FormulaEvaluator`, `InstanceValidator` — zero PySide6 imports; fully unit-testable without Qt
- ✅ `ValidationFinding` and `ValidationReport` — immutable (`frozen=True`); no mutable state
- ✅ `InstanceValidator.validate_sync()` never raises — all validator exceptions caught and converted to ERROR findings
- ✅ Formula evaluator filters out `@abstract="true"` assertions before evaluation loop (FR-013)
- ✅ `FormulaEvaluator` uses `elementpath` (already in stack) with registered `xfi:` callbacks — no new runtime dependency
- ✅ `ValidationWorker` does not block the UI thread — `QThread` + move-to-thread pattern
- ✅ Previous results remain visible during re-validation — results swapped only on `validation_completed` signal
- ✅ `DimensionalConstraintValidator` uses `HypercubeModel` from Feature 001 — no re-parsing of taxonomy
- ✅ BDE Abstraction Layer principle honoured: `FormulaEvaluator` interprets BDE taxonomy formula linkbases; `InstanceValidator` is the generic orchestrator above it

---

## Project Structure

### Documentation (this feature)

```text
specs/005-instance-validation/
├── spec.md
├── plan.md              ← this file
├── research.md          ← Phase 0: formula evaluation approach, structural checks,
│                                   dimensional validation, PySide6 results UI,
│                                   QThread worker pattern, report export format
├── data-model.md        ← Phase 1: ValidationFinding, ValidationReport, ValidationSeverity,
│                                   StructuralConformanceValidator, DimensionalConstraintValidator,
│                                   FormulaEvaluator, InstanceValidator, ValidationWorker,
│                                   ValidationPanel, ValidationResultsModel, ValidationFilterProxy,
│                                   ValidationReportExporter, FormulaAssertion hierarchy
├── contracts/
│   └── validation-api.md         ← Phase 1: full public API contract
└── tasks.md             ← Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code (additions to project)

```text
src/
└── bde_xbrl_editor/
    ├── taxonomy/          # Feature 001 — EXTENDED: add formula linkbase parser
    │   ├── linkbases/
    │   │   └── formula.py      # ← NEW: parse formula linkbase assertions, variables, filters
    │   └── models.py           # UPDATED: add FormulaAssertionSet, FormulaAssertion hierarchy,
    │                           #          FactVariableDefinition, DimensionFilter to TaxonomyStructure
    ├── instance/          # Features 002/004 — unchanged
    ├── table_renderer/    # Feature 003 — unchanged
    └── validation/        # ← NEW PACKAGE
        ├── __init__.py          # exports: InstanceValidator, ValidationReport, ValidationFinding,
        │                        #          ValidationSeverity, ValidationReportExporter
        ├── models.py            # ValidationFinding, ValidationReport, ValidationSeverity (frozen dataclasses)
        ├── structural.py        # StructuralConformanceValidator — 8 structural checks
        ├── dimensional.py       # DimensionalConstraintValidator — hypercube constraint checks
        ├── formula/
        │   ├── __init__.py      # exports FormulaEvaluator
        │   ├── evaluator.py     # FormulaEvaluator — assertion loop, variable binding, XPath eval
        │   ├── filters.py       # fact filter implementations (concept, context, period, dimension, unit)
        │   └── xfi_functions.py # xfi: namespace function registrations for elementpath
        ├── orchestrator.py      # InstanceValidator — calls structural → dimensional → formula
        └── exporter.py          # ValidationReportExporter — .txt and .json export

    └── ui/
        ├── main_window.py           # UPDATED: Validate action/button, _trigger_validation(),
        │                            #   _on_validation_done(), QThread lifecycle, ValidationPanel wiring
        └── widgets/
            ├── validation_panel.py      # ← NEW: ValidationPanel (QFrame composite widget)
            ├── validation_results_model.py  # ← NEW: ValidationResultsModel + ValidationFilterProxy
            └── ...

tests/
├── unit/
│   └── validation/
│       ├── test_structural.py       # StructuralConformanceValidator: all 7 rule types
│       ├── test_dimensional.py      # DimensionalConstraintValidator: all 4 constraint types
│       ├── test_formula_filters.py  # Fact filter predicates: concept, context, period, dimension, unit
│       ├── test_formula_evaluator.py # FormulaEvaluator: value/existence/consistency assertions;
│       │                             #   abstract assertion skip; no-formula-linkbase case
│       ├── test_xfi_functions.py    # xfi: registered functions: return types, edge cases
│       ├── test_models.py           # ValidationReport computed properties, ValidationFinding immutability
│       └── test_exporter.py         # ValidationReportExporter: text + JSON output; permission error
└── integration/
    └── validation/
        ├── test_full_validation_run.py   # Load BDE sample taxonomy + instance → validate → check report
        └── test_formula_assertions.py    # Known-failing instance → formula assertions fire correctly
```

---

## Complexity Tracking

| Area | Complexity | Reason |
|------|-----------|--------|
| `FormulaEvaluator` | HIGH | XBRL formula variable binding + filter system; XPath 2.0 evaluation; `xfi:` function library |
| `DimensionalConstraintValidator` | MEDIUM | Hypercube membership lookup; closed/notAll/default member rules |
| `StructuralConformanceValidator` | LOW | Straightforward lxml traversal and dict lookups |
| `ValidationPanel` | MEDIUM | Multi-filter proxy model; navigate-to-cell signal; progress/results swap |
| `ValidationReportExporter` | LOW | String formatting + `QFileDialog` |
| `ValidationWorker` | LOW | Standard QThread Worker pattern |
| Formula linkbase parser (in taxonomy) | MEDIUM | Parsing arc relationships, variable arcs, filter arcs from linkbase XML |

---

## Key Decisions (from research.md)

1. **elementpath + custom xfi:** — no Arelle/saxonche runtime dependency; `xfi:` functions as Python callbacks registered in elementpath
2. **lxml structural checks** — fast, synchronous, run before formula evaluation
3. **HypercubeModel reuse** — dimensional validator reads Feature 001 taxonomy model, no re-parsing
4. **Abstract assertion skip** — filter at the assertion loop level before any evaluation
5. **QThread Worker pattern** — non-blocking UI; previous results stay visible until `validation_completed`
6. **QSortFilterProxyModel (dual filter)** — severity AND table filter in a single proxy subclass
7. **Plain text + JSON export** — QFileDialog with both format options
8. **Severity from @severity attribute, default ERROR** — follows spec assumption §5

---

## Dependency Map

```
Feature 001 (taxonomy) ──extended──▶ formula linkbase parser → FormulaAssertionSet in TaxonomyStructure
Feature 002/004 (instance) ──read by──▶ StructuralConformanceValidator
                           ──read by──▶ DimensionalConstraintValidator
                           ──read by──▶ FormulaEvaluator
Feature 003 (table renderer) ──CellCoordinate──▶ navigate_to_cell signal
Feature 005 (this) ──produces──▶ ValidationReport ──displayed by──▶ ValidationPanel
```

---

## Out of Scope (confirmed from spec)

- BDE out-of-taxonomy validation rules (PDF documents) — v2+
- Automatic correction or suggestion of fixes
- BDE submission
- iXBRL validation
- Batch validation
- Differential (partial) re-validation

# Tasks: Instance Validation

**Input**: Design documents from `specs/005-instance-validation/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US4)
- Exact file paths in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create all new package and file stubs — no logic yet

- [ ] T001 Create `src/bde_xbrl_editor/validation/__init__.py` (empty re-export stub)
- [ ] T002 [P] Create `src/bde_xbrl_editor/validation/models.py` (empty file with module docstring)
- [ ] T003 [P] Create `src/bde_xbrl_editor/validation/structural.py` (empty file with module docstring)
- [ ] T004 [P] Create `src/bde_xbrl_editor/validation/dimensional.py` (empty file with module docstring)
- [ ] T005 [P] Create formula sub-package: `src/bde_xbrl_editor/validation/formula/__init__.py`, `formula/evaluator.py`, `formula/filters.py`, `formula/xfi_functions.py` (empty files with docstrings)
- [ ] T006 [P] Create `src/bde_xbrl_editor/validation/orchestrator.py` (empty file with module docstring)
- [ ] T007 [P] Create `src/bde_xbrl_editor/validation/exporter.py` (empty file with module docstring)
- [ ] T008 [P] Create `src/bde_xbrl_editor/ui/widgets/validation_panel.py` and `src/bde_xbrl_editor/ui/widgets/validation_results_model.py` (empty files with docstrings)
- [ ] T009 [P] Create taxonomy formula linkbase parser stub: `src/bde_xbrl_editor/taxonomy/linkbases/formula.py` (empty file with module docstring)
- [ ] T010 [P] Create test directories and files: `tests/unit/validation/` with `__init__.py`, `test_structural.py`, `test_dimensional.py`, `test_formula_evaluator.py`, `test_formula_filters.py`, `test_xfi_functions.py`, `test_models.py`, `test_exporter.py`; `tests/integration/validation/` with `__init__.py`, `test_full_validation_run.py`, `test_formula_assertions.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain types, error hierarchy, and taxonomy model extensions — required by every validator

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T011 Add formula linkbase domain types to `src/bde_xbrl_editor/taxonomy/models.py`: `FormulaAssertionSet` (assertions tuple, abstract_count); `FormulaAssertion` sealed base (assertion_id, label, severity, abstract, variables, precondition_xpath); `ValueAssertionDefinition` (test_xpath), `ExistenceAssertionDefinition` (test_xpath), `ConsistencyAssertionDefinition` (formula_xpath, absolute_radius, relative_radius); `FactVariableDefinition` (variable_name, concept_filter, period_filter, dimension_filters, unit_filter, fallback_value); `DimensionFilter` (dimension_qname, member_qnames, exclude)
- [ ] T012 [P] Implement `ValidationSeverity` (str Enum), `ValidationFinding` (frozen dataclass, all 11 fields), `ValidationReport` (frozen dataclass with computed properties error_count, warning_count, passed, findings_for_table, findings_by_severity), `ValidationRun` (mutable, internal only) in `src/bde_xbrl_editor/validation/models.py`
- [ ] T013 [P] Add error hierarchy to `src/bde_xbrl_editor/validation/`: `ValidationEngineError`, `FormulaParseError` (extends ValidationEngineError), `ExportPermissionError` (extends PermissionError)

**Checkpoint**: Domain types, error hierarchy, and taxonomy formula model extensions ready

---

## Phase 3: User Story 1 — Run Full Validation on an Open Instance (Priority: P1) 🎯 MVP

**Goal**: Validate an open instance (structural + dimensional + formula assertions); display result list with severity and rule ID; navigate from finding to table cell.

**Independent Test**: Run `InstanceValidator.validate_sync()` against a BDE sample instance with a known failing formula assertion; verify the returned `ValidationReport` contains a `ValidationFinding` with the expected `rule_id` and `severity == ERROR`; verify `report.passed == False`; verify `validate_sync()` never raises even when passed a structurally broken instance.

- [ ] T014 [US1] Implement formula linkbase parser in `src/bde_xbrl_editor/taxonomy/linkbases/formula.py` — parse `formula:valueAssertion`, `formula:existenceAssertion`, `formula:consistencyAssertion` elements; parse variable arcs and filter arcs; return `FormulaAssertionSet`; handle missing/invalid formula linkbase gracefully (return empty set)
- [ ] T015 [US1] Integrate formula linkbase parser into taxonomy loading in `src/bde_xbrl_editor/taxonomy/` — call `formula.py` parser during DTS discovery after label linkbase parsing; attach resulting `FormulaAssertionSet` to `TaxonomyStructure`; `formula_assertion_set` field defaults to empty set when no formula linkbase present
- [ ] T016 [US1] Implement `StructuralConformanceValidator` in `src/bde_xbrl_editor/validation/structural.py` — 8 rule checks in order: (1) missing-schemaref, (2) unresolved-context-ref, (3) unresolved-unit-ref, (4) incomplete-context, (5) period-type-mismatch, (6) duplicate-fact, (7) missing-namespace; all findings use `source="structural"`, `severity=ERROR`; never raises
- [ ] T017 [US1] Implement `DimensionalConstraintValidator` in `src/bde_xbrl_editor/validation/dimensional.py` — validate each fact's dimensions against `HypercubeModel` from `TaxonomyStructure`; 4 constraint types: UNDECLARED_DIMENSION, INVALID_MEMBER, CLOSED_MISSING_DIMENSION, PROHIBITED_COMBINATION; all findings use `source="dimensional"`, `severity=ERROR`; never raises
- [ ] T018 [US1] Implement `xfi:` function registrations in `src/bde_xbrl_editor/validation/formula/xfi_functions.py` — register core xfi: functions as Python callbacks for elementpath custom namespace; key functions: `xfi:facts`, `xfi:period`, `xfi:entity`, `xfi:unit`, `xfi:decimal`
- [ ] T019 [US1] Implement fact filter predicates in `src/bde_xbrl_editor/validation/formula/filters.py` — `apply_filters(facts, variable_def, instance) -> list[Fact]`; concept filter (exact QName match), period filter (instant/duration), dimension filter (member match/exclude), unit filter; return empty list when no match
- [ ] T020 [US1] Implement `FormulaEvaluator._bind_variables()` in `src/bde_xbrl_editor/validation/formula/evaluator.py` — for each `FactVariableDefinition` in assertion, call `apply_filters()`; produce cartesian product of binding tuples as `list[dict[str, list[Fact]]]`
- [ ] T021 [US1] Implement `FormulaEvaluator._evaluate_value_assertion()`, `_evaluate_existence_assertion()`, `_evaluate_consistency_assertion()` in `src/bde_xbrl_editor/validation/formula/evaluator.py` — evaluate @test XPath per binding (value); check at least one binding has non-empty fact set (existence); compare formula XPath result vs. fact value with radius tolerance (consistency); each returns `list[ValidationFinding]`
- [ ] T022 [US1] Implement `FormulaEvaluator.evaluate()` main loop in `src/bde_xbrl_editor/validation/formula/evaluator.py` — iterate `FormulaAssertionSet`; skip `abstract=True`; check `precondition_xpath`; call `_bind_variables()` then appropriate `_evaluate_*`; check `cancel_event` per assertion; call `progress_callback`; catch `ValidationEngineError` → ERROR finding; return `[]` if no formula linkbase
- [ ] T023 [US1] Implement `InstanceValidator.validate_sync()` in `src/bde_xbrl_editor/validation/orchestrator.py` — run `StructuralConformanceValidator` → `DimensionalConstraintValidator` → `FormulaEvaluator` in sequence; catch all exceptions from validators; wrap in `ValidationReport`; set `formula_linkbase_available` from taxonomy; never raises
- [ ] T024 [US1] Implement `ValidationWorker` (`QObject`) in `src/bde_xbrl_editor/ui/widgets/validation_panel.py` — `run()` slot calls `InstanceValidator.validate_sync()`; emits `progress_changed`, `validation_completed`, `validation_failed`; `cancel()` slot sets cancel event
- [ ] T025 [US1] Implement `ValidationResultsModel` (`QStandardItemModel`) in `src/bde_xbrl_editor/ui/widgets/validation_results_model.py` — 5 columns (Severity, Rule ID, Message, Table, Concept); `Qt.DecorationRole` for severity icon; `Qt.UserRole` on column 0 stores full `ValidationFinding` object
- [ ] T026 [US1] Implement `ValidationPanel` basic layout (no filters yet) in `src/bde_xbrl_editor/ui/widgets/validation_panel.py` — `QTreeView` backed by `ValidationResultsModel`; detail `QTextEdit` + "Go to cell" button; `show_report()`, `show_progress()`, `clear()`; emits `navigate_to_cell(str, object)` and `revalidate_requested`
- [ ] T027 [US1] Add Validate action and QThread lifecycle to `src/bde_xbrl_editor/ui/main_window.py` — toolbar/menu Validate button; `_trigger_validation()` guard against duplicate run; `ValidationWorker.moveToThread()`; `_on_validation_done()` and `_on_validation_error()` slots; mount `ValidationPanel` in sidebar; wire `navigate_to_cell` signal to `XbrlTableView`
- [ ] T028 [US1] Unit test: `StructuralConformanceValidator` — verify each of the 8 rule IDs is raised by a crafted failing instance; verify empty list for a clean instance in `tests/unit/validation/test_structural.py`
- [ ] T029 [P] [US1] Unit test: `DimensionalConstraintValidator` — verify all 4 constraint types against synthetic `HypercubeModel` + fact fixtures in `tests/unit/validation/test_dimensional.py`
- [ ] T030 [P] [US1] Unit test: `FormulaEvaluator` — value/existence/consistency assertion evaluation; abstract assertion skipped; empty result when no formula linkbase in `tests/unit/validation/test_formula_evaluator.py`
- [ ] T031 [P] [US1] Integration test: BDE sample taxonomy + known-good instance → `validate_sync()` returns `passed=True`; known-failing instance → expected findings in report in `tests/integration/validation/test_full_validation_run.py`

---

## Phase 4: User Story 2 — View Validation Results Filtered by Severity and Table (Priority: P2)

**Goal**: Severity and table filter controls on the ValidationPanel; dual-filter proxy model; summary count label.

**Independent Test**: Populate `ValidationResultsModel` with a mix of ERROR and WARNING findings across two tables; apply severity filter "ERROR" → verify only error rows pass `filterAcceptsRow()`; apply table filter → verify only findings for that table pass; call `clear_filters()` → verify all rows visible; verify summary label shows correct total counts.

- [ ] T032 [US2] Implement `ValidationFilterProxy` (`QSortFilterProxyModel`) in `src/bde_xbrl_editor/ui/widgets/validation_results_model.py` — `set_severity_filter(severity | None)`, `set_table_filter(table_id | None)`, `clear_filters()`; `filterAcceptsRow()` ANDs both filters; reads `Qt.UserRole` to access `ValidationFinding`
- [ ] T033 [US2] Add filter toolbar to `ValidationPanel` in `src/bde_xbrl_editor/ui/widgets/validation_panel.py` — severity `QComboBox` (All/Error/Warning), table `QComboBox`, Clear Filters `QPushButton`, summary `QLabel` (shows "N errors, M warnings"); stack `ValidationFilterProxy` over `ValidationResultsModel`; implement `set_available_tables(list[tuple[str, str]])`
- [ ] T034 [US2] Unit test: `ValidationFilterProxy` — severity filter, table filter, AND combination, `clear_filters()`, summary counts in `tests/unit/validation/test_models.py`

---

## Phase 5: User Story 3 — Re-Validate After Editing to Confirm Fixes (Priority: P3)

**Goal**: Re-validate button in ValidationPanel replaces results with new run without losing previous until complete; progress bar visible during run.

**Independent Test**: Call `_trigger_validation()` while a previous run is still displayed; verify previous results remain visible during the new run (progress bar shown); verify results are replaced only on `validation_completed` signal; verify the guard prevents a second `_trigger_validation()` call while a thread is running.

- [ ] T035 [US3] Add Re-validate `QPushButton` to `ValidationPanel` toolbar in `src/bde_xbrl_editor/ui/widgets/validation_panel.py` — button connects to `revalidate_requested` signal emission; add `QProgressBar` (hidden when idle) to toolbar; `show_progress()` shows progress bar and updates it without clearing result list
- [ ] T036 [US3] Wire `revalidate_requested` signal to `main_window._trigger_validation()` in `src/bde_xbrl_editor/ui/main_window.py` — same trigger path as Validate action; existing guard (skip if thread running) prevents double-trigger; results replaced only on `validation_completed`

---

## Phase 6: User Story 4 — Export the Validation Report (Priority: P4)

**Goal**: Export report to plain text or JSON file via QFileDialog; handle permission errors gracefully.

**Independent Test**: Create a `ValidationReport` with 2 findings; call `export_text(report, tmp_path)`; verify file contains each `rule_id`, `severity`, and `message`; call `export_json(report, tmp_path)`; parse the written JSON and verify it matches the documented schema; pass a non-writable path → verify `ExportPermissionError` is raised.

- [ ] T037 [US4] Implement `ValidationReportExporter.export_text()` in `src/bde_xbrl_editor/validation/exporter.py` — write summary header (instance, taxonomy, timestamp, passed/failed) then each finding formatted as `[SEVERITY] rule_id: message (table: ..., concept: ...)`; raise `ExportPermissionError` on unwritable path
- [ ] T038 [US4] Implement `ValidationReportExporter.export_json()` in `src/bde_xbrl_editor/validation/exporter.py` — write JSON following documented schema: `summary` object + `findings` array; each finding as JSON object with all fields; `null` for None fields; raise `ExportPermissionError` on unwritable path
- [ ] T039 [US4] Add Export `QPushButton` to `ValidationPanel` toolbar and implement `ValidationPanel.export_report()` in `src/bde_xbrl_editor/ui/widgets/validation_panel.py` — `QFileDialog.getSaveFileName` with `.txt` and `.json` filter; call `ValidationReportExporter.export_text()` or `.export_json()` based on selected format; handle `ExportPermissionError` with `QMessageBox`
- [ ] T040 [US4] Unit test: `ValidationReportExporter` — text output contains all findings; JSON output matches schema; empty findings = "passed" message; `ExportPermissionError` on non-writable path in `tests/unit/validation/test_exporter.py`

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Public API exports, remaining unit tests, integration test for formula assertions

- [ ] T041 Populate `src/bde_xbrl_editor/validation/__init__.py` re-exports: `InstanceValidator`, `ValidationReport`, `ValidationFinding`, `ValidationSeverity`, `ValidationReportExporter`, `ValidationEngineError`, `ExportPermissionError`
- [ ] T042 [P] Unit test: `ValidationReport` computed properties (error_count, warning_count, passed, findings_for_table, findings_by_severity); `ValidationFinding` immutability (frozen dataclass) in `tests/unit/validation/test_models.py`
- [ ] T043 [P] Unit test: fact filter predicates — concept match, period type match, dimension member match/exclude, unit match, empty result on no match in `tests/unit/validation/test_formula_filters.py`
- [ ] T044 [P] Unit test: xfi: function registrations — verify key xfi: functions return correct types; edge cases (empty facts list, missing period) in `tests/unit/validation/test_xfi_functions.py`
- [ ] T045 [P] Integration test: known-failing instance with known formula assertion failures → verify each expected `rule_id` appears in report findings in `tests/integration/validation/test_formula_assertions.py`

---

## Dependencies

```
Phase 1 (T001–T010) → Phase 2 (T011–T013) → Phase 3/US1 (T014–T031) → Phase 4/US2 (T032–T034)
                                                                       → Phase 5/US3 (T035–T036)
                                                                       → Phase 6/US4 (T037–T040)
                                                                                      ↓
                                                                       Phase 7 (T041–T045)
```

**Key sequential spines**:
- `T014` (formula linkbase parser) → `T015` (integrate into taxonomy loading) → `T022` (orchestrator) → `T031` (integration test)
- `T016` (structural) + `T017` (dimensional) + `T021` (formula evaluator) → `T023` (InstanceValidator.validate_sync)
- `T018` (xfi: functions) + `T019` (filters) → `T020` (_bind_variables) → `T021` (evaluator main loop)
- `T024` (ValidationWorker) + `T025` (ValidationResultsModel) + `T026` (ValidationPanel basic) → `T027` (main_window wiring)

**Phases 4, 5, 6 are independent of each other** — can be implemented in parallel after Phase 3 is complete.

---

## Parallel Execution Examples

**Within Phase 3/US1** (after T012 foundational models are done):
```
T014 → T015 (formula parser → taxonomy integration) ─┐
T016 (structural validator)                          ─┤→ T023 (orchestrator) → T027 (main window)
T017 (dimensional validator)                         ─┤
T018 → T019 → T020 → T021 → T022 (formula chain)   ─┘

T024 (ValidationWorker) ─┐
T025 (ResultsModel)     ─┤→ T026 (ValidationPanel basic) → T027
```

**Across Phases 4, 5, 6 (after Phase 3 complete)**:
```
Phase 4: T032–T034   (filter proxy)
Phase 5: T035–T036   (re-validate button)   ← all three in parallel
Phase 6: T037–T040   (export)
```

---

## Implementation Strategy

**MVP** = Phases 1–3 (T001–T031): Full validation run (structural + dimensional + formula) with result list and navigate-to-cell. This is the complete validation engine unblocked by Feature 004.

**Increment 2** = Phase 4 (T032–T034): Severity and table filtering — essential for usability with large result sets.

**Increment 3** = Phase 5 (T035–T036): Re-validate button — enables the edit-validate-fix loop.

**Increment 4** = Phase 6 (T037–T040): Export — audit/traceability for regulatory workflows.

**Phase 7** (T041–T045): Public exports, remaining unit tests, formula assertion integration test.

---

## Summary

| Phase | User Story | Tasks | Parallelizable |
|-------|-----------|-------|----------------|
| 1: Setup | — | T001–T010 (10) | T002–T010 all [P] |
| 2: Foundational | — | T011–T013 (3) | T012, T013 [P] |
| 3: US1 — Full Validation | P1 🎯 MVP | T014–T031 (18) | T029, T030, T031 [P] |
| 4: US2 — Filter Results | P2 | T032–T034 (3) | — |
| 5: US3 — Re-Validate | P3 | T035–T036 (2) | — |
| 6: US4 — Export Report | P4 | T037–T040 (4) | — |
| 7: Polish | — | T041–T045 (5) | T042–T045 all [P] |
| **Total** | | **45 tasks** | |

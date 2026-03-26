# Tasks: Conformance Suite Runner

**Input**: Design documents from `specs/006-conformance-suite-runner/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Exact file paths in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create all new package and file stubs — no logic yet

- [ ] T001 Create `src/bde_xbrl_editor/conformance/__init__.py` (empty re-export stub)
- [ ] T002 [P] Create `src/bde_xbrl_editor/conformance/__main__.py`, `registry.py`, `models.py`, `parser.py`, `executor.py`, `runner.py` (empty files with module docstrings)
- [ ] T003 [P] Create reporters sub-package: `src/bde_xbrl_editor/conformance/reporters/__init__.py`, `reporters/console.py`, `reporters/json_reporter.py` (empty files with docstrings)
- [ ] T004 [P] Create suite data directory structure: `tests/conformance/suite-data/xbrl-2.1/`, `tests/conformance/suite-data/dimensions-1.0/`, `tests/conformance/suite-data/table-linkbase-1.0/`, `tests/conformance/suite-data/formula-1.0/`; add `.gitkeep` in each; add `tests/conformance/formula_skip_list.py` stub
- [ ] T005 [P] Create test directories and files: `tests/unit/conformance/__init__.py`, `test_parser.py`, `test_executor.py`, `test_runner.py`, `test_registry.py`, `test_reporters.py`; `tests/integration/conformance/__init__.py`, `test_xbrl21_suite.py`, `test_dimensions_suite.py`, `test_formula_suite.py`, `test_table_linkbase_suite.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Domain types and registry constant that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Implement domain types in `src/bde_xbrl_editor/conformance/models.py`: `SuiteStatus` (str Enum: PASSED/FAILED/ERRORED/INCOMPLETE/SKIPPED), `TestResultOutcome` (str Enum: PASS/FAIL/ERROR/SKIPPED), `ExpectedOutcomeType` (VALID/ERROR/WARNING), `ExpectedOutcome` (outcome_type, error_code), `TestVariation` (variation_id, name, description, input_files, instance_file, taxonomy_file, expected_outcome, mandatory), `TestCase` (test_case_id, description, source_file, suite_id, variations), `TestCaseResult` (variation_id, test_case_id, suite_id, outcome, mandatory, expected_outcome, actual_error_codes, exception_message, description, input_files, duration_ms), `SuiteResult` (suite_id, label, blocking, status, results, informational_note; computed: total, passed, failed, failed_optional, errored, skipped, failures), `SuiteRunReport` (run_timestamp, runner_version, suite_results, exit_code; computed: overall_passed, blocking_failures)
- [ ] T007 [P] Implement `SUITE_REGISTRY` constant and `SuiteDefinition` dataclass in `src/bde_xbrl_editor/conformance/registry.py` — 4 entries: xbrl21 (blocking=True), dimensions (blocking=True), table-linkbase (blocking=False, informational_note), formula (blocking=True, informational_note); each with correct index_filename and subdirectory
- [ ] T008 [P] Implement error types in `src/bde_xbrl_editor/conformance/`: `SuiteDataMissingError` (suite_id, expected_path), `TestCaseParseError` (file_path, reason), `ConformanceConfigError` (message with valid options list)
- [ ] T009 [P] Implement `FORMULA_SKIP_LIST` frozenset in `tests/conformance/formula_skip_list.py` — empty frozenset with documented structure and inline comments for future variation ID entries (custom functions, tuple producers, filter chaining)

**Checkpoint**: Domain types, registry, error types ready — user story phases can now proceed

---

## Phase 3: User Story 1 — Run All Conformance Suites and See a Pass/Fail Summary (Priority: P1) 🎯 MVP

**Goal**: Parse all four XBRL.org conformance suites, execute every variation against the processing engine, aggregate results, and print a per-specification pass/fail summary; exit code 0 if all blocking suites pass.

**Independent Test**: Run `ConformanceRunner.run()` against local suite data for the XBRL 2.1 suite; verify `SuiteRunReport` contains one `SuiteResult` with `suite_id="xbrl21"`; verify `exit_code=0` if all mandatory cases pass; verify `exit_code=1` if any mandatory case fails; verify `run()` never raises.

- [ ] T010 [US1] Implement `ConformanceSuiteParser._parse_index()` and `_parse_test_case()` in `src/bde_xbrl_editor/conformance/parser.py` — lxml XML parsing; index file → list of test case file paths; test case file → `TestCase` with all `TestVariation` objects; all input file paths resolved to absolute paths relative to suite data directory
- [ ] T011 [US1] Implement `ConformanceSuiteParser.load_suite()` in `src/bde_xbrl_editor/conformance/parser.py` — check index file exists (raise `SuiteDataMissingError` if not); call `_parse_index()` then `_parse_test_case()` for each; skip and log warning on `TestCaseParseError`; return `list[TestCase]`
- [ ] T012 [US1] Implement `TestCaseExecutor._match_outcome()` in `src/bde_xbrl_editor/conformance/executor.py` — 5 outcome cases: VALID+no-errors→PASS; VALID+errors→FAIL(actual codes); ERROR(code)+finding-matching-rule_id→PASS; ERROR(code)+no-match→FAIL; ERROR(code)+load_error-matching-code→PASS; returns `tuple[TestResultOutcome, tuple[str, ...]]`
- [ ] T013 [US1] Implement `TestCaseExecutor.execute()` in `src/bde_xbrl_editor/conformance/executor.py` — (1) skip-list check → SKIPPED immediately; (2) load taxonomy via `TaxonomyLoader` with `TaxonomyCache`; (3) parse instance via `InstanceParser` if `instance_file` present; (4) run `InstanceValidator.validate_sync()`; (5) call `_match_outcome()`; (6) catch all exceptions → ERROR outcome; (7) measure wall-clock duration
- [ ] T014 [US1] Implement `ConformanceRunner.run()` and `_compute_exit_code()` in `src/bde_xbrl_editor/conformance/runner.py` — for each selected suite: create one `TaxonomyCache`; call parser + executor per variation; aggregate into `SuiteResult`; call `_compute_exit_code()` (0 if all blocking suites have status PASSED; 1 otherwise); build `SuiteRunReport`; progress_callback per variation; never raises
- [ ] T015 [US1] Implement `ConsoleReporter.print_report()` and `print_progress()` in `src/bde_xbrl_editor/conformance/reporters/console.py` — summary table: suite name, total/passed/failed/errored/skipped counts per spec; overall PASSED/FAILED banner; informational_note for non-blocking suites; ANSI colour when stdout is TTY; single-line progress update (overwritten in-place on TTY)
- [ ] T016 [US1] Unit test: `ConformanceSuiteParser` — index parsing produces correct test case count; test case parsing produces correct variation count; `SuiteDataMissingError` when index not found; malformed XML skips case in `tests/unit/conformance/test_parser.py`
- [ ] T017 [P] [US1] Unit test: `TestCaseExecutor._match_outcome()` — all 5 outcome combinations with crafted `ExpectedOutcome` + `ValidationFinding` fixtures in `tests/unit/conformance/test_executor.py`
- [ ] T018 [P] [US1] Unit test: `SUITE_REGISTRY` — all 4 suites registered; `table-linkbase` has `blocking=False`; all `SuiteDefinition` fields non-null; xbrl21/dimensions/formula have `blocking=True` in `tests/unit/conformance/test_registry.py`
- [ ] T019 [P] [US1] Integration test: XBRL 2.1 suite run — load from `tests/conformance/suite-data/xbrl-2.1/`; verify mandatory case count matches suite index; verify exit_code=0 when all mandatory pass in `tests/integration/conformance/test_xbrl21_suite.py`
- [ ] T020 [P] [US1] Integration test: Dimensions 1.0 suite run — same pattern as XBRL 2.1; 100% mandatory pass target in `tests/integration/conformance/test_dimensions_suite.py`

---

## Phase 4: User Story 2 — Run a Single Specification's Suite in Isolation (Priority: P2)

**Goal**: `--suite {xbrl21,dimensions,table-linkbase,formula,all}` CLI argument; selected suites run, others marked SKIPPED; unrecognised value → error with valid options.

**Independent Test**: Invoke `python -m bde_xbrl_editor.conformance --suite dimensions`; verify only the Dimensions 1.0 suite appears in output; verify other suites are not executed; invoke with `--suite unknown` and verify `ConformanceConfigError` is raised with valid options listed.

- [ ] T021 [US2] Implement `__main__.py` with argparse in `src/bde_xbrl_editor/conformance/__main__.py` — arguments: `--suite` (choices: xbrl21/dimensions/table-linkbase/formula/all; default: all), `--suite-data-dir` (default: `tests/conformance/suite-data/`), `--verbose`, `--stop-on-first-failure`, `--output-format` (console/json; default: console), `--output-file`; normalise "all" → all 4 suite IDs; raise `ConformanceConfigError` on unrecognised suite; wire `ConformanceRunner` + reporters; call `sys.exit(report.exit_code)`
- [ ] T022 [US2] Wire `selected_suites` into `ConformanceRunner.__init__()` in `src/bde_xbrl_editor/conformance/runner.py` — suites not in selected_suites get `SuiteResult(status=SuiteStatus.SKIPPED)` in `SuiteRunReport`; only selected suites are parsed and executed

---

## Phase 5: User Story 3 — Inspect Individual Test Case Results (Priority: P3)

**Goal**: Verbose output mode shows full detail per failing test case: description, input files, expected outcome, actual error codes; non-verbose shows summary only.

**Independent Test**: Create a `SuiteRunReport` with one failing `TestCaseResult`; call `ConsoleReporter(verbose=True).print_report(report)`; verify output contains description, input file path, expected error code, and actual error codes; call with `verbose=False` and verify these details are absent.

- [ ] T023 [US3] Extend `ConsoleReporter.print_report()` in `src/bde_xbrl_editor/conformance/reporters/console.py` — when `verbose=True`, after each suite summary print per-failing-variation detail block: test_case_id, variation_id, description, input_files paths, expected outcome, actual_error_codes, exception_message; concise mode shows only the summary table
- [ ] T024 [US3] Unit test: `ConsoleReporter` — summary-only vs verbose output; ANSI codes present on TTY; `JsonReporter.to_dict()` schema structure in `tests/unit/conformance/test_reporters.py`

---

## Phase 6: User Story 4 — Track Table Linkbase 1.0 Conformance Without Blocking Builds (Priority: P4)

**Goal**: TL 1.0 suite results are informational; `blocking=False` in registry; exit code unaffected by TL 1.0 failures; `informational_note` displayed prominently in output.

**Independent Test**: Construct a `SuiteRunReport` with one blocking suite (PASSED) and one non-blocking suite (FAILED); call `_compute_exit_code()` and verify result is `0`; verify `ConsoleReporter` displays the `informational_note` next to the TL 1.0 result block.

- [ ] T025 [US4] Integration test: Table Linkbase 1.0 suite run — load from `tests/conformance/suite-data/table-linkbase-1.0/`; verify `SuiteResult.blocking=False`; verify `exit_code=0` even when TL 1.0 cases fail; verify `informational_note` appears in output in `tests/integration/conformance/test_table_linkbase_suite.py`

---

## Phase 7: User Story 5 — Use the Suite Runner in CI as a Build Gate (Priority: P5)

**Goal**: JSON output format (`--output-format json`); exit code 0/1 per blocking results; machine-readable for CI tooling; Formula 1.0 skip list transparently marks out-of-scope variations as SKIPPED.

**Independent Test**: Run `ConformanceRunner` with a report that has one blocking-FAILED suite; verify `exit_code=1`; call `JsonReporter.to_dict()` on the report and parse the JSON; verify it contains `"exit_code": 1` and `"suite_results"` array with correct `"status"` fields; verify a report with all-PASSED blocking suites returns `"exit_code": 0`.

- [ ] T026 [US5] Implement `JsonReporter.to_dict()` and `JsonReporter.write()` in `src/bde_xbrl_editor/conformance/reporters/json_reporter.py` — `to_dict()` converts `SuiteRunReport` to documented JSON schema (run_timestamp ISO8601, runner_version, exit_code, suite_results array with total/passed/failed/errored/skipped counts and failures detail); `write()` serialises to file; raises `PermissionError` on unwritable path
- [ ] T027 [US5] Unit test: `ConformanceRunner` exit code logic — all blocking PASSED → 0; any blocking FAILED → 1; INCOMPLETE blocking → 1; non-blocking-only failures → 0; stop_on_first_failure terminates early in `tests/unit/conformance/test_runner.py`
- [ ] T028 [P] [US5] Integration test: Formula 1.0 scoped suite — in-scope value/existence/consistency assertions pass; skip-listed variations appear as SKIPPED in results; exit_code respects blocking flag in `tests/integration/conformance/test_formula_suite.py`

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Public API exports and entry point registration

- [ ] T029 Populate `src/bde_xbrl_editor/conformance/__init__.py` re-exports: `ConformanceRunner`, `SuiteRunReport`, `SuiteResult`, `TestCaseResult`, `SuiteStatus`, `TestResultOutcome`, `SUITE_REGISTRY`, `SuiteDataMissingError`, `ConformanceConfigError`
- [ ] T030 [P] Register CLI entry point in `pyproject.toml` — add `bde-xbrl-conformance = "bde_xbrl_editor.conformance.__main__:main"` under `[project.scripts]`; verify `python -m bde_xbrl_editor.conformance --help` works

---

## Dependencies

```
Phase 1 (T001–T005) → Phase 2 (T006–T009) → Phase 3/US1 (T010–T020) → Phase 4/US2 (T021–T022)
                                                                       → Phase 5/US3 (T023–T024)
                                                                       → Phase 6/US4 (T025)
                                                                       → Phase 7/US5 (T026–T028)
                                                                                       ↓
                                                                       Phase 8 (T029–T030)
```

**Key sequential spines**:
- `T010–T011` (parser) → `T012–T013` (executor) → `T014` (runner) → `T019–T020` (integration tests)
- `T015` (ConsoleReporter basic) → `T023` (verbose extension) → `T024` (reporter unit test)
- `T007` (SUITE_REGISTRY) → `T022` (suite selection in runner) → `T021` (__main__.py argparse)

**Phases 4–7 are independent of each other** after Phase 3 is complete.

---

## Parallel Execution Examples

**Within Phase 3/US1**:
```
T010 → T011 (parser stages) ─┐
T012 (match_outcome)         ─┤→ T013 (execute) → T014 (runner) → T015 (reporter)
                              ┘

T017 (match_outcome unit test) ─┐
T018 (registry unit test)      ─┤→ all in parallel after Phase 2
T019 (XBRL 2.1 integration)    ─┤
T020 (Dimensions integration)  ─┘
```

**Across Phases 4–7 (after Phase 3 complete)**:
```
Phase 4: T021–T022   (CLI single suite)
Phase 5: T023–T024   (verbose output)     ← all four in parallel
Phase 6: T025        (TL 1.0 info test)
Phase 7: T026–T028   (JSON + CI)
```

---

## Implementation Strategy

**MVP** = Phases 1–3 (T001–T020): Full four-suite run with summary output and exit code. This is the CI-blocking requirement from the start.

**Increment 2** = Phase 4 (T021–T022): Single-suite CLI selection — enables fast developer iteration.

**Increment 3** = Phase 5 (T023–T024): Verbose detail output — enables debugging of individual failures.

**Increment 4** = Phase 6 (T025): TL 1.0 informational integration test — documents the non-blocking baseline.

**Increment 5** = Phase 7 (T026–T028): JSON output and Formula skip list — completes the CI integration story.

**Phase 8** (T029–T030): Public exports and entry point registration.

---

## Summary

| Phase | User Story | Tasks | Parallelizable |
|-------|-----------|-------|----------------|
| 1: Setup | — | T001–T005 (5) | T002–T005 all [P] |
| 2: Foundational | — | T006–T009 (4) | T007, T008, T009 [P] |
| 3: US1 — Full Suite Run | P1 🎯 MVP | T010–T020 (11) | T017–T020 [P] |
| 4: US2 — Single Suite | P2 | T021–T022 (2) | — |
| 5: US3 — Inspect Results | P3 | T023–T024 (2) | — |
| 6: US4 — TL 1.0 Non-Blocking | P4 | T025 (1) | — |
| 7: US5 — CI Integration | P5 | T026–T028 (3) | T028 [P] |
| 8: Polish | — | T029–T030 (2) | T030 [P] |
| **Total** | | **30 tasks** | |

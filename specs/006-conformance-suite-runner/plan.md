# Implementation Plan: Conformance Suite Runner

**Branch**: `006-conformance-suite-runner` | **Date**: 2026-03-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/006-conformance-suite-runner/spec.md`

## Summary

Implement a headless CLI conformance suite runner (`python -m bde_xbrl_editor.conformance`) that executes the four XBRL.org conformance suites — XBRL 2.1, Dimensions 1.0, Table Linkbase 1.0, and Formula 1.0 — against the project's processing engine and reports pass/fail results per test case. A `ConformanceSuiteParser` reads the XBRL.org XML test case format; a `TestCaseExecutor` drives each variation through `TaxonomyLoader` + `InstanceParser` + `InstanceValidator`; a `ConformanceRunner` orchestrates the run and produces a `SuiteRunReport`. Table Linkbase 1.0 results are informational and non-blocking; the exit code is determined solely by XBRL 2.1, Dimensions 1.0, and Formula 1.0 mandatory failures. CI integration via exit code and JSON output.

**Tech stack**: Python 3.11+ · stdlib only (argparse, sys, json, pathlib, datetime) · lxml (suite XML parsing) · reuses Features 001–005 processing engine directly

---

## Technical Context

**Language/Version**: Python 3.11+
**New dependencies**: none — stdlib + lxml (already in stack); processing engine from Features 001–005
**Storage**: `SuiteRunReport` in memory; optional export to JSON or text file
**Testing**: pytest; unit tests for `ConformanceSuiteParser` (XML parsing), `TestCaseExecutor` (outcome matching logic); integration test wraps `ConformanceRunner` against real suite data
**Performance goals**: Full four-suite run completes in <10 minutes (SC-002); achieved via `TaxonomyCache` reuse across test cases in the same suite
**Constraints**: Fully non-interactive, no PySide6 import, no network calls (`LoaderSettings.allow_network=False`); `ConformanceRunner.run()` never raises; incomplete suite data → `INCOMPLETE`, not `PASSED`
**Scale/Scope**: ~1,250 test cases total across 4 suites; single run per CI invocation

---

## Constitution Check

**Gates applied**:
- ✅ No PySide6 import anywhere in `bde_xbrl_editor.conformance` — fully headless (FR-008)
- ✅ `ConformanceRunner.run()` never raises — all exceptions captured in `TestCaseResult.outcome = ERROR`
- ✅ Table Linkbase 1.0 `blocking=False` is a registry constant, not a runtime flag — cannot be accidentally overridden
- ✅ Exit code is computed from `SuiteResult.blocking` flag, not hardcoded suite names — adding a future suite is a registry-only change
- ✅ Processing engine (Features 001–005) is used as-is, black-box — no duplicate XBRL processing logic
- ✅ `TaxonomyCache` reuse: suite runner creates one cache and passes it to all `TestCaseExecutor` invocations within a suite run — satisfies Feature 001 "loaded once and cached" principle
- ✅ `allow_network=False` in all `LoaderSettings` — satisfies "no external network calls at runtime" (Feature 001 constraint)
- ✅ `SUITE_REGISTRY` is module-level constant — immutable at runtime, testable in isolation
- ✅ Formula skip list is explicit, versioned, and reported as `SKIPPED` (not silently ignored) — SC-002 compliance

---

## Project Structure

### Documentation (this feature)

```text
specs/006-conformance-suite-runner/
├── spec.md
├── plan.md              ← this file
├── research.md          ← Phase 0: suite XML format, CLI entry point, sequential execution,
│                                   suite data layout, outcome matching, output format,
│                                   network isolation, formula scope restriction
├── data-model.md        ← Phase 1: SuiteDefinition, TestCase, TestVariation, ExpectedOutcome,
│                                   TestCaseResult, SuiteResult, SuiteRunReport,
│                                   ConformanceSuiteParser, TestCaseExecutor, ConformanceRunner,
│                                   ConsoleReporter, JsonReporter
├── contracts/
│   └── conformance-runner-api.md  ← Phase 1: CLI contract, Python API, JSON schema,
│                                              CI integration pattern, error hierarchy
└── tasks.md             ← Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code (additions to project)

```text
src/
└── bde_xbrl_editor/
    ├── taxonomy/          # Feature 001 — unchanged
    ├── instance/          # Features 002/004 — unchanged
    ├── table_renderer/    # Feature 003 — unchanged
    ├── validation/        # Feature 005 — unchanged
    └── conformance/       # ← NEW PACKAGE
        ├── __init__.py         # exports: ConformanceRunner, SuiteRunReport, SuiteResult,
        │                       #          TestCaseResult, SuiteStatus, TestResultOutcome
        ├── __main__.py         # CLI entry point: argparse + ConformanceRunner + reporters + sys.exit
        ├── registry.py         # SUITE_REGISTRY constant dict[str, SuiteDefinition];
        │                       # SuiteDefinition, SuiteStatus dataclass/enum
        ├── models.py           # TestCase, TestVariation, ExpectedOutcome, ExpectedOutcomeType,
        │                       # TestCaseResult, SuiteResult, SuiteRunReport (frozen dataclasses)
        ├── parser.py           # ConformanceSuiteParser: lxml-based XML parser for XBRL.org
        │                       #   conformance suite index + test case files
        ├── executor.py         # TestCaseExecutor: drives TaxonomyLoader + InstanceParser +
        │                       #   InstanceValidator; outcome matching logic
        ├── runner.py           # ConformanceRunner: orchestrates parse → execute → aggregate
        └── reporters/
            ├── __init__.py
            ├── console.py      # ConsoleReporter: ANSI-coloured terminal output
            └── json_reporter.py # JsonReporter: to_dict() + write() for JSON output

tests/
├── conformance/
│   ├── suite-data/             # XBRL.org conformance suite test data (see quickstart.md)
│   │   ├── xbrl-2.1/
│   │   ├── dimensions-1.0/
│   │   ├── table-linkbase-1.0/
│   │   └── formula-1.0/
│   └── formula_skip_list.py    # frozenset of Formula 1.0 variation IDs out of v1 scope
├── unit/
│   └── conformance/
│       ├── test_parser.py           # ConformanceSuiteParser: index parsing, test case parsing,
│       │                            #   missing file handling, malformed XML handling
│       ├── test_executor.py         # TestCaseExecutor._match_outcome(): all outcome combinations
│       ├── test_runner.py           # ConformanceRunner: exit code logic, INCOMPLETE suite,
│       │                            #   skip list, stop-on-first-failure
│       ├── test_registry.py         # SUITE_REGISTRY: all 4 suites registered, TL 1.0 non-blocking
│       └── test_reporters.py        # ConsoleReporter and JsonReporter output format
└── integration/
    └── conformance/
        ├── test_xbrl21_suite.py          # Full XBRL 2.1 suite: 100% mandatory pass target
        ├── test_dimensions_suite.py      # Full Dimensions 1.0 suite: 100% mandatory pass target
        ├── test_formula_suite.py         # Formula 1.0 scoped suite: 100% in-scope pass target
        └── test_table_linkbase_suite.py  # TL 1.0 suite: informational, no pass target
```

---

## Complexity Tracking

| Area | Complexity | Reason |
|------|-----------|--------|
| `ConformanceSuiteParser` | MEDIUM | Four slightly different XML formats; robust path resolution |
| `TestCaseExecutor._match_outcome` | MEDIUM | Multiple outcome combinations; error code mapping |
| `ConformanceRunner` + exit code | LOW | Straightforward aggregation; simple predicate |
| `ConsoleReporter` | LOW | String formatting with ANSI codes |
| `JsonReporter` | LOW | Dataclass → dict serialisation |
| `__main__.py` CLI | LOW | argparse + connect pieces + sys.exit |
| Suite data acquisition | EXTERNAL | One-time setup; documented in quickstart.md |

---

## Key Decisions (from research.md)

1. **lxml** for suite XML parsing — already in stack; handles all four suite XML formats
2. **argparse** for CLI — stdlib, no extra dependency
3. **Sequential execution + TaxonomyCache** — achieves <10 min target; parallel execution deferred to v2
4. **Suite data in `tests/conformance/suite-data/`** — local, versioned, no network; `--suite-data-dir` override for CI
5. **Error code matching** — `rule_id` in `ValidationFinding` must use XBRL error code format (cross-cutting constraint with Feature 005)
6. **Console + JSON output** — default human-readable; `--output-format json` for CI tooling
7. **`allow_network=False`** in all `LoaderSettings` during conformance runs
8. **Formula skip list** — explicit frozenset; SKIPPED is reported transparently, not hidden

---

## Cross-Cutting Constraint for Feature 005

The `TestCaseExecutor` matches `actual_error_codes` against `ValidationFinding.rule_id` values. The Feature 005 validators must produce `rule_id` values using official XBRL specification error codes for spec-mandated rules:

| Validator | Expected rule_id format | Example |
|-----------|------------------------|---------|
| `StructuralConformanceValidator` | `xbrl.N.M.P` (XBRL 2.1 section) | `xbrl.4.9.1` |
| `DimensionalConstraintValidator` | `xdt.DNN` (Dimensions spec clause) | `xdt.D01` |
| `FormulaEvaluator` | `formula.FNN` (Formula spec clause) | `formula.F01` |

Internal BDE-specific rules continue to use the `structural:`, `dimensional:`, `formula:` prefix style.

---

## Dependency Map

```
Feature 001 (taxonomy loader + cache) ──used by──▶ TestCaseExecutor
Feature 004 (instance parser)         ──used by──▶ TestCaseExecutor
Feature 005 (instance validator)      ──used by──▶ TestCaseExecutor
Feature 006 (this) ──produces──▶ SuiteRunReport ──rendered by──▶ ConsoleReporter / JsonReporter
                   ──sets──▶ sys.exit(report.exit_code)
```

---

## Out of Scope (confirmed from spec)

- Downloading or auto-updating suite data at runtime
- Authoring or editing test cases
- GUI for browsing results
- Differential suite runs
- Full Formula 1.0 coverage (custom functions, filter chaining) — v2
- Table Linkbase 1.0 as CI-blocking — future version when TL 1.0 is implemented

# Research: Conformance Suite Runner

**Branch**: `006-conformance-suite-runner` | **Phase**: 0 | **Date**: 2026-03-26
**Inherits from**: Features 001–005 tech stack (Python 3.11+, lxml, elementpath, dataclasses)

---

## Decision 1: XBRL.org Conformance Suite XML Format

**Decision**: Parse conformance suites using the published XBRL.org format (XML), using lxml for all index and test-case file parsing.

**Rationale**: All four targeted XBRL.org conformance suites share the same XML schema family:

**Index file** (`xbrl.org-index.xml` or `conformanceSuite.xml`): root element is `<testcases>` (or `<conformanceSuite>`). Each child `<testcase>` (or `<testGroup>`) has:
- `@name` — test case identifier (e.g., `"V-01"`)
- `@description` — human-readable description of the test
- `@uri` — relative path to the individual test case file

**Test case file** (e.g., `V-01.xml`): root `<testcase>` with one or more `<variation>` children. Each variation has:
- `@id` — unique variation ID
- `@name` — variation name
- `<data>` — input files (`<taxonomy>`, `<instance>`, `<schema>`)
- `<result>` — expected outcome:
  - `<error>` with text = XBRL error code (e.g., `"xbrl.4.2.3"`) → processor should raise this error
  - `<valid>` → processor should accept without error
  - `<warning>` with error code → processor should produce this warning

**Mandatory vs optional**: The XBRL 2.1 suite uses `@blocked="true"` for optional/informational tests. The Dimensions 1.0 suite marks some tests as optional via `@type="optional"`. Each suite has minor format variations; the parser must handle all.

**Formula 1.0 suite**: Uses `<conformanceSuite>` / `<testGroup>` hierarchy with `<data>` / `<result>` per variation. Similar structure but deeper nesting.

**Table Linkbase 1.0 suite**: Same pattern as Formula 1.0.

**Alternatives considered**: Third-party test harness libraries — none exist specifically for XBRL conformance suite XML format. Using pytest's parametrize with the suite XML — viable but couples the runner to pytest's test discovery mechanism, conflicting with the requirement for a standalone headless CLI tool (FR-001, FR-008).

---

## Decision 2: CLI Entry Point — `python -m` with argparse

**Decision**: Implement the runner as a Python module callable via `python -m bde_xbrl_editor.conformance` with `argparse` for argument parsing.

**Rationale**: The runner must be fully non-interactive and headless (FR-008). A `__main__.py` in the `conformance` package makes it directly invocable with `python -m`. `argparse` (stdlib) is sufficient for the command surface:

```
Usage: python -m bde_xbrl_editor.conformance [options]

Options:
  --suite {xbrl21,dimensions,table-linkbase,formula,all}
                        Suite(s) to run (default: all)
  --suite-data-dir DIR  Root directory containing all suite test data
                        (default: ./tests/conformance/suite-data/)
  --output-format {console,json}
                        Output format (default: console)
  --output-file FILE    Write report to file in addition to stdout
  --verbose             Show per-test-case results (not just summary)
  --stop-on-first-failure
                        Abort the run on the first failure (useful during dev)
  -v, --version         Show runner version and exit
```

A pyproject.toml console script entry point (`conformance-runner = bde_xbrl_editor.conformance.__main__:main`) provides a shorter invocation name as an alias.

**Alternatives considered**: Click — powerful but adds a dependency for a single-purpose CLI. Typer — even heavier. argparse provides everything needed for this use case.

---

## Decision 3: Test Case Execution — Sequential with Per-Case Exception Isolation

**Decision**: Execute test cases sequentially within each suite, with each test case wrapped in a `try/except Exception` to catch unhandled processor exceptions (FR-012). Do not parallelise test case execution in v1.

**Rationale**: Each test case runs the project's own processing engine (taxonomy loader + instance parser + validator), which uses lxml trees in memory. These are not thread-safe for concurrent writes; `ProcessPoolExecutor` would require pickling lxml trees (not supported). The spec's performance target (full run in <10 minutes, SC-002) is achievable sequentially for the typical XBRL.org suite sizes:
- XBRL 2.1 suite: ~600 test cases
- Dimensions 1.0: ~400 test cases
- Formula 1.0: ~200 test cases (scoped subset for v1)
- Table Linkbase 1.0: ~50 test cases

At ~1 second average per test case, the full run is ~21 minutes — slightly over target. Optimisation paths: cache taxonomy DTS across test cases in the same suite (most reuse the same base taxonomy); use `TaxonomyCache` from Feature 001. With caching, average time drops to ~200ms per case → full run ~4 minutes.

**Alternatives considered**: `ThreadPoolExecutor` — lxml is not thread-safe for concurrent element access on the same tree; safe only if each case builds an independent tree (which it does, since each case has its own files). Could be enabled in v2 for parallel execution. `multiprocessing` — correct isolation but high overhead per process; defer to v2 if single-threaded with caching is too slow.

---

## Decision 4: Suite Test Data Directory Layout

**Decision**: All conformance suite test data is stored under `tests/conformance/suite-data/` in the repository, with one subdirectory per suite. The runner discovers suite data by looking for a known index filename in each subdirectory.

```
tests/conformance/suite-data/
├── xbrl-2.1/
│   └── xbrl.org-index.xml          ← XBRL 2.1 Conformance Suite index
├── dimensions-1.0/
│   └── xdt.index.xml               ← Dimensions 1.0 index
├── table-linkbase-1.0/
│   └── tableLinkbase.index.xml     ← Table Linkbase 1.0 index
└── formula-1.0/
    └── formula.index.xml           ← Formula 1.0 index
```

The `--suite-data-dir` argument overrides the default location, enabling CI environments to store suite data outside the repository (e.g., a mounted volume or artifact cache).

**Missing suite data handling** (FR-010): If the expected index file is not found in a suite directory, the suite is classified as `INCOMPLETE` (not `PASSED`). The runner reports which suites are incomplete and does not count them as passing or failing. Exit code logic ignores incomplete suites when computing the final exit code — a missing suite is treated as `SKIPPED`, not `FAILED`.

---

## Decision 5: Expected Outcome Matching

**Decision**: Match actual processor output against expected outcomes using error code comparison. Processor errors are represented as `ValidationFinding` objects with typed `rule_id` values matching the XBRL error code taxonomy.

**Matching rules**:
- Expected `<valid>` → actual result has zero `ERROR`-severity findings → `PASS`
- Expected `<valid>` → actual result has one or more errors → `FAIL` (report first error code)
- Expected `<error code="xbrl.4.2.3">` → actual result has a finding with `rule_id="xbrl.4.2.3"` → `PASS`
- Expected `<error code="xbrl.4.2.3">` → actual result has no matching finding → `FAIL`
- Expected `<error code="xbrl.4.2.3">` → processor throws unhandled exception → `ERROR` (not `FAIL`)
- Expected `<warning code="xbrl.xyz">` → matched against `WARNING`-severity findings

**Error code taxonomy**: XBRL 2.1 uses codes like `xbrl.4.2.3` (section number). Dimensions uses `xdt.D01`, `xdt.D02`. Formula uses `formula.F01`. The project's `rule_id` field in `ValidationFinding` (Feature 005) must be populated with these codes for the test harness to match correctly. The structural validator's rule IDs (currently `structural:duplicate-fact`) must be mapped to XBRL 2.1 error code equivalents (e.g., `xbrl.4.2.3` for duplicate facts) to enable conformance suite matching.

**Alternatives considered**: String pattern matching on error messages — fragile and brittle; rule_id codes are authoritative.

---

## Decision 6: Output Format — Console Table + Optional JSON

**Decision**: Default output is a formatted console table (coloured with ANSI codes if stdout is a TTY). Optional `--output-format json` writes machine-readable JSON for CI tooling integration.

**Console format** (default):
```
============================================================
XBRL Conformance Suite Runner — v1.0.0
============================================================

Suite: XBRL 2.1 Conformance Suite         [CI-BLOCKING]
  ✓ 598/600 passed  ✗ 2 failed  ⚡ 0 errored

FAILURES:
  [V-002] Variation 002: expected xbrl.4.2.3, got: no error raised
          Input: xbrl-2.1/V-002/instance.xml
  [V-015] Variation 015: expected valid, got: xbrl.4.9.1 (duplicate fact)
          Input: xbrl-2.1/V-015/instance.xml

------------------------------------------------------------
Suite: Dimensions 1.0 Conformance Suite   [CI-BLOCKING]
  ✓ 400/400 passed  ✗ 0 failed  ⚡ 0 errored

------------------------------------------------------------
Suite: Formula 1.0 Conformance Suite      [CI-BLOCKING]
  ✓ 195/200 passed  ✗ 5 failed  ⚡ 0 errored
  (v1 scope: value/existence/consistency assertions only)

------------------------------------------------------------
Suite: Table Linkbase 1.0                 [INFORMATIONAL — non-blocking]
  ℹ️ This suite is informational in v1. The application implements
    Table Linkbase PWD; TL 1.0 failures are expected and planned for v2.
  ✓ 12/50 passed  ✗ 38 failed

============================================================
OVERALL: ✗ FAILED (7 mandatory failures in CI-blocking suites)
Exit code: 1
```

**JSON format** (--output-format json):
```json
{
  "runner_version": "1.0.0",
  "run_timestamp": "2026-03-26T14:00:00Z",
  "overall_passed": false,
  "exit_code": 1,
  "suites": [
    {
      "name": "xbrl21",
      "label": "XBRL 2.1 Conformance Suite",
      "blocking": true,
      "status": "FAILED",
      "total": 600, "passed": 598, "failed": 2, "errored": 0, "skipped": 0,
      "failures": [...]
    },
    {
      "name": "table-linkbase",
      "label": "Table Linkbase 1.0",
      "blocking": false,
      "informational_note": "App implements Table Linkbase PWD in v1; TL 1.0 failures are non-blocking.",
      "status": "FAILED",
      "total": 50, "passed": 12, "failed": 38, "errored": 0, "skipped": 0,
      "failures": [...]
    }
  ]
}
```

**Alternatives considered**: JUnit XML — useful for some CI systems but more complex to generate; can be added in v2 if a CI integration requires it. Rich/Textualize — powerful terminal rendering but adds a dep; ANSI codes are sufficient.

---

## Decision 7: Network Isolation — Offline-Only Processing

**Decision**: The runner configures `TaxonomyLoader` with `allow_network=False` (Feature 001 `LoaderSettings`). All `xsi:schemaLocation` and remote `xs:import` references in conformance suite test data are satisfied from the local filesystem only. The runner fails a test case with an `ERROR` result if any taxonomy reference requires a network fetch.

**Rationale**: CI environments (air-gapped, containerised) cannot make network calls (FR-011). The XBRL.org conformance suites are designed to be self-contained: all referenced schemas are bundled in the suite directory. Remote URIs in test data are resolved via the project's URI-to-local-path catalog mapping.

**Catalog mapping**: The suite runner builds a local catalog from the suite directory structure. Standard XBRL schema namespace URIs (e.g., `http://www.xbrl.org/2003/instance`) are mapped to the bundled copies in the suite data directory.

---

## Decision 8: Formula 1.0 Suite Scope Restriction

**Decision**: For the Formula 1.0 conformance suite, the runner only executes test cases tagged as in-scope for v1 (value assertions, existence assertions, consistency assertions). Test cases exercising out-of-scope formula features (custom functions, tuple producers, filter chaining beyond the supported subset) are classified as `SKIPPED` and excluded from both pass counts and exit code computation.

**Implementation**: A static skip-list of Formula 1.0 test case IDs that exercise v1-out-of-scope formula features is maintained in `tests/conformance/formula_skip_list.py`. Skipped cases are reported in the output as `SKIPPED (out of v1 scope)` to be transparent. The skip list is reviewed and shortened with each release as more formula features are implemented.

**Rationale**: Running the full Formula 1.0 suite and reporting massive failures on unimplemented features would give a misleading picture. Skipping with explicit declaration is honest — it shows exactly what is and is not covered, and the skip list is the roadmap.

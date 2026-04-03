# Data Model: Conformance Suite Runner

**Branch**: `006-conformance-suite-runner` | **Phase**: 1 | **Date**: 2026-03-26

---

## Overview

Feature 006 is a standalone CLI tool that reuses the project's processing engine (Features 001–005) as a black box. No existing models are mutated. The additions are:

1. **Suite registry types** — `SuiteDefinition`, `SuiteStatus` — describe which suites exist and their CI role
2. **Test case parsing** — `ConformanceSuiteParser` — reads XBRL.org conformance suite XML into typed test case objects
3. **Test case execution** — `TestCaseExecutor` — runs the processor against a test case and compares to expected outcome
4. **Result types** — `TestCaseResult`, `SuiteResult`, `SuiteRunReport` — immutable structured output
5. **Runner orchestrator** — `ConformanceRunner` — coordinates parse → execute → report
6. **CLI entry point** — `__main__.py` — argparse CLI; produces console or JSON output; sets exit code

---

## Suite Registry

### `SuiteStatus` (enum)

```python
class SuiteStatus(str, Enum):
    PASSED    = "PASSED"     # all mandatory cases passed
    FAILED    = "FAILED"     # one or more mandatory cases failed
    ERRORED   = "ERRORED"    # one or more processor exceptions
    INCOMPLETE = "INCOMPLETE" # suite data not found on disk
    SKIPPED   = "SKIPPED"    # suite not selected for this run
```

### `TestResultOutcome` (enum)

```python
class TestResultOutcome(str, Enum):
    PASS    = "PASS"    # actual matched expected
    FAIL    = "FAIL"    # actual did not match expected
    ERROR   = "ERROR"   # unhandled processor exception during execution
    SKIPPED = "SKIPPED" # test case excluded from v1 scope (formula skip list)
```

### `SuiteDefinition`

Describes a registered conformance suite. Immutable dataclass. Defined in the runner's registry at startup.

| Field | Type | Description |
|-------|------|-------------|
| `suite_id` | `str` | Short identifier: `"xbrl21"`, `"dimensions"`, `"table-linkbase"`, `"formula"` |
| `label` | `str` | Human-readable name: `"XBRL 2.1 Conformance Suite"` |
| `blocking` | `bool` | `True` for CI-blocking suites; `False` for informational (Table Linkbase 1.0) |
| `informational_note` | `str \| None` | Shown in output when `blocking=False`; e.g. TL 1.0 PWD explanation |
| `index_filename` | `str` | Expected index filename in suite data directory |
| `subdirectory` | `str` | Subdirectory under `suite_data_dir/`: `"xbrl-2.1/"`, `"dimensions-1.0/"`, etc. |

**Registry** (module-level constant in `registry.py`):
```python
SUITE_REGISTRY: dict[str, SuiteDefinition] = {
    "xbrl21": SuiteDefinition(
        suite_id="xbrl21",
        label="XBRL 2.1 Conformance Suite",
        blocking=True,
        informational_note=None,
        index_filename="xbrl.org-index.xml",
        subdirectory="xbrl-2.1",
    ),
    "dimensions": SuiteDefinition(
        suite_id="dimensions",
        label="Dimensions 1.0 Conformance Suite",
        blocking=True,
        informational_note=None,
        index_filename="xdt.index.xml",
        subdirectory="dimensions-1.0",
    ),
    "table-linkbase": SuiteDefinition(
        suite_id="table-linkbase",
        label="Table Linkbase 1.0 Conformance Suite",
        blocking=False,
        informational_note=(
            "This suite is INFORMATIONAL in v1. The application implements "
            "Table Linkbase PWD; Table Linkbase 1.0 failures are expected and "
            "non-blocking. Full TL 1.0 support is planned for a future version."
        ),
        index_filename="tableLinkbase.index.xml",
        subdirectory="table-linkbase-1.0",
    ),
    "formula": SuiteDefinition(
        suite_id="formula",
        label="Formula 1.0 Conformance Suite",
        blocking=True,
        informational_note="v1 scope: value, existence, and consistency assertions only.",
        index_filename="formula.index.xml",
        subdirectory="formula-1.0",
    ),
}
```

---

## Test Case Domain Types

### `ExpectedOutcomeType` (enum)

```python
class ExpectedOutcomeType(str, Enum):
    VALID   = "valid"    # processor should accept without error
    ERROR   = "error"    # processor should produce this specific error code
    WARNING = "warning"  # processor should produce this specific warning code
```

### `ExpectedOutcome`

Parsed from `<result>` in test case XML.

| Field | Type | Description |
|-------|------|-------------|
| `outcome_type` | `ExpectedOutcomeType` | `VALID`, `ERROR`, or `WARNING` |
| `error_code` | `str \| None` | For `ERROR`/`WARNING`: the expected XBRL error code (e.g. `"xbrl.4.2.3"`) |

### `TestVariation`

A single variation within a test case. This is the atomic unit of execution.

| Field | Type | Description |
|-------|------|-------------|
| `variation_id` | `str` | Unique ID within the test case (e.g. `"V-001-V01"`) |
| `name` | `str` | Variation name |
| `description` | `str \| None` | Human-readable description |
| `input_files` | `tuple[Path, ...]` | Absolute paths to taxonomy schemas and/or instance files |
| `instance_file` | `Path \| None` | The primary XBRL instance file (if any) |
| `taxonomy_file` | `Path \| None` | The primary taxonomy entry-point schema (if any) |
| `expected_outcome` | `ExpectedOutcome` | What the processor should produce |
| `mandatory` | `bool` | True if the spec requires conforming implementations to pass this |

### `TestCase`

A group of related `TestVariation` objects, as declared in the conformance suite.

| Field | Type | Description |
|-------|------|-------------|
| `test_case_id` | `str` | E.g. `"V-001"` |
| `description` | `str` | Human-readable description of the test case |
| `source_file` | `Path` | Path to the test case XML file |
| `suite_id` | `str` | Which suite this belongs to |
| `variations` | `tuple[TestVariation, ...]` | All variations in this test case |

---

## Result Types

### `TestCaseResult`

Outcome of executing one `TestVariation`. Immutable dataclass.

| Field | Type | Description |
|-------|------|-------------|
| `variation_id` | `str` | From `TestVariation.variation_id` |
| `test_case_id` | `str` | From `TestCase.test_case_id` |
| `suite_id` | `str` | Which suite |
| `outcome` | `TestResultOutcome` | `PASS`, `FAIL`, `ERROR`, or `SKIPPED` |
| `mandatory` | `bool` | Copied from `TestVariation.mandatory` |
| `expected_outcome` | `ExpectedOutcome` | What was expected |
| `actual_error_codes` | `tuple[str, ...]` | Error codes produced by processor (empty if no errors) |
| `exception_message` | `str \| None` | For `ERROR` outcome: the exception type and message |
| `description` | `str` | Test case description (for reporting) |
| `input_files` | `tuple[Path, ...]` | Input files used (for reporting) |
| `duration_ms` | `int` | Wall-clock execution time in milliseconds |

### `SuiteResult`

Aggregated results for one conformance suite. Immutable dataclass.

| Field | Type | Description |
|-------|------|-------------|
| `suite_id` | `str` | Suite identifier |
| `label` | `str` | Suite display name |
| `blocking` | `bool` | Whether this suite's failures affect the exit code |
| `status` | `SuiteStatus` | Overall suite status |
| `results` | `tuple[TestCaseResult, ...]` | All results (including skipped) |
| `informational_note` | `str \| None` | From `SuiteDefinition` |

**Computed properties**:
- `total: int` → `len(results)`
- `passed: int` → count with `outcome == PASS`
- `failed: int` → count with `outcome == FAIL` and `mandatory == True`
- `failed_optional: int` → count with `outcome == FAIL` and `mandatory == False`
- `errored: int` → count with `outcome == ERROR`
- `skipped: int` → count with `outcome == SKIPPED`
- `failures: tuple[TestCaseResult, ...]` → all failing results (for display)

### `SuiteRunReport`

Complete output of a full runner invocation. Immutable dataclass.

| Field | Type | Description |
|-------|------|-------------|
| `run_timestamp` | `datetime` | UTC datetime of run start |
| `runner_version` | `str` | Version string from package metadata |
| `suite_results` | `tuple[SuiteResult, ...]` | Results for each suite that was run |
| `exit_code` | `int` | `0` if all blocking suites passed; `1` otherwise |

**Computed properties**:
- `overall_passed: bool` → `exit_code == 0`
- `blocking_failures: tuple[TestCaseResult, ...]` → all mandatory failures across blocking suites

---

## Service Classes

### `ConformanceSuiteParser`

Reads XBRL.org conformance suite XML index + test case files into typed domain objects.

```python
class ConformanceSuiteParser:
    def __init__(self, suite_data_dir: Path) -> None: ...

    def load_suite(self, suite_def: SuiteDefinition) -> list[TestCase]:
        """
        Parse all test cases from the suite's index file.
        If index file not found: raise SuiteDataMissingError.
        If a test case file is malformed: skip that test case and log a warning.
        All input file paths are resolved to absolute paths relative to
        the suite data directory.
        """

    def _parse_index(self, index_path: Path, suite_def: SuiteDefinition) -> list[Path]:
        """Parse the index file → list of test case file paths."""

    def _parse_test_case(self, tc_path: Path, suite_id: str) -> TestCase:
        """Parse a single test case XML file → TestCase with all variations."""
```

### `TestCaseExecutor`

Executes a single `TestVariation` against the processing engine and classifies the result.

```python
class TestCaseExecutor:
    def __init__(
        self,
        taxonomy_cache: TaxonomyCache,      # Feature 001 — reuse across test cases
        allow_network: bool = False,         # always False in conformance runs
        formula_skip_list: frozenset[str] = frozenset(),
    ) -> None: ...

    def execute(self, variation: TestVariation) -> TestCaseResult:
        """
        Execute the variation against the processing engine.
        Steps:
          1. If variation_id in formula_skip_list: return SKIPPED result immediately.
          2. Load taxonomy via TaxonomyLoader (uses cache if entry-point seen before).
          3. If variation has instance_file: parse with InstanceParser.
          4. If variation has instance_file: run InstanceValidator.validate_sync().
          5. Compare ValidationReport findings against variation.expected_outcome.
          6. Return TestCaseResult with PASS, FAIL, or ERROR.
        Catches all Exception subclasses: unhandled exceptions → ERROR outcome.
        Measures wall-clock duration.
        """

    def _match_outcome(
        self,
        expected: ExpectedOutcome,
        findings: tuple[ValidationFinding, ...],
        load_error: Exception | None,
    ) -> tuple[TestResultOutcome, tuple[str, ...]]:
        """
        Compare expected vs actual:
          - VALID + no error findings → PASS
          - VALID + error findings → FAIL (returns actual error codes)
          - ERROR(code) + finding with matching rule_id → PASS
          - ERROR(code) + no matching finding → FAIL
          - ERROR(code) + load_error matching code → PASS
          - Any unhandled exception → ERROR
        """
```

### `ConformanceRunner`

Top-level orchestrator. Coordinates parser → executor → aggregation → report.

```python
class ConformanceRunner:
    def __init__(
        self,
        suite_data_dir: Path,
        selected_suites: list[str] | None = None,  # None = all
        verbose: bool = False,
        stop_on_first_failure: bool = False,
    ) -> None: ...

    def run(self, progress_callback: Callable[[str, int, int], None] | None = None) -> SuiteRunReport:
        """
        Execute all selected suites. For each suite:
          1. Parse test cases via ConformanceSuiteParser.
          2. Execute each variation via TestCaseExecutor.
          3. Aggregate into SuiteResult.
        progress_callback(variation_id, current, total).
        Returns SuiteRunReport with computed exit_code.
        """

    def _compute_exit_code(self, suite_results: list[SuiteResult]) -> int:
        """0 if all blocking suites have status PASSED; 1 otherwise."""
```

---

## Output / Reporting

### `ConsoleReporter`

Renders a `SuiteRunReport` to stdout in formatted text. No PySide6 dependency.

```python
class ConsoleReporter:
    def __init__(self, verbose: bool = False, use_colour: bool | None = None) -> None:
        # use_colour: None = auto-detect (True if stdout is TTY)

    def print_report(self, report: SuiteRunReport) -> None:
        """Print full report to stdout. Formats per research.md Decision 6."""

    def print_progress(self, variation_id: str, current: int, total: int) -> None:
        """Print a single-line progress update (overwritten in-place if TTY)."""
```

### `JsonReporter`

Serialises a `SuiteRunReport` to JSON format.

```python
class JsonReporter:
    def to_dict(self, report: SuiteRunReport) -> dict:
        """Convert SuiteRunReport to JSON-serialisable dict (research.md Decision 6 schema)."""

    def write(self, report: SuiteRunReport, path: Path) -> None:
        """Write JSON to path. Raises PermissionError if not writable."""
```

---

## CLI Entry Point (`__main__.py`)

```python
def main() -> None:
    args = _parse_args()
    runner = ConformanceRunner(
        suite_data_dir=Path(args.suite_data_dir),
        selected_suites=_normalise_suite_arg(args.suite),
        verbose=args.verbose,
        stop_on_first_failure=args.stop_on_first_failure,
    )
    report = runner.run(progress_callback=ConsoleReporter().print_progress)
    ConsoleReporter(verbose=args.verbose).print_report(report)
    if args.output_file:
        if args.output_format == "json":
            JsonReporter().write(report, Path(args.output_file))
        else:
            # plain text: redirect ConsoleReporter output to file
            ...
    sys.exit(report.exit_code)
```

**`--suite` argument normalisation**:
- `"all"` (default) → all four suite IDs
- `"xbrl21"`, `"dimensions"`, `"table-linkbase"`, `"formula"` → single suite
- Unrecognised value → `argparse` error with valid options listed

---

## Error Types

| Error Class | Extends | When Raised |
|-------------|---------|-------------|
| `SuiteDataMissingError` | `Exception` | Suite index file not found at expected path |
| `TestCaseParseError` | `Exception` | Test case XML file is malformed (logged, test case skipped) |
| `ConformanceConfigError` | `Exception` | Invalid CLI arguments (unrecognised suite name) |

---

## Entity Relationships

```
SuiteDefinition [4 registered] ──defines──▶ suite configuration

ConformanceSuiteParser ──reads──▶ XBRL.org XML files ──produces──▶ TestCase [0..*]
                                                                      └── TestVariation [1..*]

TestCaseExecutor
  ├── uses ──▶ TaxonomyLoader (Feature 001)
  ├── uses ──▶ TaxonomyCache (Feature 001)
  ├── uses ──▶ InstanceParser (Feature 004)
  └── uses ──▶ InstanceValidator (Feature 005)
       └── executes ──▶ TestVariation ──produces──▶ TestCaseResult

ConformanceRunner
  ├── uses ──▶ ConformanceSuiteParser
  ├── uses ──▶ TestCaseExecutor
  └── produces ──▶ SuiteRunReport
                    └── SuiteResult [1..4]
                          └── TestCaseResult [0..*]

ConsoleReporter ──renders──▶ SuiteRunReport ──▶ stdout
JsonReporter    ──renders──▶ SuiteRunReport ──▶ file
__main__.py     ──orchestrates──▶ ConformanceRunner + reporters + sys.exit(exit_code)
```

---

## Formula Skip List

```python
# tests/conformance/formula_skip_list.py
# Formula 1.0 test case variation IDs that exercise features not in v1 scope.
# These are classified as SKIPPED (not FAILED) in v1 output.
FORMULA_SKIP_LIST: frozenset[str] = frozenset({
    # Custom functions (xfi: beyond v1 scope)
    # "formula-xxx-V01", ...
    # Tuple producers
    # "formula-yyy-V01", ...
    # Filter chaining beyond v1 supported subset
    # "formula-zzz-V01", ...
    # NOTE: Populate this list from the Formula 1.0 conformance suite index
    # during implementation by reviewing test case categories.
})
```

The skip list is maintained as a plain Python frozenset in the test data directory, versioned in the repository. It is the explicit contract between the runner and the implementation scope — each entry must be reviewed before release.

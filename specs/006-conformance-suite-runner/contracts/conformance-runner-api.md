# Contract: Conformance Suite Runner Public API

**Branch**: `006-conformance-suite-runner` | **Phase**: 1 | **Date**: 2026-03-26
**Module**: `bde_xbrl_editor.conformance`

**Depends on**:
- `bde_xbrl_editor.taxonomy` (Feature 001) — `TaxonomyLoader`, `TaxonomyCache`, `LoaderSettings`
- `bde_xbrl_editor.instance` (Feature 002/004) — `InstanceParser`
- `bde_xbrl_editor.validation` (Feature 005) — `InstanceValidator`, `ValidationFinding`, `ValidationReport`

---

## CLI Contract

The conformance runner is invoked as a Python module. It is the primary user-facing interface for this feature.

### Invocation

```bash
# Run all suites (default)
python -m bde_xbrl_editor.conformance

# Run single suite
python -m bde_xbrl_editor.conformance --suite dimensions

# Run with JSON output to file
python -m bde_xbrl_editor.conformance --output-format json --output-file report.json

# Verbose: show all test case results (not just failures)
python -m bde_xbrl_editor.conformance --verbose

# Use custom suite data directory
python -m bde_xbrl_editor.conformance --suite-data-dir /path/to/suite-data

# Stop on first failure (development mode)
python -m bde_xbrl_editor.conformance --stop-on-first-failure --suite formula

# Short alias (if installed as package)
conformance-runner --suite xbrl21
```

### CLI Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--suite` | `str` | `"all"` | Suite to run: `all`, `xbrl21`, `dimensions`, `table-linkbase`, `formula` |
| `--suite-data-dir` | `Path` | `./tests/conformance/suite-data` | Root directory containing suite subdirectories |
| `--output-format` | `str` | `"console"` | Output format: `console` or `json` |
| `--output-file` | `Path` | None | Write report to this file in addition to stdout |
| `--verbose` | flag | False | Show all test case results, not just failures |
| `--stop-on-first-failure` | flag | False | Abort run on first mandatory failure |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All mandatory test cases in all **CI-blocking** suites passed (XBRL 2.1, Dimensions 1.0, Formula 1.0). Table Linkbase 1.0 failures do not affect this code. |
| `1` | One or more mandatory test cases in a CI-blocking suite failed or errored. |
| `2` | Runner configuration error (unrecognised suite name, suite data directory not found). |

---

## Python API

The runner can also be used programmatically (e.g., from custom scripts or future GUI integration).

### `ConformanceRunner`

```python
from bde_xbrl_editor.conformance import ConformanceRunner, SuiteRunReport

runner = ConformanceRunner(
    suite_data_dir=Path("tests/conformance/suite-data"),
    selected_suites=["dimensions"],      # None = all four suites
    verbose=False,
    stop_on_first_failure=False,
)
report: SuiteRunReport = runner.run(
    progress_callback=lambda variation_id, current, total: print(f"{current}/{total}: {variation_id}")
)
print(f"Exit code: {report.exit_code}")
print(f"Overall passed: {report.overall_passed}")
for suite_result in report.suite_results:
    print(f"{suite_result.label}: {suite_result.passed}/{suite_result.total}")
```

**Guarantees**:
- `run()` never raises — all suite and test case errors are captured in results
- `report.exit_code` is `0` only if all blocking suites passed (Table Linkbase 1.0 never affects it)
- Suites whose data is missing are reported as `INCOMPLETE`, not `PASSED` or `FAILED`

---

### `SuiteRunReport`

```python
@dataclass(frozen=True)
class SuiteRunReport:
    run_timestamp: datetime
    runner_version: str
    suite_results: tuple[SuiteResult, ...]
    exit_code: int

    @property
    def overall_passed(self) -> bool: ...      # exit_code == 0

    @property
    def blocking_failures(self) -> tuple[TestCaseResult, ...]:
        """All mandatory failures across CI-blocking suites only."""
```

### `SuiteResult`

```python
@dataclass(frozen=True)
class SuiteResult:
    suite_id: str
    label: str
    blocking: bool
    status: SuiteStatus
    results: tuple[TestCaseResult, ...]
    informational_note: str | None

    @property
    def total(self) -> int: ...
    @property
    def passed(self) -> int: ...
    @property
    def failed(self) -> int: ...          # mandatory failures only
    @property
    def failed_optional(self) -> int: ...  # optional failures (reported, not blocking)
    @property
    def errored(self) -> int: ...
    @property
    def skipped(self) -> int: ...
    @property
    def failures(self) -> tuple[TestCaseResult, ...]: ...
```

### `TestCaseResult`

```python
@dataclass(frozen=True)
class TestCaseResult:
    variation_id: str
    test_case_id: str
    suite_id: str
    outcome: TestResultOutcome          # PASS | FAIL | ERROR | SKIPPED
    mandatory: bool
    expected_outcome: ExpectedOutcome
    actual_error_codes: tuple[str, ...]  # error codes from ValidationFindings
    exception_message: str | None        # populated only for ERROR outcome
    description: str
    input_files: tuple[Path, ...]
    duration_ms: int
```

---

## JSON Output Schema

When `--output-format json` is used, the output conforms to this schema:

```json
{
  "runner_version": "1.0.0",
  "run_timestamp": "2026-03-26T14:00:00Z",
  "overall_passed": true,
  "exit_code": 0,
  "suites": [
    {
      "suite_id": "xbrl21",
      "label": "XBRL 2.1 Conformance Suite",
      "blocking": true,
      "informational_note": null,
      "status": "PASSED",
      "total": 600,
      "passed": 600,
      "failed": 0,
      "failed_optional": 0,
      "errored": 0,
      "skipped": 0,
      "failures": [],
      "errors": []
    },
    {
      "suite_id": "table-linkbase",
      "label": "Table Linkbase 1.0 Conformance Suite",
      "blocking": false,
      "informational_note": "This suite is INFORMATIONAL in v1. The application implements Table Linkbase PWD; Table Linkbase 1.0 failures are expected and non-blocking. Full TL 1.0 support is planned for a future version.",
      "status": "FAILED",
      "total": 50,
      "passed": 12,
      "failed": 38,
      "failed_optional": 0,
      "errored": 0,
      "skipped": 0,
      "failures": [
        {
          "variation_id": "tl-001-V01",
          "test_case_id": "tl-001",
          "outcome": "FAIL",
          "mandatory": true,
          "expected": {"type": "valid"},
          "actual_error_codes": ["table-pwd.layout.01"],
          "exception_message": null,
          "description": "Basic table rendering with row breakdown",
          "input_files": ["table-linkbase-1.0/tl-001/instance.xml"],
          "duration_ms": 142
        }
      ]
    }
  ]
}
```

---

## CI Integration

### GitHub Actions Example

```yaml
- name: Run XBRL Conformance Suites
  run: |
    python -m bde_xbrl_editor.conformance \
      --suite-data-dir ./tests/conformance/suite-data \
      --output-format json \
      --output-file conformance-report.json
  # Exit code 1 on mandatory failure → step fails → build fails

- name: Upload Conformance Report
  uses: actions/upload-artifact@v4
  if: always()    # upload even on failure, for debugging
  with:
    name: conformance-report
    path: conformance-report.json
```

### pytest Integration (optional)

The runner does NOT use pytest for execution. However, a single pytest wrapper test can be added to run the full suite as part of `pytest` test discovery:

```python
# tests/integration/test_conformance_suites.py
def test_xbrl21_conformance():
    runner = ConformanceRunner(
        suite_data_dir=Path("tests/conformance/suite-data"),
        selected_suites=["xbrl21"],
    )
    report = runner.run()
    failures = [r for r in report.suite_results[0].results
                if r.outcome == TestResultOutcome.FAIL and r.mandatory]
    assert not failures, f"{len(failures)} mandatory test cases failed"
```

This enables `pytest` to surface individual conformance failures in standard test reports.

---

## Error Hierarchy

```python
class ConformanceError(Exception): ...                 # base
class SuiteDataMissingError(ConformanceError): ...     # index file not found
class TestCaseParseError(ConformanceError): ...        # malformed test case XML
class ConformanceConfigError(ConformanceError): ...    # invalid CLI arguments
```

**Handling in `ConformanceRunner.run()`**:
- `SuiteDataMissingError` → suite classified as `INCOMPLETE`; other suites continue
- `TestCaseParseError` → that test case classified as `ERROR`; rest of suite continues
- `ConformanceConfigError` → propagated to `__main__.py`; printed to stderr; exit code 2

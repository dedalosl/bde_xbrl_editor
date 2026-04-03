# Feature Specification: Conformance Suite Runner

**Feature Branch**: `006-conformance-suite-runner`
**Created**: 2026-03-25
**Status**: Draft
**Input**: User description: "Conformance suite execution — a built-in test runner that executes the XBRL.org conformance suites (XBRL 2.1, Dimensions 1.0, Table Linkbase 1.0, Formula 1.0) and reports pass/fail results per test case, integrated into CI as a build-blocking check. Note: there is no conformance suite for the Table Linkbase PWD; only Table Linkbase 1.0 has a published conformance suite. The runner will execute the Table Linkbase 1.0 suite for tracking purposes, but the application implements PWD in v1 — Table Linkbase 1.0 failures are expected in v1 and must be non-blocking in CI."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run All Conformance Suites and See a Pass/Fail Summary (Priority: P1)

A developer or QA engineer wants to verify that the processor correctly implements the targeted XBRL specifications. They trigger a conformance suite run from the command line. The application loads all four targeted conformance suites — XBRL 2.1, Dimensions 1.0, Table Linkbase 1.0, and Formula 1.0 — executes every mandatory test case, and presents a consolidated pass/fail summary grouped by specification. Table Linkbase 1.0 results are presented separately with a clear indication that v1 failures are expected (since the application implements PWD, not 1.0).

**Why this priority**: This is the primary mechanism for verifying standards compliance. The PRD requires 100% pass rates across all mandatory test cases as a v1 launch criterion. Without this runner, there is no objective way to measure or demonstrate conformance — it is also what CI uses to gate builds.

**Independent Test**: Can be fully tested by running the suite runner against the official XBRL.org conformance suite test data and confirming that the summary report identifies the correct number of test cases per specification, reports each as pass, fail, or error, and reaches 100% pass on mandatory cases.

**Acceptance Scenarios**:

1. **Given** the conformance suite test data is available locally, **When** the user triggers a full suite run, **Then** the runner executes all mandatory test cases across all four targeted specifications and presents a summary table showing total/passed/failed/errored counts per specification.
2. **Given** a suite run is completed with all tests passing for the three CI-blocking suites (XBRL 2.1, Dimensions 1.0, Formula 1.0), **When** the user views the summary, **Then** a clear "all blocking suites passed" indicator is shown and the exit status is success (0), regardless of Table Linkbase 1.0 results.
3. **Given** a suite run is completed and one or more tests fail in a CI-blocking suite, **When** the user views the summary, **Then** the failing tests are listed by specification, test case ID, and the error or discrepancy encountered; the exit status is failure (non-zero).
4. **Given** the Table Linkbase 1.0 suite is executed, **When** the user views the summary, **Then** its results are presented in a dedicated section clearly labelled as "informational — v1 application implements Table Linkbase PWD, not 1.0"; failures in this section do not affect the overall pass/fail status or the exit code.
5. **Given** the conformance suite test data for a specification is missing or inaccessible, **When** the runner is invoked, **Then** the runner reports which suite data could not be loaded and clearly marks that specification's results as incomplete rather than passing silently.

---

### User Story 2 - Run a Single Specification's Suite in Isolation (Priority: P2)

During development, an engineer working on a specific processing area (e.g., the dimensions engine) wants to run only the Dimensions 1.0 conformance suite — without waiting for the full multi-suite run. They specify a single target suite and get results scoped to that specification.

**Why this priority**: Full suite runs can be slow when all four specifications are executed. Developers need fast feedback while iterating on a specific implementation area. Being able to target a single suite accelerates the fix-verify cycle without sacrificing the completeness of the full run.

**Independent Test**: Can be fully tested by invoking the runner with a single suite argument, confirming that only test cases from that specification are executed, and that results are reported in the same format as a full run but scoped to the selected suite.

**Acceptance Scenarios**:

1. **Given** the user invokes the runner specifying a single target specification (e.g., `--suite dimensions`), **When** the run completes, **Then** only test cases belonging to that specification are executed and reported; other specifications are not mentioned in the output.
2. **Given** a single-suite run completes with failures, **When** the user views the results, **Then** each failing test case is shown with its test case ID, the expected result, the actual result produced by the processor, and the relevant input files.
3. **Given** the user specifies an unrecognised suite name, **When** the runner is invoked, **Then** an error is shown listing the valid suite names, and no test cases are executed.

---

### User Story 3 - Inspect Individual Test Case Results (Priority: P3)

After a suite run, the user wants to investigate a specific failing test case. They can drill into a single test case result to see: the test's description, the input instance and taxonomy files used, the expected outcome declared in the suite, and the actual output produced by the processor.

**Why this priority**: A pass/fail count alone is insufficient for debugging. When a test fails, the developer needs the full context — what input triggered the failure, what was expected, and what the processor actually produced — to diagnose and fix the underlying conformance gap.

**Independent Test**: Can be fully tested by running a suite, navigating to a failing test case's detailed view, and confirming that it shows the test description, input file paths, expected result, and the processor's actual result — independently of any fix or re-run.

**Acceptance Scenarios**:

1. **Given** a suite run has produced results, **When** the user selects a specific test case ID, **Then** the runner displays the full test case details: its description, the input files (instance and taxonomy paths), the expected outcome (pass/fail/specific error code), and the processor's actual outcome.
2. **Given** a failing test case's details are shown, **When** the expected outcome is a specific error code or warning message, **Then** the display includes both the expected code and the actual code or message produced, making the discrepancy immediately visible.
3. **Given** a passing test case's details are shown, **When** the user inspects it, **Then** the display confirms the expected outcome matched, along with any relevant output produced by the processor during that test.

---

### User Story 4 - Track Table Linkbase 1.0 Conformance Progress Without Blocking Builds (Priority: P4)

An engineer wants to see how far the current implementation is from full Table Linkbase 1.0 conformance — even though v1 of the application only implements the PWD version. They can run the Table Linkbase 1.0 suite, see which test cases pass and which fail, and use this as a roadmap for future v2 work.

**Why this priority**: No published conformance suite exists for Table Linkbase PWD; only Table Linkbase 1.0 has an official XBRL.org conformance suite. Running the 1.0 suite in v1 provides a baseline for measuring progress toward future 1.0 support, while keeping the results informational so they do not block current development. This separates "conformance verification" (blocking) from "conformance tracking" (informational).

**Independent Test**: Can be fully tested by running the Table Linkbase 1.0 suite in isolation, confirming its results are presented as informational, the exit code remains 0 even with failures, and the output clearly labels these results as non-blocking — independently of any other suite or CI pipeline configuration.

**Acceptance Scenarios**:

1. **Given** the Table Linkbase 1.0 suite is available locally, **When** the user runs it in isolation, **Then** the runner executes all its test cases and produces a full result report showing which pass and which fail.
2. **Given** Table Linkbase 1.0 tests fail (which is expected in v1), **When** the user views the results, **Then** the output includes a prominent notice explaining that the application implements Table Linkbase PWD in v1, and that these failures represent planned future work rather than regressions.
3. **Given** Table Linkbase 1.0 results are included in a full suite run, **When** a CI pipeline invokes the runner, **Then** the Table Linkbase 1.0 failure count is reported in the output but the exit code is determined solely by the three CI-blocking suites (XBRL 2.1, Dimensions 1.0, Formula 1.0).

---

### User Story 5 - Use the Suite Runner in CI as a Build Gate (Priority: P5)

A CI pipeline runs the full conformance suite after every build. If any mandatory test case fails, the build is marked as failed and the offending test case IDs are reported in the CI output. The pipeline passes only when all mandatory cases across all suites pass.

**Why this priority**: The PRD mandates that conformance regression is a build-blocking failure for the specifications the application implements. CI integration ensures that no code change can inadvertently break a previously passing conformance test without immediate visibility. This is what makes the 100% pass rate maintainable over time for the three CI-blocking suites.

**Independent Test**: Can be fully tested by running the suite runner in a CI context (or simulating it), verifying the exit code is non-zero on any failure, and confirming the machine-readable output format is parseable by standard CI tooling — independently of the UI or interactive result inspection.

**Acceptance Scenarios**:

1. **Given** the suite runner is invoked as part of a CI pipeline, **When** all mandatory test cases pass, **Then** the runner exits with code 0 and emits a machine-readable summary listing pass counts per specification.
2. **Given** a code change causes a previously passing mandatory test case to fail, **When** the CI pipeline runs the suite, **Then** the runner exits with a non-zero code, the specific failing test case ID(s) and specification(s) are included in the output, and the CI build is marked as failed.
3. **Given** the runner is invoked in CI, **When** it runs, **Then** no interactive prompts or GUI elements are required; the runner is fully non-interactive and headless.

---

### Edge Cases

- What happens when a conformance suite contains test cases marked as optional vs. mandatory — are optional failures counted against the build gate?
- What happens when a test case's input files reference remote URIs (e.g., `xbrl.org` schema locations) in an offline CI environment?
- What happens when the conformance suite data itself is malformed or incomplete (e.g., a test case references a non-existent input file)?
- How does the runner handle a test case that causes the processor to throw an unhandled exception — is it marked as errored rather than failed?
- What happens when a new version of a conformance suite is released with additional test cases — how does the runner's baseline update?
- How does the runner report test cases that are in a "not implemented" state (expected to fail until a specific feature is built)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST include a conformance suite runner that can be invoked from the command line without launching the full application UI.
- **FR-002**: The runner MUST support all four targeted XBRL.org conformance suites: XBRL 2.1, Dimensions 1.0 (xDT), Table Linkbase 1.0, and Formula 1.0. Note: no published conformance suite exists for Table Linkbase PWD; the Table Linkbase 1.0 suite is included for tracking purposes only.
- **FR-002a**: The runner MUST classify the Table Linkbase 1.0 suite as informational in v1 — its test case failures MUST be reported but MUST NOT affect the overall exit code or the CI build gate. The suite's results MUST be clearly labelled as non-blocking in the output, with an explanation that the application implements Table Linkbase PWD in v1.
- **FR-003**: The runner MUST execute all mandatory test cases within each targeted suite and classify each result as: pass, fail, or error (processor exception).
- **FR-004**: The runner MUST allow the user to target a single specification's suite by name, executing only that suite's test cases in isolation.
- **FR-005**: For each failing or errored test case, the runner MUST report: the test case identifier, the specification it belongs to, a description of the test, the expected outcome, and the actual outcome produced by the processor.
- **FR-006**: The runner MUST produce a summary report grouped by specification showing total, passed, failed, and errored counts per suite.
- **FR-007**: The runner MUST exit with a zero exit code if and only if all mandatory test cases across the three CI-blocking suites (XBRL 2.1, Dimensions 1.0, Formula 1.0) pass; any failure or error in a mandatory test case from these suites MUST produce a non-zero exit code. Table Linkbase 1.0 failures MUST NOT affect the exit code in v1.
- **FR-008**: The runner MUST be fully non-interactive and headless — it must not require a GUI or prompt the user for input during a run.
- **FR-009**: The runner MUST distinguish between mandatory and optional test cases; optional failures MUST be reported but MUST NOT affect the exit code or the pass/fail determination.
- **FR-010**: When conformance suite test data is not found at the expected location, the runner MUST report which suite data is missing and mark that suite as incomplete, rather than treating the missing data as a pass.
- **FR-011**: The runner MUST resolve test case input file references using local filesystem paths only, with no external network calls, to support offline and air-gapped CI environments.
- **FR-012**: Unhandled processor exceptions during a test case MUST be caught, classified as an error result for that test case, and must not abort the remainder of the suite run.

### Key Entities

- **Conformance Suite**: A published collection of test cases from XBRL.org for a specific specification (e.g., XBRL 2.1 Conformance Suite), consisting of input files (taxonomies and instances) and expected outcomes. They follow the specification on this file https://www.xbrl.org/2008/xbrl-conf-cr4-2008-07-02.htm
- **Test Case**: A single self-contained test within a conformance suite, with a unique identifier, a description, one or more input files, and a declared expected outcome (pass, specific error code, or specific warning).
- **Test Result**: The outcome of executing a single test case against the processor — classified as pass, fail, or error — together with the actual output or exception produced.
- **Suite Run**: A single invocation of the runner that executes one or more conformance suites and collects all test results into a Suite Run Report.
- **Suite Run Report**: The complete output of a suite run — a structured listing of all test results grouped by specification, with per-suite counts and an overall pass/fail determination.
- **Mandatory Test Case**: A test case within a conformance suite that the specification requires all conforming implementations to pass; failing a mandatory case means the processor is non-conforming.
- **Optional Test Case**: A test case that the specification does not require all implementations to pass; failures are reported informatively but do not affect conformance status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At v1 release, the processor achieves a 100% pass rate on all mandatory test cases across the three CI-blocking suites (XBRL 2.1, Dimensions 1.0, Formula 1.0) when run against the official XBRL.org test data. Table Linkbase 1.0 results are tracked and reported but not held to a pass-rate target in v1.
- **SC-002**: The full four-suite conformance run completes in under 10 minutes on reference hardware, making it suitable as a standard CI pipeline step without significantly blocking build throughput.
- **SC-003**: Every failing or errored test case is accompanied by enough diagnostic information that a developer can reproduce the failure and identify its root cause without consulting any source outside the runner output — measured by successful reproduction in 100% of cases during internal testing.
- **SC-004**: The runner is integrated into the CI pipeline and successfully gates builds — 0% of builds with a mandatory conformance regression reach a passing CI status.
- **SC-005**: Optional test case failures are reported but do not block CI — the pipeline correctly distinguishes mandatory from optional failures in 100% of runs.

## Assumptions

- The XBRL.org conformance suite test data is sourced and stored locally within the repository or a designated test data directory; the runner does not download suites on-the-fly.
- The test data must be available by end of Week 2 of the project timeline (as stated in the PRD dependencies).
- There is no published XBRL.org conformance suite for the Table Linkbase PWD specification. The only available conformance suite for table linkbase processing is the Table Linkbase 1.0 suite. The runner includes it as an informational, non-blocking suite in v1.
- Since the application implements Table Linkbase PWD in v1 (matching the version used by BDE), Table Linkbase 1.0 conformance test failures are expected and accepted in v1. Full Table Linkbase 1.0 support, and a corresponding 100% pass target on that suite, is planned for a future version.
- Formula 1.0 conformance suite coverage in v1 is scoped to value assertions, existence assertions, and consistency assertions — full formula specification coverage (custom functions, filter chaining) is deferred to v2 (as stated in PRD).
- The runner is a command-line tool that reuses the same processing engine as the UI application; it is not a separate implementation.

## Out of Scope

- Downloading or auto-updating conformance suite test data from xbrl.org at runtime.
- Authoring or editing test cases; the runner only executes existing XBRL.org-published test cases.
- A graphical UI for browsing conformance results (CLI output and a human-readable report file are sufficient for v1).
- Coverage of XBRL specifications outside the four targeted suites (e.g., Inline XBRL, XBRL OIM, xBRL-JSON).
- Differential suite runs (only running test cases affected by a specific code change).
- Full Formula 1.0 conformance suite coverage including custom functions and filter chaining — deferred to v2.
- Promoting Table Linkbase 1.0 suite to CI-blocking status — this will happen when the application adds full Table Linkbase 1.0 support in a future version.

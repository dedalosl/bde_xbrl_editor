# Feature Specification: Instance Validation

**Feature Branch**: `005-instance-validation`
**Created**: 2026-03-24
**Status**: Draft
**Input**: User description: "Instance validation — the user must be able to validate the XBRL instance he has already created or edited. Using the formula linkbase, and if available the additional validations rules published by the BDE in PDF format outside of the taxonomy, these last functionality could be left outside of v1 and could be implemented on the future"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run Full Validation on an Open Instance (Priority: P1)

A reporting user has finished creating or editing an XBRL instance and wants to check it for errors before submission to BDE. They trigger a validation run on the open instance. The application validates the instance against the taxonomy — checking XBRL structural conformance and executing the formula assertions defined in the taxonomy's formula linkbase — and presents a consolidated report of all findings.

**Why this priority**: Validation is the quality gate between editing and submission. Without it, users have no way to know whether their instance will be accepted by BDE. XBRL formula linkbase validation covers the calculation rules, consistency checks, and business rules that BDE taxonomies encode — this is the primary, mandatory validation layer in v1.

**Independent Test**: Can be fully tested by running validation on a known instance against a BDE taxonomy with formula linkbase assertions, and confirming that the result report correctly identifies all expected assertion failures (pre-established from the taxonomy's own test suite) and produces no false positives.

**Acceptance Scenarios**:

1. **Given** an XBRL instance is open, **When** the user triggers validation, **Then** the application runs all applicable checks (structural conformance + formula assertions from the taxonomy) and displays a validation result report.
2. **Given** validation has run and found no issues, **When** the user views the result, **Then** the report clearly states that the instance passed all checks, and a pass indicator is prominently shown.
3. **Given** validation has run and found failures, **When** the user views the result, **Then** each failure is listed with: the assertion or rule that failed, a human-readable message describing the problem, and the severity (error vs. warning).
4. **Given** validation produces errors, **When** the user selects an error in the results list, **Then** the application navigates to the table and cell related to that error (where a cell mapping exists), so the user can immediately see the problematic data in context.
5. **Given** the taxonomy has no formula linkbase, **When** the user triggers validation, **Then** the application performs structural conformance checks only and clearly informs the user that no formula assertions are available for this taxonomy.

---

### User Story 2 - View Validation Results Filtered by Severity and Table (Priority: P2)

After a validation run, the user can filter and navigate the results by severity (errors, warnings) and by report table, so they can prioritise and address issues systematically — especially when a large number of validation findings are returned.

**Why this priority**: BDE taxonomy formula linkbases can contain hundreds of assertions. A flat, unfiltered list of results is difficult to work with. Filtering by severity (errors block submission; warnings are informational) and by table lets users work through issues in a structured, efficient manner.

**Independent Test**: Can be fully tested by running validation on an instance that produces a mix of errors and warnings across multiple tables, then applying each filter in turn and confirming that the results list contains only the items matching the active filter — independently of any navigation or edit functionality.

**Acceptance Scenarios**:

1. **Given** a validation result report is displayed, **When** the user filters by severity "Error", **Then** only findings classified as errors are shown; warnings are hidden.
2. **Given** a validation result report is displayed, **When** the user filters by a specific report table, **Then** only findings associated with concepts or assertions in that table are shown.
3. **Given** the user has applied multiple filters, **When** they clear all filters, **Then** the complete, unfiltered result list is restored.
4. **Given** a validation result report is displayed, **When** no filters are applied, **Then** the total count of errors and warnings is shown as a summary at the top of the report.

---

### User Story 3 - Re-Validate After Editing to Confirm Fixes (Priority: P3)

After addressing validation errors by editing the instance, the user can re-run validation without closing the results panel. The new results replace the previous ones, so the user can immediately see whether their edits resolved the failing assertions.

**Why this priority**: The typical workflow is an edit-validate-fix loop. Supporting re-validation from within the same session, without requiring the user to navigate back and forth, reduces friction and makes the correction cycle faster.

**Independent Test**: Can be fully tested by running validation, observing a failure, editing the relevant cell to fix the issue, re-running validation, and confirming that the previously failing assertion no longer appears in the new result — independently of any filtering or navigation feature.

**Acceptance Scenarios**:

1. **Given** a validation result report is displayed, **When** the user edits a fact in the instance and then triggers re-validation, **Then** the validation result is refreshed to reflect the current state of the instance, and any previously failing assertions that are now satisfied are removed from the list.
2. **Given** re-validation is triggered, **When** new failures are introduced by the edits, **Then** those new failures appear in the refreshed results list even if they were not present in the previous run.
3. **Given** re-validation is running, **When** the process is in progress, **Then** the previous results remain visible and a progress indicator is shown; the results are only replaced when the new run is complete.

---

### User Story 4 - Export the Validation Report (Priority: P4)

The user can export the validation result report to a file (plain text or structured format), so they can share it with colleagues, archive it alongside the instance, or attach it to a submission record.

**Why this priority**: Regulatory reporting workflows often require documenting that a validation was performed and what its outcome was. Being able to export the report serves audit and traceability needs without requiring the recipient to have the application installed.

**Independent Test**: Can be fully tested by running validation, then exporting the report, opening the exported file in a standard text viewer, and confirming that it contains all findings (each with rule name, message, and severity) in a human-readable format — independently of any filtering or navigation.

**Acceptance Scenarios**:

1. **Given** a validation result report is displayed, **When** the user exports it, **Then** a file is written to a user-specified location containing all findings, each with its rule identifier, severity, human-readable message, and the associated table/concept where applicable.
2. **Given** validation produced no findings, **When** the user exports the report, **Then** the exported file states that the instance passed all checks, along with the instance filename, taxonomy version, and the date and time of the validation run.
3. **Given** the user attempts to export to a path where they lack write permissions, **When** the export is attempted, **Then** the application shows a clear error and leaves the in-memory result intact.

---

### Edge Cases

- What happens when the formula linkbase references external concept definitions or assertion sets that are not available locally?
- What happens when validation of a large instance with hundreds of formula assertions takes more than a minute — does the user receive progress feedback?
- What happens when a formula assertion produces an indeterminate result (e.g., due to missing required input facts) — is this treated as a failure or as a warning?
- What happens when the same assertion fires multiple times for different contexts (e.g., once per row in a table) — are all occurrences reported individually or aggregated?
- What happens when the formula linkbase contains assertions referencing concepts that are not present in the current instance — are they reported as inapplicable or as failures?
- What happens when the user triggers validation while an edit is in progress (cell in edit mode)?
- What happens when the instance has been modified since the last save — is validation run against the in-memory (unsaved) state or the last saved state?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow the user to trigger validation of the currently open XBRL instance at any time while the instance is loaded.
- **FR-002**: The system MUST validate the instance against the full set of XBRL formula assertions defined in the bound taxonomy's formula linkbase, applying each assertion to the instance facts.
- **FR-003**: The system MUST validate the instance for XBRL structural conformance (well-formed XML, valid namespace declarations, correct schemaRef, valid context and unit references) in addition to formula assertion evaluation.
- **FR-004**: Validation MUST run against the current in-memory state of the instance (including any unsaved edits), not only the last saved file state.
- **FR-005**: The system MUST present a validation result report listing each finding with: the assertion or rule identifier, severity (error or warning), a human-readable description of the failure, and the related table and concept identifier where a mapping exists.
- **FR-006**: The system MUST clearly distinguish between errors (which indicate the instance is not valid for submission) and warnings (which are informational and do not block submission).
- **FR-007**: When the user selects a finding in the results report, the system MUST navigate to the table and cell associated with that finding, where a cell mapping can be established from the assertion's context and concept.
- **FR-008**: The system MUST allow the user to filter the results by severity (all, errors only, warnings only) and by report table.
- **FR-009**: The system MUST allow the user to re-run validation at any time after an initial run; re-running replaces the previous result report with a new one.
- **FR-010**: The system MUST display a progress indicator during validation runs that take more than a few seconds, showing that validation is in progress.
- **FR-011**: The system MUST allow the user to export the validation result report to a file on the local filesystem in a human-readable format.
- **FR-012**: When the bound taxonomy has no formula linkbase, the system MUST still perform structural conformance checks, clearly inform the user that formula assertions are unavailable for this taxonomy, and not treat the absence of a formula linkbase as a validation failure.
- **FR-013**: The system MUST validate that each fact in the instance has a dimensional context that satisfies the applicable hypercube constraints (closed hypercubes) defined in the taxonomy's definition linkbase. Violations MUST be reported as findings that include: the failing fact, the name of the violated hypercube, and the specific dimensional constraint that was breached.

### Key Entities

- **Validation Run**: A single execution of all applicable validation checks against the current in-memory instance state; produces one Validation Result Report.
- **Validation Result Report**: The complete output of a validation run — a collection of findings, each classified by severity, associated with a specific rule, and optionally linked to a table and concept in the instance.
- **Validation Finding**: A single identified issue or informational note from a validation run, containing: rule identifier, severity (error/warning), human-readable message, and optionally the XBRL context and concept reference that triggered it.
- **Formula Assertion**: A business rule encoded in the taxonomy's formula linkbase that evaluates a condition over the instance's facts; when the condition is not satisfied, a finding is produced.
- **Structural Conformance Check**: A set of baseline XBRL 2.1 standard checks (well-formed XML, valid references, correct namespace usage) applied independently of the formula linkbase.
- **Validation Severity**: The classification of a finding as either an Error (the instance is invalid; submission is blocked) or a Warning (a potential issue; submission is not necessarily blocked).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Validation of a typical BDE instance (up to 10,000 facts, 200+ formula assertions) completes and presents results to the user in under 60 seconds.
- **SC-002**: 100% of formula assertions defined in the taxonomy's formula linkbase are evaluated during a validation run — no assertions are silently skipped.
- **SC-003**: Every finding in the results report is correctly classified as either an error or a warning — 0% misclassification rate compared to the taxonomy's declared assertion severity.
- **SC-004**: For 100% of findings that can be mapped to a table cell (concept + context matches a grid coordinate), the "navigate to cell" action takes the user to the correct cell in the rendered table.
- **SC-005**: Users can locate all errors and begin correcting them within 5 minutes of a validation run completing on an instance with up to 50 findings — measured by task completion time in usability testing.
- **SC-006**: The exported validation report is complete and human-readable — 100% of findings visible in the UI appear in the exported file with no truncation or omission.

## Assumptions

- The bound taxonomy's formula linkbase is the primary source of business rule validation in v1; BDE-specific validation rules published outside the taxonomy (in PDF documents) are explicitly out of scope for v1 and will be addressed in a future version.
- An XBRL instance is already open in the application (dependency on Features 002 or 004); validation operates on the in-memory instance state.
- The taxonomy is already loaded (dependency on Feature 001); formula assertions are parsed from the taxonomy's formula linkbase as part of taxonomy loading.
- XBRL formula linkbase support covers the XBRL Formula specification; XPath 2.0 expressions within formulas are evaluated using the taxonomy-declared namespaces.
- When a formula assertion fires multiple times (once per matching context), each occurrence is reported as a separate finding in the results list.
- Validation severity (error vs. warning) follows the severity declared in the formula linkbase for each assertion; if no severity is declared, the finding is classified as an error by default.
- Validation does not block the user from saving the instance; a user may save an invalid instance and must be informed that it has unresolved validation errors.

## Out of Scope (v1)

- Validation against BDE-specific business rules published outside the taxonomy in PDF or other non-machine-readable formats — planned for a future version.
- Automatic fixing or suggestion of corrective values for failing assertions.
- Submission of the validated instance to BDE (a separate submission feature).
- Validation of inline XBRL (iXBRL) instances.
- Batch validation of multiple instances in a single run.
- Differential validation (only re-running assertions affected by recent edits, rather than full re-validation).

## Future Considerations

- **BDE Out-of-Taxonomy Validation Rules (v2+)**: BDE publishes additional validation rules in PDF documents that are not encoded in the taxonomy's formula linkbase. A future version will parse and apply these rules as an additional validation layer, supplementing the formula linkbase checks already in scope for v1.

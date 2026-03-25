# Feature Specification: XBRL Instance Creation

**Feature Branch**: `002-xbrl-instance-creation`
**Created**: 2026-03-24
**Status**: Draft
**Input**: User description: "Instance creation — creating a new XBRL instance from a BDE taxonomy that we have already loaded and parsed."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create a New Empty XBRL Instance from a Loaded BDE Taxonomy (Priority: P1)

A reporting user has a BDE taxonomy already loaded and wants to start a new reporting period submission. They initiate the creation of a new XBRL instance, providing the required instance-level context (reporting period, reporting entity). The application generates a structurally valid, empty XBRL instance bound to that taxonomy — ready to be populated with data.

**Why this priority**: This is the entry point for all new reporting work. Without the ability to create a valid empty instance shell, users cannot begin filling in any report data. Every other instance-related feature (editing, validation, rendering) depends on this.

**Independent Test**: Can be fully tested by creating a new instance and verifying that the resulting document is a well-formed XBRL instance that references the correct taxonomy, contains the declared reporting entity and period, and passes basic XBRL structural validation — independently of any data entry or UI rendering work.

**Acceptance Scenarios**:

1. **Given** a BDE taxonomy is loaded, **When** the user initiates new instance creation and provides the reporting entity identifier and reporting period, **Then** the application produces a valid, empty XBRL instance document referencing the correct taxonomy entry point.
2. **Given** a new instance has been created, **When** the user inspects its metadata, **Then** the application shows the bound taxonomy, the reporting entity, and the reporting period correctly.
3. **Given** the user provides an invalid reporting period (e.g., end date before start date, or a period type incompatible with the taxonomy's declared period type), **When** the user attempts to create the instance, **Then** the application rejects the creation with a clear error message explaining the conflict.
4. **Given** a BDE taxonomy is loaded, **When** the user creates a new instance, **Then** the instance's namespace declarations and schemaRef are automatically populated from the taxonomy metadata — the user does not need to configure these manually.

---

### User Story 2 - Select Which Reports (Tables) to Include in the Instance (Priority: P2)

After initiating a new instance, the user selects which report tables from the taxonomy they want to include in this submission. Not all submissions require all tables — the user can choose a subset, and the instance is scoped accordingly.

**Why this priority**: BDE submissions often consist of multiple tables (reports), but reporting entities may only be obligated to submit a subset depending on their type or activity. Allowing the user to declare which tables are in scope prevents accidental inclusion of irrelevant tables and reduces the validation surface.

**Independent Test**: Can be fully tested by creating an instance, selecting a specific subset of tables, and confirming that only those tables appear as expected reporting units in the instance — with no data yet, but with the correct structural placeholders.

**Acceptance Scenarios**:

1. **Given** a new instance has been created, **When** the user views the available report tables from the loaded taxonomy, **Then** all tables from the taxonomy are listed with their identifiers and labels, and filingIndicators and all are initially unselected.
2. **Given** the user selects a subset of tables, **When** the selection is confirmed, **Then** the instance structure is updated to include exactly those tables as reporting units, with no others.
3. **Given** at least one table has been selected, **When** the user later removes a table from the selection, **Then** that table and any data already entered for it are removed from the instance, and the user is warned about the data loss before it occurs.
4. **Given** the user attempts to confirm with zero tables selected, **When** the selection is submitted, **Then** the application informs the user that at least one table must be selected.

---

### User Story 3 - Set the Dimensional Context (Hypercube Filters) for Each Selected Table (Priority: P3)

For each selected report table, the user declares the fixed dimensional values that apply to the entire table in this submission (e.g., the reporting entity, currency, consolidation scope). These are the "filter" axis values that set the context for all facts within the table.

**Why this priority**: BDE taxonomy tables use XBRL dimensions extensively. The filter (Z-axis) values define the XBRL contexts that apply to every cell in a table. Without these, no facts can be correctly contextualised and the instance cannot be validly populated.

**Independent Test**: Can be fully tested by selecting a table, setting its filter-axis dimension values, and verifying that the resulting instance contains the correct XBRL context definitions matching those values — independently of entering any numeric or text facts.

**Acceptance Scenarios**:

1. **Given** a table has been added to the instance, **When** the user views its dimensional configuration, **Then** the application lists all filter-axis (Z-axis) dimensions for that table with their allowed values as defined in the taxonomy.
2. **Given** the user selects valid dimension members for all required filter-axis dimensions of a table, **When** the configuration is confirmed, **Then** the instance's XBRL contexts are generated correctly, reflecting those selections.
3. **Given** a required filter-axis dimension has no value selected, **When** the user attempts to proceed past the dimensional configuration, **Then** the application blocks progression and highlights the missing dimension.
4. **Given** a dimension's allowed values are defined in the taxonomy as a closed enumeration (typed or explicit members), **When** the user selects a value, **Then** only taxonomy-declared members are offered — free-text input is not allowed for enumerated dimensions.

---

### User Story 4 - Save the New Instance to the Filesystem (Priority: P4)

After configuring the instance structure (entity, period, tables, dimensional contexts), the user saves the new instance as an XBRL file to a chosen location on their local filesystem, so it can be reopened, edited, or submitted later.

**Why this priority**: Persistence of the created instance is necessary for any real-world workflow. Without saving, all work done in session is lost. This is lower priority than creation and configuration because saving can initially target a fixed default location, but the user must be able to control where the file is saved.

**Independent Test**: Can be fully tested by creating and configuring an instance, saving it to a specified path, then reopening the saved file independently and confirming the structure matches what was configured.

**Acceptance Scenarios**:

1. **Given** a new instance has been created and configured, **When** the user chooses to save it and specifies a filesystem path, **Then** a well-formed XBRL instance document is written to that path.
2. **Given** the user attempts to save to a path where they lack write permissions, **When** the save is attempted, **Then** the application informs the user of the permission error and leaves the in-memory instance intact.
3. **Given** an instance has been saved, **When** the user reopens that file, **Then** the reopened instance contains exactly the same entity, period, tables, and dimensional context as when it was saved.

---

### Edge Cases

- What happens when the loaded taxonomy has no table definitions (e.g., a concepts-only taxonomy)?
- How does the system handle a reporting period that spans more than one calendar year, when the taxonomy only defines annual periods?
- What happens when the user attempts to create a second instance from the same taxonomy in the same session — does the application support multiple open instances simultaneously?
- What happens when the taxonomy declares a dimension as mandatory for a table's filter axis but provides no allowed member values?
- How does the system handle a taxonomy update (reload) while an in-progress new instance is being configured?
- What happens if the chosen save path already contains an XBRL file — does the application overwrite silently, or warn the user?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow the user to initiate the creation of a new XBRL instance when a BDE taxonomy is loaded in the current session.
- **FR-002**: The system MUST require the user to provide a reporting entity identifier (LEI or BDE-assigned code) and a reporting period (start date, end date, or instant date as required by the taxonomy) before the instance structure is created.
- **FR-003**: The system MUST automatically bind the new instance to the currently loaded taxonomy by generating the correct schemaRef and namespace declarations from the taxonomy metadata — without requiring manual input from the user.
- **FR-004**: The system MUST validate the provided reporting period against the period type declared in the taxonomy (duration vs. instant) and reject incompatible combinations with an explanatory error.
- **FR-005**: The system MUST present all report tables available in the loaded taxonomy and allow the user to select a subset to include in the new instance; at least one table must be selected.
- **FR-006**: The system MUST warn the user and require confirmation before removing a previously selected table that already has data associated with it.
- **FR-007**: For each selected table, the system MUST present all filter-axis (Z-axis) dimensions defined in the taxonomy's table linkbase (PWD specification) and require the user to assign a value to each mandatory dimension.
- **FR-008**: The system MUST restrict dimension value selection to the members declared in the taxonomy for enumerated (closed) dimensions; free-text input is not permitted for enumerated dimensions.
- **FR-009**: The system MUST generate valid XBRL context elements in the instance for each unique combination of entity, period, and selected dimension members.
- **FR-010**: The system MUST allow the user to save the configured instance to a chosen local filesystem path as a well-formed XBRL instance document (XML).
- **FR-011**: The system MUST warn the user before overwriting an existing file at the chosen save path.
- **FR-012**: The system MUST keep the newly created instance in memory after saving so the user can continue working without reopening the file.

### Key Entities

- **XBRL Instance**: The top-level reporting document, bound to a specific taxonomy entry point, containing one reporting entity, one reporting period, and a set of facts organised into contexts.
- **Reporting Entity**: The legal or organisational entity responsible for the report, identified by an LEI or BDE-assigned code.
- **Reporting Period**: The time interval (duration with start/end dates, or instant date) that the reported facts cover, constrained by the taxonomy's declared period type.
- **Instance Table Scope**: The subset of taxonomy report tables explicitly included in this instance submission, each represented as a reporting unit in the XBRL document.
- **XBRL Context**: A combination of entity identifier, reporting period, and dimensional scenario that defines the meaning of one or more facts; generated automatically from the user's selections.
- **Dimensional Configuration**: The set of filter-axis (Z-axis) dimension member assignments that the user declares for each table, which drive context generation.
- **Instance File**: The persisted XML representation of the XBRL instance, saved to the local filesystem.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can create a fully configured new XBRL instance (entity, period, tables selected, dimensional contexts set) in under 5 minutes for a taxonomy with up to 20 tables.
- **SC-002**: 100% of newly created instances pass basic XBRL structural well-formedness validation (correct namespace declarations, valid schemaRef, well-formed contexts) without any manual correction by the user.
- **SC-003**: All required dimension fields for filter axes are surfaced to the user — a user can complete dimensional configuration without consulting external taxonomy documentation.
- **SC-004**: An instance saved to disk and reopened contains exactly the same structure (entity, period, table scope, dimensional context) as when it was saved — 0% data loss on save/reopen cycle.
- **SC-005**: The application prevents creation of structurally invalid instances — instances with missing mandatory fields (entity, period, at least one table) cannot be saved.

## Assumptions

- A BDE taxonomy is already loaded and available in the current session (dependency on Feature 001 — Taxonomy Loading and Caching).
- The reporting entity identifier format accepted is the BDE-defined entity code; LEI support may be added later and is out of scope for this feature.
- A single new instance is created per workflow invocation; support for multiple simultaneously open instances is out of scope for this feature but must not be architecturally precluded.
- The XBRL instance output format is standard XBRL 2.1 XML (not inline XBRL); inline XBRL support is out of scope for this feature.
- All filter-axis (Z-axis) dimensions in BDE taxonomy tables are enumerated (closed) dimensions; open/typed dimensions at the filter axis are not expected in BDE taxonomies for this feature's scope.
- The reporting period type (duration or instant) is declared by the taxonomy and enforced; mixed-period instances are not in scope.
- The instance is saved as a single XML file; multi-file instances are out of scope.

## Out of Scope

- Entering or editing fact values within the instance (covered by a separate instance editing feature).
- Validating the instance against BDE business rules (covered by a separate validation feature).
- Rendering the instance tables in the UI viewer (covered by a separate table rendering feature).
- Reopening and editing an existing instance (covered by a separate instance editing feature).
- Inline XBRL (iXBRL) output format.
- Automatic population of default or pre-filled fact values.
- Multi-entity reporting instances.

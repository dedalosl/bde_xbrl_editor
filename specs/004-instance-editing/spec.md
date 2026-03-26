# Feature Specification: Instance Editing

**Feature Branch**: `004-instance-editing`
**Created**: 2026-03-24
**Status**: Draft
**Input**: User description: "Instance edition — open an existing XBRL instance from a BDE taxonomy, user can edit it and visualize it using the advanced table rendering"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open an Existing XBRL Instance and Bind It to Its Taxonomy (Priority: P1)

A reporting user has an existing XBRL instance file (previously created or received) and wants to review or update it. They open the instance in the BDE XBRL Editor. The application parses the instance, automatically identifies and loads the referenced BDE taxonomy (if not already cached), and presents the user with the instance ready for editing.

**Why this priority**: Opening an existing instance is the entry point for all editing work. Without it, users cannot modify previously created or received reports. It is also the most common real-world workflow — most users will open existing instances far more often than creating new ones from scratch.

**Independent Test**: Can be fully tested by opening an existing XBRL instance file, verifying that the application correctly identifies the bound taxonomy (from the instance's schemaRef), loads it, and displays the instance metadata (entity, period, filing indicators/tables) — independently of any editing or rendering.

**Acceptance Scenarios**:

1. **Given** a valid XBRL instance file exists on the filesystem, **When** the user opens it in the application, **Then** the instance is parsed, its bound taxonomy is identified from the schemaRef, the taxonomy is loaded (from cache if available, from disk otherwise), and the instance metadata is displayed.
2. **Given** an instance is opened, **When** the application identifies the taxonomy, **Then** the list of tables included in the instance (via filing indicators or reporting units) is shown to the user.
3. **Given** an instance references a taxonomy that is not found at the expected local path, **When** the user attempts to open the instance, **Then** the application informs the user that the taxonomy could not be located, states the expected path, and offers the option to point to the correct taxonomy location manually.
4. **Given** a file that is not a valid XBRL instance is opened, **When** parsing is attempted, **Then** the application reports a clear error identifying why the file was rejected (not well-formed XML, missing schemaRef, unrecognised namespace, etc.) and the application remains stable.

---

### User Story 2 - Visualise Instance Data in the Advanced Table Viewer (Priority: P2)

Once an instance is open, the user navigates to any of the instance's included report tables and views its data in the full advanced table renderer. The table structure comes from the taxonomy, and the cell values come from the instance's facts — giving the user a clear, structured view of the reported data.

**Why this priority**: The combination of table rendering with instance data is the primary way users review and understand their reports. It is the central value proposition of the editor: seeing BDE-structured data in BDE-structured tables. All editing work starts from this view.

**Independent Test**: Can be fully tested by opening an instance, selecting a table, and verifying that the rendered grid correctly shows the instance's fact values in the right cells, with proper Z-axis navigation, labels, and formatting — independently of any edit operations.

**Acceptance Scenarios**:

1. **Given** an instance is open, **When** the user selects a report table from the instance's table list, **Then** the table is rendered using the advanced PWD table viewer with the instance's fact values displayed in their correct cells.
2. **Given** a table is rendered with instance data, **When** the user navigates between Z-axis slices, **Then** the correct facts for each slice are displayed — facts that do not belong to the current Z-axis context are not shown in that slice's grid.
3. **Given** a table is rendered and some cells have no corresponding fact in the instance, **When** the user views the table, **Then** those cells appear empty and are visually distinct from cells with explicit values (including explicit zero values).
4. **Given** the same fact exists for multiple contexts that map to the same cell under the current Z-axis slice, **When** the table is rendered, **Then** the application alerts the user to the ambiguity rather than silently picking one value.

---

### User Story 3 - Edit Fact Values Directly in the Table (Priority: P3)

The user edits the value of a fact by clicking directly on a cell in the rendered table, typing a new value, and confirming. The in-memory instance is updated immediately, and the cell reflects the new value. Data type constraints from the taxonomy are enforced — the user cannot enter text in a numeric field or a date in a monetary field.

**Why this priority**: Inline table editing is the core editing interaction. It gives users the most natural and context-aware way to enter and change values — directly in the structured report layout they are familiar with from BDE reporting tools and Excel. It is what differentiates the editor from a read-only viewer.

**Independent Test**: Can be fully tested by opening an instance, editing a cell value, saving the instance, reopening it, and confirming that the new value appears in the correct cell — independently of any validation or batch operations.

**Acceptance Scenarios**:

1. **Given** a table is rendered with an instance open, **When** the user clicks on an editable cell and types a new value, **Then** the cell enters edit mode, accepts input constrained to the cell's declared data type, and displays the new value immediately upon confirmation.
2. **Given** the user enters a value that violates the cell's data type (e.g., text in a monetary field), **When** the user attempts to confirm the edit, **Then** the application rejects the value, shows an inline error explaining the expected format, and leaves the previous value intact.
3. **Given** a cell is edited, **When** the user presses Escape, **Then** the edit is cancelled and the cell reverts to its previous value with no change to the instance.
4. **Given** a cell is empty (no fact) and the user enters a new value, **When** the value is confirmed, **Then** a new fact is created in the instance with the correct XBRL context (entity, period, dimension members derived from the cell's position and Z-axis selection).
5. **Given** a cell has an existing fact and the user deletes its value (submits empty), **When** the deletion is confirmed, **Then** the fact is removed from the instance and the cell reverts to an empty state.

---

### User Story 4 - Save the Edited Instance (Priority: P4)

After making edits, the user saves the instance. They can either save it in place (overwrite the original file) or save it to a new location. The saved file is a well-formed, valid XBRL instance XML document reflecting all edits.

**Why this priority**: Without saving, all edits are lost. This is lower priority than editing itself because the save mechanism follows naturally from the editing capability and is straightforward in scope. However, it is essential for the feature to deliver any real-world value.

**Independent Test**: Can be fully tested by editing facts in an open instance, saving to a new file path, then opening the saved file independently (without relying on the in-memory state) and confirming all edits are correctly persisted.

**Acceptance Scenarios**:

1. **Given** an instance has been edited, **When** the user saves to the original file path, **Then** the file is overwritten with a well-formed XBRL XML document containing all edits.
2. **Given** an instance has been edited, **When** the user saves to a new file path, **Then** a new file is created at that path containing all edits, and the original file is unchanged.
3. **Given** the user saves to a path where a file already exists (not the original), **When** the save is attempted, **Then** the application warns the user before overwriting.
4. **Given** the user attempts to save to a path where they lack write permissions, **When** the save is attempted, **Then** the application shows a clear error and leaves the in-memory instance intact.
5. **Given** an instance is saved and then reopened, **When** the user views a table, **Then** all previously edited values appear exactly as they were at save time — no rounding, truncation, or loss of precision.

---

### User Story 5 - Track Unsaved Changes and Prevent Accidental Data Loss (Priority: P5)

The application tracks whether the currently open instance has unsaved changes and warns the user before they navigate away, close the instance, or open a different file without saving.

**Why this priority**: Data loss from accidental close or navigation is a significant risk in any editing tool. Protecting users from losing their work builds trust and is especially critical in a regulatory reporting context where re-entering data is costly.

**Independent Test**: Can be fully tested by editing a cell, then attempting to close the instance without saving, and confirming that the application presents a warning with save/discard/cancel options — independently of the save mechanism.

**Acceptance Scenarios**:

1. **Given** an instance has unsaved changes, **When** the user attempts to close it, **Then** the application presents a prompt offering Save, Discard Changes, and Cancel options.
2. **Given** an instance has unsaved changes, **When** the user attempts to open a different instance, **Then** the same unsaved-changes prompt is shown before proceeding.
3. **Given** an instance has no unsaved changes, **When** the user closes it, **Then** no prompt is shown and the instance is closed immediately.
4. **Given** an instance has unsaved changes, **When** the user chooses Discard Changes in the prompt, **Then** the instance is closed (or the action proceeds) without saving, and all edits since the last save are lost.

---

### Edge Cases

- What happens when the instance file references a taxonomy version that is not currently loaded and cannot be found locally?
- What happens when the instance contains facts that reference concepts not defined in the bound taxonomy (orphaned facts)?
- What happens when the instance has contexts that do not map to any cell in any rendered table (e.g., from a different taxonomy version)?
- How does the system handle an instance file that is too large to parse within reasonable time (e.g., hundreds of thousands of facts)?
- What happens when the user edits a cell value and the new value changes the calculation relationships with other cells in the taxonomy's calculation linkbase — are dependent cells highlighted?
- What happens when the same instance file is opened twice by the user (if the application allows multiple sessions)?
- How does the system behave when the instance file is modified externally (on disk) while it is open in the editor?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow the user to open an existing XBRL instance file from the local filesystem by providing its path.
- **FR-002**: The system MUST parse the opened instance, extract its schemaRef to identify the bound taxonomy, and load that taxonomy (from cache if available, from disk otherwise).
- **FR-003**: When the bound taxonomy cannot be found at the expected local path, the system MUST inform the user and allow them to manually specify the correct taxonomy location.
- **FR-004**: The system MUST display the instance's metadata upon opening: bound taxonomy name and version, reporting entity, reporting period, and the list of included report tables (derived from filing indicators or reporting units).
- **FR-005**: The system MUST render any table included in the open instance using the advanced PWD table viewer (Feature 003), displaying existing fact values in their correct cells.
- **FR-006**: The system MUST allow the user to edit fact values by interacting directly with cells in the rendered table; cells must be selectable and enter an edit mode on user action.
- **FR-007**: The system MUST enforce data type constraints during editing — values entered must conform to the concept's declared data type; non-conforming input must be rejected with an inline error message.
- **FR-008**: When a user confirms a new value for an empty cell (no existing fact), the system MUST create a new fact in the instance with the correct XBRL context derived from the cell's position (entity, period, dimension members from the current Z-axis and cell coordinate).
- **FR-009**: When a user deletes the value of an existing fact (submits empty), the system MUST remove that fact from the instance.
- **FR-010**: The system MUST track all unsaved changes in the current session and display a visual indicator when the instance has unsaved edits.
- **FR-011**: The system MUST prompt the user with Save / Discard / Cancel options when they attempt to close the instance or open another file while unsaved changes exist.
- **FR-012**: The system MUST allow the user to save the edited instance to the original file path (overwrite) or to a new path; saving to an existing file at a different path requires user confirmation.
- **FR-013**: The saved instance file MUST be a well-formed XBRL 2.1 XML document; the system must not produce malformed XML under any editing scenario.
- **FR-014**: The system MUST preserve all facts, contexts, units, and metadata from the original instance that were not modified by the user — no silent data loss during save.
- **FR-015**: The system MUST handle instances containing facts for concepts not present in the bound taxonomy by preserving those facts unchanged in the saved file, and informing the user that orphaned facts exist.

### Key Entities

- **Open Instance**: The in-memory, editable representation of a loaded XBRL instance file, tracking its facts, contexts, units, metadata, and unsaved-change state.
- **Fact**: A single reported value (numeric or textual) associated with a concept, a context (entity + period + dimensions), and optionally a unit; the atomic unit of data in an XBRL instance.
- **Edit Operation**: A user-initiated change to the value of a fact, the creation of a new fact, or the deletion of an existing fact; each is tracked as an unsaved change.
- **Filing Indicator**: A declaration within a BDE XBRL instance that a specific report table is included in the submission; used to determine which tables the instance covers.
- **Instance Metadata**: The top-level descriptive information of an open instance: schemaRef (bound taxonomy entry point), reporting entity, reporting period, and list of included tables.
- **Unsaved Change Set**: The collection of all edit operations applied to the instance since the last save; cleared on save, discarded on explicit discard.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An existing XBRL instance of typical BDE size (up to 10,000 facts) is opened, its taxonomy loaded (if not cached), and its first table rendered in under 15 seconds.
- **SC-002**: A user can locate, select, and edit a specific cell value in a rendered table in under 30 seconds, including navigating to the correct table and Z-axis slice.
- **SC-003**: 100% of edit operations that are confirmed by the user are correctly reflected in the saved XBRL file — no edits are silently lost between in-memory state and the saved file.
- **SC-004**: The application correctly preserves 100% of unmodified facts, contexts, units, and metadata from the original instance during a save operation — no data loss for untouched data.
- **SC-005**: The unsaved-changes safeguard prevents data loss in 100% of tested close/navigate scenarios — no scenario exists where the user loses unsaved edits without having chosen to discard them.
- **SC-006**: Data type validation correctly rejects 100% of type-incompatible inputs and allows 100% of type-compatible inputs — no false positives or false negatives in the type enforcement.

## Assumptions

- The XBRL instance format is standard XBRL 2.1 XML (not inline XBRL); iXBRL instances are out of scope.
- The bound taxonomy is identified via the instance's `xbrli:schemaRef` element; instances without a schemaRef are considered invalid and are rejected.
- The taxonomy referenced by the instance is available on the local filesystem at a path that can be derived from the schemaRef or specified manually by the user.
- Only one instance is open at a time; simultaneous multi-instance editing is out of scope.
- The table rendering capability (Feature 003) is available and fully operational; this feature builds on it directly.
- The taxonomy loading and caching capability (Feature 001) is available; taxonomy loading on instance open reuses that mechanism.
- Filing indicators are the mechanism BDE uses to declare which tables are included in a submission; instances without filing indicators are treated as including all tables whose facts are present.
- Calculation linkbase consistency checking (highlighting cells that break calculation rules after an edit) is surfaced as an informational indicator only; blocking enforcement of calculations is out of scope for this feature.

## Out of Scope

- Creating a new instance from scratch (covered by Feature 002 — Instance Creation).
- Formal XBRL validation against BDE business rules (covered by a separate validation feature).
- Editing instance-level metadata (entity, period, filing indicators) after the instance is opened — only fact values are editable in this feature.
- Inline XBRL (iXBRL) instance support.
- Exporting the instance to non-XBRL formats (PDF, Excel, CSV).
- Multi-instance editing (two instances open simultaneously).
- Merging or comparing two instances.
- Undo/redo history beyond the current session's unsaved-change tracking.

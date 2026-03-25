# Feature Specification: Table Rendering — PWD Table Linkbase Viewer

**Feature Branch**: `003-table-rendering-pwd`
**Created**: 2026-03-24
**Status**: Draft
**Input**: User description: "Table rendering — visualizing BDE taxonomy tables in an advanced viewer, we need to implement the rendering for PWD Table Linkbase Specification on https://specifications.xbrl.org/work-product-index-table-linkbase-table-linkbase-1.0.html"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Render a BDE Taxonomy Table as a Structured Grid (Priority: P1)

A user see a tree with the report tables from a loaded BDE taxonomy, he select one of them and the application renders it as a structured, multi-dimensional grid. The rendered table faithfully reflects the table's structure as defined in the taxonomy's PWD Table Linkbase — with correct row headers, column headers, and the grid of data cells — exactly as BDE expects the report to look.

**Why this priority**: Correct table rendering is the visual core of the application. Without it, users cannot see what data they need to enter, cannot understand the report structure, and cannot use any editing or data-entry features. Everything else is built on top of this.

**Independent Test**: Can be fully tested by rendering a known BDE taxonomy table and comparing the output grid structure (header labels, row count, column count, axis organisation) against the table definition in the taxonomy — independently of any instance data or editing capability.

**Acceptance Scenarios**:

1. **Given** a BDE taxonomy is loaded, a tree of the available report tables is showed **When** the user selects a report table, **Then** the application renders that table as a grid with column headers (X-axis), row headers (Y-axis), and a body of data cells correctly sized and positioned.
2. **Given** a table with multi-level column headers (hierarchical breakdown nodes on the X-axis), **When** the table is rendered, **Then** the column headers are displayed as a spanning hierarchy — parent headers span across their child columns, and leaf headers align with individual data columns.
3. **Given** a table with multi-level row headers (hierarchical breakdown nodes on the Y-axis), **When** the table is rendered, **Then** the row headers are displayed as a spanning hierarchy — parent row headers span across their child rows, and leaf headers align with individual data rows.
4. **Given** a table whose structure is entirely driven by the taxonomy definition, **When** it is rendered, **Then** no table layout is hardcoded — the header structure, spanning, and cell positions are derived solely from the PWD Table Linkbase definition.

---

### User Story 2 - Navigate and Select the Filter-Axis (Z-Axis) Context for a Table (Priority: P2)

Many BDE report tables have a filter axis (Z-axis) defining multiple slices of the same grid — for example, different entity types, currencies, or consolidation scopes. The user can navigate between Z-axis slices and the rendered grid updates to show the correct header labels and data cells for the selected slice.

**Why this priority**: BDE tables frequently use the Z-axis to represent reporting context variations. Without Z-axis navigation, the user sees only one slice and may not realise others exist, or may confuse which context applies to the data they are viewing or entering.

**Independent Test**: Can be fully tested by rendering a table with a multi-member Z-axis, switching between Z-axis members, and confirming that the displayed header labels and available data cells change correctly for each Z-axis selection — independently of any fact data.

**Acceptance Scenarios**:

1. **Given** a table with a multi-member Z-axis, **When** the table is first rendered, **Then** the available Z-axis members are displayed as a navigable selector (e.g., tabs or dropdown), and the first member is selected by default.
2. **Given** a Z-axis member is selected, **When** the user switches to a different Z-axis member, **Then** the grid updates to reflect the header labels and dimensional context for the new selection without requiring a full table reload.
3. **Given** a table with a single Z-axis member (or no Z-axis), **When** the table is rendered, **Then** no Z-axis selector is shown — the grid is displayed directly without the additional navigation element.
4. **Given** a Z-axis slice is active, **When** the user views the table, **Then** the currently active Z-axis member is clearly indicated so the user always knows which reporting context they are viewing.

---

### User Story 3 - Display Concept Labels and Data Types Within the Table (Priority: P3)

Each cell in a rendered BDE table corresponds to a taxonomy concept. The user can see the label of the concept associated with a cell (via its row/column header intersection), its data type (monetary, percentage, integer, text, etc.), and any dimensional constraints that apply — without needing to consult the taxonomy documentation separately.

**Why this priority**: BDE taxonomy concepts often have non-obvious identifiers. Surfacing labels and data types directly in the rendered table empowers users to understand what to enter in each cell and reduces reporting errors, without needing external reference material.

**Independent Test**: Can be fully tested by rendering a table and verifying that hovering over or selecting a cell reveals the correct concept label (from the taxonomy's label linkbase), its data type, and its full dimensional coordinate — independently of any data-entry functionality.

**Acceptance Scenarios**:

1. **Given** a table is rendered, **When** the user inspects a data cell, **Then** the application displays the label of the concept associated with that cell, sourced from the taxonomy's label linkbase in the active display language.
2. **Given** a table is rendered, **When** the user inspects a data cell, **Then** the application displays the data type of that cell's concept (e.g., monetary, decimal, string, date) so the user knows what format of value is expected.
3. **Given** a table uses multiple label roles (standard label, terse label, documentation label), **When** the user views a cell, **Then** the standard label is shown by default, and other label roles are accessible on demand.
4. **Given** the taxonomy declares labels in multiple languages, **When** the user views the table, **Then** labels are shown in the application's active display language (Spanish by default), falling back to English, then to the concept QName if no matching label exists.

---

### User Story 4 - Display Instance Fact Values Within the Rendered Table (Priority: P4)

When a user has an XBRL instance open alongside the loaded taxonomy, the rendered table shows the actual fact values from the instance in the corresponding cells — providing an integrated view where the table structure comes from the taxonomy and the values come from the instance.

**Why this priority**: The table viewer is most valuable when it shows real data. Displaying instance facts in the rendered grid is what transforms the viewer from a pure taxonomy browser into a reporting tool — enabling users to review, check, and understand their submitted or in-progress data in context.

**Independent Test**: Can be fully tested by opening an existing XBRL instance, navigating to a table, and confirming that the fact values stored in the instance appear in the correct cells of the rendered grid — matched by their XBRL context (entity, period, dimensions) — independently of any editing functionality.

**Acceptance Scenarios**:

1. **Given** an XBRL instance is open and a table is rendered, **When** the instance contains facts for that table's concepts with matching contexts, **Then** those fact values are displayed in the corresponding grid cells.
2. **Given** a rendered table with instance facts, **When** a cell has no corresponding fact in the instance, **Then** the cell is shown as empty (not as zero or null text) and is visually distinguishable from a cell with an explicit zero value.
3. **Given** a cell has a fact value in the instance, **When** the user views that cell, **Then** the value is formatted according to its data type — monetary values show decimal precision and optional currency symbol, dates are formatted to locale, percentages show the % indicator.
4. **Given** an instance contains a fact whose context does not match any cell coordinate in the rendered table, **When** the table is rendered, **Then** that fact is silently ignored in the grid display (it is not an error) and is not shown in an incorrect cell.

---

### User Story 5 - Display Row and Column Codes on Leaf Headers (Priority: P5)

At the deepest (leaf) level of the row headers (Y-axis) and column headers (X-axis), BDE taxonomy tables carry short alphanumeric codes — for example "0098" or "C0010" — that BDE uses to uniquely identify each row and column in its official reporting templates. These codes are stored in the taxonomy's label linkbase under the Eurofiling RC-code label role. The user sees these codes displayed alongside the header label in every leaf header cell, matching the look of the official BDE report layout.

**Why this priority**: RC codes are the official identifiers BDE uses for rows and columns in its published report templates (e.g., "Row 0098" or "Column C0010"). Reporting staff cross-reference these codes constantly when filling in or reviewing submissions against BDE's published instructions. Displaying them in the leaf headers removes the need to consult external documents and prevents errors from referencing the wrong row or column.

**Independent Test**: Can be fully tested by rendering a BDE taxonomy table and verifying that every leaf row header and every leaf column header displays the corresponding RC code from the taxonomy's label linkbase (Eurofiling RC-code role) alongside its standard label — independently of any instance data, editing, or Z-axis navigation.

**Acceptance Scenarios**:

1. **Given** a table is rendered and a leaf row or column header node has an RC-code label in the taxonomy (Eurofiling RC-code label role), **When** the header cell is displayed, **Then** the RC code value is shown visibly in that header cell, distinguishable from the standard descriptive label.
2. **Given** a leaf header node has both a standard label and an RC code, **When** the header cell is displayed, **Then** the RC code and the standard label are both shown — the RC code does not replace the descriptive label.
3. **Given** a leaf header node has no RC-code label in the taxonomy (the role is absent for that node), **When** the header cell is displayed, **Then** only the standard label is shown with no empty code placeholder — the absence of an RC code is handled gracefully.
4. **Given** RC codes are displayed in leaf headers, **When** the user copies or exports the table structure, **Then** the RC codes are included in the output alongside the corresponding labels.

---

### Edge Cases

- What happens when a table definition in the taxonomy references a concept that does not exist in the taxonomy's concept declarations (broken linkbase)?
- How does the system render a table with an extremely large number of rows or columns (e.g., 500+ rows) — is scrolling, pagination, or virtualisation needed?
- What happens when a table has breakdown nodes with no label in the active display language or any fallback language?
- How does the system handle a table whose Z-axis has a very large number of members (e.g., 50+ filter combinations)?
- What happens when the same concept appears in multiple cells of the same table (due to multi-dimensional breakdowns)?
- What happens if a table has nested breakdowns with different aspect cover rules — are header spans computed correctly in all cases?
- How does the system handle a table that is structurally valid per the PWD specification but produces a grid with zero rows or zero columns?
- What happens when two leaf header nodes at the same axis position have different RC codes — which one takes precedence?
- How does the system behave when a taxonomy declares RC-code labels with multiple language variants for the same node — are RC codes language-neutral (they should be)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST render any report table defined in a loaded BDE taxonomy as a structured two-dimensional grid, with the X-axis defining columns and the Y-axis defining rows, driven entirely by the taxonomy's PWD Table Linkbase definition.
- **FR-002**: The system MUST correctly compute and render hierarchical (multi-level, spanning) column headers from X-axis breakdown nodes, where parent nodes span their children and leaf nodes align with individual data columns.
- **FR-003**: The system MUST correctly compute and render hierarchical (multi-level, spanning) row headers from Y-axis breakdown nodes, where parent nodes span their children and leaf nodes align with individual data rows.
- **FR-004**: The system MUST support Z-axis navigation when a table has a filter axis with multiple members, presenting a selector that allows the user to switch between Z-axis slices without reloading the whole table.
- **FR-005**: The system MUST display a concept label (from the taxonomy label linkbase) for each data cell, accessible without leaving the table view.
- **FR-006**: The system MUST display the data type of the concept associated with each data cell.
- **FR-007**: The system MUST support multi-language label display, defaulting to Spanish, falling back to English, and then to the concept QName.
- **FR-008**: When an XBRL instance is open, the system MUST display instance fact values in their corresponding table cells, matched by the full XBRL context (entity, period, dimension members).
- **FR-009**: The system MUST visually distinguish between cells that have an explicit fact value in the instance, cells that are empty (no fact), and cells that are not applicable for the current Z-axis slice or dimensional context.
- **FR-010**: The system MUST format displayed fact values according to their concept data type (monetary precision, date locale formatting, percentage indicator).
- **FR-011**: The system MUST handle tables with a very large number of rows or columns (over 200 rows) without freezing the interface — the table must remain scrollable and navigable.
- **FR-012**: The system MUST display row and column headers as frozen (sticky) when the user scrolls the table body, so header context is always visible.
- **FR-013**: The system MUST handle broken or incomplete table linkbase definitions (missing concepts, unresolvable references) gracefully, rendering as much of the table as possible and clearly indicating which parts could not be resolved.
- **FR-013a**: When an instance is loaded alongside the taxonomy and multiple facts in the instance match the same cell coordinate (duplicate facts), the system MUST flag this as a validation error on that cell rather than silently displaying one of the values.
- **FR-014**: The system MUST display the RC code (sourced from the Eurofiling RC-code label role in the taxonomy's label linkbase) alongside the standard label in every leaf-level row header and column header cell where such a code is declared; the RC code must be visually distinct from the descriptive label and must not replace it.

### Key Entities

- **Rendered Table**: The visual representation of a taxonomy table definition, composed of a header area and a body grid of data cells, derived from the PWD Table Linkbase.
- **Table Axis**: One of three axes (X, Y, Z) that organise the dimensional space of a table; X = columns, Y = rows, Z = filter slices.
- **Breakdown Node**: A node in the PWD Table Linkbase that defines a header label and potentially subdivides its axis into child breakdowns; the source of all header spanning information.
- **Grid Cell**: A single intersection point in the rendered table body, identified by its row coordinate, column coordinate, and Z-axis member; associated with a specific taxonomy concept and XBRL context.
- **Cell Coordinate**: The complete set of dimensional aspect values (concept, entity, period, explicit dimensions) that uniquely identifies a grid cell's XBRL context.
- **Fact Value**: A reported numeric or textual value from an open XBRL instance, displayed in its corresponding grid cell when a matching context exists.
- **Z-Axis Slice**: One member of the filter axis (Z-axis), representing a specific dimensional context that applies uniformly to all cells in the X-Y grid for that slice.
- **RC Code**: A short alphanumeric identifier (e.g., "0098", "C0010") assigned to a leaf row or column header node via the Eurofiling RC-code label role in the taxonomy's label linkbase; used by BDE to reference specific rows and columns in its official published report templates.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Any BDE taxonomy table is rendered with its full header structure correctly in under 3 seconds from the moment the user selects it.
- **SC-002**: 100% of PWD Table Linkbase-defined tables in all tested BDE taxonomies render without structural errors — no missing headers, no misaligned cell coordinates, no incorrect spanning.
- **SC-003**: Users can identify the concept label and data type of any cell without leaving the table view — confirmed by task completion in under 10 seconds per cell.
- **SC-004**: Instance fact values are displayed in the correct cells for 100% of facts whose context exactly matches a cell coordinate in the rendered table.
- **SC-005**: Tables with 200+ rows remain scrollable and responsive — the interface does not freeze or become unresponsive when navigating large tables.
- **SC-006**: Z-axis slice switching completes and the grid updates in under 1 second for tables with up to 50 Z-axis members.
- **SC-007**: 100% of leaf row and column header cells that have an RC code declared in the taxonomy display the correct code — no RC code is silently omitted or shown in the wrong header cell.

## Assumptions

- All BDE taxonomy tables use the PWD (Proposed Working Draft) Table Linkbase specification; the final Table Linkbase 1.0 specification is not in scope.
- The taxonomy is already loaded and its PWD table definitions are fully parsed (dependency on Feature 001 — Taxonomy Loading and Caching).
- An XBRL instance is optionally open; the table renderer must work in taxonomy-only mode (no instance) as well as with an open instance.
- Tables are rendered one at a time; simultaneous rendering of multiple tables in the same view is out of scope for this feature.
- The rendering target is a desktop UI; mobile/responsive rendering is out of scope.
- The default display language for labels is Spanish; the language setting is configured at the application level, not per-table.
- Aspect cover rules in the PWD specification (all, dimensions, concept, entity, period, etc.) are supported as defined; no BDE-specific override of cover rule semantics is expected.
- RC codes (Eurofiling label role `http://www.eurofiling.info/xbrl/role/rc-code`) are treated as language-neutral identifiers; if multiple language variants exist for the same node's RC code, any variant may be used as they are expected to be identical across languages.

## Out of Scope

- Entering or editing fact values within the rendered table (covered by a separate instance editing feature).
- Exporting the rendered table to PDF, Excel, or other formats.
- Printing the rendered table.
- Rendering inline XBRL (iXBRL) documents.
- Rendering tables defined using the final Table Linkbase 1.0 specification (non-PWD).
- Custom user-defined column/row sorting or grouping not derived from the taxonomy definition.
- Comparative rendering of two different instances side by side in the same table grid.

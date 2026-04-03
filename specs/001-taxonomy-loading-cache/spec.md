# Feature Specification: Taxonomy Loading and Caching

**Feature Branch**: `001-taxonomy-loading-cache`
**Created**: 2026-03-23
**Status**: Draft
**Input**: User description: "Taxonomy loading and caching — load BDE XBRL taxonomies from local filesystem, parse their structure, and cache them in memory for reuse across sessions"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Load a BDE Taxonomy from the Local Filesystem (Priority: P1)

A reporting user opens the BDE XBRL Editor and points it to a BDE taxonomy entry point from a taxonomy stored on their local machine. The application reads the taxonomy, parses its full structure (concepts, dimensions, linkbases, table definitions, validations), and makes it ready for use — all without any manual intervention beyond selecting the taxonomy location.

**Why this priority**: This is the foundational capability. No other feature (instance creation, validation, table rendering) can function without a successfully loaded taxonomy. It is the entry point for every user session.

**Independent Test**: Can be fully tested by selecting a taxonomy entry point path and verifying that the application correctly reports the taxonomy name, version, and the count of parsed concepts and tables — delivering the core "taxonomy is ready" value independently of any instance or rendering work.

**Acceptance Scenarios**:

1. **Given** a valid BDE taxonomy exists on the filesystem, **When** the user provides its entry point location to the application, **Then** the taxonomy is loaded, its structure is fully parsed, and the user sees confirmation of the taxonomy name and version.
2. **Given** a taxonomy has been loaded, **When** the user inspects the taxonomy details, **Then** the application displays the list of available report tables.
3. **Given** an invalid or corrupted taxonomy is provided, **When** the application attempts to load it, **Then** a clear, actionable error message is shown explaining what is wrong, and the application remains stable.
4. **Given** a taxonomy with a format not supported by the BDE XBRL Editor, **When** the user attempts to load it, **Then** the application rejects it with a message listing the supported formats (based on the list of already implemented BDE taxonomies)
5. **Give** a valid BDE taxonomy exists on the filesystem, **When** Network resolution of remote schema references is disabled by default; **Then** local catalog-based resolution is the expected approach for offline/air-gapped reporting environments.
---

### User Story 2 - Reuse a Previously Loaded Taxonomy Within the Same Session (Priority: P2)

A user who has already loaded a taxonomy earlier in their session switches between different tasks (e.g., opens a second report, starts a new instance) without needing to reload the taxonomy. The application transparently reuses the already-parsed taxonomy from its in-memory cache.

**Why this priority**: BDE taxonomies can be large and complex. Reloading and re-parsing on every operation would make the application noticeably slow. In-session caching is essential for a responsive user experience.

**Independent Test**: Can be fully tested by loading a taxonomy, performing two separate operations that each require taxonomy access, and confirming that the second operation completes significantly faster than the first — demonstrating cache reuse independently of any UI or instance feature.

**Acceptance Scenarios**:

1. **Given** a taxonomy has been loaded and is in the cache, **When** a second operation requests the same taxonomy, **Then** the taxonomy is served from cache and the operation begins without a measurable reload delay.
2. **Given** a taxonomy is cached, **When** the user explicitly requests a reload (refresh), **Then** the taxonomy is re-read from the filesystem, the cache is updated, and the user is informed of the refresh.
3. **Given** two different taxonomy versions are available, **When** the user works with both, **Then** each is cached independently and switching between them does not corrupt either cached version.

---

### User Story 3 - Inspect Taxonomy Structure Before Working with Reports (Priority: P3)

A user wants to understand what reporting tables and concepts a loaded BDE taxonomy contains before creating or editing an instance. They can browse the taxonomy structure — available tables, dimensions, and concepts — directly from the loaded taxonomy.

**Why this priority**: Users need to understand what a taxonomy offers before committing to creating or editing an instance. Providing structured taxonomy browsing on top of the loaded/cached taxonomy adds immediate value and validates the completeness of the parsing step.

**Independent Test**: Can be fully tested by loading a taxonomy and listing its available tables and top-level concepts — confirming that the parsed structure is navigable and complete — independently of instance creation or rendering.

**Acceptance Scenarios**:

1. **Given** a taxonomy is loaded, **When** the user requests a list of available report tables, **Then** the application returns the complete list of table identifiers and their human-readable labels in the taxonomy's declared language.
2. **Given** a taxonomy is loaded, **When** the user requests the concepts associated with a specific table, **Then** the application returns the correct concept set with their labels and data types.
3. **Given** a taxonomy is loaded, **When** the user requests the dimensional details associated with a specific table, **Then** the application returns the correct dimensional hipercube hierarchies with their concept, dimensions and the allowed values for each dimension, with their labels and data types.
4. **Given** a taxonomy uses the PWD Table linkbase specification (as BDE taxonomies do), **When** the table structure is parsed, **Then** the table headers, axes, and cells are correctly interpreted according to the PWD specification.

---

### Edge Cases

- What happens when the taxonomy entrypoint path is a valid file but does not contain a recognizable XBRL taxonomy entry point?
- How does the system handle a taxonomy file that references remote schema files that are unavailable (network calls disabled by default)?
- What happens when available memory is insufficient to hold the fully parsed taxonomy in cache?
- How does the system behave when the taxonomy path provided by the user points to a directory that is deleted or becomes inaccessible while the taxonomy is cached?
- How does the system handle taxonomies with circular linkbase references?
- What happens when a taxonomy entry point is referencing, inside any of the files we are discovering in its DTS, an external file from other regulator like EBA or Eurofiling, even xbrl.org but it's available locally in the same base path were the user is placing its taxonomy files?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow the user to specify a taxonomy location as a local filesystem path to an unpacked directory.
- **FR-002**: The system MUST parse the full XBRL taxonomy structure from the specified location, including: concepts, labels (in all declared languages), presentation linkbase, calculation linkbase, definition linkbase, and table linkbase (PWD specification).
- **FR-002a**: The system MUST support all eight XBRL 2.1 standard label roles: `label`, `terseLabel`, `verboseLabel`, `documentation`, `periodStartLabel`, `periodEndLabel`, `totalLabel`, and `negatedLabel`. Label language selection MUST respect the `xml:lang` attribute and fall back through the configured language preference list (Spanish → English → QName).
- **FR-002b**: The system MUST parse generic linkbases using the XBRL Generic Links specification (`gen:link`, `gen:arc`) and the XBRL Generic Labels specification (`genlab:label`), resolving generic labels alongside standard labels. Label role precedence between standard and generic labels MUST follow the XBRL Generic Labels specification rules; labels defined in taxonomy extensions via generic linkbases MUST override base taxonomy labels per those rules.
- **FR-003**: The system MUST extract and expose BDE-specific taxonomy metadata, including the taxonomy name, version, reporting period type, and the list of available report tables with their identifiers and labels.
- **FR-004**: The system MUST cache the fully parsed taxonomy in memory after the first load so that subsequent operations within the same session reuse the cached version without re-parsing.
- **FR-005**: The system MUST support explicitly invalidating and reloading a cached taxonomy at the user's request, re-reading it from the filesystem.
- **FR-006**: The system MUST correctly parse taxonomies that use the PWD (Proposed Working Draft) Table linkbase specification, interpreting table structures, axes, breakdown nodes, and cell definitions as used by BDE taxonomies.
- **FR-007**: The system MUST reject taxonomy that cannot be parsed and provide a clear error message identifying the cause of failure (missing entry point, unrecognised format, structural error).
- **FR-008**: The system MUST allow multiple different taxonomy versions to be cached simultaneously without interference between them.
- **FR-009**: The system MUST NOT make external network calls during taxonomy loading unless explicitly configured to do so; all schema and linkbase resolution must default to local files only.
- **FR-010**: The system MUST report loading and parsing progress to the user for taxonomies that take longer than a few seconds to process.

### Key Entities

- **Taxonomy unpacked directory**: A distributable unit (directory) containing all XBRL schema files, linkbases, required to load the taxonomy.
- **Taxonomy Entry Point**: The declared starting point of a taxonomy, referencing the root schema that pulls in all concepts and linkbases.
- **Taxonomy Structure**: The fully parsed in-memory representation of a taxonomy, including concept tree, linkbase graphs, dimension definitions, and table definitions.
- **Table Definition**: A report table as declared in the taxonomy's table linkbase (PWD specification), with its axes sheet(Z)/row(Y)/column(X)/filter, breakdown nodes, and associated concepts.
- **Taxonomy Cache Entry**: A cache slot holding a parsed Taxonomy Structure keyed by its entry point identifier and version, with metadata about when it was loaded and its filesystem source path. It must be seriarizable.
- **Taxonomy Metadata**: High-level descriptive information about a taxonomy: name, version, publisher (BDE), supported reporting periods, and language declarations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A BDE taxonomy of typical size (up to 5,000 concepts, 50+ tables) is fully loaded and ready for use within 50 seconds of the user providing its location, on first load.
- **SC-002**: Any subsequent access to a previously loaded taxonomy within the same session is available in under 1 second (served from cache).
- **SC-003**: 100% of the report tables defined in a BDE taxonomy using the PWD Table linkbase are correctly identified and parseable — no tables are silently skipped or misinterpreted.
- **SC-004**: All taxonomy loading errors are reported with a message that allows the user to identify and resolve the problem without needing technical support — measured by a 0% "unknown error" rate in reported failures.
- **SC-005**: The application remains stable and responsive when a taxonomy fails to load — no crashes or loss of data in any open instances.

## Assumptions

- BDE taxonomies are distributed as standard ZIP archives that become unpacked directory structures, they are not conforming to the XBRL Taxonomy Packages 1.0 specification, so we cannot use them as taxonomy packages.
- The BDE XBRL Editor runs on a machine with sufficient memory to hold at least one fully parsed taxonomy; out-of-memory scenarios are handled gracefully but are not the primary design constraint for this feature.
- All BDE taxonomies use the PWD Table linkbase specification for their table definitions; no BDE taxonomy in scope uses the final Table Linkbase 1.0 specification.
- Taxonomy loading is triggered explicitly by the user; automatic discovery from the filesystem is out of scope for this feature.
- Labels are loaded in all languages declared by the taxonomy; the default display language is Spanish, with English as fallback, and the qNames values as second fallback.
- Network resolution of remote schema references is disabled by default; local catalog-based resolution is the expected approach for offline/air-gapped reporting environments. We must allow the users to review and edit it.

## Out of Scope

- Automatic discovery or download of BDE taxonomies from the internet or BDE web services.
- Editing or modifying taxonomy files.
- Persistent (on-disk) caching of parsed taxonomies across application restarts — only in-memory caching within a session is in scope (covered by a separate feature).
- Validation of XBRL instances against the taxonomy (covered by a separate feature).
- Rendering of taxonomy tables in the UI (covered by a separate feature).

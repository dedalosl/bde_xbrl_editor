# Product Requirements Document: XBRL Processor Application

**Version:** 1.0 Draft
**Date:** March 24, 2026
**Status:** Draft — Pending Review
**Target Delivery:** Q2 2026

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Goals](#goals)
3. [Non-Goals](#non-goals)
4. [Target Users & Personas](#target-users--personas)
5. [User Stories](#user-stories)
6. [Requirements](#requirements)
7. [Conformance & Standards Compliance](#conformance--standards-compliance)
8. [Success Metrics](#success-metrics)
9. [Open Questions](#open-questions)
10. [Timeline Considerations](#timeline-considerations)
11. [Appendix: Referenced Specifications](#appendix-referenced-specifications)

---

## Problem Statement

Financial reporting teams preparing XBRL-tagged regulatory filings lack a capable, integrated tool to load taxonomies, author instance documents, and visually validate their reports against dimensional models and rendering layouts. Existing commercial processors (Altova, CoreFiling, Fujitsu) are costly, opaque in their conformance posture, and often unsupported for newer XBRL standards like the Table Linkbase 1.0 PWD. Without a compliant, purpose-built tool, preparers are forced to work across disconnected utilities, increasing the risk of filing errors, non-compliance with taxonomy constraints, and costly rework before submission deadlines.

This initiative delivers a greenfield standalone XBRL processor that covers the complete authoring and validation lifecycle — from taxonomy loading and instance creation, through dimensional validation and table rendering — with full alignment to XBRL.org conformance suites.

---

## Goals

1. **Enable end-to-end XBRL instance authoring** so that financial reporting teams can create, edit, and validate XBRL instance documents without leaving a single application, reducing cross-tool context-switching to zero for core authoring workflows.

2. **Achieve conformance suite pass rates of 100%** across all targeted XBRL.org conformance suites (XBRL 2.1, Dimensions 1.0, Table Linkbase PWD, Formula 1.0, Generic Labels) at time of v1 release.

3. **Surface dimensional structure visually** so that users can inspect hypercube definitions, dimensional axes, and member hierarchies without reading raw taxonomy XML, reducing taxonomy comprehension time by at least 60% compared to raw-file workflows.

4. **Render table linkbase layouts accurately** so that preparers can see the expected rendered table structure (rows, columns, headers) before finalizing their instance data, cutting pre-submission validation rework by at least 50%.

5. **Support both standard and generic label processing** so that all label roles — including extended-type labels defined in generic linkbases — resolve correctly, ensuring preparers always see human-readable concept names rather than raw QNames.

---

## Non-Goals

The following are explicitly out of scope for v1:

- **Inline XBRL (iXBRL) rendering and tagging.** iXBRL authoring requires an HTML editing layer and a tag-in-place workflow that is a substantial independent workstream. This will be considered for v2 after core processing is proven stable.

- **Multi-user collaboration or cloud sync.** v1 is a standalone tool. Real-time co-authoring, version control integration, and cloud storage are deferred; they require a backend infrastructure investment that is out of scope for the Q2 2026 deadline.

- **Custom taxonomy authoring (DTS creation from scratch).** The tool loads and processes existing taxonomies; it does not provide a taxonomy editor or OWL/schema designer. Taxonomy creation tooling is a separate product area.

- **Automated submission to regulatory portals.** Filing submission workflows (SEC EDGAR, ESMA ESEF portal, EBA EUCLID) are integration features that depend on portal-specific APIs and authentication mechanisms, deferred to v2.

- **Full XBRL Formula execution engine (v1 partial).** Formula *validation* (evaluating formula assertions and consistency assertions against an instance) is in scope for v1 at a basic level. Full formula *authoring* and debugging tools are v2.

---

## Target Users & Personas

### Persona 1 — The Filing Preparer
**Name:** Ana, Senior Financial Reporting Analyst
**Context:** Works at a regulated financial institution preparing quarterly XBRL filings for a regulatory authority (e.g., EBA, ESMA, or SEC). Uses multiple tools today: a spreadsheet to enter data, a separate validator to check the XBRL, and a renderer to preview. Needs a unified workspace.
**Key needs:** Load the regulator's taxonomy, enter fact values, see the rendered report layout, catch dimensional errors before submission.

### Persona 2 — The Taxonomy Reviewer
**Name:** Marco, XBRL Specialist / Taxonomy Consultant
**Context:** Assists clients in understanding taxonomy structures — which concepts exist, how hypercubes are organised, what labels apply in which language. Currently navigates raw XML files.
**Key needs:** Browse concepts and their metadata, inspect dimensional hypercubes and axis/member trees, resolve labels across standard and generic linkbases.

---

## User Stories

### Taxonomy Loading

- As a filing preparer, I want to load an XBRL taxonomy package or entry-point schema so that I can work with the full DTS (Discoverable Taxonomy Set) without manually managing file references.
- As a filing preparer, I want to load a taxonomy from a local file system path or from a URL so that I can use both downloaded taxonomy packages and remotely hosted taxonomies.
- As a taxonomy reviewer, I want the processor to resolve all taxonomy imports and includes automatically so that I do not need to trace xs:import chains manually.
- As a taxonomy reviewer, I want to see a list of all concepts in a loaded taxonomy with their data types, period types, and balance attributes so that I can quickly audit coverage.

### Label Resolution

- As a filing preparer, I want all concept labels to display in my preferred language (e.g., English) using the standard label linkbase so that QNames never appear in the UI during normal use.
- As a filing preparer, I want extended label roles (e.g., `verboseLabel`, `terseLabel`, `documentation`) to be accessible per concept so that I can read the regulatory documentation label when disambiguating similar items.
- As a taxonomy reviewer, I want labels defined in generic label linkbases (using `gen:link` and `gen:arc`) to be resolved with the same precedence rules as standard labels so that taxonomy extensions using generic linkbases render correctly.
- As a taxonomy reviewer, I want to select the display language from available languages in the loaded taxonomy so that multilingual taxonomies render in the correct locale.

### Instance Document Creation & Editing

- As a filing preparer, I want to create a new XBRL instance document based on a loaded taxonomy so that I have a correctly structured starting point with the right namespace declarations.
- As a filing preparer, I want to add, edit, and delete facts (items and tuples) so that I can author the complete set of reported values.
- As a filing preparer, I want to specify the context (entity identifier, period, and dimensional members) for each fact so that facts are correctly anchored to their reporting scope.
- As a filing preparer, I want the editor to validate fact values against the concept's data type in real time so that I catch type errors before saving.
- As a filing preparer, I want to open an existing XBRL instance document and edit its facts so that I can revise previously prepared filings.
- As a filing preparer, I want to export the finished instance document as a valid XBRL XML file so that I can submit it to the regulatory portal.

### Dimensional Hypercube Inspection

- As a filing preparer, I want to see which hypercubes apply to a given concept so that I know what dimensional context is required when reporting that concept.
- As a filing preparer, I want to see all axes and their allowed member hierarchies for a hypercube so that I select only valid dimensional combinations when creating facts.
- As a taxonomy reviewer, I want to distinguish closed hypercubes from open hypercubes so that I understand which concepts accept unrestricted vs. constrained dimensional combinations.
- As a taxonomy reviewer, I want to see the default member for each dimension so that I understand when a dimension can be omitted from a context.
- As a filing preparer, I want a warning when I create a fact with dimensional members that violate the hypercube constraints so that I can correct the context before finalising the instance.

### Table Linkbase Rendering

- As a filing preparer, I want to select a table defined in the Table Linkbase and see its rendered layout (row headers, column headers, and cell axes) so that I know exactly which facts map to which cells.
- As a filing preparer, I want cells in the rendered table to show the fact values from the current instance document so that I can visually review the completed report layout.
- As a filing preparer, I want empty cells to be visually distinct from cells with values so that I can quickly spot unfilled required positions.
- As a taxonomy reviewer, I want to inspect the breakdown structure (rule nodes, aspect nodes, and constraint nodes) underlying a table so that I can verify the table definition is correct.

### Formula Validation

- As a filing preparer, I want to run formula assertions defined in the taxonomy's formula linkbase against my instance document so that I know whether my reported values satisfy the regulatory validation rules.
- As a filing preparer, I want to see a list of all formula assertion results (pass/fail) with the relevant fact values and the formula expression so that I can diagnose and correct failures.
- As a filing preparer, I want consistency assertions to be evaluated and flagged so that I catch cross-fact inconsistencies before submission.

---

## Requirements

### Must-Have — P0 (v1 launch blockers)

#### Taxonomy Processing

**XBRL 2.1 DTS Discovery**
The processor must implement XBRL 2.1 DTS discovery rules: resolving all xs:import, xs:include, and linkbaseRef elements to assemble the complete Discoverable Taxonomy Set.
_Acceptance criteria:_
- [ ] Given an entry-point schema URL or local path, when loaded, the processor resolves all reachable schema and linkbase documents without manual intervention.
- [ ] All imported schemas and linked linkbases are cached locally to avoid repeated network requests within a session.
- [ ] Discovery failures (404, schema parse errors) are reported with the failing URI and reason.

**Standard Label Linkbase Processing**
The processor must parse `label` linkbases and resolve labels for all standard label roles defined in XBRL 2.1.
_Acceptance criteria:_
- [ ] All XBRL 2.1 label roles (`label`, `terseLabel`, `verboseLabel`, `documentation`, `periodStartLabel`, `periodEndLabel`, `totalLabel`, `negatedLabel`) are supported.
- [ ] Label language selection respects the `xml:lang` attribute and falls back through a configurable language preference list.
- [ ] QNames are never shown in the UI when a label exists for the requested role and language; if no label is available, the QName is shown with a visual indicator.

**Generic Label Linkbase Processing**
The processor must parse generic linkbases using the Generic Links specification (`gen:link`, `gen:arc`) and the Generic Labels specification (`genlab:label`) and resolve labels alongside standard labels.
_Acceptance criteria:_
- [ ] Generic labels are loaded from linkbases using `gen:link` and `gen:arc` elements with `xlink:arcrole` pointing to generic label arc roles.
- [ ] Label role precedence between standard and generic labels follows XBRL Generic Labels specification rules.
- [ ] Labels defined in taxonomy extensions via generic linkbases override base taxonomy labels per precedence rules.

**Presentation, Calculation, and Definition Linkbase Parsing**
The processor must load and expose presentation, calculation, and definition linkbases for use in the UI and validation.

#### Dimensional Model (XBRL Dimensions 1.0)

**Hypercube Loading**
_Acceptance criteria:_
- [ ] All `all` and `notAll` hypercubes are identified and associated with their primary items.
- [ ] Each hypercube exposes its set of axes (dimensions) and each axis exposes its allowed member hierarchy (domain-member network).
- [ ] Closed vs. open hypercube flag is exposed per hypercube.
- [ ] Default members are identified per dimension.

**Dimensional Validation on Instance Facts**
_Acceptance criteria:_
- [ ] When a fact is created or edited, its dimensional context is validated against the applicable hypercube constraints.
- [ ] A violation is reported for each fact whose dimensional combination falls outside any applicable hypercube (for closed hypercubes).
- [ ] Validation messages include: the failing fact, the violated hypercube, and the specific constraint breached.

#### Instance Document Authoring

**Create and Edit Instances**
_Acceptance criteria:_
- [ ] A new blank instance document can be created, pre-populated with correct namespace declarations and `schemaRef` pointing to the loaded taxonomy entry point.
- [ ] Facts (items) can be added with concept, value, entity identifier, period, and dimensional context.
- [ ] Facts can be edited and deleted without corrupting the document structure.
- [ ] The instance document can be serialised to valid XBRL 2.1 XML and saved to disk.

**Open Existing Instances**
_Acceptance criteria:_
- [ ] An existing XBRL instance XML file can be opened and its facts displayed in the editor.
- [ ] The taxonomy referenced by `schemaRef` is automatically loaded when opening an instance.
- [ ] Parse errors in the instance file are reported with line/column references.

#### Table Linkbase Rendering (XBRL Table Linkbase 1.0 PWD)

**Table Discovery and Layout Computation**
_Acceptance criteria:_
- [ ] All table definitions (`table:table` elements with their breakdown structures) in the loaded taxonomy are discovered and listed.
- [ ] The processor computes the row/column layout for a selected table according to the Table Linkbase 1.0 PWD layout algorithm (structural nodes, aspect nodes, rule nodes).
- [ ] The rendered layout shows row headers, column headers, and the dimensional/concept coordinates of each cell.

**Table Populated with Instance Data**
_Acceptance criteria:_
- [ ] When an instance document is loaded alongside the taxonomy, each cell in the rendered table is resolved to its matching fact value (if present).
- [ ] Cells with no matching fact are visually distinguished (e.g., shown as empty / greyed).
- [ ] Multiple matching facts for a single cell (duplicate facts) are flagged as an error.

#### Formula Validation (XBRL Formula 1.0 — basic)

**Assertion Evaluation**
_Acceptance criteria:_
- [ ] Value assertions and existence assertions defined in the formula linkbase are evaluated against the loaded instance document.
- [ ] Consistency assertions are evaluated and reported.
- [ ] Each assertion result shows: pass/fail status, the assertion label, the evaluated expression (or human-readable summary), and the involved fact values.
- [ ] Assertions with `@abstract="true"` are not evaluated independently.

#### Conformance Suite Execution

**Self-testing against XBRL.org Conformance Suites**
_Acceptance criteria:_
- [ ] The processor includes a conformance test runner that loads and executes the XBRL 2.1, Dimensions 1.0, Table Linkbase PWD, Formula 1.0, and Generic Labels conformance suites.
- [ ] Test results are reported as pass/fail/error per test case with the relevant error message.
- [ ] The processor achieves a 100% pass rate on all mandatory test cases across all targeted conformance suites at the time of v1 release.

---

### Nice-to-Have — P1 (fast follows post-launch)

- **Calculation linkbase validation:** Evaluate calculation arc weights against reported fact values and surface calculation inconsistencies with the standard XBRL 2.1 calculation algorithm.
- **Multi-language label switching:** A language picker in the UI toolbar that immediately re-renders all concept labels in the selected language across all views.
- **Concept detail panel:** A side panel showing all metadata for a selected concept — data type, period type, balance, all available labels across roles and languages, applicable hypercubes, and presentation hierarchy position.
- **Export table as CSV/XLSX:** Allow a rendered, populated table to be exported to CSV or Excel for downstream analysis.
- **Recent taxonomies / instance files list:** Remember recently opened taxonomy packages and instance files for quick re-access.
- **Dark mode UI theme.**

---

### Future Considerations — P2 (v2 and beyond)

- **Inline XBRL (iXBRL) tagging and rendering** — embedding XBRL tags in HTML documents per the iXBRL 1.1 specification.
- **Taxonomy authoring** — creating and editing taxonomy schemas and linkbases.
- **Regulatory filing submission** — direct submission to EDGAR, ESEF, or EBA portal APIs.
- **Cloud sync and multi-user collaboration** — shared instance editing and taxonomy workspaces.
- **Full formula authoring and debugging** — a formula editor with step-through evaluation.
- **XBRL 2.2 / OIM / xBRL-JSON and xBRL-CSV support** — open information model serialisation formats.
- **Plugin/extension API** — allowing third parties to add custom validators or renderers.

---

## Conformance & Standards Compliance

The application must pass the conformance suites published at specifications.xbrl.org for the following specifications:

| Specification | Conformance Suite Target |
|---|---|
| XBRL 2.1 | XBRL 2.1 Conformance Suite (all required test cases) |
| XBRL Dimensions 1.0 (xDT) | Dimensions 1.0 Conformance Suite (all required test cases) |
| XBRL Table Linkbase 1.0 PWD | Table Linkbase Conformance Suite PWD (all required test cases) |
| XBRL Formula 1.0 | Formula Conformance Suite (value assertion and consistency assertion required test cases) |
| XBRL Generic Labels | Generic Labels Conformance Suite (all required test cases) |
| XBRL Generic Links | Covered under Generic Labels suite |

The conformance suites must be integrated as automated tests that can be run as part of the CI pipeline on every build. Conformance regression is treated as a build-blocking failure.

---

## Success Metrics

### Leading Indicators (measurable within first 4 weeks of release)

- **Conformance suite pass rate:** 100% pass on all targeted XBRL.org mandatory test cases. Measured by the built-in conformance runner on release build.
- **Taxonomy load success rate:** ≥ 95% of all major regulatory taxonomies (EBA, ESMA ESEF, IFRS Foundation, FDIC FFIEC) load without errors in pre-release testing.
- **Table render accuracy:** ≥ 98% of tables in test taxonomy packages render with the correct structural layout as verified against expected output fixtures.
- **User task completion — instance creation workflow:** In structured user testing, ≥ 80% of first-time users (financial reporting background, no prior XBRL tooling experience) can create a valid 5-fact instance document against a provided taxonomy within 20 minutes, unassisted.

### Lagging Indicators (measurable at 60–90 days post-release)

- **Filing error reduction:** Target a ≥ 50% reduction in XBRL validation errors reported at regulatory portal submission compared to prior tool baseline (requires baseline measurement before release).
- **User satisfaction (NPS or CSAT):** Target NPS ≥ 40 or CSAT ≥ 4.0/5.0 in a post-release survey to the initial user cohort.
- **Adoption within reporting team:** ≥ 80% of targeted filing preparers use the tool as their primary XBRL authoring environment within 60 days.
- **Support ticket volume:** Fewer than 5 taxonomy-load or rendering defect tickets per 100 filings prepared.

---

## Open Questions

| # | Question | Owner | Blocking? |
|---|---|---|---|
| 1 | What is the target platform / application type? (Web app, desktop/Electron, or cross-platform desktop framework) The answer affects framework selection, packaging, and offline support. | **Architecture / Engineering** | **Yes — must resolve before sprint 1** |
| 2 | Which specific regulatory taxonomies must pass load testing before v1 release? (e.g., EBA CRD IV, ESMA ESEF 2023, IFRS full taxonomy 2024, SEC US-GAAP 2023) This determines the test taxonomy corpus. | **Product / Reporting team stakeholders** | Yes — needed to define pre-release acceptance criteria |
| 3 | Which Table Linkbase PWD draft is the precise target — there have been multiple public working drafts. Must confirm the specific draft revision and its conformance suite URL to avoid implementing against a superseded draft. | **Engineering / XBRL Standards liaison** | Yes — critical for correct implementation |
| 4 | Does the tool need to function fully offline (no internet access), or can it reach `xbrl.org` and registry URLs for taxonomy resolution? This affects the taxonomy caching and resolution strategy. | **Engineering** | Yes |
| 5 | Are there specific label languages that must be supported at launch? (e.g., English only, or English + German + French for EBA taxonomies) | **Reporting team stakeholders** | No — affects language picker P1 item |
| 6 | What is the expected maximum taxonomy size the tool must handle without performance degradation? (e.g., EBA Taxonomy 3.x has thousands of concepts) Performance targets for load time need to be defined. | **Engineering** | No — but should be agreed before performance testing |
| 7 | Is Formula 1.0 support expected to cover the full formula specification (including custom functions, filter chaining, etc.) or only the most common assertion types (value assertions, existence assertions, consistency assertions)? | **Product / Engineering** | No — v1 scopes to basic assertions, but clarify for conformance suite coverage |

---

## Timeline Considerations

### Hard Deadline
**Q2 2026** (target: end of June 2026). This is approximately 13 weeks from the date of this document.

### Suggested Phasing

Given the Q2 constraint, the following phased approach is recommended to reduce risk:

**Phase 1 — Core Processing Engine (Weeks 1–5)**
Focus: DTS discovery, schema parsing, standard + generic label resolution, basic concept model, dimensional model loading (hypercubes/axes/members). No UI beyond a minimal shell. Conformance tests running in CI for XBRL 2.1 and Dimensions.

**Phase 2 — Instance Authoring + Dimensional Validation (Weeks 5–9)**
Focus: Instance create/open/edit/save, context management, dimensional constraint validation, concept detail view. Conformance tests extended to Generic Labels and Formula (assertions).

**Phase 3 — Table Rendering + Formula Assertions + Polish (Weeks 9–13)**
Focus: Table Linkbase layout computation and rendering, instance fact population in tables, Formula assertion evaluation, full conformance suite run, UI polish, user acceptance testing with filing preparer persona.

### Dependencies
- Conformance suite test data must be sourced and integrated into the CI pipeline by end of Week 2.
- The target regulatory taxonomies (for real-world load testing) must be identified and procured by end of Week 3.
- Application type/platform decision (Open Question #1) must be resolved before Week 1 begins.

---

## Appendix: Referenced Specifications

All specifications are published at [https://specifications.xbrl.org](https://specifications.xbrl.org):

- **XBRL 2.1** — Core specification defining the XBRL processing model, DTS discovery, linkbases, instances, and validation rules.
- **XBRL Dimensions 1.0 (xDT)** — Extension defining dimensional hypercubes, axes, domain-member hierarchies, and dimensional context validation.
- **XBRL Table Linkbase 1.0 (PWD)** — Public Working Draft defining the table linkbase structure for rendering dimensional report layouts as rows/columns. *(Confirm exact PWD revision with XBRL.org.)*
- **XBRL Formula 1.0** — Specification defining formula linkbases, value assertions, existence assertions, consistency assertions, and the filter/variable framework.
- **XBRL Generic Links** — Specification defining the generic linkbase mechanism (`gen:link`, `gen:arc`) as an extensible alternative to standard XLink linkbases.
- **XBRL Generic Labels** — Extension to Generic Links defining generic label arcs and label resource elements (`genlab:label`), enabling label definitions in generic linkbases.
- **Conformance Suites** — Available at https://specifications.xbrl.org for each of the above specifications. The processor must achieve 100% pass on all mandatory test cases in each suite.

## Apendix 2: Colors Convention
Instance reader conventions:
Color	Hex	Meaning
White	white	Applicable, no issue
Very light grey	#F8F8F8	is_applicable=False (abstract row)
Pink/salmon	#FFD0D0	is_duplicate=True — multiple facts in the instance matched this cell's dimensional coordinate
Dark grey	#A8A8A8	is_excluded=True — dimensional constraints forbid this cell
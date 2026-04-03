# BDE XBRL Editor Constitution

## Core Principles

### I. XBRL Standard Compliance First
All XBRL instance creation, editing, and validation must strictly conform to the XBRL 2.1 specification and the applicable XBRL Taxonomy (XBRL Dimensions, inline XBRL where applicable). The abstraction layer built on top of the XBRL processor must never silently deviate from the standard — deviations must be explicit, documented, and justified by BDE-specific requirements.

### II. BDE Taxonomy Abstraction Layer
A dedicated abstraction layer sits between the raw XBRL processor and the application features. This layer encapsulates all BDE-specific taxonomy peculiarities (not publishing taxonomy packages, just plain zips, custom linkbases, special validation rules, BDE reporting dimensions, filing requirements). No BDE-specific logic may leak into the generic XBRL processor layer or into the UI layer directly. For example we must be able to process the validations defined outside of the taxonomy, and most of the table linkbases on BDE taxonomies are using the PWD Table linkbase specification, instead of the final one.

### III. Test-First (NON-NEGOTIABLE)
TDD is mandatory. Tests are written and approved before implementation begins. The Red-Green-Refactor cycle is strictly enforced. Unit tests cover the XBRL processor abstraction layer. Integration tests validate end-to-end flows: taxonomy loading → instance creation/editing → validation → rendering. No feature is considered done without passing tests.

### IV. Layered Architecture (NON-NEGOTIABLE)
The application follows a strict layered architecture:
- **XBRL Processor Core**: raw XBRL engine (third-party or internal), no BDE specifics.
- **BDE Abstraction Layer**: BDE taxonomy customization, special rule handling, filing metadata.
- **Application Services**: orchestration of use cases (create instance, validate, render tables).
- **UI / API Layer**: user interaction, table rendering, report visualization.

Dependencies flow strictly downward — upper layers depend on lower, never the reverse.

### V. Advanced Table Rendering
The table/report visualization is a first-class feature. The rendering engine must faithfully represent BDE taxonomy table linkbase structures, supporting complex header hierarchies, multi-dimensional breakdowns, and cell-level validation feedback. Rendering must be driven by the taxonomy definition, not hardcoded layouts.

### VI. Simplicity and YAGNI
Start with the simplest implementation that satisfies the current requirement. No speculative abstractions, no premature generalization. Complexity must be justified by an existing, concrete requirement. Prefer clarity over cleverness.

## Technology & Stack Constraints

- **Language**: Java 21 (LTS). Use modern Java features (records, sealed classes, pattern matching, virtual threads) where they improve clarity.
- **Build**: Maven — remain consistent across the project.
- **XBRL Processor**: Wrap the chosen XBRL processor behind an interface; no direct coupling to the processor library outside the Core layer.
- **XPATH, XLINK**: use SaxonHE 12.9
- **Validation**: All validation results are typed (structured errors with location, code, severity) — no free-form string errors.
- **Taxonomy Loading**: Taxonomies are loaded once and cached; reloading must be explicit.
- **No external network calls at runtime** unless explicitly required for taxonomy resolution, and those calls must be configurable and mockable in tests.

## Quality Gates & Development Workflow

- Every feature must have a specification (`spec.md`) reviewed before implementation starts.
- All public APIs of the BDE Abstraction Layer must be documented (Javadoc).
- Integration tests must cover: loading a BDE taxonomy, creating a minimal valid instance, running validation, and rendering at least one table.
- No PR is merged with failing tests or unresolved validation errors in the CI pipeline.
- Breaking changes to the BDE Abstraction Layer API require a migration plan and version bump.

## Governance

This Constitution supersedes all other development practices and guidelines. Amendments require:
1. A documented rationale explaining the need for change.
2. Review and approval before merging.
3. A migration plan if the amendment affects existing features or APIs.

All feature specifications, plans, and task files must be consistent with this Constitution. Any conflict between a feature spec and the Constitution is resolved in favor of the Constitution.

**Version**: 1.0.0 | **Ratified**: 2026-03-23 | **Last Amended**: 2026-03-23

# Tasks: XBRL Instance Creation

**Branch**: `002-xbrl-instance-creation`
**Input**: `specs/002-xbrl-instance-creation/` (plan.md, spec.md, data-model.md, contracts/instance-api.md, research.md)
**Generated**: 2026-03-26

**Prerequisite**: Feature 001 (`bde_xbrl_editor.taxonomy`) fully implemented and importable.

---

## Format: `[ID] [P?] [Story?] Description — file path`

- **[P]**: Parallelizable with other [P] tasks in the same phase
- **[US1–US4]**: Maps to wizard steps / user stories from spec.md

---

## Phase 1: Setup

**Purpose**: Create the `instance/` package skeleton and wizard UI directory structure.

- [X] T001 Create `src/bde_xbrl_editor/instance/` package: `__init__.py` stub + empty `models.py`, `factory.py`, `serializer.py`, `context_builder.py`, `constants.py` — `src/bde_xbrl_editor/instance/`
- [X] T002 [P] Create wizard UI sub-package skeleton: `src/bde_xbrl_editor/ui/widgets/instance_creation_wizard/__init__.py` and empty stubs `wizard.py`, `page_entity_period.py`, `page_table_selection.py`, `page_dimensional.py`, `page_save.py` — `src/bde_xbrl_editor/ui/widgets/instance_creation_wizard/`
- [X] T003 [P] Create test directory stubs: `tests/unit/instance/` and `tests/integration/instance/` (empty `__init__.py` files) — test directories

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Instance model types, error hierarchy, and namespace constants needed by all four user story phases.

- [X] T004 Implement namespace constants: `XBRLI_NS`, `LINK_NS`, `XLINK_NS`, `XBRLDI_NS`, `ISO4217_NS`, `FILING_IND_NS`, `FILING_IND_PFX`, `XBRLDI_CONTEXT_ELEMENT` — `src/bde_xbrl_editor/instance/constants.py`
- [X] T005 [P] Implement `ContextId` (`str` alias) and `UnitId` (`str` alias) type aliases — `src/bde_xbrl_editor/instance/models.py`
- [X] T006 [P] Implement `ReportingEntity` dataclass (identifier, scheme) with `__post_init__` validation (non-empty identifier, non-empty scheme) — `src/bde_xbrl_editor/instance/models.py`
- [X] T007 [P] Implement `ReportingPeriod` dataclass (period_type, instant_date, start_date, end_date) with `__post_init__` validation (instant requires instant_date; duration requires start_date, end_date, end≥start) — `src/bde_xbrl_editor/instance/models.py`
- [X] T008 [P] Implement `DimensionalConfiguration` dataclass (table_id, dimension_assignments: `dict[QName, QName]`) — `src/bde_xbrl_editor/instance/models.py`
- [X] T009 [P] Implement `XbrlContext` dataclass (context_id, entity, period, dimensions, context_element) — `src/bde_xbrl_editor/instance/models.py`
- [X] T010 [P] Implement `XbrlUnit` dataclass (unit_id, measure_uri) — `src/bde_xbrl_editor/instance/models.py`
- [X] T011 [P] Implement `FilingIndicator` dataclass (template_id, filed, context_ref) — `src/bde_xbrl_editor/instance/models.py`
- [X] T012 [P] Implement `Fact` dataclass (concept: QName, context_ref, unit_ref, value, decimals, precision) — `src/bde_xbrl_editor/instance/models.py`
- [X] T013 [P] Implement `XbrlInstance` mutable dataclass with all fields from data-model.md including `_dirty=False`, `source_path=None`, `has_unsaved_changes` property; mutation methods `add_fact()`, `update_fact()`, `remove_fact()`, `mark_saved()` (set source_path + clear dirty) — `src/bde_xbrl_editor/instance/models.py`
- [X] T014 [P] Implement error hierarchy: `InstanceCreationError` base, `InvalidReportingPeriodError`, `InvalidEntityIdentifierError`, `MissingDimensionValueError`, `InvalidDimensionMemberError`, `InstanceSaveError` — all with typed fields per contracts/instance-api.md — `src/bde_xbrl_editor/instance/models.py`

---

## Phase 3: User Story 1 — Create a New Empty XBRL Instance

**Goal**: Given a loaded taxonomy, entity identifier, and reporting period, `InstanceFactory.create()` produces a valid `XbrlInstance` with correct schemaRef, entity, period, and an empty facts list — with no manual namespace or context configuration needed.

**Independent test criteria**: Call `InstanceFactory(taxonomy).create(entity, period, ["T1"], {})` on BDE sample taxonomy → returns `XbrlInstance` with `schema_ref_href` matching taxonomy entry point, `has_unsaved_changes=True`, `facts=[]`, at least one `XbrlContext` in `contexts`.

- [X] T015 [US1] Implement `context_builder.py`: `generate_context_id(entity, period, dimensions) -> ContextId` using SHA-256 hash of canonical tuple → `"ctx_<8-hex>"`; `build_filing_indicator_context(entity, period) -> XbrlContext`; `build_dimensional_context(entity, period, dimensions, context_element) -> XbrlContext`; `deduplicate_contexts(contexts) -> dict[ContextId, XbrlContext]` — `src/bde_xbrl_editor/instance/context_builder.py`
- [X] T016 [P] [US1] Implement `unit_prepopulation(taxonomy, table_ids) -> dict[UnitId, XbrlUnit]`: collect all numeric concept types from selected tables' X/Y breakdown leaf nodes; map XBRL numeric types to ISO 4217 units or `xbrli:pure`; deduplicate units by measure URI — `src/bde_xbrl_editor/instance/factory.py`
- [X] T017 [US1] Implement `InstanceFactory.create()`: validate entity+period against taxonomy, validate `included_table_ids` exist in taxonomy, call context_builder to generate all contexts, call unit_prepopulation, build `FilingIndicator` list, assemble `XbrlInstance` with `_dirty=True`, `source_path=None`, `facts=[]` — `src/bde_xbrl_editor/instance/factory.py`
- [X] T018 [P] [US1] Implement `instance/__init__.py` re-exports: `XbrlInstance`, `InstanceFactory`, `InstanceSerializer`, `ReportingEntity`, `ReportingPeriod`, `FilingIndicator`, `DimensionalConfiguration`, `XbrlContext`, `XbrlUnit`, `Fact`, `ContextId`, `UnitId`, all error types — `src/bde_xbrl_editor/instance/__init__.py`
- [X] T019 [P] [US1] Implement wizard page 1 (`QWizardPage`): two form fields — entity identifier `QLineEdit` (required, BDE code format) and reporting period date picker(s) (`QDateEdit` for instant; two `QDateEdit` for duration; period type determined from taxonomy); `validatePage()` calls `ReportingEntity`/`ReportingPeriod` constructors and shows inline error on `QLabel` if validation raises — `src/bde_xbrl_editor/ui/widgets/instance_creation_wizard/page_entity_period.py`
- [X] T020 [P] [US1] Write unit tests: `context_builder.py` — SHA-256 determinism (same inputs → same ID), context deduplication, filing-indicator context always present — `tests/unit/instance/test_context_builder.py`
- [X] T021 [P] [US1] Write unit tests: `InstanceFactory.create()` — invalid period raises `InvalidReportingPeriodError`; missing entity raises `InvalidEntityIdentifierError`; valid inputs produce `XbrlInstance` with correct entity/period/contexts/units — `tests/unit/instance/test_factory.py`

---

## Phase 4: User Story 2 — Select Which Tables to Include

**Goal**: After entity/period are set, the user sees all taxonomy tables with checkboxes; selecting a subset updates the wizard's table scope; zero-table selection is blocked.

**Independent test criteria**: Wizard page 2 populated with BDE sample taxonomy's table list → check 3 tables → `validatePage()` returns True; uncheck all → `validatePage()` returns False.

- [X] T022 [US2] Implement wizard page 2 (`QWizardPage`): `QListWidget` (checkable items) populated from `taxonomy.tables` with table ID + label; select-all/deselect-all helper buttons; `validatePage()` returns False (with inline error) when no tables checked; stores selected table IDs in wizard field `"selected_table_ids"` — `src/bde_xbrl_editor/ui/widgets/instance_creation_wizard/page_table_selection.py`
- [X] T023 [P] [US2] Extend `InstanceFactory.create()` to raise `InstanceCreationError("No tables selected")` if `included_table_ids` is empty (FR-005 guard) — `src/bde_xbrl_editor/instance/factory.py`
- [X] T024 [P] [US2] Write unit tests: `InstanceFactory.create()` with empty `included_table_ids` raises; with invalid table IDs raises; with valid subset succeeds — `tests/unit/instance/test_factory.py` (extend)

---

## Phase 5: User Story 3 — Set Dimensional Context for Each Table

**Goal**: For each selected table that has Z-axis dimensions, the user assigns a value to each mandatory dimension via a dropdown; missing mandatory dimensions block progression.

**Independent test criteria**: Wizard page 3 shows dimension dropdowns for a table with 2 mandatory Z-axis dimensions; fill both → `validatePage()` True; leave one empty → `validatePage()` False.

- [X] T025 [US3] Implement wizard page 3 (`QWizardPage`): for each selected table, display a group box with one `QComboBox` per Z-axis dimension (populated from `DimensionModel.members` with labels from `LabelResolver`); mandatory dimensions (no default member) marked with `*`; `validatePage()` calls `InstanceFactory` dimensional validation logic for each table; shows inline error per-table on failure — `src/bde_xbrl_editor/ui/widgets/instance_creation_wizard/page_dimensional.py`
- [X] T026 [P] [US3] Extend `InstanceFactory.create()` to validate dimensional configs: `MissingDimensionValueError` if mandatory dim has no value; `InvalidDimensionMemberError` if assigned member not in `DimensionModel.members` list — `src/bde_xbrl_editor/instance/factory.py`
- [X] T027 [P] [US3] Write unit tests: `InstanceFactory.create()` — mandatory dimension missing raises `MissingDimensionValueError`; invalid member raises `InvalidDimensionMemberError`; valid config generates correct context with `xbrldi:explicitMember` entries — `tests/unit/instance/test_factory.py` (extend)

---

## Phase 6: User Story 4 — Save the New Instance

**Goal**: After wizard completion, the user picks a filesystem path and saves the configured instance as well-formed XBRL 2.1 XML; file-overwrite confirmation prevents accidental data loss.

**Independent test criteria**: `InstanceSerializer().to_xml(instance)` returns bytes that parse as well-formed XML with correct `xbrli:xbrl` root, `link:schemaRef`, at least one `xbrli:context`, and Eurofiling `filingIndicators` wrapper.

- [X] T028 [US4] Implement `InstanceSerializer.to_xml()`: build lxml `etree.Element("xbrli:xbrl")` with `nsmap` including all required namespace prefixes; append `link:schemaRef`, all `xbrli:context` elements (in canonical order), all `xbrli:unit` elements, `ef-find:fIndicators` wrapper with `ef-find:filingIndicator` children, and all `Fact` elements; return `etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")` — `src/bde_xbrl_editor/instance/serializer.py`
- [X] T029 [P] [US4] Implement `InstanceSerializer.save()`: call `to_xml()`, write bytes to path (binary mode), catch `OSError` → raise `InstanceSaveError`; call `instance.mark_saved(path)` on success — `src/bde_xbrl_editor/instance/serializer.py`
- [X] T030 [P] [US4] Implement wizard page 4 (`QWizardPage`): `QLineEdit` + "Browse…" `QPushButton` for file path (`QFileDialog.getSaveFileName` with filter `"XBRL files (*.xbrl *.xml)"`); if chosen path exists, show `QMessageBox` confirmation before overwriting; `validatePage()` returns False if path is empty; on `QWizard.accept`, call `InstanceSerializer().save(instance, path)` and show error dialog on `InstanceSaveError` — `src/bde_xbrl_editor/ui/widgets/instance_creation_wizard/page_save.py`
- [X] T031 [US4] Implement `InstanceCreationWizard` (`QWizard` subclass): add pages in order (entity_period → table_selection → dimensional → save); pass `taxonomy` to each page on construction; implement `created_instance: XbrlInstance | None` property that returns the assembled instance after `accepted` or `None` if cancelled; wire `InstanceFactory.create()` call in `page_save.py`'s `validatePage()` — `src/bde_xbrl_editor/ui/widgets/instance_creation_wizard/wizard.py`
- [X] T032 [P] [US4] Write unit tests: `InstanceSerializer.to_xml()` — output is well-formed XML (parse with `lxml.etree.fromstring`), root is `xbrli:xbrl`, `link:schemaRef` present, contexts match `instance.contexts`, filing indicators present, all namespace prefixes declared — `tests/unit/instance/test_serializer.py`
- [X] T033 [P] [US4] Write unit tests: `XbrlInstance.has_unsaved_changes` — True after `InstanceFactory.create()`; False after `mark_saved()`; True after `add_fact()`; `XbrlInstance.mark_saved()` sets `source_path` — `tests/unit/instance/test_models.py`

---

## Phase 7: Polish and Cross-Cutting Concerns

**Purpose**: Wire wizard into main window, end-to-end round-trip test, API surface verification.

- [X] T034 Update `src/bde_xbrl_editor/ui/main_window.py`: add File → New Instance menu action (enabled only when a taxonomy is loaded); on trigger open `InstanceCreationWizard`; on accepted, store `created_instance` in application state and log/display the new instance path in the status bar — `src/bde_xbrl_editor/ui/main_window.py`
- [X] T035 [P] Write integration test: call `InstanceFactory.create()` with BDE sample taxonomy + entity + period + selected tables + dimension configs → call `InstanceSerializer.save()` → reopen the saved file with `lxml.etree.parse()` → verify schemaRef matches taxonomy path, contexts present, filing indicators list matches `included_table_ids`, facts list empty — `tests/integration/instance/test_instance_roundtrip.py`
- [X] T036 [P] Verify `instance/__init__.py` re-exports match `contracts/instance-api.md` exactly; ensure no internal sub-module is imported directly from outside the `instance/` package — `src/bde_xbrl_editor/instance/__init__.py`

---

## Dependencies Summary

```
Phase 1 (Setup) ──must complete──▶ Phase 2 (Foundational)
Phase 2 (Foundational) ──must complete──▶ Phases 3, 4, 5, 6
Phase 3 (US1) ──must complete──▶ Phase 4 (US2) — wizard pages build sequentially
Phase 4 (US2) ──must complete──▶ Phase 5 (US3)
Phase 5 (US3) ──must complete──▶ Phase 6 (US4) — serializer needs fully configured instance
Phase 3 + Phase 6 ──complete──▶ Phase 7 (Polish)
```

**Within Phase 3 (US1)**: T015 (context_builder) must complete before T017 (InstanceFactory assembly); T016 (unit pre-population) and T019 (wizard page 1) can be done in parallel with T017.

**Within Phase 6 (US4)**: T028 (to_xml) must complete before T029 (save) and T030 (wizard page 4); T031 (wizard root) requires T028–T030.

---

## Parallel Execution Examples

### Phase 2 — all tasks in parallel after T004

T005 + T006 + T007 + T008 + T009 + T010 + T011 + T012 + T013 + T014 (all different model types, same file — coordinate to avoid conflicts, or batch per developer)

### Phase 3 — after T015

T016 + T019 + T020 + T021 run in parallel with T017 background work (different files)

### Phase 6 — after T028

T029 + T030 + T032 + T033 run in parallel; T031 (wizard root) waits for T028–T030

---

## Implementation Strategy (MVP Scope)

**MVP**: Phases 1–3 only → delivers a working `InstanceFactory.create()` with entity+period validation and correct context/unit generation. No UI wizard, no file save. Allows Feature 004 (editing) and Feature 005 (validation) to begin development using programmatically-created instances.

**Full v1**: All phases (1–7) → complete wizard UI + serialization.

---

## Task Count Summary

| Phase | Tasks | Parallelizable |
|-------|-------|----------------|
| Phase 1: Setup | 3 | 2 |
| Phase 2: Foundational | 11 | 10 |
| Phase 3: US1 (Create) | 7 | 5 |
| Phase 4: US2 (Tables) | 3 | 2 |
| Phase 5: US3 (Dimensions) | 3 | 2 |
| Phase 6: US4 (Save) | 6 | 4 |
| Phase 7: Polish | 3 | 2 |
| **Total** | **36** | **27** |

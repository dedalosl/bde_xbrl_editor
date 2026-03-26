# Tasks: Instance Editing

**Input**: Design documents from `specs/004-instance-editing/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1–US5)
- Exact file paths in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new file stubs — no logic yet

- [ ] T001 Create `src/bde_xbrl_editor/instance/parser.py` (empty file with module docstring)
- [ ] T002 [P] Create `src/bde_xbrl_editor/instance/editor.py` (empty file with module docstring)
- [ ] T003 [P] Create `src/bde_xbrl_editor/instance/validator.py` (empty file with module docstring)
- [ ] T004 [P] Create `src/bde_xbrl_editor/ui/widgets/cell_edit_delegate.py` (empty file with module docstring)
- [ ] T005 [P] Create `src/bde_xbrl_editor/ui/widgets/instance_info_panel.py` (empty file with module docstring)
- [ ] T006 [P] Create test files: `tests/unit/instance/test_parser.py`, `tests/unit/instance/test_editor.py`, `tests/unit/instance/test_validator.py`, `tests/integration/instance/test_edit_roundtrip.py` (each with `__init__.py` where missing)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Extend the Feature 002 data model with the new fields and error types that every US depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Add `OrphanedFact` and `EditOperation` dataclasses to `src/bde_xbrl_editor/instance/models.py` — `OrphanedFact` fields: concept_qname_str, context_ref, unit_ref, value, decimals, raw_element_xml; `EditOperation` fields: operation_type, fact_index, previous_value, new_value, concept, context_ref, timestamp
- [ ] T008 Extend `XbrlInstance` in `src/bde_xbrl_editor/instance/models.py` with two new fields: `orphaned_facts: list[OrphanedFact]` and `edit_history: list[EditOperation]` (both default to empty list)
- [ ] T009 [P] Add error classes to `src/bde_xbrl_editor/instance/errors.py` (or models.py): `InstanceParseError` (.path, .reason), `TaxonomyResolutionError` (.schema_ref_href extends InstanceParseError), `DuplicateFactError` (.concept, .context_ref), `InvalidFactValueError` (.concept, .expected_type, .provided_value)

**Checkpoint**: Extended models and error types ready — user story phases can now proceed

---

## Phase 3: User Story 1 — Open an Existing XBRL Instance and Bind It to Its Taxonomy (Priority: P1) 🎯 MVP

**Goal**: Parse an existing XBRL instance file, resolve and load its bound taxonomy, and present instance metadata (entity, period, filing indicators, table list) in the UI.

**Independent Test**: Open an existing BDE XBRL instance; verify that `InstanceParser.load()` returns a populated `XbrlInstance` with correct contexts, units, facts, and `instance._dirty == False`; verify `OrphanedFact` list contains only facts with concepts absent from the taxonomy.

- [ ] T010 [US1] Implement `InstanceParser.__init__(taxonomy_loader, manual_taxonomy_resolver)` in `src/bde_xbrl_editor/instance/parser.py` — stores taxonomy_loader and optional callable; stateless parser (same instance reusable for multiple files)
- [ ] T011 [US1] Implement `InstanceParser.load()` stages 1–2 in `src/bde_xbrl_editor/instance/parser.py` — parse XML root; validate `xbrli:xbrl` namespace; extract `link:schemaRef/@xlink:href`; resolve path (relative → `instance_dir/href`; absolute; fallback to `manual_taxonomy_resolver`); call `TaxonomyLoader.load()`; raise `InstanceParseError` / `TaxonomyResolutionError` on failure
- [ ] T012 [US1] Implement `InstanceParser.load()` stages 3–4 in `src/bde_xbrl_editor/instance/parser.py` — parse `xbrli:context` elements → `XbrlContext`; parse `xbrli:unit` elements → `XbrlUnit`
- [ ] T013 [US1] Implement `InstanceParser.load()` stages 5–7 in `src/bde_xbrl_editor/instance/parser.py` — parse `ef-find:filingIndicator` elements → `FilingIndicator`; iterate remaining child elements as facts; concepts in taxonomy → `Fact`; concepts not in taxonomy → `OrphanedFact`; populate `XbrlInstance`; set `_dirty = False`, `source_path = path`
- [ ] T014 [US1] Implement `InstanceInfoPanel` (`QFrame`) in `src/bde_xbrl_editor/ui/widgets/instance_info_panel.py` — displays entity name, reporting period, filing indicators list; table list (`QListWidget`) populated from `XbrlInstance`; emits `table_selected(TableDefinitionPWD)` signal when user selects a table
- [ ] T015 [US1] Add File→Open action to `src/bde_xbrl_editor/ui/main_window.py` — `QFileDialog` for `.xbrl` / `.xml`; call `InstanceParser.load()`; handle `InstanceParseError` / `TaxonomyResolutionError` with `QMessageBox`; if orphaned facts present, show informational dialog; mount `InstanceInfoPanel` in sidebar; reset any open `XbrlTableView`
- [ ] T016 [US1] Unit test: `InstanceParser.load()` — parse BDE sample instance; verify context count, unit count, fact count, `_dirty == False`, `source_path` set, orphaned_facts list in `tests/unit/instance/test_parser.py`

---

## Phase 4: User Story 2 — Visualise Instance Data in the Advanced Table Viewer (Priority: P2)

**Goal**: Connect the open instance to the table renderer so fact values appear in the correct cells when the user selects a table from `InstanceInfoPanel`.

**Independent Test**: Open an instance; select a table; verify `XbrlTableView` body cells contain the correct fact values (via `TableBodyModel.data(Qt.DisplayRole)`) for cells whose coordinates match known facts; verify empty cells for coordinates with no matching fact.

- [ ] T017 [US2] Wire `InstanceInfoPanel.table_selected` signal in `src/bde_xbrl_editor/ui/main_window.py` — on signal, call `XbrlTableView.set_table(table, taxonomy, instance)` to render selected table with instance data
- [ ] T018 [US2] Integration test: open BDE sample instance → select a table → verify rendered cell values match instance facts; verify Z-axis navigation shows per-slice facts in `tests/integration/instance/test_edit_roundtrip.py`

---

## Phase 5: User Story 3 — Edit Fact Values Directly in the Table (Priority: P3)

**Goal**: Enable inline cell editing in the rendered table with type-appropriate editors, XBRL type validation, and routing edits through `InstanceEditor`.

**Independent Test**: Programmatically trigger `CellEditDelegate.setModelData()` with a valid value for a monetary cell; verify `InstanceEditor.update_fact()` is called with the normalised canonical value and `instance._dirty == True`; trigger with an invalid value and verify `(False, message)` is returned without mutating the instance.

- [ ] T019 [US3] Implement `XbrlTypeValidator` in `src/bde_xbrl_editor/instance/validator.py` — `validate(value, concept) -> tuple[bool, str]` and `normalise(value, concept) -> str`; cover 6 types: monetary (decimal precision, "." separator), decimal, integer, date (YYYY-MM-DD), boolean (true/false/1/0 → true/false), string (always valid); never raises; fallback (True, "") for unknown types
- [ ] T020 [US3] Implement `InstanceEditor` in `src/bde_xbrl_editor/instance/editor.py` — `__init__(instance)`; `add_fact()`, `update_fact()`, `remove_fact()`, `mark_saved()`; each mutating method sets `instance._dirty = True` and emits `changes_made` Signal; `add_fact()` raises `DuplicateFactError`; `update_fact()` raises `InvalidFactValueError`
- [ ] T021 [US3] Implement `CellEditDelegate.createEditor()` in `src/bde_xbrl_editor/ui/widgets/cell_edit_delegate.py` — returns `QLineEdit` for monetary/decimal/integer/string; `QDateEdit` (YYYY-MM-DD) for date; `QComboBox(["true","false"])` for boolean; resolves concept type via `TaxonomyStructure`
- [ ] T022 [US3] Implement `CellEditDelegate.setEditorData()` and `CellEditDelegate.updateEditorGeometry()` in `src/bde_xbrl_editor/ui/widgets/cell_edit_delegate.py` — `setEditorData` populates editor from `Qt.UserRole` (raw fact value or ""); `updateEditorGeometry` positions editor exactly over cell rect
- [ ] T023 [US3] Implement `CellEditDelegate.setModelData()` in `src/bde_xbrl_editor/ui/widgets/cell_edit_delegate.py` — validate via `XbrlTypeValidator.validate()`; if invalid → apply red border style + `QToolTip` + `setFocus()` (keep editor open); if valid → call `XbrlTypeValidator.normalise()`, then `InstanceEditor.update_fact()` or `InstanceEditor.add_fact()` for empty cells, then `XbrlTableView.refresh_instance()`; handle empty submission → `InstanceEditor.remove_fact()`
- [ ] T024 [US3] Implement `CellEditDelegate.eventFilter()` in `src/bde_xbrl_editor/ui/widgets/cell_edit_delegate.py` — intercept `QEvent.FocusOut` when editor holds invalid input; re-focus editor to prevent commit
- [ ] T025 [US3] Wire `CellEditDelegate` onto `XbrlTableView` body `QTableView` in `src/bde_xbrl_editor/ui/main_window.py` — instantiate `CellEditDelegate(taxonomy, editor, table_view.active_layout)` after `set_table()` and call `body_table_view.setItemDelegate()`; update delegate's `table_layout` reference on Z-axis change
- [ ] T026 [US3] Unit test: `XbrlTypeValidator` — all 6 XBRL types; Spanish locale normalisation (thousands sep, decimal comma); unknown type fallback in `tests/unit/instance/test_validator.py`
- [ ] T027 [US3] Unit test: `InstanceEditor` — add_fact sets dirty, update_fact sets dirty, remove_fact sets dirty, mark_saved clears dirty; `DuplicateFactError` on duplicate add in `tests/unit/instance/test_editor.py`

---

## Phase 6: User Story 4 — Save the Edited Instance (Priority: P4)

**Goal**: Write the in-memory instance (including orphaned facts) to an XBRL 2.1 XML file; support both Save (overwrite) and Save As (new path); preserve xs:decimal precision.

**Independent Test**: Edit facts in a loaded instance; call `InstanceSerializer.save(new_path)`; parse the saved file with `InstanceParser`; verify all edited values appear unchanged; verify orphaned facts are present in the output XML.

- [ ] T028 [US4] Update `InstanceSerializer.save()` in `src/bde_xbrl_editor/instance/serializer.py` — after writing all known facts, append each `OrphanedFact.raw_element_xml` bytes in original document order; call `editor.mark_saved(path)` on success
- [ ] T029 [US4] Implement File→Save action in `src/bde_xbrl_editor/ui/main_window.py` — if `instance.source_path` is set, save to that path; otherwise fall through to Save As; handle `PermissionError` / `OSError` with `QMessageBox`
- [ ] T030 [US4] Implement File→Save As action in `src/bde_xbrl_editor/ui/main_window.py` — `QFileDialog` for save path; if selected path already exists and is not `instance.source_path`, show overwrite-confirmation `QMessageBox`; proceed with save on confirm
- [ ] T031 [US4] Unit test: `InstanceSerializer` orphaned facts round-trip — save instance with orphaned facts; parse saved file; verify orphaned facts XML is byte-for-byte identical to original in `tests/unit/instance/test_serializer.py`
- [ ] T032 [US4] Integration test: `InstanceParser.load()` → edit 3 facts → `InstanceSerializer.save()` → `InstanceParser.load()` again → verify all edited values; verify xs:decimal precision unchanged; verify orphaned facts preserved in `tests/integration/instance/test_edit_roundtrip.py`

---

## Phase 7: User Story 5 — Track Unsaved Changes and Prevent Accidental Data Loss (Priority: P5)

**Goal**: Maintain a visible dirty-state indicator in the window title; present Save/Discard/Cancel prompt before any action that would lose unsaved edits.

**Independent Test**: Edit a cell to set `_dirty = True`; call `main_window.close()`; verify `QMessageBox` appears with Save/Discard/Cancel; choose Discard and verify window closes without save; choose Cancel and verify window remains open.

- [ ] T033 [US5] Connect `InstanceEditor.changes_made` signal to `setWindowModified(True)` in `src/bde_xbrl_editor/ui/main_window.py` — window title must follow Qt `[*]` pattern (e.g., `"BDE XBRL Editor — filename.xbrl[*]"`); title reverts to unmodified state after `mark_saved()`
- [ ] T034 [US5] Implement `closeEvent()` guard in `src/bde_xbrl_editor/ui/main_window.py` — if `instance` is open and `instance.has_unsaved_changes`, show `QMessageBox(Save | Discard | Cancel)`; Save → call save action; Discard → `event.accept()`; Cancel → `event.ignore()`; no prompt if instance is clean
- [ ] T035 [US5] Implement open-new-instance guard in `src/bde_xbrl_editor/ui/main_window.py` — before launching the File→Open dialog, check for unsaved changes and show same Save/Discard/Cancel prompt; proceed only on Save or Discard; cancel the open action on Cancel

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Public API exports and final wiring

- [ ] T036 [P] Update `src/bde_xbrl_editor/instance/__init__.py` re-exports: add `InstanceParser`, `InstanceEditor`, `XbrlTypeValidator`, `OrphanedFact`, `EditOperation`, `InstanceParseError`, `TaxonomyResolutionError`, `DuplicateFactError`, `InvalidFactValueError`

---

## Dependencies

```
Phase 1 (T001–T006) → Phase 2 (T007–T009) → Phase 3/US1 (T010–T016) → Phase 4/US2 (T017–T018)
                                                                       → Phase 5/US3 (T019–T027)
                                                                                       ↓
                                                                       Phase 6/US4 (T028–T032)
                                                                                       ↓
                                                                       Phase 7/US5 (T033–T035)
                                                                                       ↓
                                                                       Phase 8 (T036)
```

**Key sequential spines**:
- `T011–T013` (parser stages) → `T016` (parser unit test) → `T018` (integration test)
- `T019` (XbrlTypeValidator) + `T020` (InstanceEditor) → `T021–T024` (CellEditDelegate) → `T025` (wire delegate)
- `T028` (serializer orphan update) + `T029–T030` (save actions) → `T032` (round-trip integration test)

**US3, US4, US5 form a sequential chain** — editing must work before saving, saving before unsaved-change tracking makes sense.

---

## Parallel Execution Examples

**Within Phase 1**:
```
T001 (parser.py) ─┐
T002 (editor.py) ─┤
T003 (validator) ─┤→ all in parallel (different files)
T004 (delegate)  ─┤
T005 (info panel)─┤
T006 (test files)─┘
```

**Within Phase 5/US3**:
```
T019 (XbrlTypeValidator) ─┐
T020 (InstanceEditor)    ─┘→ T021 → T022 → T023 → T024 → T025
```

---

## Implementation Strategy

**MVP** = Phases 1–3 + Phase 4 (T001–T018): Open instance → view in table renderer. Unblocks Feature 005 (validation) and Feature 006 (conformance runner) which both need a loadable `XbrlInstance`.

**Increment 2** = Phase 5 (T019–T027): Inline cell editing with type validation. The core editing interaction.

**Increment 3** = Phase 6 (T028–T032): Save to file. Makes editing persistent.

**Full delivery** = Phase 7 (T033–T035): Dirty-state tracking and close guard.

**Phase 8** (T036): Clean up public exports.

---

## Summary

| Phase | User Story | Tasks | Parallelizable |
|-------|-----------|-------|----------------|
| 1: Setup | — | T001–T006 (6) | T002–T006 all [P] |
| 2: Foundational | — | T007–T009 (3) | T009 [P] |
| 3: US1 — Open Instance | P1 🎯 MVP | T010–T016 (7) | — |
| 4: US2 — Visualise Data | P2 | T017–T018 (2) | — |
| 5: US3 — Edit Facts | P3 | T019–T027 (9) | — |
| 6: US4 — Save | P4 | T028–T032 (5) | — |
| 7: US5 — Dirty Tracking | P5 | T033–T035 (3) | — |
| 8: Polish | — | T036 (1) | T036 [P] |
| **Total** | | **36 tasks** | |

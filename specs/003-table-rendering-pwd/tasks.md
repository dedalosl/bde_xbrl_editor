# Tasks: Table Rendering — PWD Table Linkbase Viewer

**Input**: Design documents from `specs/003-table-rendering-pwd/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths in all descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create package skeleton — no logic yet

- [ ] T001 Create `src/bde_xbrl_editor/table_renderer/__init__.py` (empty re-export stub)
- [ ] T002 [P] Create `src/bde_xbrl_editor/table_renderer/models.py` (empty file with module docstring)
- [ ] T003 [P] Create `src/bde_xbrl_editor/table_renderer/errors.py` (empty file with module docstring)
- [ ] T004 [P] Create `src/bde_xbrl_editor/table_renderer/layout_engine.py` (empty file with module docstring)
- [ ] T005 [P] Create `src/bde_xbrl_editor/table_renderer/fact_mapper.py` (empty file with module docstring)
- [ ] T006 [P] Create `src/bde_xbrl_editor/table_renderer/fact_formatter.py` (empty file with module docstring)
- [ ] T007 [P] Create `src/bde_xbrl_editor/ui/widgets/xbrl_table_view.py` (empty file with module docstring)
- [ ] T008 [P] Create `src/bde_xbrl_editor/ui/widgets/table_body_model.py` (empty file with module docstring)
- [ ] T009 [P] Create `src/bde_xbrl_editor/ui/widgets/column_header.py` (empty file with module docstring)
- [ ] T010 [P] Create `src/bde_xbrl_editor/ui/widgets/row_header.py` (empty file with module docstring)
- [ ] T011 [P] Create `src/bde_xbrl_editor/ui/widgets/z_axis_selector.py` (empty file with module docstring)
- [ ] T012 [P] Create test directories `tests/unit/table_renderer/` and `tests/integration/table_renderer/` with `__init__.py` files

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data models and error types that EVERY component depends on — must be complete before any user story begins

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T013 Implement `HeaderCell`, `HeaderGrid` dataclasses in `src/bde_xbrl_editor/table_renderer/models.py` — fields: label, rc_code, span, level, is_leaf, is_abstract, source_node (HeaderCell); levels, leaf_count, depth (HeaderGrid)
- [ ] T014 [P] Implement `CellCoordinate` dataclass in `src/bde_xbrl_editor/table_renderer/models.py` — fields: concept, explicit_dimensions, period_override, entity_override
- [ ] T015 [P] Implement `BodyCell` dataclass in `src/bde_xbrl_editor/table_renderer/models.py` — fields: row_index, col_index, coordinate, fact_value, fact_decimals, is_duplicate, is_applicable
- [ ] T016 [P] Implement `ZMemberOption` and `FactMatchResult` dataclasses in `src/bde_xbrl_editor/table_renderer/models.py`
- [ ] T017 Implement `ComputedTableLayout` dataclass in `src/bde_xbrl_editor/table_renderer/models.py` — fields: table_id, table_label, column_header, row_header, z_members, active_z_index, body; depends on T013–T016
- [ ] T018 [P] Implement error hierarchy in `src/bde_xbrl_editor/table_renderer/errors.py`: `TableRenderError` (base), `TableLayoutError` (.table_id, .reason), `ZIndexOutOfRangeError` (.table_id, .requested_z, .max_z)

**Checkpoint**: Data models and errors complete — user story phases can now proceed

---

## Phase 3: User Story 1 — Render a BDE Taxonomy Table as a Structured Grid (Priority: P1) 🎯 MVP

**Goal**: Render any BDE taxonomy table (no instance required) as a grid with correct multi-level spanning column and row headers, using only the PWD Table Linkbase definition.

**Independent Test**: Render a known BDE taxonomy table with a synthetic `TableDefinitionPWD` fixture and verify: correct leaf_count (= number of data columns/rows), correct span values on each HeaderCell, correct grid dimensions in the ComputedTableLayout body.

- [ ] T019 [US1] Implement DFS traversal for X-axis `HeaderGrid` computation in `src/bde_xbrl_editor/table_renderer/layout_engine.py` — leaf index assignment, span = descendant leaf count, level depth
- [ ] T020 [US1] Implement DFS traversal for Y-axis `HeaderGrid` computation in `src/bde_xbrl_editor/table_renderer/layout_engine.py` — symmetric to X-axis
- [ ] T021 [US1] Implement Z-axis member list extraction (builds `list[ZMemberOption]`) in `src/bde_xbrl_editor/table_renderer/layout_engine.py`
- [ ] T022 [US1] Implement body cell grid construction in `src/bde_xbrl_editor/table_renderer/layout_engine.py` — merge aspect constraints from X-leaf + Y-leaf + Z-member into `CellCoordinate`; produce `body[row][col]` grid with `fact_value=None`
- [ ] T023 [US1] Implement `TableLayoutEngine.__init__()` and `TableLayoutEngine.compute()` orchestration in `src/bde_xbrl_editor/table_renderer/layout_engine.py` — calls T019–T022 in order; raises `TableLayoutError` on broken definition; raises `ZIndexOutOfRangeError` on out-of-range z_index
- [ ] T024 [US1] Implement `MultiLevelColumnHeader` (`QHeaderView` subclass) with `paintSection()` spanning paint logic in `src/bde_xbrl_editor/ui/widgets/column_header.py` — pixel x-offset from cumulative leaf widths; rect = span × section_width; centred label; `set_header_grid()` and `sizeHint()`
- [ ] T025 [P] [US1] Implement `MultiLevelRowHeader` (`QHeaderView` subclass) with `paintSection()` for Y-axis in `src/bde_xbrl_editor/ui/widgets/row_header.py` — symmetric to MultiLevelColumnHeader
- [ ] T026 [US1] Implement `TableBodyModel` (`QAbstractTableModel`) in `src/bde_xbrl_editor/ui/widgets/table_body_model.py` — `rowCount()`, `columnCount()`, `data()` for `DisplayRole` (empty string, no facts yet) and `UserRole` (raw fact_value or None)
- [ ] T027 [US1] Implement `XbrlTableView` (`QFrame`) two-`QTableView` frozen-pane scaffold in `src/bde_xbrl_editor/ui/widgets/xbrl_table_view.py` — body QTableView + synchronised horizontal/vertical scrollbars; MultiLevelColumnHeader + MultiLevelRowHeader mounted; placeholder ZAxisSelector area
- [ ] T028 [US1] Implement `XbrlTableView.set_table()` and `XbrlTableView.clear()` in `src/bde_xbrl_editor/ui/widgets/xbrl_table_view.py` — calls `TableLayoutEngine.compute()`, installs resulting `ComputedTableLayout` into sub-widgets, resets to z_index=0
- [ ] T029 [US1] Unit test: DFS layout algorithm — verify leaf_count, span values, grid dimensions for a synthetic two-level X-axis and two-level Y-axis in `tests/unit/table_renderer/test_layout_engine.py`
- [ ] T030 [P] [US1] Integration test: BDE sample taxonomy table → `ComputedTableLayout` — verify column_header.leaf_count, row_header.leaf_count, body grid shape in `tests/integration/table_renderer/test_bde_table_render.py`

---

## Phase 4: User Story 2 — Navigate and Select the Filter-Axis (Z-Axis) Context (Priority: P2)

**Goal**: Show a Z-axis selector when a table has multiple Z-axis members; switching slices updates header labels and cell coordinates without a full table reload.

**Independent Test**: Render a table with a 3-member Z-axis using a synthetic fixture; switch z_index from 0 → 1 → 2 and verify that `active_z_index` updates and `body[0][0].coordinate.explicit_dimensions` changes to reflect the new Z-member constraints.

- [ ] T031 [US2] Implement `ZAxisSelector` (`QWidget`) with adaptive display in `src/bde_xbrl_editor/ui/widgets/z_axis_selector.py` — `QTabBar` when `len(z_members) <= 10`, searchable `QComboBox` when `> 10`; emits `z_index_changed(int)` signal; hides entirely when `len(z_members) <= 1`
- [ ] T032 [US2] Mount `ZAxisSelector` at top of `XbrlTableView` in `src/bde_xbrl_editor/ui/widgets/xbrl_table_view.py` — wire `z_index_changed` signal to `XbrlTableView.set_z_index()`; initialize with `layout.z_members` on `set_table()`
- [ ] T033 [US2] Implement `XbrlTableView.set_z_index()` in `src/bde_xbrl_editor/ui/widgets/xbrl_table_view.py` — call `TableLayoutEngine.compute()` with new z_index; update `TableBodyModel`, `MultiLevelColumnHeader`, `MultiLevelRowHeader` without recreating the widget tree
- [ ] T034 [US2] Unit test: `ZAxisSelector` renders `QTabBar` for ≤10 members and `QComboBox` for >10 members; hidden for ≤1 member in `tests/unit/table_renderer/test_z_axis_selector.py`

---

## Phase 5: User Story 3 — Display Concept Labels and Data Types Within the Table (Priority: P3)

**Goal**: Each cell exposes its concept label (language-resolved from taxonomy), data type, and full dimensional coordinate via tooltip; RC codes appear on leaf header nodes; label language fallback works (Spanish → English → QName).

**Independent Test**: Render a table with a known taxonomy; programmatically query `TableBodyModel.data(index, Qt.ToolTipRole)` for a known cell and verify it contains the correct concept label and data type string. Verify RC code string appears in leaf HeaderCell.rc_code field.

- [ ] T035 [US3] Implement language-preference label resolution in `src/bde_xbrl_editor/table_renderer/layout_engine.py` — `LabelResolver` lookup with `language_preference` list; fallback chain: preferred language → Spanish → English → concept QName; populate `HeaderCell.label`
- [ ] T036 [US3] Populate `HeaderCell.rc_code` for leaf nodes in `src/bde_xbrl_editor/table_renderer/layout_engine.py` — extract Eurofiling RC-code from `BreakdownNode` attributes; `None` for non-leaf nodes
- [ ] T037 [US3] Render RC code in smaller secondary font on leaf header cells in `src/bde_xbrl_editor/ui/widgets/column_header.py` and `src/bde_xbrl_editor/ui/widgets/row_header.py` — draw RC code text above/below main label when `HeaderCell.rc_code is not None`
- [ ] T038 [US3] Implement `Qt.ToolTipRole` in `TableBodyModel.data()` in `src/bde_xbrl_editor/ui/widgets/table_body_model.py` — returns formatted string with concept label + data type + full `CellCoordinate` (concept QName, period, entity, all explicit dimensions)
- [ ] T039 [US3] Unit test: label fallback chain (Spanish → English → QName) produces correct label in `tests/unit/table_renderer/test_layout_engine.py`

---

## Phase 6: User Story 4 — Display Instance Fact Values Within the Rendered Table (Priority: P4)

**Goal**: When an XBRL instance is open, resolved fact values appear in the correct body cells; cells are visually distinguished (empty/has-fact/duplicate/not-applicable); `refresh_instance()` updates values without recomputing layout structure.

**Independent Test**: Load a BDE sample instance alongside its taxonomy; render a table; call `TableBodyModel.data(index, Qt.DisplayRole)` for cells whose coordinates match known facts in the instance and verify the formatted value string is returned; verify `BackgroundRole` returns correct colour for each cell state.

- [ ] T040 [US4] Implement `FactMapper` in `src/bde_xbrl_editor/table_renderer/fact_mapper.py` — `match(coordinate: CellCoordinate, instance: XbrlInstance) -> FactMatchResult`; matches concept + period + entity + all explicit_dimensions; sets `duplicate_count` if >1 fact matches
- [ ] T041 [US4] Implement `FactFormatter` in `src/bde_xbrl_editor/table_renderer/fact_formatter.py` — `format(raw_value, concept, decimals) -> str`; monetary: locale-formatted decimal with precision from @decimals; date: locale ISO date; percentage: append %; string: pass-through; never raises; falls back to raw_value on any error
- [ ] T042 [US4] Wire `FactMapper` into `TableLayoutEngine.compute()` in `src/bde_xbrl_editor/table_renderer/layout_engine.py` — when `instance` is not None, call `FactMapper.match()` for every `BodyCell`; populate `fact_value`, `fact_decimals`, `is_duplicate`
- [ ] T043 [US4] Implement `Qt.DisplayRole` formatted value in `TableBodyModel.data()` in `src/bde_xbrl_editor/ui/widgets/table_body_model.py` — call `FactFormatter.format()` when `cell.fact_value is not None`; empty string when None
- [ ] T044 [US4] Implement `Qt.BackgroundRole` in `TableBodyModel.data()` in `src/bde_xbrl_editor/ui/widgets/table_body_model.py` — `#F0F0F0` (no fact), white (has fact, no duplicate), `#FFD0D0` (duplicate), `#F8F8F8` (not applicable)
- [ ] T045 [US4] Implement `XbrlTableView.refresh_instance()` in `src/bde_xbrl_editor/ui/widgets/xbrl_table_view.py` — re-runs fact matching only (calls `TableLayoutEngine.compute()` with existing layout inputs but updated instance); updates `TableBodyModel`; safe to call with `None` instance
- [ ] T046 [US4] Unit test: `FactFormatter` — monetary precision, date ISO format, percentage indicator, string pass-through, fallback on malformed value in `tests/unit/table_renderer/test_fact_formatter.py`
- [ ] T047 [US4] Unit test: `FactMapper` coordinate matching — concept match, period match, explicit dimension match, duplicate detection in `tests/unit/table_renderer/test_fact_mapper.py`
- [ ] T048 [P] [US4] Integration test: table layout with BDE sample instance fact values — verify `DisplayRole` values, `BackgroundRole` colours, and `refresh_instance(None)` clears cells in `tests/integration/table_renderer/test_table_with_instance.py`

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Error resilience (FR-013), public API exports, performance validation

- [ ] T049 Implement `XbrlTableView` inline error banner for `TableLayoutError` in `src/bde_xbrl_editor/ui/widgets/xbrl_table_view.py` — catch `TableLayoutError` inside `set_table()`; display warning banner above table showing `error.reason`; render partial table (cells with `is_applicable=False`) below banner (FR-013)
- [ ] T050 [P] Populate `src/bde_xbrl_editor/table_renderer/__init__.py` re-exports: `TableLayoutEngine`, `XbrlTableView`, `FactFormatter`, `ComputedTableLayout`, `TableLayoutError`, `ZIndexOutOfRangeError`
- [ ] T051 [P] Unit test: `CellCoordinate` merge logic — row+col+Z aspect constraints combine correctly; duplicate detection for conflicting dimension constraints in `tests/unit/table_renderer/test_models.py`
- [ ] T052 Benchmark test: BDE taxonomy table renders in <3 seconds; Z-axis switch completes in <1 second (SC-001, SC-006) in `tests/integration/table_renderer/test_bde_table_render.py`

---

## Dependencies

```
Phase 1 (T001–T012) → Phase 2 (T013–T018) → Phase 3 (T019–T030) → Phase 4 (T031–T034)
                                                                   → Phase 5 (T035–T039)
                                                                   → Phase 6 (T040–T048)
                                                                              ↓
                                                                       Phase 7 (T049–T052)
```

**Key sequential spines**:
- `T019–T022` (DFS axis algorithms) → `T023` (TableLayoutEngine.compute) → `T028` (set_table)
- `T026` (TableBodyModel scaffold) → `T043` (DisplayRole) → `T044` (BackgroundRole)
- `T040` (FactMapper) + `T041` (FactFormatter) → `T042` (wire into compute) → `T045` (refresh_instance)

**Phases 4, 5, 6 are independent of each other** — they can be implemented in parallel after Phase 3.

---

## Parallel Execution Examples

**Within Phase 3 (US1)**:
```
T019 (X-axis DFS) ─┐
T020 (Y-axis DFS) ─┤→ T023 (compute()) → T028 (set_table())
T021 (Z extract)  ─┤
T022 (body grid)  ─┘

T024 (column header paint) ─┐→ T027 (XbrlTableView scaffold)
T025 (row header paint)    ─┘
```

**Across Phases 4, 5, 6 (after Phase 3 complete)**:
```
Phase 4: T031–T034   (Z-axis selector)
Phase 5: T035–T039   (labels/tooltips)     ← all three in parallel
Phase 6: T040–T048   (fact values)
```

---

## Implementation Strategy

**MVP** = Phases 1–3 (T001–T030): Taxonomy-only table rendering with correct spanning headers and empty body cells. This is independently testable and unblocks Feature 004 (instance editing), which needs `XbrlTableView.refresh_instance()`.

**Increment 2** = Phase 4 (T031–T034): Z-axis navigation — adds the selector widget and layout recompute on slice change.

**Increment 3** = Phase 5 (T035–T039): Labels and tooltips — adds RC codes, language fallback, and cell tooltips.

**Full delivery** = Phase 6 (T040–T048): Instance fact values with `FactMapper`, `FactFormatter`, visual cell state coloring, and `refresh_instance()`.

**Phase 7** (T049–T052): Error resilience banner, public API exports, and benchmarks.

---

## Summary

| Phase | User Story | Tasks | Parallelizable |
|-------|-----------|-------|----------------|
| 1: Setup | — | T001–T012 (12) | T002–T012 all [P] |
| 2: Foundational | — | T013–T018 (6) | T014–T016, T018 [P] |
| 3: US1 — Grid Render | P1 🎯 MVP | T019–T030 (12) | T020, T025, T030 [P] |
| 4: US2 — Z-Axis | P2 | T031–T034 (4) | — |
| 5: US3 — Labels | P3 | T035–T039 (5) | — |
| 6: US4 — Fact Values | P4 | T040–T048 (9) | T048 [P] |
| 7: Polish | — | T049–T052 (4) | T050, T051 [P] |
| **Total** | | **52 tasks** | |

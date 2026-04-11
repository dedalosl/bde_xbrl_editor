# Implementation Plan: Table Rendering — PWD Table Linkbase Viewer

**Branch**: `003-table-rendering-pwd` | **Date**: 2026-03-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/003-table-rendering-pwd/spec.md`

## Summary

Implement the XBRL table renderer that transforms a `TableDefinitionPWD` (Feature 001) into a visual multi-level grid. A pure-Python `TableLayoutEngine` computes the `ComputedTableLayout` — multi-level `HeaderGrid` objects for X and Y axes and a `BodyCell` grid with matched fact values. A PySide6 `XbrlTableView` compound widget renders this layout using custom `QHeaderView` subclasses for spanning headers, the Qt frozen-pane pattern for sticky headers, an adaptive `ZAxisSelector` for Z-axis navigation, and a `TableBodyModel` (`QAbstractTableModel`) for body data. Works in taxonomy-only mode (no instance) and with a loaded instance (fact values displayed).

**Tech stack**: Python 3.11+ · PySide6 (QHeaderView, QTableView, QAbstractTableModel, QTabBar, QComboBox) · no new third-party dependencies

---

## Technical Context

**Language/Version**: Python 3.11+ (unchanged)
**Primary Dependencies**: PySide6 — `QHeaderView`, `QTableView`, `QAbstractTableModel`, `QFrame`, `QTabBar`, `QComboBox`, `QPainter`, `QColor`
**New dependencies**: none — all required libraries already in stack
**Storage**: No persistence; `ComputedTableLayout` is computed on demand and held in memory for the current view
**Testing**: pytest + pytest-qt; visual snapshot tests for header rendering; unit tests for `TableLayoutEngine` using synthetic `TableDefinitionPWD` fixtures
**Target Platform**: macOS, Windows, Linux desktop (unchanged)
**Performance Goals**: Any BDE taxonomy table renders in <3 seconds (SC-001); Z-axis switch in <1 second (SC-006); 200+ row tables remain scrollable without freeze (SC-005)
**Constraints**: Header spanning entirely via custom `QHeaderView` paint (no `setSpan()` on body); frozen headers via two-QTableView pattern; table renderer has no PySide6 dependency in its layout engine
**Scale/Scope**: Up to 200+ rows, 50+ columns, 50 Z-axis members; multi-level headers up to ~4 levels deep

---

## Constitution Check

*Constitution still unfilled — same note as previous features.*

**Informal gates applied**:
- ✅ Layout engine (`TableLayoutEngine`) has zero PySide6 dependency — testable without Qt
- ✅ `XbrlTableView` depends on `table_renderer` only via `ComputedTableLayout` — clean separation
- ✅ No `setSpan()` on large tables — spans handled in custom headers only
- ✅ `FactFormatter` is pure Python — reusable by export features later

---

## Project Structure

### Documentation (this feature)

```text
specs/003-table-rendering-pwd/
├── plan.md              ← this file
├── research.md          ← Phase 0: header strategy, frozen panes, layout algorithm, Z-nav UX
├── data-model.md        ← Phase 1: ComputedTableLayout, HeaderGrid, HeaderCell, BodyCell, etc.
├── contracts/
│   └── table-renderer-api.md  ← Phase 1: TableLayoutEngine, XbrlTableView, FactFormatter
└── tasks.md             ← Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code (additions to the project)

```text
src/
└── bde_xbrl_editor/
    ├── taxonomy/              # Feature 001 (unchanged)
    ├── instance/              # Feature 002 (unchanged)
    ├── table_renderer/        # ← Feature 003 scope
    │   ├── __init__.py        # re-exports: TableLayoutEngine, XbrlTableView, FactFormatter
    │   ├── layout_engine.py   # TableLayoutEngine — pure Python layout computation
    │   ├── fact_mapper.py     # Map CellCoordinate → instance facts (pure Python)
    │   ├── fact_formatter.py  # FactFormatter — type-aware display string formatting
    │   └── models.py          # ComputedTableLayout, HeaderGrid, HeaderCell,
    │                          #   BodyCell, CellCoordinate, ZMemberOption, FactMatchResult
    └── ui/
        └── widgets/
            ├── xbrl_table_view.py        # XbrlTableView (QFrame) — main compound widget
            ├── table_body_model.py       # TableBodyModel (QAbstractTableModel)
            ├── column_header.py          # MultiLevelColumnHeader (QHeaderView subclass)
            ├── row_header.py             # MultiLevelRowHeader (QHeaderView subclass)
            └── z_axis_selector.py        # ZAxisSelector (QWidget, adaptive tabs/combobox)

tests/
├── unit/
│   └── table_renderer/
│       ├── test_layout_engine.py        # Layout computation: span widths, leaf counts, grid dims
│       ├── test_fact_mapper.py          # Coordinate matching: concept, period, dimensions
│       ├── test_fact_formatter.py       # Monetary/date/pct/string formatting
│       └── test_models.py              # CellCoordinate merging, duplicate detection
└── integration/
    └── table_renderer/
        ├── test_bde_table_render.py    # End-to-end: BDE sample taxonomy table → layout
        └── test_table_with_instance.py # Layout + fact values from BDE sample instance
```

**Structure Decision**: `table_renderer/` is a new sub-package alongside `taxonomy/` and `instance/`. The layout engine and formatters live there (no Qt); the Qt widgets live under `ui/widgets/`. This keeps the dependency graph clean: UI depends on table_renderer; table_renderer depends on taxonomy and instance; neither taxonomy nor instance knows about the renderer.

---

## Complexity Tracking

> No constitution violations to justify.

---

## Phase 0 Summary — Resolved Decisions

| Decision | Resolved To |
|----------|-------------|
| Multi-level spanning headers | Custom `QHeaderView.paintSection()` for both X and Y axes |
| Frozen headers | Two-`QTableView` overlay with synchronised scrollbars (Qt Frozen Column pattern) |
| Virtual rendering | `QAbstractTableModel` auto-virtualises; no `setSpan()` on body cells |
| Body cell spans | Body grid is always 1×1; spanning only in custom `QHeaderView` headers |
| Layout algorithm | DFS traversal; leaf index assignment; span = descendant leaf count |
| Z-axis navigation | `QTabBar` ≤10 members; searchable `QComboBox` >10 members |
| Cell → fact matching | Merge aspect constraints from row+col+Z leaf nodes; match against instance facts |
| Fact value formatting | Type-specific `FactFormatter`; `DisplayRole` returns formatted string; `UserRole` raw value |

---

## Phase 1 Summary — Design Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Data model | `specs/003-table-rendering-pwd/data-model.md` | ✅ Complete |
| Renderer API contract | `specs/003-table-rendering-pwd/contracts/table-renderer-api.md` | ✅ Complete |

### Key design decisions

1. **Layout engine is pure Python** — `TableLayoutEngine` has no Qt import; it can be tested with `pytest` alone, without a display server or Qt application.
2. **`XbrlTableView.refresh_instance()` is cheap** — re-runs only fact matching (not layout recomputation); safe to call after every cell edit in Feature 004.
3. **Broken table definitions don't crash** — `TableLayoutEngine` catches individual node errors, renders as much as possible, and marks unresolvable cells as `is_applicable=False`; `XbrlTableView` displays an inline warning banner (FR-013 from spec).
4. **RC codes are always displayed on leaf headers** — `HeaderCell.rc_code` is rendered by `MultiLevelColumnHeader` and `MultiLevelRowHeader` in a smaller secondary font; `None` means no code is shown (no empty placeholder).
5. **`FactFormatter` defaults to raw value on error** — any formatting failure returns the unformatted string, never an exception, never an empty cell for a fact that exists.

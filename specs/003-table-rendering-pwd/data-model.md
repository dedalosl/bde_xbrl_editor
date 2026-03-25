# Data Model: Table Rendering — PWD Table Linkbase Viewer

**Branch**: `003-table-rendering-pwd` | **Phase**: 1 | **Date**: 2026-03-25

---

## Overview

This feature introduces a **layout computation layer** (pure Python, no Qt) and a **Qt widget layer** (PySide6). The layout layer transforms a `TableDefinitionPWD` (Feature 001) into a `ComputedTableLayout` — a flat, grid-indexed representation of header cells and body cells. The widget layer renders this layout.

All layout objects are immutable after construction. A new `ComputedTableLayout` is produced whenever the selected Z-axis member changes.

---

## Layout Computation Models

### `HeaderCell`
One cell within the multi-level column or row header area.

| Field | Type | Description |
|-------|------|-------------|
| `label` | `str` | Display label (from `LabelResolver`, active display language) |
| `rc_code` | `str \| None` | Eurofiling RC-code (leaf nodes only; `None` for branch nodes) |
| `span` | `int` | How many leaf columns/rows this cell spans (≥1; leaves always 1) |
| `level` | `int` | Depth in the breakdown hierarchy (0 = root level) |
| `is_leaf` | `bool` | Whether this cell is at the deepest level of its axis |
| `is_abstract` | `bool` | Abstract nodes group children but produce no body column/row |
| `source_node` | `BreakdownNode` | Reference to the originating `BreakdownNode` (Feature 001 model) |

### `HeaderGrid`
The complete header for one axis (X or Y), ready to paint.

| Field | Type | Description |
|-------|------|-------------|
| `levels` | `list[list[HeaderCell]]` | Outer = depth level (0 = outermost); inner = ordered cells at that level |
| `leaf_count` | `int` | Total number of leaf cells (= number of data columns or rows) |
| `depth` | `int` | Number of header levels (= number of header rows for X-axis) |

### `CellCoordinate`
The complete XBRL dimensional coordinate of one body cell. Used for fact matching.

| Field | Type | Description |
|-------|------|-------------|
| `concept` | `QName \| None` | Concept constrained by this cell (`None` if aspect not covered by table) |
| `explicit_dimensions` | `dict[QName, QName]` | Dimension → member for all explicitly constrained dimensions |
| `period_override` | `ReportingPeriod \| None` | Period if constrained by table; `None` means use instance base period |
| `entity_override` | `ReportingEntity \| None` | Entity if constrained by table; `None` means use instance base entity |

### `BodyCell`
One data cell in the rendered table body.

| Field | Type | Description |
|-------|------|-------------|
| `row_index` | `int` | 0-based row index in the body grid |
| `col_index` | `int` | 0-based column index in the body grid |
| `coordinate` | `CellCoordinate` | Merged dimensional coordinate (row + col + Z constraints) |
| `fact_value` | `str \| None` | Raw fact value from the open instance (`None` = no fact) |
| `fact_decimals` | `str \| None` | `@decimals` attribute of the matched fact |
| `is_duplicate` | `bool` | `True` if more than one instance fact matches this coordinate (error state) |
| `is_applicable` | `bool` | `False` if this cell position is not valid for the current Z-axis selection |

### `ComputedTableLayout`
The full layout for one table and one Z-axis selection. Immutable after construction.

| Field | Type | Description |
|-------|------|-------------|
| `table_id` | `str` | Source `TableDefinitionPWD.table_id` |
| `table_label` | `str` | Human-readable table label |
| `column_header` | `HeaderGrid` | X-axis header (multi-level, rendered as column headers) |
| `row_header` | `HeaderGrid` | Y-axis header (multi-level, rendered as row headers) |
| `z_members` | `list[ZMemberOption]` | Available Z-axis members (for navigation widget) |
| `active_z_index` | `int` | Index of currently selected Z-axis member |
| `body` | `list[list[BodyCell]]` | `body[row][col]`; dimensions: `row_header.leaf_count × column_header.leaf_count` |

### `ZMemberOption`
One entry in the Z-axis navigation selector.

| Field | Type | Description |
|-------|------|-------------|
| `index` | `int` | Position in the Z-axis member list |
| `label` | `str` | Display label for this Z-axis member |
| `dimension_constraints` | `dict[QName, QName]` | Dimension members defining this Z-axis slice |

---

## Fact Matching Model

### `FactMatchResult`
The outcome of attempting to match instance facts to a single `BodyCell`.

| Field | Type | Description |
|-------|------|-------------|
| `matched` | `bool` | Whether exactly one fact was found |
| `fact_value` | `str \| None` | Fact value string if matched |
| `fact_decimals` | `str \| None` | `@decimals` attribute if matched |
| `duplicate_count` | `int` | Number of matching facts (0 = empty, 1 = normal, >1 = error) |

---

## Qt Widget Model (PySide6 layer)

### `TableBodyModel` (QAbstractTableModel)

The Qt model backing the body `QTableView`. Holds a reference to a `ComputedTableLayout`; exposes rows and columns via the standard Qt model protocol.

```
TableBodyModel(layout: ComputedTableLayout)

rowCount() -> int                          # = layout.row_header.leaf_count
columnCount() -> int                       # = layout.column_header.leaf_count
data(index, role) -> Any
  Qt.DisplayRole   → formatted value string (via FactFormatter) or empty string
  Qt.UserRole      → raw fact value string or None
  Qt.BackgroundRole → QColor (empty cell = light grey; duplicate = light red; normal = white)
  Qt.ToolTipRole   → cell concept label + data type + full dimensional coordinate
```

### `MultiLevelColumnHeader` (QHeaderView subclass)

Custom horizontal header. Receives a `HeaderGrid` and paints all levels with correct spanning.

```
MultiLevelColumnHeader(header_grid: HeaderGrid, parent=None)
  .set_header_grid(header_grid: HeaderGrid) -> None   # update and repaint
  .sizeHint() -> QSize                                 # total height for all levels
```

**Paint logic**: For each `level` in `header_grid.levels`, iterate `HeaderCell` objects; compute pixel x-offset from cumulative leaf widths; paint rect of `width = span × section_width`, `height = level_height`; draw label centred; if `is_leaf` and `rc_code` is set, draw RC code in smaller font above or below the label.

### `MultiLevelRowHeader` (QHeaderView subclass)

Symmetric to `MultiLevelColumnHeader` but for the Y-axis (vertical).

### `XbrlTableView` (QFrame)

The main compound widget. Contains: `ZAxisSelector` at top, `MultiLevelColumnHeader`, `MultiLevelRowHeader`, and a `QTableView` for the body, with synchronised scrollbars.

```
XbrlTableView(parent=None)

  .set_layout(layout: ComputedTableLayout) -> None
    """
    Install a new ComputedTableLayout. Rebuilds all sub-widgets.
    Called when the user selects a table or changes Z-axis selection.
    """

  .set_z_index(z_index: int) -> None
    """
    Recompute the layout for the given Z-axis member and refresh.
    """
```

### `ZAxisSelector` (QWidget)

Adaptive: shows `QTabBar` if `len(z_members) <= 10`, else a filtered `QComboBox`.

```
ZAxisSelector(z_members: list[ZMemberOption], parent=None)
  signal: z_index_changed(int)    # emitted when user changes Z selection
```

### `FactFormatter`

Pure Python, no Qt dependency. Format a raw fact string for display given its concept data type.

```
FactFormatter(taxonomy: TaxonomyStructure)

  format(raw_value: str, concept: QName, decimals: str | None) -> str
    """
    Returns a display-ready string. Never raises.
    Falls back to raw_value if concept type is unknown.
    """
```

---

## Error / State Indicators (visual)

| State | `BackgroundRole` colour | Condition |
|-------|------------------------|-----------|
| No fact (empty) | Light grey (`#F0F0F0`) | `cell.fact_value is None` |
| Has fact | White | `cell.fact_value is not None and not cell.is_duplicate` |
| Duplicate facts | Light red (`#FFD0D0`) | `cell.is_duplicate is True` |
| Cell not applicable | Very light grey (`#F8F8F8`) | `cell.is_applicable is False` |

---

## Entity Relationships

```
ComputedTableLayout
  ├── HeaderGrid (column_header)           # X-axis
  │     └── list[list[HeaderCell]]         # levels × cells per level
  ├── HeaderGrid (row_header)              # Y-axis
  │     └── list[list[HeaderCell]]
  ├── list[ZMemberOption]                  # Z-axis navigation
  └── list[list[BodyCell]]                 # body[row][col]
        └── CellCoordinate                 # concept + dimensions + period + entity

TableBodyModel (Qt)         → references ComputedTableLayout
MultiLevelColumnHeader (Qt) → references HeaderGrid (column)
MultiLevelRowHeader (Qt)    → references HeaderGrid (row)
XbrlTableView (Qt)          → owns TableBodyModel + both headers + ZAxisSelector
```

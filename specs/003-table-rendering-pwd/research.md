# Research: Table Rendering — PWD Table Linkbase Viewer

**Branch**: `003-table-rendering-pwd` | **Phase**: 0 | **Date**: 2026-03-25
**Inherits from**: Feature 001 tech stack (Python 3.11+, PySide6, lxml, xmlschema)

---

## Decision 1: Multi-Level Spanning Column and Row Headers

**Decision**: Subclass `QHeaderView` and override `paintSection()` to draw hierarchical multi-level headers with manual span computation. One `MultiLevelColumnHeader` for the X-axis and one `MultiLevelRowHeader` for the Y-axis.

**Rationale**: `QHeaderView` has no built-in support for spanning sections across multiple hierarchy levels. The canonical approach used by Qt-based financial and spreadsheet applications is to override `paintSection()` and draw headers manually using `QPainter`. The header class receives a pre-computed list of levels (each level is a list of `HeaderCell` objects with `span`, `label`, and `rc_code`), and paints each cell at the correct position using pixel coordinates derived from the span widths.

**Key formula**: `span_width(node) = sum of leaf count in subtree`. A leaf node has span = 1. A branch node spans as many columns as the sum of all descendant leaf spans. This is computed once by `TableLayoutEngine` and passed to the header widget.

**Alternatives considered**:
- Stacking multiple `QHeaderView` instances (complex sync, unstable under resize)
- `QTableWidget.setSpan()` on headers (only works on data cells, not header sections)
- Custom `QWidget` tree from scratch (more flexible but more code, loses `QHeaderView` integration)

---

## Decision 2: Frozen (Sticky) Headers During Scroll

**Decision**: Use the Qt frozen-pane pattern: a second `QTableView` overlay sharing the same model, positioned over the frozen area, with scrollbars synchronised via `valueChanged` signal connections.

**Rationale**: Qt's documentation (Frozen Column Example, Qt 6) explicitly recommends this approach for frozen columns/rows. The frozen view and the main view share the same `QAbstractTableModel` — the frozen view hides the columns/rows that are not frozen and vice versa. Scrollbars are connected so scrolling one view scrolls the other. `moveCursor()` is overridden to prevent selection from disappearing behind the frozen area. This approach is robust and has known, documented edge cases.

**Alternatives considered**:
- Custom `QAbstractScrollArea` from scratch (loses all `QTableView` delegate benefits)
- Viewport clipping on a single `QTableView` (headers don't actually stay in place; they are part of the viewport, not the scroll area margin)
- Qt Quick `TableView` (wrong toolkit — project uses Qt Widgets)

---

## Decision 3: Virtual Rendering for 200+ Row Tables

**Decision**: `QAbstractTableModel` with `rowCount()` / `columnCount()` / `data()` provides automatic virtualisation — Qt only calls `data()` for visible cells during paint. No explicit lazy loading needed for 200 rows.

**Rationale**: Qt's view framework renders only the visible viewport rectangle. `data()` is called only for rows/columns currently on screen. For a 200-row × 50-column table this is well within Qt's comfortable range without any special handling.

**Important caveat**: `QTableView.setSpan()` pre-computes a span map internally and becomes slow when called for thousands of cells upfront. Instead, span information for body cells is **not** expressed via `setSpan()`. Row headers and column headers handle their own spans internally via `MultiLevelRowHeader` and `MultiLevelColumnHeader` (custom paint). Body cells are always 1×1; there is no cell merging in the body grid.

**Alternatives considered**: `canFetchMore()` / `fetchMore()` for incremental loading — unnecessary at 200-row scale; reserved for future if taxonomy tables grow to thousands of rows.

---

## Decision 4: PWD Table Layout Algorithm

**Decision**: Traverse each breakdown tree depth-first; assign consecutive leaf indices; parent span = count of descendant leaves. The resulting header grid has `depth` rows (one per tree level) and `leaf_count` columns (or rows for the Y-axis). Body grid = `y_leaf_count × x_leaf_count` cells.

**Algorithm**:
1. Traverse breakdown tree with DFS; assign leaf indices 0…N-1 in traversal order.
2. For each node: `span = max_leaf_idx - min_leaf_idx + 1` (or 1 for leaves).
3. Header levels = depth of the deepest path in the tree.
4. Each `HeaderCell` at `(level, position)` occupies `span` consecutive column/row positions.
5. `BodyCell` at `(row_idx, col_idx)` is identified by the pair `(y_leaf[row_idx], x_leaf[col_idx])`.
6. Z-axis: treated separately — layout is recomputed (or filtered) when a different Z-axis member is selected; the XY grid structure may differ per Z member.

**Aspect constraint merging**: Each leaf node carries an `aspect_constraints` dict. For a body cell, the full constraint set = merge of `y_leaf.aspect_constraints ∪ x_leaf.aspect_constraints ∪ z_member.aspect_constraints`. If the same aspect is constrained by multiple axes, it is a taxonomy error (not expected in well-formed BDE taxonomies).

**Alternatives considered**: Pre-computing a full Cartesian grid eagerly — correct but allocates O(rows × cols) objects upfront; acceptable at 200-row scale but computed lazily for performance clarity.

---

## Decision 5: Z-Axis Navigation Widget

**Decision**: `QTabBar` (not `QTabWidget`) for ≤10 Z-axis members; `QComboBox` with client-side text filter for >10 members. Adaptive: the widget checks the member count and creates the right control.

**Rationale**: Tabs provide single-click, always-visible member selection and allow users to scan all options at once — optimal when ≤10 members fit without scrolling. For >10 members (common in BDE tables with many entity types or consolidation scopes), a `QComboBox` with an inline `QLineEdit` for filtering allows fast lookup by name. Using `QTabBar` rather than `QTabWidget` keeps the layout simpler (the table area is not nested inside a tab widget).

**Alternatives considered**: Radio buttons (≤5 only, takes too much space for tables with 5+ Z members); dropdown only (loses the always-visible benefit for small member counts).

---

## Decision 6: Cell Coordinate to XBRL Context Matching

**Decision**: Each `BodyCell` pre-computes a `CellCoordinate` (concept + entity_override + period_override + dimension_members dict). Fact matching: iterate instance facts; a fact matches a cell if its concept and all non-None coordinate components equal the fact's context components.

**Rationale**: The cell coordinate is derived at layout time from the merged aspect constraints of the row, column, and Z-axis leaf nodes. Not all aspects are necessarily constrained by the table (e.g., entity and period may be "open" — inherited from the instance's base context). For unspecified aspects, the instance's base entity and period are used. Dimensional aspects always come from the breakdown.

**Matching rule**: A fact matches cell `(row, col, z)` if:
- `fact.concept == cell.concept`
- `fact.context.entity == instance.entity` (if entity not constrained by table)
- `fact.context.period == instance.period` (if period not constrained by table)
- For each dimension in `cell.dimension_members`: `fact.context.dimensions[dim] == cell.dimension_members[dim]`
- `fact.context` has no extra dimensions beyond those covered by the cell

**Alternatives considered**: String-based context ID comparison — fragile (sensitive to ID generation differences); full context object equality — correct but requires implementing full XBRL context equality semantics (same result, more code).

---

## Decision 7: Fact Value Formatting

**Decision**: Type-specific formatters in `FactFormatter`, called from `QAbstractTableModel.data(index, Qt.DisplayRole)`. Raw value stored in `Qt.UserRole` for export and editing. Formatters:
- **Monetary** (`xbrli:monetaryItemType`): locale-aware thousand-separator, decimal places from `@decimals` attribute (e.g., `decimals="-3"` → round to thousands; `decimals="2"` → 2dp). No currency symbol in cell (currency shown in column/row header if declared).
- **Decimal / pure**: same as monetary but without currency consideration.
- **Percentage** (`num:percentItemType`): multiply by 100 if stored as fraction (taxonomy-specific); append `%`.
- **Date**: parse ISO 8601 date; format as `DD/MM/YYYY` for Spanish locale.
- **String**: display as-is; `QStyledItemDelegate` handles truncation with ellipsis.
- **Integer**: locale-aware thousand-separator, no decimal places.

**Empty cell**: `data()` returns `None` for `DisplayRole` when no fact exists; the delegate renders an empty, visually distinct background (light grey).

**Alternatives considered**: Formatting in the delegate's `paint()` method — increases delegate complexity; model should own display logic per Qt MVC conventions.

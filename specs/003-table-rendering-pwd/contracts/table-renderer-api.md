# Contract: Table Renderer Public API

**Branch**: `003-table-rendering-pwd` | **Phase**: 1 | **Date**: 2026-03-25
**Module**: `bde_xbrl_editor.table_renderer`

This document defines the public interface exposed by the table rendering feature to the rest of the application. All other modules must use only the interfaces defined here.

**Depends on**:
- `bde_xbrl_editor.taxonomy` (Feature 001) — `TaxonomyStructure`, `TableDefinitionPWD`, `LabelResolver`, `QName`
- `bde_xbrl_editor.instance` (Feature 002) — `XbrlInstance` (optional; table can render taxonomy-only)

---

## Primary Entry Points

### `TableLayoutEngine`

Pure Python — no PySide6 dependency. Converts a `TableDefinitionPWD` into a `ComputedTableLayout`.

```
TableLayoutEngine(taxonomy: TaxonomyStructure)

Methods:
  compute(
    table: TableDefinitionPWD,
    instance: XbrlInstance | None = None,
    z_index: int = 0,
    language_preference: list[str] | None = None,
  ) -> ComputedTableLayout
    """
    Compute the full grid layout for the given table and Z-axis selection.
    If instance is provided, fact values are resolved into BodyCell.fact_value.
    If instance is None, all BodyCell.fact_value fields are None.
    z_index selects which Z-axis member is active (0 if table has no Z-axis).
    Raises:
      TableLayoutError — table definition is structurally invalid (broken linkbase)
      ZIndexOutOfRangeError — z_index >= len(table.z_breakdowns[0].members)
    """
```

### `FactFormatter`

Pure Python. Formats raw fact values for display.

```
FactFormatter(taxonomy: TaxonomyStructure)

Methods:
  format(
    raw_value: str,
    concept: QName,
    decimals: str | None = None,
  ) -> str
    """
    Returns a locale-appropriate display string. Never raises.
    Falls back to raw_value if concept type is unknown or value is malformed.
    """
```

---

## UI Widget

### `XbrlTableView` (QFrame — PySide6)

The main renderable widget. Embed in the application's main window or a docking area.

```
XbrlTableView(parent: QWidget | None = None)

Methods:
  set_table(
    table: TableDefinitionPWD,
    taxonomy: TaxonomyStructure,
    instance: XbrlInstance | None = None,
  ) -> None
    """
    Load and render a table. Clears the previous table if any.
    If instance is None, renders the taxonomy structure without fact values.
    Automatically selects z_index=0.
    """

  refresh_instance(instance: XbrlInstance | None) -> None
    """
    Re-match fact values against the current layout without recomputing structure.
    Call after fact edits (Feature 004) to update displayed values.
    """

  clear() -> None
    """
    Remove the current table and show an empty state.
    """

Properties:
  .active_z_index: int           # currently selected Z-axis member index
  .active_table_id: str | None   # table_id of currently displayed table, or None

Signals:
  cell_selected(row: int, col: int)    # emitted when user clicks a body cell
  z_index_changed(z_index: int)        # emitted when user changes Z-axis selection
```

---

## Error Hierarchy

```
TableRenderError (base)
  ├── TableLayoutError
  │     .table_id: str
  │     .reason: str         # what was broken in the linkbase definition
  └── ZIndexOutOfRangeError
        .table_id: str
        .requested_z: int
        .max_z: int
```

---

## Usage Example (main window pseudocode)

```python
# After taxonomy + instance are loaded (Features 001, 002/004):
table_view = XbrlTableView(parent=main_window)
main_layout.addWidget(table_view)

# User selects a table from the tree:
def on_table_selected(table: TableDefinitionPWD):
    try:
        table_view.set_table(
            table=table,
            taxonomy=app_state.current_taxonomy,
            instance=app_state.open_instance,  # None if no instance open
        )
    except TableLayoutError as e:
        status_bar.showMessage(f"Table could not be rendered: {e.reason}")

# After user edits a fact value (Feature 004):
def on_fact_edited():
    table_view.refresh_instance(app_state.open_instance)
```

---

## Invariants and Guarantees

- `TableLayoutEngine.compute()` is **pure** — same inputs always produce the same output; no side effects.
- `XbrlTableView.set_table()` **never crashes** on a broken table definition — it catches `TableLayoutError` internally and displays a partial table with an error indicator for the unresolvable portions (FR-013 from spec).
- `FactFormatter.format()` **never raises** — always returns a displayable string.
- `XbrlTableView` is safe to call `refresh_instance()` on at any time, including with `None` — it will clear all fact values and show an empty-cell state.
- **Taxonomy module has no dependency on the table renderer** — the dependency is one-directional: `table_renderer` depends on `taxonomy`, not the reverse.

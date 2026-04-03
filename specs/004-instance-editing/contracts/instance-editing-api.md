# Contract: Instance Editing Module Public API

**Branch**: `004-instance-editing` | **Phase**: 1 | **Date**: 2026-03-26
**Module**: `bde_xbrl_editor.instance` (extends Feature 002)

**Depends on**:
- `bde_xbrl_editor.taxonomy` (Feature 001) — `TaxonomyStructure`, `TaxonomyLoader`, `QName`
- `bde_xbrl_editor.instance` (Feature 002) — `XbrlInstance`, `Fact`, `ContextId`, `UnitId`, `InstanceSerializer`
- `bde_xbrl_editor.table_renderer` (Feature 003) — `XbrlTableView.refresh_instance()`

---

## New Entry Points

### `InstanceParser`

Loads an existing XBRL instance from disk into an `XbrlInstance`.

```
InstanceParser(
  taxonomy_loader: TaxonomyLoader,
  manual_taxonomy_resolver: Callable[[str], Path | None] | None = None,
)

Methods:
  load(path: str | Path) -> tuple[XbrlInstance, list[OrphanedFact]]
    """
    Parse the XBRL instance at path. Resolve and load the bound taxonomy.
    Returns (populated XbrlInstance, list of orphaned facts).
    instance._dirty is False after load; instance.source_path = path.
    If orphaned facts exist, the caller must present them to the user.
    Raises:
      InstanceParseError        — not well-formed XML, missing xbrli:xbrl root,
                                   missing link:schemaRef, or unresolvable context ref
      TaxonomyResolutionError   — schemaRef could not be resolved and no manual
                                   resolver was provided or it returned None
    """
```

**`manual_taxonomy_resolver`**: A callable that receives the unresolved schemaRef href string and returns a `Path` to the taxonomy entry point (or `None` if the user cancels). In the UI this is wired to a folder-picker dialog.

---

### `InstanceEditor`

Mutation service. Wraps an `XbrlInstance` and enforces the dirty-state invariant.

```
InstanceEditor(instance: XbrlInstance)

Signals (PySide6 Signal, emit on every mutation):
  changes_made = Signal()      # connect to main window's dirty-state handler

Methods:
  add_fact(
    concept: QName,
    context_ref: ContextId,
    value: str,                    # XBRL canonical form (invariant "." decimal separator)
    unit_ref: UnitId | None = None,
    decimals: str | None = None,
  ) -> Fact
    """
    Create a new Fact; append to instance.facts; emit changes_made.
    Raises DuplicateFactError if concept+context already has a fact.
    """

  update_fact(fact_index: int, new_value: str) -> None
    """
    Replace fact value at index; emit changes_made.
    new_value must already be in XBRL canonical form (use XbrlTypeValidator.normalise()).
    Raises InvalidFactValueError if new_value fails type validation for the concept.
    """

  remove_fact(fact_index: int) -> None
    """
    Remove fact at index; emit changes_made.
    """

  mark_saved(path: Path) -> None
    """
    Called by InstanceSerializer.save(). Sets source_path and clears dirty flag.
    """
```

---

### `XbrlTypeValidator`

Pure Python. Type-aware validation and normalisation for XBRL fact values.

```
XbrlTypeValidator(taxonomy: TaxonomyStructure)

Methods:
  validate(value: str, concept: QName) -> tuple[bool, str]
    """
    (is_valid, error_message). error_message is "" when valid.
    Never raises. Returns (True, "") for unknown concept types (safe fallback).
    """

  normalise(value: str, concept: QName) -> str
    """
    Convert locale-formatted user input to XBRL canonical form.
    Monetary/decimal: remove thousands separators, replace locale decimal with ".".
    Date: reformat to YYYY-MM-DD.
    Boolean: normalise "true"/"false"/"1"/"0" → "true"/"false".
    Never raises; returns value unchanged if normalisation is not possible.
    """
```

---

## Updated `XbrlInstance` (Feature 002 model additions)

These fields are added to `XbrlInstance` in Feature 004:

```
XbrlInstance (extended):
  .orphaned_facts: list[OrphanedFact]   # read-only after parse; preserved on save
  .edit_history: list[EditOperation]    # append-only; cleared on load (not on save)
```

---

## Error Hierarchy (additions)

```
InstanceParseError (base for parse failures)
  ├── .path: str
  └── .reason: str

TaxonomyResolutionError (extends InstanceParseError)
  └── .schema_ref_href: str        # the href that could not be resolved

DuplicateFactError
  ├── .concept: QName
  └── .context_ref: ContextId

InvalidFactValueError
  ├── .concept: QName
  ├── .expected_type: str          # e.g., "xbrli:monetaryItemType"
  └── .provided_value: str
```

---

## UI Contract: `CellEditDelegate` (PySide6)

Installed on the `QTableView` body inside `XbrlTableView`. Not part of the public `table_renderer` API — it is wired by the main window after both `XbrlTableView` and `InstanceEditor` are available.

```
CellEditDelegate(
  taxonomy: TaxonomyStructure,
  instance_editor: InstanceEditor,
  table_layout: ComputedTableLayout,   # from active XbrlTableView
  parent: QWidget | None = None,
)
  → QStyledItemDelegate subclass

# Wired by main window:
table_view.body_table_view.setItemDelegate(
    CellEditDelegate(taxonomy, editor, table_view.active_layout)
)
```

---

## Main Window Contract (unsaved-change guard)

The main window must implement these two patterns (not a public module API, but documented here for implementor clarity):

**Title tracking**:
```python
editor.changes_made.connect(lambda: self.setWindowModified(True))
# Window title must contain "[*]": e.g., "BDE XBRL Editor — filename.xbrl[*]"
```

**Close / navigate guard**:
```python
def closeEvent(self, event):
    if self.instance and self.instance.has_unsaved_changes:
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            "Save changes before closing?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
        )
        if reply == QMessageBox.Save:
            self._save_instance()   # may call event.ignore() if save fails
            event.accept()
        elif reply == QMessageBox.Discard:
            event.accept()
        else:
            event.ignore()
    else:
        event.accept()
```

---

## Invariants and Guarantees

- `InstanceParser.load()` always sets `instance._dirty = False` — a freshly loaded instance is never considered modified.
- `InstanceEditor` is the **only** code path that sets `instance._dirty = True` — no direct field mutation outside this class.
- `XbrlTypeValidator.validate()` and `.normalise()` **never raise** — all errors are returned as `(False, message)` or the original value.
- `InstanceSerializer.save()` (Feature 002) is unchanged; it calls `editor.mark_saved()` on success to clear the dirty flag.
- Orphaned facts are **always preserved** in the saved XML — `InstanceSerializer` appends their `raw_element_xml` after all known facts, in original document order.

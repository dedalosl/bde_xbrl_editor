# Data Model: Instance Editing

**Branch**: `004-instance-editing` | **Phase**: 1 | **Date**: 2026-03-26

---

## Overview

Feature 004 adds two major capabilities on top of the existing model:

1. **Parsing** — an `InstanceParser` that reads an XBRL 2.1 XML file and produces a populated `XbrlInstance` (defined in Feature 002).
2. **Editing** — an `InstanceEditor` that mutates `XbrlInstance.facts` and maintains the dirty-state invariant.

No new top-level entities are introduced. The additions are:
- `InstanceParser` (service class)
- `InstanceEditor` (service class)
- `OrphanedFact` (data class for facts whose concept is not in the taxonomy)
- `EditOperation` (data class for audit trail — optional in v1 but scaffolded)
- `CellEditDelegate` (PySide6 `QStyledItemDelegate` subclass — UI layer only)

The existing `XbrlInstance`, `XbrlContext`, `XbrlUnit`, `Fact`, and `FilingIndicator` from Feature 002 are extended in-place; no new root objects.

---

## Parsing Model

### `InstanceParser`
Parses an XBRL 2.1 XML file into a populated `XbrlInstance`. The parser is the only code path that reads XBRL XML into memory; `InstanceFactory` (Feature 002) only creates new instances.

```
InstanceParser(taxonomy: TaxonomyStructure | None = None)

  load(path: str | Path) -> tuple[XbrlInstance, list[OrphanedFact]]
    """
    Parse the file at path. Resolve and load the taxonomy if not provided.
    Returns the populated instance + a (possibly empty) list of orphaned facts.
    Raises:
      InstanceParseError         — not well-formed XML or missing mandatory elements
      TaxonomyResolutionError    — schemaRef cannot be resolved and user declined manual override
    """
```

**Parse stages**:
1. Parse XML root; validate `xbrli:xbrl` namespace.
2. Extract `link:schemaRef/@xlink:href` → resolve taxonomy path → load via `TaxonomyLoader`.
3. Parse `xbrli:context` elements → `XbrlContext` objects.
4. Parse `xbrli:unit` elements → `XbrlUnit` objects.
5. Parse `ef-find:filingIndicator` elements → `FilingIndicator` objects.
6. Iterate remaining child elements as facts → `Fact` objects; concepts not in taxonomy go to `OrphanedFact`.
7. Populate `XbrlInstance` with all parsed objects; set `_dirty = False`, `source_path = path`.

### `OrphanedFact`
A fact present in the XML whose concept `QName` is not declared in the loaded taxonomy.

| Field | Type | Description |
|-------|------|-------------|
| `concept_qname_str` | `str` | Clark notation `{ns}local` of the unknown concept |
| `context_ref` | `str` | Raw `@contextRef` value from XML |
| `unit_ref` | `str \| None` | Raw `@unitRef` value from XML |
| `value` | `str` | Raw text content |
| `decimals` | `str \| None` | Raw `@decimals` attribute |
| `raw_element_xml` | `bytes` | Serialised XML element, for lossless round-trip |

**Invariant**: Orphaned facts are preserved verbatim in the saved XML (FR-015). The `XbrlInstance.orphaned_facts` list holds them; `InstanceSerializer` appends their `raw_element_xml` to the output.

---

## Editing Model

### `InstanceEditor`
Mutation service for an open `XbrlInstance`. All writes to the instance go through this class; direct field mutation is prohibited outside this class.

```
InstanceEditor(instance: XbrlInstance)

  add_fact(
    concept: QName,
    context_ref: ContextId,
    value: str,                      # XBRL canonical string
    unit_ref: UnitId | None = None,
    decimals: str | None = None,
  ) -> Fact
    """
    Create and append a new Fact. Auto-generates a context if the given
    context_ref doesn't exist yet (should not happen in normal flow —
    CellCoordinate-based context lookup ensures contexts exist).
    Sets instance._dirty = True. Emits changes_made signal (if Qt signal attached).
    Raises DuplicateFactError if a fact for this concept+context already exists.
    """

  update_fact(fact_index: int, new_value: str) -> None
    """
    Replace the value of fact at index. new_value must be XBRL canonical form.
    Sets instance._dirty = True.
    Raises IndexError if fact_index out of range.
    Raises InvalidFactValueError if new_value format is invalid for the concept's type.
    """

  remove_fact(fact_index: int) -> None
    """
    Delete the fact at index from instance.facts.
    Sets instance._dirty = True.
    Raises IndexError if fact_index out of range.
    """

  mark_saved(path: Path) -> None
    """
    Set instance.source_path = path, instance._dirty = False.
    Called by InstanceSerializer.save() on success.
    """
```

**Signal** (PySide6 `Signal` object, attached by the main window): `changes_made = Signal()` — emitted after every mutating call.

### `EditOperation` *(scaffolded in v1; not used for undo/redo yet)*

| Field | Type | Description |
|-------|------|-------------|
| `operation_type` | `Literal['add', 'update', 'remove']` | Type of edit |
| `fact_index` | `int \| None` | Index in `instance.facts` (None for add-new) |
| `previous_value` | `str \| None` | Value before edit (None for new facts) |
| `new_value` | `str \| None` | Value after edit (None for removes) |
| `concept` | `QName` | Concept the fact belongs to |
| `context_ref` | `ContextId` | Context reference |
| `timestamp` | `datetime` | When the operation occurred |

---

## `XbrlInstance` Additions (Feature 002 model extended)

Two new fields are added to `XbrlInstance`:

| Field | Type | Description |
|-------|------|-------------|
| `orphaned_facts` | `list[OrphanedFact]` | Facts whose concept is not in the taxonomy (preserved on save) |
| `edit_history` | `list[EditOperation]` | Audit trail of all edits in the current session (scaffolded; not displayed in v1) |

The `add_fact` / `update_fact` / `remove_fact` / `mark_saved` methods from Feature 002's mutation contract are implemented here in `InstanceEditor` rather than directly on the model.

---

## Error Types

| Error Class | Extends | When Raised |
|-------------|---------|-------------|
| `InstanceParseError` | `Exception` | XML not well-formed, missing `xbrli:xbrl` root, missing `link:schemaRef` |
| `TaxonomyResolutionError` | `InstanceParseError` | schemaRef could not be resolved to a local taxonomy path |
| `DuplicateFactError` | `Exception` | `add_fact()` called for a concept+context that already has a fact |
| `InvalidFactValueError` | `Exception` | `update_fact()` called with a value that fails XBRL type validation |

---

## Cell Edit Delegate Model (PySide6 layer)

### `CellEditDelegate` (QStyledItemDelegate)
Installed on the body `QTableView` in `XbrlTableView`. Manages type-appropriate editor creation, validation, and routing edits to `InstanceEditor`.

```
CellEditDelegate(taxonomy: TaxonomyStructure, editor: InstanceEditor, parent=None)
  → QStyledItemDelegate subclass

  createEditor(parent, option, index)
    → QLineEdit (monetary/decimal/integer/string)
    → QDateEdit  (date)
    → QComboBox  (boolean)

  setEditorData(editor, index)
    # Populates editor with index's Qt.UserRole (raw fact value string or "")

  setModelData(editor, model, index)
    # Validates; if invalid → red border + tooltip + setFocus() (keep editor open)
    # If valid → normalise to XBRL canonical; call InstanceEditor.update_fact()
    #            or InstanceEditor.add_fact(); call model.refresh_instance()

  updateEditorGeometry(editor, option, index)
    # Position editor exactly over the cell rect

  eventFilter(obj, event)
    # Intercept QEvent.FocusOut when editor has invalid input → re-focus editor
```

### `XbrlTypeValidator`
Pure Python. Maps a concept `QName` → data type → validation function.

```
XbrlTypeValidator(taxonomy: TaxonomyStructure)

  validate(value: str, concept: QName) -> tuple[bool, str]
    """
    Returns (is_valid, error_message).
    error_message is "" when is_valid is True.
    """

  normalise(value: str, concept: QName) -> str
    """
    Convert locale-formatted input to XBRL canonical string.
    E.g., "1.234,56" (Spanish) → "1234.56"
    Never raises; returns value unchanged if normalisation fails.
    """
```

---

## Entity Relationships (additions to Features 001–003)

```
XbrlInstance (Feature 002, extended)
  ├── Fact [0..*]                     # now populated from parsed instance or user edits
  ├── OrphanedFact [0..*]             # concepts not in taxonomy (preserved verbatim)
  └── EditOperation [0..*]            # audit trail (scaffolded)

InstanceParser ──reads──▶ XML file ──produces──▶ XbrlInstance + list[OrphanedFact]
InstanceEditor ──mutates──▶ XbrlInstance (facts, dirty flag)
CellEditDelegate ──calls──▶ InstanceEditor
                ──reads──▶ XbrlTypeValidator
                ──notifies──▶ XbrlTableView.refresh_instance()
```

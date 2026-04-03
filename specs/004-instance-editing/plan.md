# Implementation Plan: Instance Editing

**Branch**: `004-instance-editing` | **Date**: 2026-03-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/004-instance-editing/spec.md`

## Summary

Implement the full instance editing workflow, integrating Features 001–003 into a coherent open/view/edit/save loop. An `InstanceParser` reads an existing XBRL 2.1 XML file into a populated `XbrlInstance`, resolving the bound taxonomy via `TaxonomyLoader`. An `InstanceEditor` service provides all mutation operations (add/update/remove fact) while maintaining the dirty-state invariant. A `CellEditDelegate` (`QStyledItemDelegate` subclass) enables inline cell editing in the table view with per-type XBRL validation. The main window gains a close-guard prompt, a window-title dirty indicator, and save/save-as actions.

**Tech stack**: Python 3.11+ · PySide6 (`QStyledItemDelegate`, `QDoubleValidator`, `QDateEdit`, `QComboBox`, `QMessageBox`) · lxml (instance XML parsing) · `decimal.Decimal` (edit-time normalisation only)

---

## Technical Context

**Language/Version**: Python 3.11+
**New dependencies**: none — all required libraries already in the stack
**Storage**: `XbrlInstance` in memory; round-trip to/from XBRL 2.1 XML via lxml
**Testing**: pytest + pytest-qt; unit tests for `InstanceParser`, `XbrlTypeValidator`, `InstanceEditor`; integration tests for parse→edit→save round-trip
**Performance goals**: Instance of 10,000 facts loaded and first table rendered in <15 seconds (SC-001); cell edit confirmed in <1 second (SC-002)
**Constraints**: All numeric fact values stored as `str` to preserve xs:decimal precision (never as `float`); orphaned facts preserved verbatim on save (FR-015)
**Scale/Scope**: Instances up to 10,000 facts; up to 20 tables; single instance open at a time

---

## Constitution Check

*Constitution still unfilled — same note as previous features.*

**Informal gates applied**:
- ✅ `InstanceParser` and `InstanceEditor` have zero PySide6 dependencies — testable without Qt
- ✅ `XbrlTypeValidator.validate()` and `.normalise()` never raise — safe for delegate calls
- ✅ No `float` anywhere in the fact value pipeline — xs:decimal precision preserved
- ✅ `InstanceEditor` is the sole mutation path — no direct field writes to `instance.facts`
- ✅ Feature 002's `InstanceSerializer` is reused unchanged — no duplicate serialisation code

---

## Project Structure

### Documentation (this feature)

```text
specs/004-instance-editing/
├── spec.md
├── plan.md              ← this file
├── research.md          ← Phase 0: lxml fact parsing, schemaRef resolution,
│                                   QStyledItemDelegate, QDoubleValidator,
│                                   XBRL type mapping, dirty tracking, round-trip accuracy
├── data-model.md        ← Phase 1: InstanceParser, InstanceEditor, OrphanedFact,
│                                   EditOperation, CellEditDelegate, XbrlTypeValidator
├── contracts/
│   └── instance-editing-api.md  ← Phase 1: InstanceParser, InstanceEditor,
│                                             XbrlTypeValidator, CellEditDelegate
└── tasks.md             ← Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code (additions to project)

```text
src/
└── bde_xbrl_editor/
    ├── taxonomy/          # Feature 001 (unchanged)
    ├── table_renderer/    # Feature 003 (unchanged)
    ├── instance/          # Feature 002 base + Feature 004 additions
    │   ├── __init__.py    # updated: re-exports InstanceParser, InstanceEditor, XbrlTypeValidator
    │   ├── models.py      # extended: adds orphaned_facts, edit_history to XbrlInstance;
    │   │                  #           adds OrphanedFact, EditOperation dataclasses
    │   ├── factory.py     # Feature 002 (unchanged)
    │   ├── serializer.py  # Feature 002 — minor update: appends orphaned_facts raw XML on save
    │   ├── parser.py      # ← NEW: InstanceParser (lxml-based XBRL instance reader)
    │   ├── editor.py      # ← NEW: InstanceEditor (add/update/remove fact; dirty flag)
    │   ├── validator.py   # ← NEW: XbrlTypeValidator (validate + normalise per XBRL type)
    │   ├── context_builder.py  # Feature 002 (unchanged)
    │   └── constants.py        # Feature 002 (unchanged)
    └── ui/
        ├── main_window.py           # UPDATED: File→Open, File→Save, File→Save As,
        │                            #   closeEvent guard, setWindowModified, dirty signal,
        │                            #   open-instance panel layout, CellEditDelegate wiring
        └── widgets/
            ├── cell_edit_delegate.py    # ← NEW: CellEditDelegate (QStyledItemDelegate)
            ├── instance_info_panel.py   # ← NEW: entity, period, filing indicators, table list
            └── instance_creation_wizard/  # Feature 002 (unchanged)

tests/
├── unit/
│   └── instance/
│       ├── test_parser.py       # InstanceParser: contexts, units, facts, orphans, filing indicators
│       ├── test_editor.py       # InstanceEditor: add/update/remove, dirty flag, duplicate guard
│       ├── test_validator.py    # XbrlTypeValidator: all 6 types, normalise locale
│       └── test_serializer.py   # updated: orphaned facts round-trip
└── integration/
    └── instance/
        └── test_edit_roundtrip.py  # Parse → edit facts → save → re-parse → verify values
```

---

## Complexity Tracking

> No constitution violations to justify.

---

## Phase 0 Summary — Resolved Decisions

| Decision | Resolved To |
|----------|-------------|
| Instance XML parsing | lxml Clark-notation tag filtering; non-metadata namespace children are facts |
| Filing indicator detection | Clark tag: `{http://www.eurofiling.info/xbrl/ext/filing-indicators}filingIndicator` |
| schemaRef resolution | `instance_dir / href` (relative); absolute; fallback to manual folder picker; no network |
| Inline cell editing | `QStyledItemDelegate` subclass; type-specific widget per XBRL concept type |
| Numeric validation | `QDoubleValidator(locale)` monetary/decimal; `QIntValidator` integer |
| Boolean editor | `QComboBox(["true", "false"])` |
| Date editor | `QDateEdit` with `YYYY-MM-DD` display format |
| Invalid input UX | Red border + tooltip; `eventFilter` intercepts `FocusOut` to keep editor open |
| Numeric storage | Raw `str` throughout; `decimal.Decimal` only at edit-time normalisation |
| Dirty tracking | `XbrlInstance._dirty` + `InstanceEditor.changes_made` signal + `setWindowModified()` |
| Close guard | `closeEvent()` override with `QMessageBox(Save / Discard / Cancel)` |

---

## Phase 1 Summary — Design Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Data model | `specs/004-instance-editing/data-model.md` | ✅ Complete |
| Editing API contract | `specs/004-instance-editing/contracts/instance-editing-api.md` | ✅ Complete |

### Key design decisions

1. **`InstanceParser` is stateless** — reusable for multiple files; the `TaxonomyLoader` it wraps is the shared session cache from Feature 001.
2. **`InstanceEditor` is the sole mutation path** — `instance.facts` is never written outside this class; ensures `_dirty` is always consistent.
3. **No `float` in the fact pipeline** — values enter as `str` (XML), stay `str` in memory, exit as `str` (XML). `decimal.Decimal` is used only transiently to normalise user input.
4. **`CellEditDelegate` keeps editor open on invalid input** — overrides `eventFilter` to intercept `FocusOut`; red border and tooltip remain until the user fixes or cancels.
5. **Orphaned facts survive every save** — `InstanceSerializer` appends `OrphanedFact.raw_element_xml` after all known facts; never discarded silently.
6. **`InstanceParser` and `InstanceEditor` have zero Qt imports** — fully testable in pytest without a display server.

# Implementation Plan: XBRL Instance Creation

**Branch**: `002-xbrl-instance-creation` | **Date**: 2026-03-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/002-xbrl-instance-creation/spec.md`

## Summary

Implement the XBRL instance creation workflow, building on the `TaxonomyStructure` delivered by Feature 001. A `QWizard`-based UI guides the user through four steps (entity/period → table selection → dimensional configuration → save). An `InstanceFactory` validates inputs against the taxonomy and generates all required XBRL contexts and filing indicators. An `InstanceSerializer` writes a well-formed XBRL 2.1 XML file via lxml. The result is a new `XbrlInstance` object — empty of facts but structurally complete — that subsequent features (table rendering, editing, validation) operate on.

**Tech stack**: Python 3.11+ · PySide6 (QWizard) · lxml (XML serialisation) · dataclasses (instance model)

---

## Technical Context

**Language/Version**: Python 3.11+ (unchanged from Feature 001)
**Primary Dependencies**: PySide6 (QWizard UI), lxml (XBRL XML serialisation), dataclasses (stdlib)
**New dependencies**: none — all required libraries already established in Feature 001
**Storage**: In-memory `XbrlInstance` dataclass; serialised to local filesystem as XBRL 2.1 XML on save
**Testing**: pytest, pytest-qt (wizard page validation tests)
**Target Platform**: macOS, Windows, Linux desktop (unchanged)
**Project Type**: Desktop application (unchanged)
**Performance Goals**: Instance creation wizard completes and instance is ready in under 5 minutes for a 20-table taxonomy (SC-001 from spec); XML serialisation is instantaneous for an empty instance
**Constraints**: No facts at creation time (only contexts, units, filing indicators); must produce structurally valid XBRL 2.1 XML that passes well-formedness validation (SC-002)
**Scale/Scope**: Up to 20 tables per instance at creation; up to 10 Z-axis dimension values per table

---

## Constitution Check

*Constitution is still an unfilled template — same note as Feature 001 applies.*

**Informal gates applied**:
- ✅ Depends cleanly on Feature 001's public API (`TaxonomyStructure`, `QName`, `HypercubeModel`) — no internal sub-module imports
- ✅ `InstanceFactory` and `InstanceSerializer` are separate concerns (creation vs I/O)
- ✅ Wizard UI has no business logic — delegates entirely to `InstanceFactory`
- ✅ No new external dependencies needed

---

## Project Structure

### Documentation (this feature)

```text
specs/002-xbrl-instance-creation/
├── plan.md              ← this file
├── research.md          ← Phase 0: XBRL instance structure, filing indicators, QWizard
├── data-model.md        ← Phase 1: XbrlInstance, XbrlContext, FilingIndicator, Fact, etc.
├── contracts/
│   └── instance-api.md  ← Phase 1: InstanceFactory, InstanceSerializer, QWizard interface
└── tasks.md             ← Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code (additions to Feature 001 structure)

```text
src/
└── bde_xbrl_editor/
    ├── taxonomy/                       # Feature 001 (unchanged)
    ├── instance/                       # ← Feature 002 scope
    │   ├── __init__.py                 # re-exports: XbrlInstance, InstanceFactory, InstanceSerializer
    │   ├── models.py                   # XbrlInstance, XbrlContext, ReportingEntity,
    │   │                               #   ReportingPeriod, FilingIndicator,
    │   │                               #   DimensionalConfiguration, XbrlUnit, Fact
    │   ├── factory.py                  # InstanceFactory — validates inputs, generates contexts/units/indicators
    │   ├── serializer.py               # InstanceSerializer — lxml XML serialisation + file I/O
    │   ├── context_builder.py          # Generates XbrlContext list from entity+period+dimensional configs
    │   └── constants.py                # Namespace URIs (XBRLI_NS, XBRLDI_NS, FILING_IND_NS, …)
    └── ui/
        ├── main_window.py              # Updated: adds "New Instance" menu action → opens wizard
        └── widgets/
            ├── taxonomy_loader_widget.py  # Feature 001 (unchanged)
            ├── progress_dialog.py         # Feature 001 (unchanged)
            └── instance_creation_wizard/
                ├── __init__.py
                ├── wizard.py               # InstanceCreationWizard (QWizard subclass)
                ├── page_entity_period.py   # Step 1: entity identifier + reporting period
                ├── page_table_selection.py # Step 2: table checklist from taxonomy
                ├── page_dimensional.py     # Step 3: per-table Z-axis dimension pickers
                └── page_save.py            # Step 4: file path selection + confirm

tests/
├── unit/
│   └── instance/
│       ├── test_factory.py            # InstanceFactory validation (period types, dim members, contexts)
│       ├── test_context_builder.py    # Context generation + deduplication
│       ├── test_serializer.py         # XML output well-formedness, namespace declarations
│       └── test_models.py             # XbrlInstance state transitions, has_unsaved_changes
└── integration/
    └── instance/
        └── test_instance_roundtrip.py # Create instance → save → reopen → verify structure preserved
```

**Structure Decision**: Single `instance/` sub-package added to the existing `bde_xbrl_editor` package. The wizard UI lives under `ui/widgets/instance_creation_wizard/` as a sub-package (multiple pages warrant a directory). Business logic (`InstanceFactory`, `InstanceSerializer`) is fully separate from the UI and is testable without PySide6.

---

## Complexity Tracking

> No constitution violations to justify.

---

## Phase 0 Summary — Resolved Decisions

| Decision | Resolved To |
|----------|-------------|
| Instance XML structure | xbrli:xbrl root + schemaRef + contexts + units + facts (lxml etree) |
| Dimensional encoding | `xbrldi:explicitMember` in `xbrli:scenario` (or `segment` per `HypercubeModel.context_element`) |
| Filing indicators | `ef-find:filingIndicator` in `http://www.eurofiling.info/xbrl/ext/filing-indicators` |
| Context ID generation | Deterministic SHA-256 hash of (scheme, identifier, period, sorted dimensions) → `ctx_<8-hex>` |
| Units pre-population | Pre-generate units for all numeric concepts in selected tables at creation time |
| Instance model | Python `@dataclass` classes (not Pydantic); `_dirty` flag for unsaved-change tracking |
| XML serialisation | lxml etree with `nsmap` on root; `etree.tostring(pretty_print=True, xml_declaration=True)` |
| UI wizard | `QWizard` with 4 `QWizardPage` subclasses; `validatePage()` for step-level validation |

---

## Phase 1 Summary — Design Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Data model | `specs/002-xbrl-instance-creation/data-model.md` | ✅ Complete |
| Instance API contract | `specs/002-xbrl-instance-creation/contracts/instance-api.md` | ✅ Complete |

### Key design decisions

1. **`InstanceFactory` never produces an invalid instance** — it raises typed errors for every constraint violation; the returned `XbrlInstance` is always structurally sound.
2. **`InstanceSerializer.to_xml()` is pure** — no file I/O, no side effects; the wizard can call it to preview the output before the user selects a save path.
3. **Context IDs are deterministic** — same inputs always produce the same context ID, making save/reload round-trips stable and diff-friendly.
4. **Wizard holds no state** — all state lives in a `XbrlInstance` draft that the wizard builds up step by step; the wizard passes the completed instance to the caller via `created_instance` property.
5. **Business logic is UI-free** — `InstanceFactory` and `InstanceSerializer` import nothing from PySide6; all wizard pages call these services and display the results, not the other way around.

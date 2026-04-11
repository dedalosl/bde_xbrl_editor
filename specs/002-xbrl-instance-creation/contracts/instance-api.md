# Contract: Instance Module Public API

**Branch**: `002-xbrl-instance-creation` | **Phase**: 1 | **Date**: 2026-03-25
**Module**: `bde_xbrl_editor.instance`

This document defines the public Python interface that the instance creation feature exposes to the rest of the application (UI, table renderer, validator). All other modules must use only the interfaces defined here.

**Depends on**: `bde_xbrl_editor.taxonomy` (Feature 001) — consumes `TaxonomyStructure`, `QName`, `HypercubeModel`, `TableDefinitionPWD`.

---

## Primary Entry Points

### `InstanceFactory`

Creates new `XbrlInstance` objects. Validates inputs against the bound `TaxonomyStructure`.

```
InstanceFactory(taxonomy: TaxonomyStructure)

Methods:
  create(
    entity: ReportingEntity,
    period: ReportingPeriod,
    included_table_ids: list[str],
    dimensional_configs: dict[str, DimensionalConfiguration],
  ) -> XbrlInstance
    """
    Create a new empty XbrlInstance bound to the loaded taxonomy.
    Validates:
      - period type matches taxonomy declaration
      - all included_table_ids exist in the taxonomy
      - all mandatory Z-axis dimensions have a value in dimensional_configs
      - all assigned dimension members are valid (in allowed member list)
    Generates:
      - schema_ref_href from taxonomy.metadata.entry_point_path
      - all XbrlContext objects (filing-indicator context + per-table contexts)
      - all XbrlUnit objects for numeric concepts in selected tables
      - FilingIndicator elements for all included tables (filed=True)
    Returns a new XbrlInstance with _dirty=True, source_path=None, facts=[].
    Raises:
      InvalidReportingPeriodError   — period incompatible with taxonomy
      InvalidEntityIdentifierError  — entity identifier or scheme missing
      MissingDimensionValueError    — mandatory Z-axis dimension has no value
      InvalidDimensionMemberError   — member not in allowed list for dimension
    """
```

### `InstanceSerializer`

Converts an `XbrlInstance` to/from XBRL 2.1 XML.

```
InstanceSerializer()

Methods:
  save(instance: XbrlInstance, path: str | Path) -> None
    """
    Serialise instance to well-formed XBRL 2.1 XML and write to path.
    Sets instance.source_path = path and instance._dirty = False on success.
    Raises:
      InstanceSaveError — file write failed (permission, disk space, etc.)
    """

  to_xml(instance: XbrlInstance) -> bytes
    """
    Serialise instance to well-formed XBRL 2.1 XML bytes without writing to disk.
    Raises no I/O errors.
    """
```

---

## Read Interface: `XbrlInstance`

All public fields are readable. `_dirty` is private but observable via `has_unsaved_changes` property.

```
XbrlInstance:
  .taxonomy_entry_point: Path           # bound taxonomy entry-point path
  .schema_ref_href: str                 # xlink:href for schemaRef element
  .entity: ReportingEntity              # reporting entity
  .period: ReportingPeriod             # reporting period
  .filing_indicators: list[FilingIndicator]
  .included_table_ids: list[str]        # ordered table IDs
  .dimensional_configs: dict[str, DimensionalConfiguration]
  .contexts: dict[ContextId, XbrlContext]
  .units: dict[UnitId, XbrlUnit]
  .facts: list[Fact]                    # empty at creation; populated by Feature 004
  .source_path: Path | None
  .has_unsaved_changes: bool            # property wrapping _dirty
```

### Mutation contract (for Feature 004 — Instance Editing)

Features that mutate an `XbrlInstance` must call the following methods rather than directly modifying fields. This ensures `_dirty` is always set correctly.

```
XbrlInstance (mutation methods — used by Feature 004):
  .add_fact(fact: Fact) -> None
  .update_fact(index: int, new_value: str) -> None
  .remove_fact(index: int) -> None
  .mark_saved(path: Path) -> None         # called by InstanceSerializer.save()
```

---

## Wizard API (UI-layer contract)

The `QWizard` subclass exposes only two methods to the rest of the UI:

```
InstanceCreationWizard(taxonomy: TaxonomyStructure, parent: QWidget | None = None)
  → QWizard subclass

  .exec() -> int
    """
    Open the wizard modally. Returns QDialog.Accepted or QDialog.Rejected.
    """

  .created_instance: XbrlInstance | None
    """
    The newly created instance if wizard was accepted; None if cancelled.
    Available only after exec() returns QDialog.Accepted.
    """
```

The wizard internally uses `InstanceFactory` and `InstanceSerializer`; the UI layer does not need to call these directly.

---

## Error Hierarchy

```
InstanceCreationError (base)
  ├── InvalidReportingPeriodError
  │     .period_type_required: str      # what taxonomy declares
  │     .period_type_provided: str      # what user provided
  ├── InvalidEntityIdentifierError
  │     .reason: str
  ├── MissingDimensionValueError
  │     .table_id: str
  │     .dimension_qname: QName
  └── InvalidDimensionMemberError
        .table_id: str
        .dimension_qname: QName
        .provided_member: QName
        .allowed_members: list[QName]

InstanceSaveError
  .path: str
  .reason: str
```

---

## Namespace Constants

```python
# bde_xbrl_editor.instance.constants

XBRLI_NS        = "http://www.xbrl.org/2003/instance"
LINK_NS         = "http://www.xbrl.org/2003/linkbase"
XLINK_NS        = "http://www.w3.org/1999/xlink"
XBRLDI_NS       = "http://xbrl.org/2006/xbrldi"
ISO4217_NS      = "http://www.xbrl.org/2003/iso4217"
FILING_IND_NS   = "http://www.eurofiling.info/xbrl/ext/filing-indicators"
FILING_IND_PFX  = "ef-find"
```

---

## Usage Example (UI pseudocode)

```python
# After taxonomy is loaded (Feature 001) and user opens creation wizard:
wizard = InstanceCreationWizard(taxonomy=app_state.current_taxonomy, parent=main_window)
if wizard.exec() == QDialog.Accepted:
    instance = wizard.created_instance      # already saved if user completed wizard
    app_state.open_instance = instance
    table_browser.set_instance(instance)
```

---

## Invariants and Guarantees

- `InstanceFactory.create()` never produces a structurally invalid instance — if it returns without raising, the result passes XBRL 2.1 structural well-formedness checks.
- `InstanceSerializer.to_xml()` **never raises** for an instance produced by `InstanceFactory.create()`.
- `XbrlInstance.has_unsaved_changes` is `True` immediately after `InstanceFactory.create()` (new instance not yet saved); `False` after `InstanceSerializer.save()`.
- Context IDs are **deterministic and stable**: the same (entity, period, dimensions) always produces the same context ID, making round-trip save/reload consistent.

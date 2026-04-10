# Data Model: XBRL Instance Creation

**Branch**: `002-xbrl-instance-creation` | **Phase**: 1 | **Date**: 2026-03-25

---

## Overview

All entities below are mutable Python dataclasses. They form the in-memory representation of a new or loaded XBRL instance. The `XbrlInstance` is the root object; it is constructed empty by `InstanceFactory` and progressively filled during the creation wizard. It is later populated with facts by Feature 004 (Instance Editing). Serialisation to XML is handled by `InstanceSerializer` (separate from the model).

Feature 001 types (`QName`, `TaxonomyStructure`, `TableDefinitionPWD`) are consumed directly; they are **not** redefined here.

---

## Identifier Types

### `ContextId`
A `str` alias. Context IDs are auto-generated as deterministic short hashes from the context's components (entity scheme, identifier, period, dimensions). Format: `ctx_<sha256[:8]>`. Uniqueness is guaranteed within a single instance.

### `UnitId`
A `str` alias. Unit IDs are auto-generated from the measure URI. Examples: `"EUR"` for `iso4217:EUR`, `"pure"` for `xbrli:pure`.

---

## Core Instance Model

### `XbrlInstance`
The root mutable object representing one open XBRL instance document.

| Field | Type | Description |
|-------|------|-------------|
| `taxonomy_entry_point` | `Path` | Absolute path of the bound taxonomy entry point |
| `schema_ref_href` | `str` | The `xlink:href` value for `link:schemaRef` in the output XML |
| `entity` | `ReportingEntity` | The reporting entity (shared across all contexts) |
| `period` | `ReportingPeriod` | The reporting period (shared across all contexts) |
| `filing_indicators` | `list[FilingIndicator]` | Tables declared as filed/not-filed |
| `included_table_ids` | `list[str]` | Ordered list of taxonomy table IDs selected for this instance |
| `dimensional_configs` | `dict[str, DimensionalConfiguration]` | Table ID → Z-axis dimension assignments |
| `contexts` | `dict[ContextId, XbrlContext]` | All generated XBRL contexts |
| `units` | `dict[UnitId, XbrlUnit]` | All units referenced in the instance |
| `facts` | `list[Fact]` | All facts (empty at creation time; populated in Feature 004) |
| `source_path` | `Path \| None` | Where the instance was loaded from / last saved to (`None` for new) |
| `_dirty` | `bool` | `True` if there are unsaved changes since last save (not serialised to XML) |

**State transitions**:
```
NEW (source_path=None, _dirty=False)
  → CONFIGURED (after wizard completes, contexts generated, _dirty=True)
  → SAVED (after first save, source_path set, _dirty=False)
  → MODIFIED (_dirty=True after any fact edit in Feature 004)
  → SAVED again
```

---

## Entity and Period

### `ReportingEntity`

| Field | Type | Description |
|-------|------|-------------|
| `identifier` | `str` | Entity code (BDE-assigned or LEI) |
| `scheme` | `str` | URI identifying the identifier scheme (e.g., `http://www.bde.es/`) |

**Validation**: `identifier` must be non-empty; `scheme` must be a valid URI. The BDE scheme URI is sourced from the taxonomy metadata (Feature 001).

### `ReportingPeriod`

| Field | Type | Description |
|-------|------|-------------|
| `period_type` | `Literal['instant', 'duration']` | Constrained by the taxonomy's declared period type |
| `instant_date` | `date \| None` | Date for instant periods |
| `start_date` | `date \| None` | Start of duration periods |
| `end_date` | `date \| None` | End of duration periods |

**Validation**: If `period_type == 'instant'`, `instant_date` must be set. If `period_type == 'duration'`, both `start_date` and `end_date` must be set and `end_date >= start_date`.

---

## Filing Indicators

### `FilingIndicator`

| Field | Type | Description |
|-------|------|-------------|
| `template_id` | `str` | The table/report identifier as declared in the taxonomy |
| `filed` | `bool` | `True` if the table is included in this submission (default `True`) |
| `context_ref` | `ContextId` | Reference to the filing-indicator context (entity+period, no dimensions) |

**Encoding**: Serialises to `<ef-find:filingIndicator contextRef="{context_ref}" filed="{filed}">{template_id}</ef-find:filingIndicator>` in namespace `http://www.eurofiling.info/xbrl/ext/filing-indicators`.

---

## Dimensional Configuration

### `DimensionalConfiguration`
The Z-axis dimensional assignments for a single report table. Configures what XBRL context(s) are generated for that table.

| Field | Type | Description |
|-------|------|-------------|
| `table_id` | `str` | The taxonomy table ID this config applies to |
| `dimension_assignments` | `dict[QName, QName]` | Dimension concept QName → selected member QName |

**Validation**: For each dimension in the table's Z-axis that is declared mandatory (no default member), a value must be assigned. Assigning a member not in the dimension's `DomainMember` list is invalid.

---

## XBRL Contexts

### `XbrlContext`
One generated XBRL context element. Contexts are derived from the entity, period, and dimensional configuration.

| Field | Type | Description |
|-------|------|-------------|
| `context_id` | `ContextId` | Unique identifier within the instance (auto-generated) |
| `entity` | `ReportingEntity` | Entity reference |
| `period` | `ReportingPeriod` | Period reference |
| `dimensions` | `dict[QName, QName]` | Dimension → member assignments (`{}` for the base filing-indicator context) |
| `context_element` | `Literal['scenario', 'segment']` | Where dimensions are encoded (read from `HypercubeModel.context_element`) |

**Context generation rules**:
1. One **filing-indicator context** is always generated: entity + period, no dimensions.
2. For each table with a `DimensionalConfiguration`, one context per unique dimension combination is generated.
3. Context deduplication: if two tables produce identical (entity, period, dimensions), they share a single context.

---

## Units

### `XbrlUnit`

| Field | Type | Description |
|-------|------|-------------|
| `unit_id` | `UnitId` | Short identifier used as `@id` in XML (e.g., `"EUR"`) |
| `measure_uri` | `str` | Full measure URI (e.g., `iso4217:EUR`, `xbrli:pure`) |

**Pre-population rule**: At instance creation, units are pre-populated for all numeric concept types referenced by the selected tables' row/column concepts. This avoids having to add units incrementally as facts are entered.

---

## Facts (created empty in Feature 002; populated in Feature 004)

### `Fact`

| Field | Type | Description |
|-------|------|-------------|
| `concept` | `QName` | The taxonomy concept this fact reports |
| `context_ref` | `ContextId` | Reference to the applicable context |
| `unit_ref` | `UnitId \| None` | Reference to unit (`None` for non-numeric concepts) |
| `value` | `str` | String representation of the fact value |
| `decimals` | `str \| None` | Decimal attribute (e.g., `"-3"`, `"INF"`) for numeric facts |
| `precision` | `str \| None` | Precision attribute (mutually exclusive with decimals) |

**Note**: `Fact` is defined here for completeness; it is only populated in Feature 004 (Instance Editing). Feature 002 creates instances with an empty `facts` list.

---

## Error Types

| Error Class | Extends | When Raised |
|-------------|---------|-------------|
| `InstanceCreationError` | `Exception` | Base class for instance creation failures |
| `InvalidReportingPeriodError` | `InstanceCreationError` | Period type incompatible with taxonomy declaration, or end date before start date |
| `InvalidEntityIdentifierError` | `InstanceCreationError` | Entity identifier is empty or scheme is missing |
| `MissingDimensionValueError` | `InstanceCreationError` | A mandatory Z-axis dimension has no value assigned |
| `InvalidDimensionMemberError` | `InstanceCreationError` | Assigned member is not in the dimension's allowed member list |
| `InstanceSaveError` | `Exception` | File write failed (permission error, disk full, etc.) |

---

## Entity Relationships

```
XbrlInstance
  ├── ReportingEntity [1]
  ├── ReportingPeriod [1]
  ├── FilingIndicator [0..*]
  ├── DimensionalConfiguration [0..*] (keyed by table_id)
  │     └── dimension_assignments: dict[QName → QName]
  ├── XbrlContext [1..*] (keyed by ContextId)
  │     ├── ReportingEntity [ref]
  │     ├── ReportingPeriod [ref]
  │     └── dimensions: dict[QName → QName]
  ├── XbrlUnit [0..*] (keyed by UnitId)
  └── Fact [0..*] (empty at creation; populated in Feature 004)
```

---

## Serialisation Mapping (Instance → XBRL 2.1 XML)

| Model field | XML output |
|-------------|------------|
| `schema_ref_href` | `<link:schemaRef xlink:href="{href}" xlink:type="simple"/>` |
| `XbrlContext` | `<xbrli:context id="{context_id}"><xbrli:entity>...</xbrli:entity><xbrli:period>...</xbrli:period>[<xbrli:scenario><xbrldi:explicitMember dimension="{dim}">{member}</xbrldi:explicitMember>...</xbrli:scenario>]</xbrli:context>` |
| `ReportingPeriod (instant)` | `<xbrli:period><xbrli:instant>{date}</xbrli:instant></xbrli:period>` |
| `ReportingPeriod (duration)` | `<xbrli:period><xbrli:startDate>{start}</xbrli:startDate><xbrli:endDate>{end}</xbrli:endDate></xbrli:period>` |
| `XbrlUnit (monetary)` | `<xbrli:unit id="{unit_id}"><xbrli:measure>iso4217:{currency}</xbrli:measure></xbrli:unit>` |
| `XbrlUnit (pure)` | `<xbrli:unit id="pure"><xbrli:measure>xbrli:pure</xbrli:measure></xbrli:unit>` |
| `FilingIndicator` | `<ef-find:filingIndicator contextRef="{ctx}" filed="{true/false}">{template_id}</ef-find:filingIndicator>` |
| `Fact` | `<{concept} contextRef="{ctx}" [unitRef="{unit}"] [decimals="{n}"]>{value}</{concept}>` |

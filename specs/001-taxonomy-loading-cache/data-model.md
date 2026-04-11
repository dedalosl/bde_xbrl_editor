# Data Model: Taxonomy Loading and Caching

**Branch**: `001-taxonomy-loading-cache` | **Phase**: 1 | **Date**: 2026-03-25

---

## Overview

All entities below are immutable Python dataclasses (or frozen dataclasses where identity equality is not needed). They are constructed during taxonomy loading and cached as part of `TaxonomyStructure`. No entity is modified after construction; editing features (Features 002–004) work on separate mutable instance models.

---

## Core Identifier Types

### `QName`
The fundamental identifier for XBRL concepts, roles, arcroles, and dimensions.

| Field | Type | Description |
|-------|------|-------------|
| `namespace` | `str` | XML namespace URI |
| `local_name` | `str` | Local part of the qualified name |
| `prefix` | `str \| None` | Namespace prefix (display only; not part of identity) |

**Identity**: Two `QName` objects are equal if `namespace` and `local_name` match; `prefix` is ignored for equality. `QName` is hashable (used as dict key throughout).

---

## Concept Model

### `Concept`
An XBRL element declaration (a concept in taxonomy terms).

| Field | Type | Description |
|-------|------|-------------|
| `qname` | `QName` | Fully qualified concept name (primary key) |
| `data_type` | `QName` | XSD or XBRL type (e.g., `xbrli:monetaryItemType`) |
| `period_type` | `Literal['instant', 'duration']` | Period constraint |
| `balance` | `Literal['debit', 'credit'] \| None` | Balance attribute (monetary only) |
| `abstract` | `bool` | Whether the concept is abstract |
| `nillable` | `bool` | Whether nil values are permitted |
| `substitution_group` | `QName \| None` | Substitution group (e.g., `xbrli:item`, `xbrli:tuple`) |

---

## Label Model

### `Label`
A single label string for a concept in a specific language and role.

| Field | Type | Description |
|-------|------|-------------|
| `text` | `str` | Human-readable label text |
| `language` | `str` | BCP 47 language tag (e.g., `"es"`, `"en"`) |
| `role` | `str` | Label role URI (e.g., `http://www.xbrl.org/2003/role/label`) |
| `source` | `Literal['standard', 'generic']` | Whether from standard or generic linkbase |
| `priority` | `int` | Arc priority (higher wins in conflict; 0 by default) |

### `LabelResolver`
The runtime label lookup service built from all loaded label linkbases.

**Lookup contract**: `resolve(qname, role, language_preference) -> str | None`
- Iterates `language_preference` list (e.g., `["es", "en"]`) until a match is found
- For the same role + language, standard and generic labels are merged; higher `priority` wins; ties broken by `@use="prohibited"` propagation
- Falls back to QName string representation if no label found

**Standard label roles supported** (all 8 XBRL 2.1 roles):
- `http://www.xbrl.org/2003/role/label` (`label`)
- `http://www.xbrl.org/2003/role/terseLabel` (`terseLabel`)
- `http://www.xbrl.org/2003/role/verboseLabel` (`verboseLabel`)
- `http://www.xbrl.org/2003/role/documentation` (`documentation`)
- `http://www.xbrl.org/2003/role/periodStartLabel` (`periodStartLabel`)
- `http://www.xbrl.org/2003/role/periodEndLabel` (`periodEndLabel`)
- `http://www.xbrl.org/2003/role/totalLabel` (`totalLabel`)
- `http://www.xbrl.org/2003/role/negatedLabel` (`negatedLabel`)

**RC-code label role** (Eurofiling):
- `http://www.eurofiling.info/xbrl/role/rc-code` — row/column codes on leaf header nodes

---

## Linkbase Models

### `PresentationArc`

| Field | Type | Description |
|-------|------|-------------|
| `parent` | `QName` | Source concept (parent in hierarchy) |
| `child` | `QName` | Target concept (child in hierarchy) |
| `order` | `float` | Sibling ordering |
| `preferred_label` | `str \| None` | Label role to display for this arc |
| `extended_link_role` | `str` | ELR URI grouping this arc |

### `PresentationNetwork`
A set of presentation arcs for a single extended link role, exposing the root concepts and the ordered child list for any concept.

### `CalculationArc`

| Field | Type | Description |
|-------|------|-------------|
| `parent` | `QName` | Summation concept |
| `child` | `QName` | Contributory concept |
| `order` | `float` | Sibling ordering |
| `weight` | `float` | +1.0 (add) or −1.0 (subtract) |
| `extended_link_role` | `str` | ELR URI |

### `DefinitionArc`

| Field | Type | Description |
|-------|------|-------------|
| `arcrole` | `str` | Standard or custom arcrole URI |
| `source` | `QName` | Source concept |
| `target` | `QName` | Target concept |
| `order` | `float` | Sibling ordering |
| `closed` | `bool \| None` | For `all`/`notAll` hypercube arcs |
| `context_element` | `Literal['segment', 'scenario'] \| None` | Dimensional placement |
| `usable` | `bool \| None` | For domain-member arcs |

---

## Dimensional Model

### `HypercubeModel`
A dimensional hypercube definition extracted from the definition linkbase.

| Field | Type | Description |
|-------|------|-------------|
| `qname` | `QName` | Hypercube concept QName |
| `arcrole` | `Literal['all', 'notAll']` | Whether the hypercube is inclusive or exclusive |
| `closed` | `bool` | Closed (constrained) vs. open (unconstrained) |
| `context_element` | `Literal['segment', 'scenario']` | Where dimensional context appears |
| `primary_items` | `list[QName]` | Concepts governed by this hypercube |
| `dimensions` | `list[QName]` | Dimension concepts on this hypercube |
| `extended_link_role` | `str` | ELR this hypercube belongs to |

### `DimensionModel`
A single dimension axis within a hypercube.

| Field | Type | Description |
|-------|------|-------------|
| `qname` | `QName` | Dimension concept QName |
| `dimension_type` | `Literal['explicit', 'typed']` | Explicit (member enumeration) or typed (free value) |
| `default_member` | `QName \| None` | Default member when dimension is omitted from context |
| `domain` | `QName \| None` | Root domain concept (explicit dimensions only) |
| `members` | `list[DomainMember]` | Ordered member hierarchy (explicit dimensions only) |

### `DomainMember`

| Field | Type | Description |
|-------|------|-------------|
| `qname` | `QName` | Member concept QName |
| `parent` | `QName \| None` | Parent member in hierarchy (`None` for domain root) |
| `order` | `float` | Sibling order within parent |
| `usable` | `bool` | Whether this member may appear in instance context |

---

## Table Linkbase PWD Model

### `TableDefinitionPWD`
A complete report table as defined in the PWD Table Linkbase.

| Field | Type | Description |
|-------|------|-------------|
| `table_id` | `str` | XML `@id` attribute of the `table:table` element |
| `label` | `str` | Human-readable label (from label linkbase, display language) |
| `x_breakdown` | `BreakdownNode` | Root breakdown for the column (X) axis |
| `y_breakdown` | `BreakdownNode` | Root breakdown for the row (Y) axis |
| `z_breakdowns` | `list[BreakdownNode]` | Filter (Z) axis breakdowns (may be empty) |
| `extended_link_role` | `str` | ELR this table belongs to |

### `BreakdownNode`
A node in the table's hierarchical breakdown structure. Can be a rule node, aspect node, or concept-relationship node.

| Field | Type | Description |
|-------|------|-------------|
| `node_type` | `Literal['rule', 'aspect', 'conceptRelationship', 'dimensionRelationship']` | PWD node type |
| `label` | `str \| None` | Display label for this header cell |
| `rc_code` | `str \| None` | Eurofiling RC-code (leaf nodes only) |
| `is_abstract` | `bool` | Abstract nodes group children but produce no data cell |
| `merge` | `bool` | Whether this node merges with its parent in header spanning |
| `span` | `int \| None` | Computed column/row span (set during layout computation) |
| `children` | `list[BreakdownNode]` | Ordered child nodes |
| `aspect_constraints` | `dict[str, Any]` | Aspect values this node constrains (concept, period, dimension members, etc.) |

---

## Taxonomy Cache and Structure

### `TaxonomyMetadata`

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Human-readable taxonomy name |
| `version` | `str` | Taxonomy version string |
| `publisher` | `str` | Publisher (e.g., `"Banco de España"`) |
| `entry_point_path` | `Path` | Absolute path of the entry-point schema file |
| `loaded_at` | `datetime` | Timestamp of this load |
| `declared_languages` | `list[str]` | All language codes declared in label linkbases |

### `TaxonomyStructure`
The complete, immutable in-memory representation of a loaded taxonomy. This is the object stored in the cache and consumed by all other features.

| Field | Type | Description |
|-------|------|-------------|
| `metadata` | `TaxonomyMetadata` | Descriptive metadata |
| `concepts` | `dict[QName, Concept]` | All declared concepts |
| `labels` | `LabelResolver` | Label lookup service |
| `presentation` | `dict[str, PresentationNetwork]` | Presentation networks, keyed by ELR |
| `calculation` | `dict[str, list[CalculationArc]]` | Calculation arcs, keyed by ELR |
| `definition` | `dict[str, list[DefinitionArc]]` | Definition arcs, keyed by ELR |
| `hypercubes` | `list[HypercubeModel]` | All hypercube definitions |
| `dimensions` | `dict[QName, DimensionModel]` | All dimension definitions |
| `tables` | `list[TableDefinitionPWD]` | All PWD table definitions |
| `formula_linkbase_path` | `Path \| None` | Path of the formula linkbase file (parsed on-demand by Feature 005) |

### `TaxonomyCacheEntry`

| Field | Type | Description |
|-------|------|-------------|
| `entry_point_key` | `str` | Canonical absolute path (cache key) |
| `structure` | `TaxonomyStructure` | The cached taxonomy |
| `cached_at` | `datetime` | When it was cached |
| `source_path` | `Path` | Filesystem directory the taxonomy was loaded from |

### `TaxonomyCache`
Singleton in-memory store for all loaded taxonomies within a session.

**Operations**:
- `get(entry_point: str) -> TaxonomyStructure | None` — retrieve if present
- `put(entry_point: str, structure: TaxonomyStructure) -> None` — store
- `invalidate(entry_point: str) -> None` — remove specific entry
- `clear() -> None` — remove all entries
- `is_cached(entry_point: str) -> bool` — existence check
- `list_cached() -> list[TaxonomyMetadata]` — enumerate all cached taxonomy metadata

**Eviction**: LRU eviction at configurable max-size (default: 5 taxonomies). Eviction is silent and based on least-recently-accessed.

---

## Error Types

| Error Class | Extends | When Raised |
|-------------|---------|-------------|
| `TaxonomyLoadError` | `Exception` | Base class for all taxonomy load failures |
| `UnsupportedTaxonomyFormatError` | `TaxonomyLoadError` | Entry point does not appear to be a valid XBRL taxonomy |
| `TaxonomyDiscoveryError` | `TaxonomyLoadError` | One or more DTS references could not be resolved (includes list of failing URIs) |
| `TaxonomyParseError` | `TaxonomyLoadError` | Structural parse error in a schema or linkbase file (includes file path + line/column) |

---

## Entity Relationships

```
TaxonomyCache
  └── TaxonomyCacheEntry [1..*]
        └── TaxonomyStructure [1]
              ├── TaxonomyMetadata [1]
              ├── Concept [*] (keyed by QName)
              ├── LabelResolver [1]
              │     └── Label [*] (keyed by QName + role + language)
              ├── PresentationNetwork [*] (keyed by ELR)
              │     └── PresentationArc [*]
              ├── CalculationArc [*] (keyed by ELR)
              ├── DefinitionArc [*] (keyed by ELR)
              ├── HypercubeModel [*]
              │     └── DimensionModel [*]
              │           └── DomainMember [*]
              └── TableDefinitionPWD [*]
                    └── BreakdownNode [* recursive tree]
```

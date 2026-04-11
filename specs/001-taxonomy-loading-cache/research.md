# Research: Taxonomy Loading and Caching

**Branch**: `001-taxonomy-loading-cache` | **Phase**: 0 | **Date**: 2026-03-25

---

## Decision 1: UI Toolkit — PySide6

**Decision**: PySide6 (not PyQt6)

**Rationale**: PySide6 is LGPL-licensed, allowing proprietary distribution without a commercial license. It is officially maintained by The Qt Company, ensuring long-term alignment with Qt6. The API is functionally identical to PyQt6 (same Qt C++ under the hood), with the only material difference being that PyQt6 uses fully-qualified enum names (`Qt.ItemDataRole.DisplayRole`). Complex table rendering (QTableView + custom `QAbstractTableModel`) is a first-class pattern in PySide6 and is the right approach for the spanning-header tables this application requires.

**Alternatives considered**:
- PyQt6: identical API, stronger third-party documentation base, but GPL/commercial licensing makes distribution harder.
- tkinter: insufficient for the complex multi-level spanning header table rendering required.
- wxPython: adequate, but smaller ecosystem and fewer Qt-grade widgets.

---

## Decision 2: XML Parsing — lxml + xmlschema

**Decision**: lxml for XML tree manipulation; xmlschema for XSD validation and schema decoding

**Rationale**: lxml is the standard Cython-optimised XML parser for Python, significantly faster than ElementTree for large taxonomy files. xmlschema adds full XSD 1.0/1.1 schema validation coverage that is essential for XBRL DTS discovery (xs:import, xs:include, type system). The two libraries compose well: lxml does tree traversal and namespace handling; xmlschema handles type resolution and schema graph walking.

**Alternatives considered**:
- Pure lxml: fast but limited XSD support; xs:import/include resolution is not fully automated.
- ElementTree (stdlib): too slow for 5,000-concept taxonomies; no XSD support.
- minidom: rejected; verbose API, no XSD.

---

## Decision 3: XPath 2.0 — elementpath

**Decision**: elementpath library with lxml backend

**Rationale**: XBRL formula linkbases use XPath 2.0 expressions; the Table Linkbase PWD uses XPath 2.0 in aspect node constraint expressions. lxml natively supports only XPath 1.0 (via libxml2). elementpath provides XPath 1.0/2.0/3.0 parsers and integrates cleanly with lxml.etree objects by replacing `.xpath()` calls with `elementpath.select()`. It is actively maintained and used in the Python XML ecosystem.

**Alternatives considered**:
- lxml XPath 1.0 only: insufficient for formula assertions and table constraint expressions.
- Custom XPath 2.0 engine: not recommended; would take months to implement correctly.

---

## Decision 4: In-Memory Taxonomy Cache

**Decision**: Dict-based `TaxonomyCache` keyed by entry-point path, with optional max-size via `cachetools.LRUCache`

**Rationale**: For v1 (single-session, single-taxonomy typical use), a simple `dict` keyed by the canonical entry-point path is sufficient and has zero overhead. To guard against memory exhaustion when multiple taxonomies are loaded, the cache wraps the dict with a configurable LRU eviction policy via `cachetools.LRUCache`. Cache entries store the fully parsed `TaxonomyStructure` object, which is immutable after construction. The cache key is the resolved absolute path of the entry-point file.

**Alternatives considered**:
- `functools.lru_cache` on loader function: cleaner but inflexible (no manual invalidation, fixed key shape).
- weakref cache: allows GC to collect unused taxonomies, but makes cache lifetime unpredictable.
- Disk/pickle cache across sessions: deferred to a future feature per spec Out of Scope.

---

## Decision 5: Project Layout

**Decision**: `src/` layout with `pyproject.toml` (setuptools backend)

**Rationale**: The `src/` layout (code under `src/bde_xbrl_editor/`) enforces installation before import, preventing path-collision bugs where tests accidentally import the local uninstalled package instead of the installed one. This is the modern Python packaging standard and is especially important for a project with multiple sub-packages (taxonomy, instance, validation, ui). `pyproject.toml` with setuptools auto-discovery covers build, test, and dev-dependency configuration in one file.

**Alternatives considered**:
- Flat layout: simpler initial setup but causes test/production import path divergence; rejected.
- Poetry: good alternative to setuptools but adds a dependency manager layer that may complicate CI.

---

## Decision 6: Generic Linkbase Precedence

**Decision**: Generic arcs (`gen:link` / `gen:arc`) follow the same XBRL 2.1 relationship algebra as standard arcs; no special handling needed

**Rationale**: The XBRL Generic Links specification explicitly states that generic arcs use the same partitioning, prohibition, and reintroduction rules as standard XLink arcs. Arc precedence is governed by `@priority` and `@use="prohibited"` attributes, not by whether the arc is in a standard or generic linkbase. The label resolver must merge generic label arcs into the same resolution lookup as standard label arcs, applying the precedence rules uniformly.

**Practical impact for this feature**: When resolving a label for a concept, the resolver checks both `label:label` arcs (standard linkbase) and `gen:arc` arcs pointing to `genlab:label` resources. If both exist for the same concept + role + language, the arc with higher `@priority` wins; ties resolved by `@use="prohibited"` prohibition propagation.

---

## Decision 7: DTS Discovery Scope

**Decision**: Full recursive DTS discovery — resolve xs:import, xs:include, linkbaseRef, roleRef, arcroleRef; no network calls by default

**Rationale**: XBRL 2.1 DTS discovery starts from the instance's `schemaRef` and recursively follows every schema reference until the complete Discoverable Taxonomy Set is assembled. The BDE taxonomies are unpacked directory structures (not XBRL Taxonomy Packages), so all references resolve to local paths relative to the entry-point directory. Network resolution is disabled by default (spec FR-009); a local file-path catalog is used for any URI-based references.

**Discovery chain**:
1. Instance `xbrli:schemaRef` → entry-point schema
2. Schema `xs:import/@schemaLocation` → imported schemas (recursive)
3. Schema `xs:include/@schemaLocation` → included schemas (recursive)
4. Schema `link:linkbaseRef/@xlink:href` → linkbases
5. Linkbase `link:roleRef/@xlink:href` → role definitions
6. Linkbase `link:arcroleRef/@xlink:href` → arcrole definitions

**Error handling**: Any unresolvable reference (file not found, parse error) surfaces as a `TaxonomyDiscoveryError` with the failing URI and reason; the load aborts and reports all failing references in one pass.

---

## Decision 8: Table Linkbase PWD Version

**Decision**: Target the PWD 2012/2013 Table Linkbase specification as used by BDE taxonomies; no 1.0 final-spec constructs needed

**Rationale**: BDE taxonomies use the PWD version of the Table Linkbase. The structural differences between PWD and Table Linkbase 1.0 are minimal (1.0 is primarily an errata-corrected publication of the same spec), but the namespaces and element names differ enough to require deliberate targeting. The parser must use the PWD namespace `http://xbrl.org/PWD/2013-05-17/table` (or the specific BDE-declared namespace) and handle: `table:table`, `table:breakdown`, `table:breakdownTree`, `table:ruleNode`, `table:aspectNode`, `table:conceptRelationshipNode`, `table:dimensionRelationshipNode`.

**Practical impact**: The conformance suite runner (Feature 006) uses the Table Linkbase 1.0 conformance suite (no PWD suite exists); results are informational/non-blocking in v1. The taxonomy loader only needs to parse PWD constructs.

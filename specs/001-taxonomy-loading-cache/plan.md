# Implementation Plan: Taxonomy Loading and Caching

**Branch**: `001-taxonomy-loading-cache` | **Date**: 2026-03-25 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/001-taxonomy-loading-cache/spec.md`

## Summary

Implement the core taxonomy loading and caching engine for the BDE XBRL Editor. Starting from a local filesystem entry-point path, the loader performs full XBRL 2.1 DTS discovery (xs:import/include/linkbaseRef chains), parses all schema concepts and linkbases (label, presentation, calculation, definition, table PWD), builds the complete in-memory `TaxonomyStructure`, and stores it in a session-scoped LRU cache. Network calls are disabled by default. The feature delivers the foundational Python module (`bde_xbrl_editor.taxonomy`) that all subsequent features (instance creation, table rendering, validation) depend on.

**Tech stack**: Python 3.11+ · PySide6 · lxml + xmlschema · elementpath · pyproject.toml (src layout)

---

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: PySide6 (UI), lxml (XML parsing and tree manipulation), xmlschema (XSD schema validation and DTS graph), elementpath (XPath 2.0 for formula/table expressions), cachetools (LRU cache)
**Storage**: In-memory `TaxonomyCache` (session-scoped, LRU eviction); no disk persistence in this feature
**Testing**: pytest, pytest-qt (PySide6 widget tests), pytest-benchmark (load-time SC-001/SC-002)
**Target Platform**: macOS, Windows, Linux desktop (PySide6 cross-platform)
**Project Type**: Desktop application (src-layout Python package)
**Performance Goals**: First load of a BDE taxonomy (≤5,000 concepts, ≤50 tables) in ≤50 seconds (SC-001); cached access in <1 second (SC-002)
**Constraints**: No external network calls during taxonomy loading by default (FR-009); offline-capable; all schema/linkbase resolution via local filesystem paths
**Scale/Scope**: Up to 5,000 concepts, 50+ tables per taxonomy; up to 5 taxonomies simultaneously in cache

---

## Constitution Check

*Note: The project constitution (`/.specify/memory/constitution.md`) is an unfilled template — no project-specific principles have been ratified yet. This plan proceeds without constitution gates. It is recommended to fill the constitution before work on Feature 002 begins.*

**Informal gates applied for this plan**:
- ✅ No unnecessary complexity: single-package Python module, no micro-service or plugin architecture at this stage
- ✅ Test coverage: unit tests for parsing logic; integration tests against real BDE taxonomy samples
- ✅ No network calls by default: FR-009 honoured in design
- ✅ Clean internal API: `contracts/taxonomy-api.md` defines the module boundary

---

## Project Structure

### Documentation (this feature)

```text
specs/001-taxonomy-loading-cache/
├── plan.md              ← this file
├── research.md          ← Phase 0: tech decisions
├── data-model.md        ← Phase 1: entity model
├── contracts/
│   └── taxonomy-api.md  ← Phase 1: public Python API contract
└── tasks.md             ← Phase 2 output (/speckit.tasks — not yet created)
```

### Source Code (repository root)

```text
src/
└── bde_xbrl_editor/
    ├── __init__.py
    ├── __main__.py                    # python -m bde_xbrl_editor entry point
    ├── taxonomy/                      # ← Feature 001 scope
    │   ├── __init__.py                # re-exports: TaxonomyLoader, TaxonomyCache, TaxonomyStructure
    │   ├── loader.py                  # TaxonomyLoader — orchestrates load / reload
    │   ├── cache.py                   # TaxonomyCache — LRU session cache
    │   ├── settings.py                # LoaderSettings dataclass
    │   ├── models.py                  # All taxonomy dataclasses (Concept, Label, QName, …)
    │   ├── constants.py               # Label role URIs, arcrole URIs, namespace constants
    │   ├── discovery.py               # DTS discovery algorithm (xs:import/include/linkbaseRef)
    │   ├── schema.py                  # XML Schema parsing → Concept objects
    │   ├── label_resolver.py          # LabelResolver — standard + generic label merge
    │   └── linkbases/
    │       ├── __init__.py
    │       ├── label.py               # Parse standard label linkbases
    │       ├── generic_label.py       # Parse gen:link / gen:arc / genlab:label linkbases
    │       ├── presentation.py        # Parse presentation linkbases → PresentationNetwork
    │       ├── calculation.py         # Parse calculation linkbases → CalculationArc list
    │       ├── definition.py          # Parse definition linkbases → HypercubeModel / DimensionModel
    │       └── table_pwd.py           # Parse PWD Table Linkbase → TableDefinitionPWD tree
    ├── instance/                      # Features 002, 004 (future)
    ├── validation/                    # Feature 005 (future)
    └── ui/                            # PySide6 UI shell (minimal for Feature 001)
        ├── __init__.py
        ├── app.py                     # QApplication setup
        ├── main_window.py             # QMainWindow shell
        └── widgets/
            ├── taxonomy_loader_widget.py   # File picker + load trigger
            └── progress_dialog.py          # QProgressDialog wrapper

tests/
├── conftest.py                        # Shared fixtures (test taxonomy paths, sample data)
├── unit/
│   └── taxonomy/
│       ├── test_qname.py              # QName equality and hashing
│       ├── test_label_resolver.py     # Label precedence rules (standard vs generic, priority)
│       ├── test_discovery.py          # DTS traversal with mock filesystem
│       ├── test_schema_parser.py      # Concept extraction from XSD
│       ├── test_table_pwd_parser.py   # Breakdown tree construction
│       └── test_cache.py              # LRU eviction, invalidate, reload
├── integration/
│   └── taxonomy/
│       ├── test_bde_taxonomy_load.py  # Load a real (sampled) BDE taxonomy end-to-end
│       └── test_table_pwd_bde.py      # All tables in BDE sample taxonomy parse without error
└── conformance/                       # Feature 006 scope (future)

test_data/
└── taxonomies/
    └── bde_sample/                    # Minimal subset of a BDE taxonomy for CI tests
        ├── entry_point.xsd
        └── …

pyproject.toml
```

**Structure Decision**: Single Python package (`bde_xbrl_editor`) under `src/` layout. The `taxonomy/` sub-package contains all Feature 001 code; other feature sub-packages (`instance/`, `validation/`) are created empty now to establish the structure. The UI is a thin PySide6 shell in Feature 001 — just enough to wire up taxonomy loading; the full UI is built incrementally in subsequent features.

---

## Complexity Tracking

> No constitution violations to justify for this feature.

---

## Phase 0 Summary — Resolved Decisions

All NEEDS CLARIFICATION items resolved. See `research.md` for full rationale.

| Decision | Resolved To |
|----------|-------------|
| UI toolkit | PySide6 (LGPL) |
| XML parsing | lxml + xmlschema |
| XPath 2.0 | elementpath |
| Cache implementation | `cachetools.LRUCache` wrapped in `TaxonomyCache` class |
| Project layout | src-layout, `pyproject.toml` |
| Generic label precedence | Same XBRL 2.1 arc algebra as standard labels |
| Table Linkbase target | PWD namespace (BDE-specific); no 1.0 constructs needed |
| DTS discovery scope | Full recursive: xs:import, xs:include, linkbaseRef, roleRef, arcroleRef |

---

## Phase 1 Summary — Design Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Data model | `specs/001-taxonomy-loading-cache/data-model.md` | ✅ Complete |
| Python API contract | `specs/001-taxonomy-loading-cache/contracts/taxonomy-api.md` | ✅ Complete |

### Key design decisions

1. **`TaxonomyStructure` is immutable** after construction — safe to share across the UI and all feature modules without defensive copying.
2. **`LabelResolver.resolve()` never raises** — always returns a string (QName fallback), so UI code never needs to guard against missing labels.
3. **Formula linkbase deferred to Feature 005** — the loader discovers the formula linkbase path and records it in `TaxonomyStructure.formula_linkbase_path`, but does not parse it. Parsing is triggered on-demand by the validator.
4. **`TaxonomyCache` is single-threaded** in v1 — all access on the Qt main thread; no locking needed.
5. **Progress reporting** via a plain Python callback (not a Qt signal) so the taxonomy module has zero dependency on PySide6; the UI adapts the callback to `QProgressDialog`.

# Tasks: Taxonomy Loading and Caching

**Branch**: `001-taxonomy-loading-cache`
**Input**: `specs/001-taxonomy-loading-cache/` (plan.md, spec.md, data-model.md, contracts/taxonomy-api.md, research.md)
**Generated**: 2026-03-26

---

## Format: `[ID] [P?] [Story?] Description — file path`

- **[P]**: Parallelizable with other [P] tasks in the same phase (different files, no inter-task dependency)
- **[US1/US2/US3]**: Maps to user story from spec.md
- All paths relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the project skeleton, package layout, and tooling configuration. Must complete before any code is written.

- [X] T001 Create `pyproject.toml` with dependencies (PySide6, lxml, xmlschema, elementpath, cachetools), dev extras (pytest, pytest-qt, ruff), and console-script entry point — `pyproject.toml`
- [X] T002 [P] Create `src/bde_xbrl_editor/__init__.py` and `src/bde_xbrl_editor/__main__.py` (empty entry point shell) — `src/bde_xbrl_editor/__init__.py`, `src/bde_xbrl_editor/__main__.py`
- [X] T003 [P] Create empty package stubs for future features: `src/bde_xbrl_editor/instance/__init__.py`, `src/bde_xbrl_editor/validation/__init__.py`, `src/bde_xbrl_editor/ui/__init__.py` — stub files
- [X] T004 [P] Create test directory structure: `tests/conftest.py` (empty), `tests/unit/taxonomy/`, `tests/integration/taxonomy/`, `tests/conformance/` — directory layout
- [X] T005 [P] Create BDE sample taxonomy test fixture directory and a minimal valid entry-point XSD for unit tests — `test_data/taxonomies/bde_sample/entry_point.xsd`
- [X] T006 [P] Configure ruff (`pyproject.toml` [tool.ruff] section) and verify `ruff check .` passes on empty project — `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core types shared by all three user stories. Must be complete before any US phase begins.

- [X] T007 Implement `QName` frozen dataclass with `__eq__`/`__hash__` based on `namespace`+`local_name` (prefix ignored); `from_clark()` and `__str__()` helpers — `src/bde_xbrl_editor/taxonomy/models.py`
- [X] T008 [P] Implement error hierarchy: `TaxonomyLoadError`, `UnsupportedTaxonomyFormatError`, `TaxonomyDiscoveryError` (with `failing_uris`), `TaxonomyParseError` (with `file_path`, `line`, `column`) — `src/bde_xbrl_editor/taxonomy/models.py`
- [X] T009 [P] Implement `LoaderSettings` frozen dataclass with `allow_network=False`, `language_preference=["es","en"]`, `local_catalog=None` — `src/bde_xbrl_editor/taxonomy/settings.py`
- [X] T010 [P] Implement all namespace and label-role constants: `LABEL_ROLE`, `TERSE_LABEL_ROLE`, `VERBOSE_LABEL_ROLE`, `DOCUMENTATION_ROLE`, `PERIOD_START_ROLE`, `PERIOD_END_ROLE`, `TOTAL_LABEL_ROLE`, `NEGATED_LABEL_ROLE`, `RC_CODE_ROLE`, XBRL/link/xlink namespace URIs, Eurofiling filing-indicator namespace, PWD table namespace — `src/bde_xbrl_editor/taxonomy/constants.py`
- [X] T011 [P] Implement `TaxonomyMetadata` frozen dataclass (name, version, publisher, entry_point_path, loaded_at, declared_languages, period_type) — `src/bde_xbrl_editor/taxonomy/models.py`
- [X] T012 [P] Implement `Concept` frozen dataclass (qname, data_type, period_type, balance, abstract, nillable, substitution_group) — `src/bde_xbrl_editor/taxonomy/models.py`
- [X] T013 Write unit tests for `QName` (equality, hashing, prefix ignored, `from_clark`, `__str__`) — `tests/unit/taxonomy/test_qname.py`

---

## Phase 3: User Story 1 — Load a BDE Taxonomy from the Local Filesystem

**Goal**: Given a local filesystem path to an unpacked BDE taxonomy, the application parses all XBRL structures and makes the taxonomy ready for use.

**Independent test criteria**: Provide a BDE sample taxonomy entry point path → `TaxonomyLoader.load()` returns a `TaxonomyStructure` with correct concept count, table count, and at least one label per table.

- [X] T014 [US1] Implement DTS discovery: recursive traversal of `xs:import`, `xs:include`, and `linkbaseRef` to collect all schema and linkbase file paths; respects `LoaderSettings.allow_network=False`; raises `TaxonomyDiscoveryError` on unresolvable references — `src/bde_xbrl_editor/taxonomy/discovery.py`
- [X] T015 [P] [US1] Implement schema parser: extract `Concept` objects from `xs:element` declarations in XSD files; map XSD types to XBRL types; populate `concepts` dict keyed by `QName` — `src/bde_xbrl_editor/taxonomy/schema.py`
- [X] T016 [P] [US1] Implement standard label linkbase parser: parse `lab:labelLink` arcs → `Label` objects (text, language, role, priority, use); handle `@use="prohibited"` arc — `src/bde_xbrl_editor/taxonomy/linkbases/label.py`
- [X] T017 [P] [US1] Implement generic label linkbase parser: parse `gen:link`/`gen:arc`/`genlab:label` structures → `Label` objects with `source="generic"`; apply same priority/prohibited arc algebra as standard labels — `src/bde_xbrl_editor/taxonomy/linkbases/generic_label.py`
- [X] T018 [US1] Implement `LabelResolver`: merge standard and generic labels; resolve by role + language preference list; fallback to `str(qname)`; implement `resolve()` (never raises) and `get_all_labels()` — `src/bde_xbrl_editor/taxonomy/label_resolver.py`
- [X] T019 [P] [US1] Implement presentation linkbase parser: parse `link:presentationLink` arcs → `PresentationArc` objects; build `PresentationNetwork` per ELR with `roots` list and `children_of()` lookup — `src/bde_xbrl_editor/taxonomy/linkbases/presentation.py`
- [X] T020 [P] [US1] Implement calculation linkbase parser: parse `link:calculationLink` arcs → `CalculationArc` objects (parent, child, order, weight ±1.0) grouped by ELR — `src/bde_xbrl_editor/taxonomy/linkbases/calculation.py`
- [X] T021 [P] [US1] Implement definition linkbase parser: parse `link:definitionLink` arcs → `DefinitionArc` objects; extract `HypercubeModel`, `DimensionModel`, `DomainMember` hierarchies from `all`/`notAll`/`hypercube-dimension`/`domain-member`/`dimension-default` arcroles — `src/bde_xbrl_editor/taxonomy/linkbases/definition.py`
- [X] T022 [P] [US1] Implement PWD Table Linkbase parser: parse `table:table`, `table:breakdown`, `table:ruleNode`, `table:aspectNode`, `table:conceptRelationshipNode` elements → `TableDefinitionPWD` and `BreakdownNode` tree; use PWD namespace `http://xbrl.org/PWD/2013-05-17/table`; extract RC-codes from Eurofiling label role — `src/bde_xbrl_editor/taxonomy/linkbases/table_pwd.py`
- [X] T023 [US1] Implement `TaxonomyLoader.load()`: orchestrate DTS discovery → schema parse → linkbase parses → assemble `TaxonomyStructure`; wire progress callback at each phase (min 5 progress events); raise typed errors on failure; record `formula_linkbase_path` without parsing it — `src/bde_xbrl_editor/taxonomy/loader.py`
- [X] T024 [P] [US1] Implement `TaxonomyStructure` assembled dataclass with all fields from data-model.md; finalise `src/bde_xbrl_editor/taxonomy/models.py` (Label, PresentationArc, PresentationNetwork, CalculationArc, DefinitionArc, HypercubeModel, DimensionModel, DomainMember, TableDefinitionPWD, BreakdownNode, TaxonomyCacheEntry)
- [X] T025 [P] [US1] Implement `taxonomy/__init__.py` re-exports: `TaxonomyLoader`, `TaxonomyCache`, `TaxonomyStructure`, `TaxonomyMetadata`, `LabelResolver`, `LoaderSettings`, all error types, `QName`, `Concept` — `src/bde_xbrl_editor/taxonomy/__init__.py`
- [X] T026 [P] [US1] Implement PySide6 progress dialog wrapper: `QProgressDialog` subclass that wraps the progress callback protocol `(message, current, total)` and posts updates safely on the main thread — `src/bde_xbrl_editor/ui/widgets/progress_dialog.py`
- [X] T027 [P] [US1] Implement taxonomy file-picker widget: `QWidget` with `QLineEdit` (path display), `QPushButton` ("Browse…"), `QPushButton` ("Load"); triggers `TaxonomyLoader.load()` in a background thread; shows `ProgressDialog`; emits `taxonomy_loaded(TaxonomyStructure)` signal on success; shows `QMessageBox` on error — `src/bde_xbrl_editor/ui/widgets/taxonomy_loader_widget.py`
- [X] T028 [P] [US1] Implement minimal `QMainWindow` shell: menu bar with File → Open Taxonomy; embeds `TaxonomyLoaderWidget`; displays loaded taxonomy name and table count in status bar — `src/bde_xbrl_editor/ui/main_window.py`, `src/bde_xbrl_editor/ui/app.py`
- [X] T029 [P] [US1] Write unit tests: DTS discovery with mock filesystem (path resolution, network block, circular reference detection); also test negative path: pass a non-XBRL file to `TaxonomyLoader.load()` and assert `TaxonomyLoadError` is raised with a non-empty, human-readable `str(e)` (FR-007, SC-004) — `tests/unit/taxonomy/test_discovery.py`
- [X] T030 [P] [US1] Write unit tests: schema parser (concept extraction, type mapping, abstract flag) — `tests/unit/taxonomy/test_schema_parser.py`
- [X] T031 [P] [US1] Write unit tests: `LabelResolver` (standard vs generic precedence, priority, prohibited, language fallback, never-raises guarantee) — `tests/unit/taxonomy/test_label_resolver.py`
- [X] T032 [P] [US1] Write unit tests: PWD table parser (breakdown tree construction, node types, RC-code extraction) — `tests/unit/taxonomy/test_table_pwd_parser.py`
- [X] T033 [US1] Write integration test: load BDE sample taxonomy end-to-end; assert correct concept count, table count, at least one label per concept, at least one RC-code on a leaf node; pass a counting progress callback and assert it is called ≥5 times during load (FR-010) — `tests/integration/taxonomy/test_bde_taxonomy_load.py`

---

## Phase 4: User Story 2 — Reuse a Previously Loaded Taxonomy Within the Same Session

**Goal**: A taxonomy loaded earlier in the session is served from cache on second access; explicit reload bypasses cache and updates the entry.

**Independent test criteria**: Load same entry point twice → second call returns identical object reference from cache with no re-parse (measure time < 1s). Explicit `reload()` returns a fresh object and updates the cache.

- [X] T034 [US2] Implement `TaxonomyCache`: LRU-evicting dict (`cachetools.LRUCache` max_size=5); implement `get`, `put`, `invalidate`, `clear`, `is_cached`, `list_cached` — `src/bde_xbrl_editor/taxonomy/cache.py`
- [X] T035 [US2] Integrate cache into `TaxonomyLoader.load()`: check `cache.get()` first; on cache hit return immediately; on cache miss load and `cache.put()` — `src/bde_xbrl_editor/taxonomy/loader.py`
- [X] T036 [US2] Implement `TaxonomyLoader.reload()`: force-bypass cache, re-parse, replace cache entry — `src/bde_xbrl_editor/taxonomy/loader.py`
- [X] T037 [P] [US2] Wire "Reload Taxonomy" action into main window (File → Reload Taxonomy menu item; calls `loader.reload()`; refreshes status bar) — `src/bde_xbrl_editor/ui/main_window.py`
- [X] T038 [P] [US2] Write unit tests: `TaxonomyCache` LRU eviction (max_size respected), `invalidate`, `clear`, `list_cached`, multi-version isolation — `tests/unit/taxonomy/test_cache.py`
- [X] T039 [P] [US2] Write integration test: load same path twice; verify second load is cache hit and returns same object; measure second access time < 1s — `tests/integration/taxonomy/test_bde_taxonomy_load.py` (extend existing)

---

## Phase 5: User Story 3 — Inspect Taxonomy Structure Before Working with Reports

**Goal**: From a loaded taxonomy, the user can browse available tables, their concepts, dimensions, and allowed dimension members — with human-readable labels.

**Independent test criteria**: Call `taxonomy.tables` on a loaded BDE taxonomy → returns list with correct table IDs and labels; `taxonomy.dimensions` contains all expected dimension QNames with their members.

- [X] T040 [US3] Verify `TaxonomyStructure` provides complete read API per `contracts/taxonomy-api.md`: `concepts`, `labels`, `presentation`, `calculation`, `definition`, `hypercubes`, `dimensions`, `tables`; add any missing properties or convenience accessors (e.g., `get_table(table_id: str) -> TableDefinitionPWD | None`) — `src/bde_xbrl_editor/taxonomy/models.py`
- [X] T041 [P] [US3] Implement taxonomy info panel widget: `QWidget` displaying loaded taxonomy name, version, language list, and table count; includes a `QListWidget` showing all table IDs and labels from `taxonomy.tables` — `src/bde_xbrl_editor/ui/widgets/taxonomy_info_panel.py`
- [X] T042 [P] [US3] Wire taxonomy info panel into main window: shown after successful taxonomy load (replacing the loader widget in the central area or added as a sidebar dock) — `src/bde_xbrl_editor/ui/main_window.py`
- [X] T043 [P] [US3] Write integration test: from loaded BDE sample taxonomy, assert `taxonomy.tables` list is complete (all expected table IDs present); assert labels available in `es` and `en`; assert at least one dimension per table that uses dimensions — `tests/integration/taxonomy/test_table_pwd_bde.py`

---

## Phase 6: Polish and Cross-Cutting Concerns

**Purpose**: Performance validation, API surface clean-up, and benchmark targets from success criteria.

- [X] T044 Verify all public API types in `taxonomy/__init__.py` re-exports match `contracts/taxonomy-api.md` exactly; add any missing re-exports — `src/bde_xbrl_editor/taxonomy/__init__.py`
- [X] T045 [P] Add `pytest-benchmark` to dev dependencies and write a performance benchmark test: full load of BDE sample taxonomy must complete in ≤50 seconds (SC-001); cached access must complete in <1 second (SC-002) — `tests/unit/taxonomy/test_performance.py` (using `pytest-benchmark`)
- [X] T046 [P] Add `conftest.py` shared fixtures: `bde_sample_taxonomy_path` pointing to `test_data/taxonomies/bde_sample/entry_point.xsd`; `loaded_taxonomy` fixture that loads once per session (`scope="session"`) — `tests/conftest.py`
- [X] T047 [P] Validate `LabelResolver.resolve()` never-raises guarantee with a fuzz-like test: random QNames not in taxonomy always return non-empty string — `tests/unit/taxonomy/test_label_resolver.py` (extend)
- [X] T048 [P] Verify error messages meet SC-004 (actionable, no "unknown error"): review each `TaxonomyLoadError` subclass to ensure `str(e)` is human-readable and specific — `src/bde_xbrl_editor/taxonomy/models.py`
- [X] T049 [P] Implement `LoaderSettings` persistence and UI: add a "Settings…" button to `TaxonomyLoaderWidget` that opens a `QDialog` allowing the user to view and edit `local_catalog` path and `allow_network` toggle; persist settings to a JSON config file (`~/.bde_xbrl_editor/settings.json`) loaded at startup — `src/bde_xbrl_editor/ui/widgets/taxonomy_loader_widget.py`, `src/bde_xbrl_editor/ui/widgets/loader_settings_dialog.py`

---

## Dependencies Summary

```
Phase 1 (Setup) ──must complete──▶ Phase 2 (Foundational)
Phase 2 (Foundational) ──must complete──▶ Phase 3 (US1)
Phase 3 (US1) ──must complete──▶ Phase 4 (US2) — cache integration requires TaxonomyLoader
Phase 3 (US1) ──must complete──▶ Phase 5 (US3) — inspection requires loaded TaxonomyStructure
Phase 4 + Phase 5 ──complete──▶ Phase 6 (Polish)
```

**Within Phase 3** (US1): Tasks with [P] can be parallelized once T014 (DTS discovery) is complete; T023 (loader assembly) requires T014–T022 all complete; T024 (TaxonomyStructure) can be started in parallel with parsing implementations.

**Strictly sequential in US1**: T014 → T023 (DTS must work before load orchestration is testable end-to-end).

---

## Parallel Execution Examples

### Phase 3 (US1) — max parallelism after T014

Batch A (after T014 completes):
- T015 schema.py + T016 label.py + T017 generic_label.py + T019 presentation.py + T020 calculation.py + T021 definition.py + T022 table_pwd.py (all parsers, different files)

Batch B (after Batch A and T018 LabelResolver):
- T023 loader.py + T024 models.py + T025 __init__.py + T026 progress_dialog.py + T027 taxonomy_loader_widget.py + T028 main_window.py

Batch C (unit tests, after implementations):
- T029 + T030 + T031 + T032 (all different test files)

### Phase 4 (US2) — sequential core, parallel UI+tests

Sequential: T034 → T035 → T036
Parallel after T034: T038 (cache unit tests)
Parallel after T036: T037 (UI reload action) + T039 (integration test)

---

## Implementation Strategy (MVP Scope)

**MVP**: Phase 1 + Phase 2 + Phase 3 only → delivers User Story 1 (load taxonomy, see tables, no caching yet).

**Full v1**: All phases → all three user stories.

The spec's P1 story (load) is the only hard prerequisite for all downstream features (002–006). Completing Phase 3 unblocks the entire project roadmap.

---

## Task Count Summary

| Phase | Tasks | Parallelizable |
|-------|-------|----------------|
| Phase 1: Setup | 6 | 5 |
| Phase 2: Foundational | 7 | 6 |
| Phase 3: US1 (Load) | 20 | 17 |
| Phase 4: US2 (Cache) | 6 | 4 |
| Phase 5: US3 (Inspect) | 4 | 3 |
| Phase 6: Polish | 6 | 5 |
| **Total** | **49** | **40** |

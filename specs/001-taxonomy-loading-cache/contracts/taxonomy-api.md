# Contract: Taxonomy Module Public API

**Branch**: `001-taxonomy-loading-cache` | **Phase**: 1 | **Date**: 2026-03-25
**Module**: `bde_xbrl_editor.taxonomy`

This document defines the public Python interface that the taxonomy loading and caching feature exposes to the rest of the application (UI, instance editor, validator, table renderer). All other modules **must** use only the interfaces defined here; they must not import from sub-modules directly.

---

## Primary Entry Points

### `TaxonomyLoader`

The main service for loading taxonomies. Consumers obtain an instance via the application's service container (passed by the UI on startup). It is **not** a singleton on its own — the `TaxonomyCache` it wraps is the shared state.

```
TaxonomyLoader(cache: TaxonomyCache, settings: LoaderSettings)

Methods:
  load(entry_point: str | Path,
       progress_callback: Callable[[str, int, int], None] | None = None
       ) -> TaxonomyStructure
    """
    Load the taxonomy at entry_point.
    Returns a cached TaxonomyStructure if already loaded.
    Calls progress_callback(message, current_step, total_steps) during loading.
    Raises:
      UnsupportedTaxonomyFormatError — entry_point is not an XBRL taxonomy
      TaxonomyDiscoveryError        — one or more DTS references could not be resolved
      TaxonomyParseError            — structural error in a schema or linkbase file
    """

  reload(entry_point: str | Path,
         progress_callback: Callable[[str, int, int], None] | None = None
         ) -> TaxonomyStructure
    """
    Force-reload the taxonomy, bypassing and replacing the cache entry.
    Same exceptions as load().
    """
```

### `TaxonomyCache`

The shared in-memory store. The application creates one instance at startup and passes it to all `TaxonomyLoader` instances.

```
TaxonomyCache(max_size: int = 5)

Methods:
  get(entry_point: str) -> TaxonomyStructure | None
  put(entry_point: str, structure: TaxonomyStructure) -> None
  invalidate(entry_point: str) -> None
  clear() -> None
  is_cached(entry_point: str) -> bool
  list_cached() -> list[TaxonomyMetadata]
```

### `LoaderSettings`

Configuration object passed to `TaxonomyLoader`. Controls network resolution and language preferences.

```
LoaderSettings(
  allow_network: bool = False,            # FR-009: off by default
  language_preference: list[str] = ["es", "en"],  # Spanish first, English fallback
  local_catalog: dict[str, Path] | None = None,   # URI → local path overrides
)
```

---

## Read Interface: `TaxonomyStructure`

All fields are read-only. The object is safe to share across threads after construction.

```
TaxonomyStructure:
  .metadata: TaxonomyMetadata
  .concepts: Mapping[QName, Concept]              # all declared concepts
  .labels: LabelResolver                          # label lookup service
  .presentation: Mapping[str, PresentationNetwork] # keyed by ELR URI
  .calculation: Mapping[str, Sequence[CalculationArc]]  # keyed by ELR URI
  .definition: Mapping[str, Sequence[DefinitionArc]]    # keyed by ELR URI
  .hypercubes: Sequence[HypercubeModel]
  .dimensions: Mapping[QName, DimensionModel]
  .tables: Sequence[TableDefinitionPWD]           # PWD table definitions
  .formula_linkbase_path: Path | None             # loaded on-demand by validator
```

### `LabelResolver` (accessed via `TaxonomyStructure.labels`)

```
LabelResolver:
  resolve(
    qname: QName,
    role: str = LABEL_ROLE,       # defaults to standard label role
    language_preference: list[str] | None = None  # overrides LoaderSettings default
  ) -> str
    """
    Returns the best-matching label text.
    Falls back through language_preference, then returns str(qname) if no label found.
    Never raises; always returns a non-empty string.
    """

  get_all_labels(qname: QName) -> list[Label]
    """
    Returns all labels for a concept across all roles and languages.
    """
```

---

## Standard Label Role Constants

```python
# bde_xbrl_editor.taxonomy.constants

LABEL_ROLE            = "http://www.xbrl.org/2003/role/label"
TERSE_LABEL_ROLE      = "http://www.xbrl.org/2003/role/terseLabel"
VERBOSE_LABEL_ROLE    = "http://www.xbrl.org/2003/role/verboseLabel"
DOCUMENTATION_ROLE    = "http://www.xbrl.org/2003/role/documentation"
PERIOD_START_ROLE     = "http://www.xbrl.org/2003/role/periodStartLabel"
PERIOD_END_ROLE       = "http://www.xbrl.org/2003/role/periodEndLabel"
TOTAL_LABEL_ROLE      = "http://www.xbrl.org/2003/role/totalLabel"
NEGATED_LABEL_ROLE    = "http://www.xbrl.org/2003/role/negatedLabel"
RC_CODE_ROLE          = "http://www.eurofiling.info/xbrl/role/rc-code"
```

---

## Error Hierarchy

```
TaxonomyLoadError (base)
  ├── UnsupportedTaxonomyFormatError
  │     .entry_point: str
  │     .reason: str
  ├── TaxonomyDiscoveryError
  │     .entry_point: str
  │     .failing_uris: list[tuple[str, str]]  # (uri, reason) pairs
  └── TaxonomyParseError
        .file_path: str
        .line: int | None
        .column: int | None
        .message: str
```

---

## Progress Callback Protocol

The `progress_callback` parameter follows this signature:

```
progress_callback(message: str, current_step: int, total_steps: int) -> None
```

- `message`: human-readable description of the current step (e.g., `"Parsing label linkbase…"`)
- `current_step`: 0-based step index
- `total_steps`: estimated total steps (may be revised upward during discovery)
- Called at least once per major loading phase: discovery, schema parse, linkbase parse, table parse, cache store
- UI consumers connect this to a `QProgressDialog`

---

## Usage Example (UI consumer pseudocode)

```python
# Application startup
cache = TaxonomyCache(max_size=5)
settings = LoaderSettings(allow_network=False, language_preference=["es", "en"])
loader = TaxonomyLoader(cache=cache, settings=settings)

# User picks a taxonomy directory
def on_load_taxonomy(entry_point_path: str):
    def on_progress(msg, step, total):
        progress_dialog.setLabelText(msg)
        progress_dialog.setValue(int(step / total * 100))

    try:
        taxonomy = loader.load(entry_point_path, progress_callback=on_progress)
    except TaxonomyDiscoveryError as e:
        show_error_dialog(f"Could not load taxonomy: {e.failing_uris}")
        return
    except TaxonomyLoadError as e:
        show_error_dialog(str(e))
        return

    # taxonomy is now ready; pass to table renderer, instance editor, etc.
    app_state.current_taxonomy = taxonomy
    table_browser.set_taxonomy(taxonomy)
```

---

## Invariants and Guarantees

- `TaxonomyStructure` is **immutable** after construction. All fields are read-only. Multiple UI widgets may hold references without risk of mutation.
- `TaxonomyLoader.load()` is **idempotent**: calling it twice with the same path returns the same cached object without re-parsing.
- `LabelResolver.resolve()` **never raises** — it always returns a non-empty string.
- `TaxonomyCache` is **not thread-safe** in v1; all access must occur on the main thread (acceptable for a single-window desktop app).
- A `TaxonomyLoadError` subclass **always includes enough information** to let the user identify the problem without technical support (spec SC-004, FR-007).

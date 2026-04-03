# Data Model: Instance Validation

**Branch**: `005-instance-validation` | **Phase**: 1 | **Date**: 2026-03-26

---

## Overview

Feature 005 introduces a self-contained validation subsystem that operates on an already-loaded `XbrlInstance` (Feature 002/004) and `TaxonomyStructure` (Feature 001). No existing models are mutated. The additions are:

1. **Validation domain types** — immutable results (`ValidationFinding`, `ValidationReport`, `ValidationSeverity`)
2. **Validator services** — `StructuralConformanceValidator`, `FormulaEvaluator`, `DimensionalConstraintValidator`, `InstanceValidator` (orchestrator)
3. **UI types** — `ValidationPanel` (PySide6 widget), `ValidationWorker` (QThread worker), `ValidationResultsModel` (QStandardItemModel), `ValidationFilterProxy` (QSortFilterProxyModel subclass)
4. **Export service** — `ValidationReportExporter`

---

## Domain Types

### `ValidationSeverity` (enum)

```python
class ValidationSeverity(str, Enum):
    ERROR   = "error"
    WARNING = "warning"
```

### `ValidationFinding`

A single identified issue from a validation run. Immutable dataclass.

| Field | Type | Description |
|-------|------|-------------|
| `rule_id` | `str` | Assertion/rule identifier (e.g. `"va_001"`, `"structural:duplicate-fact"`) |
| `severity` | `ValidationSeverity` | `ERROR` or `WARNING` |
| `message` | `str` | Human-readable description of the failure |
| `source` | `Literal["structural", "formula", "dimensional"]` | Which validator produced this finding |
| `table_id` | `str \| None` | Table identifier where the issue was detected (None if not mappable) |
| `table_label` | `str \| None` | Human-readable table label (looked up from taxonomy at report time) |
| `concept_qname` | `QName \| None` | The concept involved (None for instance-level structural findings) |
| `context_ref` | `str \| None` | `@contextRef` of the offending fact (None if not applicable) |
| `hypercube_qname` | `QName \| None` | For dimensional findings: the violated hypercube |
| `dimension_qname` | `QName \| None` | For dimensional findings: the violated dimension |
| `constraint_type` | `str \| None` | For dimensional findings: one of `CLOSED_MISSING_DIMENSION`, `PROHIBITED_COMBINATION`, `UNDECLARED_DIMENSION`, `INVALID_MEMBER` |

**Invariant**: `message` is never empty. All other optional fields are `None` when not applicable.

---

### `ValidationReport`

The complete output of one validation run. Immutable dataclass.

| Field | Type | Description |
|-------|------|-------------|
| `instance_path` | `str` | Absolute path of the validated instance file (or `"<unsaved>"`) |
| `taxonomy_name` | `str` | Human-readable taxonomy name from `TaxonomyMetadata.name` |
| `taxonomy_version` | `str` | Taxonomy version string |
| `run_timestamp` | `datetime` | UTC datetime when the run completed |
| `findings` | `tuple[ValidationFinding, ...]` | All findings, ordered: structural → dimensional → formula |
| `formula_linkbase_available` | `bool` | False if the taxonomy has no formula linkbase (FR-012) |
| `structural_checks_run` | `bool` | Always True (structural is always run) |

**Computed properties**:
- `error_count: int` → number of findings with `severity == ERROR`
- `warning_count: int` → number of findings with `severity == WARNING`
- `passed: bool` → `error_count == 0`
- `findings_for_table(table_id: str) -> tuple[ValidationFinding, ...]`
- `findings_by_severity(sev: ValidationSeverity) -> tuple[ValidationFinding, ...]`

---

### `ValidationRun`

Mutable in-progress state, held only inside `ValidationWorker`. Not exposed outside the worker.

| Field | Type | Description |
|-------|------|-------------|
| `findings` | `list[ValidationFinding]` | Accumulated findings |
| `cancelled` | `threading.Event` | Set to request cancellation |
| `total_assertions` | `int` | Total count of formula assertions to evaluate (for progress) |
| `evaluated_assertions` | `int` | Count evaluated so far |

---

## Validator Services (non-Qt, no PySide6 dependency)

### `StructuralConformanceValidator`

Pure Python. No Qt, no UI.

```
StructuralConformanceValidator()

  validate(instance: XbrlInstance) -> list[ValidationFinding]
    """
    Run all XBRL 2.1 structural checks against the in-memory instance.
    Returns a (possibly empty) list of findings; never raises.
    Checks performed (in order):
      1. Root element namespace (xbrli:xbrl)
      2. At least one link:schemaRef present
      3. All @contextRef values in facts resolve to a declared context
      4. All @unitRef values in numeric facts resolve to a declared unit
      5. Context completeness: each context has entity + period
      6. Period type consistency: concept declared period type matches context period type
      7. Duplicate facts: same concept + contextRef + unitRef
      8. Namespace declaration completeness: xbrli, link, xlink namespaces declared
    """
```

Each failing check produces one or more `ValidationFinding` with `source="structural"`.

---

### `DimensionalConstraintValidator`

Pure Python. Uses `HypercubeModel` from `TaxonomyStructure`.

```
DimensionalConstraintValidator(taxonomy: TaxonomyStructure)

  validate(instance: XbrlInstance) -> list[ValidationFinding]
    """
    Validate each fact's dimensional context against the taxonomy's hypercube constraints.
    Returns a (possibly empty) list of findings; never raises.
    Checks performed per fact:
      1. If fact has explicit dimension values: dimension must be declared in at least
         one hypercube covering the concept (UNDECLARED_DIMENSION if not).
      2. For closed hypercubes: all required dimensions must have explicit values or
         taxonomy-declared defaults (CLOSED_MISSING_DIMENSION if missing).
      3. For notAll hypercubes: prohibited concept+dimension combinations must not
         appear together (PROHIBITED_COMBINATION if found).
      4. Explicit dimension member values must be declared domain members
         (INVALID_MEMBER if not).
    """
```

---

### `FormulaEvaluator`

Pure Python. Uses `elementpath` for XPath 2.0 evaluation with custom `xfi:` function registration.

```
FormulaEvaluator(
  taxonomy: TaxonomyStructure,
  progress_callback: Callable[[int, int, str], None] | None = None,
  cancel_event: threading.Event | None = None,
)

  evaluate(instance: XbrlInstance) -> list[ValidationFinding]
    """
    Evaluate all non-abstract formula assertions in the taxonomy's formula linkbase
    against the instance. Returns a (possibly empty) list of findings.
    Progress callback signature: (evaluated_count, total_count, assertion_id).
    If cancel_event is set, stops early and returns findings collected so far.
    Abstract assertions (@abstract="true") are silently skipped (FR-013).
    If the taxonomy has no formula linkbase, returns [].
    """

  _bind_variables(
    assertion: FormulaAssertion,
    instance: XbrlInstance,
  ) -> list[dict[str, list[Fact]]]
    """
    Produce the list of variable binding tuples for a formula assertion.
    Each binding maps variable names to matching facts after applying
    all attached filters (concept, context, period, dimension, unit, tuple).
    """

  _evaluate_value_assertion(
    assertion: ValueAssertionDefinition,
    bindings: list[dict[str, list[Fact]]],
    instance: XbrlInstance,
  ) -> list[ValidationFinding]
    """Evaluate @test XPath for each binding tuple."""

  _evaluate_existence_assertion(
    assertion: ExistenceAssertionDefinition,
    bindings: list[dict[str, list[Fact]]],
  ) -> list[ValidationFinding]
    """Pass if at least one binding tuple has a non-empty fact set."""

  _evaluate_consistency_assertion(
    assertion: ConsistencyAssertionDefinition,
    bindings: list[dict[str, list[Fact]]],
    instance: XbrlInstance,
  ) -> list[ValidationFinding]
    """Evaluate formula expression; compare computed vs. actual fact value."""
```

---

### `InstanceValidator` (orchestrator)

```
InstanceValidator(taxonomy: TaxonomyStructure)

  validate_sync(
    instance: XbrlInstance,
    progress_callback: Callable[[int, int, str], None] | None = None,
    cancel_event: threading.Event | None = None,
  ) -> ValidationReport
    """
    Run structural → dimensional → formula validation in sequence.
    Structural and dimensional run synchronously first (fast).
    Formula evaluation uses progress_callback and cancel_event.
    Returns ValidationReport regardless of findings.
    Never raises — exceptions from validators are caught and recorded
    as ERROR findings with rule_id="internal:validator-error".
    """
```

---

## Formula Linkbase Domain Types (additions to taxonomy data model)

These are parsed during taxonomy loading (Feature 001 extension) and stored in `TaxonomyStructure`.

### `FormulaAssertionSet`

| Field | Type | Description |
|-------|------|-------------|
| `assertions` | `tuple[FormulaAssertion, ...]` | All non-abstract assertions in evaluation order |
| `abstract_count` | `int` | Count of abstract assertions (for diagnostics) |

### `FormulaAssertion` (base, sealed hierarchy)

| Field | Type | Description |
|-------|------|-------------|
| `assertion_id` | `str` | Unique ID from taxonomy linkbase |
| `label` | `str \| None` | Human-readable label (from generic label linkbase) |
| `severity` | `ValidationSeverity` | From `@severity` or defaulted to `ERROR` |
| `abstract` | `bool` | `@abstract="true"` → skip evaluation |
| `variables` | `tuple[FactVariableDefinition, ...]` | Bound fact variables |
| `precondition_xpath` | `str \| None` | XPath condition; if False, skip assertion |

**Concrete subclasses**:
- `ValueAssertionDefinition(test_xpath: str)` — `formula:valueAssertion`
- `ExistenceAssertionDefinition(test_xpath: str | None)` — `formula:existenceAssertion`
- `ConsistencyAssertionDefinition(formula_xpath: str, absolute_radius: Decimal | None, relative_radius: Decimal | None)` — `formula:consistencyAssertion`

### `FactVariableDefinition`

| Field | Type | Description |
|-------|------|-------------|
| `variable_name` | `str` | XPath variable name (without `$`) |
| `concept_filter` | `QName \| None` | Concept QName to match |
| `period_filter` | `Literal["instant", "duration"] \| None` | Period type filter |
| `dimension_filters` | `tuple[DimensionFilter, ...]` | Dimension member filters |
| `unit_filter` | `QName \| None` | Unit measure QName |
| `fallback_value` | `str \| None` | XPath expression for fallback when no fact matches |

### `DimensionFilter`

| Field | Type | Description |
|-------|------|-------------|
| `dimension_qname` | `QName` | Dimension concept |
| `member_qnames` | `tuple[QName, ...]` | Allowed members (empty = any member) |
| `exclude` | `bool` | True = dimension must NOT have these members |

---

## PySide6 UI Types

### `ValidationWorker` (QObject, moved to QThread)

```
ValidationWorker(
  instance: XbrlInstance,
  taxonomy: TaxonomyStructure,
)

Signals:
  progress_changed = Signal(int, int, str)     # (current, total, message)
  finding_discovered = Signal(object)           # ValidationFinding (emitted per finding, optional)
  validation_completed = Signal(object)         # ValidationReport
  validation_failed = Signal(str)               # error message

Slots:
  run()     # Called by thread.started signal; runs InstanceValidator.validate_sync()
  cancel()  # Sets cancel_event
```

---

### `ValidationResultsModel` (QStandardItemModel)

Flat model, one row per `ValidationFinding`. Columns:

| Column | Data | Role |
|--------|------|------|
| 0 — Severity | "Error" / "Warning" | DisplayRole; icon via DecorationRole |
| 1 — Rule ID | `finding.rule_id` | DisplayRole |
| 2 — Message | `finding.message` | DisplayRole |
| 3 — Table | `finding.table_label or "–"` | DisplayRole |
| 4 — Concept | `str(finding.concept_qname) or "–"` | DisplayRole |

`Qt.UserRole` on row 0 stores the full `ValidationFinding` object for retrieval on selection.

---

### `ValidationFilterProxy` (QSortFilterProxyModel)

```
ValidationFilterProxy(parent=None)

  set_severity_filter(severity: ValidationSeverity | None) -> None
    """None = show all. ERROR = errors only. WARNING = warnings only."""

  set_table_filter(table_id: str | None) -> None
    """None = show all tables. str = show only findings for this table."""

  clear_filters() -> None

  filterAcceptsRow(source_row, source_parent) -> bool
    """ANDs severity_filter and table_filter."""
```

---

### `ValidationPanel` (QFrame — composite widget)

The complete validation results panel, embedded in the main window.

```
ValidationPanel(parent=None)

Signals:
  navigate_to_cell = Signal(str, object)   # (table_id, CellCoordinate | None)
  revalidate_requested = Signal()           # user clicked re-validate button

Public API:
  show_report(report: ValidationReport) -> None
    """Replace current results with new report. Preserves active filters."""

  show_progress(current: int, total: int, message: str) -> None
    """Update progress bar; leave previous results visible."""

  clear() -> None
    """Remove all results and reset filters."""

  export_report(report: ValidationReport) -> None
    """Open QFileDialog and delegate to ValidationReportExporter."""
```

**Layout (top-to-bottom)**:
1. Toolbar: `QLabel` (summary counts) + `QComboBox` (severity) + `QComboBox` (table) + `QPushButton` ("Clear Filters") + `QPushButton` ("Re-validate") + `QPushButton` ("Export") + `QProgressBar` (hidden when not running)
2. `QTreeView` with `ValidationFilterProxy` over `ValidationResultsModel`
3. Detail `QTextEdit` (read-only) + `QPushButton` ("Go to cell")

---

## Export Service

### `ValidationReportExporter`

```
ValidationReportExporter()

  export_text(report: ValidationReport, path: Path) -> None
    """
    Write human-readable plain text report to path.
    Raises PermissionError if path is not writable.
    """

  export_json(report: ValidationReport, path: Path) -> None
    """
    Write JSON report to path. Each finding is a JSON object.
    Raises PermissionError if path is not writable.
    """
```

**Text format**: See research.md Decision 7 for exact layout.

**JSON schema**:
```json
{
  "summary": {
    "instance": "<path>",
    "taxonomy": "<name> <version>",
    "run_timestamp": "<ISO8601>",
    "passed": false,
    "error_count": 5,
    "warning_count": 3
  },
  "findings": [
    {
      "rule_id": "va_001",
      "severity": "error",
      "source": "formula",
      "message": "...",
      "table_id": "...",
      "concept": "{ns}local",
      "context_ref": "ctx_01",
      "constraint_type": null
    }
  ]
}
```

---

## Error Types

| Error Class | Extends | When Raised |
|-------------|---------|-------------|
| `ValidationEngineError` | `Exception` | Formula evaluator internal error (caught, converted to finding) |
| `FormulaParseError` | `ValidationEngineError` | Formula linkbase XPath expression cannot be compiled |
| `ExportPermissionError` | `PermissionError` | Export path is not writable |

---

## Entity Relationships

```
TaxonomyStructure (Feature 001, extended)
  └── FormulaAssertionSet
        └── FormulaAssertion [0..*]
              └── FactVariableDefinition [0..*]

XbrlInstance (Feature 002/004) ──read by──▶ StructuralConformanceValidator
                                ──read by──▶ DimensionalConstraintValidator
                                ──read by──▶ FormulaEvaluator

InstanceValidator
  ├── uses ──▶ StructuralConformanceValidator
  ├── uses ──▶ DimensionalConstraintValidator
  └── uses ──▶ FormulaEvaluator
         └── produces ──▶ ValidationReport
                            └── ValidationFinding [0..*]

ValidationWorker (QThread) ──runs──▶ InstanceValidator
                           ──emits──▶ ValidationPanel (signals)

ValidationPanel
  ├── ValidationResultsModel (QStandardItemModel)
  └── ValidationFilterProxy (QSortFilterProxyModel)
        └── stacked over ValidationResultsModel

ValidationReportExporter ──reads──▶ ValidationReport ──writes──▶ filesystem
```

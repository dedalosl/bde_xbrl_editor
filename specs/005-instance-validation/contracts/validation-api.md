# Contract: Instance Validation Module Public API

**Branch**: `005-instance-validation` | **Phase**: 1 | **Date**: 2026-03-26
**Module**: `bde_xbrl_editor.validation`

**Depends on**:
- `bde_xbrl_editor.taxonomy` (Feature 001) — `TaxonomyStructure`, `QName`, `HypercubeModel`
- `bde_xbrl_editor.instance` (Feature 002/004) — `XbrlInstance`, `Fact`, `XbrlContext`
- `bde_xbrl_editor.table_renderer` (Feature 003) — `CellCoordinate` (for navigate-to-cell)

---

## Core Entry Point

### `InstanceValidator`

The single entry point for all validation logic. Runs structural, dimensional, and formula checks in sequence.

```python
from bde_xbrl_editor.validation import InstanceValidator, ValidationReport

validator = InstanceValidator(taxonomy=taxonomy_structure)
report = validator.validate_sync(
    instance=xbrl_instance,
    progress_callback=lambda current, total, msg: ...,  # optional
    cancel_event=cancel_event,  # optional threading.Event
)
```

**Signature**:
```python
class InstanceValidator:
    def __init__(self, taxonomy: TaxonomyStructure) -> None: ...

    def validate_sync(
        self,
        instance: XbrlInstance,
        progress_callback: Callable[[int, int, str], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> ValidationReport:
        """
        Run full validation. Never raises — all validator exceptions are caught and
        converted to ERROR findings with rule_id="internal:validator-error".
        progress_callback(current_step, total_steps, current_assertion_id).
        If cancel_event is set, returns partial report with findings collected so far.
        """
```

**Guarantees**:
- Always returns a `ValidationReport` — never raises
- Structural conformance checks always run, regardless of formula linkbase availability
- If taxonomy has no formula linkbase: `report.formula_linkbase_available == False`, structural + dimensional checks still run
- Abstract assertions (`@abstract="true"`) are never evaluated

---

## Result Types

### `ValidationReport`

```python
@dataclass(frozen=True)
class ValidationReport:
    instance_path: str
    taxonomy_name: str
    taxonomy_version: str
    run_timestamp: datetime
    findings: tuple[ValidationFinding, ...]
    formula_linkbase_available: bool
    structural_checks_run: bool

    # Computed
    @property
    def error_count(self) -> int: ...
    @property
    def warning_count(self) -> int: ...
    @property
    def passed(self) -> bool: ...           # True iff error_count == 0

    def findings_for_table(self, table_id: str) -> tuple[ValidationFinding, ...]: ...
    def findings_by_severity(self, severity: ValidationSeverity) -> tuple[ValidationFinding, ...]: ...
```

### `ValidationFinding`

```python
@dataclass(frozen=True)
class ValidationFinding:
    rule_id: str
    severity: ValidationSeverity          # ValidationSeverity.ERROR or .WARNING
    message: str                          # never empty
    source: Literal["structural", "formula", "dimensional"]
    table_id: str | None = None
    table_label: str | None = None
    concept_qname: QName | None = None
    context_ref: str | None = None
    # Dimensional-only:
    hypercube_qname: QName | None = None
    dimension_qname: QName | None = None
    constraint_type: str | None = None    # CLOSED_MISSING_DIMENSION | PROHIBITED_COMBINATION |
                                          # UNDECLARED_DIMENSION | INVALID_MEMBER
```

### `ValidationSeverity`

```python
class ValidationSeverity(str, Enum):
    ERROR   = "error"
    WARNING = "warning"
```

---

## Individual Validators (internal, but testable directly)

### `StructuralConformanceValidator`

```python
class StructuralConformanceValidator:
    def validate(self, instance: XbrlInstance) -> list[ValidationFinding]:
        """
        Run all 8 structural checks. Returns empty list if all pass.
        All findings have source="structural", severity=ERROR.
        Never raises.
        """
```

**Structural rule IDs**:
| Rule ID | Check |
|---------|-------|
| `structural:missing-schemaref` | No `link:schemaRef` element |
| `structural:unresolved-context-ref` | Fact references non-existent context |
| `structural:unresolved-unit-ref` | Numeric fact references non-existent unit |
| `structural:incomplete-context` | Context missing entity or period element |
| `structural:period-type-mismatch` | Concept period type ≠ context period type |
| `structural:duplicate-fact` | Same concept + contextRef + unitRef appears twice |
| `structural:missing-namespace` | Required namespace (`xbrli`, `link`, `xlink`) not declared |

---

### `DimensionalConstraintValidator`

```python
class DimensionalConstraintValidator:
    def __init__(self, taxonomy: TaxonomyStructure) -> None: ...

    def validate(self, instance: XbrlInstance) -> list[ValidationFinding]:
        """
        Validate dimensional constraints for all facts.
        Returns empty list if all pass. Never raises.
        All findings have source="dimensional", severity=ERROR.
        """
```

**Dimensional rule IDs**:
| Rule ID | Constraint type |
|---------|----------------|
| `dimensional:undeclared-dimension` | Dimension not in any hypercube covering concept |
| `dimensional:invalid-member` | Member not in dimension domain |
| `dimensional:closed-missing-dimension` | Closed hypercube: required dimension absent |
| `dimensional:prohibited-combination` | notAll: prohibited concept+dimension combination present |

---

### `FormulaEvaluator`

```python
class FormulaEvaluator:
    def __init__(
        self,
        taxonomy: TaxonomyStructure,
        progress_callback: Callable[[int, int, str], None] | None = None,
        cancel_event: threading.Event | None = None,
    ) -> None: ...

    def evaluate(self, instance: XbrlInstance) -> list[ValidationFinding]:
        """
        Evaluate all non-abstract formula assertions. Returns [] if no formula linkbase.
        Assertion failures produce findings with source="formula".
        Severity from assertion @severity attribute (default: ERROR).
        Never raises — internal errors produce an ERROR finding.
        """
```

---

## Export

### `ValidationReportExporter`

```python
class ValidationReportExporter:
    def export_text(self, report: ValidationReport, path: Path) -> None:
        """
        Write plain text report. Raises PermissionError if path not writable.
        """

    def export_json(self, report: ValidationReport, path: Path) -> None:
        """
        Write JSON report. Raises PermissionError if path not writable.
        """
```

---

## PySide6 UI Contract

### `ValidationWorker` (used with QThread)

```python
class ValidationWorker(QObject):
    # Signals
    progress_changed   = Signal(int, int, str)   # (current, total, assertion_id)
    validation_completed = Signal(object)         # ValidationReport
    validation_failed  = Signal(str)              # error message string

    def __init__(
        self,
        instance: XbrlInstance,
        taxonomy: TaxonomyStructure,
        parent: QObject | None = None,
    ) -> None: ...

    @Slot()
    def run(self) -> None:
        """
        Invoked via thread.started signal. Calls InstanceValidator.validate_sync().
        Emits validation_completed on success or validation_failed on unexpected error.
        """

    @Slot()
    def cancel(self) -> None:
        """Sets internal cancel_event; worker exits cleanly at next check point."""
```

**Wiring pattern**:
```python
thread = QThread()
worker = ValidationWorker(instance, taxonomy)
worker.moveToThread(thread)
thread.started.connect(worker.run)
worker.validation_completed.connect(panel.show_report)
worker.progress_changed.connect(panel.show_progress)
worker.validation_failed.connect(handle_error)
thread.start()
```

---

### `ValidationPanel` (QFrame)

```python
class ValidationPanel(QFrame):
    # Signals
    navigate_to_cell   = Signal(str, object)  # (table_id: str, coord: CellCoordinate | None)
    revalidate_requested = Signal()

    def show_report(self, report: ValidationReport) -> None:
        """
        Populate results list from report. Preserves active severity/table filters.
        Hides progress bar. Updates summary label.
        """

    def show_progress(self, current: int, total: int, message: str) -> None:
        """
        Update progress bar and status label. Previous results remain visible.
        """

    def clear(self) -> None:
        """Remove all results, reset filters, hide progress bar."""

    def set_available_tables(self, tables: list[tuple[str, str]]) -> None:
        """
        Populate the table filter combobox.
        tables: list of (table_id, table_label) pairs.
        """
```

**navigate_to_cell contract**: Emitted when user double-clicks a finding row OR clicks "Go to cell" button. `table_id` is `finding.table_id`; `coord` is derived from `finding.concept_qname + finding.context_ref` by looking up the table layout — `None` if no cell mapping exists. Main window connects this to `XbrlTableView.navigate_to_cell(table_id, coord)`.

---

## Error Hierarchy

```python
class ValidationError(Exception): ...          # base

class ValidationEngineError(ValidationError): ...   # formula evaluator internal error
class FormulaParseError(ValidationEngineError): ...  # XPath cannot be compiled
class ExportPermissionError(PermissionError): ...    # cannot write export file
```

All `ValidationEngineError` subclasses are **caught inside `InstanceValidator.validate_sync()`** and converted to `ValidationFinding(rule_id="internal:validator-error", severity=ERROR, ...)`. They are not propagated to callers.

---

## Integration with Main Window

```python
# In MainWindow / EditorView:

def _trigger_validation(self):
    if self._validation_thread and self._validation_thread.isRunning():
        return  # validation already in progress; ignore duplicate trigger

    self._validation_worker = ValidationWorker(self._instance, self._taxonomy)
    self._validation_thread = QThread()
    self._validation_worker.moveToThread(self._validation_thread)
    self._validation_thread.started.connect(self._validation_worker.run)
    self._validation_worker.validation_completed.connect(self._on_validation_done)
    self._validation_worker.validation_failed.connect(self._on_validation_error)
    self._validation_worker.progress_changed.connect(self._validation_panel.show_progress)
    self._validation_thread.start()

def _on_validation_done(self, report: ValidationReport):
    self._last_validation_report = report
    self._validation_panel.show_report(report)
    self._validation_thread.quit()
```

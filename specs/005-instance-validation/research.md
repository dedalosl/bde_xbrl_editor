# Research: Instance Validation

**Branch**: `005-instance-validation` | **Phase**: 0 | **Date**: 2026-03-26
**Inherits from**: Features 001–004 tech stack (Python 3.11+, PySide6, lxml, elementpath, dataclasses)

---

## Decision 1: XBRL Formula Linkbase Evaluation — elementpath + custom XFI

**Decision**: Implement formula assertion evaluation using `elementpath` (XPath 2.0) for expression parsing and evaluation, with a custom implementation of the XBRL Formula Instance Functions (`xfi:`) namespace. Do **not** depend on Arelle or saxonche as runtime formula evaluation engines.

**Rationale**:
- **Arelle** is the only Python library with mature XBRL formula support (value/existence/consistency assertions, all filter types, XFI functions). However, adding Arelle as a runtime dependency pulls in a large, GPL-licensed codebase that conflicts with the project's LGPL distribution goal and the constitution's YAGNI principle.
- **saxonche** (SaxonHE 12.9 Python wrapper) executes XPath 2.0 efficiently but has no understanding of XBRL constructs (formula variables, fact filters, `xfi:` extension functions). Wiring a full formula execution engine on top of Saxon requires essentially re-implementing the formula processor itself.
- **elementpath** already in the stack for table linkbase processing. It supports XPath 2.0 with custom function libraries registered via `XPathToken.register_function()`. The `xfi:` function namespace (`http://xbrl.org/2008/function/instance`) can be implemented as Python callbacks returning typed results, covering the subset of XFI functions actually used in BDE taxonomy formula linkbases (`xfi:facts-in-instance`, `xfi:context`, `xfi:period`, `xfi:segment`, `xfi:scenario`, `xfi:unit`, `xfi:concept`, `xfi:period-start`, `xfi:period-end`, `xfi:instant`).
- BDE taxonomy formula linkbases primarily use `formula:valueAssertion` with fact-variable bindings and simple arithmetic/comparison expressions — not the full formula specification surface. A focused implementation of the most-used formula features is feasible and aligns with YAGNI.

**Evaluation algorithm** (per assertion):
1. Collect `formula:factVariable` arcs → bind each variable to the matching fact set (applying attached filters: concept, context, period, dimension).
2. Evaluate precondition XPath (if any) against the bound variable set. If False, skip assertion.
3. For `valueAssertion`: evaluate the `@test` XPath expression over all cross-product variable binding tuples. Assertion passes if `@test` evaluates to True for all tuples; fails otherwise.
4. For `existenceAssertion`: assertion passes if at least one matching fact exists for the bound variable.
5. For `consistencyAssertion`: evaluate the formula expression to a computed value, compare to each matching fact value; assertion passes if ratio ≤ `@absoluteAcceptanceRadius` or relative radius.

**Filter support**: concept filter (most common), context filter (period, entity), dimension filter (explicit members), tuple filter, unit filter. Each filter maps to a Python predicate applied to the candidate fact set.

**Alternatives considered**:
- Subprocess call to Arelle CLI: viable for correctness but introduces a system dependency, makes testing hard, and is slow for interactive use.
- saxonche with XBRL schema documents: cannot evaluate formula variables; would require building a full custom formula processor on top anyway.
- py-xbrl: incomplete formula support; not actively maintained for XBRL 2.1 formula spec.

---

## Decision 2: XBRL Structural Conformance Checks — lxml + xmlschema

**Decision**: Implement structural conformance as a multi-stage validator using lxml for structural traversal and xmlschema for schema-level validation. Run synchronously before formula evaluation, in this order:
1. Well-formed XML (lxml parse — free, already happens at load time)
2. Root element must be `{http://www.xbrl.org/2003/instance}xbrl`
3. At least one `link:schemaRef` present with a non-empty `@xlink:href`
4. All `@contextRef` attributes in facts map to a `xbrli:context` id in the instance
5. All `@unitRef` attributes in numeric facts map to a `xbrli:unit` id in the instance
6. Each `xbrli:context` has exactly one entity, one period (duration or instant)
7. Period type consistency: duration concepts paired with duration contexts; instant concepts with instant contexts
8. Duplicate fact detection: same concept + contextRef + unitRef → error
9. Required namespace declarations: `xbrli`, `link`, `xlink` in document namespace map

**Rationale**: lxml parse already validates well-formedness. The subsequent checks are straightforward XPath or dict lookups against the already-parsed tree. Running structural checks first ensures the formula engine receives a structurally valid instance; it avoids confusing formula errors that are actually caused by structural problems.

**Alternatives considered**: Full xmlschema validation of the instance against the combined DTS schema — correct in principle but very slow for large taxonomy DTS (hundreds of imported schemas). Structural checks by hand are faster and sufficient for catching the practical issues BDE users encounter.

---

## Decision 3: Dimensional Hypercube Constraint Validation — HypercubeModel from Feature 001

**Decision**: Dimensional validation uses the `HypercubeModel` already built during taxonomy loading (Feature 001). Per-fact validation checks:
1. For each non-default dimension value in a fact's context: verify the dimension is declared in the hypercube that covers the fact's concept (not a forbidden dimension for that concept).
2. For closed hypercubes (`@closed="true"`): verify all required dimensions are present in the fact's context (no missing mandatory dimension members).
3. For `notAll` hypercubes (prohibited concept-dimension combinations): verify the fact does not simultaneously belong to a prohibited combination.
4. Default member handling: if a dimension is declared in the hypercube but the context does not provide an explicit dimension value, the taxonomy-declared default member applies (no violation).

**Violation message structure** (FR-014): `ValidationFinding` includes `concept_qname`, `context_ref`, `hypercube_qname`, `dimension_qname`, `constraint_type` (one of `CLOSED_MISSING_DIMENSION`, `PROHIBITED_COMBINATION`, `UNDECLARED_DIMENSION`, `INVALID_MEMBER`).

**Alternatives considered**: Re-parsing taxonomy for dimension constraints at validation time — rejected; `HypercubeModel` from taxonomy loading already has everything needed.

---

## Decision 4: Abstract Assertion Exclusion (FR-013)

**Decision**: Before iterating formula linkbase assertions for evaluation, filter out any assertion whose `@abstract="true"` attribute is set. Abstract assertions are template patterns used in taxonomy authoring; they are linked to concrete assertions via arc relationships and must never be evaluated directly. Detection: read `@abstract` attribute from the assertion element; if `"true"` (case-insensitive), skip.

**Rationale**: XBRL Formula 1.0 spec §3.1 defines abstract assertions. BDE taxonomies use abstract assertion patterns as parameterised templates — evaluating them directly produces incorrect results or exceptions because they have unresolved variable bindings.

---

## Decision 5: PySide6 Validation Results Panel — QTreeView with QStandardItemModel + QSortFilterProxyModel

**Decision**: Use `QTreeView` (not `QTableView`) for the validation results list. A `QSortFilterProxyModel` stacked on a flat `QStandardItemModel` provides multi-criteria filtering (severity + table). The panel layout:
- Top bar: summary label ("5 errors, 3 warnings"), severity `QComboBox`, table `QComboBox`, "Clear filters" button
- Tree/list: one row per `ValidationFinding`, columns: Severity | Rule ID | Message | Table | Concept
- Bottom: detail panel (`QTextEdit` read-only) showing full finding details + "Go to cell" button

**Multi-filter proxy**: Subclass `QSortFilterProxyModel`, override `filterAcceptsRow()` to AND two criteria: `_severity_filter` (All / Error / Warning) and `_table_filter` (All / specific table name). Both filters are updated on combobox `currentIndexChanged` signals.

**Navigate-to-cell**: `ValidationPanel.finding_selected` signal carries `(table_id: str, cell_coord: CellCoordinate | None)`. Main window connects this to `XbrlTableView.navigate_to_cell(table_id, coord)`.

**Alternatives considered**: `QTableView` with `QAbstractTableModel` — equally viable but `QTreeView` with `QStandardItemModel` is faster to populate for read-only result lists and allows future grouping by table. `QListView` — insufficient column support.

---

## Decision 6: Background Validation Thread — QThread Worker Pattern

**Decision**: Run validation in a dedicated `QThread` using the Worker-object pattern (move a `ValidationWorker` QObject to a thread, not subclass QThread). Progress signals: `progress_changed(current: int, total: int, message: str)`, `finding_discovered(finding: ValidationFinding)`, `validation_completed(report: ValidationReport)`, `validation_failed(error: str)`.

**Keep-previous-results rule** (FR-009 / US3 SC-003): While re-validation is running, the previous results remain visible (not cleared). Results are swapped atomically only when `validation_completed` fires. A `QProgressBar` + status label in a non-modal toolbar area shows progress.

**Cancellation**: `ValidationWorker.cancel()` sets a `threading.Event`; the worker checks it between assertions and exits cleanly.

**Alternatives considered**: `QRunnable + QThreadPool` — simpler for fire-and-forget, but signals from `QRunnable` require an auxiliary `QObject` anyway, adding the same complexity. `asyncio` — poor PySide6 integration in Qt 6.4 LTS; `QThread` is the standard Qt concurrency primitive.

---

## Decision 7: Validation Report Export — Plain Text with JSON Option

**Decision**: Primary export format is **plain text** (`.txt`), human-readable, structured with clear section headers. A secondary **JSON** format (`.json`) is offered as an alternative for programmatic consumption. Export via `QFileDialog.getSaveFileName()` with a filter `"Text files (*.txt);;JSON files (*.json)"`.

**Plain text structure**:
```
BDE XBRL Instance Validation Report
====================================
Instance:   <filename>
Taxonomy:   <taxonomy name and version>
Run date:   <ISO 8601 datetime>
Result:     FAILED (5 errors, 3 warnings)  |  PASSED

ERRORS (5)
----------
[E001] RULE: formula:assertion-id
       Message: <human-readable message>
       Table:   <table label or N/A>
       Concept: <qname or N/A>
       Context: <context_ref>

...
```

**JSON structure**: Array of finding objects with fields matching `ValidationFinding` dataclass; plus a `summary` object at the root.

**Alternatives considered**: CSV — loses the hierarchical severity grouping; harder to read. HTML — unnecessary complexity for a plain audit report. PDF — requires additional library.

---

## Decision 8: Severity Classification

**Decision**: Severity is read from the formula linkbase. Each assertion element carries an optional `@severity` attribute (`error` or `warning`). If the attribute is absent, default to `error` (spec assumption §5). Structural conformance violations are always `error`.

**Rationale**: BDE taxonomies follow the XBRL Formula 1.0 severity extension. The assumption that absent severity = error is explicitly documented in the spec assumptions and matches the BDE submission validation expectation.

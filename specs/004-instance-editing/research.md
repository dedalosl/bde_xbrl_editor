# Research: Instance Editing

**Branch**: `004-instance-editing` | **Phase**: 0 | **Date**: 2026-03-26
**Inherits from**: Features 001–003 tech stack (Python 3.11+, PySide6, lxml, dataclasses)

---

## Decision 1: Parsing XBRL Instance Facts with lxml

**Decision**: Use lxml XPath with a predefined namespace dictionary to distinguish fact elements from metadata elements. All child elements of `xbrli:xbrl` whose namespace is NOT `xbrli`, `link`, or `xlink` are treated as facts. `contextRef` and `unitRef` are plain attribute lookups. Filing indicators are detected by checking element tag against `{http://www.eurofiling.info/xbrl/ext/filing-indicators}filingIndicator`.

**Rationale**: XBRL 2.1 places all facts as direct or indirect children of the root element in their own taxonomy-defined namespaces. Metadata elements (`xbrli:context`, `xbrli:unit`, `link:schemaRef`) are in well-known namespaces that can be excluded by namespace check. Attribute lookups for `@contextRef` and `@unitRef` are direct and fast. lxml's `element.tag` returns Clark notation `{namespace}local` which makes namespace-aware filtering reliable regardless of document prefix bindings.

**Algorithm**:
1. Parse root element; assert `xbrli:xbrl` namespace.
2. Iterate `root` children; skip known metadata namespaces (`xbrli`, `link`, `xlink`).
3. For remaining elements: tag → `(namespace, local_name)` → `QName`; read `@contextRef`, `@unitRef`, `@decimals`, text content.
4. Detect `ef-find:filingIndicator` by full Clark tag before the generic fact loop.
5. Orphaned facts (concept `QName` not in `taxonomy.concepts`) are collected in `OrphanFact` list, preserved unchanged, and reported to the user.

**Alternatives considered**: python-xbrl library — higher-level but adds a third-party dependency and is not actively maintained for XBRL 2.1 edge cases. Manual child iteration — slower and more error-prone than filtered XPath.

---

## Decision 2: Resolving the schemaRef Taxonomy Path

**Decision**: Resolve `link:schemaRef/@xlink:href` relative to the instance file's directory using `Path(instance_path).parent / href`. If the result is an absolute path, use it directly. If the href is an HTTP/HTTPS URL, extract the path component and attempt the same directory as the instance. If resolution fails, ask the user to point to the taxonomy manually.

**Rationale**: BDE taxonomies are distributed as unpacked local directories alongside their instances, so relative path resolution against the instance's parent directory is almost always correct. The XBRL 2.1 spec permits relative URIs in schemaRef, resolved per RFC 3986. Network calls are disabled by default (Feature 001 `LoaderSettings.allow_network=False`); the manual override path covers the case where the user has the taxonomy in a different location.

**Resolution order**:
1. If href is a `file://` URI → strip scheme, resolve as absolute path.
2. If href is a relative URI (no scheme, no leading `/`) → `Path(instance_dir) / href`.
3. If href is an absolute path → use directly.
4. If href is HTTP/HTTPS → try `Path(instance_dir) / Path(urllib.parse.urlparse(href).path).name`.
5. If none resolved → prompt user with a folder picker dialog.

**Alternatives considered**: Catalog-based URI mapping — more robust for large enterprises but adds complexity beyond v1 scope. Recursive upward search — ambiguous when multiple taxonomy versions coexist.

---

## Decision 3: PySide6 Inline Cell Editing — QStyledItemDelegate

**Decision**: Subclass `QStyledItemDelegate`; override `createEditor()` (returns type-appropriate widget), `setEditorData()` (populates editor from raw `Qt.UserRole` value), `setModelData()` (validates, then calls `InstanceEditor` only if valid), `updateEditorGeometry()` (positions editor over cell rect).

**Rationale**: `QStyledItemDelegate` is the Qt standard for in-table editing. It integrates with the stylesheet system and requires no custom paint overrides for simple text input. `setModelData()` is the correct validation gate — if input is invalid, do not call `model.setData()`; instead mark the editor widget (red border, tooltip) and call `editor.setFocus()` to prevent the editor from closing while the user sees the error. The editor stays open until the user either fixes the value or presses Escape.

**Key implementation detail**: Qt closes the editor on focus loss. To keep the editor open on invalid input, override `eventFilter()` in the delegate and intercept `QEvent.FocusOut` — call `editor.setFocus()` immediately to return focus to the editor, then return `True` to suppress the default close-on-focusout behaviour.

**Alternatives considered**: Modal dialog per cell — too disruptive for tabular entry. QItemDelegate (older class) — deprecated in favour of QStyledItemDelegate. Validation-only in `setModelData` without keeping editor open — poor UX; user loses context of the error.

---

## Decision 4: Numeric Input Validation — QDoubleValidator with QLocale

**Decision**: Use `QDoubleValidator` with `setLocale(QLocale())` (system locale) for monetary and decimal facts; `QIntValidator` for integer facts. Visual feedback via stylesheet on the editor `QLineEdit` (red border on invalid state). `QDateEdit` for date facts with `YYYY-MM-DD` display format. `QComboBox` with `["true", "false"]` for boolean facts.

**Rationale**: `QDoubleValidator.setLocale()` makes the validator respect the system locale's decimal separator and thousands grouping, so Spanish users type `1.234,56` while the stored canonical value uses the invariant `.` separator. The validator's `Intermediate` and `Invalid` states drive the border colour. On `setModelData()`, the value is normalised to the XBRL canonical form (`.` decimal separator, no thousands separators) before storing in the `Fact`.

**Alternatives considered**: `QRegularExpressionValidator` for full control — locale-agnostic; rejected because locale-aware grouping rules are complex to replicate. `inputMask` — too rigid; incompatible with validators in some Qt versions.

---

## Decision 5: XBRL Type-to-Editor Mapping

| XBRL type | Editor widget | Validator |
|-----------|--------------|-----------|
| `xbrli:monetaryItemType` | `QLineEdit` | `QDoubleValidator` (locale-aware) |
| `xbrli:decimalItemType` | `QLineEdit` | `QDoubleValidator` (locale-aware) |
| `xbrli:integerItemType` | `QLineEdit` | `QIntValidator` |
| `xbrli:stringItemType` | `QLineEdit` | None (any text) |
| `xbrli:dateItemType` | `QDateEdit` | Built-in date validation |
| `xbrli:booleanItemType` | `QComboBox` | Not applicable |
| Unknown type | `QLineEdit` | None (fallback) |

**Round-trip accuracy**: All numeric types store the raw lexical string from the source XML; never convert to Python `float`. When a user edits a value, parse the locale-formatted input using `locale.atof()` then convert to `decimal.Decimal`, then `str()` for canonical XBRL storage. This preserves xs:decimal precision through the edit cycle.

---

## Decision 6: Unsaved-Change Tracking and Window Guard

**Decision**: Dirty flag lives in `XbrlInstance.has_unsaved_changes` (from Feature 002 model). The main window:
1. Connects to a `changes_made` signal emitted by `InstanceEditor` after every mutation.
2. Calls `self.setWindowModified(True)` when `changes_made` fires — PySide6 automatically appends `[*]` to the window title on macOS/Linux.
3. Overrides `closeEvent(event)`: if `instance.has_unsaved_changes`, shows `QMessageBox` with **Save** / **Discard** / **Cancel**; calls `event.accept()` or `event.ignore()` accordingly.
4. Same guard is applied before "Open File" and "New Instance" actions.

**Rationale**: Model-resident dirty state is the single source of truth — it survives widget re-creation during navigation. Qt's `setWindowModified()` + `[*]` in the title string is the platform-native way to signal unsaved changes. Using `closeEvent()` override is the standard PySide6 pattern; `QMessageBox.exec()` blocks until the user responds.

**Alternatives considered**: `QUndoStack` for undo/redo — heavier; provides full undo history but the spec scopes this feature to simple tracking without undo. Auto-save — inappropriate for regulatory data; user must explicitly confirm saves.

---

## Decision 7: XBRL Round-Trip Value Accuracy

**Decision**: Store all fact values as raw lexical strings (`str`) throughout the in-memory model. Never convert to `float`. When the user provides a new value, normalise to XBRL canonical form using `decimal.Decimal` → `str()` (e.g., `"1234.5"`, not `"1.2345E+3"`). The `@decimals` attribute is stored as a separate `str` field on `Fact` and round-tripped unchanged.

**Rationale**: The XBRL 2.1 spec explicitly states that processors must not apply rounding or reformatting to the lexical representation of reported values. Python `float` has only ~15 significant digits of precision — monetary values in millions of EUR with 6dp would lose precision. `str` storage is zero-cost, lossless, and the simplest approach. `decimal.Decimal` is used only at the moment a user enters or edits a value, to parse the locale-formatted input and produce a canonical XBRL string.

**Alternatives considered**: `decimal.Decimal` as the stored type — correct but heavier; adds a dependency for a field that is mostly read-only. Python `int`/`float` — precision loss; rejected.

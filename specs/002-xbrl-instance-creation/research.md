# Research: XBRL Instance Creation

**Branch**: `002-xbrl-instance-creation` | **Phase**: 0 | **Date**: 2026-03-25
**Inherits from**: Feature 001 tech stack (Python 3.11+, PySide6, lxml, xmlschema)

---

## Decision 1: XBRL 2.1 Instance Document Structure

**Decision**: Minimal valid instance requires `xbrli:xbrl` root → `link:schemaRef` (taxonomy binding) → one or more `xbrli:context` elements → one or more `xbrli:unit` elements (for numeric facts) → fact elements.

**Rationale**: The XBRL 2.1 spec enforces this ordering. `schemaRef` must appear before any facts; it binds the instance to a specific taxonomy entry point via `xlink:href`. Contexts define the entity/period/dimensional scope for facts. Units define the measurement for numeric facts (required for all numeric concepts; absent for strings, booleans, dates).

**Mandatory namespace declarations on root element**:
- `xmlns:xbrli="http://www.xbrl.org/2003/instance"`
- `xmlns:link="http://www.xbrl.org/2003/linkbase"`
- `xmlns:xlink="http://www.w3.org/1999/xlink"`
- `xmlns:xbrldi="http://xbrl.org/2006/xbrldi"` (for dimensional contexts)
- `xmlns:iso4217="http://www.xbrl.org/2003/iso4217"` (for monetary units)
- Plus all concept namespaces declared in the bound taxonomy

**Alternatives considered**: Building instance programmatically with ElementTree (stdlib) — rejected because lxml's `nsmap` support on the root element avoids scattered namespace re-declarations that ElementTree produces.

---

## Decision 2: XBRL Context Structure

**Decision**: Each `xbrli:context` has a unique `@id`, contains `xbrli:entity` (with `xbrli:identifier` bearing a `@scheme` URI) and `xbrli:period` (either `xbrli:instant` with a date, or `xbrli:startDate` + `xbrli:endDate`).

**Rationale**: The context ID is referenced by every fact via `@contextRef`. Context IDs are generated automatically during instance creation as a deterministic hash of (entity scheme, entity identifier, period, dimension members) to ensure uniqueness and reproducibility. The BDE entity scheme URI is taxonomy-specific (e.g., `http://www.bde.es/`) and is declared in the taxonomy metadata.

**Alternatives considered**: Sequential numeric IDs (e.g., `ctx1`, `ctx2`) — simpler but not deterministic across reloads; makes diff-based comparison of two instances harder.

---

## Decision 3: Dimensional Context Encoding

**Decision**: Explicit dimension members are encoded as `xbrldi:explicitMember` children of `xbrli:scenario` within the context. The `@dimension` attribute holds the dimension concept QName and the element text holds the member concept QName. Namespace: `http://xbrl.org/2006/xbrldi`.

**Rationale**: BDE taxonomies use explicit dimensions (closed enumeration of members) for all Z-axis filter values. `xbrli:scenario` is used rather than `xbrli:segment` as this is the convention in EBA/Eurofiling regulatory reporting taxonomies (scenario is for "reporting context" dimensions; segment is for entity sub-reporting). The exact choice must be confirmed against BDE taxonomy samples during implementation.

**Alternatives considered**: `xbrli:segment` — also valid per XBRL Dimensions spec; the correct choice depends on which `@contextElement` the taxonomy's `all`/`notAll` hypercube arc declares. The dimensional config logic must read this attribute from the `HypercubeModel` (Feature 001 data model).

---

## Decision 4: Filing Indicators

**Decision**: Filing indicators use the Eurofiling `ef-find:filingIndicator` element in namespace `http://www.eurofiling.info/xbrl/ext/filing-indicators`. Each element declares `@contextRef` (referencing the filing context) and a text value of the template identifier. The `@filed` attribute (boolean, defaults to `true`) declares whether the template was submitted.

**Rationale**: Filing indicators are the mechanism BDE uses to declare which report tables are included in a submission. They are not standard XBRL facts (they don't correspond to a taxonomy concept) but are metadata elements that BDE's validation engine checks before applying table-specific formula assertions. An instance without a filing indicator for a table will not be validated against that table's rules.

**Filing indicator context**: Filing indicators reference a special context that contains only the entity and period (no dimensional members). This context is always generated, even if no table-specific contexts are created.

**Alternatives considered**: Encoding table inclusion as a standard boolean fact — incorrect; BDE validators specifically expect `ef-find:filingIndicator` elements.

---

## Decision 5: XBRL Unit Handling

**Decision**: Monetary facts use ISO 4217 currency units via `xbrli:measure` with value `iso4217:EUR` (or relevant currency). Dimensionless numeric facts (percentages, ratios) use `xbrli:pure` (`xbrli:measure` = `xbrli:pure`). Non-numeric facts (strings, dates, booleans) require no unit.

**Rationale**: XBRL 2.1 mandates unit references for all numeric facts. BDE taxonomies predominantly use EUR for monetary items. The unit ID is generated as a deterministic string from the measure URI (e.g., `"EUR"` for `iso4217:EUR`). Units are collected upfront from the taxonomy's concept declarations and pre-populated in the instance at creation time for all numeric concepts in the selected tables.

**Alternatives considered**: Generating units on-demand when facts are entered — deferred to Feature 004; Feature 002 pre-populates units for all monetary and pure concepts referenced by the selected tables.

---

## Decision 6: Instance Data Model — Python Dataclasses

**Decision**: Use plain Python `@dataclass` classes (not Pydantic, not attrs) for the mutable in-memory instance model.

**Rationale**: XBRL structural validation is performed by the validation engine (Feature 005), not by the model. The instance model is just a container for data that will be serialised to XML. Python dataclasses provide `__eq__` and `__repr__` for free, are lightweight, and are 3–5× faster than Pydantic for construction-heavy operations (e.g., loading an instance with thousands of facts). Unsaved-change tracking is a simple `_dirty: bool` flag, not a complex validation concern.

**Alternatives considered**:
- Pydantic V2: excellent for validation on assignment, but the overhead is unjustified when validation is done separately by the XBRL engine.
- attrs: good middle ground, but adds a dependency with no benefit over stdlib dataclasses for this use case.

---

## Decision 7: XML Serialisation with lxml

**Decision**: Build the XML tree using `lxml.etree.Element` / `SubElement` with `nsmap={}` on the root element. Serialise via `etree.tostring(root, pretty_print=True, xml_declaration=True, encoding='UTF-8')`.

**Rationale**: lxml's `nsmap` on the root element declares all namespaces once at the top of the document, producing clean output without repeated xmlns declarations throughout the tree. `etree.QName(namespace, local)` is used for all element and attribute names to ensure correct namespace handling. The serialised bytes are written directly to disk.

**Alternatives considered**: Building XML as string concatenation — rejected; namespace handling is too error-prone for a standards-compliant tool.

---

## Decision 8: UI Wizard — QWizard

**Decision**: Use `QWizard` with four `QWizardPage` subclasses for the 4-step instance creation flow: (1) Entity & Period, (2) Table Selection, (3) Dimensional Configuration, (4) Save Location. `validatePage()` on each page enforces step-level constraints.

**Rationale**: QWizard provides built-in linear navigation (Back / Next / Finish), a field registry that makes data from earlier pages available to later pages, automatic Next/Finish button enablement based on mandatory field completion, and `validatePage()` hooks for custom validation before advancing. This eliminates the need to write custom navigation state machine code.

**Alternatives considered**: Custom `QDialog` with `QStackedWidget` — flexible for non-linear flows, but Feature 002's flow is strictly linear, making QWizard the right fit.

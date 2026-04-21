# XBRL 2.1 conformance — next validation buckets

This document is a **sequenced playbook** for reducing the remaining mandatory failures in the XBRL 2.1 conformance suite (~199 at last check). Each section gives **one primary prompt** you can paste into the agent (or use as a spec) so you can tackle buckets **one at a time**.

**Project context**

- Processor: `src/bde_xbrl_editor/` — instance parsing (`instance/parser.py`), structural checks (`validation/structural.py`), orchestration (`validation/orchestrator.py`), taxonomy DTS (`taxonomy/loader.py`, `taxonomy/linkbases/calculation.py`, …).
- Conformance runner: `python -m bde_xbrl_editor.conformance --suite xbrl21` (with suite data paths as in `CLAUDE.md`).
- **Do not edit** files under `conformance/` (suite cases); only change implementation and tests under `src/` / `tests/`.

**Suggested order** (dependencies and risk)

1. **Monetary ISO unit rules** — mostly instance + taxonomy type info; fewer graph algorithms.
2. **Calculation consistency** — needs summation-item arcs, weights, decimals/precision rules; larger surface.
3. **S-equality** — context equality for dimensions, nil, decimals; overlaps calculation binding.
4. **Schema-based segment/scenario substitution** — needs XSD / substitution-group awareness; heaviest.

After each bucket, re-run:

```bash
python -m bde_xbrl_editor.conformance --suite xbrl21 --output-format json --output-file report-xbrl21.json
```

and/or targeted pytest under `tests/integration/conformance/` if present.

---

## 1. Monetary ISO unit rules

**Goal:** Pass conformance variations that require monetary facts to use **ISO 4217** currency measures (correct namespace and local name), and related unit consistency rules (often suite cases in the 304.x / “Unit of Measure” family).

**Why it’s its own bucket:** Findings today are mostly **missing validation**, not parser bugs. You already resolve `structural:unresolved-unit-ref` and period types; monetary measure checks need taxonomy `Concept` data types plus instance `xbrli:unit` / `xbrli:measure` QName checks.

**Primary prompt (copy-paste)**

```text
Implement XBRL 2.1 monetary unit validation for the instance validator (not the conformance suite files).

Requirements:
- For facts whose concept has a monetary (or monetary-derived) item type in the loaded taxonomy, require the fact’s unit to use an ISO 4217 currency measure: correct namespace (http://www.xbrl.org/2003/iso4217) and a valid currency code local name, matching the conformance “Unit of Measure Consistency” cases (304.x and similar).
- Emit ValidationFinding entries with stable rule_ids and ERROR severity; follow patterns in validation/structural.py and validation/orchestrator.py (never raise from validators).
- Add focused unit tests under tests/unit/validation/ with minimal XbrlInstance + TaxonomyStructure fixtures; optionally add a pytest -k filter against one failing conformance variation ID once identified from report-xbrl21.json.

Constraints: do not modify conformance/; keep changes limited to validation + models if needed. Run pytest on affected tests and ruff check changed files.
```

**Done when:** Mandatory failures whose descriptions mention ISO currency / monetary unit / wrong namespace for units drop materially; no regressions on previously passing segment/footnote/duplicate cases.

**Likely touch points:** `validation/structural.py` or a new module imported by `validation/orchestrator.py`; `instance/models.py` (`XbrlUnit`, `Fact`); `taxonomy/models.py` (`Concept`, type QName).

---

## 2. Calculation consistency (summation-item)

**Goal:** Pass cases where the suite expects **invalid** because calculation arcs (summation-item) are inconsistent with reported facts, and cases where **valid** instances rely on correct treatment of duplicate facts, precision/decimals, and weight signs.

**Why it’s its own bucket:** Requires reading **calculation linkbase** arcs already loaded in `TaxonomyStructure`, binding facts to contexts/units, and implementing XBRL 2.1 calculation binding rules (including interaction with inferred precision).

**Primary prompt (copy-paste)**

```text
Add XBRL 2.1 calculation (summation-item) consistency validation to the processor.

Scope:
- Use the taxonomy’s calculation relationships (from taxonomy/linkbases/calculation.py and whatever TaxonomyStructure exposes) for summation-item arcs.
- For each summation binding in the instance, verify contributing facts exist, respect weights, and satisfy the calculation consistency rules expected by the XBRL 2.1 conformance suite (start with failing cases in the 320.x / 331.x families identified from a fresh JSON conformance report).
- Respect decimals vs precision and duplicate-fact reporting per spec where it affects whether a calculation binds; align with existing structural duplicate-fact semantics in validation/structural.py.

Deliverables:
- New validator component or methods called from validation/orchestrator.py, returning ValidationFinding list, severity ERROR, no uncaught exceptions.
- Unit tests with tiny synthetic taxonomy + instance XML or in-memory models mirroring one or two conformance excerpts.
- Do not edit conformance/. Run pytest and ruff on touched files.

Work incrementally: first detect obvious inconsistency (missing contributors, wrong sign), then decimals/precision binding if needed for the next batch of failures.
```

**Done when:** A measurable drop in mandatory failures whose descriptions reference calculation, summation, binding, or equivalent relationships; document any intentionally deferred sub-rules.

**Likely touch points:** `validation/orchestrator.py`, new `validation/calculation.py` (or similar), `taxonomy/models.py`, possibly `instance/parser.py` only if fact metadata (nil, precision) is incomplete.

---

## 3. S-equality (context equality)

**Goal:** Pass cases where two contexts must be considered **S-equal** or **not S-equal** based on entity, period, scenario/segment XML (including duplicate dimensions, typed members, nil facts, decimal lexical forms, etc.) — often 302.11 / 302.12 style cases and calculation-related equivalence.

**Why it’s its own bucket:** It is a **canonical comparison** problem across XML subtrees and typed values, not just QName maps. You may need canonical XML or a careful normalised comparison consistent with the spec.

**Primary prompt (copy-paste)**

```text
Implement XBRL S-equality for contexts (and any fact-level S-equality needed by calculation binding) inside bde_xbrl_editor.

Tasks:
1. From a fresh xbrl21 conformance JSON report, list the top failing test_case_id / variation_id entries whose descriptions mention S-equal, scenario, segment, lexical, or duplicate dimension in context.
2. Introduce a dedicated module (e.g. validation/s_equality.py or instance/s_equal.py) that compares two XbrlContext values plus their original segment/scenario XML if the in-memory model is insufficient — extend the model only if necessary, preferring to store normalised comparable forms at parse time.
3. Use this for: (a) duplicate-context detection if required by suite; (b) calculation contributor grouping if the orchestrator needs S-equal facts; (c) any validator messages the suite expects.
4. Add unit tests for at least the 302.11 and 302.12 scenarios (build minimal XML or etree fixtures).

Constraints: no conformance file edits; no broad refactors; follow existing error-handling patterns (validators return findings). Run pytest + ruff.
```

**Done when:** Targeted 302.11 / 302.12 (and related) mandatory outcomes flip to pass; calculation tests that depend on S-equal grouping improve.

**Likely touch points:** `instance/parser.py` (`_parse_context`, storage of segment/scenario), `instance/models.py` (`XbrlContext`), new comparison module, `validation/orchestrator.py`.

---

## 4. Schema-based segment / scenario substitution checks

**Goal:** Pass cases where segment or scenario content must be validated against XSD — e.g. **no elements in the substitution group of xbrli:item or xbrli:tuple** inside segment/scenario (302.05 / 302.06 style), beyond the current “no raw xbrli:* descendants” guard.

**Why it’s its own bucket:** Requires **taxonomy schema** knowledge (substitution groups, types), possibly `xmlschema` or lxml schema APIs, and clear error reporting when validation is unavailable (e.g. missing imports).

**Primary prompt (copy-paste)**

```text
Extend instance validation so segment and scenario contents are checked against the DTS schema rules required by XBRL 2.1 conformance (items/tuples must not appear in segment/scenario via substitution groups).

Approach:
1. Identify failing variations (302.05, 302.06, and similar) from the latest conformance JSON report.
2. For each context, take the serialized segment and/or scenario subtree (or raw bytes kept on XbrlContext if not already available) and validate against the appropriate schema components discovered from the taxonomy loader — reuse taxonomy/schema.py and TaxonomyStructure where possible; avoid loading unrelated network resources.
3. If full schema validation is too heavy for v1, implement a staged solution: (phase A) resolve element QNames in segment/scenario to global element declarations and reject if substitution group chain hits xbrli:item or xbrli:tuple; (phase B) add full particle validation if still failing cases remain.
4. Surface violations as ValidationFinding (ERROR), source distinct from structural:duplicate-fact, never raise from the validator entrypoint.

Do not modify conformance/. Add unit tests with small XSD + instance fragments mirroring the suite. Run pytest + ruff.
```

**Done when:** 302.05 / 302.06 (and closely related) mandatory failures pass; ensure segment-only taxonomies like SegmentValid.xsd still load and valid 302.01-style instances still pass.

**Likely touch points:** `instance/parser.py`, `instance/models.py`, `taxonomy/schema.py`, new `validation/segment_schema.py` (or similar), `validation/orchestrator.py`.

---

## Optional: how to drive the agent per variation

When a bucket is still large, narrow further with a **secondary prompt**:

```text
Open report-xbrl21.json (or the path I specify). List all mandatory failures where the description contains "<keyword>" and group them by test_case_id. Pick the smallest family (fewest files), implement only what those need, then re-run conformance and show the before/after count for that family.
```

Useful keywords: `calculation`, `summation`, `ISO`, `4217`, `currency`, `S-equal`, `segment`, `scenario`, `substitution`.

---

## Tracking template (for you)

| Bucket                         | Branch / PR | Mandatory fail count before | After | Notes |
|--------------------------------|-------------|-----------------------------|-------|-------|
| Monetary ISO units             |             |                             |       |       |
| Calculation consistency        |             |                             |       |       |
| S-equality                     |             |                             |       |       |
| Segment/scenario schema checks |             |                             |       |       |

Fill counts from `report-xbrl21.json` (`suites[].results` where `mandatory` is true and `outcome` is `fail`).

"""Unit tests for Formula 1.0 static output-resource validation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bde_xbrl_editor.taxonomy.linkbases.formula import parse_formula_linkbase
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    FormulaAssertionSet,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
)
from bde_xbrl_editor.validation.formula.static import FormulaStaticValidator

_NS = "http://example.com/formula"
_XBRLI = "http://www.xbrl.org/2003/instance"


class _FakeLabels:
    def get(self, *args, **kwargs):
        return None


def _concept(local: str, type_local: str, period_type: str = "instant") -> Concept:
    return Concept(
        qname=QName(_NS, local, "eg"),
        data_type=QName(_XBRLI, type_local, "xbrli"),
        period_type=period_type,  # type: ignore[arg-type]
    )


def _taxonomy(assertion_set: FormulaAssertionSet) -> TaxonomyStructure:
    return TaxonomyStructure(
        metadata=TaxonomyMetadata(
            name="Test",
            version="1.0",
            publisher="Example",
            entry_point_path=Path("test.xsd"),
            loaded_at=datetime(2026, 1, 1),
            declared_languages=("en",),
        ),
        concepts={
            QName(_NS, "assets", "eg"): _concept("assets", "monetaryItemType"),
            QName(_NS, "note", "eg"): _concept("note", "stringItemType", "duration"),
        },
        labels=_FakeLabels(),
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
        formula_assertion_set=assertion_set,
    )


def _formula_set(tmp_path: Path, formula_body: str) -> FormulaAssertionSet:
    path = tmp_path / "static-analysis-formula.xml"
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:generic="http://xbrl.org/2008/generic"
               xmlns:formula="http://xbrl.org/2008/formula"
               xmlns:variable="http://xbrl.org/2008/variable"
               xmlns:cf="http://xbrl.org/2008/filter/concept"
               xmlns:xlink="http://www.w3.org/1999/xlink"
               xmlns:eg="{_NS}">
  <generic:link xlink:type="extended">
    <variable:factVariable xlink:type="resource" xlink:label="source_fact"/>
    <cf:conceptName xlink:type="resource" xlink:label="source_concept">
      <cf:concept><cf:qname>eg:assets</cf:qname></cf:concept>
    </cf:conceptName>
    {formula_body}
    <variable:variableArc xlink:type="arc"
                          xlink:from="formula1"
                          xlink:to="source_fact"
                          name="v:source"
                          xlink:arcrole="http://xbrl.org/arcrole/2008/variable-set"/>
    <variable:variableFilterArc xlink:type="arc"
                                xlink:from="source_fact"
                                xlink:to="source_concept"
                                xlink:arcrole="http://xbrl.org/arcrole/2008/variable-filter"/>
  </generic:link>
</link:linkbase>
""",
        encoding="utf-8",
    )
    return parse_formula_linkbase(path)


def _rule_ids(assertion_set: FormulaAssertionSet) -> set[str]:
    return {
        finding.rule_id for finding in FormulaStaticValidator(_taxonomy(assertion_set)).validate()
    }


def test_formula_static_validation_reports_missing_output_concept(tmp_path) -> None:
    assertion_set = _formula_set(
        tmp_path,
        """
    <formula:formula xlink:type="resource" xlink:label="formula1" value="1">
      <formula:aspects>
        <formula:entityIdentifier scheme="'scheme'" value="'entity'"/>
        <formula:period><formula:instant value="xs:date('2026-01-01')"/></formula:period>
      </formula:aspects>
    </formula:formula>
""",
    )

    assert "xbrlfe:missingConceptRule" in _rule_ids(assertion_set)


def test_formula_static_validation_reports_missing_unit_for_numeric_concept(tmp_path) -> None:
    assertion_set = _formula_set(
        tmp_path,
        """
    <formula:formula xlink:type="resource" xlink:label="formula1" value="1">
      <formula:aspects>
        <formula:concept><formula:qname>eg:assets</formula:qname></formula:concept>
        <formula:entityIdentifier scheme="'scheme'" value="'entity'"/>
        <formula:period><formula:instant value="xs:date('2026-01-01')"/></formula:period>
      </formula:aspects>
    </formula:formula>
""",
    )

    assert "xbrlfe:missingUnitRule" in _rule_ids(assertion_set)


def test_formula_static_validation_reports_unknown_source_variable(tmp_path) -> None:
    assertion_set = _formula_set(
        tmp_path,
        """
    <formula:formula xlink:type="resource" xlink:label="formula1" value="1" source="eg:assets"/>
""",
    )

    assert "xbrlfe:nonexistentSourceVariable" in _rule_ids(assertion_set)


def test_formula_static_validation_reports_conflicting_unit_for_non_numeric_concept(
    tmp_path,
) -> None:
    assertion_set = _formula_set(
        tmp_path,
        """
    <formula:formula xlink:type="resource" xlink:label="formula1" value="1" source="v:source">
      <formula:aspects>
        <formula:concept><formula:qname>eg:note</formula:qname></formula:concept>
        <formula:unit/>
      </formula:aspects>
    </formula:formula>
""",
    )

    assert "xbrlfe:conflictingAspectRules" in _rule_ids(assertion_set)

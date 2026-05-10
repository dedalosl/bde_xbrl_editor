"""Tests for taxonomy relationship-set validation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from bde_xbrl_editor.taxonomy.models import TaxonomyMetadata, TaxonomyStructure
from bde_xbrl_editor.validation.relationships import RelationshipSetValidator


def _taxonomy(schema_files: tuple[Path, ...], linkbase_files: tuple[Path, ...]) -> TaxonomyStructure:
    return TaxonomyStructure(
        metadata=TaxonomyMetadata(
            name="Test",
            version="1.0",
            publisher="Test",
            entry_point_path=schema_files[0],
            loaded_at=datetime.now(),
            declared_languages=("en",),
        ),
        concepts={},
        labels=MagicMock(),
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
        schema_files=schema_files,
        linkbase_files=linkbase_files,
    )


def test_custom_arcrole_used_on_rejects_standard_arc_mismatch(tmp_path: Path) -> None:
    schema = tmp_path / "entry.xsd"
    linkbase = tmp_path / "bad.xml"
    schema.write_text(
        """<schema xmlns="http://www.w3.org/2001/XMLSchema"
           xmlns:link="http://www.xbrl.org/2003/linkbase">
  <annotation><appinfo>
    <link:arcroleType id="row-cell" arcroleURI="http://example.com/row-cell" cyclesAllowed="any">
      <link:usedOn>link:presentationArc</link:usedOn>
    </link:arcroleType>
  </appinfo></annotation>
</schema>""",
        encoding="utf-8",
    )
    linkbase.write_text(
        """<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
           xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:arcroleRef xlink:type="simple" xlink:href="entry.xsd#row-cell"
    arcroleURI="http://example.com/row-cell"/>
  <link:calculationLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <link:loc xlink:type="locator" xlink:href="entry.xsd#a" xlink:label="a"/>
    <link:loc xlink:type="locator" xlink:href="entry.xsd#b" xlink:label="b"/>
    <link:calculationArc xlink:type="arc" xlink:from="a" xlink:to="b"
      xlink:arcrole="http://example.com/row-cell"/>
  </link:calculationLink>
</link:linkbase>""",
        encoding="utf-8",
    )

    findings = RelationshipSetValidator().validate_taxonomy(
        _taxonomy((schema,), (linkbase,))
    )

    assert [finding.rule_id for finding in findings] == ["xbrl:arcrole-used-on"]


def test_declared_arcrole_detects_directed_cycle(tmp_path: Path) -> None:
    schema = tmp_path / "entry.xsd"
    linkbase = tmp_path / "cycle.xml"
    schema.write_text(
        """<schema xmlns="http://www.w3.org/2001/XMLSchema"
           xmlns:link="http://www.xbrl.org/2003/linkbase">
  <annotation><appinfo>
    <link:arcroleType id="no-directed" arcroleURI="http://example.com/no-directed" cyclesAllowed="undirected">
      <link:usedOn>link:definitionArc</link:usedOn>
    </link:arcroleType>
  </appinfo></annotation>
</schema>""",
        encoding="utf-8",
    )
    linkbase.write_text(
        """<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
           xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:arcroleRef xlink:type="simple" xlink:href="entry.xsd#no-directed"
    arcroleURI="http://example.com/no-directed"/>
  <link:definitionLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <link:loc xlink:type="locator" xlink:href="entry.xsd#a" xlink:label="a"/>
    <link:loc xlink:type="locator" xlink:href="entry.xsd#b" xlink:label="b"/>
    <link:definitionArc xlink:type="arc" xlink:from="a" xlink:to="b"
      xlink:arcrole="http://example.com/no-directed"/>
    <link:definitionArc xlink:type="arc" xlink:from="b" xlink:to="a"
      xlink:arcrole="http://example.com/no-directed"/>
  </link:definitionLink>
</link:linkbase>""",
        encoding="utf-8",
    )

    findings = RelationshipSetValidator().validate_taxonomy(
        _taxonomy((schema,), (linkbase,))
    )

    assert [finding.rule_id for finding in findings] == [
        "xbrl:relationship-directed-cycle"
    ]


def test_custom_arc_cycles_ignored_without_arcrole_ref(tmp_path: Path) -> None:
    schema = tmp_path / "entry.xsd"
    linkbase = tmp_path / "custom.xml"
    schema.write_text(
        """<schema xmlns="http://www.w3.org/2001/XMLSchema"
           xmlns:link="http://www.xbrl.org/2003/linkbase">
  <annotation><appinfo>
    <link:arcroleType id="no-cycles" arcroleURI="http://example.com/no-cycles" cyclesAllowed="none">
      <link:usedOn>link:presentationArc</link:usedOn>
    </link:arcroleType>
  </appinfo></annotation>
</schema>""",
        encoding="utf-8",
    )
    linkbase.write_text(
        """<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
           xmlns:xlink="http://www.w3.org/1999/xlink"
           xmlns:ex="http://example.com/custom">
  <ex:customLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <link:loc xlink:type="locator" xlink:href="entry.xsd#a" xlink:label="a"/>
    <link:loc xlink:type="locator" xlink:href="entry.xsd#b" xlink:label="b"/>
    <ex:customArc xlink:type="arc" xlink:from="a" xlink:to="b"
      xlink:arcrole="http://example.com/no-cycles"/>
    <ex:customArc xlink:type="arc" xlink:from="b" xlink:to="a"
      xlink:arcrole="http://example.com/no-cycles"/>
  </ex:customLink>
</link:linkbase>""",
        encoding="utf-8",
    )

    assert RelationshipSetValidator().validate_taxonomy(_taxonomy((schema,), (linkbase,))) == []


def test_remote_arcrole_ref_matches_loaded_catalog_schema(tmp_path: Path) -> None:
    schema = tmp_path / "cache" / "www.eurofiling.info" / "eu" / "fr" / "xbrl" / "ext" / "model.xsd"
    schema.parent.mkdir(parents=True)
    linkbase = tmp_path / "hier-cal.xml"
    schema.write_text(
        """<schema xmlns="http://www.w3.org/2001/XMLSchema"
           xmlns:link="http://www.xbrl.org/2003/linkbase">
  <annotation><appinfo>
    <link:arcroleType id="complete-breakdown"
      arcroleURI="http://www.eurofiling.info/xbrl/arcrole/complete-breakdown"
      cyclesAllowed="undirected">
      <link:usedOn>link:calculationArc</link:usedOn>
    </link:arcroleType>
  </appinfo></annotation>
</schema>""",
        encoding="utf-8",
    )
    linkbase.write_text(
        """<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
           xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:arcroleRef xlink:type="simple"
    xlink:href="http://www.eurofiling.info/eu/fr/xbrl/ext/model.xsd#complete-breakdown"
    arcroleURI="http://www.eurofiling.info/xbrl/arcrole/complete-breakdown"/>
  <link:calculationLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <link:loc xlink:type="locator" xlink:href="entry.xsd#a" xlink:label="a"/>
    <link:loc xlink:type="locator" xlink:href="entry.xsd#b" xlink:label="b"/>
    <link:calculationArc xlink:type="arc" xlink:from="a" xlink:to="b"
      xlink:arcrole="http://www.eurofiling.info/xbrl/arcrole/complete-breakdown"/>
  </link:calculationLink>
</link:linkbase>""",
        encoding="utf-8",
    )

    findings = RelationshipSetValidator().validate_taxonomy(
        _taxonomy((schema,), (linkbase,))
    )

    assert not any(f.rule_id == "xbrl:arcrole-undeclared" for f in findings)


def test_prohibited_arc_uses_canonical_locator_href_for_cycle_detection(
    tmp_path: Path,
) -> None:
    schema = tmp_path / "cache" / "www.example.com" / "tax" / "entry.xsd"
    schema.parent.mkdir(parents=True)
    base = tmp_path / "base.xml"
    extension = schema.parent / "extension.xml"
    schema.write_text(
        """<schema xmlns="http://www.w3.org/2001/XMLSchema"
           xmlns:link="http://www.xbrl.org/2003/linkbase"/>""",
        encoding="utf-8",
    )
    base.write_text(
        """<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
           xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:definitionLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <link:loc xlink:type="locator" xlink:href="http://www.example.com/tax/entry.xsd#a" xlink:label="a"/>
    <link:loc xlink:type="locator" xlink:href="http://www.example.com/tax/entry.xsd#b" xlink:label="b"/>
    <link:loc xlink:type="locator" xlink:href="http://www.example.com/tax/entry.xsd#c" xlink:label="c"/>
    <link:loc xlink:type="locator" xlink:href="http://www.example.com/tax/entry.xsd#d" xlink:label="d"/>
    <link:definitionArc xlink:type="arc" xlink:from="a" xlink:to="b"
      xlink:arcrole="http://xbrl.org/int/dim/arcrole/dimension-domain"/>
    <link:definitionArc xlink:type="arc" xlink:from="c" xlink:to="b"
      xlink:arcrole="http://xbrl.org/int/dim/arcrole/dimension-domain"/>
    <link:definitionArc xlink:type="arc" xlink:from="c" xlink:to="d"
      xlink:arcrole="http://xbrl.org/int/dim/arcrole/dimension-domain"/>
    <link:definitionArc xlink:type="arc" xlink:from="a" xlink:to="d"
      xlink:arcrole="http://xbrl.org/int/dim/arcrole/dimension-domain"/>
  </link:definitionLink>
</link:linkbase>""",
        encoding="utf-8",
    )
    extension.write_text(
        """<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
           xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:definitionLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <link:loc xlink:type="locator" xlink:href="entry.xsd#a" xlink:label="a"/>
    <link:loc xlink:type="locator" xlink:href="entry.xsd#d" xlink:label="d"/>
    <link:definitionArc xlink:type="arc" xlink:from="a" xlink:to="d"
      xlink:arcrole="http://xbrl.org/int/dim/arcrole/dimension-domain"
      use="prohibited" priority="1"/>
  </link:definitionLink>
</link:linkbase>""",
        encoding="utf-8",
    )

    findings = RelationshipSetValidator().validate_taxonomy(
        _taxonomy((schema,), (base, extension))
    )

    assert not any(f.rule_id == "xbrl:relationship-cycle" for f in findings)


def test_generic_label_resource_labels_are_link_local_nodes(tmp_path: Path) -> None:
    schema = tmp_path / "generic-label.xsd"
    linkbase = tmp_path / "generic-labels.xml"
    schema.write_text(
        """<schema xmlns="http://www.w3.org/2001/XMLSchema"
           xmlns:link="http://www.xbrl.org/2003/linkbase"
           xmlns:gen="http://xbrl.org/2008/generic">
  <annotation><appinfo>
    <link:arcroleType id="element-label"
      arcroleURI="http://xbrl.org/arcrole/2008/element-label"
      cyclesAllowed="none">
      <link:usedOn>gen:arc</link:usedOn>
    </link:arcroleType>
  </appinfo></annotation>
</schema>""",
        encoding="utf-8",
    )
    linkbase.write_text(
        """<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
           xmlns:xlink="http://www.w3.org/1999/xlink"
           xmlns:gen="http://xbrl.org/2008/generic"
           xmlns:label="http://xbrl.org/2008/label">
  <link:arcroleRef xlink:type="simple" xlink:href="generic-label.xsd#element-label"
    arcroleURI="http://xbrl.org/arcrole/2008/element-label"/>
  <gen:link xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <gen:resource xlink:type="resource" xlink:label="a"/>
    <label:label xlink:type="resource" xlink:label="b">First label</label:label>
    <gen:arc xlink:type="arc" xlink:from="a" xlink:to="b"
      xlink:arcrole="http://xbrl.org/arcrole/2008/element-label"/>
  </gen:link>
  <gen:link xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <gen:resource xlink:type="resource" xlink:label="b"/>
    <label:label xlink:type="resource" xlink:label="a">Second label</label:label>
    <gen:arc xlink:type="arc" xlink:from="b" xlink:to="a"
      xlink:arcrole="http://xbrl.org/arcrole/2008/element-label"/>
  </gen:link>
</link:linkbase>""",
        encoding="utf-8",
    )

    findings = RelationshipSetValidator().validate_taxonomy(
        _taxonomy((schema,), (linkbase,))
    )

    assert not any(f.rule_id == "xbrl:relationship-cycle" for f in findings)

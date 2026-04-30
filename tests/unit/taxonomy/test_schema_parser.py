"""Unit tests for schema parser — concept extraction, type mapping, abstract flag."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from bde_xbrl_editor.taxonomy.models import QName, TaxonomyParseError
from bde_xbrl_editor.taxonomy.schema import (
    build_global_named_type_registry,
    extract_concept_enumerations_for_schema,
    parse_schema,
)

NS_XBRLI = "http://www.xbrl.org/2003/instance"
NS_TEST = "http://test.example/ns"


XSD_CONCEPTS = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
               xmlns:xbrli="http://www.xbrl.org/2003/instance"
               targetNamespace="http://test.example/ns"
               elementFormDefault="qualified">

      <xs:import namespace="http://www.xbrl.org/2003/instance"/>

      <xs:element name="Assets"
                  id="ns_Assets"
                  type="xbrli:monetaryItemType"
                  substitutionGroup="xbrli:item"
                  xbrli:periodType="instant"
                  xbrli:balance="debit"
                  abstract="false"
                  nillable="true"/>

      <xs:element name="EntityName"
                  id="ns_EntityName"
                  type="xbrli:stringItemType"
                  substitutionGroup="xbrli:item"
                  xbrli:periodType="duration"
                  abstract="false"
                  nillable="false"/>

      <xs:element name="AbstractGroup"
                  id="ns_AbstractGroup"
                  type="xbrli:stringItemType"
                  substitutionGroup="xbrli:item"
                  xbrli:periodType="duration"
                  abstract="true"
                  nillable="true"/>

      <!-- Non-XBRL element should NOT be included -->
      <xs:element name="InternalHelper" type="xs:string"/>

    </xs:schema>
""")


@pytest.fixture
def sample_xsd(tmp_path: Path) -> Path:
    p = tmp_path / "sample.xsd"
    p.write_text(XSD_CONCEPTS, encoding="utf-8")
    return p


class TestConceptExtraction:
    def test_extracts_monetary_concept(self, sample_xsd):
        concepts = parse_schema(sample_xsd)
        qname = QName(NS_TEST, "Assets")
        assert qname in concepts

    def test_extracts_string_concept(self, sample_xsd):
        concepts = parse_schema(sample_xsd)
        assert QName(NS_TEST, "EntityName") in concepts

    def test_excludes_non_xbrl_element(self, sample_xsd):
        concepts = parse_schema(sample_xsd)
        assert not any(c.local_name == "InternalHelper" for c in concepts)

    def test_concept_count(self, sample_xsd):
        concepts = parse_schema(sample_xsd)
        assert len(concepts) == 3  # Assets, EntityName, AbstractGroup


class TestConceptAttributes:
    def test_period_type_instant(self, sample_xsd):
        concepts = parse_schema(sample_xsd)
        assets = concepts[QName(NS_TEST, "Assets")]
        assert assets.period_type == "instant"

    def test_period_type_duration(self, sample_xsd):
        concepts = parse_schema(sample_xsd)
        name_concept = concepts[QName(NS_TEST, "EntityName")]
        assert name_concept.period_type == "duration"

    def test_balance_debit(self, sample_xsd):
        concepts = parse_schema(sample_xsd)
        assets = concepts[QName(NS_TEST, "Assets")]
        assert assets.balance == "debit"

    def test_balance_none_for_string(self, sample_xsd):
        concepts = parse_schema(sample_xsd)
        name_concept = concepts[QName(NS_TEST, "EntityName")]
        assert name_concept.balance is None

    def test_abstract_flag_true(self, sample_xsd):
        concepts = parse_schema(sample_xsd)
        abstract = concepts[QName(NS_TEST, "AbstractGroup")]
        assert abstract.abstract is True

    def test_abstract_flag_false(self, sample_xsd):
        concepts = parse_schema(sample_xsd)
        assets = concepts[QName(NS_TEST, "Assets")]
        assert assets.abstract is False

    def test_nillable_true(self, sample_xsd):
        concepts = parse_schema(sample_xsd)
        assets = concepts[QName(NS_TEST, "Assets")]
        assert assets.nillable is True

    def test_nillable_false(self, sample_xsd):
        concepts = parse_schema(sample_xsd)
        name_concept = concepts[QName(NS_TEST, "EntityName")]
        assert name_concept.nillable is False

    def test_substitution_group_item(self, sample_xsd):
        concepts = parse_schema(sample_xsd)
        assets = concepts[QName(NS_TEST, "Assets")]
        assert assets.substitution_group is not None
        assert assets.substitution_group.local_name == "item"
        assert assets.substitution_group.namespace == NS_XBRLI

    def test_data_type_qname(self, sample_xsd):
        concepts = parse_schema(sample_xsd)
        assets = concepts[QName(NS_TEST, "Assets")]
        assert assets.data_type.local_name == "monetaryItemType"


def _write_tuple_schema(path: Path, tuple_body: str) -> None:
    path.write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:xbrli="http://www.xbrl.org/2003/instance"
           xmlns:xlink="http://www.w3.org/1999/xlink"
           xmlns:ex="http://example.com/tuple"
           targetNamespace="http://example.com/tuple"
           elementFormDefault="qualified">
  <xs:element name="child" type="xbrli:stringItemType" substitutionGroup="xbrli:item" xbrli:periodType="instant"/>
  <xs:element name="tuple" substitutionGroup="xbrli:tuple">
    {tuple_body}
  </xs:element>
</xs:schema>
""",
        encoding="utf-8",
    )


class TestXbrlSchemaConstraints:
    def test_tuple_schema_rejects_explicit_xbrl_attribute(self, tmp_path: Path) -> None:
        schema_path = tmp_path / "tuple.xsd"
        _write_tuple_schema(
            schema_path,
            """<xs:complexType>
      <xs:complexContent>
        <xs:restriction base="xs:anyType">
          <xs:sequence><xs:element ref="ex:child"/></xs:sequence>
          <xs:attribute ref="xbrli:periodType" use="optional"/>
        </xs:restriction>
      </xs:complexContent>
    </xs:complexType>""",
        )

        with pytest.raises(TaxonomyParseError, match="xbrl:schema-validation-error"):
            parse_schema(schema_path)

    def test_tuple_schema_rejects_explicit_xlink_attribute(self, tmp_path: Path) -> None:
        schema_path = tmp_path / "tuple.xsd"
        _write_tuple_schema(
            schema_path,
            """<xs:complexType>
      <xs:complexContent>
        <xs:restriction base="xs:anyType">
          <xs:sequence><xs:element ref="ex:child"/></xs:sequence>
          <xs:attribute ref="xlink:href" use="optional"/>
        </xs:restriction>
      </xs:complexContent>
    </xs:complexType>""",
        )

        with pytest.raises(TaxonomyParseError, match="xbrl:schema-validation-error"):
            parse_schema(schema_path)

    def test_tuple_schema_rejects_mixed_content(self, tmp_path: Path) -> None:
        schema_path = tmp_path / "tuple.xsd"
        _write_tuple_schema(
            schema_path,
            """<xs:complexType mixed="true">
      <xs:complexContent>
        <xs:restriction base="xs:anyType">
          <xs:sequence><xs:element ref="ex:child"/></xs:sequence>
        </xs:restriction>
      </xs:complexContent>
    </xs:complexType>""",
        )

        with pytest.raises(TaxonomyParseError, match="mixed content"):
            parse_schema(schema_path)

    def test_tuple_schema_rejects_local_child_declaration(self, tmp_path: Path) -> None:
        schema_path = tmp_path / "tuple.xsd"
        _write_tuple_schema(
            schema_path,
            """<xs:complexType>
      <xs:complexContent>
        <xs:restriction base="xs:anyType">
          <xs:sequence><xs:element name="localChild" type="xs:string"/></xs:sequence>
        </xs:restriction>
      </xs:complexContent>
    </xs:complexType>""",
        )

        with pytest.raises(TaxonomyParseError, match="child declarations"):
            parse_schema(schema_path)

    def test_item_schema_rejects_missing_period_type(self, tmp_path: Path) -> None:
        schema_path = tmp_path / "items.xsd"
        schema_path.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:xbrli="http://www.xbrl.org/2003/instance"
           targetNamespace="http://example.com/item">
  <xs:element name="itemWithoutPeriod" type="xbrli:stringItemType" substitutionGroup="xbrli:item"/>
</xs:schema>
""",
            encoding="utf-8",
        )

        with pytest.raises(TaxonomyParseError, match="missing required xbrli:periodType"):
            parse_schema(schema_path)

    def test_tuple_schema_rejects_period_type(self, tmp_path: Path) -> None:
        schema_path = tmp_path / "items.xsd"
        schema_path.write_text(
            """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:xbrli="http://www.xbrl.org/2003/instance"
           targetNamespace="http://example.com/item">
  <xs:element name="tupleWithPeriod" substitutionGroup="xbrli:tuple" xbrli:periodType="instant"/>
</xs:schema>
""",
            encoding="utf-8",
        )

        with pytest.raises(TaxonomyParseError, match="must not declare xbrli:periodType"):
            parse_schema(schema_path)


XSD_QNAME_ENUM = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
               xmlns:xbrli="http://www.xbrl.org/2003/instance"
               xmlns:tns="http://test.example/ns"
               targetNamespace="http://test.example/ns"
               elementFormDefault="qualified">

      <xs:import namespace="http://www.xbrl.org/2003/instance"/>

      <xs:simpleType name="ChoiceEnum">
        <xs:restriction base="xbrli:QNameItemType">
          <xs:enumeration value="eba_qSC:qx3"/>
          <xs:enumeration value="eba_qSC:qx4"/>
        </xs:restriction>
      </xs:simpleType>

      <xs:element name="qBVQ"
                  type="tns:ChoiceEnum"
                  substitutionGroup="xbrli:item"
                  xbrli:periodType="instant"/>
    </xs:schema>
""")


class TestConceptEnumerationValues:
    def test_parse_schema_attaches_xsd_enumerations(self, tmp_path: Path) -> None:
        p = tmp_path / "enum.xsd"
        p.write_text(XSD_QNAME_ENUM, encoding="utf-8")
        concepts = parse_schema(p)
        q = QName(NS_TEST, "qBVQ")
        assert q in concepts
        assert concepts[q].enumeration_values == ("eba_qSC:qx3", "eba_qSC:qx4")

    def test_cross_file_type_reference(self, tmp_path: Path) -> None:
        types_xsd = tmp_path / "enum_types.xsd"
        items_xsd = tmp_path / "items.xsd"
        types_xsd.write_text(
            textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
                       xmlns:xbrli="http://www.xbrl.org/2003/instance"
                       targetNamespace="http://ext.example/types"
                       elementFormDefault="qualified">
              <xs:import namespace="http://www.xbrl.org/2003/instance"/>
              <xs:simpleType name="SharedChoice">
                <xs:restriction base="xbrli:QNameItemType">
                  <xs:enumeration value="a:one"/>
                  <xs:enumeration value="a:two"/>
                </xs:restriction>
              </xs:simpleType>
            </xs:schema>
            """),
            encoding="utf-8",
        )
        items_xsd.write_text(
            textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
                       xmlns:xbrli="http://www.xbrl.org/2003/instance"
                       xmlns:ext="http://ext.example/types"
                       targetNamespace="http://test.example/ns"
                       elementFormDefault="qualified">
              <xs:import namespace="http://www.xbrl.org/2003/instance"/>
              <xs:import namespace="http://ext.example/types" schemaLocation="enum_types.xsd"/>
              <xs:element name="MetricX"
                          type="ext:SharedChoice"
                          substitutionGroup="xbrli:item"
                          xbrli:periodType="instant"/>
            </xs:schema>
            """),
            encoding="utf-8",
        )
        registry = build_global_named_type_registry([types_xsd, items_xsd], {})
        enums = extract_concept_enumerations_for_schema(items_xsd, None, registry)
        assert enums[QName(NS_TEST, "MetricX")] == ("a:one", "a:two")

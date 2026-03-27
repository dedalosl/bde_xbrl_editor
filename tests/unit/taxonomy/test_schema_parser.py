"""Unit tests for schema parser — concept extraction, type mapping, abstract flag."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from bde_xbrl_editor.taxonomy.models import QName
from bde_xbrl_editor.taxonomy.schema import parse_schema

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

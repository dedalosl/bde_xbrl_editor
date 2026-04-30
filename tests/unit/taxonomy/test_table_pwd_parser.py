"""Unit tests for PWD Table Linkbase parser — breakdown tree construction, node types, RC-codes."""

from __future__ import annotations

import textwrap

from bde_xbrl_editor.taxonomy.linkbases.table_pwd import parse_table_linkbase
from bde_xbrl_editor.taxonomy.models import BreakdownNode

NS_TABLE = "http://xbrl.org/PWD/2013-05-17/table"
NS_TABLE_2014 = "http://xbrl.org/2014/table"
NS_XLINK = "http://www.w3.org/1999/xlink"
NS_LINK = "http://www.xbrl.org/2003/linkbase"


MINIMAL_TABLE_LB = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
                   xmlns:table="http://xbrl.org/PWD/2013-05-17/table"
                   xmlns:xlink="http://www.w3.org/1999/xlink">

      <table:table id="t1"
                   xlink:type="extended"
                   xlink:label="t1"
                   xlink:role="http://example.com/role/t1"/>

    </link:linkbase>
""")

TABLE_WITH_BREAKDOWN = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
                   xmlns:table="http://xbrl.org/PWD/2013-05-17/table"
                   xmlns:xlink="http://www.w3.org/1999/xlink">

      <table:table id="t1"
                   xlink:type="extended"
                   xlink:label="t1"
                   xlink:role="http://example.com/role/t1"/>

      <table:breakdown id="bd_x"
                       xlink:type="resource"
                       xlink:label="bd_x"/>

      <table:ruleNode id="rn1"
                      xlink:type="resource"
                      xlink:label="rn1"
                      abstract="false"
                      merge="false"/>

      <table:tableBreakdownArc xlink:type="arc"
                               xlink:arcrole="http://xbrl.org/PWD/2013-05-17/table/arcrole/table-breakdown"
                               xlink:from="t1"
                               xlink:to="bd_x"
                               axis="xAxis"/>

      <table:breakdownTreeArc xlink:type="arc"
                              xlink:arcrole="http://xbrl.org/PWD/2013-05-17/table/arcrole/breakdown-tree"
                              xlink:from="bd_x"
                              xlink:to="rn1"/>

    </link:linkbase>
""")

TABLE_WITH_BREAKDOWN_2014 = TABLE_WITH_BREAKDOWN.replace(
    "http://xbrl.org/PWD/2013-05-17/table",
    "http://xbrl.org/2014/table",
).replace(
    "http://xbrl.org/PWD/2013-05-17/table/arcrole/table-breakdown",
    "http://xbrl.org/arcrole/2014/table-breakdown",
).replace(
    "http://xbrl.org/PWD/2013-05-17/table/arcrole/breakdown-tree",
    "http://xbrl.org/arcrole/2014/breakdown-tree",
)

TABLE_LABEL_CODES = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
                   xmlns:gen="http://xbrl.org/2008/generic"
                   xmlns:label="http://xbrl.org/2008/label"
                   xmlns:xlink="http://www.w3.org/1999/xlink">
      <gen:link xlink:type="extended">
        <link:loc xlink:type="locator"
                  xlink:href="sample-rend.xml#t1"
                  xlink:label="loc_t1"/>
        <label:label xlink:type="resource"
                     xlink:label="label_t1"
                     xlink:role="http://www.bde.es/xbrl/role/fin-code"
                     xml:lang="es">0010</label:label>
        <gen:arc xlink:type="arc"
                 xlink:arcrole="http://xbrl.org/arcrole/2008/element-label"
                 xlink:from="loc_t1"
                 xlink:to="label_t1"/>
      </gen:link>
    </link:linkbase>
""")

TABLE_LABEL_ES = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
                   xmlns:gen="http://xbrl.org/2008/generic"
                   xmlns:label="http://xbrl.org/2008/label"
                   xmlns:xlink="http://www.w3.org/1999/xlink">
      <gen:link xlink:type="extended">
        <link:loc xlink:type="locator"
                  xlink:href="http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/corep/4.2/tab/c_40.00.a/c_40.00.a-rend.xml#t1"
                  xlink:label="loc_t1"/>
        <label:label xlink:type="resource"
                     xlink:label="label_t1"
                     xlink:role="http://www.xbrl.org/2008/role/label"
                     xml:lang="es">Tabla en espanol</label:label>
        <gen:arc xlink:type="arc"
                 xlink:arcrole="http://xbrl.org/arcrole/2008/element-label"
                 xlink:from="loc_t1"
                 xlink:to="label_t1"/>
      </gen:link>
    </link:linkbase>
""")

TABLE_WITH_ASPECT_NODE_FILTER = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
                   xmlns:table="http://xbrl.org/PWD/2013-05-17/table"
                   xmlns:df="http://xbrl.org/2008/filter/dimension"
                   xmlns:xlink="http://www.w3.org/1999/xlink"
                   xmlns:dim="http://example.com/dim"
                   xmlns:mem="http://example.com/mem">

      <link:roleRef roleURI="http://example.com/role/filter"
                    xlink:type="simple"
                    xlink:href="filter.xsd#role"/>

      <gen:link xmlns:gen="http://xbrl.org/2008/generic"
                xlink:type="extended"
                xlink:role="http://example.com/role/t1">
        <table:table id="t1"
                     xlink:type="resource"
                     xlink:label="t1"/>

        <table:breakdown id="bd_z"
                         xlink:type="resource"
                         xlink:label="bd_z"/>

        <table:aspectNode id="z_root"
                          xlink:type="resource"
                          xlink:label="z_root">
          <table:dimensionAspect>dim:ZDim</table:dimensionAspect>
        </table:aspectNode>

        <df:explicitDimension xlink:type="resource"
                              xlink:label="z_root.filter"
                              id="z_root.filter">
          <df:dimension>
            <df:qname>dim:ZDim</df:qname>
          </df:dimension>
          <df:member>
            <df:qname>mem:RootMember</df:qname>
            <df:linkrole>http://example.com/role/filter</df:linkrole>
            <df:arcrole>http://xbrl.org/int/dim/arcrole/domain-member</df:arcrole>
            <df:axis>descendant</df:axis>
          </df:member>
        </df:explicitDimension>

        <table:breakdownTreeArc xlink:type="arc"
                                xlink:arcrole="http://xbrl.org/arcrole/PWD/2013-05-17/breakdown-tree"
                                xlink:from="bd_z"
                                xlink:to="z_root"
                                order="0"/>

        <table:aspectNodeFilterArc xlink:type="arc"
                                   xlink:arcrole="http://xbrl.org/arcrole/PWD/2013-05-17/aspect-node-filter"
                                   xlink:from="z_root"
                                   xlink:to="z_root.filter"
                                   complement="false"/>

        <table:tableBreakdownArc xlink:type="arc"
                                 xlink:arcrole="http://xbrl.org/arcrole/PWD/2013-05-17/table-breakdown"
                                 xlink:from="t1"
                                 xlink:to="bd_z"
                                 axis="z"
                                 order="1"/>
      </gen:link>
    </link:linkbase>
""")

FILTER_HIER_XSD = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
               xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:xlink="http://www.w3.org/1999/xlink"
               targetNamespace="http://example.com/hier">
      <xs:annotation>
        <xs:appinfo>
          <link:linkbaseRef xlink:type="simple"
                            xlink:href="hier-def.xml"
                            xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"
                            xlink:role="http://www.xbrl.org/2003/role/definitionLinkbaseRef"/>
          <link:roleType roleURI="http://example.com/role/filter" id="role_filter">
            <link:usedOn>link:definitionLink</link:usedOn>
          </link:roleType>
        </xs:appinfo>
      </xs:annotation>
    </xs:schema>
""")

FILTER_MEM_XSD = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
               targetNamespace="http://example.com/mem">
      <xs:element id="root_member_id" name="RootMember"/>
      <xs:element id="child_a_id" name="ChildA"/>
      <xs:element id="child_b_id" name="ChildB"/>
    </xs:schema>
""")

FILTER_HIER_DEF = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
                   xmlns:xlink="http://www.w3.org/1999/xlink">
      <link:definitionLink xlink:type="extended" xlink:role="http://example.com/role/filter">
        <link:loc xlink:type="locator" xlink:label="root" xlink:href="mem.xsd#root_member_id"/>
        <link:loc xlink:type="locator" xlink:label="child_a" xlink:href="mem.xsd#child_a_id"/>
        <link:loc xlink:type="locator" xlink:label="child_b" xlink:href="mem.xsd#child_b_id"/>
        <link:definitionArc xlink:type="arc"
                            xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member"
                            xlink:from="root"
                            xlink:to="child_a"/>
        <link:definitionArc xlink:type="arc"
                            xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member"
                            xlink:from="root"
                            xlink:to="child_b"/>
      </link:definitionLink>
    </link:linkbase>
""")

FILTER_MEM_WITH_ABSTRACT_GROUPS_XSD = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
               targetNamespace="http://example.com/mem">
      <xs:element id="root_member_id" name="RootMember" abstract="true"/>
      <xs:element id="group_id" name="GroupMember" abstract="true"/>
      <xs:element id="child_a_id" name="ChildA"/>
      <xs:element id="child_b_id" name="ChildB"/>
      <xs:element id="abstract_leaf_id" name="AbstractLeaf" abstract="true"/>
    </xs:schema>
""")

FILTER_HIER_WITH_ABSTRACT_GROUPS_DEF = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
                   xmlns:xlink="http://www.w3.org/1999/xlink"
                   xmlns:xbrldt="http://xbrl.org/2005/xbrldt">
      <link:definitionLink xlink:type="extended" xlink:role="http://example.com/role/filter">
        <link:loc xlink:type="locator" xlink:label="root" xlink:href="mem.xsd#root_member_id"/>
        <link:loc xlink:type="locator" xlink:label="group" xlink:href="mem.xsd#group_id"/>
        <link:loc xlink:type="locator" xlink:label="child_a" xlink:href="mem.xsd#child_a_id"/>
        <link:loc xlink:type="locator" xlink:label="child_b" xlink:href="mem.xsd#child_b_id"/>
        <link:loc xlink:type="locator" xlink:label="abstract_leaf" xlink:href="mem.xsd#abstract_leaf_id"/>
        <link:definitionArc xlink:type="arc"
                            xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member"
                            xlink:from="root"
                            xlink:to="group"/>
        <link:definitionArc xlink:type="arc"
                            xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member"
                            xlink:from="group"
                            xlink:to="child_a"/>
        <link:definitionArc xlink:type="arc"
                            xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member"
                            xlink:from="root"
                            xlink:to="child_b"
                            xbrldt:usable="false"/>
        <link:definitionArc xlink:type="arc"
                            xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member"
                            xlink:from="root"
                            xlink:to="abstract_leaf"/>
      </link:definitionLink>
    </link:linkbase>
""")

TABLE_WITH_MALFORMED_ASPECT_NODE_FILTER = TABLE_WITH_ASPECT_NODE_FILTER.replace(
    "<df:linkrole>",
    "< df:linkrole>",
)


class TestMinimalTableParsing:
    def test_parse_minimal_returns_empty_tables_or_one(self, tmp_path):
        lb = tmp_path / "table.xml"
        lb.write_text(MINIMAL_TABLE_LB, encoding="utf-8")
        tables = parse_table_linkbase(lb)
        # May return 0 or 1 tables depending on whether a table:table is detected
        assert isinstance(tables, list)

    def test_table_with_breakdown_parses(self, tmp_path):
        lb = tmp_path / "table.xml"
        lb.write_text(TABLE_WITH_BREAKDOWN, encoding="utf-8")
        tables = parse_table_linkbase(lb)
        # Should find at least one table
        assert len(tables) >= 1

    def test_table_with_breakdown_2014_namespace_parses(self, tmp_path):
        lb = tmp_path / "table-2014.xml"
        lb.write_text(TABLE_WITH_BREAKDOWN_2014, encoding="utf-8")
        tables = parse_table_linkbase(lb)
        assert len(tables) >= 1

    def test_table_id_correct(self, tmp_path):
        lb = tmp_path / "table.xml"
        lb.write_text(TABLE_WITH_BREAKDOWN, encoding="utf-8")
        tables = parse_table_linkbase(lb)
        if tables:
            assert tables[0].table_id == "t1"

    def test_x_breakdown_is_breakdown_node(self, tmp_path):
        lb = tmp_path / "table.xml"
        lb.write_text(TABLE_WITH_BREAKDOWN, encoding="utf-8")
        tables = parse_table_linkbase(lb)
        if tables:
            assert isinstance(tables[0].x_breakdown, BreakdownNode)

    def test_empty_linkbase_returns_empty_list(self, tmp_path):
        lb = tmp_path / "empty.xml"
        lb.write_text(
            '<?xml version="1.0"?><link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"/>',
            encoding="utf-8",
        )
        tables = parse_table_linkbase(lb)
        assert tables == []

    def test_table_fin_code_is_loaded_from_generic_label_linkbase(self, tmp_path):
        rend = tmp_path / "sample-rend.xml"
        rend.write_text(MINIMAL_TABLE_LB, encoding="utf-8")
        codes = tmp_path / "sample-lab-codes.xml"
        codes.write_text(TABLE_LABEL_CODES, encoding="utf-8")

        tables = parse_table_linkbase(rend)

        assert len(tables) == 1
        assert tables[0].table_code == "0010"
        assert tables[0].display_code == "0010  |  t1"

    def test_bde_spanish_table_labels_override_eba_english_when_available(self, tmp_path):
        eba_dir = (
            tmp_path
            / "cache"
            / "www.eba.europa.eu"
            / "eu"
            / "fr"
            / "xbrl"
            / "crr"
            / "fws"
            / "corep"
            / "4.2"
            / "tab"
            / "c_40.00.a"
        )
        bde_dir = (
            tmp_path
            / "cache"
            / "www.bde.es"
            / "es"
            / "fr"
            / "xbrl"
            / "fws"
            / "ebacrr_corep"
            / "4.2"
            / "tab"
            / "c_40.00.a"
        )
        eba_dir.mkdir(parents=True)
        bde_dir.mkdir(parents=True)

        rend = eba_dir / "c_40.00.a-rend.xml"
        rend.write_text(MINIMAL_TABLE_LB, encoding="utf-8")
        en = eba_dir / "c_40.00.a-lab-en.xml"
        en.write_text(
            TABLE_LABEL_ES.replace('xml:lang="es">Tabla en espanol', 'xml:lang="en">English table'),
            encoding="utf-8",
        )
        es = bde_dir / "c_40.00.a-lab-es.xml"
        es.write_text(TABLE_LABEL_ES, encoding="utf-8")

        tables = parse_table_linkbase(rend)

        assert len(tables) == 1
        assert tables[0].label == "Tabla en espanol"
        assert dict(tables[0].label_variants) == {
            "en": "English table",
            "es": "Tabla en espanol",
        }

        tables = parse_table_linkbase(rend, language_preference=("en", "es"))
        assert tables[0].label == "English table"


class TestBreakdownNodeTypes:
    def test_rule_node_type(self):
        from bde_xbrl_editor.taxonomy.linkbases.table_pwd import _node_type_from_tag
        assert _node_type_from_tag(f"{{{NS_TABLE}}}ruleNode") == "rule"

    def test_aspect_node_type(self):
        from bde_xbrl_editor.taxonomy.linkbases.table_pwd import _node_type_from_tag
        assert _node_type_from_tag(f"{{{NS_TABLE}}}aspectNode") == "aspect"

    def test_concept_relationship_node_type(self):
        from bde_xbrl_editor.taxonomy.linkbases.table_pwd import _node_type_from_tag
        assert _node_type_from_tag(f"{{{NS_TABLE}}}conceptRelationshipNode") == "conceptRelationship"

    def test_dimension_relationship_node_type(self):
        from bde_xbrl_editor.taxonomy.linkbases.table_pwd import _node_type_from_tag
        assert _node_type_from_tag(f"{{{NS_TABLE}}}dimensionRelationshipNode") == "dimensionRelationship"

    def test_rule_node_type_2014_namespace(self):
        from bde_xbrl_editor.taxonomy.linkbases.table_pwd import _node_type_from_tag
        assert _node_type_from_tag(f"{{{NS_TABLE_2014}}}ruleNode") == "rule"


class TestBreakdownNodeAttributes:
    def test_abstract_node(self):
        node = BreakdownNode(node_type="rule", is_abstract=True)
        assert node.is_abstract is True

    def test_rc_code_stored(self):
        node = BreakdownNode(node_type="rule", rc_code="R0010")
        assert node.rc_code == "R0010"

    def test_children_default_empty(self):
        node = BreakdownNode(node_type="rule")
        assert node.children == []

    def test_merge_flag(self):
        node = BreakdownNode(node_type="rule", merge=True)
        assert node.merge is True

    def test_aspect_node_filter_is_parsed_into_breakdown_constraints(self, tmp_path):
        lb = tmp_path / "filter-table.xml"
        lb.write_text(TABLE_WITH_ASPECT_NODE_FILTER, encoding="utf-8")
        hier_xsd = tmp_path / "filter.xsd"
        hier_xsd.write_text(FILTER_HIER_XSD, encoding="utf-8")
        mem_xsd = tmp_path / "mem.xsd"
        mem_xsd.write_text(FILTER_MEM_XSD, encoding="utf-8")
        hier_def = tmp_path / "hier-def.xml"
        hier_def.write_text(FILTER_HIER_DEF, encoding="utf-8")

        tables = parse_table_linkbase(lb)

        assert len(tables) == 1
        assert len(tables[0].z_breakdowns) == 1
        z_root = tables[0].z_breakdowns[0]
        assert z_root.aspect_constraints["dimensionAspect"] == "{http://example.com/dim}ZDim"
        assert z_root.aspect_constraints["explicitDimensionFilters"] == [
            {
                "dimension": "{http://example.com/dim}ZDim",
                "members": [
                    {
                        "member": "{http://example.com/mem}RootMember",
                        "linkrole": "http://example.com/role/filter",
                        "arcrole": "http://xbrl.org/int/dim/arcrole/domain-member",
                        "axis": "descendant",
                        "resolved_members": [
                            "{http://example.com/mem}ChildA",
                            "{http://example.com/mem}ChildB",
                        ],
                    }
                ],
                "complement": False,
            }
        ]

    def test_aspect_node_filter_keeps_only_usable_leaf_descendants(self, tmp_path):
        lb = tmp_path / "filter-table.xml"
        lb.write_text(TABLE_WITH_ASPECT_NODE_FILTER, encoding="utf-8")
        hier_xsd = tmp_path / "filter.xsd"
        hier_xsd.write_text(FILTER_HIER_XSD, encoding="utf-8")
        mem_xsd = tmp_path / "mem.xsd"
        mem_xsd.write_text(FILTER_MEM_WITH_ABSTRACT_GROUPS_XSD, encoding="utf-8")
        hier_def = tmp_path / "hier-def.xml"
        hier_def.write_text(FILTER_HIER_WITH_ABSTRACT_GROUPS_DEF, encoding="utf-8")

        tables = parse_table_linkbase(lb)

        assert len(tables) == 1
        z_root = tables[0].z_breakdowns[0]
        assert z_root.aspect_constraints["explicitDimensionFilters"] == [
            {
                "dimension": "{http://example.com/dim}ZDim",
                "members": [
                    {
                        "member": "{http://example.com/mem}RootMember",
                        "linkrole": "http://example.com/role/filter",
                        "arcrole": "http://xbrl.org/int/dim/arcrole/domain-member",
                        "axis": "descendant",
                        "resolved_members": [
                            "{http://example.com/mem}AbstractLeaf",
                            "{http://example.com/mem}ChildA",
                        ],
                    }
                ],
                "complement": False,
            }
        ]

    def test_aspect_node_filter_repairs_malformed_prefixed_start_tag(self, tmp_path):
        lb = tmp_path / "filter-table.xml"
        lb.write_text(TABLE_WITH_MALFORMED_ASPECT_NODE_FILTER, encoding="utf-8")
        hier_xsd = tmp_path / "filter.xsd"
        hier_xsd.write_text(FILTER_HIER_XSD, encoding="utf-8")
        mem_xsd = tmp_path / "mem.xsd"
        mem_xsd.write_text(FILTER_MEM_XSD, encoding="utf-8")
        hier_def = tmp_path / "hier-def.xml"
        hier_def.write_text(FILTER_HIER_DEF, encoding="utf-8")

        tables = parse_table_linkbase(lb)

        assert len(tables) == 1
        z_root = tables[0].z_breakdowns[0]
        assert z_root.aspect_constraints["explicitDimensionFilters"] == [
            {
                "dimension": "{http://example.com/dim}ZDim",
                "members": [
                    {
                        "member": "{http://example.com/mem}RootMember",
                        "linkrole": "http://example.com/role/filter",
                        "arcrole": "http://xbrl.org/int/dim/arcrole/domain-member",
                        "axis": "descendant",
                        "resolved_members": [
                            "{http://example.com/mem}ChildA",
                            "{http://example.com/mem}ChildB",
                        ],
                    }
                ],
                "complement": False,
            }
        ]

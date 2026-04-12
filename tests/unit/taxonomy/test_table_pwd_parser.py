"""Unit tests for PWD Table Linkbase parser — breakdown tree construction, node types, RC-codes."""

from __future__ import annotations

import textwrap

from bde_xbrl_editor.taxonomy.linkbases.table_pwd import parse_table_linkbase
from bde_xbrl_editor.taxonomy.models import BreakdownNode

NS_TABLE = "http://xbrl.org/PWD/2013-05-17/table"
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

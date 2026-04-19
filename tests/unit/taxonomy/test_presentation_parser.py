"""Unit tests for presentation linkbase parser extras."""

from __future__ import annotations

import textwrap

from bde_xbrl_editor.taxonomy.linkbases.presentation import parse_presentation_linkbase
from bde_xbrl_editor.taxonomy.models import QName


def test_parse_presentation_linkbase_extracts_group_table_metadata(tmp_path) -> None:
    lb = tmp_path / "presentation.xml"
    lb.write_text(
        textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
                           xmlns:xlink="http://www.w3.org/1999/xlink">
              <link:loc xlink:type="locator"
                        xlink:href="sample-rend.xml#table_root"
                        xlink:label="table_loc"/>
              <link:loc xlink:type="locator"
                        xlink:href="sample-rend.xml#table_child"
                        xlink:label="child_loc"/>
              <link:arc xlink:type="arc"
                        xlink:arcrole="http://www.eurofiling.info/xbrl/arcrole/group-table"
                        xlink:from="group_root"
                        xlink:to="table_loc"
                        order="1"/>
              <link:arc xlink:type="arc"
                        xlink:arcrole="http://www.eurofiling.info/xbrl/arcrole/group-table"
                        xlink:from="table_loc"
                        xlink:to="child_loc"
                        order="2"/>
            </link:linkbase>
        """),
        encoding="utf-8",
    )

    result = parse_presentation_linkbase(lb, concept_map={})

    assert result.networks == {}
    assert result.group_table_root_fragment == "group_root"
    assert result.group_table_children["group_root"] == [(1.0, "table_root")]
    assert result.group_table_children["table_root"] == [(2.0, "table_child")]
    assert result.group_table_rend_fragments == {"table_root", "table_child"}


def test_parse_presentation_linkbase_keeps_network_output(tmp_path) -> None:
    q_parent = QName("http://example.com", "Parent")
    q_child = QName("http://example.com", "Child")
    lb = tmp_path / "presentation.xml"
    lb.write_text(
        textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
                           xmlns:xlink="http://www.w3.org/1999/xlink">
              <link:presentationLink xlink:type="extended" xlink:role="http://example.com/role/pres">
                <link:loc xlink:type="locator" xlink:href="tax.xsd#parent_id" xlink:label="p"/>
                <link:loc xlink:type="locator" xlink:href="tax.xsd#child_id" xlink:label="c"/>
                <link:presentationArc xlink:type="arc"
                                      xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child"
                                      xlink:from="p"
                                      xlink:to="c"
                                      order="3"/>
              </link:presentationLink>
            </link:linkbase>
        """),
        encoding="utf-8",
    )

    result = parse_presentation_linkbase(
        lb,
        concept_map={"parent_id": q_parent, "child_id": q_child},
    )

    network = result.networks["http://example.com/role/pres"]
    assert len(network.arcs) == 1
    assert network.arcs[0].parent == q_parent
    assert network.arcs[0].child == q_child

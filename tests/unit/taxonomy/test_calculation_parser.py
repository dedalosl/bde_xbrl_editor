"""Unit tests for calculation linkbase parsing."""

from __future__ import annotations

from pathlib import Path

from bde_xbrl_editor.taxonomy.linkbases.calculation import parse_calculation_linkbase
from bde_xbrl_editor.taxonomy.models import QName


def test_parse_calculation_linkbase_decodes_percent_encoded_locator_fragments(
    tmp_path: Path,
) -> None:
    linkbase = tmp_path / "calc.xml"
    linkbase.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:calculationLink xlink:type="extended" xlink:role="http://example.com/role">
    <link:loc xlink:type="locator" xlink:href="tax.xsd#tx_Espa%c3%b1a1" xlink:label="parent"/>
    <link:loc xlink:type="locator" xlink:href="tax.xsd#tx_la_%c3%a1" xlink:label="child"/>
    <link:calculationArc xlink:type="arc"
                         xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item"
                         xlink:from="parent"
                         xlink:to="child"
                         weight="1"/>
  </link:calculationLink>
</link:linkbase>
""",
        encoding="utf-8",
    )
    parent = QName("http://example.com", "España1")
    child = QName("http://example.com", "la_á")

    arcs = parse_calculation_linkbase(
        linkbase,
        {
            "tx_España1": parent,
            "tx_la_á": child,
        },
    )

    assert arcs["http://example.com/role"][0].parent == parent
    assert arcs["http://example.com/role"][0].child == child

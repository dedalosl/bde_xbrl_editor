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


def test_parse_calculation_11_reverses_item_to_summation_direction(
    tmp_path: Path,
) -> None:
    linkbase = tmp_path / "calc11.xml"
    linkbase.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:calculationLink xlink:type="extended" xlink:role="http://example.com/role">
    <link:loc xlink:type="locator" xlink:href="tax.xsd#item" xlink:label="item"/>
    <link:loc xlink:type="locator" xlink:href="tax.xsd#sum" xlink:label="sum"/>
    <link:calculationArc xlink:type="arc"
                         xlink:arcrole="https://xbrl.org/2023/arcrole/summation-item"
                         xlink:from="item"
                         xlink:to="sum"
                         weight="-1"/>
  </link:calculationLink>
</link:linkbase>
""",
        encoding="utf-8",
    )
    item = QName("http://example.com", "Item")
    summation = QName("http://example.com", "Sum")

    arcs = parse_calculation_linkbase(
        linkbase,
        {
            "item": item,
            "sum": summation,
        },
    )

    arc = arcs["http://example.com/role"][0]
    assert arc.parent == summation
    assert arc.child == item
    assert arc.weight == -1


def test_calculation_equivalence_key_uses_resolved_endpoints_not_labels(
    tmp_path: Path,
) -> None:
    linkbase = tmp_path / "calc.xml"
    linkbase.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:calculationLink xlink:type="extended" xlink:role="http://example.com/role">
    <link:loc xlink:type="locator" xlink:href="tax.xsd#parent" xlink:label="A"/>
    <link:loc xlink:type="locator" xlink:href="tax.xsd#parent" xlink:label="X"/>
    <link:loc xlink:type="locator" xlink:href="tax.xsd#child" xlink:label="C"/>
    <link:calculationArc xlink:type="arc"
                         xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item"
                         xlink:from="A"
                         xlink:to="C"
                         order="2.0"
                         weight="1.0"/>
    <link:calculationArc xlink:type="arc"
                         xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item"
                         xlink:from="X"
                         xlink:to="C"
                         order="2.0"
                         weight="1.0"
                         use="prohibited"/>
  </link:calculationLink>
</link:linkbase>
""",
        encoding="utf-8",
    )
    parent = QName("http://example.com", "Parent")
    child = QName("http://example.com", "Child")

    arcs = parse_calculation_linkbase(
        linkbase,
        {
            "parent": parent,
            "child": child,
        },
    )["http://example.com/role"]

    assert arcs[0].equivalence_key == arcs[1].equivalence_key


def test_parse_calculation_expands_shared_locator_label_to_all_concepts(
    tmp_path: Path,
) -> None:
    """397-ABC-calculation.xml: one arc to label shared by B and C."""
    linkbase = tmp_path / "calc.xml"
    linkbase.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:calculationLink xlink:type="extended" xlink:role="http://example.com/role">
    <link:loc xlink:type="locator" xlink:href="tax.xsd#A" xlink:label="sum"/>
    <link:loc xlink:type="locator" xlink:href="tax.xsd#B" xlink:label="item"/>
    <link:loc xlink:type="locator" xlink:href="tax.xsd#C" xlink:label="item"/>
    <link:calculationArc xlink:type="arc"
                         xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item"
                         xlink:from="sum"
                         xlink:to="item"
                         weight="1"/>
  </link:calculationLink>
</link:linkbase>
""",
        encoding="utf-8",
    )
    qa = QName("http://example.com", "A")
    qb = QName("http://example.com", "B")
    qc = QName("http://example.com", "C")
    arcs = parse_calculation_linkbase(
        linkbase, {"A": qa, "B": qb, "C": qc}
    )["http://example.com/role"]
    children = {arc.child for arc in arcs}
    assert children == {qb, qc}
    assert all(arc.parent == qa for arc in arcs)


def test_calculation_equivalence_key_treats_missing_order_as_default(
    tmp_path: Path,
) -> None:
    """210.03: arcs with no order attribute are equivalent to order=1."""
    linkbase = tmp_path / "calc.xml"
    linkbase.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:calculationLink xlink:type="extended" xlink:role="http://example.com/role">
    <link:loc xlink:type="locator" xlink:href="tax.xsd#p" xlink:label="parent"/>
    <link:loc xlink:type="locator" xlink:href="tax.xsd#c" xlink:label="child"/>
    <link:calculationArc xlink:type="arc"
                         xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item"
                         xlink:from="parent"
                         xlink:to="child"
                         order="1"
                         weight="1"
                         use="optional"/>
    <link:calculationArc xlink:type="arc"
                         xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item"
                         xlink:from="parent"
                         xlink:to="child"
                         weight="1"
                         use="prohibited"
                         priority="1"/>
  </link:calculationLink>
</link:linkbase>
""",
        encoding="utf-8",
    )
    parent = QName("http://example.com", "Parent")
    child = QName("http://example.com", "Child")

    arcs = parse_calculation_linkbase(linkbase, {"p": parent, "c": child})[
        "http://example.com/role"
    ]

    assert arcs[0].equivalence_key == arcs[1].equivalence_key


def test_parse_calculation_arc_priority_defaults_to_zero(
    tmp_path: Path,
) -> None:
    linkbase = tmp_path / "calc.xml"
    linkbase.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
               xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:calculationLink xlink:type="extended" xlink:role="http://example.com/role">
    <link:loc xlink:type="locator" xlink:href="tax.xsd#p" xlink:label="parent"/>
    <link:loc xlink:type="locator" xlink:href="tax.xsd#c" xlink:label="child"/>
    <link:calculationArc xlink:type="arc"
                         xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item"
                         xlink:from="parent"
                         xlink:to="child"
                         weight="1"
                         priority="3"/>
    <link:calculationArc xlink:type="arc"
                         xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item"
                         xlink:from="parent"
                         xlink:to="child"
                         weight="1"
                         priority="not-a-number"/>
  </link:calculationLink>
</link:linkbase>
""",
        encoding="utf-8",
    )
    pp = QName("http://example.com", "Parent")
    cc = QName("http://example.com", "Child")

    arcs = parse_calculation_linkbase(linkbase, {"p": pp, "c": cc})["http://example.com/role"]

    assert arcs[0].priority == 3
    assert arcs[1].priority == 0

from __future__ import annotations

from pathlib import Path

from lxml import etree

from bde_xbrl_editor.taxonomy.linkbases.generic_label import parse_generic_label_linkbase
from bde_xbrl_editor.taxonomy.linkbases.label import parse_label_linkbase
from bde_xbrl_editor.taxonomy.models import QName


def test_parse_label_linkbase_prefers_schema_qualified_locator_resolution(tmp_path: Path) -> None:
    schema_a = tmp_path / "a.xsd"
    schema_b = tmp_path / "b.xsd"
    label_lb = tmp_path / "labels.xml"

    schema_a.write_text(
        """<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="http://example.com/a">
  <xs:element name="Wrong" id="dup"/>
</xs:schema>""",
        encoding="utf-8",
    )
    schema_b.write_text(
        """<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="http://example.com/b">
  <xs:element name="Right" id="dup"/>
</xs:schema>""",
        encoding="utf-8",
    )
    label_lb.write_text(
        """<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:labelLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <link:loc xlink:type="locator" xlink:href="b.xsd#dup" xlink:label="loc"/>
    <link:label xlink:type="resource" xlink:label="lab" xml:lang="en" xlink:role="http://www.xbrl.org/2003/role/label">Right label</link:label>
    <link:labelArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label" xlink:from="loc" xlink:to="lab"/>
  </link:labelLink>
</link:linkbase>""",
        encoding="utf-8",
    )

    wrong_qname = QName("http://example.com/a", "Wrong")
    right_qname = QName("http://example.com/b", "Right")

    result = parse_label_linkbase(
        label_lb,
        {"dup": wrong_qname},
        ns_qualified_map={"http://example.com/b#dup": right_qname},
        schema_ns_map={str(schema_b.resolve()): "http://example.com/b"},
    )

    assert right_qname in result
    assert [label.text for label in result[right_qname]] == ["Right label"]
    assert wrong_qname not in result


def test_parse_label_linkbase_keeps_fragment_only_fallback(tmp_path: Path) -> None:
    label_lb = tmp_path / "labels.xml"
    label_lb.write_text(
        """<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:labelLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <link:loc xlink:type="locator" xlink:href="#dup" xlink:label="loc"/>
    <link:label xlink:type="resource" xlink:label="lab" xml:lang="en" xlink:role="http://www.xbrl.org/2003/role/label">Fallback label</link:label>
    <link:labelArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label" xlink:from="loc" xlink:to="lab"/>
  </link:labelLink>
</link:linkbase>""",
        encoding="utf-8",
    )

    qname = QName("http://example.com/a", "Thing")
    result = parse_label_linkbase(label_lb, {"dup": qname})

    assert [label.text for label in result[qname]] == ["Fallback label"]


def test_parse_label_linkbase_uses_xml_helper_for_non_empty_file(
    monkeypatch,
    tmp_path: Path,
) -> None:
    label_lb = tmp_path / "labels.xml"
    label_lb.write_text(
        """<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:labelLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <link:loc xlink:type="locator" xlink:href="#dup" xlink:label="loc"/>
    <link:label xlink:type="resource" xlink:label="lab" xml:lang="en" xlink:role="http://www.xbrl.org/2003/role/label">Recovered label</link:label>
    <link:labelArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label" xlink:from="loc" xlink:to="lab"/>
  </link:labelLink>
</link:linkbase>""",
        encoding="utf-8",
    )

    original_parse = etree.parse

    def flaky_parse(source, *args, **kwargs):
        if isinstance(source, str):
            raise etree.XMLSyntaxError("Document is empty, line 1, column 1", 1, 0, 0)
        return original_parse(source, *args, **kwargs)

    monkeypatch.setattr(etree, "parse", flaky_parse)

    qname = QName("http://example.com/a", "Thing")
    result = parse_label_linkbase(label_lb, {"dup": qname})

    assert [label.text for label in result[qname]] == ["Recovered label"]


def test_parse_generic_label_linkbase_prefers_schema_qualified_locator_resolution(
    tmp_path: Path,
) -> None:
    schema_a = tmp_path / "a.xsd"
    schema_b = tmp_path / "b.xsd"
    label_lb = tmp_path / "gen-labels.xml"

    schema_a.write_text(
        """<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="http://example.com/a">
  <xs:element name="Wrong" id="dup"/>
</xs:schema>""",
        encoding="utf-8",
    )
    schema_b.write_text(
        """<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="http://example.com/b">
  <xs:element name="Right" id="dup"/>
</xs:schema>""",
        encoding="utf-8",
    )
    label_lb.write_text(
        """<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns:gen="http://xbrl.org/2008/generic" xmlns:genlab="http://xbrl.org/2008/label" xmlns:xlink="http://www.w3.org/1999/xlink">
  <gen:link xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <gen:loc xlink:type="locator" xlink:href="b.xsd#dup" xlink:label="loc"/>
    <genlab:label xlink:type="resource" xlink:label="lab" xml:lang="en" xlink:role="http://www.xbrl.org/2003/role/label">Right generic label</genlab:label>
    <gen:arc xlink:type="arc" xlink:arcrole="http://xbrl.org/arcrole/2008/element-label" xlink:from="loc" xlink:to="lab"/>
  </gen:link>
</link:linkbase>""",
        encoding="utf-8",
    )

    wrong_qname = QName("http://example.com/a", "Wrong")
    right_qname = QName("http://example.com/b", "Right")

    result = parse_generic_label_linkbase(
        label_lb,
        {"dup": wrong_qname},
        ns_qualified_map={"http://example.com/b#dup": right_qname},
        schema_ns_map={str(schema_b.resolve()): "http://example.com/b"},
    )

    assert right_qname in result
    assert [label.text for label in result[right_qname]] == ["Right generic label"]
    assert wrong_qname not in result

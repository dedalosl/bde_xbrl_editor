from __future__ import annotations

from pathlib import Path

from lxml import etree

from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file


def test_parse_xml_file_uses_in_memory_bytes_parser(
    monkeypatch,
    tmp_path: Path,
) -> None:
    xml_path = tmp_path / "schema.xsd"
    xml_path.write_text(
        """<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="ok" type="xs:string"/>
</xs:schema>""",
        encoding="utf-8",
    )

    original_parse = etree.parse
    calls = {"count": 0}

    def flaky_parse(source, *args, **kwargs):
        calls["count"] += 1
        if isinstance(source, str):
            raise etree.XMLSyntaxError("Document is empty, line 1, column 1", 1, 0, 0)
        return original_parse(source, *args, **kwargs)

    monkeypatch.setattr(etree, "parse", flaky_parse)

    tree = parse_xml_file(xml_path)

    assert tree.getroot().tag == "{http://www.w3.org/2001/XMLSchema}schema"
    assert calls["count"] == 1


def test_parse_xml_file_repairs_malformed_prefixed_start_tag(tmp_path: Path) -> None:
    xml_path = tmp_path / "broken.xml"
    xml_path.write_text(
        """<root xmlns:df="http://example.com">
  < df:linkrole>value</df:linkrole>
</root>""",
        encoding="utf-8",
    )

    tree = parse_xml_file(xml_path)

    assert tree.getroot().tag == "root"

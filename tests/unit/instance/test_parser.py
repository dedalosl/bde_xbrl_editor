"""Unit tests for InstanceParser."""

from __future__ import annotations

import textwrap
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bde_xbrl_editor.instance.models import (
    InstanceParseError,
    TaxonomyResolutionError,
)
from bde_xbrl_editor.instance.parser import InstanceParser
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_NS = "http://example.com/xbrl/test"
_XBRLI_NS = "http://www.xbrl.org/2003/instance"

_ASSETS_QNAME = QName(namespace=_TEST_NS, local_name="Assets")
_ENTITY_NAME_QNAME = QName(namespace=_TEST_NS, local_name="EntityName")
_XBRLI_MONETARY = QName(namespace=_XBRLI_NS, local_name="monetaryItemType")
_XBRLI_STRING = QName(namespace=_XBRLI_NS, local_name="stringItemType")


def _make_taxonomy(concepts: dict | None = None) -> TaxonomyStructure:
    meta = TaxonomyMetadata(
        name="Test",
        version="1.0",
        publisher="Test",
        entry_point_path=Path("/tmp/entry.xsd"),
        loaded_at=datetime.now(),
        declared_languages=("en",),
    )
    if concepts is None:
        concepts = {
            _ASSETS_QNAME: Concept(
                qname=_ASSETS_QNAME,
                data_type=_XBRLI_MONETARY,
                period_type="instant",
                balance="debit",
            ),
            _ENTITY_NAME_QNAME: Concept(
                qname=_ENTITY_NAME_QNAME,
                data_type=_XBRLI_STRING,
                period_type="duration",
            ),
        }
    return TaxonomyStructure(
        metadata=meta,
        concepts=concepts,
        labels=MagicMock(),
        presentation={},
        calculation={},
        definition={},
        hypercubes=[],
        dimensions={},
        tables=[],
    )


def _make_parser(taxonomy: TaxonomyStructure | None = None) -> tuple[InstanceParser, MagicMock]:
    """Return (parser, mock_loader). Mock loader always returns the given taxonomy."""
    if taxonomy is None:
        taxonomy = _make_taxonomy()
    loader = MagicMock()
    loader.load.return_value = taxonomy
    parser = InstanceParser(taxonomy_loader=loader)
    return parser, loader


def _write_xbrl(tmp_path: Path, xml_body: str, schema_href: str = "entry.xsd") -> Path:
    """Write a minimal XBRL instance to a temp file."""
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<xbrli:xbrl'
        f' xmlns:xbrli="http://www.xbrl.org/2003/instance"'
        f' xmlns:link="http://www.xbrl.org/2003/linkbase"'
        f' xmlns:xlink="http://www.w3.org/1999/xlink"'
        f' xmlns:test="{_TEST_NS}"'
        f' xmlns:ef-find="http://www.eurofiling.info/xbrl/ext/filing-indicators">\n'
        f'  <link:schemaRef xlink:type="simple" xlink:href="{schema_href}"/>\n'
        f'{xml_body}\n'
        '</xbrli:xbrl>\n'
    )
    # create a dummy schema file so relative path resolution works
    (tmp_path / schema_href).write_text("<xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema'/>")
    p = tmp_path / "instance.xbrl"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Tests: well-formedness and root validation
# ---------------------------------------------------------------------------


def test_parse_error_on_bad_xml(tmp_path: Path) -> None:
    bad = tmp_path / "bad.xbrl"
    bad.write_text("this is not xml", encoding="utf-8")
    parser, _ = _make_parser()
    with pytest.raises(InstanceParseError):
        parser.load(bad)


def test_parse_error_on_wrong_root(tmp_path: Path) -> None:
    wrong = tmp_path / "wrong.xml"
    wrong.write_text(
        "<?xml version='1.0'?><root xmlns='http://example.com'/>",
        encoding="utf-8",
    )
    parser, _ = _make_parser()
    with pytest.raises(InstanceParseError, match="Root element must be xbrli:xbrl"):
        parser.load(wrong)


def test_parse_error_missing_schema_ref(tmp_path: Path) -> None:
    xml = tmp_path / "no_schema.xbrl"
    xml.write_text(
        textwrap.dedent("""\
            <?xml version='1.0'?>
            <xbrli:xbrl xmlns:xbrli='http://www.xbrl.org/2003/instance'/>
        """),
        encoding="utf-8",
    )
    parser, _ = _make_parser()
    with pytest.raises(InstanceParseError, match="Missing link:schemaRef"):
        parser.load(xml)


# ---------------------------------------------------------------------------
# Tests: taxonomy resolution
# ---------------------------------------------------------------------------


def test_taxonomy_resolution_error(tmp_path: Path) -> None:
    p = _write_xbrl(tmp_path, "", schema_href="missing.xsd")
    # Remove the stub schema so resolution fails
    (tmp_path / "missing.xsd").unlink()
    parser, _ = _make_parser()
    with pytest.raises(TaxonomyResolutionError):
        parser.load(p)


def test_manual_resolver_called_as_fallback(tmp_path: Path) -> None:
    p = _write_xbrl(tmp_path, "", schema_href="remote.xsd")
    (tmp_path / "remote.xsd").unlink()

    taxonomy = _make_taxonomy()
    loader = MagicMock()
    loader.load.return_value = taxonomy
    resolved_path = tmp_path / "local_schema.xsd"
    resolved_path.write_text("<xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema'/>")

    resolver = MagicMock(return_value=resolved_path)
    parser = InstanceParser(taxonomy_loader=loader, manual_taxonomy_resolver=resolver)
    instance, _ = parser.load(p)
    resolver.assert_called_once_with("remote.xsd")
    assert instance is not None


# ---------------------------------------------------------------------------
# Tests: context parsing
# ---------------------------------------------------------------------------


def test_parses_instant_context(tmp_path: Path) -> None:
    body = textwrap.dedent("""\
        <xbrli:context id="C1">
          <xbrli:entity>
            <xbrli:identifier scheme="http://bde.es">ES1234</xbrli:identifier>
          </xbrli:entity>
          <xbrli:period>
            <xbrli:instant>2023-12-31</xbrli:instant>
          </xbrli:period>
        </xbrli:context>
    """)
    p = _write_xbrl(tmp_path, body)
    parser, _ = _make_parser()
    instance, _ = parser.load(p)
    assert "C1" in instance.contexts
    ctx = instance.contexts["C1"]
    assert ctx.period.period_type == "instant"
    assert ctx.period.instant_date == date(2023, 12, 31)
    assert ctx.entity.identifier == "ES1234"
    assert ctx.entity.scheme == "http://bde.es"


def test_parses_duration_context(tmp_path: Path) -> None:
    body = textwrap.dedent("""\
        <xbrli:context id="D1">
          <xbrli:entity>
            <xbrli:identifier scheme="http://bde.es">ES9999</xbrli:identifier>
          </xbrli:entity>
          <xbrli:period>
            <xbrli:startDate>2023-01-01</xbrli:startDate>
            <xbrli:endDate>2023-12-31</xbrli:endDate>
          </xbrli:period>
        </xbrli:context>
    """)
    p = _write_xbrl(tmp_path, body)
    parser, _ = _make_parser()
    instance, _ = parser.load(p)
    ctx = instance.contexts["D1"]
    assert ctx.period.period_type == "duration"
    assert ctx.period.start_date == date(2023, 1, 1)
    assert ctx.period.end_date == date(2023, 12, 31)


# ---------------------------------------------------------------------------
# Tests: unit parsing
# ---------------------------------------------------------------------------


def test_parses_unit(tmp_path: Path) -> None:
    body = textwrap.dedent("""\
        <xbrli:context id="C1">
          <xbrli:entity>
            <xbrli:identifier scheme="http://bde.es">ES1</xbrli:identifier>
          </xbrli:entity>
          <xbrli:period><xbrli:instant>2023-12-31</xbrli:instant></xbrli:period>
        </xbrli:context>
        <xbrli:unit id="EUR">
          <xbrli:measure>iso4217:EUR</xbrli:measure>
        </xbrli:unit>
    """)
    p = _write_xbrl(tmp_path, body)
    parser, _ = _make_parser()
    instance, _ = parser.load(p)
    assert "EUR" in instance.units
    assert instance.units["EUR"].measure_uri == "iso4217:EUR"


# ---------------------------------------------------------------------------
# Tests: fact parsing
# ---------------------------------------------------------------------------


def test_parses_known_fact(tmp_path: Path) -> None:
    body = textwrap.dedent("""\
        <xbrli:context id="C1">
          <xbrli:entity>
            <xbrli:identifier scheme="http://bde.es">ES1</xbrli:identifier>
          </xbrli:entity>
          <xbrli:period><xbrli:instant>2023-12-31</xbrli:instant></xbrli:period>
        </xbrli:context>
        <xbrli:unit id="EUR">
          <xbrli:measure>iso4217:EUR</xbrli:measure>
        </xbrli:unit>
        <test:Assets contextRef="C1" unitRef="EUR" decimals="2">1000.00</test:Assets>
    """)
    p = _write_xbrl(tmp_path, body)
    parser, _ = _make_parser()
    instance, orphaned = parser.load(p)
    assert len(instance.facts) == 1
    assert len(orphaned) == 0
    fact = instance.facts[0]
    assert fact.concept == _ASSETS_QNAME
    assert fact.value == "1000.00"
    assert fact.unit_ref == "EUR"
    assert fact.decimals == "2"


def test_orphaned_fact_for_unknown_concept(tmp_path: Path) -> None:
    body = textwrap.dedent("""\
        <xbrli:context id="C1">
          <xbrli:entity>
            <xbrli:identifier scheme="http://bde.es">ES1</xbrli:identifier>
          </xbrli:entity>
          <xbrli:period><xbrli:instant>2023-12-31</xbrli:instant></xbrli:period>
        </xbrli:context>
        <test:UnknownConcept contextRef="C1">some value</test:UnknownConcept>
    """)
    p = _write_xbrl(tmp_path, body)
    parser, _ = _make_parser()
    instance, orphaned = parser.load(p)
    assert len(instance.facts) == 0
    assert len(orphaned) == 1
    assert orphaned[0].value == "some value"


# ---------------------------------------------------------------------------
# Tests: filing indicators
# ---------------------------------------------------------------------------


def test_parses_filing_indicator(tmp_path: Path) -> None:
    body = textwrap.dedent("""\
        <xbrli:context id="C1">
          <xbrli:entity>
            <xbrli:identifier scheme="http://bde.es">ES1</xbrli:identifier>
          </xbrli:entity>
          <xbrli:period><xbrli:instant>2023-12-31</xbrli:instant></xbrli:period>
        </xbrli:context>
        <ef-find:fIndicators>
          <ef-find:filingIndicator contextRef="C1" filed="true">T1</ef-find:filingIndicator>
          <ef-find:filingIndicator contextRef="C1" filed="false">T2</ef-find:filingIndicator>
        </ef-find:fIndicators>
    """)
    p = _write_xbrl(tmp_path, body)
    parser, _ = _make_parser()
    instance, _ = parser.load(p)
    assert len(instance.filing_indicators) == 2
    fi_map = {fi.template_id: fi for fi in instance.filing_indicators}
    assert fi_map["T1"].filed is True
    assert fi_map["T2"].filed is False


# ---------------------------------------------------------------------------
# Tests: _dirty and source_path
# ---------------------------------------------------------------------------


def test_dirty_is_false_after_load(tmp_path: Path) -> None:
    p = _write_xbrl(tmp_path, "")
    parser, _ = _make_parser()
    instance, _ = parser.load(p)
    assert instance._dirty is False  # noqa: SLF001


def test_source_path_set_after_load(tmp_path: Path) -> None:
    p = _write_xbrl(tmp_path, "")
    parser, _ = _make_parser()
    instance, _ = parser.load(p)
    assert instance.source_path == p

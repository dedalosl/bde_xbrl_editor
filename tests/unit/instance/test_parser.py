"""Unit tests for InstanceParser."""

from __future__ import annotations

import textwrap
from datetime import date, datetime
from pathlib import Path
from unittest.mock import ANY, MagicMock

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
from bde_xbrl_editor.taxonomy.settings import LoaderSettings

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
    loader.settings = LoaderSettings()
    parser = InstanceParser(taxonomy_loader=loader)
    return parser, loader


_BDE_PBLO_NS = "http://www.bde.es/es/fr/esrs/comun/2008-06-01/preambulo"
_BDE_DIM_NS = "http://www.bde.es/es/fr/esrs/comun/2008-06-01/dimensiones"


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


def _write_bde_xbrl(tmp_path: Path, xml_body: str, schema_href: str = "entry.xsd") -> Path:
    """Write a BDE IE_2008_02 XBRL instance with the BDE-specific namespaces declared."""
    content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<xbrli:xbrl'
        f' xmlns:xbrli="http://www.xbrl.org/2003/instance"'
        f' xmlns:link="http://www.xbrl.org/2003/linkbase"'
        f' xmlns:xlink="http://www.w3.org/1999/xlink"'
        f' xmlns:xbrldi="http://xbrl.org/2006/xbrldi"'
        f' xmlns:test="{_TEST_NS}"'
        f' xmlns:ef-find="http://www.eurofiling.info/xbrl/ext/filing-indicators"'
        f' xmlns:es-be-cm-pblo="{_BDE_PBLO_NS}"'
        f' xmlns:es-be-cm-dim="{_BDE_DIM_NS}">\n'
        f'  <link:schemaRef xlink:type="simple" xlink:href="{schema_href}"/>\n'
        f'{xml_body}\n'
        '</xbrli:xbrl>\n'
    )
    (tmp_path / schema_href).write_text("<xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema'/>")
    p = tmp_path / "bde_instance.xbrl"
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


def test_parser_preserves_typed_dimension_value_and_element(tmp_path: Path) -> None:
    parser, _ = _make_parser()
    xbrl = _write_xbrl(
        tmp_path,
        """
  <xbrli:context id="ctx1">
    <xbrli:entity><xbrli:identifier scheme="http://example.com/entity">E1</xbrli:identifier></xbrli:entity>
    <xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>
    <xbrli:scenario xmlns:xbrldi="http://xbrl.org/2006/xbrldi" xmlns:dim="http://example.com/dim" xmlns:dom="http://example.com/dom">
      <xbrldi:typedMember dimension="dim:qLIN"><dom:qLE>Entidad A</dom:qLE></xbrldi:typedMember>
    </xbrli:scenario>
  </xbrli:context>
        """,
    )

    instance, _ = parser.load(xbrl)
    ctx = instance.contexts["ctx1"]
    dim_qname = QName(namespace="http://example.com/dim", local_name="qLIN", prefix="dim")
    assert ctx.dimensions[dim_qname] == dim_qname
    assert ctx.typed_dimensions[dim_qname] == "Entidad A"
    assert ctx.typed_dimension_elements[dim_qname] == QName(namespace="http://example.com/dom", local_name="qLE")


def test_local_catalog_resolves_bde_fr_schema_ref_to_cache_path(tmp_path: Path) -> None:
    schema_href = "http://www.bde.es/es/fr/xbrl/fws/test/entry.xsd"
    (tmp_path / Path(schema_href)).parent.mkdir(parents=True, exist_ok=True)
    p = _write_xbrl(tmp_path, "", schema_href=schema_href)
    # Remove the stub written next to the instance so only the catalog path can resolve it.
    (tmp_path / schema_href).unlink()

    taxonomy = _make_taxonomy()
    loader = MagicMock()
    loader.load.return_value = taxonomy
    cache_root = tmp_path / "cache"
    resolved_path = cache_root / "es" / "xbrl" / "fws" / "test" / "entry.xsd"
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_path.write_text("<xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema'/>")
    loader.settings = LoaderSettings(local_catalog={"http://www.bde.es/": cache_root})

    parser = InstanceParser(taxonomy_loader=loader)
    instance, _ = parser.load(p)

    loader.load.assert_called_once_with(resolved_path.resolve(), progress_callback=ANY)
    assert instance is not None


def test_reuses_matching_preloaded_taxonomy(tmp_path: Path) -> None:
    p = _write_xbrl(tmp_path, "")
    taxonomy = _make_taxonomy()
    taxonomy = TaxonomyStructure(
        metadata=TaxonomyMetadata(
            name=taxonomy.metadata.name,
            version=taxonomy.metadata.version,
            publisher=taxonomy.metadata.publisher,
            entry_point_path=(tmp_path / "entry.xsd").resolve(),
            loaded_at=taxonomy.metadata.loaded_at,
            declared_languages=taxonomy.metadata.declared_languages,
        ),
        concepts=taxonomy.concepts,
        labels=taxonomy.labels,
        presentation=taxonomy.presentation,
        calculation=taxonomy.calculation,
        definition=taxonomy.definition,
        hypercubes=taxonomy.hypercubes,
        dimensions=taxonomy.dimensions,
        tables=taxonomy.tables,
        formula_linkbase_path=taxonomy.formula_linkbase_path,
        formula_assertion_set=taxonomy.formula_assertion_set,
        schema_files=taxonomy.schema_files,
        linkbase_files=taxonomy.linkbase_files,
    )

    parser, loader = _make_parser(taxonomy)
    resolved = []

    instance, _ = parser.load(
        p,
        taxonomy_resolved_callback=resolved.append,
        preloaded_taxonomy=taxonomy,
    )

    loader.load.assert_not_called()
    assert resolved == [taxonomy]
    assert instance.taxonomy_entry_point == taxonomy.metadata.entry_point_path


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


def test_bde_estados_reportados_become_filing_indicators(tmp_path: Path) -> None:
    body = textwrap.dedent("""\
        <xbrli:context id="cBasico">
          <xbrli:entity>
            <xbrli:identifier scheme="http://www.ecb.int/stats/money/mfi">ES9000</xbrli:identifier>
          </xbrli:entity>
          <xbrli:period><xbrli:instant>2024-01-31</xbrli:instant></xbrli:period>
        </xbrli:context>
        <es-be-cm-pblo:EstadosReportados>
          <es-be-cm-pblo:CodigoEstado contextRef="cBasico">3201</es-be-cm-pblo:CodigoEstado>
          <es-be-cm-pblo:CodigoEstado contextRef="cBasico"
            es-be-cm-pblo:blanco="true">3251</es-be-cm-pblo:CodigoEstado>
        </es-be-cm-pblo:EstadosReportados>
    """)
    p = _write_bde_xbrl(tmp_path, body)
    parser, _ = _make_parser()
    instance, _ = parser.load(p)

    fi_map = {fi.template_id: fi for fi in instance.filing_indicators}
    assert fi_map["3201"].filed is True
    assert fi_map["3251"].filed is False
    assert instance.included_table_ids == ["3201"]


def test_bde_filing_indicators_take_precedence_over_eurofiling_wrapper(tmp_path: Path) -> None:
    body = textwrap.dedent("""\
        <xbrli:context id="cBasico">
          <xbrli:entity>
            <xbrli:identifier scheme="http://www.ecb.int/stats/money/mfi">ES9000</xbrli:identifier>
          </xbrli:entity>
          <xbrli:period><xbrli:instant>2024-01-31</xbrli:instant></xbrli:period>
        </xbrli:context>
        <es-be-cm-pblo:EstadosReportados>
          <es-be-cm-pblo:CodigoEstado contextRef="cBasico">3201</es-be-cm-pblo:CodigoEstado>
        </es-be-cm-pblo:EstadosReportados>
        <ef-find:fIndicators>
          <ef-find:filingIndicator contextRef="cBasico" filed="true">T1</ef-find:filingIndicator>
        </ef-find:fIndicators>
    """)
    p = _write_bde_xbrl(tmp_path, body)
    parser, _ = _make_parser()
    instance, _ = parser.load(p)

    assert [fi.template_id for fi in instance.filing_indicators] == ["3201"]


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


# ---------------------------------------------------------------------------
# Tests: BDE IE_2008_02 preamble parsing
# ---------------------------------------------------------------------------


def test_bde_preambulo_none_for_non_bde_instance(tmp_path: Path) -> None:
    """bde_preambulo is None when no es-be-cm-pblo elements are present."""
    p = _write_xbrl(tmp_path, "")
    parser, _ = _make_parser()
    instance, _ = parser.load(p)
    assert instance.bde_preambulo is None


def test_bde_preambulo_parses_entidad_and_tipo_envio(tmp_path: Path) -> None:
    """EntidadPresentadora and TipoEnvio are extracted into BdePreambulo."""
    body = textwrap.dedent("""\
        <xbrli:context id="cBasico">
          <xbrli:entity>
            <xbrli:identifier scheme="http://www.ecb.int/stats/money/mfi">ES9000</xbrli:identifier>
          </xbrli:entity>
          <xbrli:period><xbrli:instant>2024-01-31</xbrli:instant></xbrli:period>
        </xbrli:context>
        <es-be-cm-pblo:EntidadPresentadora contextRef="cBasico">9000</es-be-cm-pblo:EntidadPresentadora>
        <es-be-cm-pblo:TipoEnvio contextRef="cBasico">Ordinario</es-be-cm-pblo:TipoEnvio>
    """)
    p = _write_bde_xbrl(tmp_path, body)
    parser, _ = _make_parser()
    instance, _ = parser.load(p)
    assert instance.bde_preambulo is not None
    assert instance.bde_preambulo.entidad_presentadora == "9000"
    assert instance.bde_preambulo.tipo_envio == "Ordinario"
    assert instance.bde_preambulo.context_ref == "cBasico"


def test_bde_preambulo_parses_estados_reportados(tmp_path: Path) -> None:
    """CodigoEstado elements inside EstadosReportados are parsed into BdeEstadoReportado."""
    body = textwrap.dedent("""\
        <xbrli:context id="cBasico">
          <xbrli:entity>
            <xbrli:identifier scheme="http://www.ecb.int/stats/money/mfi">ES9000</xbrli:identifier>
          </xbrli:entity>
          <xbrli:period><xbrli:instant>2024-01-31</xbrli:instant></xbrli:period>
        </xbrli:context>
        <es-be-cm-pblo:EntidadPresentadora contextRef="cBasico">9000</es-be-cm-pblo:EntidadPresentadora>
        <es-be-cm-pblo:TipoEnvio contextRef="cBasico">Sustitutivo</es-be-cm-pblo:TipoEnvio>
        <es-be-cm-pblo:EstadosReportados>
          <es-be-cm-pblo:CodigoEstado contextRef="cBasico">3201</es-be-cm-pblo:CodigoEstado>
          <es-be-cm-pblo:CodigoEstado contextRef="cBasico">3202</es-be-cm-pblo:CodigoEstado>
        </es-be-cm-pblo:EstadosReportados>
    """)
    p = _write_bde_xbrl(tmp_path, body)
    parser, _ = _make_parser()
    instance, _ = parser.load(p)
    assert instance.bde_preambulo is not None
    estados = instance.bde_preambulo.estados_reportados
    assert len(estados) == 2
    assert estados[0].codigo == "3201"
    assert estados[0].blanco is False
    assert estados[1].codigo == "3202"
    assert estados[1].blanco is False


def test_bde_preambulo_parses_blanco_estado(tmp_path: Path) -> None:
    """CodigoEstado with es-be-cm-pblo:blanco='true' sets blanco=True."""
    body = textwrap.dedent(f"""\
        <xbrli:context id="cBasico">
          <xbrli:entity>
            <xbrli:identifier scheme="http://www.ecb.int/stats/money/mfi">ES9000</xbrli:identifier>
          </xbrli:entity>
          <xbrli:period><xbrli:instant>2024-01-31</xbrli:instant></xbrli:period>
        </xbrli:context>
        <es-be-cm-pblo:EntidadPresentadora contextRef="cBasico">9000</es-be-cm-pblo:EntidadPresentadora>
        <es-be-cm-pblo:EstadosReportados>
          <es-be-cm-pblo:CodigoEstado contextRef="cBasico">3201</es-be-cm-pblo:CodigoEstado>
          <es-be-cm-pblo:CodigoEstado contextRef="cBasico"
            es-be-cm-pblo:blanco="true">3251</es-be-cm-pblo:CodigoEstado>
        </es-be-cm-pblo:EstadosReportados>
    """)
    p = _write_bde_xbrl(tmp_path, body)
    parser, _ = _make_parser()
    instance, _ = parser.load(p)
    assert instance.bde_preambulo is not None
    estados = instance.bde_preambulo.estados_reportados
    assert len(estados) == 2
    assert estados[0].blanco is False
    assert estados[1].codigo == "3251"
    assert estados[1].blanco is True


def test_bde_preambulo_elements_not_parsed_as_facts(tmp_path: Path) -> None:
    """Preamble elements in es-be-cm-pblo namespace are excluded from facts and orphaned_facts."""
    body = textwrap.dedent("""\
        <xbrli:context id="cBasico">
          <xbrli:entity>
            <xbrli:identifier scheme="http://www.ecb.int/stats/money/mfi">ES9000</xbrli:identifier>
          </xbrli:entity>
          <xbrli:period><xbrli:instant>2024-01-31</xbrli:instant></xbrli:period>
        </xbrli:context>
        <es-be-cm-pblo:EntidadPresentadora contextRef="cBasico">9000</es-be-cm-pblo:EntidadPresentadora>
        <es-be-cm-pblo:TipoEnvio contextRef="cBasico">Ordinario</es-be-cm-pblo:TipoEnvio>
        <es-be-cm-pblo:EstadosReportados>
          <es-be-cm-pblo:CodigoEstado contextRef="cBasico">3201</es-be-cm-pblo:CodigoEstado>
        </es-be-cm-pblo:EstadosReportados>
    """)
    p = _write_bde_xbrl(tmp_path, body)
    parser, _ = _make_parser()
    instance, orphaned = parser.load(p)
    assert len(instance.facts) == 0
    assert len(orphaned) == 0


def test_bde_segment_agrupacion_parsed_as_dimension(tmp_path: Path) -> None:
    """The Agrupacion dimension in xbrli:segment is parsed as a proper XBRL dimension."""
    body = textwrap.dedent("""\
        <xbrli:context id="ctx1">
          <xbrli:entity>
            <xbrli:identifier scheme="http://www.ecb.int/stats/money/mfi">ES9000</xbrli:identifier>
            <xbrli:segment>
              <xbrldi:explicitMember dimension="es-be-cm-dim:Agrupacion">
                es-be-cm-dim:AgrupacionIndividual
              </xbrldi:explicitMember>
            </xbrli:segment>
          </xbrli:entity>
          <xbrli:period><xbrli:instant>2024-01-31</xbrli:instant></xbrli:period>
        </xbrli:context>
    """)
    p = _write_bde_xbrl(tmp_path, body)
    parser, _ = _make_parser()
    instance, _ = parser.load(p)
    ctx = instance.contexts.get("ctx1")
    assert ctx is not None
    assert ctx.context_element == "segment"
    # Agrupacion must appear as a proper XBRL dimension, not as arbitrary content
    dim_keys = [str(k) for k in ctx.dimensions]
    assert any("Agrupacion" in k for k in dim_keys), (
        f"Agrupacion dimension not found in context dimensions: {dim_keys}"
    )
    mem_vals = [str(v) for v in ctx.dimensions.values()]
    assert any("AgrupacionIndividual" in v for v in mem_vals)


def test_fact_loading_reports_incremental_progress(tmp_path: Path) -> None:
    context = textwrap.dedent("""\
        <xbrli:context id="C1">
          <xbrli:entity>
            <xbrli:identifier scheme="http://bde.es">ES1234</xbrli:identifier>
          </xbrli:entity>
          <xbrli:period>
            <xbrli:instant>2023-12-31</xbrli:instant>
          </xbrli:period>
        </xbrli:context>
    """)
    facts = "\n".join(
        f'<test:Assets contextRef="C1">{100 + index}</test:Assets>'
        for index in range(60)
    )
    p = _write_xbrl(tmp_path, f"{context}\n{facts}")
    parser, _ = _make_parser()

    progress_events: list[tuple[str, int, int]] = []
    parser.load(p, progress_callback=lambda message, current, total: progress_events.append((message, current, total)))

    fact_updates = [event for event in progress_events if event[0].startswith("Reading facts…")]
    metadata_updates = [
        event for event in progress_events if event[0].startswith("Reading filing metadata…")
    ]
    final_indexed = [event for event in progress_events if event[0].startswith("Facts indexed —")]

    assert len(metadata_updates) >= 1
    assert metadata_updates[0][0] == "Reading filing metadata… 0/62"
    assert len(fact_updates) > 3
    assert fact_updates[0][0] == "Reading facts… 1 parsed"
    assert final_indexed[-1][0] == "Facts indexed — 60 resolved, 0 orphaned"

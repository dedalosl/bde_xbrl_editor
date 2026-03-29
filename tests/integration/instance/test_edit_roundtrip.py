"""Integration tests for parse → edit → save round-trip."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from bde_xbrl_editor.instance.models import (
    Fact,
)
from bde_xbrl_editor.instance.parser import InstanceParser
from bde_xbrl_editor.instance.serializer import InstanceSerializer
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_XBRLI_NS = "http://www.xbrl.org/2003/instance"
_TEST_NS = "http://example.com/xbrl/test"

_ASSETS_QNAME = QName(namespace=_TEST_NS, local_name="Assets")
_LIABILITIES_QNAME = QName(namespace=_TEST_NS, local_name="Liabilities")
_XBRLI_MONETARY = QName(namespace=_XBRLI_NS, local_name="monetaryItemType")


def _make_taxonomy() -> TaxonomyStructure:
    meta = TaxonomyMetadata(
        name="Test",
        version="1.0",
        publisher="Test",
        entry_point_path=Path("/tmp/entry.xsd"),
        loaded_at=datetime.now(),
        declared_languages=("en",),
    )
    concepts = {
        _ASSETS_QNAME: Concept(
            qname=_ASSETS_QNAME,
            data_type=_XBRLI_MONETARY,
            period_type="instant",
            balance="debit",
        ),
        _LIABILITIES_QNAME: Concept(
            qname=_LIABILITIES_QNAME,
            data_type=_XBRLI_MONETARY,
            period_type="instant",
            balance="credit",
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


def _write_instance(tmp_path: Path, extra_body: str = "") -> Path:
    """Write a minimal XBRL instance file."""
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<xbrli:xbrl'
        f' xmlns:xbrli="{_XBRLI_NS}"'
        ' xmlns:link="http://www.xbrl.org/2003/linkbase"'
        ' xmlns:xlink="http://www.w3.org/1999/xlink"'
        f' xmlns:test="{_TEST_NS}">\n'
        '  <link:schemaRef xlink:type="simple" xlink:href="entry.xsd"/>\n'
        '  <xbrli:context id="C1">\n'
        '    <xbrli:entity>\n'
        '      <xbrli:identifier scheme="http://bde.es">ES1</xbrli:identifier>\n'
        '    </xbrli:entity>\n'
        '    <xbrli:period><xbrli:instant>2023-12-31</xbrli:instant></xbrli:period>\n'
        '  </xbrli:context>\n'
        '  <xbrli:unit id="EUR"><xbrli:measure>iso4217:EUR</xbrli:measure></xbrli:unit>\n'
        '  <test:Assets contextRef="C1" unitRef="EUR" decimals="2">1000.00</test:Assets>\n'
        f'{extra_body}\n'
        '</xbrli:xbrl>\n'
    )
    p = tmp_path / "instance.xbrl"
    p.write_text(body, encoding="utf-8")
    # create stub schema
    (tmp_path / "entry.xsd").write_text(
        "<xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema'/>",
    )
    return p


def _make_parser(taxonomy: TaxonomyStructure) -> InstanceParser:
    loader = MagicMock()
    loader.load.return_value = taxonomy
    return InstanceParser(taxonomy_loader=loader)


# ---------------------------------------------------------------------------
# Round-trip: parse → edit → save → parse
# ---------------------------------------------------------------------------


def test_edit_fact_survives_roundtrip(tmp_path: Path) -> None:
    taxonomy = _make_taxonomy()
    p = _write_instance(tmp_path)
    parser = _make_parser(taxonomy)

    instance, _ = parser.load(p)
    assert instance.facts[0].value == "1000.00"

    # Edit the fact
    instance.update_fact(0, "2000.00")

    # Save to new file
    saved_path = tmp_path / "saved.xbrl"
    serializer = InstanceSerializer()
    serializer.save(instance, saved_path)

    # Parse saved file
    instance2, _ = parser.load(saved_path)
    assert len(instance2.facts) == 1
    assert instance2.facts[0].value == "2000.00"
    assert instance2._dirty is False  # noqa: SLF001


def test_orphaned_facts_preserved_in_roundtrip(tmp_path: Path) -> None:
    taxonomy = _make_taxonomy()
    # Add an unknown concept as extra body
    extra = '  <test:UnknownConcept contextRef="C1">orphan-value</test:UnknownConcept>'
    p = _write_instance(tmp_path, extra_body=extra)
    parser = _make_parser(taxonomy)

    instance, orphaned = parser.load(p)
    assert len(orphaned) == 1
    assert orphaned[0].value == "orphan-value"

    # Save
    saved_path = tmp_path / "saved_orphan.xbrl"
    serializer = InstanceSerializer()
    serializer.save(instance, saved_path)

    # Parse saved file — orphan should be present
    instance2, orphaned2 = parser.load(saved_path)
    assert len(orphaned2) == 1
    assert orphaned2[0].value == "orphan-value"


def test_decimal_precision_preserved(tmp_path: Path) -> None:
    taxonomy = _make_taxonomy()
    p = _write_instance(tmp_path)
    parser = _make_parser(taxonomy)
    instance, _ = parser.load(p)

    # Original decimals attribute preserved
    assert instance.facts[0].decimals == "2"

    saved_path = tmp_path / "precision.xbrl"
    InstanceSerializer().save(instance, saved_path)

    instance2, _ = parser.load(saved_path)
    assert instance2.facts[0].decimals == "2"


def test_multiple_edits_all_survive(tmp_path: Path) -> None:
    taxonomy = _make_taxonomy()
    p = _write_instance(tmp_path)
    parser = _make_parser(taxonomy)
    instance, _ = parser.load(p)

    # Add a second fact manually
    instance.facts.append(
        Fact(
            concept=_LIABILITIES_QNAME,
            context_ref="C1",
            unit_ref="EUR",
            value="500.00",
            decimals="2",
        )
    )
    instance.update_fact(0, "3000.00")

    saved_path = tmp_path / "multi.xbrl"
    InstanceSerializer().save(instance, saved_path)

    instance2, _ = parser.load(saved_path)
    assert len(instance2.facts) == 2
    fact_map = {f.concept: f for f in instance2.facts}
    assert fact_map[_ASSETS_QNAME].value == "3000.00"
    assert fact_map[_LIABILITIES_QNAME].value == "500.00"

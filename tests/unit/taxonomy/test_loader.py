"""Unit tests for taxonomy loader helper behavior."""

from __future__ import annotations

from pathlib import Path

from bde_xbrl_editor.taxonomy.loader import _classify_linkbases, _schema_parse_workers


def test_classify_linkbases_preserves_order_within_each_type() -> None:
    linkbases = [
        Path("/tmp/labels.xml"),
        Path("/tmp/presentation.xml"),
        Path("/tmp/calc.xml"),
        Path("/tmp/definition.xml"),
        Path("/tmp/labels-gen.xml"),
        Path("/tmp/rendering-rend.xml"),
        Path("/tmp/formula/formula.xml"),
    ]

    classified = _classify_linkbases(linkbases)

    assert classified["label"] == [Path("/tmp/labels.xml")]
    assert classified["pres"] == [Path("/tmp/presentation.xml")]
    assert classified["calc"] == [Path("/tmp/calc.xml")]
    assert classified["def"] == [Path("/tmp/definition.xml")]
    assert classified["generic"] == [Path("/tmp/labels-gen.xml")]
    assert classified["table"] == [Path("/tmp/rendering-rend.xml")]
    assert classified["formula"] == [Path("/tmp/formula/formula.xml")]


def test_schema_parse_workers_is_bounded() -> None:
    assert _schema_parse_workers(0) == 1
    assert _schema_parse_workers(1) == 1
    assert 1 <= _schema_parse_workers(50) <= 8

"""Unit tests for taxonomy loader helper behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from bde_xbrl_editor.taxonomy.loader import (
    _classify_linkbases,
    _run_path_jobs,
    _schema_parse_workers,
)
from bde_xbrl_editor.taxonomy.models import TaxonomyParseError


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


def test_run_path_jobs_preserves_input_order_when_parallel() -> None:
    paths = [Path("/tmp/b"), Path("/tmp/a"), Path("/tmp/c")]

    results = _run_path_jobs(
        paths,
        lambda path: path.name.upper(),
        workers=3,
    )

    assert results == [
        (Path("/tmp/b"), "B"),
        (Path("/tmp/a"), "A"),
        (Path("/tmp/c"), "C"),
    ]


def test_run_path_jobs_wraps_unexpected_exceptions() -> None:
    with pytest.raises(TaxonomyParseError, match="boom") as exc_info:
        _run_path_jobs(
            [Path("/tmp/fail.xml")],
            lambda _path: (_ for _ in ()).throw(RuntimeError("boom")),
            workers=1,
        )

    assert exc_info.value.file_path == "/tmp/fail.xml"

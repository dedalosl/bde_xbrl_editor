"""Unit tests for taxonomy loader helper behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from bde_xbrl_editor.taxonomy.linkbases.formula import (
    linkbase_contains_formula_assertions,
    parse_assertion_table_mappings,
    parse_formula_linkbase,
)
from bde_xbrl_editor.taxonomy.linkbases.presentation import PresentationLinkbaseParseResult
from bde_xbrl_editor.taxonomy.loader import (
    _build_group_table_order,
    _classify_linkbases,
    _find_companion_tab_presentation_linkbases,
    _preferred_group_table_results,
    _run_path_jobs,
    _schema_parse_workers,
    _sniff_linkbase_type,
)
from bde_xbrl_editor.taxonomy.models import TaxonomyParseError


def test_sniff_linkbase_calculation_stem_does_not_use_formula_bucket() -> None:
    """Filename heuristics no longer expose a ``formula`` bucket — only structural detection."""
    assert _sniff_linkbase_type(Path("/dts/my-formula-calculation.xml")) == "calc"


def test_sniff_linkbase_pre_stem_is_treated_as_presentation() -> None:
    assert _sniff_linkbase_type(Path("/dts/tab-pre.xml")) == "pres"
    assert _sniff_linkbase_type(Path("/dts/mod-pre.xml")) == "pres"


def test_linkbase_contains_formula_assertions_detects_validation_assertion_set(
    tmp_path: Path,
) -> None:
    """Generic linkbase with ``validation:assertionSet`` (XBRL Formula / Validation packaging)."""
    lb = tmp_path / "arbitrary-name.xml"
    lb.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
  xmlns:gen="http://xbrl.org/2008/generic"
  xmlns:validation="http://xbrl.org/2008/validation"
  xmlns:xlink="http://www.w3.org/1999/xlink">
  <gen:link xlink:type="extended" xlink:role="http://www.xbrl.org/2008/role/link">
    <validation:assertionSet xlink:type="resource" xlink:label="aset" id="set1"/>
  </gen:link>
</link:linkbase>
""",
        encoding="utf-8",
    )
    assert linkbase_contains_formula_assertions(lb) is True


def test_linkbase_contains_formula_assertions_detects_assertion_sets_2_0_pwd(
    tmp_path: Path,
) -> None:
    """Assertion Sets 2.0 PWD — Table 1 ``as`` namespace (assertionSet resource)."""
    lb = tmp_path / "assertion-sets-packaging.xml"
    lb.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
  xmlns:gen="http://xbrl.org/2008/generic"
  xmlns:as="http://xbrl.org/PWD/2017-05-04/assertion-sets-2.0"
  xmlns:xlink="http://www.w3.org/1999/xlink">
  <gen:link xlink:type="extended" xlink:role="http://www.xbrl.org/2008/role/link">
    <as:assertionSet name="eg:Example" xlink:type="resource" xlink:label="s1"/>
  </gen:link>
</link:linkbase>
""",
        encoding="utf-8",
    )
    assert linkbase_contains_formula_assertions(lb) is True


def test_linkbase_contains_formula_assertions_finds_assertion_after_many_nodes(
    tmp_path: Path,
) -> None:
    """Tag-filtered iterparse must not miss assertions buried after many other elements."""
    lb = tmp_path / "heavy-preamble.xml"
    locs = "\n".join(f'  <link:loc xlink:type="locator" xlink:href="x.xsd#c{i}" xlink:label="l{i}"/>' for i in range(4000))
    lb.write_text(
        f'''<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
  xmlns:gen="http://xbrl.org/2008/generic"
  xmlns:va="http://xbrl.org/2008/assertion/value"
  xmlns:xlink="http://www.w3.org/1999/xlink">
  <gen:link xlink:type="extended" xlink:role="http://www.xbrl.org/2008/role/link">
{locs}
    <va:valueAssertion xlink:type="resource" xlink:label="a1" id="a1" test="true()"/>
  </gen:link>
</link:linkbase>
''',
        encoding="utf-8",
    )
    assert linkbase_contains_formula_assertions(lb) is True


def test_parse_value_assertion_uses_xlink_label_when_id_absent(tmp_path: Path) -> None:
    lb = tmp_path / "label-only-assertion.xml"
    lb.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
  xmlns:gen="http://xbrl.org/2008/generic"
  xmlns:va="http://xbrl.org/2008/assertion/value"
  xmlns:xlink="http://www.w3.org/1999/xlink">
  <gen:link xlink:type="extended" xlink:role="http://www.xbrl.org/2008/role/link">
    <va:valueAssertion xlink:type="resource" xlink:label="rule-A" test="true()"/>
  </gen:link>
</link:linkbase>
""",
        encoding="utf-8",
    )
    fas = parse_formula_linkbase(lb)
    assert len(fas.assertions) == 1
    assert fas.assertions[0].assertion_id == "rule-A"


def test_parse_assertion_table_mappings_resolves_applies_to_table(tmp_path: Path) -> None:
    lb = tmp_path / "assertion-set.xml"
    lb.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
  xmlns:gen="http://xbrl.org/2008/generic"
  xmlns:validation="http://xbrl.org/2008/validation"
  xmlns:xlink="http://www.w3.org/1999/xlink">
  <gen:link xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">
    <validation:assertionSet xlink:type="resource" xlink:label="assertionSet" id="assertionSet1"/>
    <link:loc xlink:type="locator" xlink:href="../../tab/fi_40-1-rend.xml#es_tFI_40-1" xlink:label="table_loc"/>
    <link:loc xlink:type="locator" xlink:href="vr-v4019_a.xml#es_v4019_a" xlink:label="assertion_loc"/>
    <gen:arc xlink:type="arc"
      xlink:arcrole="http://www.eurofiling.info/xbrl/arcrole/applies-to-table"
      xlink:from="assertionSet"
      xlink:to="table_loc"/>
    <gen:arc xlink:type="arc"
      xlink:arcrole="http://xbrl.org/arcrole/2008/assertion-set"
      xlink:from="assertionSet"
      xlink:to="assertion_loc"/>
  </gen:link>
</link:linkbase>
""",
        encoding="utf-8",
    )

    assert parse_assertion_table_mappings(lb) == {"es_v4019_a": "es_tFI_40-1"}


def test_linkbase_contains_formula_assertions_detects_value_assertion(tmp_path: Path) -> None:
    lb = tmp_path / "nested-packaging.xml"
    lb.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase"
  xmlns:gen="http://xbrl.org/2008/generic"
  xmlns:va="http://xbrl.org/2008/assertion/value"
  xmlns:xlink="http://www.w3.org/1999/xlink">
  <gen:link xlink:type="extended" xlink:role="http://www.xbrl.org/2008/role/link">
    <va:valueAssertion xlink:type="resource" xlink:label="v1" id="a1" test="true()"/>
  </gen:link>
</link:linkbase>
""",
        encoding="utf-8",
    )
    assert linkbase_contains_formula_assertions(lb) is True


def test_classify_linkbases_preserves_order_within_each_type() -> None:
    linkbases = [
        Path("/tmp/labels.xml"),
        Path("/tmp/presentation.xml"),
        Path("/tmp/calc.xml"),
        Path("/tmp/definition.xml"),
        Path("/tmp/labels-gen.xml"),
        Path("/tmp/rendering-rend.xml"),
        Path("/tmp/formula/value-assertions.xml"),
    ]

    classified = _classify_linkbases(linkbases)

    assert classified["label"] == [Path("/tmp/labels.xml")]
    assert classified["pres"] == [Path("/tmp/presentation.xml")]
    assert classified["calc"] == [Path("/tmp/calc.xml")]
    assert classified["def"] == [Path("/tmp/definition.xml")]
    assert classified["generic"] == [Path("/tmp/labels-gen.xml")]
    assert classified["table"] == [Path("/tmp/rendering-rend.xml")]
    assert classified["unknown"] == [Path("/tmp/formula/value-assertions.xml")]


def test_build_group_table_order_uses_arc_order_depth_first() -> None:
    result = PresentationLinkbaseParseResult(
        networks={},
        group_table_children={
            "group-root": [(2.0, "table_b"), (1.0, "table_a"), (3.0, "table_c")],
            "table_b": [(1.0, "table_b_child")],
        },
        group_table_rend_fragments={"table_a", "table_b", "table_b_child", "table_c"},
        group_table_root_fragment="group-root",
    )

    assert _build_group_table_order([result]) == {
        "table_a": 0,
        "table_b": 1,
        "table_b_child": 2,
        "table_c": 3,
    }


def test_build_group_table_order_traverses_multiple_roots_in_discovery_order() -> None:
    first = PresentationLinkbaseParseResult(
        networks={},
        group_table_children={"group-a": [(2.0, "table_a2"), (1.0, "table_a1")]},
        group_table_rend_fragments={"table_a1", "table_a2"},
        group_table_root_fragment="group-a",
    )
    second = PresentationLinkbaseParseResult(
        networks={},
        group_table_children={"group-b": [(1.0, "table_b1")]},
        group_table_rend_fragments={"table_b1"},
        group_table_root_fragment="group-b",
    )

    assert _build_group_table_order([first, second]) == {
        "table_a1": 0,
        "table_a2": 1,
        "table_b1": 2,
    }


def test_preferred_group_table_results_prefers_tab_directory() -> None:
    mod_result = PresentationLinkbaseParseResult(
        networks={},
        group_table_children={"mod-root": [(1.0, "mod-table")]},
        group_table_rend_fragments={"mod-table"},
        group_table_root_fragment="mod-root",
    )
    tab_result = PresentationLinkbaseParseResult(
        networks={},
        group_table_children={"tab-root": [(1.0, "tab-table")]},
        group_table_rend_fragments={"tab-table"},
        group_table_root_fragment="tab-root",
    )

    selected = _preferred_group_table_results([
        (Path("/tmp/mod/finrep_ind-pre.xml"), mod_result),
        (Path("/tmp/tab/tab-pre.xml"), tab_result),
    ])

    assert selected == [tab_result]


def test_find_companion_tab_presentation_linkbases_detects_tab_pre(tmp_path: Path) -> None:
    mod_dir = tmp_path / "mod"
    tab_dir = tmp_path / "tab"
    mod_dir.mkdir()
    tab_dir.mkdir()
    entry = mod_dir / "finrep_ind.xsd"
    entry.write_text("<xs:schema xmlns:xs='http://www.w3.org/2001/XMLSchema'/>", encoding="utf-8")
    tab_pre = tab_dir / "tab-pre.xml"
    tab_pre.write_text(
        "<link:linkbase xmlns:link='http://www.xbrl.org/2003/linkbase'/>",
        encoding="utf-8",
    )

    found = _find_companion_tab_presentation_linkbases(entry, known_linkbases=[])

    assert found == [tab_pre]


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

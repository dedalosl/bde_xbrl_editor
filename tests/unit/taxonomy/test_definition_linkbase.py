from __future__ import annotations

from pathlib import Path

from bde_xbrl_editor.taxonomy.linkbases.definition import (
    _resolve_locator_href,
    parse_definition_linkbase,
)
from bde_xbrl_editor.taxonomy.models import QName


def test_resolve_locator_href_keeps_fragment_only_fallback() -> None:
    qname = QName("http://example.com/tax", "Concept")

    resolved = _resolve_locator_href(
        "#example_Concept",
        Path("/tmp/example-def.xml"),
        {"example_Concept": qname},
        {},
        {},
    )

    assert resolved == qname


def test_resolve_locator_href_skips_ambiguous_explicit_schema_fallback() -> None:
    dim_qname = QName("http://www.eba.europa.eu/xbrl/crr/dict/dim", "GXI")

    resolved = _resolve_locator_href(
        "../../../../../dict/met/4.2/met.xsd#eba_GXI",
        Path("/tmp/z_15.00-def.xml"),
        {"eba_GXI": dim_qname},
        {},
        {},
    )

    assert resolved is None


def test_parse_definition_linkbase_expands_primary_items_across_has_hypercube_target_role(
    tmp_path: Path,
) -> None:
    primary_root = QName("http://example.com/met", "Root")
    primary_leaf = QName("http://example.com/met", "Leaf")
    hypercube = QName("http://www.eurofiling.info/xbrl/ext/model", "hyp")
    dimension = QName("http://example.com/dim", "Axis")

    concept_map = {
        "root": primary_root,
        "leaf": primary_leaf,
        "hyp": hypercube,
        "dim": dimension,
    }

    linkbase = tmp_path / "sample-def.xml"
    linkbase.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<link:linkbase
    xmlns:link="http://www.xbrl.org/2003/linkbase"
    xmlns:xlink="http://www.w3.org/1999/xlink"
    xmlns:xbrldt="http://xbrl.org/2005/xbrldt">
  <link:definitionLink xlink:role="http://example.com/elr/source">
    <link:loc xlink:type="locator" xlink:href="#root" xlink:label="loc_root"/>
    <link:loc xlink:type="locator" xlink:href="#hyp" xlink:label="loc_hyp"/>
    <link:definitionArc
        xlink:type="arc"
        xlink:arcrole="http://xbrl.org/int/dim/arcrole/all"
        xlink:from="loc_root"
        xlink:to="loc_hyp"
        xbrldt:contextElement="scenario"
        xbrldt:closed="true"
        xbrldt:targetRole="http://example.com/elr/target"/>
  </link:definitionLink>
  <link:definitionLink xlink:role="http://example.com/elr/target">
    <link:loc xlink:type="locator" xlink:href="#root" xlink:label="loc_root_target"/>
    <link:loc xlink:type="locator" xlink:href="#leaf" xlink:label="loc_leaf_target"/>
    <link:loc xlink:type="locator" xlink:href="#hyp" xlink:label="loc_hyp_target"/>
    <link:loc xlink:type="locator" xlink:href="#dim" xlink:label="loc_dim_target"/>
    <link:definitionArc
        xlink:type="arc"
        xlink:arcrole="http://xbrl.org/int/dim/arcrole/domain-member"
        xlink:from="loc_root_target"
        xlink:to="loc_leaf_target"/>
    <link:definitionArc
        xlink:type="arc"
        xlink:arcrole="http://xbrl.org/int/dim/arcrole/hypercube-dimension"
        xlink:from="loc_hyp_target"
        xlink:to="loc_dim_target"/>
  </link:definitionLink>
</link:linkbase>
""",
        encoding="utf-8",
    )

    _, hypercubes, _ = parse_definition_linkbase(linkbase, concept_map)

    assert len(hypercubes) == 1
    assert set(hypercubes[0].primary_items) == {primary_root, primary_leaf}
    assert hypercubes[0].dimensions == (dimension,)

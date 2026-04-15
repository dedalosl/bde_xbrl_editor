from __future__ import annotations

from pathlib import Path

from bde_xbrl_editor.taxonomy.linkbases.definition import _resolve_locator_href
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

"""CellEditDelegate — fact enumeration combo labels and prefixed QName data."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bde_xbrl_editor.taxonomy.label_resolver import LabelResolver
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    Label,
    QName,
    TaxonomyMetadata,
    TaxonomyStructure,
)
from bde_xbrl_editor.ui.widgets.cell_edit_delegate import (
    _build_namespace_prefix_map,
    _build_prefix_to_namespace,
    _fact_option_match_candidates,
    _parse_fact_option_lexical,
    _qname_to_prefixed_lexical,
)

_NS = "http://mem.example/ns"
_XBRLI = "http://www.xbrl.org/2003/instance"


def _taxonomy_with_member_labels() -> TaxonomyStructure:
    m_a = QName(_NS, "MemberA", prefix="mem")
    m_b = QName(_NS, "MemberB", prefix="mem")
    concepts = {
        m_a: Concept(qname=m_a, data_type=QName(_XBRLI, "stringItemType"), period_type="instant"),
        m_b: Concept(qname=m_b, data_type=QName(_XBRLI, "stringItemType"), period_type="instant"),
    }
    labels = {
        m_b: [
            Label(text="Miembro B (ES)", language="es", role="http://www.xbrl.org/2003/role/label"),
            Label(text="Member B EN", language="en", role="http://www.xbrl.org/2003/role/label"),
        ],
    }
    resolver = LabelResolver(labels, default_language_preference=["es", "en"])
    meta = TaxonomyMetadata("t", "1", "p", Path("/x.xsd"), datetime.now(), ("es", "en"))
    return TaxonomyStructure(
        metadata=meta,
        concepts=concepts,
        labels=resolver,
        presentation={},
        calculation={},
        definition={},
        hypercubes=(),
        dimensions={},
        tables=(),
    )


def test_parse_uri_and_prefix_roundtrip() -> None:
    tax = _taxonomy_with_member_labels()
    p2n = _build_prefix_to_namespace(tax)
    ns2p = _build_namespace_prefix_map(tax)
    uri = f"{_NS}#MemberB"
    qn = _parse_fact_option_lexical(uri, tax, p2n)
    assert qn is not None
    assert _qname_to_prefixed_lexical(qn, ns2p) == "mem:MemberB"
    assert _parse_fact_option_lexical("mem:MemberB", tax, p2n) == qn


def test_match_candidates_unify_prefix_clark_uri() -> None:
    tax = _taxonomy_with_member_labels()
    ns2p = _build_namespace_prefix_map(tax)
    p2n = _build_prefix_to_namespace(tax)
    c1 = _fact_option_match_candidates(f"{_NS}#MemberB", tax, ns2p, p2n)
    c2 = _fact_option_match_candidates("mem:MemberB", tax, ns2p, p2n)
    c3 = _fact_option_match_candidates(f"{{{_NS}}}MemberB", tax, ns2p, p2n)
    assert "mem:MemberB" in c1 and f"{_NS}#MemberB" in c1
    assert set(c1) == set(c2) == set(c3)


def test_spanish_label_preferred_for_member() -> None:
    tax = _taxonomy_with_member_labels()
    m_b = QName(_NS, "MemberB", prefix="mem")
    text = tax.labels.resolve(m_b, language_preference=["es", "en"])
    assert text == "Miembro B (ES)"

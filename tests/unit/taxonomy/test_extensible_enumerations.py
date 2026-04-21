"""Extensible Enumerations 1.0/2.0 — domain-member resolution for concept dropdowns."""

from __future__ import annotations

from bde_xbrl_editor.taxonomy.constants import ARCROLE_DOMAIN_MEMBER
from bde_xbrl_editor.taxonomy.loader import (
    _apply_extensible_enumeration_values,
    _collect_enumeration_domain_members,
    _member_qname_to_expanded_name_uri,
)
from bde_xbrl_editor.taxonomy.models import Concept, DefinitionArc, QName

_NS = "http://example.com/tst"
_EL = "http://example.com/role/enum-domain"


def _arc(
    source: QName,
    target: QName,
    *,
    elr: str = _EL,
    usable: bool | None = True,
    target_role: str | None = None,
) -> DefinitionArc:
    return DefinitionArc(
        arcrole=ARCROLE_DOMAIN_MEMBER,
        source=source,
        target=target,
        order=1.0,
        extended_link_role=elr,
        usable=usable,
        target_role=target_role,
    )


def test_collect_domain_skips_head_when_not_usable() -> None:
    head = QName(_NS, "Head")
    m1 = QName(_NS, "M1")
    m2 = QName(_NS, "M2")
    arcs = {_EL: [_arc(head, m1), _arc(m1, m2)]}
    got = _collect_enumeration_domain_members(_EL, head, head_usable=False, definition_arcs=arcs)
    assert got == [m1, m2]


def test_collect_domain_includes_head_when_usable() -> None:
    head = QName(_NS, "Head")
    m1 = QName(_NS, "M1")
    arcs = {_EL: [_arc(head, m1)]}
    got = _collect_enumeration_domain_members(_EL, head, head_usable=True, definition_arcs=arcs)
    assert got == [head, m1]


def test_collect_respects_usable_false() -> None:
    head = QName(_NS, "Head")
    bad = QName(_NS, "Bad")
    good = QName(_NS, "Good")
    arcs = {_EL: [_arc(head, bad, usable=False), _arc(head, good)]}
    got = _collect_enumeration_domain_members(_EL, head, head_usable=False, definition_arcs=arcs)
    assert got == [good]


def test_member_uri_format() -> None:
    q = QName("https://eba.europa.eu/xbrl/cdic", "qx123")
    assert _member_qname_to_expanded_name_uri(q) == "https://eba.europa.eu/xbrl/cdic#qx123"


def test_apply_sets_enumeration_values() -> None:
    head = QName(_NS, "Head")
    m1 = QName(_NS, "M1")
    metric = QName(_NS, "Metric0090")
    arcs = {_EL: [_arc(head, m1)]}
    c = Concept(
        qname=metric,
        data_type=QName("http://xbrl.org/2020/extensible-enumerations-2.0", "enumerationItemType"),
        period_type="instant",
        enumeration_domain=head,
        enumeration_linkrole=_EL,
        enumeration_head_usable=False,
    )
    concepts = {metric: c}
    out = _apply_extensible_enumeration_values(concepts, arcs)
    assert out[metric].enumeration_values == (_member_qname_to_expanded_name_uri(m1),)

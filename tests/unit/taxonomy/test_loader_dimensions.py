"""Unit tests for dimension reconstruction edge cases in taxonomy loader."""

from __future__ import annotations

from bde_xbrl_editor.taxonomy.constants import ARCROLE_DIMENSION_DOMAIN
from bde_xbrl_editor.taxonomy.loader import _rebuild_dimensions
from bde_xbrl_editor.taxonomy.models import DefinitionArc, QName


def test_rebuild_dimensions_keeps_multiple_dimension_domain_roots() -> None:
    dim_q = QName("http://www.bde.es/es/fr/esrs/comun/2008-06-01/dimensiones", "Agrupacion")
    member_a = QName(dim_q.namespace, "AgrupacionGrupoConsolidado")
    member_b = QName(dim_q.namespace, "AgrupacionSubgrupoConsolidado")
    member_c = QName(dim_q.namespace, "AgrupacionIndividual")
    member_d = QName(dim_q.namespace, "AgrupacionIndividualConInstrumentales")

    dimensions = _rebuild_dimensions(
        {
            "elr": [
                DefinitionArc(
                    arcrole=ARCROLE_DIMENSION_DOMAIN,
                    source=dim_q,
                    target=member_a,
                    order=1.0,
                    extended_link_role="elr",
                    usable=True,
                ),
                DefinitionArc(
                    arcrole=ARCROLE_DIMENSION_DOMAIN,
                    source=dim_q,
                    target=member_b,
                    order=2.0,
                    extended_link_role="elr",
                    usable=True,
                ),
                DefinitionArc(
                    arcrole=ARCROLE_DIMENSION_DOMAIN,
                    source=dim_q,
                    target=member_c,
                    order=3.0,
                    extended_link_role="elr",
                    usable=True,
                ),
                DefinitionArc(
                    arcrole=ARCROLE_DIMENSION_DOMAIN,
                    source=dim_q,
                    target=member_d,
                    order=4.0,
                    extended_link_role="elr",
                    usable=True,
                ),
            ]
        },
        concepts={},
    )

    assert [member.qname for member in dimensions[dim_q].members] == [
        member_a,
        member_b,
        member_c,
        member_d,
    ]

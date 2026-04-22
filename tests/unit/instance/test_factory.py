"""Unit tests for InstanceFactory.create() — validation and assembly."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bde_xbrl_editor.instance import (
    DimensionalConfiguration,
    InstanceCreationError,
    InstanceFactory,
    InvalidDimensionMemberError,
    InvalidEntityIdentifierError,
    InvalidReportingPeriodError,
    MissingDimensionValueError,
    ReportingEntity,
    ReportingPeriod,
    XbrlInstance,
)
from bde_xbrl_editor.instance.constants import BDE_DIM_NS
from bde_xbrl_editor.taxonomy.models import (
    DimensionModel,
    DomainMember,
    HypercubeModel,
    QName,
    TableDefinitionPWD,
    TaxonomyMetadata,
    TaxonomyStructure,
)


def _make_taxonomy(
    tables: list[TableDefinitionPWD] | None = None,
    hypercubes: list[HypercubeModel] | None = None,
    dimensions: dict | None = None,
) -> TaxonomyStructure:
    """Build a minimal TaxonomyStructure for factory tests."""
    from bde_xbrl_editor.taxonomy.models import BreakdownNode

    if tables is None:
        bd = BreakdownNode(node_type="rule")
        tables = [
            TableDefinitionPWD(
                table_id="T1",
                label="Table 1",
                extended_link_role="http://example.com/role/T1",
                x_breakdown=bd,
                y_breakdown=bd,
            )
        ]

    meta = TaxonomyMetadata(
        name="Test Taxonomy",
        version="1.0",
        publisher="Test",
        entry_point_path=Path("/tmp/entry_point.xsd"),
        loaded_at=datetime.now(),
        declared_languages=("es",),
    )
    label_resolver = MagicMock()
    label_resolver.resolve.return_value = "Label"

    return TaxonomyStructure(
        metadata=meta,
        concepts={},
        labels=label_resolver,
        presentation={},
        calculation={},
        definition={},
        hypercubes=hypercubes or [],
        dimensions=dimensions or {},
        tables=tables,
        formula_linkbase_path=None,
    )


def _entity() -> ReportingEntity:
    return ReportingEntity(identifier="ES0123456789", scheme="http://www.bde.es/")


def _instant() -> ReportingPeriod:
    return ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31))


class TestFactoryBasicValidation:
    def test_empty_table_ids_raises(self):
        factory = InstanceFactory(_make_taxonomy())
        with pytest.raises(InstanceCreationError, match="No tables selected"):
            factory.create(_entity(), _instant(), [], {})

    def test_unknown_table_id_raises(self):
        factory = InstanceFactory(_make_taxonomy())
        with pytest.raises(InstanceCreationError, match="not found"):
            factory.create(_entity(), _instant(), ["UNKNOWN"], {})

    def test_invalid_entity_identifier_raises(self):
        with pytest.raises(InvalidEntityIdentifierError):
            ReportingEntity(identifier="", scheme="http://www.bde.es/")

    def test_invalid_entity_scheme_raises(self):
        with pytest.raises(InvalidEntityIdentifierError):
            ReportingEntity(identifier="ES123", scheme="")

    def test_invalid_period_instant_without_date_raises(self):
        with pytest.raises(InvalidReportingPeriodError):
            ReportingPeriod(period_type="instant")

    def test_invalid_period_duration_end_before_start_raises(self):
        with pytest.raises(InvalidReportingPeriodError):
            ReportingPeriod(
                period_type="duration",
                start_date=date(2024, 12, 31),
                end_date=date(2024, 1, 1),
            )

    def test_invalid_period_duration_missing_dates_raises(self):
        with pytest.raises(InvalidReportingPeriodError):
            ReportingPeriod(period_type="duration")


class TestFactorySuccessfulCreate:
    def test_returns_xbrl_instance(self):
        factory = InstanceFactory(_make_taxonomy())
        result = factory.create(_entity(), _instant(), ["T1"], {})
        assert isinstance(result, XbrlInstance)

    def test_dirty_flag_set(self):
        factory = InstanceFactory(_make_taxonomy())
        result = factory.create(_entity(), _instant(), ["T1"], {})
        assert result.has_unsaved_changes is True

    def test_source_path_none(self):
        factory = InstanceFactory(_make_taxonomy())
        result = factory.create(_entity(), _instant(), ["T1"], {})
        assert result.source_path is None

    def test_facts_empty(self):
        factory = InstanceFactory(_make_taxonomy())
        result = factory.create(_entity(), _instant(), ["T1"], {})
        assert result.facts == []

    def test_entity_and_period_preserved(self):
        e, p = _entity(), _instant()
        factory = InstanceFactory(_make_taxonomy())
        result = factory.create(e, p, ["T1"], {})
        assert result.entity is e
        assert result.period is p

    def test_included_table_ids_preserved(self):
        factory = InstanceFactory(_make_taxonomy())
        result = factory.create(_entity(), _instant(), ["T1"], {})
        assert result.included_table_ids == ["T1"]

    def test_at_least_one_context_generated(self):
        factory = InstanceFactory(_make_taxonomy())
        result = factory.create(_entity(), _instant(), ["T1"], {})
        assert len(result.contexts) >= 1

    def test_filing_indicators_match_tables(self):
        factory = InstanceFactory(_make_taxonomy())
        result = factory.create(_entity(), _instant(), ["T1"], {})
        assert len(result.filing_indicators) == 1
        assert result.filing_indicators[0].template_id == "T1"
        assert result.filing_indicators[0].filed is True

    def test_units_prepopulated(self):
        factory = InstanceFactory(_make_taxonomy())
        result = factory.create(_entity(), _instant(), ["T1"], {})
        assert "EUR" in result.units
        assert "pure" in result.units

    def test_schema_ref_href_from_entry_point(self):
        factory = InstanceFactory(_make_taxonomy())
        result = factory.create(_entity(), _instant(), ["T1"], {})
        assert "entry_point.xsd" in result.schema_ref_href

    def test_bde_taxonomy_prepopulates_all_estados_reportados(self):
        from bde_xbrl_editor.taxonomy.models import BreakdownNode

        bd = BreakdownNode(node_type="rule")
        taxonomy = _make_taxonomy(
            tables=[
                TableDefinitionPWD(
                    table_id="T1",
                    label="Table 1",
                    extended_link_role="http://example.com/role/T1",
                    x_breakdown=bd,
                    y_breakdown=bd,
                    table_code="3201",
                ),
                TableDefinitionPWD(
                    table_id="T2",
                    label="Table 2",
                    extended_link_role="http://example.com/role/T2",
                    x_breakdown=bd,
                    y_breakdown=bd,
                    table_code="3202",
                ),
            ]
        )

        result = InstanceFactory(taxonomy).create(_entity(), _instant(), ["T1"], {})

        assert result.bde_preambulo is not None
        assert [estado.codigo for estado in result.bde_preambulo.estados_reportados] == ["3201", "3202"]
        assert result.bde_preambulo.estados_reportados[0].blanco is False
        assert result.bde_preambulo.estados_reportados[1].blanco is True
        assert [fi.template_id for fi in result.filing_indicators] == ["3201", "3202"]

    def test_bde_taxonomy_requires_agrupacion_selection(self):
        from bde_xbrl_editor.taxonomy.models import BreakdownNode

        bd = BreakdownNode(node_type="rule")
        taxonomy = _make_taxonomy(
            tables=[
                TableDefinitionPWD(
                    table_id="T1",
                    label="Table 1",
                    extended_link_role="http://example.com/role/T1",
                    x_breakdown=bd,
                    y_breakdown=bd,
                    table_code="3201",
                )
            ],
            dimensions={
                QName(BDE_DIM_NS, "Agrupacion", prefix="es-be-cm-dim"): DimensionModel(
                    qname=QName(BDE_DIM_NS, "Agrupacion", prefix="es-be-cm-dim"),
                    dimension_type="explicit",
                    members=(
                        DomainMember(
                            qname=QName(
                                BDE_DIM_NS,
                                "AgrupacionIndividual",
                                prefix="es-be-cm-dim",
                            ),
                            parent=None,
                            order=1.0,
                            usable=True,
                        ),
                    ),
                )
            },
        )

        with pytest.raises(InstanceCreationError, match="Agrupacion"):
            InstanceFactory(taxonomy).create(_entity(), _instant(), ["T1"], {})

    def test_bde_taxonomy_sets_agrupacion_on_all_generated_contexts(self):
        from bde_xbrl_editor.taxonomy.models import BreakdownNode

        bd = BreakdownNode(node_type="rule")
        dim_q = QName("http://example.com/dim", "Dim1")
        mem_q = QName("http://example.com/dim", "Mem1")
        agrupacion_dim = QName(BDE_DIM_NS, "Agrupacion", prefix="es-be-cm-dim")
        agrupacion_member = QName(
            BDE_DIM_NS,
            "AgrupacionIndividual",
            prefix="es-be-cm-dim",
        )
        taxonomy = _make_taxonomy(
            tables=[
                TableDefinitionPWD(
                    table_id="T1",
                    label="Table 1",
                    extended_link_role="http://example.com/role/T1",
                    x_breakdown=bd,
                    y_breakdown=bd,
                    table_code="3201",
                )
            ],
            hypercubes=[
                HypercubeModel(
                    qname=QName("http://example.com/dim", "HC1"),
                    arcrole="all",
                    closed=True,
                    context_element="scenario",
                    primary_items=(),
                    dimensions=(dim_q,),
                    extended_link_role="http://example.com/role/T1",
                )
            ],
            dimensions={
                dim_q: DimensionModel(
                    qname=dim_q,
                    dimension_type="explicit",
                    members=(DomainMember(qname=mem_q, parent=None, order=1.0, usable=True),),
                ),
                agrupacion_dim: DimensionModel(
                    qname=agrupacion_dim,
                    dimension_type="explicit",
                    members=(
                        DomainMember(
                            qname=agrupacion_member,
                            parent=None,
                            order=1.0,
                            usable=True,
                        ),
                    ),
                ),
            },
        )

        result = InstanceFactory(taxonomy).create(
            _entity(),
            _instant(),
            ["T1"],
            {
                "T1": DimensionalConfiguration(
                    table_id="T1",
                    dimension_assignments={dim_q: mem_q},
                )
            },
            agrupacion_member=agrupacion_member,
        )

        assert result.contexts
        for ctx in result.contexts.values():
            assert ctx.dimensions[agrupacion_dim] == agrupacion_member
            assert ctx.dim_containers[agrupacion_dim] == "segment"


class TestFactoryDimensionalValidation:
    def _make_taxonomy_with_dim(self, has_default: bool = False) -> TaxonomyStructure:
        """Build a taxonomy with one table and one mandatory dimension."""
        from bde_xbrl_editor.taxonomy.models import BreakdownNode

        dim_q = QName("http://example.com/dim", "Dim1")
        mem1 = QName("http://example.com/dim", "Mem1")
        mem2 = QName("http://example.com/dim", "Mem2")
        elr = "http://example.com/role/T1"

        bd = BreakdownNode(node_type="rule")
        table = TableDefinitionPWD(
            table_id="T1",
            label="Table 1",
            extended_link_role=elr,
            x_breakdown=bd,
            y_breakdown=bd,
        )
        hc = HypercubeModel(
            qname=QName("http://example.com/dim", "HC1"),
            arcrole="all",
            closed=True,
            context_element="scenario",
            primary_items=(),
            dimensions=(dim_q,),
            extended_link_role=elr,
        )
        dim_model = DimensionModel(
            qname=dim_q,
            dimension_type="explicit",
            default_member=mem1 if has_default else None,
            domain=None,
            members=(
                DomainMember(qname=mem1, parent=None, order=1.0, usable=True),
                DomainMember(qname=mem2, parent=None, order=2.0, usable=True),
            ),
        )
        return _make_taxonomy(
            tables=[table],
            hypercubes=[hc],
            dimensions={dim_q: dim_model},
        )

    def test_missing_mandatory_dimension_raises(self):
        taxonomy = self._make_taxonomy_with_dim(has_default=False)
        factory = InstanceFactory(taxonomy)
        with pytest.raises(MissingDimensionValueError) as exc_info:
            factory.create(_entity(), _instant(), ["T1"], {})
        assert exc_info.value.table_id == "T1"

    def test_optional_dimension_not_required(self):
        taxonomy = self._make_taxonomy_with_dim(has_default=True)
        factory = InstanceFactory(taxonomy)
        # Should not raise — dimension has a default member
        result = factory.create(_entity(), _instant(), ["T1"], {})
        assert result is not None

    def test_invalid_member_raises(self):
        taxonomy = self._make_taxonomy_with_dim(has_default=False)
        factory = InstanceFactory(taxonomy)
        dim_q = QName("http://example.com/dim", "Dim1")
        bad_member = QName("http://example.com/dim", "BadMem")
        dim_cfg = DimensionalConfiguration(
            table_id="T1",
            dimension_assignments={dim_q: bad_member},
        )
        with pytest.raises(InvalidDimensionMemberError) as exc_info:
            factory.create(_entity(), _instant(), ["T1"], {"T1": dim_cfg})
        assert exc_info.value.table_id == "T1"

    def test_valid_dimension_assignment_succeeds(self):
        taxonomy = self._make_taxonomy_with_dim(has_default=False)
        factory = InstanceFactory(taxonomy)
        dim_q = QName("http://example.com/dim", "Dim1")
        mem1 = QName("http://example.com/dim", "Mem1")
        dim_cfg = DimensionalConfiguration(
            table_id="T1",
            dimension_assignments={dim_q: mem1},
        )
        result = factory.create(_entity(), _instant(), ["T1"], {"T1": dim_cfg})
        assert result is not None
        # Context with dimension should be generated
        assert len(result.contexts) >= 2  # fi context + dimensional context

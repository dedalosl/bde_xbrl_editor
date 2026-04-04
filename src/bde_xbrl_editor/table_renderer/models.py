"""Layout computation models — ComputedTableLayout, HeaderGrid, HeaderCell, BodyCell, etc."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.models import ReportingEntity, ReportingPeriod
    from bde_xbrl_editor.taxonomy.models import BreakdownNode, QName


@dataclass
class HeaderCell:
    """One cell within the multi-level column or row header area."""

    label: str
    rc_code: str | None
    span: int  # number of leaf columns/rows this cell spans (>=1; leaves=1)
    level: int  # depth in hierarchy (0 = root level)
    is_leaf: bool
    is_abstract: bool
    source_node: BreakdownNode
    fin_code: str | None = None  # http://www.bde.es/xbrl/role/fin-code label, for cell code


@dataclass
class HeaderGrid:
    """Complete header for one axis (X or Y), ready to paint."""

    levels: list[list[HeaderCell]]  # outer = depth level 0 is outermost
    leaf_count: int  # total leaf cells = number of data columns or rows
    depth: int  # number of header levels


@dataclass
class CellCoordinate:
    """Complete XBRL dimensional coordinate of one body cell."""

    concept: QName | None = None
    explicit_dimensions: dict[QName, QName] = field(default_factory=dict)
    period_override: ReportingPeriod | None = None
    entity_override: ReportingEntity | None = None


@dataclass
class BodyCell:
    """One data cell in the rendered table body."""

    row_index: int
    col_index: int
    coordinate: CellCoordinate
    fact_value: str | None = None
    fact_decimals: str | None = None
    is_duplicate: bool = False
    is_applicable: bool = True
    cell_code: str | None = None  # row_fin_code + col_fin_code


@dataclass
class ZMemberOption:
    """One entry in the Z-axis navigation selector."""

    index: int
    label: str
    dimension_constraints: dict[QName, QName] = field(default_factory=dict)


@dataclass
class FactMatchResult:
    """Outcome of attempting to match instance facts to a single BodyCell."""

    matched: bool
    fact_value: str | None = None
    fact_decimals: str | None = None
    duplicate_count: int = 0


@dataclass
class ComputedTableLayout:
    """Full layout for one table and one Z-axis selection. Immutable after construction."""

    table_id: str
    table_label: str
    column_header: HeaderGrid
    row_header: HeaderGrid
    z_members: list[ZMemberOption]
    active_z_index: int
    body: list[list[BodyCell]]  # body[row][col]

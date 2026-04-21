"""Layout computation models — ComputedTableLayout, HeaderGrid, HeaderCell, BodyCell, etc."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

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
    # Accumulated constraints from root → this node (parent dims + own dims).
    # Used by layout engine to build fully-qualified CellCoordinates.
    accumulated_aspect_constraints: dict[str, Any] = field(default_factory=dict)
    # True when this cell is the virtual leaf injected for a roll-up node (non-abstract
    # node that also has children).  The painter uses this to apply a "roll-up" style.
    is_rollup_virtual: bool = False


@dataclass
class HeaderGrid:
    """Complete header for one axis (X or Y), ready to paint."""

    levels: list[list[HeaderCell]]  # outer = depth level 0 is outermost
    leaf_count: int  # total leaf cells = number of data columns or rows
    depth: int  # number of header levels
    # Leaf cells in strict left-to-right (DFS) column order.  Used for body coordinate
    # mapping instead of scanning levels, which gives wrong order for nested roll-ups.
    ordered_leaves: list[HeaderCell] = field(default_factory=list)


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
    is_excluded: bool = False  # True when dimensional constraints forbid this cell
    cell_code: str | None = None  # row_fin_code + col_fin_code
    cell_kind: str = "fact"  # fact | open-key | placeholder
    open_key_signature: tuple[Any, ...] | None = None
    open_key_dimension: "QName | None" = None
    open_key_member: "QName | None" = None
    open_key_text: str | None = None
    open_key_options: tuple[Any, ...] = field(default_factory=tuple)
    fact_options: tuple[str, ...] = field(default_factory=tuple)


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
    active_z_constraints: dict["QName", "QName"] = field(default_factory=dict)

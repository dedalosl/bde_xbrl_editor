"""TableLayoutEngine — pure-Python layout computation (no Qt dependency)."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from bde_xbrl_editor.table_renderer.errors import TableLayoutError, ZIndexOutOfRangeError
from bde_xbrl_editor.table_renderer.models import (
    BodyCell,
    CellCoordinate,
    ComputedTableLayout,
    FactMatchResult,
    HeaderCell,
    HeaderGrid,
    ZMemberOption,
)
from bde_xbrl_editor.taxonomy.models import QName

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.models import XbrlInstance
    from bde_xbrl_editor.taxonomy.models import (
        BreakdownNode,
        TableDefinitionPWD,
        TaxonomyStructure,
    )

# Aspect constraint key constants
_CONCEPT_KEY = "concept"
_EXPLICIT_DIM_KEY = "explicitDimension"


def _get_label(node: BreakdownNode, taxonomy: TaxonomyStructure, language_preference: list[str]) -> str:
    """Resolve a display label for a breakdown node."""
    if node.label:
        return node.label
    # Try to resolve from concept aspect constraint
    concept_str = node.aspect_constraints.get(_CONCEPT_KEY)
    if concept_str:
        try:
            qname = QName.from_clark(concept_str)
            return taxonomy.labels.resolve(qname, language_preference=language_preference)
        except Exception:  # noqa: BLE001
            pass
    return ""


def _build_axis_grid(
    root: BreakdownNode,
    taxonomy: TaxonomyStructure,
    language_preference: list[str],
) -> HeaderGrid:
    """DFS traversal to build a HeaderGrid for one axis (X or Y).

    Leaf index assignment: left-to-right DFS order.
    Span = number of descendant leaf nodes.
    Level = depth from root.
    """
    levels: list[list[HeaderCell]] = []

    def _count_leaves(node: BreakdownNode) -> int:
        non_abstract_children = [c for c in node.children if not c.is_abstract or c.children]
        if not non_abstract_children:
            return 1
        return sum(_count_leaves(c) for c in non_abstract_children)

    def _dfs(node: BreakdownNode, level: int) -> None:
        while len(levels) <= level:
            levels.append([])

        non_abstract_children = [c for c in node.children if not c.is_abstract or c.children]
        is_leaf = len(non_abstract_children) == 0
        span = 1 if is_leaf else sum(_count_leaves(c) for c in non_abstract_children)

        label = _get_label(node, taxonomy, language_preference)
        cell = HeaderCell(
            label=label,
            rc_code=node.rc_code,
            span=span,
            level=level,
            is_leaf=is_leaf,
            is_abstract=node.is_abstract,
            source_node=node,
        )
        levels[level].append(cell)

        for child in non_abstract_children:
            _dfs(child, level + 1)

    for child in root.children:
        _dfs(child, 0)

    if not levels:
        # Degenerate case: root has no children — treat root itself as a leaf
        levels = [[
            HeaderCell(
                label=_get_label(root, taxonomy, language_preference),
                rc_code=root.rc_code,
                span=1,
                level=0,
                is_leaf=True,
                is_abstract=root.is_abstract,
                source_node=root,
            )
        ]]

    leaf_count = sum(1 for cell in levels[-1] if cell.is_leaf)
    if leaf_count == 0:
        leaf_count = sum(cell.span for cell in levels[0])

    return HeaderGrid(levels=levels, leaf_count=leaf_count, depth=len(levels))


def _extract_z_members(
    z_breakdowns: tuple[BreakdownNode, ...],
    taxonomy: TaxonomyStructure,
    language_preference: list[str],
) -> list[ZMemberOption]:
    """Extract Z-axis member options from z_breakdowns."""
    if not z_breakdowns:
        return [ZMemberOption(index=0, label="Default", dimension_constraints={})]

    options: list[ZMemberOption] = []
    idx = 0

    def _collect(node: BreakdownNode) -> None:
        nonlocal idx
        if not node.children:
            label = _get_label(node, taxonomy, language_preference) or f"Z-member {idx}"
            dim_constraints: dict[QName, QName] = {}
            # Extract dimension constraints from aspect_constraints
            for key, val in node.aspect_constraints.items():
                if key == _EXPLICIT_DIM_KEY and val:
                    try:
                        dim_q = QName.from_clark(str(key))
                        mem_q = QName.from_clark(str(val))
                        dim_constraints[dim_q] = mem_q
                    except Exception:  # noqa: BLE001
                        pass
            options.append(ZMemberOption(index=idx, label=label, dimension_constraints=dim_constraints))
            idx += 1
        else:
            for child in node.children:
                _collect(child)

    for z_root in z_breakdowns:
        if z_root.children:
            for child in z_root.children:
                _collect(child)
        else:
            _collect(z_root)

    if not options:
        options = [ZMemberOption(index=0, label="Default", dimension_constraints={})]

    return options


def _get_leaf_constraints(header_grid: HeaderGrid) -> list[dict[str, str]]:
    """Return a list of aspect_constraints dicts for each leaf node (in order)."""
    if not header_grid.levels:
        return [{}]
    leaf_level = header_grid.levels[-1]
    return [cell.source_node.aspect_constraints for cell in leaf_level if cell.is_leaf]


def _build_coordinate(
    row_constraints: dict[str, str],
    col_constraints: dict[str, str],
    z_constraints: dict[QName, QName],
    taxonomy: TaxonomyStructure,
) -> CellCoordinate:
    """Merge aspect constraints from X-leaf + Y-leaf + Z-member into a CellCoordinate."""
    concept: QName | None = None
    explicit_dims: dict[QName, QName] = {}

    # Merge all constraints; last writer wins for conflicts
    merged: dict[str, str] = {}
    merged.update(row_constraints)
    merged.update(col_constraints)

    for key, val in merged.items():
        if key == _CONCEPT_KEY and val:
            with contextlib.suppress(Exception):
                concept = QName.from_clark(str(val))
        elif key == _EXPLICIT_DIM_KEY and val:
            # val could be "dim:member" or similar; treat as a single dimension for now
            pass

    # Add Z-axis dimension constraints
    explicit_dims.update(z_constraints)

    return CellCoordinate(concept=concept, explicit_dimensions=explicit_dims)


def _build_body(
    row_grid: HeaderGrid,
    col_grid: HeaderGrid,
    z_constraints: dict[QName, QName],
    taxonomy: TaxonomyStructure,
) -> list[list[BodyCell]]:
    """Build the body cell grid from row/col leaf constraints + Z member constraints."""
    row_leaf_constraints = _get_leaf_constraints(row_grid)
    col_leaf_constraints = _get_leaf_constraints(col_grid)

    body: list[list[BodyCell]] = []
    for row_idx, row_c in enumerate(row_leaf_constraints):
        row_cells: list[BodyCell] = []
        for col_idx, col_c in enumerate(col_leaf_constraints):
            coord = _build_coordinate(row_c, col_c, z_constraints, taxonomy)
            cell = BodyCell(
                row_index=row_idx,
                col_index=col_idx,
                coordinate=coord,
            )
            row_cells.append(cell)
        body.append(row_cells)

    return body


class TableLayoutEngine:
    """Converts a TableDefinitionPWD into a ComputedTableLayout. Pure Python, no Qt."""

    def __init__(self, taxonomy: TaxonomyStructure) -> None:
        self._taxonomy = taxonomy

    def compute(
        self,
        table: TableDefinitionPWD,
        instance: XbrlInstance | None = None,
        z_index: int = 0,
        language_preference: list[str] | None = None,
    ) -> ComputedTableLayout:
        """Compute the full grid layout for the given table and Z-axis selection.

        Raises:
            TableLayoutError: table definition is structurally invalid.
            ZIndexOutOfRangeError: z_index >= number of available Z members.
        """
        lang_pref = language_preference or ["es", "en"]

        try:
            # Build Z-axis members
            z_members = _extract_z_members(table.z_breakdowns, self._taxonomy, lang_pref)

            # Validate z_index
            if z_index < 0 or z_index >= len(z_members):
                raise ZIndexOutOfRangeError(
                    table_id=table.table_id,
                    requested_z=z_index,
                    max_z=len(z_members) - 1,
                )

            active_z = z_members[z_index]

            # Build X-axis (column) and Y-axis (row) header grids
            col_header = _build_axis_grid(table.x_breakdown, self._taxonomy, lang_pref)
            row_header = _build_axis_grid(table.y_breakdown, self._taxonomy, lang_pref)

            # Build body cell grid
            body = _build_body(row_header, col_header, active_z.dimension_constraints, self._taxonomy)

            # Optionally wire fact values
            if instance is not None:
                from bde_xbrl_editor.table_renderer.fact_mapper import FactMapper  # noqa: PLC0415

                mapper = FactMapper(self._taxonomy)
                for row in body:
                    for cell in row:
                        result: FactMatchResult = mapper.match(cell.coordinate, instance)
                        if result.matched or result.duplicate_count > 0:
                            cell.fact_value = result.fact_value
                            cell.fact_decimals = result.fact_decimals
                            cell.is_duplicate = result.duplicate_count > 1

            table_label = table.label or table.table_id

        except (TableLayoutError, ZIndexOutOfRangeError):
            raise
        except Exception as exc:  # noqa: BLE001
            raise TableLayoutError(table_id=table.table_id, reason=str(exc)) from exc

        return ComputedTableLayout(
            table_id=table.table_id,
            table_label=table_label,
            column_header=col_header,
            row_header=row_header,
            z_members=z_members,
            active_z_index=z_index,
            body=body,
        )

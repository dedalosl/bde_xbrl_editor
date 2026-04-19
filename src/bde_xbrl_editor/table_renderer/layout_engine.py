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
from bde_xbrl_editor.taxonomy.constants import (
    ARCROLE_DIMENSION_DOMAIN,
    ARCROLE_DOMAIN_MEMBER,
    ARCROLE_HYPERCUBE_DIMENSION,
    RC_CODE_ROLE,
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


def _strip_default_member_dimensions(
    explicit_dims: dict[QName, QName],
    taxonomy: TaxonomyStructure,
) -> dict[QName, QName]:
    """Drop dimensions whose member is the taxonomy default member.

    In XBRL Dimensions, an omitted explicit dimension is semantically
    equivalent to the default member for that dimension. Table coordinates must
    therefore not require facts to carry explicit ``qx0``-style defaults.
    """
    normalized: dict[QName, QName] = {}
    for dim_qname, member_qname in explicit_dims.items():
        dim_model = taxonomy.dimensions.get(dim_qname)
        if dim_model is not None and dim_model.default_member == member_qname:
            continue
        normalized[dim_qname] = member_qname
    return normalized


def _accumulate_constraints(
    parent: dict,
    node: dict,
) -> dict:
    """Merge parent aspect_constraints into a child node's constraints.

    Child wins on conflicts.  explicitDimension sub-dicts are merged so that
    parent-declared dimensions survive unless the child overrides them.
    """
    result: dict = dict(parent)
    if _CONCEPT_KEY in node:
        result[_CONCEPT_KEY] = node[_CONCEPT_KEY]
    parent_dims: dict = result.get(_EXPLICIT_DIM_KEY) or {}
    child_dims: dict = node.get(_EXPLICIT_DIM_KEY) or {}
    if parent_dims or child_dims:
        result[_EXPLICIT_DIM_KEY] = {**parent_dims, **child_dims}
    for k, v in node.items():
        if k not in (_CONCEPT_KEY, _EXPLICIT_DIM_KEY):
            result[k] = v
    return result


def _get_label(
    node: BreakdownNode, taxonomy: TaxonomyStructure, language_preference: list[str]
) -> str:
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


def _get_fin_code(
    node: BreakdownNode, taxonomy: TaxonomyStructure, language_preference: list[str]  # noqa: ARG001
) -> str | None:
    """Return the fin-code for a breakdown node.

    Fin-codes are parsed directly from the table node label linkbase
    (http://www.bde.es/xbrl/role/fin-code) into BreakdownNode.fin_code during
    taxonomy loading, so we just return that field.
    """
    return node.fin_code


def _get_rc_code(
    node: BreakdownNode, taxonomy: TaxonomyStructure, language_preference: list[str]
) -> str | None:
    """Resolve the RC-code for a breakdown node.

    Uses node.rc_code (from the table-level label linkbase) first.
    Falls back to the ``http://www.eurofiling.info/xbrl/role/rc-code`` label
    of the concept this node constrains, if available.
    """
    if node.rc_code:
        return node.rc_code
    concept_str = node.aspect_constraints.get(_CONCEPT_KEY)
    if not concept_str:
        return None
    with contextlib.suppress(Exception):
        qname = QName.from_clark(concept_str)
        rc_labels = [
            lb for lb in taxonomy.labels.get_all_labels(qname) if lb.role == RC_CODE_ROLE
        ]
        if not rc_labels:
            return None
        for lang in language_preference:
            for lb in rc_labels:
                if lb.language == lang:
                    return lb.text
        return rc_labels[0].text
    return None


def _build_row_axis_grid(
    root: BreakdownNode,
    taxonomy: TaxonomyStructure,
    language_preference: list[str],
) -> HeaderGrid:
    """DFS traversal to build a flat HeaderGrid for the Y-axis (rows).

    Every node — abstract and non-abstract — becomes exactly one row in DFS order.
    ``HeaderCell.level`` records the tree depth for indentation.
    Abstract rows get is_leaf=False; non-abstract rows get is_leaf=True (they carry data).
    ``levels[i]`` is always a single-element list so ``levels[i][0]`` is the i-th row cell.
    """
    dfs_cells: list[HeaderCell] = []
    max_depth = 0

    def _dfs(node: BreakdownNode, depth: int, parent_constraints: dict) -> None:
        nonlocal max_depth
        if depth > max_depth:
            max_depth = depth
        accumulated = _accumulate_constraints(parent_constraints, node.aspect_constraints)
        label = _get_label(node, taxonomy, language_preference)
        cell = HeaderCell(
            label=label,
            rc_code=_get_rc_code(node, taxonomy, language_preference),
            fin_code=_get_fin_code(node, taxonomy, language_preference),
            span=1,
            level=depth,
            is_leaf=not node.is_abstract,
            is_abstract=node.is_abstract,
            source_node=node,
            accumulated_aspect_constraints=accumulated,
        )
        dfs_cells.append(cell)
        for child in node.children:
            _dfs(child, depth + 1, accumulated)

    for child in root.children:
        _dfs(child, 0, {})

    if not dfs_cells:
        dfs_cells = [
            HeaderCell(
                label=_get_label(root, taxonomy, language_preference),
                rc_code=_get_rc_code(root, taxonomy, language_preference),
                fin_code=_get_fin_code(root, taxonomy, language_preference),
                span=1,
                level=0,
                is_leaf=not root.is_abstract,
                is_abstract=root.is_abstract,
                source_node=root,
                accumulated_aspect_constraints=dict(root.aspect_constraints),
            )
        ]

    levels = [[cell] for cell in dfs_cells]
    return HeaderGrid(levels=levels, leaf_count=len(dfs_cells), depth=max_depth + 1)


def _build_axis_grid(
    root: BreakdownNode,
    taxonomy: TaxonomyStructure,
    language_preference: list[str],
) -> HeaderGrid:
    """DFS traversal to build a HeaderGrid for one axis (X or Y).

    Leaf index assignment: left-to-right DFS order.
    Span = number of descendant leaf nodes (including the roll-up node's own virtual leaf).
    Level = depth from root.

    Roll-up nodes (non-abstract nodes that also have children) generate two structures:
      1. A spanning header cell at their natural level (is_leaf=False, span=N).
      2. A virtual leaf cell at the next level, positioned per parentChildOrder.
    Placeholder cells (is_leaf=False, span=1, is_abstract=True) are inserted at all levels
    deeper than the virtual leaf to keep the cursor aligned for the painter.

    ``ordered_leaves`` in the returned HeaderGrid contains all leaf cells in strict
    left-to-right DFS order — use this (not level scanning) for body column mapping.
    """
    levels: list[list[tuple[int, HeaderCell]]] = []
    ordered_leaves: list[HeaderCell] = []

    def _subtree_leaf_width(node: BreakdownNode) -> int:
        child_total = sum(_subtree_leaf_width(child) for child in node.children)
        own_width = 1 if not node.is_abstract else 0
        return max(own_width + child_total, 1)

    def _dfs(node: BreakdownNode, level: int, start: int, parent_constraints: dict) -> int:
        while len(levels) <= level:
            levels.append([])

        accumulated = _accumulate_constraints(parent_constraints, node.aspect_constraints)
        # A roll-up node is non-abstract AND has children.  It contributes both a
        # spanning header cell (at this level) and a virtual leaf cell (at the next
        # level, whose position follows parentChildOrder).
        is_rollup = not node.is_abstract and bool(node.children)
        is_leaf = not node.is_abstract and not node.children
        span = _subtree_leaf_width(node)

        label = _get_label(node, taxonomy, language_preference)
        cell = HeaderCell(
            label=label,
            rc_code=_get_rc_code(node, taxonomy, language_preference),
            fin_code=_get_fin_code(node, taxonomy, language_preference),
            span=span,
            level=level,
            is_leaf=is_leaf,
            is_abstract=node.is_abstract,
            source_node=node,
            accumulated_aspect_constraints=accumulated,
        )
        levels[level].append((start, cell))

        if is_leaf:
            ordered_leaves.append(cell)
            return span

        if is_rollup:
            pco = node.parent_child_order
            while len(levels) <= level + 1:
                levels.append([])

            # Virtual leaf: represents this roll-up node's own data column.
            # Label is empty — the spanning header above already shows the label.
            virtual_leaf = HeaderCell(
                label="",
                rc_code=_get_rc_code(node, taxonomy, language_preference),
                fin_code=_get_fin_code(node, taxonomy, language_preference),
                span=1,
                level=level + 1,
                is_leaf=True,
                is_abstract=False,
                is_rollup_virtual=True,
                source_node=node,
                accumulated_aspect_constraints=accumulated,
            )

            if pco == "children-first":
                cursor = start
                for child in node.children:
                    child_width = _subtree_leaf_width(child)
                    _dfs(child, level + 1, cursor, accumulated)
                    cursor += child_width
                ordered_leaves.append(virtual_leaf)
                levels[level + 1].append((cursor, virtual_leaf))
            else:
                # parent-first (default)
                ordered_leaves.append(virtual_leaf)
                levels[level + 1].append((start, virtual_leaf))
                cursor = start + 1
                for child in node.children:
                    child_width = _subtree_leaf_width(child)
                    _dfs(child, level + 1, cursor, accumulated)
                    cursor += child_width
        else:
            cursor = start
            for child in node.children:
                child_width = _subtree_leaf_width(child)
                _dfs(child, level + 1, cursor, accumulated)
                cursor += child_width

        return span

    total_leaf_count = 0
    cursor = 0

    for child in root.children:
        child_width = _subtree_leaf_width(child)
        _dfs(child, 0, cursor, {})
        cursor += child_width
        total_leaf_count += child_width

    if not levels:
        # Degenerate case: root has no children — treat root itself as a leaf
        root_cell = HeaderCell(
            label=_get_label(root, taxonomy, language_preference),
            rc_code=_get_rc_code(root, taxonomy, language_preference),
            fin_code=_get_fin_code(root, taxonomy, language_preference),
            span=1,
            level=0,
            is_leaf=True,
            is_abstract=root.is_abstract,
            source_node=root,
            accumulated_aspect_constraints=dict(root.aspect_constraints),
        )
        levels = [[(0, root_cell)]]
        ordered_leaves = [root_cell]
        total_leaf_count = 1

    normalised_levels: list[list[HeaderCell]] = []
    for level_idx, entries in enumerate(levels):
        ordered_entries = sorted(entries, key=lambda item: item[0])
        cursor = 0
        cells: list[HeaderCell] = []
        for start, cell in ordered_entries:
            while cursor < start:
                cells.append(
                    HeaderCell(
                        label="",
                        rc_code=None,
                        fin_code=None,
                        span=1,
                        level=level_idx,
                        is_leaf=False,
                        is_abstract=True,
                        source_node=root,
                        accumulated_aspect_constraints={},
                    )
                )
                cursor += 1
            cells.append(cell)
            cursor += 1 if cell.is_leaf else cell.span
        while cursor < total_leaf_count:
            cells.append(
                HeaderCell(
                    label="",
                    rc_code=None,
                    fin_code=None,
                    span=1,
                    level=level_idx,
                    is_leaf=False,
                    is_abstract=True,
                    source_node=root,
                    accumulated_aspect_constraints={},
                )
            )
            cursor += 1
        normalised_levels.append(cells)

    return HeaderGrid(
        levels=normalised_levels,
        leaf_count=total_leaf_count,
        depth=len(normalised_levels),
        ordered_leaves=ordered_leaves,
    )


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

    def _collect(node: BreakdownNode, parent_constraints: dict) -> None:
        nonlocal idx
        accumulated = _accumulate_constraints(parent_constraints, node.aspect_constraints)
        if not node.children:
            label = _get_label(node, taxonomy, language_preference) or f"Z-member {idx}"
            dim_constraints: dict[QName, QName] = {}
            # Extract dimension constraints from accumulated aspect_constraints
            dims = accumulated.get(_EXPLICIT_DIM_KEY)
            if dims and isinstance(dims, dict):
                for dim_clark, mem_clark in dims.items():
                    with contextlib.suppress(Exception):
                        dim_constraints[QName.from_clark(str(dim_clark))] = QName.from_clark(
                            str(mem_clark)
                        )
            options.append(
                ZMemberOption(index=idx, label=label, dimension_constraints=dim_constraints)
            )
            idx += 1
        else:
            for child in node.children:
                _collect(child, accumulated)

    for z_root in z_breakdowns:
        root_accumulated = dict(z_root.aspect_constraints)
        if z_root.children:
            for child in z_root.children:
                _collect(child, root_accumulated)
        else:
            _collect(z_root, {})

    if not options:
        options = [ZMemberOption(index=0, label="Default", dimension_constraints={})]

    return options


def _get_leaf_constraints(header_grid: HeaderGrid) -> list[dict[str, str]]:
    """Return a list of aspect_constraints dicts for each leaf node (in order)."""
    if not header_grid.levels:
        return [{}]
    all_leaves = []
    for level in header_grid.levels:
        for cell in level:
            if cell.is_leaf:
                all_leaves.append(cell.source_node.aspect_constraints)
    return all_leaves if all_leaves else [{}]


def _get_leaf_cells(header_grid: HeaderGrid) -> list[HeaderCell]:
    """Return leaf HeaderCell objects in strict left-to-right (DFS) column order.

    Uses ``header_grid.ordered_leaves`` when available (populated by ``_build_axis_grid``
    for correct ordering with nested roll-up nodes).  Falls back to level-scanning for
    grids built without roll-up tracking (e.g. row axis).
    """
    if header_grid.ordered_leaves:
        return header_grid.ordered_leaves
    if not header_grid.levels:
        return []
    leaves = []
    for level in header_grid.levels:
        for cell in level:
            if cell.is_leaf:
                leaves.append(cell)
    return leaves


def _build_coordinate(
    row_constraints: dict[str, str],
    col_constraints: dict[str, str],
    z_constraints: dict[QName, QName],
    taxonomy: TaxonomyStructure,
) -> CellCoordinate:
    """Merge aspect constraints from X-leaf + Y-leaf + Z-member into a CellCoordinate."""
    concept: QName | None = None
    explicit_dims: dict[QName, QName] = {}

    # Extract concept from row constraints (column wins for concept)
    if _CONCEPT_KEY in col_constraints:
        val = col_constraints[_CONCEPT_KEY]
        with contextlib.suppress(Exception):
            concept = QName.from_clark(str(val))
    elif _CONCEPT_KEY in row_constraints:
        val = row_constraints[_CONCEPT_KEY]
        with contextlib.suppress(Exception):
            concept = QName.from_clark(str(val))

    # Extract explicit dimensions from row constraints
    if _EXPLICIT_DIM_KEY in row_constraints:
        val = row_constraints[_EXPLICIT_DIM_KEY]
        if isinstance(val, dict):
            for dim_clark, mem_clark in val.items():
                with contextlib.suppress(Exception):
                    explicit_dims[QName.from_clark(str(dim_clark))] = QName.from_clark(
                        str(mem_clark)
                    )

    # Extract explicit dimensions from column constraints (column wins for conflicts)
    if _EXPLICIT_DIM_KEY in col_constraints:
        val = col_constraints[_EXPLICIT_DIM_KEY]
        if isinstance(val, dict):
            for dim_clark, mem_clark in val.items():
                with contextlib.suppress(Exception):
                    explicit_dims[QName.from_clark(str(dim_clark))] = QName.from_clark(
                        str(mem_clark)
                    )

    # Add Z-axis dimension constraints
    explicit_dims.update(z_constraints)

    return CellCoordinate(
        concept=concept,
        explicit_dimensions=_strip_default_member_dimensions(explicit_dims, taxonomy),
    )


def _get_dimension_members_in_elr(
    dim_qname: QName,
    elr: str,
    definition: dict,
) -> frozenset | None:
    """Return the set of QNames allowed for dim_qname in the given ELR, or None if unconstrained."""
    arcs = definition.get(elr, [])
    domain: QName | None = None
    for arc in arcs:
        if arc.arcrole == ARCROLE_DIMENSION_DOMAIN and arc.source == dim_qname:
            domain = arc.target
            break
    if domain is None:
        return None
    # Collect all members transitively from the domain
    allowed: set = {domain}
    changed = True
    while changed:
        changed = False
        for arc in arcs:
            if arc.arcrole == ARCROLE_DOMAIN_MEMBER and arc.source in allowed and arc.target not in allowed:
                allowed.add(arc.target)
                changed = True
    return frozenset(allowed)


def _is_cell_excluded(
    coordinate: CellCoordinate,
    taxonomy: TaxonomyStructure,
    table_elr: str = "",
) -> bool:
    """Return True if no closed all-hypercube for the concept allows this cell's dimensions.

    A cell is excluded when its concept belongs to at least one closed hypercube (scoped to
    this table's ELR) but the cell's dimension values fall outside every such hypercube's
    allowed member sets.

    ``table_elr`` is the table's extended_link_role; hypercubes from other tables are ignored.
    """
    if coordinate.concept is None or not coordinate.explicit_dimensions:
        return False

    concept = coordinate.concept
    cell_dims = coordinate.explicit_dimensions

    # Relevant: closed "all" hypercubes where concept is a primary item,
    # scoped to this table's ELR prefix to avoid cross-table contamination.
    elr_prefix = (table_elr + "/") if table_elr else ""
    relevant_hcs = [
        hc for hc in taxonomy.hypercubes
        if hc.arcrole == "all"
        and hc.closed
        and concept in hc.primary_items
        and (not elr_prefix or hc.extended_link_role.startswith(elr_prefix))
    ]

    if not relevant_hcs:
        return False  # No closed constraint → applicable

    for hc in relevant_hcs:
        fits = True
        for dim_qname, member in cell_dims.items():
            if dim_qname not in hc.dimensions:
                continue  # Dimension not constrained in this hypercube

            # Find targetRole for (hc.qname, dim) in this hypercube's ELR
            target_elr = hc.extended_link_role
            for arc in taxonomy.definition.get(hc.extended_link_role, []):
                if (
                    arc.arcrole == ARCROLE_HYPERCUBE_DIMENSION
                    and arc.source == hc.qname
                    and arc.target == dim_qname
                    and arc.target_role
                ):
                    target_elr = arc.target_role
                    break

            allowed = _get_dimension_members_in_elr(dim_qname, target_elr, taxonomy.definition)
            if allowed is not None and member not in allowed:
                fits = False
                break

        if fits:
            return False  # At least one hypercube accepts this cell

    return True  # No hypercube accepts this cell — excluded


def _compute_cell_code(row_fin: str | None, col_fin: str | None) -> str | None:
    """Compute cell code as zero-padded 4-digit sum of row and column fin-codes.

    Per BDE convention: cell_code = int(row_fin) + int(col_fin), formatted as 4 digits.
    Returns None if row_fin is absent or non-integer.
    """
    if not row_fin:
        return None
    try:
        row_num = int(row_fin)
        col_num = int(col_fin) if col_fin else 0
        return f"{row_num + col_num:04d}"
    except ValueError:
        return None


def _build_body(
    row_grid: HeaderGrid,
    col_grid: HeaderGrid,
    z_constraints: dict[QName, QName],
    taxonomy: TaxonomyStructure,
    table_elr: str = "",
) -> list[list[BodyCell]]:
    """Build the body cell grid from row/col constraints + Z member constraints.

    ``row_grid`` must be a DFS-ordered row grid (levels[i] = [cell_i]).
    Abstract row cells get is_applicable=False and an empty coordinate.
    cell_code = row fin_code + col fin_code (both from fin-code role labels).
    """
    col_leaf_cells = _get_leaf_cells(col_grid)

    body: list[list[BodyCell]] = []
    for row_idx, level_cells in enumerate(row_grid.levels):
        row_cell = level_cells[0]
        row_cells: list[BodyCell] = []
        for col_idx, col_cell in enumerate(col_leaf_cells):
            if row_cell.is_abstract:
                cell = BodyCell(
                    row_index=row_idx,
                    col_index=col_idx,
                    coordinate=CellCoordinate(),
                    is_applicable=False,
                )
            else:
                coord = _build_coordinate(
                    row_cell.accumulated_aspect_constraints,
                    col_cell.accumulated_aspect_constraints,
                    z_constraints,
                    taxonomy,
                )
                excluded = _is_cell_excluded(coord, taxonomy, table_elr)
                cell_code = _compute_cell_code(row_cell.fin_code, col_cell.fin_code)
                cell = BodyCell(
                    row_index=row_idx,
                    col_index=col_idx,
                    coordinate=coord,
                    cell_code=cell_code,
                    is_excluded=excluded,
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
        z_constraints: dict[QName, QName] | None = None,
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

            # Validate z_index when explicit z_constraints are not provided.
            if z_constraints is None:
                if z_index < 0 or z_index >= len(z_members):
                    raise ZIndexOutOfRangeError(
                        table_id=table.table_id,
                        requested_z=z_index,
                        max_z=len(z_members) - 1,
                    )
                active_z = z_members[z_index]
                active_constraints = dict(active_z.dimension_constraints)
                active_index = z_index
            else:
                active_constraints = dict(z_constraints)
                active_index = next(
                    (
                        idx
                        for idx, opt in enumerate(z_members)
                        if opt.dimension_constraints == active_constraints
                    ),
                    0,
                )

            # Build X-axis (column) and Y-axis (row) header grids
            col_header = _build_axis_grid(table.x_breakdown, self._taxonomy, lang_pref)
            row_header = _build_row_axis_grid(table.y_breakdown, self._taxonomy, lang_pref)

            # Build body cell grid
            body = _build_body(
                row_header, col_header, active_constraints, self._taxonomy,
                table_elr=table.extended_link_role,
            )

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
            active_z_index=active_index,
            active_z_constraints=active_constraints,
            body=body,
        )

    def populate_facts(
        self,
        layout: ComputedTableLayout,
        instance: XbrlInstance | None,
    ) -> ComputedTableLayout:
        """Return a copy of layout with fact values refreshed from instance."""
        if instance is None:
            for row in layout.body:
                for cell in row:
                    cell.fact_value = None
                    cell.fact_decimals = None
                    cell.is_duplicate = False
            return layout

        from bde_xbrl_editor.table_renderer.fact_mapper import FactMapper  # noqa: PLC0415

        mapper = FactMapper(self._taxonomy)
        for row in layout.body:
            for cell in row:
                result: FactMatchResult = mapper.match(cell.coordinate, instance)
                if result.matched or result.duplicate_count > 0:
                    cell.fact_value = result.fact_value
                    cell.fact_decimals = result.fact_decimals
                    cell.is_duplicate = result.duplicate_count > 1
                else:
                    cell.fact_value = None
                    cell.fact_decimals = None
                    cell.is_duplicate = False
        return layout

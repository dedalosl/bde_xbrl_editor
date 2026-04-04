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

    def _dfs(node: BreakdownNode, depth: int) -> None:
        nonlocal max_depth
        if depth > max_depth:
            max_depth = depth
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
        )
        dfs_cells.append(cell)
        for child in node.children:
            _dfs(child, depth + 1)

    for child in root.children:
        _dfs(child, 0)

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
    Span = number of descendant leaf nodes.
    Level = depth from root.
    """
    levels: list[list[HeaderCell]] = []

    def _collect_all_non_abstract(node: BreakdownNode) -> list[BreakdownNode]:
        result = []
        if not node.is_abstract:
            result.append(node)
        for child in node.children:
            result.extend(_collect_all_non_abstract(child))
        return result

    def _dfs(node: BreakdownNode, level: int) -> None:
        while len(levels) <= level:
            levels.append([])

        all_non_abstract = _collect_all_non_abstract(node)
        is_leaf = not node.is_abstract
        span = len(all_non_abstract)

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
        )
        levels[level].append(cell)

        for child in node.children:
            _dfs(child, level + 1)

    for child in root.children:
        _dfs(child, 0)

    if not levels:
        # Degenerate case: root has no children — treat root itself as a leaf
        levels = [
            [
                HeaderCell(
                    label=_get_label(root, taxonomy, language_preference),
                    rc_code=_get_rc_code(root, taxonomy, language_preference),
                    fin_code=_get_fin_code(root, taxonomy, language_preference),
                    span=1,
                    level=0,
                    is_leaf=True,
                    is_abstract=root.is_abstract,
                    source_node=root,
                )
            ]
        ]

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
            options.append(
                ZMemberOption(index=idx, label=label, dimension_constraints=dim_constraints)
            )
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
    all_leaves = []
    for level in header_grid.levels:
        for cell in level:
            if cell.is_leaf:
                all_leaves.append(cell.source_node.aspect_constraints)
    return all_leaves if all_leaves else [{}]


def _get_leaf_cells(header_grid: HeaderGrid) -> list[HeaderCell]:
    """Return leaf HeaderCell objects for a column grid (level-based) in order."""
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

    return CellCoordinate(concept=concept, explicit_dimensions=explicit_dims)


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
                    row_cell.source_node.aspect_constraints,
                    col_cell.source_node.aspect_constraints,
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
            row_header = _build_row_axis_grid(table.y_breakdown, self._taxonomy, lang_pref)

            # Build body cell grid
            body = _build_body(
                row_header, col_header, active_z.dimension_constraints, self._taxonomy,
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
            active_z_index=z_index,
            body=body,
        )

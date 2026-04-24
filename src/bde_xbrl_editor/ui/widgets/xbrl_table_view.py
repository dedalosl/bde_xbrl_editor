"""XbrlTableView — main compound table rendering widget."""

from __future__ import annotations

import contextlib
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING

from lxml import etree
from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from bde_xbrl_editor.instance.constants import BDE_DIM_NS
from bde_xbrl_editor.table_renderer.errors import TableLayoutError, ZIndexOutOfRangeError
from bde_xbrl_editor.table_renderer.layout_engine import (
    TableLayoutEngine,
    _build_coordinate,
)
from bde_xbrl_editor.table_renderer.models import (
    BodyCell,
    CellCoordinate,
    ComputedTableLayout,
    HeaderCell,
    HeaderGrid,
)
from bde_xbrl_editor.taxonomy.constants import ARCROLE_DOMAIN_MEMBER
from bde_xbrl_editor.taxonomy.models import QName
from bde_xbrl_editor.ui import theme
from bde_xbrl_editor.ui.loading import TableLayoutLoadWorker
from bde_xbrl_editor.ui.widgets.cell_edit_delegate import CellEditDelegate
from bde_xbrl_editor.ui.widgets.column_header import MultiLevelColumnHeader
from bde_xbrl_editor.ui.widgets.row_header import MultiLevelRowHeader
from bde_xbrl_editor.ui.widgets.table_body_model import TableBodyModel
from bde_xbrl_editor.ui.widgets.z_axis_selector import (
    ZAxisDimension,
    ZAxisOption,
    ZAxisSelector,
)

if TYPE_CHECKING:
    from bde_xbrl_editor.instance.editor import InstanceEditor
    from bde_xbrl_editor.instance.models import XbrlInstance
    from bde_xbrl_editor.taxonomy.models import BreakdownNode, TableDefinitionPWD, TaxonomyStructure

_DEFAULT_BODY_COLUMN_WIDTH = 172
_OPEN_ROW_PLACEHOLDER_LABEL = "Open row"
_OPEN_ROW_PLACEHOLDER_RC_CODE = "999"
_AGRUPACION_DIM = QName(namespace=BDE_DIM_NS, local_name="Agrupacion")
_XBRLDI_NS = "http://xbrl.org/2006/xbrldi"
_LEGACY_Z_DIMENSION = QName(
    namespace="urn:bde:xbrl-editor:ui",
    local_name="z-axis-view",
    prefix="ui",
)
_EDIT_TRIGGERS = (
    QTableView.EditTrigger.DoubleClicked
    | QTableView.EditTrigger.EditKeyPressed
    | QTableView.EditTrigger.AnyKeyPressed
    | QTableView.EditTrigger.SelectedClicked
)
_MANUAL_DIMENSION_LABELS_ES = {
    "qLIN": "Código (0011)",
    "qCIN": "Tipo de código (0015)",
}


def _qname_to_clark(qname: QName) -> str:
    return f"{{{qname.namespace}}}{qname.local_name}"


def _table_identity(table: TableDefinitionPWD | None) -> str:
    if table is None:
        return ""
    return table.display_code or table.table_id


def _append_unique_qname(target: list[QName], qname: QName) -> None:
    if qname not in target:
        target.append(qname)


def _empty_layout() -> ComputedTableLayout:
    from bde_xbrl_editor.table_renderer.models import HeaderGrid  # noqa: PLC0415

    empty_grid = HeaderGrid(levels=[[]], leaf_count=0, depth=0)
    return ComputedTableLayout(
        table_id="",
        table_label="",
        column_header=empty_grid,
        row_header=empty_grid,
        z_members=[],
        active_z_index=0,
        body=[],
    )


def _iter_breakdown_nodes(node: BreakdownNode) -> list[BreakdownNode]:
    nodes = [node]
    for child in node.children:
        nodes.extend(_iter_breakdown_nodes(child))
    return nodes


def _display_qname(
    qname: QName,
    taxonomy: TaxonomyStructure,
    language_preference: list[str],
) -> str:
    manual = _MANUAL_DIMENSION_LABELS_ES.get(qname.local_name)
    if manual and "es" in language_preference:
        return manual
    resolved = taxonomy.labels.resolve(qname, language_preference=language_preference)
    if resolved and resolved != str(qname):
        return resolved
    return qname.local_name or str(qname)


def _resolve_prefixed_qname_from_nsmap(raw_qname: str, nsmap: dict[str | None, str]) -> QName | None:
    if raw_qname.startswith("{"):
        return QName.from_clark(raw_qname)
    if ":" not in raw_qname:
        namespace = nsmap.get(None)
        if namespace:
            return QName(namespace=namespace, local_name=raw_qname)
        return QName(namespace="", local_name=raw_qname)
    prefix, local_name = raw_qname.split(":", 1)
    namespace = nsmap.get(prefix)
    if namespace is None:
        return None
    return QName(namespace=namespace, local_name=local_name, prefix=prefix)


def _typed_dimension_text_from_xml(fragment: bytes | None, dim_qname: QName) -> str | None:
    if not fragment:
        return None
    try:
        root = etree.fromstring(fragment)
    except Exception:  # noqa: BLE001
        return None

    for member_el in root.findall(f".//{{{_XBRLDI_NS}}}typedMember"):
        raw_dimension = member_el.get("dimension", "")
        resolved_dimension = _resolve_prefixed_qname_from_nsmap(raw_dimension, member_el.nsmap)
        if resolved_dimension != dim_qname:
            continue
        child = next((node for node in member_el if isinstance(node.tag, str)), None)
        if child is None:
            return (member_el.text or "").strip() or None
        return "".join(child.itertext()).strip() or None
    return None


def _context_typed_dimension_text(context: object, dim_qname: QName) -> str | None:
    typed_value = (getattr(context, "typed_dimensions", {}) or {}).get(dim_qname)
    if isinstance(typed_value, str) and typed_value.strip():
        return typed_value.strip()
    scenario_xml = getattr(context, "scenario_xml", None)
    segment_xml = getattr(context, "segment_xml", None)
    return _typed_dimension_text_from_xml(scenario_xml, dim_qname) or _typed_dimension_text_from_xml(
        segment_xml, dim_qname
    )


def _resolve_typed_dimension_element(
    taxonomy: TaxonomyStructure,
    dim_qname: QName,
) -> QName:
    concept = taxonomy.concepts.get(dim_qname)
    if concept is None or not concept.typed_domain_ref or not concept.schema_path:
        return dim_qname
    typed_domain_ref = concept.typed_domain_ref
    if "#" not in typed_domain_ref:
        return dim_qname
    rel_path, fragment = typed_domain_ref.split("#", 1)
    schema_path = Path(concept.schema_path)
    target_path = (schema_path.parent / rel_path).resolve()
    try:
        root = etree.parse(str(target_path)).getroot()
    except Exception:  # noqa: BLE001
        return dim_qname
    target_ns = root.get("targetNamespace", "")
    for element in root.findall(".//{http://www.w3.org/2001/XMLSchema}element"):
        if element.get("id") == fragment or element.get("name") == fragment:
            local_name = element.get("name") or fragment.split("_", 1)[-1]
            return QName(namespace=target_ns, local_name=local_name)
    return dim_qname


def _enumeration_fact_options(
    taxonomy: TaxonomyStructure | None,
    concept: QName | None,
) -> tuple[str, ...]:
    if taxonomy is None or concept is None:
        return ()
    concept_def = taxonomy.concepts.get(concept)
    if concept_def is None or not concept_def.enumeration_values:
        return ()
    return tuple(concept_def.enumeration_values)


def _apply_taxonomy_fact_options(
    layout: ComputedTableLayout,
    *,
    taxonomy: TaxonomyStructure | None,
) -> ComputedTableLayout:
    for row in layout.body:
        for cell in row:
            if cell.cell_kind != "fact":
                continue
            cell.fact_options = _enumeration_fact_options(taxonomy, cell.coordinate.concept)
    return layout


def _layout_has_open_key_columns(layout: ComputedTableLayout | None) -> bool:
    if layout is None:
        return False
    return any(
        cell.cell_kind == "open-key"
        for row in layout.body
        for cell in row
    )


def _collect_descendant_leaf_constraints(
    node: BreakdownNode,
    inherited_constraints: dict[str, object],
) -> list[dict[str, object]]:
    accumulated = dict(inherited_constraints)
    explicit_dims = dict(accumulated.get("explicitDimension") or {})
    explicit_dims.update(node.aspect_constraints.get("explicitDimension") or {})
    if explicit_dims:
        accumulated["explicitDimension"] = explicit_dims
    if "concept" in node.aspect_constraints:
        accumulated["concept"] = node.aspect_constraints["concept"]

    if not node.children and not node.is_abstract:
        return [accumulated]

    constraints: list[dict[str, object]] = []
    for child in node.children:
        constraints.extend(_collect_descendant_leaf_constraints(child, accumulated))
    return constraints


def _iter_open_row_candidates(
    root: BreakdownNode,
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    seen_signatures: set[tuple[object, ...]] = set()
    row_index = -1

    def _dfs(
        node: BreakdownNode,
        depth: int,
        inherited_constraints: dict[str, object],
    ) -> None:
        nonlocal row_index
        accumulated = dict(inherited_constraints)
        explicit_dims = dict(accumulated.get("explicitDimension") or {})
        explicit_dims.update(node.aspect_constraints.get("explicitDimension") or {})
        if explicit_dims:
            accumulated["explicitDimension"] = explicit_dims
        if "concept" in node.aspect_constraints:
            accumulated["concept"] = node.aspect_constraints["concept"]

        row_index += 1
        for child in node.children:
            _dfs(child, depth + 1, accumulated)

        if not node.is_abstract or not node.children:
            return

        leaf_constraints = _collect_descendant_leaf_constraints(node, inherited_constraints)
        if len(leaf_constraints) < 2:
            return

        concept_values = {str(item.get("concept", "")) for item in leaf_constraints if item.get("concept")}
        if len(concept_values) != 1:
            return

        parent_dims = {
            str(dim): str(member)
            for dim, member in dict(accumulated.get("explicitDimension") or {}).items()
        }
        seen_members: dict[str, set[str]] = {}
        for leaf in leaf_constraints:
            leaf_dims = {
                str(dim): str(member)
                for dim, member in dict(leaf.get("explicitDimension") or {}).items()
            }
            if any(leaf_dims.get(dim) != member for dim, member in parent_dims.items()):
                return
            additional_dims = {
                dim: member for dim, member in leaf_dims.items() if parent_dims.get(dim) != member
            }
            if len(additional_dims) != 1:
                return
            for dim, member in additional_dims.items():
                seen_members.setdefault(dim, set()).add(member)

        varying_dimensions = {dim: members for dim, members in seen_members.items() if len(members) >= 2}
        if len(varying_dimensions) != 1:
            return

        dim_clark, used_members = next(iter(varying_dimensions.items()))
        signature = (
            row_index,
            next(iter(concept_values)),
            dim_clark,
            tuple(sorted(parent_dims.items())),
        )
        if signature in seen_signatures:
            return
        seen_signatures.add(signature)
        candidates.append(
            {
                "anchor_row_index": row_index,
                "insert_after_row_index": row_index,
                "level": depth + 1,
                "label": node.label or _OPEN_ROW_PLACEHOLDER_LABEL,
                "concept_clark": next(iter(concept_values)),
                "dimension_clark": dim_clark,
                "base_constraints": {
                    "concept": next(iter(concept_values)),
                    "explicitDimension": dict(parent_dims),
                },
                "static_member_clarks": used_members,
                "signature": signature,
            }
        )

    for child in root.children:
        _dfs(child, 0, {})
    return candidates


def _rows_from_instance_facts(
    candidate: dict[str, object],
    *,
    instance: XbrlInstance | None,
    taxonomy: TaxonomyStructure,
    z_constraints: dict[QName, QName],
) -> list[str]:
    if instance is None:
        return []

    concept_clark = candidate.get("concept_clark")
    dimension_clark = candidate.get("dimension_clark")
    base_constraints = candidate.get("base_constraints")
    if not isinstance(concept_clark, str) or not isinstance(dimension_clark, str):
        return []
    if not isinstance(base_constraints, dict):
        return []

    with contextlib.suppress(Exception):
        concept_qname = QName.from_clark(concept_clark)
        varying_dim = QName.from_clark(dimension_clark)
    if "concept_qname" not in locals() or "varying_dim" not in locals():
        return []

    base_dims = {}
    raw_base_dims = base_constraints.get("explicitDimension")
    if isinstance(raw_base_dims, dict):
        for dim_clark, member_clark in raw_base_dims.items():
            with contextlib.suppress(Exception):
                base_dims[QName.from_clark(str(dim_clark))] = QName.from_clark(str(member_clark))

    def _normalize_dims(raw_dims: dict[QName, QName]) -> dict[QName, QName]:
        normalized: dict[QName, QName] = {}
        for dim_qname, member_qname in raw_dims.items():
            if dim_qname == _AGRUPACION_DIM:
                continue
            dim_model = taxonomy.dimensions.get(dim_qname)
            if dim_model is not None and dim_model.default_member == member_qname:
                continue
            normalized[dim_qname] = member_qname
        return normalized

    normalized_base_dims = _normalize_dims(base_dims)
    normalized_z_constraints = _normalize_dims(dict(z_constraints))
    dynamic_members: list[str] = []
    static_members = {
        str(member)
        for member in candidate.get("static_member_clarks", set())
        if isinstance(member, str)
    }

    for fact in instance.facts:
        if fact.concept != concept_qname:
            continue
        context = instance.contexts.get(fact.context_ref)
        if context is None:
            continue
        dims = _normalize_dims(dict(getattr(context, "dimensions", {}) or {}))
        if any(dims.get(dim) != member for dim, member in normalized_z_constraints.items()):
            continue
        if any(dims.get(dim) != member for dim, member in normalized_base_dims.items()):
            continue
        varying_member = dims.get(varying_dim)
        if varying_member is None:
            continue
        relevant_dims = set(normalized_base_dims) | set(normalized_z_constraints) | {varying_dim}
        if any(dim not in relevant_dims for dim in dims):
            continue
        member_clark = _qname_to_clark(varying_member)
        if member_clark in static_members or member_clark in dynamic_members:
            continue
        dynamic_members.append(member_clark)

    return dynamic_members


def _iter_open_aspect_row_dimensions(
    root: BreakdownNode,
    taxonomy: TaxonomyStructure,
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for child in root.children:
        dimension_clark = child.aspect_constraints.get("dimensionAspect")
        if child.node_type != "aspect" or not isinstance(dimension_clark, str):
            return []
        try:
            dim_qname = QName.from_clark(dimension_clark)
        except Exception:  # noqa: BLE001
            return []

        dim_model = taxonomy.dimensions.get(dim_qname)
        option_clarks: list[str] = []
        raw_filters = child.aspect_constraints.get("explicitDimensionFilters")
        if isinstance(raw_filters, list):
            for raw_filter in raw_filters:
                if not isinstance(raw_filter, dict):
                    continue
                if raw_filter.get("dimension") != dimension_clark:
                    continue
                for raw_member in raw_filter.get("members", []):
                    if not isinstance(raw_member, dict):
                        continue
                    resolved_members = raw_member.get("resolved_members")
                    if isinstance(resolved_members, list) and resolved_members:
                        for member_clark in resolved_members:
                            if isinstance(member_clark, str) and member_clark not in option_clarks:
                                option_clarks.append(member_clark)
                    else:
                        member_clark = raw_member.get("member")
                        if isinstance(member_clark, str) and member_clark not in option_clarks:
                            option_clarks.append(member_clark)
        elif dim_model is not None:
            option_clarks = [_qname_to_clark(member.qname) for member in dim_model.members]

        candidates.append(
            {
                "dimension_clark": dimension_clark,
                "label": _display_qname(dim_qname, taxonomy, ["es", "en"]),
                "options": tuple(option_clarks),
            }
        )
    return candidates


def _rows_from_instance_aspect_dimensions(
    aspect_dimensions: list[dict[str, object]],
    *,
    layout: ComputedTableLayout,
    instance: XbrlInstance | None,
) -> list[tuple[str, ...]]:
    if instance is None or not aspect_dimensions:
        return []

    x_concepts = {
        cell.coordinate.concept
        for row in layout.body
        for cell in row
        if cell.coordinate.concept is not None
    }
    rows: list[tuple[str, ...]] = []

    for fact in instance.facts:
        if fact.concept not in x_concepts:
            continue
        context = instance.contexts.get(fact.context_ref)
        if context is None:
            continue
        dims = dict(getattr(context, "dimensions", {}) or {})
        row_members: list[str] = []
        for candidate in aspect_dimensions:
            try:
                dim_qname = QName.from_clark(str(candidate["dimension_clark"]))
            except Exception:  # noqa: BLE001
                row_members = []
                break
            if candidate.get("options"):
                member_qname = dims.get(dim_qname)
                if member_qname is None:
                    row_members = []
                    break
                row_members.append(_qname_to_clark(member_qname))
                continue
            typed_text = _context_typed_dimension_text(context, dim_qname)
            if not typed_text:
                row_members = []
                break
            row_members.append(typed_text)
        if row_members:
            row_key = tuple(row_members)
            if row_key not in rows:
                rows.append(row_key)
    return rows


def _find_fact_indexes(
    instance: XbrlInstance,
    coordinate: CellCoordinate,
) -> list[int]:
    if coordinate.concept is None:
        return []

    coord_dims = coordinate.explicit_dimensions or {}
    coord_typed_dims = {
        dim_qname: value.strip()
        for dim_qname, value in (coordinate.typed_dimensions or {}).items()
        if value.strip()
    }
    matches: list[int] = []
    for idx, fact in enumerate(instance.facts):
        if fact.concept != coordinate.concept:
            continue
        context = instance.contexts.get(fact.context_ref)
        if context is None:
            continue
        typed_dim_keys = set((getattr(context, "typed_dimensions", {}) or {}).keys())
        fact_dims = {
            dim_qname: member_qname
            for dim_qname, member_qname in (getattr(context, "dimensions", {}) or {}).items()
            if dim_qname not in typed_dim_keys
        }
        fact_typed_dims = {
            dim_qname: value.strip()
            for dim_qname, value in (getattr(context, "typed_dimensions", {}) or {}).items()
            if value.strip()
        }
        if any(fact_dims.get(dim) != member for dim, member in coord_dims.items()):
            continue
        if any(fact_typed_dims.get(dim) != value for dim, value in coord_typed_dims.items()):
            continue
        if any(dim not in coord_dims for dim in fact_dims):
            continue
        if any(dim not in coord_typed_dims for dim in fact_typed_dims):
            continue
        matches.append(idx)
    return matches


def _ensure_context_ref_for_dimensions(
    instance: XbrlInstance,
    *,
    dimensions: dict[QName, QName],
    typed_dimensions: dict[QName, str] | None = None,
    typed_dimension_elements: dict[QName, QName] | None = None,
    context_element: str = "scenario",
) -> str:
    from bde_xbrl_editor.instance.context_builder import (  # noqa: PLC0415
        build_dimensional_context,
        generate_context_id,
    )

    report_level_dims = {}
    report_level_dim_containers = {}
    for context in instance.contexts.values():
        context_dimensions = getattr(context, "dimensions", {}) or {}
        if _AGRUPACION_DIM not in context_dimensions:
            continue
        dim_containers = getattr(context, "dim_containers", {}) or {}
        report_level_dims = {_AGRUPACION_DIM: context_dimensions[_AGRUPACION_DIM]}
        report_level_dim_containers = {
            _AGRUPACION_DIM: dim_containers.get(_AGRUPACION_DIM, "segment")
        }
        break

    merged_dimensions = dict(report_level_dims)
    merged_dimensions.update(dimensions)
    dim_containers = dict(report_level_dim_containers)
    target_context_element = "segment" if context_element == "segment" else "scenario"
    for dim_qname in dimensions:
        dim_containers[dim_qname] = target_context_element
    for dim_qname in typed_dimensions or {}:
        dim_containers[dim_qname] = target_context_element

    ctx_id = generate_context_id(
        instance.entity,
        instance.period,
        merged_dimensions,
        typed_dimensions,
        dim_containers,
    )
    if ctx_id not in instance.contexts:
        ctx = build_dimensional_context(
            instance.entity,
            instance.period,
            merged_dimensions,
            typed_dimensions=typed_dimensions,
            typed_dimension_elements=typed_dimension_elements,
            context_element=target_context_element,
            dim_containers=dim_containers,
        )
        instance.contexts[ctx_id] = ctx
    return ctx_id


def _open_row_member_options(
    candidate: dict[str, object],
    *,
    taxonomy: TaxonomyStructure,
    instance: XbrlInstance | None,
    z_constraints: dict[QName, QName],
    open_row_members: dict[tuple[object, ...], list[str]],
    current_member_clark: str | None = None,
) -> tuple[QName, ...]:
    dimension_clark = candidate.get("dimension_clark")
    signature = candidate.get("signature")
    if not isinstance(dimension_clark, str) or not isinstance(signature, tuple):
        return ()

    try:
        dim_qname = QName.from_clark(dimension_clark)
    except Exception:  # noqa: BLE001
        return ()

    dim_model = taxonomy.dimensions.get(dim_qname)
    if dim_model is None:
        return ()

    used_members = {
        str(member)
        for member in candidate.get("static_member_clarks", set())
        if isinstance(member, str)
    }
    used_members.update(
        _rows_from_instance_facts(
            candidate,
            instance=instance,
            taxonomy=taxonomy,
            z_constraints=z_constraints,
        )
    )
    used_members.update(open_row_members.get(signature, []))
    if current_member_clark is not None:
        used_members.discard(current_member_clark)

    return tuple(
        member.qname
        for member in dim_model.members
        if _qname_to_clark(member.qname) not in used_members
    )


def _append_open_rows_to_layout(
    layout: ComputedTableLayout,
    *,
    table: TableDefinitionPWD | None,
    taxonomy: TaxonomyStructure | None,
    instance: XbrlInstance | None,
    open_row_members: dict[tuple[object, ...], list[str]],
    include_placeholder_rows: bool,
) -> tuple[ComputedTableLayout, list[dict[str, object]]]:
    if table is None or taxonomy is None:
        return layout, []

    candidates = _iter_open_row_candidates(table.y_breakdown)
    if not candidates:
        return layout, []

    if not layout.column_header.ordered_leaves:
        return layout, []

    row_levels: list[list[HeaderCell]] = list(layout.row_header.levels)
    body_rows: list[list[BodyCell]] = list(layout.body)
    inserted_candidates: list[dict[str, object]] = list(candidates)
    offset = 0
    inserted_dynamic_rows = 0
    fact_mapper = None
    if instance is not None:
        from bde_xbrl_editor.table_renderer.fact_mapper import FactMapper  # noqa: PLC0415

        fact_mapper = FactMapper(taxonomy)

    row_open_keys: dict[int, tuple[tuple[object, ...], str | None]] = {}

    for candidate in candidates:
        member_clarks = list(_rows_from_instance_facts(
            candidate,
            instance=instance,
            taxonomy=taxonomy,
            z_constraints=layout.active_z_constraints,
        ))
        member_clarks.extend(open_row_members.get(candidate["signature"], []))
        deduped_members: list[str] = []
        for member_clark in member_clarks:
            if member_clark not in deduped_members:
                deduped_members.append(member_clark)

        dynamic_rows: list[tuple[str | None, bool]] = []
        for member_clark in deduped_members:
            dynamic_rows.append((member_clark, True))
        if not dynamic_rows:
            continue

        insert_at = int(candidate["insert_after_row_index"]) + 1 + offset
        inserted = 0
        for member_clark, is_dynamic in dynamic_rows:
            label = _OPEN_ROW_PLACEHOLDER_LABEL
            row_constraints = dict(candidate["base_constraints"])
            if member_clark is not None:
                with contextlib.suppress(Exception):
                    member_qname = QName.from_clark(member_clark)
                    label = _display_qname(member_qname, taxonomy, ["es", "en"])
                explicit_dims = dict(row_constraints.get("explicitDimension") or {})
                explicit_dims[str(candidate["dimension_clark"])] = member_clark
                row_constraints["explicitDimension"] = explicit_dims

            header_cell = HeaderCell(
                label=label,
                rc_code=_OPEN_ROW_PLACEHOLDER_RC_CODE if not is_dynamic else None,
                span=1,
                level=int(candidate["level"]),
                is_leaf=is_dynamic,
                is_abstract=not is_dynamic,
                source_node=table.y_breakdown,
                accumulated_aspect_constraints=row_constraints,
            )

            row_levels.insert(insert_at + inserted, [header_cell])

            row_cells: list[BodyCell] = []
            for col_idx, col_cell in enumerate(layout.column_header.ordered_leaves):
                if not is_dynamic:
                    cell = BodyCell(
                        row_index=insert_at + inserted,
                        col_index=col_idx,
                        coordinate=CellCoordinate(),
                        is_applicable=False,
                        cell_kind="placeholder",
                    )
                else:
                    coord = _build_coordinate(
                        row_constraints,
                        col_cell.accumulated_aspect_constraints,
                        layout.active_z_constraints,
                        taxonomy,
                    )
                    cell = BodyCell(
                        row_index=insert_at + inserted,
                        col_index=col_idx,
                        coordinate=coord,
                        cell_code=None,
                    )
                    if fact_mapper is not None:
                        result = fact_mapper.match(cell.coordinate, instance)
                        if result.matched or result.duplicate_count > 0:
                            cell.fact_value = result.fact_value
                            cell.fact_decimals = result.fact_decimals
                            cell.is_duplicate = result.duplicate_count > 1
                    inserted_dynamic_rows += 1
                row_cells.append(cell)

            body_rows.insert(insert_at + inserted, row_cells)
            row_open_keys[insert_at + inserted] = (candidate["signature"], member_clark)
            inserted += 1
        offset += inserted

    should_insert_placeholder = include_placeholder_rows or inserted_dynamic_rows == 0
    if should_insert_placeholder and candidates:
        placeholder_level = min(
            int(candidate["level"]) for candidate in candidates if isinstance(candidate.get("level"), int)
        )
        placeholder_insert_at = max(
            int(candidate["insert_after_row_index"]) for candidate in candidates if isinstance(candidate.get("insert_after_row_index"), int)
        ) + 1 + offset
        header_cell = HeaderCell(
            label=_OPEN_ROW_PLACEHOLDER_LABEL,
            rc_code=_OPEN_ROW_PLACEHOLDER_RC_CODE,
            span=1,
            level=placeholder_level,
            is_leaf=False,
            is_abstract=True,
            source_node=table.y_breakdown,
            accumulated_aspect_constraints={},
        )
        row_levels.insert(placeholder_insert_at, [header_cell])
        placeholder_row: list[BodyCell] = []
        for col_idx, _col_cell in enumerate(layout.column_header.ordered_leaves):
            placeholder_row.append(
                BodyCell(
                    row_index=placeholder_insert_at,
                    col_index=col_idx,
                    coordinate=CellCoordinate(),
                    is_applicable=False,
                    cell_kind="placeholder",
                )
            )
        body_rows.insert(placeholder_insert_at, placeholder_row)
        row_open_keys[placeholder_insert_at] = ((), None)

    key_candidates = list(candidates)
    key_headers: list[HeaderCell] = []
    for candidate in key_candidates:
        try:
            dim_qname = QName.from_clark(str(candidate["dimension_clark"]))
            dim_label = _display_qname(dim_qname, taxonomy, ["es", "en"])
        except Exception:  # noqa: BLE001
            dim_qname = None
            dim_label = str(candidate.get("label") or _OPEN_ROW_PLACEHOLDER_LABEL)
        key_headers.append(
            HeaderCell(
                label=dim_label,
                rc_code=None,
                span=1,
                level=0,
                is_leaf=True,
                is_abstract=False,
                source_node=table.y_breakdown,
            )
        )

    if key_headers:
        new_levels: list[list[HeaderCell]] = []
        new_levels.append(key_headers + layout.column_header.levels[0])
        for level_idx in range(1, layout.column_header.depth):
            placeholders = [
                HeaderCell(
                    label="",
                    rc_code=None,
                    span=1,
                    level=level_idx,
                    is_leaf=False,
                    is_abstract=True,
                    source_node=table.y_breakdown,
                )
                for _ in key_headers
            ]
            new_levels.append(placeholders + layout.column_header.levels[level_idx])

        for row_idx, row in enumerate(body_rows):
            signature, member_clark = row_open_keys.get(row_idx, (None, None))
            key_cells: list[BodyCell] = []
            for key_col_idx, candidate in enumerate(key_candidates):
                try:
                    dim_qname = QName.from_clark(str(candidate["dimension_clark"]))
                except Exception:  # noqa: BLE001
                    dim_qname = None
                if signature == candidate["signature"]:
                    selected_member = None
                    if isinstance(member_clark, str):
                        with contextlib.suppress(Exception):
                            selected_member = QName.from_clark(member_clark)
                    options = _open_row_member_options(
                        candidate,
                        taxonomy=taxonomy,
                        instance=instance,
                        z_constraints=layout.active_z_constraints,
                        open_row_members=open_row_members,
                        current_member_clark=member_clark if isinstance(member_clark, str) else None,
                    )
                    if selected_member is not None and selected_member not in options:
                        options = (selected_member, *options)
                    key_cells.append(
                        BodyCell(
                            row_index=row_idx,
                            col_index=key_col_idx,
                            coordinate=CellCoordinate(),
                            is_applicable=True,
                            cell_kind="open-key",
                            open_key_signature=candidate["signature"],
                            open_key_dimension=dim_qname,
                            open_key_member=selected_member,
                            open_key_options=options,
                        )
                    )
                elif signature == ():
                    options = _open_row_member_options(
                        candidate,
                        taxonomy=taxonomy,
                        instance=instance,
                        z_constraints=layout.active_z_constraints,
                        open_row_members=open_row_members,
                    )
                    key_cells.append(
                        BodyCell(
                            row_index=row_idx,
                            col_index=key_col_idx,
                            coordinate=CellCoordinate(),
                            is_applicable=True,
                            cell_kind="open-key",
                            open_key_signature=candidate["signature"],
                            open_key_dimension=dim_qname,
                            open_key_member=None,
                            open_key_options=options,
                        )
                    )
                else:
                    key_cells.append(
                        BodyCell(
                            row_index=row_idx,
                            col_index=key_col_idx,
                            coordinate=CellCoordinate(),
                            is_applicable=False,
                            cell_kind="placeholder",
                        )
                    )
            body_rows[row_idx] = key_cells + row

        layout = ComputedTableLayout(
            table_id=layout.table_id,
            table_label=layout.table_label,
            column_header=HeaderGrid(
                levels=new_levels,
                leaf_count=layout.column_header.leaf_count + len(key_headers),
                depth=layout.column_header.depth,
                ordered_leaves=key_headers + list(layout.column_header.ordered_leaves),
            ),
            row_header=layout.row_header,
            z_members=list(layout.z_members),
            active_z_index=layout.active_z_index,
            body=body_rows,
            active_z_constraints=dict(layout.active_z_constraints),
        )
    else:
        layout = ComputedTableLayout(
            table_id=layout.table_id,
            table_label=layout.table_label,
            column_header=layout.column_header,
            row_header=layout.row_header,
            z_members=list(layout.z_members),
            active_z_index=layout.active_z_index,
            body=body_rows,
            active_z_constraints=dict(layout.active_z_constraints),
        )

    for row_idx, row in enumerate(body_rows):
        for col_idx, cell in enumerate(row):
            cell.row_index = row_idx
            cell.col_index = col_idx

    return ComputedTableLayout(
        table_id=layout.table_id,
        table_label=layout.table_label,
        column_header=layout.column_header,
        row_header=HeaderGrid(
            levels=row_levels,
            leaf_count=len(row_levels),
            depth=max((row[0].level for row in row_levels if row), default=-1) + 1,
            ordered_leaves=[row[0] for row in row_levels if row],
        ),
        z_members=list(layout.z_members),
        active_z_index=layout.active_z_index,
        body=body_rows,
        active_z_constraints=dict(layout.active_z_constraints),
    ), inserted_candidates


def _append_open_aspect_rows_to_layout(
    layout: ComputedTableLayout,
    *,
    table: TableDefinitionPWD | None,
    taxonomy: TaxonomyStructure | None,
    instance: XbrlInstance | None,
    stored_rows: list[dict[str, str]],
    include_placeholder_rows: bool,
) -> tuple[ComputedTableLayout, list[dict[str, object]], bool]:
    if table is None or taxonomy is None:
        return layout, [], False

    aspect_dimensions = _iter_open_aspect_row_dimensions(table.y_breakdown, taxonomy)
    if not aspect_dimensions:
        return layout, [], False

    key_headers = [
        HeaderCell(
            label=str(candidate["label"]),
            rc_code=None,
            span=1,
            level=0,
            is_leaf=True,
            is_abstract=False,
            source_node=table.y_breakdown,
        )
        for candidate in aspect_dimensions
    ]

    row_maps: list[dict[str, str]] = []
    for row_key in _rows_from_instance_aspect_dimensions(
        aspect_dimensions,
        layout=layout,
        instance=instance,
    ):
        row_map = {
            str(candidate["dimension_clark"]): member_clark
            for candidate, member_clark in zip(aspect_dimensions, row_key, strict=False)
        }
        if row_map not in row_maps:
            row_maps.append(row_map)
    for stored_row in stored_rows:
        normalized = {str(dim_clark): member for dim_clark, member in stored_row.items() if member}
        if normalized and normalized not in row_maps:
            row_maps.append(normalized)
    if include_placeholder_rows or not row_maps:
        row_maps.append({})

    new_levels: list[list[HeaderCell]] = []
    new_levels.append(key_headers + layout.column_header.levels[0])
    for level_idx in range(1, layout.column_header.depth):
        placeholders = [
            HeaderCell(
                label="",
                rc_code=None,
                span=1,
                level=level_idx,
                is_leaf=False,
                is_abstract=True,
                source_node=table.y_breakdown,
            )
            for _ in key_headers
        ]
        new_levels.append(placeholders + layout.column_header.levels[level_idx])

    body_rows: list[list[BodyCell]] = []
    row_levels: list[list[HeaderCell]] = []
    fact_mapper = None
    if instance is not None:
        from bde_xbrl_editor.table_renderer.fact_mapper import FactMapper  # noqa: PLC0415

        fact_mapper = FactMapper(taxonomy)

    for row_idx, row_map in enumerate(row_maps):
        selected_dims: dict[QName, QName] = {}
        selected_typed_dims: dict[QName, str] = {}
        selected_typed_elements: dict[QName, QName] = {}
        row_label = _OPEN_ROW_PLACEHOLDER_LABEL
        is_placeholder = True
        for candidate in aspect_dimensions:
            member_clark = row_map.get(str(candidate["dimension_clark"]))
            if not member_clark:
                continue
            dim_qname = None
            with contextlib.suppress(Exception):
                dim_qname = QName.from_clark(str(candidate["dimension_clark"]))
            if dim_qname is None:
                continue
            if candidate.get("options"):
                with contextlib.suppress(Exception):
                    member_qname = QName.from_clark(member_clark)
                    selected_dims[dim_qname] = member_qname
                    if row_label == _OPEN_ROW_PLACEHOLDER_LABEL:
                        row_label = _display_qname(member_qname, taxonomy, ["es", "en"])
                    is_placeholder = False
            else:
                selected_typed_dims[dim_qname] = member_clark
                selected_typed_elements[dim_qname] = _resolve_typed_dimension_element(taxonomy, dim_qname)
                if row_label == _OPEN_ROW_PLACEHOLDER_LABEL:
                    row_label = member_clark
                is_placeholder = False

        row_levels.append(
            [
                HeaderCell(
                    label=row_label,
                    rc_code=_OPEN_ROW_PLACEHOLDER_RC_CODE if is_placeholder else None,
                    span=1,
                    level=0,
                    is_leaf=not is_placeholder,
                    is_abstract=is_placeholder,
                    source_node=table.y_breakdown,
                )
            ]
        )

        row_cells: list[BodyCell] = []
        for key_col_idx, candidate in enumerate(aspect_dimensions):
            dim_qname = None
            with contextlib.suppress(Exception):
                dim_qname = QName.from_clark(str(candidate["dimension_clark"]))
            member_clark = row_map.get(str(candidate["dimension_clark"]))
            selected_member = None
            selected_text = None
            if member_clark and candidate.get("options"):
                with contextlib.suppress(Exception):
                    selected_member = QName.from_clark(member_clark)
            elif member_clark:
                selected_text = member_clark
            row_cells.append(
                BodyCell(
                    row_index=row_idx,
                    col_index=key_col_idx,
                    coordinate=CellCoordinate(),
                    is_applicable=True,
                    cell_kind="open-key",
                    open_key_signature=("aspect-row", row_idx),
                    open_key_dimension=dim_qname,
                    open_key_member=selected_member,
                    open_key_text=selected_text,
                    open_key_options=tuple(
                        QName.from_clark(str(option_clark))
                        for option_clark in candidate.get("options", ())
                        if isinstance(option_clark, str)
                    ),
                )
            )

        explicit_dims = {
            _qname_to_clark(dim_qname): _qname_to_clark(member_qname)
            for dim_qname, member_qname in selected_dims.items()
        }
        for col_idx, col_cell in enumerate(layout.column_header.ordered_leaves, start=len(aspect_dimensions)):
            if is_placeholder:
                row_cells.append(
                    BodyCell(
                        row_index=row_idx,
                        col_index=col_idx,
                        coordinate=CellCoordinate(),
                        is_applicable=False,
                        cell_kind="placeholder",
                    )
                )
                continue
            coord = _build_coordinate(
                {"explicitDimension": explicit_dims},
                col_cell.accumulated_aspect_constraints,
                layout.active_z_constraints,
                taxonomy,
            )
            coord.typed_dimensions = dict(selected_typed_dims)
            coord.typed_dimension_elements = dict(selected_typed_elements)
            cell = BodyCell(
                row_index=row_idx,
                col_index=col_idx,
                coordinate=coord,
                fact_options=_enumeration_fact_options(taxonomy, coord.concept),
            )
            if fact_mapper is not None:
                result = fact_mapper.match(coord, instance)
                if result.matched or result.duplicate_count > 0:
                    cell.fact_value = result.fact_value
                    cell.fact_decimals = result.fact_decimals
                    cell.is_duplicate = result.duplicate_count > 1
            row_cells.append(cell)
        body_rows.append(row_cells)

    return (
        ComputedTableLayout(
            table_id=layout.table_id,
            table_label=layout.table_label,
            column_header=HeaderGrid(
                levels=new_levels,
                leaf_count=layout.column_header.leaf_count + len(key_headers),
                depth=layout.column_header.depth,
                ordered_leaves=key_headers + list(layout.column_header.ordered_leaves),
            ),
            row_header=HeaderGrid(
                levels=row_levels,
                leaf_count=len(row_levels),
                depth=1,
                ordered_leaves=[row[0] for row in row_levels],
            ),
            z_members=list(layout.z_members),
            active_z_index=layout.active_z_index,
            body=body_rows,
            active_z_constraints=dict(layout.active_z_constraints),
        ),
        aspect_dimensions,
        True,
    )


def _collect_filtered_z_dimensions(table: TableDefinitionPWD) -> list[QName]:
    dimensions: list[QName] = []
    for z_root in table.z_breakdowns:
        for node in _iter_breakdown_nodes(z_root):
            dim_aspect = node.aspect_constraints.get("dimensionAspect")
            if isinstance(dim_aspect, str):
                with contextlib.suppress(Exception):
                    qname = QName.from_clark(dim_aspect)
                    _append_unique_qname(dimensions, qname)
            raw_filters = node.aspect_constraints.get("explicitDimensionFilters")
            if not isinstance(raw_filters, list):
                continue
            for raw_filter in raw_filters:
                if not isinstance(raw_filter, dict):
                    continue
                dim_clark = raw_filter.get("dimension")
                if not isinstance(dim_clark, str):
                    continue
                with contextlib.suppress(Exception):
                    qname = QName.from_clark(dim_clark)
                    _append_unique_qname(dimensions, qname)
    return dimensions


def _expand_filtered_members(
    member_qname: QName,
    *,
    linkrole: str | None,
    axis: str | None,
    arcrole: str | None,
    taxonomy: TaxonomyStructure,
) -> list[QName]:
    if not linkrole or axis != "descendant" or arcrole != ARCROLE_DOMAIN_MEMBER:
        return [member_qname]

    descendants: list[QName] = []
    queue: list[QName] = [member_qname]
    seen: set[QName] = {member_qname}
    arcs = taxonomy.definition.get(linkrole, [])

    while queue:
        current = queue.pop(0)
        for arc in arcs:
            if arc.arcrole != ARCROLE_DOMAIN_MEMBER or arc.source != current:
                continue
            if arc.usable is False or arc.target in seen:
                continue
            seen.add(arc.target)
            descendants.append(arc.target)
            queue.append(arc.target)

    return descendants or [member_qname]


def _collect_filtered_z_members(
    table: TableDefinitionPWD,
    taxonomy: TaxonomyStructure,
) -> dict[QName, list[QName]]:
    filtered_members: dict[QName, list[QName]] = {}

    for z_root in table.z_breakdowns:
        for node in _iter_breakdown_nodes(z_root):
            raw_filters = node.aspect_constraints.get("explicitDimensionFilters")
            if not isinstance(raw_filters, list):
                continue
            for raw_filter in raw_filters:
                if not isinstance(raw_filter, dict) or raw_filter.get("complement") is True:
                    continue
                dimension_clark = raw_filter.get("dimension")
                if not isinstance(dimension_clark, str):
                    continue
                try:
                    dimension_qname = QName.from_clark(dimension_clark)
                except Exception:  # noqa: BLE001
                    continue

                members = raw_filter.get("members")
                if not isinstance(members, list):
                    continue
                collected = filtered_members.setdefault(dimension_qname, [])
                for raw_member in members:
                    if not isinstance(raw_member, dict):
                        continue
                    resolved_members = raw_member.get("resolved_members")
                    if isinstance(resolved_members, list) and resolved_members:
                        expanded = []
                        for resolved_member in resolved_members:
                            if not isinstance(resolved_member, str):
                                continue
                            with contextlib.suppress(Exception):
                                expanded_member = QName.from_clark(resolved_member)
                                if expanded_member not in expanded:
                                    expanded.append(expanded_member)
                    else:
                        member_clark = raw_member.get("member")
                        if not isinstance(member_clark, str):
                            continue
                        try:
                            member_qname = QName.from_clark(member_clark)
                        except Exception:  # noqa: BLE001
                            continue
                        expanded = _expand_filtered_members(
                            member_qname,
                            linkrole=raw_member.get("linkrole")
                            if isinstance(raw_member.get("linkrole"), str)
                            else None,
                            axis=raw_member.get("axis")
                            if isinstance(raw_member.get("axis"), str)
                            else None,
                            arcrole=raw_member.get("arcrole")
                            if isinstance(raw_member.get("arcrole"), str)
                            else None,
                            taxonomy=taxonomy,
                        )
                    for expanded_member in expanded:
                        if expanded_member not in collected:
                            collected.append(expanded_member)

    return filtered_members


def _collect_layout_z_dimensions(layout: ComputedTableLayout | None) -> list[QName]:
    if layout is None:
        return []
    dimensions: list[QName] = []
    for option in layout.z_members:
        for dim_qname in option.dimension_constraints:
            _append_unique_qname(dimensions, dim_qname)
    return dimensions


def _collect_z_dimension_candidates(
    table: TableDefinitionPWD,
    taxonomy: TaxonomyStructure,
    layout: ComputedTableLayout | None = None,
) -> list[QName]:
    dimensions = _collect_filtered_z_dimensions(table)

    for hc in taxonomy.hypercubes:
        if hc.extended_link_role != table.extended_link_role:
            continue
        for dim_qname in hc.dimensions:
            _append_unique_qname(dimensions, dim_qname)

    for dim_qname in _collect_layout_z_dimensions(layout):
        _append_unique_qname(dimensions, dim_qname)

    return dimensions


def _instance_z_assignments_for_table(
    table: TableDefinitionPWD,
    instance: XbrlInstance | None,
) -> dict[QName, QName]:
    if instance is None:
        return {}

    candidate_keys = [table.table_id]
    if table.table_code:
        candidate_keys.append(table.table_code)

    for key in candidate_keys:
        config = instance.dimensional_configs.get(key)
        if config is not None and config.dimension_assignments:
            return dict(config.dimension_assignments)

    return {}


def _collect_instance_used_z_members(
    instance: XbrlInstance | None,
    relevant_dimensions: Iterable[QName],
) -> dict[QName, list[QName]]:
    if instance is None:
        return {}

    relevant = set(relevant_dimensions)
    used: dict[QName, list[QName]] = {}

    for context in instance.contexts.values():
        dimensions = getattr(context, "dimensions", {}) or {}
        for dim_qname, member_qname in dimensions.items():
            if dim_qname not in relevant:
                continue
            collected = used.setdefault(dim_qname, [])
            if member_qname not in collected:
                collected.append(member_qname)

    return used


def _allowed_members_for_dimension(
    dim_qname: QName,
    *,
    table: TableDefinitionPWD,
    taxonomy: TaxonomyStructure,
    layout: ComputedTableLayout | None,
    filtered_members: dict[QName, list[QName]],
) -> list[QName]:
    if filtered_members.get(dim_qname):
        return list(filtered_members[dim_qname])

    dim_model = taxonomy.dimensions.get(dim_qname)
    if dim_model is not None and dim_model.members:
        return [member.qname for member in dim_model.members]

    members: list[QName] = []
    if layout is not None:
        for option in layout.z_members:
            member_qname = option.dimension_constraints.get(dim_qname)
            if member_qname is not None:
                _append_unique_qname(members, member_qname)

    return members


def _derive_initial_z_constraints(
    table: TableDefinitionPWD,
    taxonomy: TaxonomyStructure,
    instance: XbrlInstance | None,
    layout: ComputedTableLayout | None = None,
) -> dict[QName, QName]:
    dimension_candidates = _collect_z_dimension_candidates(table, taxonomy, layout)
    if not dimension_candidates:
        return {}

    filtered_members = _collect_filtered_z_members(table, taxonomy)
    preferred_assignments = _instance_z_assignments_for_table(table, instance)
    used_members = _collect_instance_used_z_members(instance, dimension_candidates)
    selected: dict[QName, QName] = {}

    for dim_qname in dimension_candidates:
        allowed_members = _allowed_members_for_dimension(
            dim_qname,
            table=table,
            taxonomy=taxonomy,
            layout=layout,
            filtered_members=filtered_members,
        )
        chosen_member: QName | None = None
        preferred_member = preferred_assignments.get(dim_qname)
        if preferred_member is not None and (
            not allowed_members or preferred_member in allowed_members
        ):
            chosen_member = preferred_member
        if chosen_member is None:
            for used_member in used_members.get(dim_qname, []):
                if not allowed_members or used_member in allowed_members:
                    chosen_member = used_member
                    break
        if chosen_member is None and allowed_members:
            chosen_member = allowed_members[0]
        if chosen_member is not None:
            selected[dim_qname] = chosen_member

    return selected


def _legacy_z_selector_state(
    layout: ComputedTableLayout,
) -> tuple[list[ZAxisDimension], list[dict[QName, QName]], dict[QName, int]]:
    options: list[ZAxisOption] = []
    member_to_index: dict[QName, int] = {}

    for option in layout.z_members:
        option_qname = QName(
            namespace=_LEGACY_Z_DIMENSION.namespace,
            local_name=f"view_{option.index}",
            prefix=_LEGACY_Z_DIMENSION.prefix,
        )
        member_to_index[option_qname] = option.index
        options.append(
            ZAxisOption(
                member_qname=option_qname,
                label=option.label,
                is_used=option.index == layout.active_z_index,
            )
        )

    selected_member = next(
        (member for member, index in member_to_index.items() if index == layout.active_z_index),
        options[0].member_qname if options else None,
    )

    return [
        ZAxisDimension(
            dimension_qname=_LEGACY_Z_DIMENSION,
            label="View",
            options=tuple(options),
            selected_member=selected_member,
        )
    ], [], member_to_index


def _build_z_axis_selector_state(
    table: TableDefinitionPWD | None,
    taxonomy: TaxonomyStructure | None,
    layout: ComputedTableLayout,
    instance: XbrlInstance | None,
) -> tuple[list[ZAxisDimension], list[dict[QName, QName]], dict[QName, int]]:
    if table is None or taxonomy is None:
        return [], [], {}

    dimension_candidates = _collect_z_dimension_candidates(table, taxonomy, layout)
    if not dimension_candidates:
        if len(layout.z_members) > 1:
            return _legacy_z_selector_state(layout)
        return [], [], {}

    filtered_members = _collect_filtered_z_members(table, taxonomy)
    preferred_assignments = _instance_z_assignments_for_table(table, instance)
    used_members = _collect_instance_used_z_members(instance, dimension_candidates)
    for dim_qname, member_qname in preferred_assignments.items():
        collected = used_members.setdefault(dim_qname, [])
        if member_qname in collected:
            collected.remove(member_qname)
        collected.insert(0, member_qname)
    active_constraints = dict(layout.active_z_constraints) or _derive_initial_z_constraints(
        table,
        taxonomy,
        instance,
        layout,
    )
    valid_combinations = [
        dict(option.dimension_constraints)
        for option in layout.z_members
        if option.dimension_constraints
    ]

    dimensions: list[ZAxisDimension] = []
    for dim_qname in dimension_candidates:
        allowed_members = _allowed_members_for_dimension(
            dim_qname,
            table=table,
            taxonomy=taxonomy,
            layout=layout,
            filtered_members=filtered_members,
        )
        if not allowed_members:
            continue

        selected_member = active_constraints.get(dim_qname)
        ordered_members: list[QName] = []
        if selected_member is not None and selected_member in allowed_members:
            ordered_members.append(selected_member)
        for used_member in used_members.get(dim_qname, []):
            if used_member in allowed_members and used_member not in ordered_members:
                ordered_members.append(used_member)
        for allowed_member in allowed_members:
            if allowed_member not in ordered_members:
                ordered_members.append(allowed_member)

        option_members = tuple(
            ZAxisOption(
                member_qname=member_qname,
                label=_display_qname(member_qname, taxonomy, ["es", "en"]),
                is_used=member_qname in set(used_members.get(dim_qname, [])),
            )
            for member_qname in ordered_members
        )
        dimensions.append(
            ZAxisDimension(
                dimension_qname=dim_qname,
                label=_display_qname(dim_qname, taxonomy, ["es", "en"]),
                options=option_members,
                selected_member=(
                    selected_member
                    if selected_member in {option.member_qname for option in option_members}
                    else preferred_assignments.get(dim_qname)
                ),
            )
        )

    return dimensions, valid_combinations, {}


class XbrlTableView(QFrame):
    """Main compound widget for rendering an XBRL table."""

    cell_selected = Signal(int, int)
    z_index_changed = Signal(int)
    editing_mode_changed = Signal(bool)
    layout_ready = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._taxonomy: TaxonomyStructure | None = None
        self._table: TableDefinitionPWD | None = None
        self._instance: XbrlInstance | None = None
        self._editor: InstanceEditor | None = None
        self._layout: ComputedTableLayout | None = None
        self._open_row_candidates: list[dict[str, object]] = []
        self._open_row_members_by_table: dict[str, dict[tuple[object, ...], list[str]]] = {}
        self._open_aspect_rows_by_table: dict[str, list[dict[str, str]]] = {}
        self._active_z_index: int = 0
        self._active_z_constraints: dict[QName, QName] = {}
        self._editing_enabled: bool = False
        self._pending_table_request: tuple[
            TableDefinitionPWD,
            TaxonomyStructure,
            XbrlInstance | None,
            int,
            dict[QName, QName] | None,
        ] | None = None
        self._table_load_thread: QThread | None = None
        self._table_load_worker: TableLayoutLoadWorker | None = None
        self._table_load_request_id = 0
        self._legacy_z_index_map: dict[QName, int] = {}

        # Layout
        self._outer_layout = QVBoxLayout(self)
        self._outer_layout.setContentsMargins(0, 0, 0, 0)
        self._outer_layout.setSpacing(0)

        self.setStyleSheet(f"QFrame {{ background: {theme.SURFACE_BG}; }}")

        # Table workspace header
        self._table_header = QFrame(self)
        self._table_header.setStyleSheet(
            f"QFrame {{ background: {theme.SURFACE_BG}; }}"
        )
        header_layout = QHBoxLayout(self._table_header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(16)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(2)

        self._title_label = QLabel("No table selected", self._table_header)
        self._title_label.setStyleSheet(
            f"color: {theme.TEXT_MAIN}; font-size: 18px; font-weight: 700; background: transparent;"
        )
        title_col.addWidget(self._title_label)

        self._subtitle_label = QLabel("Select a table from the sidebar to start working.", self._table_header)
        self._subtitle_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 11px; background: transparent;"
        )
        title_col.addWidget(self._subtitle_label)

        self._z_axis_summary_label = QLabel("", self._table_header)
        self._z_axis_summary_label.setWordWrap(True)
        self._z_axis_summary_label.setStyleSheet(
            f"color: {theme.TEXT_SUBTLE}; font-size: 10px; background: transparent;"
        )
        self._z_axis_summary_label.hide()
        title_col.addWidget(self._z_axis_summary_label)

        header_layout.addLayout(title_col, stretch=1)

        status_col = QVBoxLayout()
        status_col.setContentsMargins(0, 0, 0, 0)
        status_col.setSpacing(6)

        self._meta_label = QLabel("", self._table_header)
        self._meta_label.setStyleSheet(
            f"color: {theme.TEXT_SUBTLE}; font-size: 10px; font-weight: 600; background: transparent;"
        )
        self._meta_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_col.addWidget(self._meta_label)

        self._editing_switch = QCheckBox("Editing mode on", self._table_header)
        self._editing_switch.setCursor(Qt.CursorShape.PointingHandCursor)
        self._editing_switch.setStyleSheet(
            f"""
            QCheckBox {{
                color: {theme.TEXT_MAIN};
                font-size: 11px;
                font-weight: 600;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 34px;
                height: 18px;
                border-radius: 9px;
                border: 1px solid {theme.BORDER};
                background: {theme.DISABLED_BG};
            }}
            QCheckBox::indicator:checked {{
                background: {theme.NAV_BG_DEEP};
                border-color: {theme.NAV_BG_DEEP};
            }}
            """
        )
        self._editing_switch.toggled.connect(self._set_editing_enabled)
        status_col.addWidget(self._editing_switch, alignment=Qt.AlignmentFlag.AlignRight)

        self._add_open_row_button = QPushButton("Add row", self._table_header)
        self._add_open_row_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_open_row_button.hide()
        self._add_open_row_button.clicked.connect(self._add_open_row)
        header_layout.addLayout(status_col, stretch=0)

        self._outer_layout.addWidget(self._table_header)

        # Error banner (hidden by default)
        self._error_banner = QLabel(self)
        self._error_banner.setWordWrap(True)
        self._error_banner.setStyleSheet(
            f"background: {theme.WARNING_BG}; color: {theme.WARNING_FG};"
            f" border-bottom: 1px solid {theme.BORDER}; padding: 4px;"
        )
        self._error_banner.hide()
        self._outer_layout.addWidget(self._error_banner)

        # Z-axis selector placeholder
        self._z_selector: ZAxisSelector | None = None

        # Body QTableView
        self._body_view = QTableView(self)
        self._col_header = MultiLevelColumnHeader(parent=self._body_view)
        self._row_header = MultiLevelRowHeader(parent=self._body_view)
        self._body_view.setHorizontalHeader(self._col_header)
        self._body_view.setVerticalHeader(self._row_header)
        self._body_view.horizontalHeader().setDefaultSectionSize(_DEFAULT_BODY_COLUMN_WIDTH)
        self._body_view.horizontalHeader().setMinimumSectionSize(120)
        self._body_view.setStyleSheet(
            f"QTableView {{ background: {theme.CELL_BG}; border: none; }}"
        )
        self._body_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self._outer_layout.addWidget(self._body_view)

        self._table_request_timer = QTimer(self)
        self._table_request_timer.setSingleShot(True)
        self._table_request_timer.timeout.connect(self._apply_requested_table)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def active_z_index(self) -> int:
        return self._active_z_index

    @property
    def active_table_id(self) -> str | None:
        return self._table.table_id if self._table is not None else None

    @property
    def editing_enabled(self) -> bool:
        return self._editing_enabled

    @property
    def active_z_constraints(self) -> dict[QName, QName]:
        return dict(self._active_z_constraints)

    def set_editor(self, editor: InstanceEditor | None) -> None:
        self._editor = editor

    def set_editing_enabled(self, enabled: bool) -> None:
        """Enable or disable inline fact editing for the active instance view."""
        self._set_editing_enabled(enabled)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_table(
        self,
        table: TableDefinitionPWD,
        taxonomy: TaxonomyStructure,
        instance: XbrlInstance | None = None,
    ) -> None:
        """Load and render a table. Clears the previous table if any."""
        self._cancel_async_table_load()
        self._table_request_timer.stop()
        self._pending_table_request = None
        self._taxonomy = taxonomy
        self._table = table
        self._instance = instance
        self._active_z_index = 0
        self._active_z_constraints = _derive_initial_z_constraints(table, taxonomy, instance)

        self._error_banner.hide()

        engine = TableLayoutEngine(taxonomy)
        try:
            layout = engine.compute(
                table,
                instance=instance,
                z_index=0,
                z_constraints=self._active_z_constraints or None,
            )
        except TableLayoutError as exc:
            self._error_banner.setText(f"⚠ Table layout warning: {exc.reason}")
            self._error_banner.show()
            # Try to render with z_index=0 anyway (partial layout)
            try:
                layout = engine.compute(
                    table,
                    instance=None,
                    z_index=0,
                    z_constraints=self._active_z_constraints or None,
                )
            except Exception:  # noqa: BLE001
                return
        except ZIndexOutOfRangeError:
            return

        self._install_layout(layout)

    def request_table(
        self,
        table: TableDefinitionPWD,
        taxonomy: TaxonomyStructure,
        instance: XbrlInstance | None = None,
    ) -> None:
        """Queue a table render for the next UI turn so the shell can paint first."""
        z_index = 0
        z_constraints = _derive_initial_z_constraints(table, taxonomy, instance)
        self._pending_table_request = (table, taxonomy, instance, z_index, z_constraints or None)
        self._show_loading_state(
            table,
            taxonomy,
            instance,
            z_index=z_index,
            z_constraints=z_constraints or None,
            loading_label="Loading table…",
        )
        self._table_request_timer.start(0)

    def set_layout(self, layout: ComputedTableLayout) -> None:
        """Install a pre-computed ComputedTableLayout."""
        self._install_layout(layout)

    def set_z_index(self, z_index: int) -> None:
        """Recompute layout for the given Z-axis member and refresh."""
        if self._table is None or self._taxonomy is None:
            return
        if self._layout is not None and self._layout.active_z_index == z_index:
            return
        self._pending_table_request = (self._table, self._taxonomy, self._instance, z_index, None)
        self._show_loading_state(
            self._table,
            self._taxonomy,
            self._instance,
            z_index=z_index,
            z_constraints=None,
            loading_label="Loading view…",
        )
        self._table_request_timer.start(0)

    def set_z_constraints(self, z_constraints: dict[QName, QName]) -> None:
        """Recompute layout for the given explicit Z-axis assignments and refresh."""
        if self._table is None or self._taxonomy is None:
            return

        normalised_constraints = dict(z_constraints)
        if self._layout is not None and self._layout.active_z_constraints == normalised_constraints:
            return

        self._persist_instance_z_constraints(normalised_constraints)
        self._pending_table_request = (
            self._table,
            self._taxonomy,
            self._instance,
            0,
            normalised_constraints or None,
        )
        self._show_loading_state(
            self._table,
            self._taxonomy,
            self._instance,
            z_index=0,
            z_constraints=normalised_constraints or None,
            loading_label="Loading view…",
        )
        self._table_request_timer.start(0)

    def refresh_instance(self, instance: XbrlInstance | None) -> None:
        """Re-match fact values without recomputing structure."""
        self._instance = instance
        if self._pending_table_request is not None:
            table, taxonomy, _, z_index, z_constraints = self._pending_table_request
            self._pending_table_request = (table, taxonomy, instance, z_index, z_constraints)
        if self._table is None or self._taxonomy is None:
            return
        engine = TableLayoutEngine(self._taxonomy)
        if (
            self._layout is not None
            and self._layout.table_id == self._table.table_id
            and not self._active_z_constraints
            and not _collect_z_dimension_candidates(self._table, self._taxonomy, self._layout)
            and not _layout_has_open_key_columns(self._layout)
        ):
            layout = engine.populate_facts(self._layout, instance)
        else:
            try:
                layout = engine.compute(
                    self._table,
                    instance=instance,
                    z_index=self._active_z_index,
                    z_constraints=self._active_z_constraints or None,
                )
            except (TableLayoutError, ZIndexOutOfRangeError):
                return
        self._install_layout(layout)

    def clear(self) -> None:
        """Remove the current table and show empty state."""
        self._cancel_async_table_load()
        self._table_request_timer.stop()
        self._pending_table_request = None
        self._table = None
        self._taxonomy = None
        self._instance = None
        self._layout = None
        self._active_z_constraints = {}
        self._open_row_candidates = []
        self._open_aspect_rows_by_table = {}
        self._legacy_z_index_map = {}
        self._error_banner.hide()
        self._title_label.setText("No table selected")
        self._subtitle_label.setText("Select a table from the sidebar to start working.")
        self._z_axis_summary_label.clear()
        self._z_axis_summary_label.hide()
        self._meta_label.setText("")
        self._editing_switch.blockSignals(True)
        self._editing_switch.setChecked(False)
        self._editing_switch.blockSignals(False)
        self._editing_switch.setVisible(False)
        self._editing_switch.setText("Editing mode off")
        self._add_open_row_button.hide()
        self._set_editing_enabled(False)
        self._clear_z_selector()
        self._body_view.setModel(TableBodyModel(_empty_layout(), self))

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _apply_requested_table(self) -> None:
        if self._pending_table_request is None:
            return
        table, taxonomy, instance, z_index, z_constraints = self._pending_table_request
        self._pending_table_request = None
        self._start_async_table_load(table, taxonomy, instance, z_index, z_constraints)

    def _start_async_table_load(
        self,
        table: TableDefinitionPWD,
        taxonomy: TaxonomyStructure,
        instance: XbrlInstance | None,
        z_index: int,
        z_constraints: dict[QName, QName] | None,
    ) -> None:
        self._cancel_async_table_load()
        self._table_load_request_id += 1
        request_id = self._table_load_request_id
        worker = TableLayoutLoadWorker(
            request_id=request_id,
            table=table,
            taxonomy=taxonomy,
            instance=instance,
            z_index=z_index,
            z_constraints=z_constraints,
        )
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._on_async_table_loaded, Qt.ConnectionType.QueuedConnection)
        worker.error.connect(self._on_async_table_error, Qt.ConnectionType.QueuedConnection)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._table_load_worker = worker
        self._table_load_thread = thread
        thread.start()

    def _cancel_async_table_load(self) -> None:
        worker = self._table_load_worker
        thread = self._table_load_thread
        self._table_load_worker = None
        self._table_load_thread = None
        if worker is not None:
            worker.cancel()
        if thread is not None and thread.isRunning():
            thread.quit()

    def _finish_async_table_load(self, request_id: int) -> bool:
        if request_id != self._table_load_request_id:
            return False
        thread = self._table_load_thread
        worker = self._table_load_worker
        self._table_load_thread = None
        self._table_load_worker = None
        if worker is not None:
            worker.cancel()
        if thread is not None and thread.isRunning():
            thread.quit()
        return True

    def _on_async_table_loaded(self, request_id: int, layout: ComputedTableLayout, warning: str) -> None:
        if not self._finish_async_table_load(request_id):
            return
        if warning:
            self._error_banner.setText(f"⚠ Table layout warning: {warning}")
            self._error_banner.show()
        else:
            self._error_banner.hide()
        self._install_layout(layout)

    def _on_async_table_error(self, request_id: int, message: str) -> None:
        if not self._finish_async_table_load(request_id):
            return
        self._error_banner.setText(f"⚠ {message}")
        self._error_banner.show()
        self._meta_label.setText("Layout failed")

    def _show_loading_state(
        self,
        table: TableDefinitionPWD,
        taxonomy: TaxonomyStructure,
        instance: XbrlInstance | None,
        *,
        z_index: int,
        z_constraints: dict[QName, QName] | None,
        loading_label: str,
    ) -> None:
        self._taxonomy = taxonomy
        self._table = table
        self._instance = instance
        self._layout = None
        self._active_z_index = z_index
        self._active_z_constraints = dict(z_constraints or {})
        self._error_banner.hide()
        if self._z_selector is not None:
            self._outer_layout.removeWidget(self._z_selector)
            self._z_selector.deleteLater()
            self._z_selector = None
        self._legacy_z_index_map = {}

        title = table.label or table.table_id or "Selected table"
        self._title_label.setText(title)
        subtitle_parts = []
        table_identity = _table_identity(table)
        if table_identity:
            subtitle_parts.append(table_identity)
        subtitle_parts.append(loading_label)
        self._subtitle_label.setText("  |  ".join(subtitle_parts))
        self._z_axis_summary_label.clear()
        self._z_axis_summary_label.hide()
        self._meta_label.setText("Preparing layout…")
        self._editing_switch.setVisible(instance is not None)
        self._editing_switch.setEnabled(False)
        self._editing_switch.blockSignals(True)
        self._editing_switch.setChecked(False)
        self._editing_switch.blockSignals(False)
        self._editing_switch.setText(loading_label)
        self._body_view.setModel(TableBodyModel(_empty_layout(), self))

    def _clear_z_selector(self) -> None:
        if self._z_selector is not None:
            self._outer_layout.removeWidget(self._z_selector)
            self._z_selector.deleteLater()
            self._z_selector = None
        self._legacy_z_index_map = {}

    def _install_layout(self, layout: ComputedTableLayout) -> None:
        stored_aspect_rows = self._open_aspect_rows_by_table.get(layout.table_id, [])
        aspect_layout, aspect_candidates, used_aspect_rows = _append_open_aspect_rows_to_layout(
            layout,
            table=self._table,
            taxonomy=self._taxonomy,
            instance=self._instance,
            stored_rows=stored_aspect_rows,
            include_placeholder_rows=True,
        )
        if used_aspect_rows:
            layout = aspect_layout
            self._open_row_candidates = aspect_candidates
        else:
            open_row_members = self._open_row_members_by_table.get(layout.table_id, {})
            layout, open_row_candidates = _append_open_rows_to_layout(
                layout,
                table=self._table,
                taxonomy=self._taxonomy,
                instance=self._instance,
                open_row_members=open_row_members,
                include_placeholder_rows=self._instance is None,
            )
            self._open_row_candidates = open_row_candidates
        layout = _apply_taxonomy_fact_options(layout, taxonomy=self._taxonomy)
        self._layout = layout
        self._active_z_index = layout.active_z_index
        self._active_z_constraints = dict(layout.active_z_constraints)
        self._refresh_header(layout)

        # Update Z-axis selector
        self._clear_z_selector()

        selector_dimensions, valid_combinations, legacy_map = _build_z_axis_selector_state(
            self._table,
            self._taxonomy,
            layout,
            self._instance,
        )
        self._legacy_z_index_map = legacy_map
        if selector_dimensions:
            self._z_selector = ZAxisSelector(
                selector_dimensions,
                valid_combinations=valid_combinations,
                parent=self,
            )
            self._z_selector.z_selection_changed.connect(self._on_z_selector_changed)
            self._outer_layout.insertWidget(1, self._z_selector)

        # Update body model
        model = TableBodyModel(layout, self)
        if self._taxonomy is not None:
            from bde_xbrl_editor.table_renderer.fact_formatter import FactFormatter  # noqa: PLC0415

            formatter = FactFormatter(self._taxonomy)
            model.set_formatter(formatter, self._taxonomy)
        model.set_open_key_handler(self._handle_open_key_edit)
        self._body_view.setModel(model)

        # Keep delegate in sync with the new layout. If main_window has installed a full
        # CellEditDelegate (with taxonomy + editor), update its layout reference so coordinate
        # lookups stay correct after Z-axis changes. Otherwise install a minimal one for painting.
        existing_delegate = self._body_view.itemDelegate()
        if isinstance(existing_delegate, CellEditDelegate):
            existing_delegate.set_table_layout(layout)
        else:
            self._body_view.setItemDelegate(CellEditDelegate(table_view_widget=self._body_view))

        self._set_editing_enabled(self._editing_enabled and self._instance is not None)

        # Update headers
        self._col_header.set_header_grid(layout.column_header)
        self._row_header.set_header_grid(layout.row_header)

        # Adjust header sizes
        self._body_view.horizontalHeader().setDefaultSectionSize(_DEFAULT_BODY_COLUMN_WIDTH)
        self._body_view.horizontalHeader().setMinimumHeight(
            layout.column_header.depth * 28
        )
        self._body_view.verticalHeader().setMinimumWidth(280)

        # Wire cell selection
        self._body_view.clicked.connect(
            lambda idx: self.cell_selected.emit(idx.row(), idx.column())
        )
        self.layout_ready.emit(layout)

    def _on_z_selector_changed(self, assignments: dict[QName, QName]) -> None:
        if set(assignments) == {_LEGACY_Z_DIMENSION}:
            selected_member = assignments.get(_LEGACY_Z_DIMENSION)
            if selected_member is None:
                return
            index = self._legacy_z_index_map.get(selected_member)
            if index is None:
                return
            self.set_z_index(index)
            self.z_index_changed.emit(index)
            return

        self.set_z_constraints(assignments)
        if self._layout is not None:
            self.z_index_changed.emit(self._layout.active_z_index)

    def _refresh_header(self, layout: ComputedTableLayout) -> None:
        title = layout.table_label or layout.table_id or "Selected table"
        self._title_label.setText(title)

        subtitle_parts = []
        table_identity = _table_identity(self._table)
        if table_identity:
            subtitle_parts.append(table_identity)
        if self._instance is not None:
            subtitle_parts.append(
                "Editing enabled" if self._editing_enabled else "Editing disabled"
            )
        else:
            subtitle_parts.append("Taxonomy browse")
        if self._active_z_constraints:
            selected_parts = []
            if self._taxonomy is not None:
                for dim_qname, member_qname in self._active_z_constraints.items():
                    selected_parts.append(
                        f"{_display_qname(dim_qname, self._taxonomy, ['es', 'en'])}: "
                        f"{_display_qname(member_qname, self._taxonomy, ['es', 'en'])}"
                    )
            if selected_parts:
                subtitle_parts.append("  /  ".join(selected_parts))
        elif layout.z_members and len(layout.z_members) > 1:
            active = min(layout.active_z_index, len(layout.z_members) - 1)
            subtitle_parts.append(f"View {layout.z_members[active].label}")
        self._subtitle_label.setText("  |  ".join(subtitle_parts))
        self._z_axis_summary_label.clear()
        self._z_axis_summary_label.hide()
        self._z_axis_summary_label.setToolTip("")

        row_count = len(layout.body)
        col_count = len(layout.body[0]) if layout.body else 0
        self._meta_label.setText(f"{row_count} rows  |  {col_count} columns")
        self._editing_switch.setVisible(self._instance is not None)
        self._editing_switch.setEnabled(self._instance is not None)
        self._editing_switch.blockSignals(True)
        self._editing_switch.setChecked(self._editing_enabled and self._instance is not None)
        self._editing_switch.blockSignals(False)
        self._editing_switch.setText(
            "Editing mode on" if self._editing_enabled and self._instance is not None else "Editing mode off"
        )
        # Open rows are added directly from the grid's placeholder cells; the
        # header shortcut is intentionally removed from the editor chrome.
        self._add_open_row_button.hide()
        self._add_open_row_button.setEnabled(False)

    def _set_editing_enabled(self, enabled: bool) -> None:
        self._editing_enabled = bool(enabled)
        self._body_view.setEditTriggers(
            _EDIT_TRIGGERS
            if self._editing_enabled and self._instance is not None
            else QTableView.EditTrigger.NoEditTriggers
        )
        self._editing_switch.setText("Editing mode on" if self._editing_enabled else "Editing mode off")
        if self._layout is not None:
            self._refresh_header(self._layout)
        self.editing_mode_changed.emit(self._editing_enabled)

    def _add_open_row(self) -> None:
        if (
            self._table is None
            or self._taxonomy is None
            or self._instance is None
            or not self._open_row_candidates
        ):
            return

        candidate = self._open_row_candidates[0]
        if len(self._open_row_candidates) > 1:
            labels = [str(item.get("label") or _OPEN_ROW_PLACEHOLDER_LABEL) for item in self._open_row_candidates]
            selected_label, accepted = QInputDialog.getItem(
                self,
                "Open row region",
                "Choose where to add the new row:",
                labels,
                0,
                False,
            )
            if not accepted:
                return
            candidate = self._open_row_candidates[labels.index(selected_label)]

        dimension_clark = candidate.get("dimension_clark")
        if not isinstance(dimension_clark, str):
            return

        try:
            dim_qname = QName.from_clark(dimension_clark)
        except Exception:  # noqa: BLE001
            return

        dim_model = self._taxonomy.dimensions.get(dim_qname)
        if dim_model is None or not dim_model.members:
            QMessageBox.information(
                self,
                "Open rows",
                "No candidate members were found for this open row region.",
            )
            return

        used_members = set(candidate.get("static_member_clarks", set()))
        used_members.update(
            _rows_from_instance_facts(
                candidate,
                instance=self._instance,
                taxonomy=self._taxonomy,
                z_constraints=self._active_z_constraints,
            )
        )
        used_members.update(
            self._open_row_members_by_table.get(self._table.table_id, {}).get(candidate["signature"], [])
        )
        available_members = [
            member.qname for member in dim_model.members if str(member.qname) not in used_members
        ]
        if not available_members:
            QMessageBox.information(
                self,
                "Open rows",
                "All available members for this open row region are already in the table.",
            )
            return

        labels = [_display_qname(member, self._taxonomy, ["es", "en"]) for member in available_members]
        selected_label, accepted = QInputDialog.getItem(
            self,
            "Open row member",
            "Choose the member for the new row:",
            labels,
            0,
            False,
        )
        if not accepted:
            return

        selected_member = available_members[labels.index(selected_label)]
        table_rows = self._open_row_members_by_table.setdefault(self._table.table_id, {})
        table_rows.setdefault(candidate["signature"], []).append(str(selected_member))
        self.set_table(self._table, self._taxonomy, self._instance)

    def _handle_open_key_edit(self, row: int, col: int, member_clark: str) -> bool:
        if self._layout is None or self._table is None or self._taxonomy is None or self._instance is None:
            return False
        if row >= len(self._layout.body) or col >= len(self._layout.body[row]):
            return False
        cell = self._layout.body[row][col]
        signature = cell.open_key_signature
        if signature is None:
            return False
        selected_member = None
        expects_member_qname = bool(cell.open_key_options)
        if expects_member_qname:
            try:
                selected_member = QName.from_clark(member_clark)
            except Exception:  # noqa: BLE001
                return False

        if (
            isinstance(signature, tuple)
            and len(signature) == 2
            and signature[0] == "aspect-row"
        ):
            row_map: dict[str, str] = {}
            for row_cell in self._layout.body[row]:
                if row_cell.cell_kind != "open-key" or row_cell.open_key_dimension is None:
                    continue
                if row_cell.open_key_dimension == cell.open_key_dimension:
                    row_map[_qname_to_clark(row_cell.open_key_dimension)] = member_clark
                elif row_cell.open_key_member is not None:
                    row_map[_qname_to_clark(row_cell.open_key_dimension)] = _qname_to_clark(
                        row_cell.open_key_member
                    )
                elif row_cell.open_key_text:
                    row_map[_qname_to_clark(row_cell.open_key_dimension)] = row_cell.open_key_text

            existing_fact_indexes: list[int] = []
            target_context_ref: str | None = None
            target_dimensions: dict[QName, QName] | None = None
            target_typed_dimensions: dict[QName, str] | None = None
            target_typed_elements: dict[QName, QName] | None = None
            for row_cell in self._layout.body[row]:
                if row_cell.cell_kind != "fact" or row_cell.coordinate.concept is None:
                    continue
                if target_dimensions is None:
                    target_dimensions = dict(row_cell.coordinate.explicit_dimensions or {})
                    target_typed_dimensions = dict(row_cell.coordinate.typed_dimensions or {})
                    target_typed_elements = dict(row_cell.coordinate.typed_dimension_elements or {})
                    for dim_clark, selected_clark in row_map.items():
                        with contextlib.suppress(Exception):
                            dim_qname = QName.from_clark(dim_clark)
                            if selected_clark.startswith("{"):
                                target_dimensions[dim_qname] = QName.from_clark(selected_clark)
                                continue
                            target_typed_dimensions[dim_qname] = selected_clark
                            if dim_qname not in target_typed_elements:
                                target_typed_elements[dim_qname] = _resolve_typed_dimension_element(
                                    self._taxonomy,
                                    dim_qname,
                                )
                    old_context = None
                    matches = _find_fact_indexes(self._instance, row_cell.coordinate)
                    if matches:
                        old_context = self._instance.contexts.get(self._instance.facts[matches[0]].context_ref)
                    if old_context is not None:
                        for dim_qname, element_qname in (getattr(old_context, "typed_dimension_elements", {}) or {}).items():
                            target_typed_elements.setdefault(dim_qname, element_qname)
                    target_context_ref = _ensure_context_ref_for_dimensions(
                        self._instance,
                        dimensions=target_dimensions,
                        typed_dimensions=target_typed_dimensions,
                        typed_dimension_elements=target_typed_elements,
                        context_element=getattr(old_context, "context_element", "scenario"),
                    )
                existing_fact_indexes.extend(_find_fact_indexes(self._instance, row_cell.coordinate))

            if existing_fact_indexes and target_context_ref is not None:
                try:
                    if self._editor is not None:
                        self._editor.reassign_facts_context(existing_fact_indexes, target_context_ref)
                    else:
                        for fact_index in set(existing_fact_indexes):
                            self._instance.facts[fact_index].context_ref = target_context_ref
                        if hasattr(self._instance, "_dirty"):
                            self._instance._dirty = True  # type: ignore[attr-defined]  # noqa: SLF001
                except Exception as exc:  # noqa: BLE001
                    QMessageBox.warning(self, "Open rows", str(exc))
                    return False

            table_rows = self._open_aspect_rows_by_table.setdefault(self._table.table_id, [])
            row_id = int(signature[1])
            while len(table_rows) <= row_id:
                table_rows.append({})
            table_rows[row_id] = row_map
            self.set_table(self._table, self._taxonomy, self._instance)
            return True

        existing_fact_indexes: list[int] = []
        target_context_ref: str | None = None
        target_dimensions: dict[QName, QName] | None = None
        for row_cell in self._layout.body[row]:
            if row_cell.cell_kind != "fact" or row_cell.coordinate.concept is None:
                continue
            if target_dimensions is None:
                target_dimensions = dict(row_cell.coordinate.explicit_dimensions or {})
                if cell.open_key_dimension is not None and selected_member is not None:
                    target_dimensions[cell.open_key_dimension] = selected_member
                old_context = None
                matches = _find_fact_indexes(self._instance, row_cell.coordinate)
                if matches:
                    old_context = self._instance.contexts.get(self._instance.facts[matches[0]].context_ref)
                target_context_ref = _ensure_context_ref_for_dimensions(
                    self._instance,
                    dimensions=target_dimensions,
                    context_element=getattr(old_context, "context_element", "scenario"),
                )
            existing_fact_indexes.extend(_find_fact_indexes(self._instance, row_cell.coordinate))

        if existing_fact_indexes and target_context_ref is not None:
            try:
                if self._editor is not None:
                    self._editor.reassign_facts_context(existing_fact_indexes, target_context_ref)
                else:
                    moving = set(existing_fact_indexes)
                    for fact_index in moving:
                        self._instance.facts[fact_index].context_ref = target_context_ref
                    if hasattr(self._instance, "_dirty"):
                        self._instance._dirty = True  # type: ignore[attr-defined]  # noqa: SLF001
            except Exception as exc:  # noqa: BLE001
                QMessageBox.warning(self, "Open rows", str(exc))
                return False

        table_rows = self._open_row_members_by_table.setdefault(self._table.table_id, {})
        current_members = list(table_rows.get(signature, []))
        old_member = str(cell.open_key_member) if cell.open_key_member is not None else None

        if old_member is not None and old_member in current_members:
            current_members.remove(old_member)
        if member_clark not in current_members:
            current_members.append(member_clark)
        table_rows[signature] = current_members
        self.set_table(self._table, self._taxonomy, self._instance)
        return True

    def _persist_instance_z_constraints(self, z_constraints: dict[QName, QName]) -> None:
        if self._instance is None or self._table is None:
            return
        if not z_constraints:
            self._instance.dimensional_configs.pop(self._table.table_id, None)
            if self._table.table_code:
                self._instance.dimensional_configs.pop(self._table.table_code, None)
            return

        from bde_xbrl_editor.instance.models import DimensionalConfiguration  # noqa: PLC0415

        config = DimensionalConfiguration(
            table_id=self._table.table_id,
            dimension_assignments=dict(z_constraints),
        )
        self._instance.dimensional_configs[self._table.table_id] = config
        if self._table.table_code and self._table.table_code in self._instance.dimensional_configs:
            self._instance.dimensional_configs[self._table.table_code] = config

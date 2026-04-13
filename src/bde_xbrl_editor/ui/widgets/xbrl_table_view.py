"""XbrlTableView — main compound table rendering widget."""

from __future__ import annotations

import contextlib
from collections.abc import Iterable
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from bde_xbrl_editor.table_renderer.errors import TableLayoutError, ZIndexOutOfRangeError
from bde_xbrl_editor.table_renderer.layout_engine import TableLayoutEngine
from bde_xbrl_editor.table_renderer.models import ComputedTableLayout
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
    from bde_xbrl_editor.instance.models import XbrlInstance
    from bde_xbrl_editor.taxonomy.models import BreakdownNode, TableDefinitionPWD, TaxonomyStructure

_DEFAULT_BODY_COLUMN_WIDTH = 172
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
    resolved = taxonomy.labels.resolve(qname, language_preference=language_preference)
    if resolved and resolved != str(qname):
        return resolved
    return qname.local_name or str(qname)


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
        self._layout: ComputedTableLayout | None = None
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

    def _set_editing_enabled(self, enabled: bool) -> None:
        self._editing_enabled = bool(enabled) and self._instance is not None
        self._body_view.setEditTriggers(
            _EDIT_TRIGGERS if self._editing_enabled else QTableView.EditTrigger.NoEditTriggers
        )
        self._editing_switch.setText("Editing mode on" if self._editing_enabled else "Editing mode off")
        if self._layout is not None:
            self._refresh_header(self._layout)
        self.editing_mode_changed.emit(self._editing_enabled)

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

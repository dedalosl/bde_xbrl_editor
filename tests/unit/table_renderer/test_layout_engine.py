"""Unit tests for TableLayoutEngine — DFS layout, span values, grid dimensions."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bde_xbrl_editor.table_renderer.errors import ZIndexOutOfRangeError
from bde_xbrl_editor.table_renderer.layout_engine import TableLayoutEngine
from bde_xbrl_editor.taxonomy.models import BreakdownNode, QName, TableDefinitionPWD


def _make_node(
    label: str | None = None,
    rc_code: str | None = None,
    is_abstract: bool = False,
    children: list | None = None,
    aspect_constraints: dict | None = None,
) -> BreakdownNode:
    return BreakdownNode(
        node_type="rule",
        label=label,
        rc_code=rc_code,
        is_abstract=is_abstract,
        children=children or [],
        aspect_constraints=aspect_constraints or {},
    )


def _make_taxonomy() -> MagicMock:
    taxonomy = MagicMock()
    taxonomy.labels.resolve.side_effect = lambda qn, **kw: str(qn)
    taxonomy.concepts = {}
    return taxonomy


def _simple_table(x_root: BreakdownNode, y_root: BreakdownNode) -> TableDefinitionPWD:
    return TableDefinitionPWD(
        table_id="T1",
        label="Test Table",
        extended_link_role="http://example.com/role/T1",
        x_breakdown=x_root,
        y_breakdown=y_root,
    )


class TestAxisDFS:
    """Tests for X/Y axis DFS traversal."""

    def test_single_level_x_axis(self):
        """Three leaf nodes → leaf_count=3, depth=1, all span=1."""
        x_root = _make_node(
            children=[
                _make_node("A"),
                _make_node("B"),
                _make_node("C"),
            ]
        )
        y_root = _make_node(children=[_make_node("R1")])
        taxonomy = _make_taxonomy()
        engine = TableLayoutEngine(taxonomy)
        layout = engine.compute(_simple_table(x_root, y_root))

        assert layout.column_header.leaf_count == 3
        assert layout.column_header.depth == 1
        cells = layout.column_header.levels[0]
        assert len(cells) == 3
        assert all(c.span == 1 for c in cells)
        assert all(c.is_leaf for c in cells)

    def test_two_level_x_axis_span(self):
        """Two-level X-axis: parent with 2 children, parent is non-abstract."""
        x_root = _make_node(
            children=[
                _make_node(
                    "P",
                    children=[
                        _make_node("A"),
                        _make_node("B"),
                    ],
                )
            ]
        )
        y_root = _make_node(children=[_make_node("R")])
        taxonomy = _make_taxonomy()
        engine = TableLayoutEngine(taxonomy)
        layout = engine.compute(_simple_table(x_root, y_root))

        # Non-abstract parent P has span=3 (1 for itself + 2 for its children)
        assert layout.column_header.levels[0][0].span == 3
        assert layout.column_header.levels[0][0].is_leaf
        # Level 1: two children with span=1
        assert len(layout.column_header.levels[1]) == 2
        assert all(c.span == 1 for c in layout.column_header.levels[1])
        # Total leaf count: P + A + B = 3
        assert layout.column_header.leaf_count == 3

    def test_y_axis_symmetric(self):
        """Y-axis DFS is symmetric to X-axis."""
        x_root = _make_node(children=[_make_node("C1")])
        y_root = _make_node(
            children=[
                _make_node("R1"),
                _make_node("R2"),
                _make_node("R3"),
            ]
        )
        taxonomy = _make_taxonomy()
        engine = TableLayoutEngine(taxonomy)
        layout = engine.compute(_simple_table(x_root, y_root))

        assert layout.row_header.leaf_count == 3
        assert layout.row_header.depth == 1

    def test_body_grid_dimensions(self):
        """Body is row_header.leaf_count × column_header.leaf_count."""
        x_root = _make_node(children=[_make_node("C1"), _make_node("C2")])
        y_root = _make_node(children=[_make_node("R1"), _make_node("R2"), _make_node("R3")])
        taxonomy = _make_taxonomy()
        engine = TableLayoutEngine(taxonomy)
        layout = engine.compute(_simple_table(x_root, y_root))

        assert len(layout.body) == 3
        assert all(len(row) == 2 for row in layout.body)

    def test_nested_two_level_span(self):
        """Non-abstract parent with 3 children → parent span=4 (itself + 3 children)."""
        x_root = _make_node(
            children=[
                _make_node(
                    "G",
                    children=[
                        _make_node("A"),
                        _make_node("B"),
                        _make_node("C"),
                    ],
                )
            ]
        )
        y_root = _make_node(children=[_make_node("R")])
        taxonomy = _make_taxonomy()
        engine = TableLayoutEngine(taxonomy)
        layout = engine.compute(_simple_table(x_root, y_root))

        # Non-abstract G has span=4 (1 for itself + 3 for its children)
        assert layout.column_header.levels[0][0].span == 4
        # Total leaf count: G + A + B + C = 4
        assert layout.column_header.leaf_count == 4


class TestRowAxisDFS:
    """Tests for Y-axis DFS row ordering with abstract and non-abstract parent nodes."""

    def test_abstract_and_non_abstract_rows_in_dfs_order(self):
        """Abstract nodes appear as rows in DFS order; they're not skipped."""
        y_root = _make_node(
            is_abstract=True,
            children=[
                _make_node("Total", is_abstract=False, rc_code="r0001"),
                _make_node(
                    "Group",
                    is_abstract=True,
                    children=[
                        _make_node("Child A", is_abstract=False, rc_code="r0002"),
                        _make_node("Child B", is_abstract=False, rc_code="r0003"),
                    ],
                ),
            ],
        )
        x_root = _make_node(children=[_make_node("C")])
        taxonomy = _make_taxonomy()
        engine = TableLayoutEngine(taxonomy)
        layout = engine.compute(_simple_table(x_root, y_root))

        # DFS order: Total, Group, Child A, Child B → 4 rows
        assert layout.row_header.leaf_count == 4
        assert layout.row_header.depth == 2

        rows = [layout.row_header.levels[i][0] for i in range(4)]
        assert rows[0].label == "Total"
        assert rows[0].is_abstract is False
        assert rows[1].label == "Group"
        assert rows[1].is_abstract is True
        assert rows[2].label == "Child A"
        assert rows[3].label == "Child B"

        # Abstract Group row has is_applicable=False body cells
        assert layout.body[1][0].is_applicable is False
        # Non-abstract rows have applicable body cells
        assert layout.body[0][0].is_applicable is True
        assert layout.body[2][0].is_applicable is True

    def test_non_abstract_parent_with_children_appears_before_children(self):
        """Non-abstract parent (total row) appears before its children in DFS."""
        y_root = _make_node(
            children=[
                _make_node(
                    "TOTAL",
                    is_abstract=False,
                    rc_code="r0001",
                    children=[
                        _make_node("Sub A", is_abstract=False, rc_code="r0002"),
                        _make_node("Sub B", is_abstract=False, rc_code="r0003"),
                    ],
                ),
            ]
        )
        x_root = _make_node(children=[_make_node("C")])
        taxonomy = _make_taxonomy()
        engine = TableLayoutEngine(taxonomy)
        layout = engine.compute(_simple_table(x_root, y_root))

        # DFS order: TOTAL, Sub A, Sub B → 3 rows
        assert layout.row_header.leaf_count == 3
        rows = [layout.row_header.levels[i][0] for i in range(3)]
        assert rows[0].label == "TOTAL"
        assert rows[0].rc_code == "r0001"
        assert rows[1].label == "Sub A"
        assert rows[2].label == "Sub B"

        # All 3 rows have applicable body cells
        assert all(layout.body[i][0].is_applicable for i in range(3))

    def test_row_depths_reflect_tree_depth(self):
        """Each row's level attribute reflects its depth in the hierarchy."""
        y_root = _make_node(
            children=[
                _make_node(
                    "L0",
                    is_abstract=True,
                    children=[
                        _make_node(
                            "L1",
                            is_abstract=False,
                            children=[
                                _make_node("L2", is_abstract=False),
                            ],
                        ),
                    ],
                ),
            ]
        )
        x_root = _make_node(children=[_make_node("C")])
        taxonomy = _make_taxonomy()
        engine = TableLayoutEngine(taxonomy)
        layout = engine.compute(_simple_table(x_root, y_root))

        assert layout.row_header.levels[0][0].level == 0  # L0
        assert layout.row_header.levels[1][0].level == 1  # L1
        assert layout.row_header.levels[2][0].level == 2  # L2


class TestZAxis:
    """Tests for Z-axis member extraction."""

    def test_no_z_axis_gives_default(self):
        x_root = _make_node(children=[_make_node("C")])
        y_root = _make_node(children=[_make_node("R")])
        table = TableDefinitionPWD(
            table_id="T1",
            label="T",
            extended_link_role="http://x.com/T1",
            x_breakdown=x_root,
            y_breakdown=y_root,
            z_breakdowns=(),
        )
        taxonomy = _make_taxonomy()
        engine = TableLayoutEngine(taxonomy)
        layout = engine.compute(table)
        assert len(layout.z_members) == 1
        assert layout.active_z_index == 0

    def test_z_index_out_of_range(self):
        x_root = _make_node(children=[_make_node("C")])
        y_root = _make_node(children=[_make_node("R")])
        table = _simple_table(x_root, y_root)
        taxonomy = _make_taxonomy()
        engine = TableLayoutEngine(taxonomy)
        with pytest.raises(ZIndexOutOfRangeError) as exc_info:
            engine.compute(table, z_index=5)
        assert exc_info.value.requested_z == 5


class TestLabelFallback:
    """Tests for label resolution and fallback chain."""

    def test_label_from_node(self):
        """Node with explicit label uses it directly."""
        x_root = _make_node(children=[_make_node("My Label")])
        y_root = _make_node(children=[_make_node("R")])
        taxonomy = _make_taxonomy()
        engine = TableLayoutEngine(taxonomy)
        layout = engine.compute(_simple_table(x_root, y_root))
        assert layout.column_header.levels[0][0].label == "My Label"

    def test_label_falls_back_to_label_resolver(self):
        """Node without label falls back to LabelResolver via concept QName."""
        qn = QName(namespace="http://example.com", local_name="Assets", prefix="ex")
        x_root = _make_node(
            children=[
                _make_node(
                    label=None, aspect_constraints={"concept": f"{{{qn.namespace}}}{qn.local_name}"}
                )
            ]
        )
        y_root = _make_node(children=[_make_node("R")])
        taxonomy = _make_taxonomy()
        taxonomy.labels.resolve.side_effect = None
        taxonomy.labels.resolve.return_value = "Assets (resolved)"
        engine = TableLayoutEngine(taxonomy)
        layout = engine.compute(_simple_table(x_root, y_root))
        assert layout.column_header.levels[0][0].label == "Assets (resolved)"

    def test_rc_code_on_leaf(self):
        """RC code is propagated from BreakdownNode to HeaderCell."""
        x_root = _make_node(children=[_make_node("Col", rc_code="c0010")])
        y_root = _make_node(children=[_make_node("Row", rc_code="r0010")])
        taxonomy = _make_taxonomy()
        engine = TableLayoutEngine(taxonomy)
        layout = engine.compute(_simple_table(x_root, y_root))
        assert layout.column_header.levels[0][0].rc_code == "c0010"
        assert layout.row_header.levels[0][0].rc_code == "r0010"

    def test_rc_code_none_on_branch(self):
        """Branch nodes have rc_code=None."""
        x_root = _make_node(
            children=[
                _make_node(
                    "Parent",
                    rc_code=None,
                    children=[
                        _make_node("Child1", rc_code="c0010"),
                        _make_node("Child2", rc_code="c0020"),
                    ],
                )
            ]
        )
        y_root = _make_node(children=[_make_node("R")])
        taxonomy = _make_taxonomy()
        engine = TableLayoutEngine(taxonomy)
        layout = engine.compute(_simple_table(x_root, y_root))
        assert layout.column_header.levels[0][0].rc_code is None
        assert layout.column_header.levels[1][0].rc_code == "c0010"

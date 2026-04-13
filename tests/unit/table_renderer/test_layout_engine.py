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
        """Two-level X-axis: non-abstract parent with 2 children is a roll-up node."""
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

        # Roll-up node P: spanning header (not a leaf) with span=3 (itself + 2 children)
        assert layout.column_header.levels[0][0].span == 3
        assert not layout.column_header.levels[0][0].is_leaf
        # Level 1: virtual leaf for P + A + B = 3 cells
        assert len(layout.column_header.levels[1]) == 3
        assert all(c.span == 1 for c in layout.column_header.levels[1])
        # First cell is the virtual leaf (parent-first default), last two are children
        assert layout.column_header.levels[1][0].source_node.label == "P"
        assert layout.column_header.levels[1][1].source_node.label == "A"
        assert layout.column_header.levels[1][2].source_node.label == "B"
        # Total leaf count: P-virtual + A + B = 3
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


class TestRollUpNodes:
    """Tests for roll-up node handling (non-abstract nodes with children)."""

    def _make_rollup_node(
        self,
        label: str,
        children: list,
        parent_child_order: str = "parent-first",
    ) -> BreakdownNode:
        return BreakdownNode(
            node_type="rule",
            label=label,
            is_abstract=False,
            children=children,
            parent_child_order=parent_child_order,
        )

    def test_rollup_parent_first_virtual_leaf_before_children(self):
        """parent-first: virtual leaf is the first cell at level 1, before children."""
        rollup = self._make_rollup_node(
            "R0180",
            children=[_make_node("R0185")],
            parent_child_order="parent-first",
        )
        x_root = _make_node(children=[rollup])
        y_root = _make_node(children=[_make_node("Row")])
        taxonomy = _make_taxonomy()
        layout = TableLayoutEngine(taxonomy).compute(_simple_table(x_root, y_root))

        # Level 0: roll-up spanning header (not a leaf, span=2)
        assert len(layout.column_header.levels[0]) == 1
        assert not layout.column_header.levels[0][0].is_leaf
        assert layout.column_header.levels[0][0].span == 2
        # Level 1: [R0180-virtual, R0185] — virtual comes first (parent-first)
        assert len(layout.column_header.levels[1]) == 2
        assert layout.column_header.levels[1][0].is_leaf
        assert layout.column_header.levels[1][0].source_node.label == "R0180"  # virtual
        assert layout.column_header.levels[1][1].source_node.label == "R0185"
        # Leaf count = 2 (virtual + child)
        assert layout.column_header.leaf_count == 2

    def test_rollup_children_first_virtual_leaf_after_children(self):
        """children-first: virtual leaf is the last cell at level 1, after children."""
        rollup = self._make_rollup_node(
            "R0180",
            children=[_make_node("R0185"), _make_node("R0186")],
            parent_child_order="children-first",
        )
        x_root = _make_node(children=[rollup])
        y_root = _make_node(children=[_make_node("Row")])
        taxonomy = _make_taxonomy()
        layout = TableLayoutEngine(taxonomy).compute(_simple_table(x_root, y_root))

        # Level 1: [R0185, R0186, R0180-virtual] — virtual comes last (children-first)
        assert len(layout.column_header.levels[1]) == 3
        assert layout.column_header.levels[1][0].source_node.label == "R0185"
        assert layout.column_header.levels[1][1].source_node.label == "R0186"
        assert layout.column_header.levels[1][2].source_node.label == "R0180"  # virtual last
        assert layout.column_header.levels[1][2].is_leaf
        assert layout.column_header.leaf_count == 3

    def test_rollup_body_has_correct_column_count(self):
        """Body columns match leaf count including the virtual leaf."""
        rollup = self._make_rollup_node(
            "R0180",
            children=[_make_node("R0185")],
        )
        x_root = _make_node(children=[rollup])
        y_root = _make_node(children=[_make_node("Row1"), _make_node("Row2")])
        taxonomy = _make_taxonomy()
        layout = TableLayoutEngine(taxonomy).compute(_simple_table(x_root, y_root))

        # 2 rows × 2 columns (R0180-virtual + R0185)
        assert len(layout.body) == 2
        assert all(len(row) == 2 for row in layout.body)

    def test_nested_rollup_two_levels_ordered_leaves_and_placeholders(self):
        """Two-level roll-up: ordered_leaves in DFS order; placeholder cells align cursor."""
        # Tree: R0010 (rollup) → R0020 (rollup) → R0030 (leaf)
        #                      → R0040 (leaf)
        inner_rollup = BreakdownNode(
            node_type="rule", label="R0020",
            is_abstract=False,
            children=[_make_node("R0030"), _make_node("R0040")],
            parent_child_order="parent-first",
        )
        outer_rollup = BreakdownNode(
            node_type="rule", label="R0010",
            is_abstract=False,
            children=[inner_rollup, _make_node("R0050")],
            parent_child_order="parent-first",
        )
        x_root = _make_node(children=[outer_rollup])
        y_root = _make_node(children=[_make_node("Row")])
        taxonomy = _make_taxonomy()
        layout = TableLayoutEngine(taxonomy).compute(_simple_table(x_root, y_root))

        ch = layout.column_header
        # Level 0: R0010 spanning header (span=5: itself + R0020 + R0030 + R0040 + R0050)
        assert len(ch.levels[0]) == 1
        assert ch.levels[0][0].span == 5
        assert not ch.levels[0][0].is_leaf

        # Level 1: [R0010-virtual, R0020(span=3), R0050]  — parent-first for R0010
        assert len(ch.levels[1]) == 3
        assert ch.levels[1][0].is_rollup_virtual        # R0010 virtual leaf
        assert ch.levels[1][0].source_node.label == "R0010"
        assert ch.levels[1][1].source_node.label == "R0020"
        assert not ch.levels[1][1].is_leaf              # R0020 is a roll-up spanning header
        assert ch.levels[1][1].span == 3
        assert ch.levels[1][2].source_node.label == "R0050"

        # Level 2: [placeholder, R0020-virtual, R0030, R0040]  (placeholder for R0010-virtual)
        assert len(ch.levels[2]) == 4
        assert ch.levels[2][0].is_abstract              # placeholder for R0010-virtual
        assert ch.levels[2][0].span == 1
        assert ch.levels[2][1].is_rollup_virtual        # R0020 virtual leaf
        assert ch.levels[2][2].source_node.label == "R0030"
        assert ch.levels[2][3].source_node.label == "R0040"

        # ordered_leaves: DFS order [R0010-virtual, R0020-virtual, R0030, R0040, R0050]
        leaves = ch.ordered_leaves
        assert len(leaves) == 5
        assert leaves[0].source_node.label == "R0010"   # R0010 virtual leaf, col 0
        assert leaves[1].source_node.label == "R0020"   # R0020 virtual leaf, col 1
        assert leaves[2].source_node.label == "R0030"   # col 2
        assert leaves[3].source_node.label == "R0040"   # col 3
        assert leaves[4].source_node.label == "R0050"   # col 4

        # leaf_count and body dimensions
        assert ch.leaf_count == 5
        assert len(layout.body[0]) == 5


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

    def test_explicit_z_constraints_override_active_coordinate(self):
        x_root = _make_node(children=[_make_node("C")])
        y_root = _make_node(children=[_make_node("R")])
        table = _simple_table(x_root, y_root)
        taxonomy = _make_taxonomy()
        dim = QName(namespace="http://example.com/dim", local_name="DimZ", prefix="dim")
        member = QName(namespace="http://example.com/mem", local_name="MemberA", prefix="mem")

        layout = TableLayoutEngine(taxonomy).compute(
            table,
            z_constraints={dim: member},
        )

        assert layout.active_z_constraints == {dim: member}
        assert layout.body[0][0].coordinate.explicit_dimensions == {dim: member}


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
        """Roll-up node (non-abstract with children) has rc_code=None on the spanning header;
        virtual leaf inherits the same rc_code (None); children follow."""
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
        # Level 0: spanning header for roll-up Parent (rc_code=None)
        assert layout.column_header.levels[0][0].rc_code is None
        # Level 1: [Parent-virtual (rc_code=None), Child1 (rc_code=c0010), Child2 (rc_code=c0020)]
        assert layout.column_header.levels[1][0].rc_code is None   # virtual leaf
        assert layout.column_header.levels[1][1].rc_code == "c0010"
        assert layout.column_header.levels[1][2].rc_code == "c0020"


class TestDimensionalExclusion:
    """Tests for is_excluded flag based on closed hypercube constraints."""

    def _make_hc_taxonomy(
        self,
        concept_qn: QName,
        hc_qn: QName,
        dim_qn: QName,
        allowed_members: list[QName],
    ):
        """Build a mock taxonomy with one closed all-hypercube and targetRole member list."""
        from unittest.mock import MagicMock
        from bde_xbrl_editor.taxonomy.models import DefinitionArc, DimensionModel, HypercubeModel

        taxonomy = MagicMock()
        taxonomy.labels.resolve.side_effect = lambda qn, **kw: str(qn)
        taxonomy.concepts = {}

        domain_qn = QName(namespace="http://x.com", local_name="domain")
        # Use sub-roles of the table ELR so the prefix filter works:
        # table ELR = "http://example.com/role/T1" → hypercube ELR = ".../T1/1"
        primary_elr = "http://example.com/role/T1/1"
        target_elr = "http://example.com/role/T1/2"

        # hypercube-dimension arc with targetRole
        hc_dim_arc = DefinitionArc(
            arcrole="http://xbrl.org/int/dim/arcrole/hypercube-dimension",
            source=hc_qn,
            target=dim_qn,
            order=1.0,
            extended_link_role=primary_elr,
            target_role=target_elr,
        )
        # dimension-domain arc in target ELR
        dim_domain_arc = DefinitionArc(
            arcrole="http://xbrl.org/int/dim/arcrole/dimension-domain",
            source=dim_qn,
            target=domain_qn,
            order=1.0,
            extended_link_role=target_elr,
        )
        # domain-member arcs in target ELR
        member_arcs = [
            DefinitionArc(
                arcrole="http://xbrl.org/int/dim/arcrole/domain-member",
                source=domain_qn,
                target=m,
                order=float(i + 1),
                extended_link_role=target_elr,
            )
            for i, m in enumerate(allowed_members)
        ]

        taxonomy.definition = {
            primary_elr: [hc_dim_arc],
            target_elr: [dim_domain_arc] + member_arcs,
        }
        taxonomy.hypercubes = [
            HypercubeModel(
                qname=hc_qn,
                arcrole="all",
                closed=True,
                context_element="segment",
                primary_items=(concept_qn,),
                dimensions=(dim_qn,),
                extended_link_role=primary_elr,
            )
        ]
        return taxonomy

    def test_cell_with_allowed_member_not_excluded(self):
        concept = QName(namespace="http://x.com", local_name="C")
        hc = QName(namespace="http://x.com", local_name="Hc")
        dim = QName(namespace="http://x.com", local_name="Dim")
        allowed = QName(namespace="http://x.com", local_name="m1")

        taxonomy = self._make_hc_taxonomy(concept, hc, dim, [allowed])
        engine = TableLayoutEngine(taxonomy)

        col_node = _make_node(
            aspect_constraints={"concept": f"{{{concept.namespace}}}{concept.local_name}"}
        )
        row_node = _make_node(
            aspect_constraints={
                "explicitDimension": {
                    f"{{{dim.namespace}}}{dim.local_name}": f"{{{allowed.namespace}}}{allowed.local_name}"
                }
            }
        )
        x_root = _make_node(children=[col_node])
        y_root = _make_node(children=[row_node])
        layout = engine.compute(_simple_table(x_root, y_root))
        assert layout.body[0][0].is_excluded is False

    def test_cell_with_excluded_member_is_excluded(self):
        concept = QName(namespace="http://x.com", local_name="C")
        hc = QName(namespace="http://x.com", local_name="Hc")
        dim = QName(namespace="http://x.com", local_name="Dim")
        allowed = QName(namespace="http://x.com", local_name="m1")
        forbidden = QName(namespace="http://x.com", local_name="m_bad")

        taxonomy = self._make_hc_taxonomy(concept, hc, dim, [allowed])
        engine = TableLayoutEngine(taxonomy)

        col_node = _make_node(
            aspect_constraints={"concept": f"{{{concept.namespace}}}{concept.local_name}"}
        )
        row_node = _make_node(
            aspect_constraints={
                "explicitDimension": {
                    f"{{{dim.namespace}}}{dim.local_name}": f"{{{forbidden.namespace}}}{forbidden.local_name}"
                }
            }
        )
        x_root = _make_node(children=[col_node])
        y_root = _make_node(children=[row_node])
        layout = engine.compute(_simple_table(x_root, y_root))
        assert layout.body[0][0].is_excluded is True

    def test_cell_with_no_hypercubes_not_excluded(self):
        """When no closed hypercubes exist for the concept, cell is never excluded."""
        taxonomy = _make_taxonomy()
        taxonomy.hypercubes = []
        taxonomy.definition = {}
        engine = TableLayoutEngine(taxonomy)

        concept = QName(namespace="http://x.com", local_name="C")
        col_node = _make_node(
            aspect_constraints={"concept": f"{{{concept.namespace}}}{concept.local_name}"}
        )
        row_node = _make_node(label="R")
        x_root = _make_node(children=[col_node])
        y_root = _make_node(children=[row_node])
        layout = engine.compute(_simple_table(x_root, y_root))
        assert layout.body[0][0].is_excluded is False

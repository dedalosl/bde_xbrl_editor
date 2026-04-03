"""ActivitySidebar — VS Code-style collapsible left sidebar.

A narrow icon bar (44 px) selects between panel views.
Clicking the active icon collapses the panel to give the table more space.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bde_xbrl_editor.taxonomy.models import TaxonomyStructure

# ---------------------------------------------------------------------------
# Activity bar constants
# ---------------------------------------------------------------------------

_BAR_W = 44          # icon bar width in px
_PANEL_W = 260       # content panel width in px

_ICONS = ["⊡", "⊞", "⚡", "≡", "⟷"]
_TIPS = ["DTS Files", "Tables", "Validations", "Concepts", "Definition Linkbase"]

_BAR_STYLE = """
    QWidget#ActivityBar {
        background: #1E3A5F;
        border-right: 1px solid #16304F;
    }
"""

_BTN_STYLE = """
    QToolButton {
        background: transparent;
        border: none;
        color: #7BA4C8;
        font-size: 20px;
        padding: 6px;
        border-radius: 4px;
    }
    QToolButton:hover {
        color: #FFFFFF;
        background: rgba(255,255,255,0.10);
    }
    QToolButton:checked {
        color: #FFFFFF;
        background: rgba(255,255,255,0.18);
        border-left: 3px solid #5BA3F5;
    }
"""

_PANEL_STYLE = """
    QWidget#PanelRoot {
        background: #F5F7FA;
        border-right: 1px solid #C8D4E5;
    }
"""

_SECTION_HDR_STYLE = (
    "background: #1E3A5F; color: #FFFFFF; font-weight: bold;"
    " font-size: 11px; padding: 6px 10px; letter-spacing: 1px;"
)

_COLLAPSIBLE_HDR_STYLE = (
    "QPushButton { text-align: left; padding: 5px 8px; background: #2B5287;"
    " color: #FFFFFF; font-size: 11px; font-weight: bold; border: none; }"
    "QPushButton:hover { background: #3A6AA8; }"
)

_LIST_STYLE = """
    QListWidget {
        border: none;
        background: #FFFFFF;
        font-size: 12px;
        color: #1E3A5F;
        outline: none;
    }
    QListWidget::item {
        padding: 5px 8px;
        border-bottom: 1px solid #E8EDF5;
    }
    QListWidget::item:selected {
        background: #1E3A5F;
        color: #FFFFFF;
    }
    QListWidget::item:hover:!selected {
        background: #DCE8F5;
    }
"""

_TREE_STYLE = """
    QTreeWidget {
        border: none;
        background: #FFFFFF;
        font-size: 11px;
        color: #1E3A5F;
        outline: none;
    }
    QTreeWidget::item {
        padding: 2px 4px;
    }
    QTreeWidget::item:selected {
        background: #1E3A5F;
        color: #FFFFFF;
    }
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _CollapsibleSection(QWidget):
    """A collapsible section with a toggle-button header and a body widget."""

    def __init__(self, title: str, body: QWidget, expanded: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._btn = QPushButton(f"▾  {title}")
        self._btn.setStyleSheet(_COLLAPSIBLE_HDR_STYLE)
        self._btn.setCheckable(True)
        self._btn.setChecked(True)
        self._btn.clicked.connect(self._toggle)
        layout.addWidget(self._btn)

        self._body = body
        layout.addWidget(body)

        if not expanded:
            self._toggle(False)

    def _toggle(self, checked: bool) -> None:
        self._body.setVisible(checked)
        arrow = "▾" if checked else "▸"
        text = self._btn.text()[2:]  # strip old arrow + space
        self._btn.setText(f"{arrow}  {text}")


# ---------------------------------------------------------------------------
# Panel: DTS Files
# ---------------------------------------------------------------------------

class _DtsFilesPanel(QWidget):
    def __init__(self, taxonomy: TaxonomyStructure, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QLabel("DTS FILES")
        hdr.setStyleSheet(_SECTION_HDR_STYLE)
        layout.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        schema_tree = self._build_tree(taxonomy.schema_files)
        schema_section = _CollapsibleSection(
            f"Schema files  ({len(taxonomy.schema_files)})", schema_tree
        )
        inner_layout.addWidget(schema_section)

        lb_files = taxonomy.linkbase_files
        lb_tree = self._build_tree(lb_files)
        lb_section = _CollapsibleSection(
            f"Linkbase files  ({len(lb_files)})", lb_tree, expanded=False
        )
        inner_layout.addWidget(lb_section)
        inner_layout.addStretch(1)

        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)

    @staticmethod
    def _build_tree(paths: list[Path] | tuple[Path, ...] | object) -> QTreeWidget:
        tree = QTreeWidget()
        tree.setHeaderHidden(True)
        tree.setStyleSheet(_TREE_STYLE)
        tree.setIndentation(14)

        by_dir: dict[str, list[str]] = {}
        file_list: list[Path] = list(paths) if paths else []
        for p in file_list:
            key = p.parent.name or str(p.parent)
            by_dir.setdefault(key, []).append(p.name)

        for dir_name in sorted(by_dir):
            parent_item = QTreeWidgetItem([dir_name])
            parent_item.setExpanded(False)
            for fname in sorted(by_dir[dir_name]):
                child = QTreeWidgetItem([fname])
                parent_item.addChild(child)
            tree.addTopLevelItem(parent_item)

        return tree


# ---------------------------------------------------------------------------
# Panel: Tables
# ---------------------------------------------------------------------------

class _TablesPanel(QWidget):
    table_selected = Signal(object)  # TableDefinitionPWD

    def __init__(self, taxonomy: TaxonomyStructure, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        meta = taxonomy.metadata

        hdr = QLabel(f"TABLES  ({len(taxonomy.tables)})")
        hdr.setStyleSheet(_SECTION_HDR_STYLE)
        layout.addWidget(hdr)

        # Table list
        self._list = QListWidget()
        self._list.setStyleSheet(_LIST_STYLE)
        for table in taxonomy.tables:
            item = QListWidgetItem(f"{table.table_id}\n{table.label}")
            item.setData(Qt.ItemDataRole.UserRole, table)
            self._list.addItem(item)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list, stretch=1)

        # Taxonomy info (collapsible, collapsed by default)
        info_widget = self._build_info_widget(meta, taxonomy)
        info_section = _CollapsibleSection("Taxonomy info", info_widget, expanded=False)
        layout.addWidget(info_section)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        table = item.data(Qt.ItemDataRole.UserRole)
        if table is not None:
            self.table_selected.emit(table)

    def select_first(self) -> None:
        if self._list.count() > 0:
            first = self._list.item(0)
            self._list.setCurrentItem(first)
            self._on_item_clicked(first)

    @staticmethod
    def _build_info_widget(meta: object, taxonomy: TaxonomyStructure) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        key_style = "color: #5A7FA8; font-size: 10px; font-weight: bold;"
        val_style = "color: #1E3A5F; font-size: 11px;"

        def _row(key: str, value: str) -> None:
            kl = QLabel(key)
            kl.setStyleSheet(key_style)
            layout.addWidget(kl)
            vl = QLabel(value)
            vl.setStyleSheet(val_style)
            vl.setWordWrap(True)
            vl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(vl)

        _row("NAME", meta.name)
        _row("VERSION", meta.version)
        _row("PUBLISHER", meta.publisher)
        _row("ENTRY POINT", str(meta.entry_point_path.name))
        _row("LOADED AT", meta.loaded_at.strftime("%Y-%m-%d %H:%M"))
        _row("LANGUAGES", ", ".join(meta.declared_languages) or "—")
        _row("CONCEPTS", str(len(taxonomy.concepts)))
        _row("TABLES", str(len(taxonomy.tables)))
        layout.addSpacing(4)
        return w


# ---------------------------------------------------------------------------
# Panel: Validations
# ---------------------------------------------------------------------------

class _ValidationsPanel(QWidget):
    def __init__(self, taxonomy: TaxonomyStructure, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QLabel("VALIDATIONS (Formula)")
        hdr.setStyleSheet(_SECTION_HDR_STYLE)
        layout.addWidget(hdr)

        assertions = list(taxonomy.formula_assertion_set.assertions)

        if not assertions:
            lbl = QLabel("No formula assertions in this taxonomy.")
            lbl.setStyleSheet("color: #7BA4C8; font-size: 11px; padding: 12px;")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
            layout.addStretch(1)
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        from bde_xbrl_editor.taxonomy.models import (  # noqa: PLC0415
            ConsistencyAssertionDefinition,
            ExistenceAssertionDefinition,
            ValueAssertionDefinition,
        )

        groups: dict[str, list] = {
            "Value Assertions": [],
            "Existence Assertions": [],
            "Consistency Assertions": [],
            "Other": [],
        }
        for a in assertions:
            if isinstance(a, ValueAssertionDefinition):
                groups["Value Assertions"].append(a)
            elif isinstance(a, ExistenceAssertionDefinition):
                groups["Existence Assertions"].append(a)
            elif isinstance(a, ConsistencyAssertionDefinition):
                groups["Consistency Assertions"].append(a)
            else:
                groups["Other"].append(a)

        for group_name, items in groups.items():
            if not items:
                continue
            lst = QListWidget()
            lst.setStyleSheet(_LIST_STYLE)
            lst.setMaximumHeight(min(len(items) * 30 + 4, 200))
            for a in items:
                label = getattr(a, "label", None) or a.assertion_id
                lst.addItem(QListWidgetItem(f"{a.assertion_id}  {label or ''}".strip()))
            section = _CollapsibleSection(f"{group_name}  ({len(items)})", lst, expanded=False)
            inner_layout.addWidget(section)

        inner_layout.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)


# ---------------------------------------------------------------------------
# Panel: Concepts
# ---------------------------------------------------------------------------

class _ConceptsPanel(QWidget):
    def __init__(self, taxonomy: TaxonomyStructure, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QLabel(f"CONCEPTS  ({len(taxonomy.concepts)})")
        hdr.setStyleSheet(_SECTION_HDR_STYLE)
        layout.addWidget(hdr)

        search = QLineEdit()
        search.setPlaceholderText("Filter concepts…")
        search.setStyleSheet(
            "QLineEdit { border: none; border-bottom: 1px solid #C8D4E5;"
            " padding: 5px 8px; font-size: 11px; color: #1E3A5F; background: #FFFFFF; }"
        )
        layout.addWidget(search)

        self._all_names = sorted(
            (str(q) for q in taxonomy.concepts),
            key=lambda s: s.lower(),
        )

        self._list = QListWidget()
        self._list.setStyleSheet(_LIST_STYLE)
        self._list.addItems(self._all_names)
        layout.addWidget(self._list, stretch=1)

        search.textChanged.connect(self._filter)

    def _filter(self, text: str) -> None:
        lower = text.lower()
        self._list.clear()
        self._list.addItems(
            name for name in self._all_names if lower in name.lower()
        )


# ---------------------------------------------------------------------------
# Panel: Definition Linkbase
# ---------------------------------------------------------------------------

class _DefinitionPanel(QWidget):
    def __init__(self, taxonomy: TaxonomyStructure, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QLabel("DEFINITION LINKBASE")
        hdr.setStyleSheet(_SECTION_HDR_STYLE)
        layout.addWidget(hdr)

        definition = taxonomy.definition
        if not definition:
            lbl = QLabel("No definition arcs in this taxonomy.")
            lbl.setStyleSheet("color: #7BA4C8; font-size: 11px; padding: 12px;")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
            layout.addStretch(1)
            return

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        for arcrole, arcs in definition.items():
            tree = QTreeWidget()
            tree.setHeaderHidden(True)
            tree.setStyleSheet(_TREE_STYLE)
            tree.setIndentation(14)

            # Group arcs by source
            by_source: dict[str, list[str]] = {}
            for arc in arcs:
                src = str(getattr(arc, "source", arc))
                tgt = str(getattr(arc, "target", ""))
                by_source.setdefault(src, []).append(tgt)

            for src, targets in by_source.items():
                src_item = QTreeWidgetItem([src])
                src_item.setExpanded(False)
                for tgt in targets:
                    src_item.addChild(QTreeWidgetItem([f"→ {tgt}"]))
                tree.addTopLevelItem(src_item)

            short_role = arcrole.split("/")[-1] if "/" in arcrole else arcrole
            section = _CollapsibleSection(
                f"{short_role}  ({len(arcs)})", tree, expanded=False
            )
            inner_layout.addWidget(section)

        inner_layout.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)


# ---------------------------------------------------------------------------
# ActivitySidebar
# ---------------------------------------------------------------------------

class ActivitySidebar(QWidget):
    """VS Code-style sidebar: narrow icon bar + collapsible content panel.

    Clicking the active icon collapses the panel to free space for the table.
    """

    table_selected = Signal(object)  # TableDefinitionPWD

    def __init__(self, taxonomy: TaxonomyStructure, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._taxonomy = taxonomy
        self._active_index: int | None = None

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Activity bar (icon strip) ──────────────────────────────────
        self._bar = QWidget()
        self._bar.setObjectName("ActivityBar")
        self._bar.setFixedWidth(_BAR_W)
        self._bar.setStyleSheet(_BAR_STYLE)
        bar_layout = QVBoxLayout(self._bar)
        bar_layout.setContentsMargins(0, 8, 0, 8)
        bar_layout.setSpacing(4)
        bar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._buttons: list[QToolButton] = []
        for i, (icon, tip) in enumerate(zip(_ICONS, _TIPS, strict=True)):
            btn = QToolButton()
            btn.setText(icon)
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.setFixedSize(_BAR_W, _BAR_W)
            btn.setStyleSheet(_BTN_STYLE)
            btn.clicked.connect(lambda checked, idx=i: self._on_button_clicked(idx))
            bar_layout.addWidget(btn)
            self._buttons.append(btn)

        bar_layout.addStretch(1)
        root_layout.addWidget(self._bar)

        # ── Content panel (stacked) ────────────────────────────────────
        self._panel_root = QWidget()
        self._panel_root.setObjectName("PanelRoot")
        self._panel_root.setStyleSheet(_PANEL_STYLE)
        panel_layout = QVBoxLayout(self._panel_root)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        self._stack = QStackedWidget()
        panel_layout.addWidget(self._stack)

        self._tables_panel = _TablesPanel(taxonomy)
        self._tables_panel.table_selected.connect(self.table_selected)

        self._stack.addWidget(_DtsFilesPanel(taxonomy))       # 0
        self._stack.addWidget(self._tables_panel)             # 1
        self._stack.addWidget(_ValidationsPanel(taxonomy))    # 2
        self._stack.addWidget(_ConceptsPanel(taxonomy))       # 3
        self._stack.addWidget(_DefinitionPanel(taxonomy))     # 4

        root_layout.addWidget(self._panel_root)

        # Start with Tables panel visible
        self._activate(1)
        self.setFixedWidth(_BAR_W + _PANEL_W)

    # ------------------------------------------------------------------
    # Toggle logic
    # ------------------------------------------------------------------

    def _on_button_clicked(self, idx: int) -> None:
        if self._active_index == idx and self._panel_root.isVisible():
            # Clicking the already-active button → collapse panel
            self._panel_root.setVisible(False)
            self._buttons[idx].setChecked(False)
            self._active_index = None
            self.setFixedWidth(_BAR_W)
        else:
            self._activate(idx)

    def _activate(self, idx: int) -> None:
        self._active_index = idx
        self._stack.setCurrentIndex(idx)
        self._panel_root.setVisible(True)
        self.setFixedWidth(_BAR_W + _PANEL_W)
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == idx)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select_first_table(self) -> None:
        """Activate the Tables panel and select the first table."""
        self._activate(1)
        self._tables_panel.select_first()

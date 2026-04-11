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
from bde_xbrl_editor.ui import theme

# ---------------------------------------------------------------------------
# Activity bar constants
# ---------------------------------------------------------------------------

_BAR_W = 44          # icon bar width in px
_PANEL_W = 260       # content panel width in px

_ICONS = ["⊡", "⊞", "⚡", "≡", "⟷", "◈"]
_TIPS = ["DTS Files", "Tables", "Validations", "Concepts", "Definition Linkbase", "Instance"]

_BAR_STYLE = """
    QWidget#ActivityBar {
        background: """ + theme.NAV_BG_DEEP + """;
        border-right: 1px solid """ + theme.BORDER_STRONG + """;
    }
"""

_BTN_STYLE = """
    QToolButton {
        background: transparent;
        border: none;
        color: """ + theme.ACCENT_SOFT + """;
        font-size: 20px;
        padding: 6px;
        border-radius: 4px;
    }
    QToolButton:hover {
        color: """ + theme.TEXT_INVERSE + """;
        background: rgba(255,253,248,0.12);
    }
    QToolButton:checked {
        color: """ + theme.TEXT_INVERSE + """;
        background: rgba(255,248,236,0.2);
        border-left: 3px solid """ + theme.HEADER_BG_LIGHT + """;
    }
"""

_PANEL_STYLE = """
    QWidget#PanelRoot {
        background: """ + theme.PANEL_BG + """;
        border-right: 1px solid """ + theme.BORDER + """;
    }
"""

_SECTION_HDR_STYLE = (
    f"background: {theme.NAV_BG_DARK}; color: {theme.TEXT_INVERSE}; font-weight: bold;"
    " font-size: 11px; padding: 6px 10px; letter-spacing: 1px;"
)

_COLLAPSIBLE_HDR_STYLE = (
    f"QPushButton {{ text-align: left; padding: 5px 8px; background: {theme.HEADER_BG};"
    f" color: {theme.TEXT_MAIN}; font-size: 11px; font-weight: bold; border: none; }}"
    f"QPushButton:hover {{ background: {theme.HEADER_BG_LIGHT}; }}"
)

_LIST_STYLE = """
    QListWidget {
        border: none;
        background: """ + theme.SURFACE_BG + """;
        font-size: 12px;
        color: """ + theme.TEXT_MAIN + """;
        outline: none;
    }
    QListWidget::item {
        padding: 5px 8px;
        border-bottom: 1px solid """ + theme.ACCENT_SOFT + """;
    }
    QListWidget::item:selected {
        background: """ + theme.SELECTION_BG + """;
        color: """ + theme.SELECTION_FG + """;
    }
    QListWidget::item:hover:!selected {
        background: """ + theme.HOVER_BG + """;
    }
"""

_TREE_STYLE = """
    QTreeWidget {
        border: none;
        background: """ + theme.SURFACE_BG + """;
        font-size: 11px;
        color: """ + theme.TEXT_MAIN + """;
        outline: none;
    }
    QTreeWidget::item {
        padding: 2px 4px;
    }
    QTreeWidget::item:selected {
        background: """ + theme.SELECTION_BG + """;
        color: """ + theme.SELECTION_FG + """;
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
            self._btn.setChecked(False)
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

        key_style = f"color: {theme.TEXT_MUTED}; font-size: 10px; font-weight: bold;"
        val_style = f"color: {theme.TEXT_MAIN}; font-size: 11px;"

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

_DETAIL_STYLE = """
    QWidget#DetailContainer {
        background: """ + theme.SURFACE_ALT_BG + """;
        border-top: 1px solid """ + theme.BORDER + """;
    }
"""

_DETAIL_KEY_STYLE = f"color: {theme.TEXT_MUTED}; font-size: 10px; font-weight: bold; padding: 0;"
_DETAIL_VAL_STYLE = f"color: {theme.TEXT_MAIN}; font-size: 11px; padding: 0 0 4px 0;"


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
            lbl.setStyleSheet(f"color: {theme.TEXT_SUBTLE}; font-size: 11px; padding: 12px;")
            lbl.setWordWrap(True)
            layout.addWidget(lbl)
            layout.addStretch(1)
            self._detail_section = None
            return

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

        # Scroll area with collapsible groups — fills all available height
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        self._assertion_lists: list[QListWidget] = []
        first_non_empty = True
        for group_name, items in groups.items():
            if not items:
                continue
            lst = QListWidget()
            lst.setStyleSheet(_LIST_STYLE)
            for a in items:
                label = getattr(a, "label", None) or a.assertion_id
                wi = QListWidgetItem(f"{a.assertion_id}  {label or ''}".strip())
                wi.setData(Qt.ItemDataRole.UserRole, a)
                lst.addItem(wi)
            lst.currentItemChanged.connect(self._on_item_selected)
            self._assertion_lists.append(lst)
            section = _CollapsibleSection(
                f"{group_name}  ({len(items)})", lst, expanded=first_non_empty
            )
            inner_layout.addWidget(section)
            first_non_empty = False

        inner_layout.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll, stretch=1)

        # ── Collapsible detail panel ───────────────────────────────────
        detail_body = QWidget()
        detail_body.setObjectName("DetailContainer")
        detail_body.setStyleSheet(_DETAIL_STYLE)
        detail_body_layout = QVBoxLayout(detail_body)
        detail_body_layout.setContentsMargins(8, 6, 8, 6)
        detail_body_layout.setSpacing(1)

        def _make_row(key: str) -> QLabel:
            kl = QLabel(key)
            kl.setStyleSheet(_DETAIL_KEY_STYLE)
            detail_body_layout.addWidget(kl)
            vl = QLabel("—")
            vl.setStyleSheet(_DETAIL_VAL_STYLE)
            vl.setWordWrap(True)
            vl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            detail_body_layout.addWidget(vl)
            return vl

        self._det_id = _make_row("ID")
        self._det_label = _make_row("LABEL")
        self._det_severity = _make_row("SEVERITY")
        self._det_test = _make_row("TEST / FORMULA")
        self._det_vars = _make_row("VARIABLES")
        self._det_precond = _make_row("PRECONDITION")

        self._detail_section = _CollapsibleSection("Details", detail_body, expanded=False)
        layout.addWidget(self._detail_section)

    def _on_item_selected(self, current: QListWidgetItem | None, _previous) -> None:
        if current is None or self._detail_section is None:
            return
        a = current.data(Qt.ItemDataRole.UserRole)
        if a is None:
            return

        # Deselect other lists so only one item is active at a time
        for lst in self._assertion_lists:
            if lst is not self.sender():
                lst.blockSignals(True)
                lst.clearSelection()
                lst.setCurrentItem(None)
                lst.blockSignals(False)

        self._det_id.setText(a.assertion_id)
        self._det_label.setText(getattr(a, "label", None) or "—")
        sev = getattr(a, "severity", None)
        self._det_severity.setText(str(sev.value).upper() if sev else "—")

        test = getattr(a, "test_xpath", None) or getattr(a, "formula_xpath", None)
        self._det_test.setText(test or "—")

        vars_ = getattr(a, "variables", ())
        if vars_:
            var_text = ", ".join(getattr(v, "name", str(v)) for v in vars_)
        else:
            var_text = "—"
        self._det_vars.setText(var_text)

        precond = getattr(a, "precondition_xpath", None)
        self._det_precond.setText(precond or "—")

        # Auto-expand detail section
        if not self._detail_section._body.isVisible():
            self._detail_section._btn.click()


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
            f"QLineEdit {{ border: none; border-bottom: 1px solid {theme.BORDER};"
            f" padding: 5px 8px; font-size: 11px; color: {theme.TEXT_MAIN}; background: {theme.SURFACE_BG}; }}"
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
            lbl.setStyleSheet(f"color: {theme.TEXT_SUBTLE}; font-size: 11px; padding: 12px;")
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
# Panel: Instance (index 5)
# ---------------------------------------------------------------------------

class _InstancePanel(QWidget):
    """Panel showing instance metadata (entity, period, filing indicators) and
    a table list filtered to the filed templates.

    All three sections are collapsible via ``_CollapsibleSection``:
    - INSTANCE   — entity + period, expanded by default
    - FILING INDICATORS — template list, collapsed by default to save space
    - TABLES     — filed-table list, expanded + stretchy (takes all remaining height)
    """

    table_selected = Signal(object)  # TableDefinitionPWD

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        _key_style = f"color: {theme.TEXT_MUTED}; font-size: 10px; font-weight: bold; padding: 0;"
        _val_style = f"color: {theme.TEXT_MAIN}; font-size: 11px; padding: 0 0 4px 0;"

        # ── INSTANCE section (collapsible, expanded) ───────────────────
        meta_body = QWidget()
        meta_layout = QVBoxLayout(meta_body)
        meta_layout.setContentsMargins(8, 6, 8, 8)
        meta_layout.setSpacing(2)

        kl1 = QLabel("ENTITY")
        kl1.setStyleSheet(_key_style)
        self._entity_val = QLabel("—")
        self._entity_val.setStyleSheet(_val_style)
        self._entity_val.setWordWrap(True)
        meta_layout.addWidget(kl1)
        meta_layout.addWidget(self._entity_val)

        kl2 = QLabel("PERIOD")
        kl2.setStyleSheet(_key_style)
        self._period_val = QLabel("—")
        self._period_val.setStyleSheet(_val_style)
        meta_layout.addWidget(kl2)
        meta_layout.addWidget(self._period_val)

        layout.addWidget(_CollapsibleSection("INSTANCE", meta_body, expanded=True))

        # ── FILING INDICATORS section (collapsible, collapsed by default) ──
        fi_body = QWidget()
        fi_layout = QVBoxLayout(fi_body)
        fi_layout.setContentsMargins(8, 6, 8, 8)
        fi_layout.setSpacing(0)

        self._fi_val = QLabel("—")
        self._fi_val.setWordWrap(True)
        self._fi_val.setStyleSheet(f"color: {theme.TEXT_MAIN}; font-size: 11px;")
        fi_layout.addWidget(self._fi_val)

        layout.addWidget(
            _CollapsibleSection("FILING INDICATORS", fi_body, expanded=False)
        )

        # ── TABLES section (collapsible, expanded, takes all remaining height) ──
        self._table_list = QListWidget()
        self._table_list.setStyleSheet(_LIST_STYLE)
        self._table_list.itemClicked.connect(self._on_item_clicked)

        self._tables_section = _CollapsibleSection(
            "TABLES", self._table_list, expanded=True
        )
        layout.addWidget(self._tables_section, stretch=1)

        self._table_map: dict[str, object] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def populate(self, instance: object, taxonomy: object) -> None:
        """Fill the panel with data from *instance* and *taxonomy*."""
        # Entity
        entity = instance.entity  # type: ignore[union-attr]
        self._entity_val.setText(f"{entity.identifier}\n{entity.scheme}")

        # Period
        period = instance.period  # type: ignore[union-attr]
        if period.period_type == "instant":
            period_text = f"Instant: {period.instant_date}"
        else:
            period_text = f"{period.start_date} – {period.end_date}"
        self._period_val.setText(period_text)

        # Filing indicators
        fi_texts: list[str] = []
        for fi in instance.filing_indicators:  # type: ignore[union-attr]
            status = "✓" if fi.filed else "✗"
            fi_texts.append(f"{status} {fi.template_id}")
        self._fi_val.setText("\n".join(fi_texts) if fi_texts else "None")

        # Tables — only filed ones (fall back to all if no indicators)
        self._table_list.clear()
        self._table_map.clear()
        filed_ids = {
            fi.template_id
            for fi in instance.filing_indicators  # type: ignore[union-attr]
            if fi.filed
        }
        count = 0
        for table in taxonomy.tables:  # type: ignore[union-attr]
            if table.table_id in filed_ids or not filed_ids:
                item = QListWidgetItem(f"{table.table_id}\n{table.label}")
                item.setData(Qt.ItemDataRole.UserRole, table)
                self._table_list.addItem(item)
                self._table_map[table.table_id] = table
                count += 1

        # Update the TABLES section header to show the count
        arrow = "▾" if self._tables_section._body.isVisible() else "▸"
        self._tables_section._btn.setText(f"{arrow}  TABLES  ({count})")

    def select_first(self) -> None:
        """Select and emit the first table in the list, if any."""
        if self._table_list.count() > 0:
            first = self._table_list.item(0)
            self._table_list.setCurrentItem(first)
            self._on_item_clicked(first)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        table = item.data(Qt.ItemDataRole.UserRole)
        if table is not None:
            self.table_selected.emit(table)


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

        self._instance_panel = _InstancePanel()
        self._instance_panel.table_selected.connect(self.table_selected)

        self._stack.addWidget(_DtsFilesPanel(taxonomy))       # 0
        self._stack.addWidget(self._tables_panel)             # 1
        self._stack.addWidget(_ValidationsPanel(taxonomy))    # 2
        self._stack.addWidget(_ConceptsPanel(taxonomy))       # 3
        self._stack.addWidget(_DefinitionPanel(taxonomy))     # 4
        self._stack.addWidget(self._instance_panel)           # 5

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

    def set_instance(self, instance: object, taxonomy: object) -> None:
        """Populate the Instance panel with *instance* data and switch to it."""
        self._instance_panel.populate(instance, taxonomy)
        self._activate(5)

    def clear_instance(self) -> None:
        """Switch back to the Tables panel (used when an instance is closed)."""
        self._activate(1)

    def select_first_instance_table(self) -> None:
        """Select and emit the first table from the Instance panel."""
        self._instance_panel.select_first()

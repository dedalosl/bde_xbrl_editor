"""ActivitySidebar — VS Code-style collapsible left sidebar.

A narrow icon bar (44 px) selects between panel views.
Clicking the active icon collapses the panel to give the table more space.
"""

from __future__ import annotations

from pathlib import Path
from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bde_xbrl_editor.taxonomy.models import (
    ConsistencyAssertionDefinition,
    ExistenceAssertionDefinition,
    TaxonomyStructure,
    ValueAssertionDefinition,
)
from bde_xbrl_editor.ui import theme
from bde_xbrl_editor.validation.formula.details import (
    build_formula_display_details,
    format_assertion_expression,
)

# ---------------------------------------------------------------------------
# Activity bar constants
# ---------------------------------------------------------------------------

_BAR_W = 44          # icon bar width in px
_PANEL_W = 260       # content panel width in px
_SIDEBAR_ANIM_MS = 160
_FADE_ANIM_MS = 120
_SECTION_ANIM_MS = 140

_ICONS = ["TAX", "TAB", "VAL", "INS"]
_TIPS = ["Taxonomy", "Tables", "Validations", "Instance"]

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
        font-size: 9px;
        font-weight: 700;
        padding: 4px 2px;
        border-radius: 8px;
        text-align: center;
    }
    QToolButton:hover {
        color: """ + theme.TEXT_INVERSE + """;
        background: rgba(255,253,248,0.10);
    }
    QToolButton:checked {
        color: """ + theme.TEXT_INVERSE + """;
        background: rgba(255,248,236,0.18);
        border-left: 2px solid """ + theme.HEADER_BG_LIGHT + """;
    }
"""

_PANEL_STYLE = """
    QWidget#PanelRoot {
        background: """ + theme.PANEL_BG + """;
        border-right: 1px solid """ + theme.BORDER + """;
    }
"""

_SECTION_HDR_STYLE = (
    f"background: {theme.SURFACE_ALT_BG}; color: {theme.TEXT_MUTED}; font-weight: bold;"
    f" font-size: 10px; padding: 7px 10px;"
)

_COLLAPSIBLE_HDR_STYLE = (
    f"QPushButton {{ text-align: left; padding: 6px 8px; background: {theme.SURFACE_BG};"
    f" color: {theme.TEXT_MAIN}; font-size: 11px; font-weight: 600; border: none;"
    f" border-bottom: 1px solid {theme.ACCENT_SOFT}; }}"
    f"QPushButton:hover {{ background: {theme.SURFACE_ALT_BG}; }}"
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
        padding: 7px 8px;
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

_TABLE_HAS_DATA_BG = QColor("#F7EFD8")
_TABLE_HAS_DATA_FG = QColor(theme.TEXT_MAIN)
_TABLE_EMPTY_FG = QColor(theme.TEXT_SUBTLE)


def _indicator_aliases(value: str) -> set[str]:
    """Return equivalent filing-indicator spellings used by BDE/Eurofiling tables."""
    if not value:
        return set()

    aliases = {value}
    if value.startswith("es_t"):
        aliases.add("es_b" + value[4:])
    elif value.startswith("es_b"):
        aliases.add("es_t" + value[4:])
    elif value.startswith("t"):
        aliases.add("b" + value[1:])
    elif value.startswith("b"):
        aliases.add("t" + value[1:])
    return aliases


def _table_identity(table: object) -> str:
    table_code = getattr(table, "table_code", None)
    table_id = getattr(table, "table_id", "")
    parts = [part for part in (table_code, table_id) if part]
    return "  |  ".join(parts)


def _table_matches_query(table: object, query: str) -> bool:
    if not query:
        return True
    haystack = " ".join((
        getattr(table, "table_code", "") or "",
        getattr(table, "table_id", "") or "",
        getattr(table, "label", "") or "",
    )).lower()
    return query in haystack


def _table_is_filed(table: object, filed_ids: set[str]) -> bool:
    table_id = getattr(table, "table_id", "") or ""
    table_code = getattr(table, "table_code", None) or ""
    candidate_ids = _indicator_aliases(table_id)
    if table_code:
        candidate_ids.update(_indicator_aliases(table_code))
    return bool(candidate_ids & filed_ids)


def _table_matches_indicator(table: object, template_id: str) -> bool:
    table_id = getattr(table, "table_id", "") or ""
    table_code = getattr(table, "table_code", None) or ""
    table_ids = _indicator_aliases(table_id)
    if table_code:
        table_ids.update(_indicator_aliases(table_code))
    return template_id in table_ids


class _CollapsibleSection(QWidget):
    """A collapsible section with a toggle-button header and a body widget."""

    def __init__(
        self,
        title: str,
        body: QWidget,
        expanded: bool = True,
        parent: QWidget | None = None,
        body_stretch: int = 0,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._title = title

        self._btn = QPushButton()
        self._btn.setStyleSheet(_COLLAPSIBLE_HDR_STYLE)
        self._btn.setCheckable(True)
        self._btn.setChecked(True)
        self._btn.clicked.connect(self._toggle)
        layout.addWidget(self._btn)

        self._body = body
        layout.addWidget(body, body_stretch)
        self._body_height_hint = max(body.sizeHint().height(), 1)
        self._body.setMaximumHeight(16777215)
        self._toggle_anim = QVariantAnimation(self)
        self._toggle_anim.setDuration(_SECTION_ANIM_MS)
        self._toggle_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._toggle_anim.valueChanged.connect(self._on_toggle_animate)
        self._toggle_anim.finished.connect(self._on_toggle_finished)

        if not expanded:
            self._btn.setChecked(False)
            self._body.setMaximumHeight(0)
            self._body.setVisible(False)
        self._sync_header()

    def _toggle(self, checked: bool) -> None:
        self._body_height_hint = max(self._body.sizeHint().height(), self._body_height_hint, 1)
        self._toggle_anim.stop()
        self._sync_header(checked)
        if checked:
            self._body.setVisible(True)
            self._toggle_anim.setStartValue(max(self._body.maximumHeight(), 0))
            self._toggle_anim.setEndValue(self._body_height_hint)
        else:
            self._toggle_anim.setStartValue(self._body.height() or self._body_height_hint)
            self._toggle_anim.setEndValue(0)
        self._toggle_anim.start()

    def _on_toggle_animate(self, value: object) -> None:
        height = max(int(value), 0)
        self._body.setMaximumHeight(height)
        if height == 0 and not self._btn.isChecked():
            self._body.setVisible(False)

    def _on_toggle_finished(self) -> None:
        if self._btn.isChecked():
            self._body.setMaximumHeight(16777215)

    def set_title(self, title: str) -> None:
        self._title = title
        self._sync_header()

    def _sync_header(self, checked: bool | None = None) -> None:
        is_open = self._btn.isChecked() if checked is None else checked
        arrow = "▾" if is_open else "▸"
        self._btn.setText(f"{arrow}  {self._title}")


# ---------------------------------------------------------------------------
# Panel: DTS Files
# ---------------------------------------------------------------------------

class _DtsFilesPanel(QWidget):
    def __init__(
        self,
        taxonomy: TaxonomyStructure,
        parent: QWidget | None = None,
        *,
        show_header: bool = True,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if show_header:
            hdr = QLabel("DTS Files")
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

        hdr = QLabel(f"Tables  ({len(taxonomy.tables)})")
        hdr.setStyleSheet(_SECTION_HDR_STYLE)
        layout.addWidget(hdr)

        # Table list
        self._list = QListWidget()
        self._list.setStyleSheet(_LIST_STYLE)
        for table in taxonomy.tables:
            item = QListWidgetItem(f"{_table_identity(table)}\n{table.label}")
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
            kl = QLabel(key.title())
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

        hdr = QLabel("Validations")
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
                wi.setToolTip(format_assertion_expression(a))
                wi.setData(Qt.ItemDataRole.UserRole, a)
                lst.addItem(wi)
            lst.currentItemChanged.connect(self._on_item_selected)
            self._assertion_lists.append(lst)
            section = _CollapsibleSection(
                f"{group_name}  ({len(items)})",
                lst,
                expanded=first_non_empty,
                body_stretch=1 if first_non_empty else 0,
            )
            section.setSizePolicy(
                QSizePolicy.Policy.Preferred,
                QSizePolicy.Policy.Expanding if first_non_empty else QSizePolicy.Policy.Minimum,
            )
            lst.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
            inner_layout.addWidget(section, 1 if first_non_empty else 0)
            first_non_empty = False

        scroll.setWidget(inner)

        # ── Resizable detail panel ─────────────────────────────────────
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

        self._det_id = _make_row("Id")
        self._det_label = _make_row("Label")
        self._det_type = _make_row("Type")
        self._det_severity = _make_row("Severity")
        self._det_test = _make_row("Test / Formula")
        self._det_vars = _make_row("Operands")
        self._det_precond = _make_row("Precondition")

        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        detail_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        detail_scroll.setStyleSheet("QScrollArea { border: none; }")
        detail_scroll.setWidget(detail_body)
        self._detail_scroll = detail_scroll

        self._detail_section = _CollapsibleSection("Details", self._detail_scroll, expanded=False)
        self._detail_section._btn.clicked.connect(self._sync_detail_splitter)

        self._content_splitter = QSplitter(Qt.Orientation.Vertical)
        self._content_splitter.setChildrenCollapsible(False)
        self._content_splitter.setHandleWidth(0)
        self._content_splitter.addWidget(scroll)
        self._content_splitter.addWidget(self._detail_section)
        self._content_splitter.setStretchFactor(0, 1)
        self._content_splitter.setStretchFactor(1, 0)
        self._detail_section.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        layout.addWidget(self._content_splitter, stretch=1)
        self._sync_detail_splitter()

    def _sync_detail_splitter(self) -> None:
        checked = self._detail_section._btn.isChecked()
        header_height = self._detail_section._btn.sizeHint().height()
        if checked:
            self._content_splitter.setHandleWidth(6)
            total = max(self._content_splitter.height(), sum(self._content_splitter.sizes()))
            detail_height = max(160, min(260, total // 3))
            self._content_splitter.setSizes([max(total - detail_height, 0), detail_height])
        else:
            self._content_splitter.setHandleWidth(0)
            total = max(self._content_splitter.height(), sum(self._content_splitter.sizes()), header_height + 1)
            self._content_splitter.setSizes([max(total - header_height, 1), header_height])

    def _on_item_selected(self, current: QListWidgetItem | None, _previous) -> None:
        if current is None:
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
        details = build_formula_display_details(a)
        self._det_type.setText(details.assertion_type)
        sev = getattr(a, "severity", None)
        self._det_severity.setText(self._format_severity(sev))
        self._det_test.setText(details.expression)
        self._det_vars.setText(details.operands_text)
        self._det_precond.setText(details.precondition)

        if not self._detail_section._btn.isChecked():
            self._detail_section._btn.setChecked(True)
            self._detail_section._toggle(True)
            self._sync_detail_splitter()

    @staticmethod
    def _format_severity(severity: object) -> str:
        if severity is None:
            return "—"

        value = getattr(severity, "value", severity)
        text = str(value).strip()
        return text.upper() if text else "—"


# ---------------------------------------------------------------------------
# Panel: Concepts
# ---------------------------------------------------------------------------

class _ConceptsPanel(QWidget):
    def __init__(
        self,
        taxonomy: TaxonomyStructure,
        parent: QWidget | None = None,
        *,
        show_header: bool = True,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if show_header:
            hdr = QLabel(f"Concepts  ({len(taxonomy.concepts)})")
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
    def __init__(
        self,
        taxonomy: TaxonomyStructure,
        parent: QWidget | None = None,
        *,
        show_header: bool = True,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if show_header:
            hdr = QLabel("Definition Linkbase")
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
    the taxonomy table list for the loaded instance.

    All three sections are collapsible via ``_CollapsibleSection``:
    - INSTANCE   — entity + period, expanded by default
    - FILING INDICATORS — template list, collapsed by default to save space
    - TABLES     — taxonomy table list, expanded + stretchy (takes all remaining height)
    """

    table_selected = Signal(object)  # TableDefinitionPWD

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._instance = None
        self._taxonomy = None
        self._editor = None
        self._fi_syncing = False
        self._fi_items_by_template_id: dict[str, QListWidgetItem] = {}
        self._fi_table_lookup: dict[str, object] = {}
        self._editing_enabled = False
        self._data_presence_cache_key: tuple[int, int] | None = None
        self._data_presence_cache: dict[str, bool] = {}
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

        kl1 = QLabel("Entity")
        kl1.setStyleSheet(_key_style)
        self._entity_val = QLabel("—")
        self._entity_val.setStyleSheet(_val_style)
        self._entity_val.setWordWrap(True)
        meta_layout.addWidget(kl1)
        meta_layout.addWidget(self._entity_val)

        kl2 = QLabel("Period")
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
        fi_layout.setSpacing(6)

        self._fi_val = QLabel("—")
        self._fi_val.setWordWrap(True)
        self._fi_val.setStyleSheet(f"color: {theme.TEXT_MAIN}; font-size: 11px;")
        fi_layout.addWidget(self._fi_val)

        self._fi_list = QListWidget()
        self._fi_list.setStyleSheet(_LIST_STYLE)
        self._fi_list.itemChanged.connect(self._on_filing_indicator_changed)
        self._fi_list.hide()
        fi_layout.addWidget(self._fi_list)

        layout.addWidget(
            _CollapsibleSection("Filing Indicators", fi_body, expanded=False)
        )

        # ── TABLES section (collapsible, expanded, takes all remaining height) ──
        tables_body = QWidget()
        tables_layout = QVBoxLayout(tables_body)
        tables_layout.setContentsMargins(0, 0, 0, 0)
        tables_layout.setSpacing(0)

        self._table_search = QLineEdit()
        self._table_search.setPlaceholderText("Search tables…")
        self._table_search.setStyleSheet(
            f"QLineEdit {{ border: none; border-bottom: 1px solid {theme.BORDER};"
            f" padding: 5px 8px; font-size: 11px; color: {theme.TEXT_MAIN}; background: {theme.SURFACE_BG}; }}"
        )
        self._table_search.textChanged.connect(self._filter_tables)
        tables_layout.addWidget(self._table_search)

        self._table_list = QListWidget()
        self._table_list.setStyleSheet(_LIST_STYLE)
        self._table_list.itemClicked.connect(self._on_item_clicked)
        tables_layout.addWidget(self._table_list, stretch=1)

        self._tables_section = _CollapsibleSection(
            "Tables", tables_body, expanded=True
        )
        layout.addWidget(self._tables_section, stretch=1)

        self._table_map: dict[str, object] = {}
        self._table_entries: list[tuple[object, bool]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def populate(self, instance: object, taxonomy: object) -> None:
        """Fill the panel with data from *instance* and *taxonomy*."""
        self._instance = instance
        self._taxonomy = taxonomy
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
        self._populate_filing_indicators(instance, taxonomy)

        # Tables — show the full taxonomy list in instance mode, ordered by data presence.
        self._table_list.clear()
        self._table_map.clear()
        self._table_entries.clear()
        visible_tables = list(taxonomy.tables)  # type: ignore[union-attr]
        data_presence = self._compute_table_data_presence(instance, taxonomy, visible_tables)
        populated_entries = [
            (table, True) for table in visible_tables if data_presence.get(table.table_id, False)
        ]
        empty_entries = [
            (table, False) for table in visible_tables if not data_presence.get(table.table_id, False)
        ]
        self._table_entries = populated_entries + empty_entries
        self._table_search.blockSignals(True)
        self._table_search.clear()
        self._table_search.blockSignals(False)
        self._rebuild_table_list()

        # Update the TABLES section header to show the count
        self._tables_section.set_title(f"Tables  ({len(self._table_entries)})")

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

    def _filter_tables(self, text: str) -> None:
        self._rebuild_table_list(text.strip().lower())

    def _rebuild_table_list(self, query: str = "") -> None:
        selected = self._table_list.currentItem()
        selected_id = None
        if selected is not None:
            table = selected.data(Qt.ItemDataRole.UserRole)
            selected_id = getattr(table, "table_id", None)

        self._table_list.clear()
        self._table_map.clear()
        for table, has_data in self._table_entries:
            if not _table_matches_query(table, query):
                continue
            status = "Contains data" if has_data else "Empty"
            item = QListWidgetItem(f"{_table_identity(table)}  |  {status}\n{table.label}")
            item.setData(Qt.ItemDataRole.UserRole, table)
            item.setToolTip(
                f"{_table_identity(table)}\n{table.label}\n"
                f"{'Contains facts in the current instance.' if has_data else 'No facts matched in the current instance yet.'}"
            )
            font = QFont(self._table_list.font())
            font.setBold(has_data)
            item.setFont(font)
            if has_data:
                item.setBackground(_TABLE_HAS_DATA_BG)
                item.setForeground(_TABLE_HAS_DATA_FG)
            else:
                item.setForeground(_TABLE_EMPTY_FG)
            self._table_list.addItem(item)
            self._table_map[table.table_id] = table
            if selected_id is not None and table.table_id == selected_id:
                self._table_list.setCurrentItem(item)

    def _compute_table_data_presence(
        self,
        instance: object,
        taxonomy: object,
        tables: list[object],
    ) -> dict[str, bool]:
        cache_key = (id(instance), len(getattr(instance, "facts", []) or []))
        if self._data_presence_cache_key == cache_key:
            return {table.table_id: self._data_presence_cache.get(table.table_id, False) for table in tables}

        presence: dict[str, bool] = {}
        filed_ids: set[str] = set()
        filing_indicators = list(getattr(instance, "filing_indicators", []) or [])
        if filing_indicators:
            filed_ids.update(
                str(getattr(indicator, "template_id", ""))
                for indicator in filing_indicators
                if getattr(indicator, "filed", False) and getattr(indicator, "template_id", "")
            )
        bde_preambulo = getattr(instance, "bde_preambulo", None)
        if bde_preambulo is not None:
            filed_ids.update(
                str(getattr(estado, "codigo", ""))
                for estado in getattr(bde_preambulo, "estados_reportados", []) or []
                if not getattr(estado, "blanco", False) and getattr(estado, "codigo", "")
            )

        if filed_ids:
            presence = {
                table.table_id: _table_is_filed(table, filed_ids)
                for table in tables
            }
            self._data_presence_cache_key = cache_key
            self._data_presence_cache = dict(presence)
            return presence

        from bde_xbrl_editor.table_renderer.errors import TableLayoutError, ZIndexOutOfRangeError
        from bde_xbrl_editor.table_renderer.layout_engine import TableLayoutEngine
        from bde_xbrl_editor.ui.widgets.xbrl_table_view import _derive_initial_z_constraints

        engine = TableLayoutEngine(taxonomy)  # type: ignore[arg-type]

        for table in tables:
            has_data = False
            try:
                z_constraints = _derive_initial_z_constraints(table, taxonomy, instance)
                layout = engine.compute(
                    table,
                    instance=instance,
                    z_constraints=z_constraints or None,
                )
                has_data = any(
                    cell.fact_value is not None
                    for row in layout.body
                    for cell in row
                )
            except (TableLayoutError, ZIndexOutOfRangeError):
                has_data = False
            presence[table.table_id] = has_data

        self._data_presence_cache_key = cache_key
        self._data_presence_cache = dict(presence)

        return presence

    def set_editor(self, editor: object | None) -> None:
        self._editor = editor
        self._apply_filing_indicator_editability()

    def set_editing_enabled(self, enabled: bool) -> None:
        self._editing_enabled = enabled
        self._apply_filing_indicator_editability()

    def _populate_filing_indicators(self, instance: object, taxonomy: object) -> None:
        indicators = list(getattr(instance, "filing_indicators", []) or [])
        self._fi_syncing = True
        self._fi_list.clear()
        self._fi_items_by_template_id.clear()
        self._fi_table_lookup.clear()

        if not indicators:
            self._fi_list.hide()
            self._fi_val.show()
            self._fi_val.setText("None")
            self._fi_syncing = False
            return

        tables = list(getattr(taxonomy, "tables", []) or [])
        table_lookup: dict[str, object] = {}
        for table in tables:
            for alias in _indicator_aliases(getattr(table, "table_id", "") or ""):
                table_lookup.setdefault(alias, table)
            table_code = getattr(table, "table_code", None) or ""
            for alias in _indicator_aliases(table_code):
                table_lookup.setdefault(alias, table)
        use_bde_list = any(getattr(table, "table_code", None) for table in tables)
        if not use_bde_list:
            fi_texts = []
            for fi in indicators:
                status = "✓" if fi.filed else "✗"
                fi_texts.append(f"{status} {fi.template_id}")
            self._fi_list.hide()
            self._fi_val.show()
            self._fi_val.setText("\n".join(fi_texts) if fi_texts else "None")
            self._fi_syncing = False
            return

        for fi in indicators:
            table = table_lookup.get(fi.template_id)
            identity = _table_identity(table) if table is not None else fi.template_id
            label = getattr(table, "label", "") if table is not None else ""
            line = f"{identity}\n{label or 'Unknown table'}"
            item = QListWidgetItem(line)
            item.setData(Qt.ItemDataRole.UserRole, fi.template_id)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if fi.filed else Qt.CheckState.Unchecked)
            item.setToolTip(
                "Checked means the table contains data and blanco is omitted.\n"
                "Unchecked means blanco=\"true\" and the table is saved as empty."
            )
            self._fi_list.addItem(item)
            self._fi_items_by_template_id[fi.template_id] = item
            if table is not None:
                self._fi_table_lookup[fi.template_id] = table

        self._fi_val.hide()
        self._fi_list.show()
        self._fi_syncing = False
        self._apply_filing_indicator_editability()

    def _apply_filing_indicator_editability(self) -> None:
        editable = self._editing_enabled and self._editor is not None and self._fi_list.count() > 0
        self._fi_list.setEnabled(self._fi_list.count() > 0)
        self._fi_syncing = True
        for index in range(self._fi_list.count()):
            item = self._fi_list.item(index)
            flags = item.flags() | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            if editable:
                flags |= Qt.ItemFlag.ItemIsUserCheckable
            else:
                flags &= ~Qt.ItemFlag.ItemIsUserCheckable
            item.setFlags(flags)
        self._fi_syncing = False
        title = (
            "Filing indicators can be edited when editing mode is on."
            if not editable
            else "Toggle whether each reported table is saved with data or as blanco."
        )
        self._fi_list.setToolTip(title)

    def _on_filing_indicator_changed(self, item: QListWidgetItem) -> None:
        if self._fi_syncing or self._editor is None or not self._editing_enabled:
            return
        template_id = item.data(Qt.ItemDataRole.UserRole)
        if not template_id:
            return
        filed = item.checkState() == Qt.CheckState.Checked
        context_ref = ""
        indicators = getattr(self._instance, "filing_indicators", []) if self._instance is not None else []
        for indicator in indicators:
            if getattr(indicator, "template_id", None) == template_id:
                context_ref = getattr(indicator, "context_ref", "") or ""
                break
        self._editor.set_filing_indicator(template_id, filed, context_ref=context_ref)


class _TaxonomyPanel(QWidget):
    """Compact taxonomy panel combining DTS, concepts, and definition content."""

    def __init__(self, taxonomy: TaxonomyStructure, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        hdr = QLabel("Taxonomy")
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

        inner_layout.addWidget(
            _CollapsibleSection(
                f"DTS Files  ({len(taxonomy.schema_files) + len(taxonomy.linkbase_files)})",
                _DtsFilesPanel(taxonomy, show_header=False),
                expanded=True,
            )
        )
        inner_layout.addWidget(
            _CollapsibleSection(
                f"Concepts  ({len(taxonomy.concepts)})",
                _ConceptsPanel(taxonomy, show_header=False),
                expanded=False,
            )
        )
        inner_layout.addWidget(
            _CollapsibleSection(
                "Definition Linkbase",
                _DefinitionPanel(taxonomy, show_header=False),
                expanded=False,
            )
        )
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
    width_changed = Signal(int)

    def __init__(
        self,
        taxonomy: TaxonomyStructure,
        parent: QWidget | None = None,
        *,
        visible_indexes: tuple[int, ...] = (0, 1, 2, 3),
        initial_index: int | None = None,
    ) -> None:
        super().__init__(parent)
        self._taxonomy = taxonomy
        self._visible_indexes = tuple(sorted(set(visible_indexes)))
        self._lazy_builders: dict[int, Callable[[], QWidget]] = {}
        self._loaded_indexes: set[int] = set()
        self._active_index: int | None = None
        self._target_width = _BAR_W + _PANEL_W
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        self._width_anim = QVariantAnimation(self)
        self._width_anim.setDuration(_SIDEBAR_ANIM_MS)
        self._width_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._width_anim.valueChanged.connect(self._on_width_animate)

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
            btn.setAccessibleName(tip)
            btn.setCheckable(True)
            btn.setFixedSize(_BAR_W, _BAR_W)
            btn.setStyleSheet(_BTN_STYLE)
            btn.clicked.connect(lambda checked, idx=i: self._on_button_clicked(idx))
            bar_layout.addWidget(btn)
            self._buttons.append(btn)

        for index, button in enumerate(self._buttons):
            button.setVisible(index in self._visible_indexes)

        bar_layout.addStretch(1)
        root_layout.addWidget(self._bar)

        # ── Content panel (stacked) ────────────────────────────────────
        self._panel_root = QWidget()
        self._panel_root.setObjectName("PanelRoot")
        self._panel_root.setStyleSheet(_PANEL_STYLE)
        self._panel_opacity = QGraphicsOpacityEffect(self._panel_root)
        self._panel_opacity.setOpacity(1.0)
        self._panel_root.setGraphicsEffect(self._panel_opacity)
        self._fade_anim = QVariantAnimation(self)
        self._fade_anim.setDuration(_FADE_ANIM_MS)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.valueChanged.connect(self._on_fade_animate)
        panel_layout = QVBoxLayout(self._panel_root)
        panel_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.setSpacing(0)

        self._stack = QStackedWidget()
        panel_layout.addWidget(self._stack)

        self._tables_panel = _TablesPanel(taxonomy) if 1 in self._visible_indexes else None
        if self._tables_panel is not None:
            self._tables_panel.table_selected.connect(self.table_selected)

        self._instance_panel = _InstancePanel() if 3 in self._visible_indexes else None
        if self._instance_panel is not None:
            self._instance_panel.table_selected.connect(self.table_selected)

        taxonomy_widget = _TaxonomyPanel(taxonomy) if 0 in self._visible_indexes else QWidget()
        tables_widget = self._tables_panel or QWidget()
        validations_widget = QWidget()
        instance_widget = self._instance_panel or QWidget()

        self._stack.addWidget(taxonomy_widget)    # 0
        self._stack.addWidget(tables_widget)      # 1
        self._stack.addWidget(validations_widget) # 2
        self._stack.addWidget(instance_widget)    # 3

        if 0 in self._visible_indexes:
            self._loaded_indexes.add(0)
        if 1 in self._visible_indexes:
            self._loaded_indexes.add(1)
        if 3 in self._visible_indexes:
            self._loaded_indexes.add(3)
        if 2 in self._visible_indexes:
            self._lazy_builders[2] = lambda: _ValidationsPanel(taxonomy)

        root_layout.addWidget(self._panel_root)

        default_index = initial_index if initial_index in self._visible_indexes else None
        if default_index is None and self._visible_indexes:
            default_index = self._visible_indexes[0]

        if default_index is None:
            self._panel_root.setVisible(False)
            self._panel_opacity.setOpacity(0.0)
            self._active_index = None
            for btn in self._buttons:
                btn.setChecked(False)
            self._apply_sidebar_width(_BAR_W, animated=False)
        else:
            self._ensure_panel_loaded(default_index)
            self._stack.setCurrentIndex(default_index)
            self._panel_root.setVisible(True)
            self._panel_opacity.setOpacity(1.0)
            self._active_index = default_index
            for i, btn in enumerate(self._buttons):
                btn.setChecked(i == default_index)
            self._apply_sidebar_width(_BAR_W + _PANEL_W, animated=False)

    # ------------------------------------------------------------------
    # Toggle logic
    # ------------------------------------------------------------------

    def _on_button_clicked(self, idx: int) -> None:
        if idx not in self._visible_indexes:
            return
        if self._active_index == idx and self._panel_root.isVisible():
            # Clicking the already-active button → collapse panel
            self._buttons[idx].setChecked(False)
            self._active_index = None
            self._animate_panel_visibility(False)
            self._apply_sidebar_width(_BAR_W, animated=True)
        else:
            self._activate(idx)

    def _activate(self, idx: int) -> None:
        if idx not in self._visible_indexes:
            return
        self._ensure_panel_loaded(idx)
        self._active_index = idx
        self._stack.setCurrentIndex(idx)
        self._panel_root.setVisible(True)
        self._animate_panel_visibility(True)
        self._apply_sidebar_width(_BAR_W + _PANEL_W, animated=True)
        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == idx)

    def _apply_sidebar_width(self, width: int, *, animated: bool) -> None:
        self._target_width = width
        self._width_anim.stop()
        self.setFixedWidth(width)
        self.updateGeometry()
        self.width_changed.emit(width)

    def _on_width_animate(self, value: object) -> None:
        width = max(int(value), _BAR_W)
        self.setFixedWidth(width)
        self.updateGeometry()
        self.width_changed.emit(width)

    def _animate_panel_visibility(self, visible: bool) -> None:
        self._fade_anim.stop()
        if visible:
            self._panel_root.setVisible(True)
            self._fade_anim.setStartValue(self._panel_opacity.opacity())
            self._fade_anim.setEndValue(1.0)
        else:
            self._fade_anim.setStartValue(self._panel_opacity.opacity())
            self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def _on_fade_animate(self, value: object) -> None:
        opacity = max(0.0, min(float(value), 1.0))
        self._panel_opacity.setOpacity(opacity)
        if opacity == 0.0 and self._active_index is None:
            self._panel_root.setVisible(False)

    def _ensure_panel_loaded(self, idx: int) -> None:
        if idx in self._loaded_indexes:
            return
        builder = self._lazy_builders.get(idx)
        if builder is None:
            self._loaded_indexes.add(idx)
            return
        widget = builder()
        old_widget = self._stack.widget(idx)
        self._stack.removeWidget(old_widget)
        self._stack.insertWidget(idx, widget)
        old_widget.deleteLater()
        self._loaded_indexes.add(idx)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def select_first_table(self) -> None:
        """Activate the Tables panel and select the first table."""
        if self._tables_panel is None:
            return
        self._activate(1)
        self._tables_panel.select_first()

    def set_instance(self, instance: object, taxonomy: object, editor: object | None = None) -> None:
        """Populate the Instance panel with *instance* data and switch to it."""
        if self._instance_panel is None:
            return
        self.refresh_instance_panel(instance, taxonomy, editor)
        self._activate(3)

    def set_instance_editing_enabled(self, enabled: bool) -> None:
        if self._instance_panel is not None:
            self._instance_panel.set_editing_enabled(enabled)

    def refresh_instance_panel(
        self,
        instance: object,
        taxonomy: object,
        editor: object | None = None,
    ) -> None:
        if self._instance_panel is None:
            return
        self._instance_panel.populate(instance, taxonomy)
        self._instance_panel.set_editor(editor)

    def clear_instance(self) -> None:
        """Switch back to the Tables panel (used when an instance is closed)."""
        fallback_index = 1 if 1 in self._visible_indexes else (self._visible_indexes[0] if self._visible_indexes else None)
        if fallback_index is not None:
            self._activate(fallback_index)

    def select_first_instance_table(self) -> None:
        """Select and emit the first table from the Instance panel."""
        if self._instance_panel is not None:
            self._instance_panel.select_first()

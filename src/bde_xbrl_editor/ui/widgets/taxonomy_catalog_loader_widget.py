"""Catalog-based welcome screen — browse BDE taxonomies from taxonomies.json."""

from __future__ import annotations

import contextlib
import time
import webbrowser
from datetime import UTC, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QObject, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from bde_xbrl_editor.performance import LoadTiming, StageTiming, format_duration
from bde_xbrl_editor.taxonomy import LoaderSettings, TaxonomyCache, TaxonomyLoader
from bde_xbrl_editor.taxonomy_catalog.changes import (
    build_file_snapshot,
    collect_flagged_updates,
    detect_catalog_delta,
)
from bde_xbrl_editor.taxonomy_catalog.filter_sort import (
    filter_taxonomies,
    sort_taxonomies,
    unique_categories,
)
from bde_xbrl_editor.taxonomy_catalog.loader import (
    TaxonomyCatalogError,
    load_catalog,
    resolve_catalog_path,
)
from bde_xbrl_editor.taxonomy_catalog.models import (
    CatalogChangeReport,
    CatalogFileRef,
    EntryPoint,
    ModuleFile,
    Taxonomy,
    TaxonomyCatalogData,
)
from bde_xbrl_editor.taxonomy_catalog.resolve import resolve_entry_point_path
from bde_xbrl_editor.taxonomy_catalog.scraper import (
    bundled_catalog_path,
    default_generated_catalog_path,
    run_catalog_scrape,
)
from bde_xbrl_editor.ui import theme
from bde_xbrl_editor.ui.loading import InstanceLoadWorker, TaxonomyLoadWorker
from bde_xbrl_editor.ui.widgets.catalog_updates_dialog import CatalogUpdatesDialog
from bde_xbrl_editor.ui.widgets.loader_settings_dialog import (
    add_recent_file,
    add_recent_instance,
    load_catalog_web_check,
    load_taxonomy_catalog_path,
    save_catalog_last_seen,
    save_catalog_web_check,
    save_taxonomy_catalog_path,
)
from bde_xbrl_editor.ui.widgets.progress_dialog import TaxonomyProgressDialog
from bde_xbrl_editor.ui.widgets.taxonomy_loader_widget import _RecentFileRow

_CATALOG_ACCENT = "#1E4D72"
_CATALOG_ACCENT_HOVER = "#163A57"
_CATALOG_SURFACE = "#F4F6F8"
_UPDATE_BORDER = "#F59E0B"
_UPDATE_BG = "#FFFBEB"
_NEW_BORDER = "#10B981"
_NEW_BG = "#ECFDF5"

_CARD_STATE_NONE = ""
_CARD_STATE_DOCUMENTS = "documents"
_CARD_STATE_TAXONOMY = "taxonomy"
_CARD_STATE_NEW = "new"


class _CardHeader(QFrame):
    """Clickable card header — QPushButton cannot host child layouts on macOS."""

    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TaxonomyCardHeader")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hovered = False
        self._apply_style()

    def _apply_style(self) -> None:
        background = theme.HOVER_BG if self._hovered else "transparent"
        self.setStyleSheet(
            f"""
            QFrame#TaxonomyCardHeader {{
                background: {background};
                border: none;
                border-radius: 6px;
            }}
            """
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._hovered = True
        self._apply_style()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._hovered = False
        self._apply_style()
        super().leaveEvent(event)


class _TaxonomyCard(QFrame):
    """Collapsible taxonomy card with entry points and reporting documents."""

    load_entry_point = Signal(str, str)  # url, alternate_url (entry point name)

    def __init__(
        self,
        taxonomy: Taxonomy,
        *,
        change_state: str = _CARD_STATE_NONE,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._taxonomy = taxonomy
        self._change_state = change_state
        self._expanded = False
        self.setObjectName("TaxonomyCatalogCard")
        self._apply_card_style()
        self._build_ui()

    def _apply_card_style(self) -> None:
        is_new = self._change_state == _CARD_STATE_NEW
        has_update = self._change_state in {_CARD_STATE_TAXONOMY, _CARD_STATE_DOCUMENTS}
        if self._change_state == _CARD_STATE_NONE:
            has_update = self._taxonomy.has_updates
        border = _NEW_BORDER if is_new else (_UPDATE_BORDER if has_update else theme.BORDER)
        ring = f"border: 2px solid {border};" if is_new or has_update else ""
        self.setStyleSheet(
            f"""
            QFrame#TaxonomyCatalogCard {{
                background: {theme.SURFACE_BG};
                border: 1px solid {border};
                border-radius: 10px;
                {ring}
            }}
            QFrame#TaxonomyCatalogCard QLabel {{
                color: {theme.TEXT_MAIN};
                background: transparent;
            }}
            QFrame#TaxonomyCatalogCard QPushButton {{
                background: {theme.SURFACE_BG};
                color: {theme.TEXT_MAIN};
                border: 1px solid {theme.BORDER};
            }}
            """
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(8)

        header = _CardHeader()
        header.clicked.connect(self._toggle_expanded)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(4, 4, 4, 4)
        header_layout.setSpacing(4)

        title_row = QHBoxLayout()
        name_lbl = QLabel(self._taxonomy.name)
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {theme.TEXT_MAIN}; background: transparent;"
        )
        title_row.addWidget(name_lbl, stretch=1)

        badges = QVBoxLayout()
        badges.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        if self._change_state == _CARD_STATE_NEW:
            badges.addWidget(self._badge("Taxonomía nueva", kind="new"))
        elif self._change_state == _CARD_STATE_TAXONOMY or self._taxonomy.has_entry_point_updates:
            badges.addWidget(self._badge("Taxonomía actualizada"))
        if self._change_state == _CARD_STATE_DOCUMENTS or self._taxonomy.has_reporting_file_updates:
            badges.addWidget(self._badge("Documentos actualizados"))
        status_text = "Vigente" if self._taxonomy.status == "vigente" else "No vigente"
        status_color = "#065F46" if self._taxonomy.status == "vigente" else theme.TEXT_MUTED
        status_bg = "#D1FAE5" if self._taxonomy.status == "vigente" else theme.SURFACE_ALT_BG
        status_lbl = QLabel(status_text)
        status_lbl.setStyleSheet(
            f"background: {status_bg}; color: {status_color}; font-size: 10px;"
            f" font-weight: 650; padding: 3px 8px; border-radius: 10px;"
        )
        badges.addWidget(status_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        if self._taxonomy.date:
            date_lbl = QLabel(self._taxonomy.date)
            date_lbl.setStyleSheet(
                f"color: {theme.TEXT_MUTED}; font-size: 10px; background: transparent;"
            )
            badges.addWidget(date_lbl, alignment=Qt.AlignmentFlag.AlignRight)
        title_row.addLayout(badges)
        header_layout.addLayout(title_row)

        cat_lbl = QLabel(self._taxonomy.category)
        cat_lbl.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px; background: transparent;")
        header_layout.addWidget(cat_lbl)
        if self._taxonomy.subcategory:
            sub_lbl = QLabel(self._taxonomy.subcategory)
            sub_lbl.setStyleSheet(
                f"color: {theme.TEXT_SUBTLE}; font-size: 11px; background: transparent;"
            )
            header_layout.addWidget(sub_lbl)

        ep_count = len(self._taxonomy.entry_points)
        doc_count = len(self._taxonomy.reporting_files)
        meta = f"{ep_count} punto(s) de entrada"
        if doc_count:
            meta += f" · {doc_count} documento(s)"
        meta_row = QHBoxLayout()
        meta_lbl = QLabel(meta)
        meta_lbl.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 11px; background: transparent;"
        )
        meta_row.addWidget(meta_lbl, stretch=1)
        if len(self._taxonomy.entry_points) == 1:
            ep = self._taxonomy.entry_points[0]
            quick_load = QPushButton("Cargar taxonomía")
            quick_load.setCursor(Qt.CursorShape.PointingHandCursor)
            quick_load.clicked.connect(
                lambda _checked=False, u=ep.url, n=ep.name: self.load_entry_point.emit(u, n)
            )
            quick_load.setStyleSheet(self._primary_chip_style())
            meta_row.addWidget(quick_load)

        meta_sep = QFrame()
        meta_sep.setFrameShape(QFrame.Shape.HLine)
        meta_sep.setStyleSheet(f"color: {theme.BORDER}; background: {theme.BORDER}; max-height: 1px;")
        header_layout.addWidget(meta_sep)
        header_layout.addLayout(meta_row)
        root.addWidget(header)

        self._details = QWidget()
        details_layout = QVBoxLayout(self._details)
        details_layout.setContentsMargins(4, 0, 4, 4)
        details_layout.setSpacing(10)

        if self._taxonomy.owner or self._taxonomy.spec_version or self._taxonomy.comments:
            meta_grid = QLabel(
                " · ".join(
                    part
                    for part in (
                        f"Propietario: {self._taxonomy.owner}" if self._taxonomy.owner else "",
                        self._taxonomy.spec_version if self._taxonomy.spec_version else "",
                        self._taxonomy.comments if self._taxonomy.comments else "",
                    )
                    if part
                )
            )
            meta_grid.setWordWrap(True)
            meta_grid.setStyleSheet(
                f"color: {theme.TEXT_MAIN}; font-size: 11px; background: transparent;"
            )
            details_layout.addWidget(meta_grid)

        if self._taxonomy.entry_points:
            details_layout.addWidget(self._section_title("Puntos de entrada"))
            for ep in self._taxonomy.entry_points:
                details_layout.addWidget(self._entry_point_row(ep))

        if self._taxonomy.reporting_files:
            details_layout.addWidget(self._section_title("Documentos de reporting"))
            for doc in self._taxonomy.reporting_files:
                details_layout.addWidget(self._resource_row(doc.label, doc.url, doc.is_updated_since_last_check))

        if self._taxonomy.source_url:
            link_btn = QPushButton("Abrir página BDE")
            link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            link_btn.clicked.connect(lambda: webbrowser.open(self._taxonomy.source_url))
            link_btn.setStyleSheet(self._link_btn_style())
            details_layout.addWidget(link_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self._details.setVisible(False)
        root.addWidget(self._details)

    def _badge(self, text: str, *, kind: str = "update") -> QLabel:
        lbl = QLabel(text)
        background = _NEW_BG if kind == "new" else _UPDATE_BG
        color = "#047857" if kind == "new" else "#92400E"
        lbl.setStyleSheet(
            f"background: {background}; color: {color}; font-size: 10px; font-weight: 650;"
            f" padding: 3px 8px; border-radius: 10px;"
        )
        return lbl

    def _section_title(self, text: str) -> QLabel:
        lbl = QLabel(text.upper())
        lbl.setStyleSheet(
            f"color: {theme.TEXT_SUBTLE}; font-size: 10px; font-weight: 700;"
            f" letter-spacing: 0.06em; background: transparent;"
        )
        return lbl

    def _entry_point_row(self, ep: EntryPoint) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        name_lbl = QLabel(ep.url)
        name_lbl.setWordWrap(True)
        name_lbl.setToolTip(ep.name or ep.url)
        name_lbl.setStyleSheet(f"color: {theme.TEXT_MAIN}; font-size: 11px; background: transparent;")
        if ep.is_updated_since_last_check:
            name_lbl.setStyleSheet(
                f"color: #92400E; font-size: 11px; font-weight: 650; background: {_UPDATE_BG};"
                f" padding: 4px 6px; border-radius: 4px;"
            )
        layout.addWidget(name_lbl, stretch=1)

        load_btn = QPushButton("Cargar")
        load_btn.setFixedHeight(28)
        load_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        load_btn.clicked.connect(
            lambda _checked=False, u=ep.url, n=ep.name: self.load_entry_point.emit(u, n)
        )
        load_btn.setStyleSheet(self._primary_chip_style())
        layout.addWidget(load_btn)
        return row

    def _resource_row(self, label: str, url: str, updated: bool) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 2, 0, 2)
        lbl = QLabel(label)
        lbl.setToolTip(url)
        style = f"color: {theme.TEXT_MAIN}; font-size: 11px; background: transparent;"
        if updated:
            style = (
                f"color: #92400E; font-size: 11px; background: {_UPDATE_BG};"
                f" padding: 4px 6px; border-radius: 4px;"
            )
        lbl.setStyleSheet(style)
        layout.addWidget(lbl, stretch=1)
        open_btn = QPushButton("Abrir")
        open_btn.setFixedHeight(26)
        open_btn.clicked.connect(lambda: webbrowser.open(url))
        open_btn.setStyleSheet(self._link_btn_style())
        layout.addWidget(open_btn)
        return row

    def _toggle_expanded(self) -> None:
        self._expanded = not self._expanded
        self._details.setVisible(self._expanded)

    @staticmethod
    def _primary_chip_style() -> str:
        return (
            f"QPushButton {{ background: {_CATALOG_ACCENT}; color: white; border: none;"
            f" border-radius: 6px; font-size: 11px; font-weight: 650; padding: 4px 12px; }}"
            f"QPushButton:hover {{ background: {_CATALOG_ACCENT_HOVER}; }}"
        )

    @staticmethod
    def _link_btn_style() -> str:
        return (
            f"QPushButton {{ color: {_CATALOG_ACCENT}; border: none; background: transparent;"
            f" font-size: 11px; font-weight: 600; padding: 2px 6px; }}"
            f"QPushButton:hover {{ color: {_CATALOG_ACCENT_HOVER}; background: {theme.HOVER_BG};"
            f" border-radius: 4px; }}"
        )


class _CatalogCheckWorker(QObject):
    """Run the catalog scraper off the UI thread."""

    finished = Signal(object, object, str, str)  # data, report, path, checked_at
    error = Signal(str, str)  # message, checked_at

    def __init__(self, previous_data: TaxonomyCatalogData | None) -> None:
        super().__init__()
        self._previous_data = previous_data
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        checked_at = datetime.now(UTC).isoformat()
        try:
            catalog_path = run_catalog_scrape(should_cancel=lambda: self._cancelled)
            data = load_catalog(catalog_path)
            report = detect_catalog_delta(self._previous_data, data)
        except Exception as exc:  # noqa: BLE001
            if self._cancelled:
                return
            self.error.emit(str(exc), checked_at)
            return
        self.finished.emit(data, report, str(catalog_path), checked_at)


class TaxonomyCatalogLoaderWidget(QWidget):
    """Welcome screen that browses taxonomies from taxonomies.json."""

    taxonomy_loaded = Signal(object)
    instance_loaded = Signal(object, object)
    settings_changed = Signal()
    status_message_changed = Signal(str)

    def __init__(
        self,
        cache: TaxonomyCache | None = None,
        settings: LoaderSettings | None = None,
        *,
        catalog_path: str | Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._cache = cache or TaxonomyCache()
        self._settings = settings or LoaderSettings()
        self._loader = TaxonomyLoader(cache=self._cache, settings=self._settings)
        self._catalog_path_override = catalog_path
        self._catalog_data: TaxonomyCatalogData | None = None
        self._active_catalog_path: Path | None = None
        self._thread: QThread | None = None
        self._worker: TaxonomyLoadWorker | None = None
        self._inst_thread: QThread | None = None
        self._inst_worker: InstanceLoadWorker | None = None
        self._catalog_check_thread: QThread | None = None
        self._catalog_check_worker: _CatalogCheckWorker | None = None
        self._catalog_check_timer: QTimer | None = None
        self._progress_dialog: TaxonomyProgressDialog | None = None
        self.last_taxonomy_load_timing: LoadTiming | None = None
        self.last_instance_load_timing: LoadTiming | None = None
        self._taxonomy_load_started_at: float | None = None
        self._instance_load_started_at: float | None = None
        self._pending_entry_url: str | None = None
        self._pending_local_path: str | None = None
        self._pending_instance_path: str | None = None
        self._pending_catalog_data: TaxonomyCatalogData | None = None
        self._pending_catalog_report: CatalogChangeReport | None = None
        self._pending_catalog_path: str | None = None
        self._visible_catalog_update_refs: tuple[CatalogFileRef, ...] = ()
        self._catalog_header_update_counts = (0, 0, 0)  # taxonomies, entry points, files
        self._taxonomy_card_states: dict[str, str] = {}
        self._catalog_check_running = False
        self._catalog_check_error: str | None = None
        self._last_catalog_check_at, _ = load_catalog_web_check()
        self._instance_open_dialog: QDialog | None = None
        self._inst_path_edit: QLineEdit | None = None
        self._load_inst_btn: QPushButton | None = None
        self._loading = False
        self._setup_ui()
        self._reload_catalog(show_errors=True)
        self._update_catalog_check_ui()
        self._catalog_check_timer = QTimer(self)
        self._catalog_check_timer.setSingleShot(True)
        self._catalog_check_timer.timeout.connect(self._maybe_start_scheduled_catalog_check)
        self._catalog_check_timer.start(0)
        self.destroyed.connect(self._cancel_catalog_check)

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"TaxonomyCatalogLoaderWidget {{ background: {_CATALOG_SURFACE}; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QFrame()
        header.setObjectName("CatalogLoaderHeader")
        header.setStyleSheet(
            f"""
            QFrame#CatalogLoaderHeader {{
                background: {theme.SURFACE_BG};
                border-bottom: 1px solid {theme.BORDER};
            }}
            """
        )
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(28, 18, 28, 14)
        header_layout.setSpacing(6)

        top_row = QHBoxLayout()
        title = QLabel("Información financiera BDE")
        title.setStyleSheet(
            f"font-size: 22px; font-weight: 750; color: {theme.TEXT_MAIN}; background: transparent;"
        )
        top_row.addWidget(title, stretch=1)

        self._catalog_check_panel = QFrame()
        self._catalog_check_panel.setObjectName("CatalogCheckPanel")
        check_layout = QHBoxLayout(self._catalog_check_panel)
        check_layout.setContentsMargins(10, 6, 10, 6)
        check_layout.setSpacing(8)
        self._catalog_check_label = QLabel()
        self._catalog_check_label.setWordWrap(False)
        self._catalog_check_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 11px; background: transparent;"
        )
        check_layout.addWidget(self._catalog_check_label, stretch=1)
        self._catalog_check_now_btn = QPushButton("Comprobar")
        self._catalog_check_now_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._catalog_check_now_btn.clicked.connect(
            lambda _checked=False: self._start_catalog_update_check(force=True)
        )
        self._catalog_check_now_btn.setStyleSheet(self._link_btn_style())
        check_layout.addWidget(self._catalog_check_now_btn)
        self._catalog_view_updates_btn = QPushButton("Ver cambios")
        self._catalog_view_updates_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._catalog_view_updates_btn.clicked.connect(self._show_pending_catalog_updates)
        self._catalog_view_updates_btn.setStyleSheet(self._link_btn_style())
        check_layout.addWidget(self._catalog_view_updates_btn)
        self._catalog_apply_updates_btn = QPushButton("Actualizar")
        self._catalog_apply_updates_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._catalog_apply_updates_btn.clicked.connect(self._apply_pending_catalog_update)
        self._catalog_apply_updates_btn.setStyleSheet(self._primary_btn_style())
        check_layout.addWidget(self._catalog_apply_updates_btn)
        top_row.addWidget(self._catalog_check_panel, stretch=0)

        settings_btn = QPushButton("Settings…")
        settings_btn.clicked.connect(self._on_settings)
        settings_btn.setStyleSheet(self._secondary_btn_style())
        top_row.addWidget(settings_btn)
        header_layout.addLayout(top_row)

        self._meta_label = QLabel()
        self._meta_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 12px; background: transparent;"
        )
        header_layout.addWidget(self._meta_label)
        outer.addWidget(header)

        body = QHBoxLayout()
        body.setContentsMargins(20, 16, 20, 16)
        body.setSpacing(16)

        catalog_col = QVBoxLayout()
        catalog_col.setSpacing(10)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Buscar taxonomías, categorías, documentos…")
        self._search_edit.textChanged.connect(self._refresh_cards)
        self._search_edit.setStyleSheet(self._input_style())
        controls.addWidget(self._search_edit, stretch=2)

        self._status_combo = QComboBox()
        self._status_combo.addItem("Todos los estados", "all")
        self._status_combo.addItem("Vigente", "vigente")
        self._status_combo.addItem("No vigente", "no-vigente")
        self._status_combo.currentIndexChanged.connect(self._refresh_cards)
        controls.addWidget(self._status_combo)

        self._category_combo = QComboBox()
        self._category_combo.addItem("Todas las categorías", "")
        self._category_combo.currentIndexChanged.connect(self._refresh_cards)
        controls.addWidget(self._category_combo, stretch=1)

        self._sort_combo = QComboBox()
        self._sort_combo.addItem("Fecha ↓", "date-desc")
        self._sort_combo.addItem("Fecha ↑", "date-asc")
        self._sort_combo.addItem("Nombre A–Z", "name-asc")
        self._sort_combo.addItem("Nombre Z–A", "name-desc")
        self._sort_combo.currentIndexChanged.connect(self._refresh_cards)
        controls.addWidget(self._sort_combo)
        catalog_col.addLayout(controls)

        self._results_label = QLabel()
        self._results_label.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 11px; background: transparent;"
        )
        catalog_col.addWidget(self._results_label)

        self._cards_scroll = QScrollArea()
        self._cards_scroll.setWidgetResizable(True)
        self._cards_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._cards_host = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_host)
        self._cards_layout.setContentsMargins(0, 0, 8, 0)
        self._cards_layout.setSpacing(12)
        self._cards_layout.addStretch()
        self._cards_scroll.setWidget(self._cards_host)
        catalog_col.addWidget(self._cards_scroll, stretch=1)

        catalog_wrap = QWidget()
        catalog_wrap.setLayout(catalog_col)
        body.addWidget(catalog_wrap, stretch=3)

        side_wrap = QWidget()
        side_wrap.setObjectName("CatalogSidePanel")
        self._side_panel_layout = QVBoxLayout(side_wrap)
        self._side_panel_layout.setContentsMargins(0, 0, 0, 0)
        self._side_panel_layout.setSpacing(16)
        self._open_instance_btn = QPushButton("Abrir instancia…")
        self._open_instance_btn.setObjectName("OpenInstanceButton")
        self._open_instance_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_instance_btn.clicked.connect(self._show_instance_open_dialog)
        self._open_instance_btn.setStyleSheet(self._primary_btn_style())
        self._global_resources_panel = self._build_global_resources_panel()
        self._side_panel_layout.addWidget(self._open_instance_btn, stretch=0)
        self._side_panel_layout.addWidget(self._global_resources_panel, stretch=1)
        body.addWidget(side_wrap, stretch=1)
        outer.addLayout(body, stretch=1)

    def _build_global_resources_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("CatalogGlobalResourcesPanel")
        panel.setStyleSheet(
            f"""
            QFrame#CatalogGlobalResourcesPanel {{
                background: {theme.SURFACE_BG};
                border: 1px solid {theme.BORDER};
                border-radius: 10px;
            }}
            QFrame#CatalogGlobalResourcesPanel QLabel {{
                background: transparent;
            }}
            """
        )
        panel.setVisible(False)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        title = QLabel("Global resources")
        title.setStyleSheet(
            f"font-size: 14px; font-weight: 750; color: {theme.TEXT_MAIN}; background: transparent;"
        )
        layout.addWidget(title)

        subtitle = QLabel("General BDE documents and related taxonomy links.")
        subtitle.setStyleSheet(
            f"color: {theme.TEXT_MUTED}; font-size: 11px; background: transparent;"
        )
        layout.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setObjectName("GlobalResourcesScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea#GlobalResourcesScroll {{ background: {theme.SURFACE_BG}; border: none; }}"
        )
        scroll.viewport().setStyleSheet(f"background: {theme.SURFACE_BG};")
        self._global_resources_host = QWidget()
        self._global_resources_host.setObjectName("GlobalResourcesHost")
        self._global_resources_host.setStyleSheet(f"background: {theme.SURFACE_BG};")
        self._global_resources_layout = QVBoxLayout(self._global_resources_host)
        self._global_resources_layout.setContentsMargins(0, 0, 4, 0)
        self._global_resources_layout.setSpacing(6)
        scroll.setWidget(self._global_resources_host)
        layout.addWidget(scroll)
        return panel

    def _show_instance_open_dialog(self) -> None:
        dialog = self._build_instance_dialog()
        self._instance_open_dialog = dialog
        dialog.finished.connect(lambda _result, current=dialog: self._clear_instance_dialog(current))
        dialog.exec()

    def _clear_instance_dialog(self, dialog: QDialog) -> None:
        if self._instance_open_dialog is dialog:
            self._instance_open_dialog = None
            self._inst_path_edit = None
            self._load_inst_btn = None

    def _build_instance_dialog(self) -> QDialog:
        dialog = QDialog(self)
        dialog.setObjectName("InstanceOpenDialog")
        dialog.setWindowTitle("Abrir instancia existente")
        dialog.setModal(True)
        dialog.setMinimumSize(620, 520)
        dialog.setStyleSheet(
            f"""
            QDialog#InstanceOpenDialog {{
                background: {theme.SURFACE_BG};
            }}
            QDialog#InstanceOpenDialog QLabel {{
                border: none;
                background: transparent;
            }}
            """
        )
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)

        title = QLabel("Abrir instancia existente")
        title.setStyleSheet(
            f"font-size: 16px; font-weight: 750; color: {theme.TEXT_MAIN}; background: transparent;"
        )
        layout.addWidget(title)

        hint = QLabel(
            "Selecciona un archivo .xbrl si ya tienes un envío preparado. "
            "La taxonomía se resolverá automáticamente."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 11px; background: transparent;")
        layout.addWidget(hint)

        from bde_xbrl_editor.ui.widgets.loader_settings_dialog import load_recent_instances

        self._inst_path_edit = QLineEdit()
        self._inst_path_edit.setPlaceholderText("Archivo de instancia…")
        self._inst_path_edit.setStyleSheet(self._input_style())
        layout.addWidget(self._inst_path_edit)

        browse_row = QHBoxLayout()
        browse_btn = QPushButton("Examinar…")
        browse_btn.clicked.connect(self._on_browse_instance)
        browse_btn.setStyleSheet(self._secondary_btn_style())
        self._load_inst_btn = QPushButton("Cargar instancia")
        self._load_inst_btn.clicked.connect(self._on_load_instance)
        self._load_inst_btn.setStyleSheet(self._primary_btn_style())
        browse_row.addWidget(browse_btn)
        browse_row.addWidget(self._load_inst_btn)
        layout.addLayout(browse_row)

        recent = load_recent_instances()
        if recent:
            layout.addSpacing(8)
            rec_title = QLabel("Recientes")
            rec_title.setStyleSheet(
                f"color: {theme.TEXT_MAIN}; font-size: 12px; font-weight: 700; background: transparent;"
            )
            layout.addWidget(rec_title)
            recent_scroll = QScrollArea()
            recent_scroll.setObjectName("RecentInstancesScroll")
            recent_scroll.setWidgetResizable(True)
            recent_scroll.setFrameShape(QFrame.Shape.NoFrame)
            recent_scroll.setStyleSheet(
                f"QScrollArea#RecentInstancesScroll {{ background: {theme.SURFACE_BG}; border: none; }}"
            )
            recent_scroll.viewport().setStyleSheet(f"background: {theme.SURFACE_BG};")
            recent_host = QWidget()
            recent_host.setObjectName("RecentInstancesHost")
            recent_host.setStyleSheet(f"background: {theme.SURFACE_BG};")
            recent_layout = QVBoxLayout(recent_host)
            recent_layout.setContentsMargins(0, 0, 4, 0)
            recent_layout.setSpacing(8)
            for path in recent:
                row = _RecentFileRow(path)
                row.clicked.connect(self._on_recent_instance_clicked)
                recent_layout.addWidget(row)
            recent_layout.addStretch()
            recent_scroll.setWidget(recent_host)
            layout.addWidget(recent_scroll, stretch=1)

        if not recent:
            layout.addStretch()
        return dialog

    def _reload_catalog(self, *, show_errors: bool) -> None:
        explicit = self._catalog_path_override or load_taxonomy_catalog_path()
        path = resolve_catalog_path(explicit)
        if path is None:
            if show_errors:
                candidates = "\n".join(
                    f"  • {p}"
                    for p in (
                        default_generated_catalog_path(),
                        bundled_catalog_path(),
                    )
                )
                QMessageBox.warning(
                    self,
                    "Catálogo no encontrado",
                    "No se encontró taxonomies.json.\n\n"
                    "Configura la ruta en Settings → Catalog JSON, o ejecuta "
                    "bde-xbrl-catalog-scrape.\n\n"
                    f"Ubicaciones probadas:\n{candidates}",
                )
            self._catalog_data = None
            self._active_catalog_path = None
            self._visible_catalog_update_refs = ()
            self._refresh_global_resources()
            self._meta_label.setText("Catálogo no disponible")
            self._refresh_cards()
            return
        try:
            data = load_catalog(path)
        except TaxonomyCatalogError as exc:
            if show_errors:
                QMessageBox.critical(self, "Error al cargar catálogo", str(exc))
            self._catalog_data = None
            self._active_catalog_path = None
            self._visible_catalog_update_refs = ()
            self._refresh_global_resources()
            self._meta_label.setText("Error al cargar el catálogo")
            self._refresh_cards()
            return
        self._active_catalog_path = path
        self._apply_catalog_data(data)

    def _apply_catalog_data(self, data: TaxonomyCatalogData) -> None:
        self._catalog_data = data
        self._update_catalog_meta_label()
        self._refresh_global_resources()

        self._category_combo.blockSignals(True)
        current_cat = self._category_combo.currentData()
        self._category_combo.clear()
        self._category_combo.addItem("Todas las categorías", "")
        for category in unique_categories(self._catalog_data.taxonomies):
            self._category_combo.addItem(category, category)
        if current_cat:
            idx = self._category_combo.findData(current_cat)
            if idx >= 0:
                self._category_combo.setCurrentIndex(idx)
        self._category_combo.blockSignals(False)
        self._refresh_cards()

    def _catalog_update_refs_by_url(self) -> dict[str, CatalogFileRef]:
        if self._catalog_data is None:
            return {}
        refs = {ref.url: ref for ref in collect_flagged_updates(self._catalog_data)}
        refs.update({ref.url: ref for ref in self._visible_catalog_update_refs})
        return refs

    def _global_resources(self) -> tuple[tuple[str, ModuleFile, bool], ...]:
        if self._catalog_data is None:
            return ()
        update_refs = self._catalog_update_refs_by_url()
        rows: list[tuple[str, ModuleFile, bool]] = []
        for doc in self._catalog_data.general_documents:
            rows.append((
                "General document",
                doc,
                doc.is_updated_since_last_check or doc.url in update_refs,
            ))
        for link in self._catalog_data.taxonomy_related_links:
            rows.append((
                "Related link",
                link,
                link.is_updated_since_last_check or link.url in update_refs,
            ))
        return tuple(rows)

    def _refresh_global_resources(self) -> None:
        while self._global_resources_layout.count():
            item = self._global_resources_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        resources = self._global_resources()
        self._global_resources_panel.setVisible(bool(resources))
        if not resources:
            return

        for kind, resource, updated in resources:
            row = QFrame()
            row.setObjectName("GlobalResourceRow")
            row.setStyleSheet(
                self._global_resource_row_style(updated=updated)
            )
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 6, 8, 6)
            row_layout.setSpacing(8)

            label = QLabel(f"{kind} · {resource.label}")
            label.setWordWrap(True)
            label.setToolTip(resource.url)
            label.setStyleSheet(
                f"color: {theme.TEXT_MAIN}; font-size: 11px; background: transparent;"
            )
            row_layout.addWidget(label, stretch=1)

            if updated:
                badge = QLabel("Actualizado")
                badge.setStyleSheet(
                    f"background: {_UPDATE_BG}; color: #92400E; font-size: 10px;"
                    f" font-weight: 650; padding: 3px 8px; border-radius: 10px;"
                )
                row_layout.addWidget(badge, alignment=Qt.AlignmentFlag.AlignTop)

            open_btn = QPushButton("Abrir")
            open_btn.setFixedHeight(26)
            open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            open_btn.clicked.connect(
                lambda _checked=False, url=resource.url: webbrowser.open(url)
            )
            open_btn.setStyleSheet(self._link_btn_style())
            row_layout.addWidget(open_btn)
            self._global_resources_layout.addWidget(row)
        self._global_resources_layout.addStretch()

    @staticmethod
    def _global_resource_row_style(*, updated: bool) -> str:
        if updated:
            return (
                f"QFrame#GlobalResourceRow {{ background: {_UPDATE_BG};"
                f" border: 2px solid {_UPDATE_BORDER}; border-radius: 6px; }}"
            )
        return (
            f"QFrame#GlobalResourceRow {{ background: {theme.SURFACE_BG};"
            " border: 1px solid transparent; border-radius: 6px; }}"
        )

    def _update_catalog_meta_label(self) -> None:
        if self._catalog_data is None:
            return
        meta = self._catalog_data.metadata
        try:
            last_run = datetime.fromisoformat(meta.last_run.replace("Z", "+00:00"))
            last_run_text = last_run.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            last_run_text = meta.last_run

        reporting_total = sum(len(t.reporting_files) for t in self._catalog_data.taxonomies)
        meta_parts = [
            f"Última actualización: {last_run_text}",
            f"{meta.total_count} taxonomías",
        ]
        if reporting_total:
            meta_parts.append(f"{reporting_total} documentos de reporting")
        update_parts = self._catalog_header_update_parts()
        if update_parts:
            meta_parts.extend(update_parts)
        self._meta_label.setText(" • ".join(meta_parts))
        self._meta_label.setToolTip(self._catalog_header_update_tooltip())

    def _catalog_header_update_parts(self) -> list[str]:
        counts = self._catalog_header_update_counts
        if not any(counts) and self._catalog_data is not None:
            meta = self._catalog_data.metadata
            counts = (
                meta.taxonomies_with_updates or 0,
                meta.entry_points_with_updates or 0,
                meta.files_with_updates or 0,
            )

        taxonomies, entry_points, files = counts
        parts: list[str] = []
        if taxonomies:
            parts.append(
                f"{taxonomies} taxonomía{'s' if taxonomies != 1 else ''} actualizada"
                f"{'s' if taxonomies != 1 else ''}"
            )
        if entry_points:
            parts.append(f"{entry_points} punto(s) de entrada actualizado(s)")
        if files:
            parts.append(f"{files} archivo(s) actualizado(s)")
        return parts

    def _catalog_header_update_tooltip(self) -> str:
        if self._catalog_data is None:
            return ""
        updated_taxonomies = [
            taxonomy.name
            for taxonomy in self._catalog_data.taxonomies
            if taxonomy.has_entry_point_updates or taxonomy.has_reporting_file_updates
        ]
        refs = tuple(
            sorted(
                self._catalog_update_refs_by_url().values(),
                key=lambda ref: (ref.taxonomy_name.lower(), ref.label.lower()),
            )
        )
        if not updated_taxonomies and not refs:
            return ""
        lines: list[str] = []
        if refs:
            lines.append("Archivos actualizados:")
            lines.extend(
                f"- {ref.taxonomy_name}: {ref.label}"
                if ref.taxonomy_name
                else f"- {ref.label}"
                for ref in refs
            )
        elif updated_taxonomies:
            lines.append("Taxonomías actualizadas:")
            lines.extend(f"- {name}" for name in updated_taxonomies)
        return "\n".join(lines)

    def _acknowledge_catalog_state(self) -> None:
        if self._catalog_data is None:
            return
        save_catalog_last_seen(
            self._catalog_data.metadata.last_run,
            build_file_snapshot(self._catalog_data),
        )

    def _maybe_start_scheduled_catalog_check(self) -> None:
        if not self.isVisible():
            self._emit_catalog_status()
            return
        if self._checked_within_last_day():
            self._emit_catalog_status()
            return
        self._start_catalog_update_check(force=False)

    def _checked_within_last_day(self) -> bool:
        checked_at = self._parse_check_timestamp(self._last_catalog_check_at)
        if checked_at is None:
            return False
        return datetime.now(UTC) - checked_at < timedelta(hours=24)

    def _start_catalog_update_check(self, *, force: bool) -> None:
        if self._catalog_check_running:
            return
        if not force and self._checked_within_last_day():
            self._emit_catalog_status()
            return

        self._catalog_check_error = None
        self._catalog_check_running = True
        self._update_catalog_check_ui()

        baseline_data = self._pending_catalog_data or self._catalog_data
        self._catalog_check_worker = _CatalogCheckWorker(baseline_data)
        self._catalog_check_thread = QThread(self)
        self._catalog_check_worker.moveToThread(self._catalog_check_thread)
        self._catalog_check_thread.started.connect(self._catalog_check_worker.run)
        self._catalog_check_worker.finished.connect(
            self._on_catalog_check_finished,
            Qt.ConnectionType.QueuedConnection,
        )
        self._catalog_check_worker.error.connect(
            self._on_catalog_check_error,
            Qt.ConnectionType.QueuedConnection,
        )
        self._catalog_check_thread.start()

    def _on_catalog_check_finished(
        self,
        data: object,
        report: object,
        catalog_path: str,
        checked_at: str,
    ) -> None:
        self._cleanup_catalog_check_thread()
        self._catalog_check_running = False
        self._last_catalog_check_at = checked_at
        save_catalog_web_check(checked_at, catalog_path)

        catalog_data = data if isinstance(data, TaxonomyCatalogData) else None
        change_report = report if isinstance(report, CatalogChangeReport) else None
        if catalog_data is None or change_report is None:
            self._catalog_check_error = "El scraper devolvió un resultado no válido"
            self._update_catalog_check_ui()
            return

        if self._catalog_data is None:
            self._active_catalog_path = Path(catalog_path)
            self._catalog_path_override = catalog_path
            save_taxonomy_catalog_path(catalog_path)
            self._catalog_header_update_counts = (0, 0, 0)
            self._taxonomy_card_states = {}
            self._visible_catalog_update_refs = ()
            self._apply_catalog_data(catalog_data)
            self._acknowledge_catalog_state()
            self._update_catalog_check_ui()
            return

        available_report = detect_catalog_delta(self._catalog_data, catalog_data)
        self._catalog_header_update_counts = self._change_report_counts(available_report)
        next_states = self._taxonomy_change_states(self._catalog_data, catalog_data, available_report)
        if available_report.updated_files:
            self._pending_catalog_data = catalog_data
            self._pending_catalog_report = available_report
            self._pending_catalog_path = catalog_path
            self._visible_catalog_update_refs = available_report.updated_files
        else:
            self._pending_catalog_data = None
            self._pending_catalog_report = None
            self._pending_catalog_path = None
            self._visible_catalog_update_refs = ()
            next_states = {}
        self._taxonomy_card_states = next_states
        self._refresh_global_resources()
        self._update_catalog_meta_label()
        self._update_catalog_check_ui()

    def _on_catalog_check_error(self, message: str, checked_at: str) -> None:
        self._cleanup_catalog_check_thread()
        self._catalog_check_running = False
        self._last_catalog_check_at = checked_at
        self._catalog_check_error = message
        save_catalog_web_check(checked_at, None)
        self._update_catalog_check_ui()

    def _cleanup_catalog_check_thread(self) -> None:
        if self._catalog_check_thread is not None:
            self._catalog_check_thread.quit()
            self._catalog_check_thread.wait()
        self._catalog_check_thread = None
        self._catalog_check_worker = None

    def _cancel_catalog_check(self, *_args: object) -> None:
        if self._catalog_check_timer is not None:
            self._catalog_check_timer.stop()
            self._catalog_check_timer = None
        if self._catalog_check_worker is not None:
            self._catalog_check_worker.cancel()
        self._cleanup_catalog_check_thread()

    def _show_pending_catalog_updates(self) -> None:
        if self._pending_catalog_report is None:
            return
        CatalogUpdatesDialog(self._pending_catalog_report, self).exec()

    def _apply_pending_catalog_update(self) -> None:
        if self._pending_catalog_data is None or self._pending_catalog_path is None:
            return
        applied_counts = (
            self._change_report_counts(self._pending_catalog_report)
            if self._pending_catalog_report is not None
            else (0, 0, 0)
        )
        self._active_catalog_path = Path(self._pending_catalog_path)
        self._catalog_path_override = self._pending_catalog_path
        save_taxonomy_catalog_path(self._pending_catalog_path)
        self._catalog_header_update_counts = applied_counts
        self._visible_catalog_update_refs = (
            self._pending_catalog_report.updated_files
            if self._pending_catalog_report is not None
            else ()
        )
        self._apply_catalog_data(self._pending_catalog_data)
        self._show_pending_catalog_updates()
        self._acknowledge_catalog_state()
        self._pending_catalog_data = None
        self._pending_catalog_report = None
        self._pending_catalog_path = None
        self._update_catalog_check_ui()

    @staticmethod
    def _taxonomy_change_states(
        previous: TaxonomyCatalogData,
        current: TaxonomyCatalogData,
        report: CatalogChangeReport,
    ) -> dict[str, str]:
        previous_ids = {taxonomy.id for taxonomy in previous.taxonomies}
        taxonomy_ids_by_name = {taxonomy.name: taxonomy.id for taxonomy in current.taxonomies}
        states: dict[str, str] = {
            taxonomy.id: _CARD_STATE_NEW
            for taxonomy in current.taxonomies
            if taxonomy.id not in previous_ids
        }
        for ref in report.updated_files:
            taxonomy_id = taxonomy_ids_by_name.get(ref.taxonomy_name)
            if not taxonomy_id or states.get(taxonomy_id) == _CARD_STATE_NEW:
                continue
            if ref.resource_kind == "entry_point":
                states[taxonomy_id] = _CARD_STATE_TAXONOMY
            elif states.get(taxonomy_id) != _CARD_STATE_TAXONOMY:
                states[taxonomy_id] = _CARD_STATE_DOCUMENTS
        return states

    @staticmethod
    def _change_report_counts(report: CatalogChangeReport) -> tuple[int, int, int]:
        taxonomy_names: set[str] = set()
        entry_points = 0
        files = 0
        for ref in report.updated_files:
            if ref.resource_kind == "entry_point":
                entry_points += 1
                if ref.taxonomy_name:
                    taxonomy_names.add(ref.taxonomy_name)
            else:
                files += 1
                if ref.taxonomy_name not in ("Documentos generales", "Enlaces relacionados"):
                    taxonomy_names.add(ref.taxonomy_name)
        return len(taxonomy_names), entry_points, files

    def _update_catalog_check_ui(self) -> None:
        pending_count = (
            len(self._pending_catalog_report.updated_files)
            if self._pending_catalog_report is not None
            else 0
        )
        if self._catalog_check_running:
            label = "Comprobando cambios en BDE..."
            panel_style = self._catalog_check_panel_style("checking")
        elif pending_count:
            label = f"{pending_count} cambio(s) disponibles"
            panel_style = self._catalog_check_panel_style("updates")
        elif self._catalog_check_error:
            label = "No se pudo comprobar BDE"
            panel_style = self._catalog_check_panel_style("error")
        else:
            label = f"Comprobado: {self._format_check_timestamp(self._last_catalog_check_at)}"
            panel_style = self._catalog_check_panel_style("idle")

        self._catalog_check_panel.setStyleSheet(panel_style)
        self._catalog_check_label.setText(label)
        self._catalog_check_label.setToolTip(
            self._catalog_check_error or self._catalog_header_update_tooltip()
        )
        self._catalog_check_now_btn.setVisible(not pending_count)
        self._catalog_check_now_btn.setEnabled(not self._catalog_check_running)
        self._catalog_view_updates_btn.setVisible(bool(pending_count))
        self._catalog_apply_updates_btn.setVisible(bool(pending_count))
        self._emit_catalog_status()

    def _emit_catalog_status(self) -> None:
        if self._catalog_check_running:
            message = "No taxonomy loaded · comprobando cambios del catálogo BDE en segundo plano"
        else:
            message = (
                "No taxonomy loaded · última comprobación BDE: "
                f"{self._format_check_timestamp(self._last_catalog_check_at)}"
            )
            if self._pending_catalog_report is not None:
                count = len(self._pending_catalog_report.updated_files)
                message += f" · {count} cambio(s) disponibles"
            elif self._catalog_check_error:
                message += " · error al comprobar cambios"
        self.status_message_changed.emit(message)

    @staticmethod
    def _parse_check_timestamp(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @classmethod
    def _format_check_timestamp(cls, value: str | None) -> str:
        parsed = cls._parse_check_timestamp(value)
        if parsed is None:
            return "nunca"
        return parsed.astimezone().strftime("%d/%m/%Y %H:%M")

    def _filtered_taxonomies(self) -> tuple[Taxonomy, ...]:
        if self._catalog_data is None:
            return ()
        status = self._status_combo.currentData() or "all"
        category = self._category_combo.currentData() or ""
        sort = self._sort_combo.currentData() or "date-desc"
        filtered = filter_taxonomies(
            self._catalog_data.taxonomies,
            search=self._search_edit.text(),
            status=status,  # type: ignore[arg-type]
            category=category,
        )
        return sort_taxonomies(filtered, sort)  # type: ignore[arg-type]

    def _refresh_cards(self) -> None:
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        taxonomies = self._filtered_taxonomies()
        count = len(taxonomies)
        self._results_label.setText(
            f"Mostrando {count} resultado{'s' if count != 1 else ''}"
        )

        if self._catalog_data is None:
            empty = QLabel(
                "Configura la ruta al catálogo en Settings o ejecuta "
                "bde-xbrl-catalog-scrape."
            )
            empty.setWordWrap(True)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 40px; background: transparent;")
            self._cards_layout.insertWidget(0, empty)
            return

        for tax in taxonomies:
            change_state = self._taxonomy_card_states.get(
                tax.id,
                self._taxonomy_flag_state(tax),
            )
            card = _TaxonomyCard(
                tax,
                change_state=change_state,
            )
            card.load_entry_point.connect(self._on_entry_point_requested)
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)

    @staticmethod
    def _taxonomy_flag_state(taxonomy: Taxonomy) -> str:
        if taxonomy.has_entry_point_updates:
            return _CARD_STATE_TAXONOMY
        if taxonomy.has_reporting_file_updates:
            return _CARD_STATE_DOCUMENTS
        return _CARD_STATE_NONE

    def load_entry_point_path(self, path: str) -> None:
        """Load a taxonomy from a local entry-point path (reload from menu)."""
        self._start_taxonomy_load(path)

    def _on_entry_point_requested(self, url: str, alternate_url: str = "") -> None:
        if self._loading:
            return
        alternates = tuple(u for u in (alternate_url,) if u and u != url)
        local = resolve_entry_point_path(
            url,
            local_catalog=self._settings.local_catalog,
            alternate_urls=alternates,
        )
        if local is None:
            cache_hint = Path.cwd() / "cache" / "www.bde.es"
            QMessageBox.warning(
                self,
                "Ruta local no encontrada",
                "No se pudo resolver este punto de entrada a un archivo .xsd local.\n\n"
                f"URL: {url}\n"
                + (f"Nombre: {alternate_url}\n" if alternate_url and alternate_url != url else "")
                + "\nDescarga la taxonomía en la carpeta cache (p. ej. "
                f"{cache_hint}) o añade un mapeo en Settings → URL-to-Path Catalog.\n"
                "También puedes usar la pantalla clásica para seleccionar el .xsd directamente.",
            )
            return
        self._start_taxonomy_load(str(local), entry_url=url)

    def _start_taxonomy_load(self, path: str, *, entry_url: str | None = None) -> None:
        self._loading = True
        self._pending_entry_url = entry_url
        self._pending_local_path = path
        self._taxonomy_load_started_at = time.perf_counter()
        self.last_taxonomy_load_timing = None

        progress = self._show_progress_dialog("Loading Taxonomy…", "Initialising taxonomy load…")
        progress.set_context("Taxonomy", path)

        self._worker = TaxonomyLoadWorker(self._loader, path)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._thread.finished.connect(self._worker.deleteLater)
        self._worker.finished.connect(self._on_load_finished, Qt.ConnectionType.QueuedConnection)
        self._worker.error.connect(self._on_load_error, Qt.ConnectionType.QueuedConnection)
        self._worker.progress.connect(
            progress.update_progress,
            Qt.ConnectionType.QueuedConnection,
        )
        self._thread.start()

    def _on_load_finished(self, payload: object) -> None:
        structure, skipped_urls = payload  # type: ignore[misc]
        self._cleanup_thread()
        self._loading = False
        elapsed = 0.0
        if self._taxonomy_load_started_at is not None:
            elapsed = time.perf_counter() - self._taxonomy_load_started_at
        self.last_taxonomy_load_timing = LoadTiming(
            total_seconds=elapsed,
            stages=(StageTiming("taxonomy load", elapsed),),
        )
        local_path = self._pending_local_path or ""
        with contextlib.suppress(OSError):
            if local_path:
                add_recent_file(local_path)
        self._pending_entry_url = None
        self._pending_local_path = None

        if skipped_urls:
            url_list = "\n".join(f"  • {u}" for u in skipped_urls[:20])
            suffix = f"\n  … and {len(skipped_urls) - 20} more" if len(skipped_urls) > 20 else ""
            QMessageBox.warning(
                self,
                "Remote References Skipped",
                "Some remote references were skipped.\n\n"
                f"{url_list}{suffix}",
            )

        if self._progress_dialog is not None and elapsed > 0:
            self._progress_dialog.update_progress(
                f"Taxonomy parsed in {format_duration(elapsed)}",
                100,
                100,
            )
        self._close_progress_dialog()
        self.taxonomy_loaded.emit(structure)

    def _on_load_error(self, message: str) -> None:
        self._cleanup_thread()
        self._loading = False
        self._pending_local_path = None
        self._close_progress_dialog()
        QMessageBox.critical(self, "Taxonomy Load Error", message)

    def _cleanup_thread(self, *, wait: bool = True) -> None:
        worker, thread = self._worker, self._thread
        self._worker = None
        self._thread = None
        if not wait and worker is not None:
            worker.cancel()
        if thread is not None:
            if not wait and thread.parent() is self and (app := QCoreApplication.instance()) is not None:
                thread.setParent(app)
            thread.quit()
            if wait:
                thread.wait()

    def _on_browse_instance(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        if self._inst_path_edit is None:
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open XBRL Instance",
            "",
            "XBRL Files (*.xbrl *.xml);;All Files (*)",
        )
        if path:
            self._inst_path_edit.setText(path)

    def _on_recent_instance_clicked(self, path: str) -> None:
        if self._inst_path_edit is None:
            return
        self._inst_path_edit.setText(path)
        self._on_load_instance()

    def _on_load_instance(self) -> None:
        if self._inst_path_edit is None:
            return
        path = self._inst_path_edit.text().strip()
        if not path:
            QMessageBox.warning(self, "No File Selected", "Please select an XBRL instance file.")
            return
        if not Path(path).exists():
            QMessageBox.warning(self, "File Not Found", f"File not found:\n{path}")
            return

        self._pending_instance_path = path
        if self._load_inst_btn is not None:
            self._load_inst_btn.setEnabled(False)
        self._instance_load_started_at = time.perf_counter()
        progress = self._show_progress_dialog("Loading Instance…", "Initialising instance load…")
        progress.set_context("Instance", path)

        self._inst_worker = InstanceLoadWorker(self._cache, self._settings, path)
        self._inst_thread = QThread(self)
        self._inst_worker.moveToThread(self._inst_thread)
        self._inst_thread.started.connect(self._inst_worker.run)
        self._inst_thread.finished.connect(self._inst_worker.deleteLater)
        self._inst_worker.finished.connect(
            self._on_inst_load_finished, Qt.ConnectionType.QueuedConnection
        )
        self._inst_worker.error.connect(
            self._on_inst_load_error, Qt.ConnectionType.QueuedConnection
        )
        self._inst_worker.progress.connect(
            progress.update_progress,
            Qt.ConnectionType.QueuedConnection,
        )
        self._inst_thread.start()
        if self._instance_open_dialog is not None:
            self._instance_open_dialog.accept()

    def _on_inst_load_finished(self, instance: object, taxonomy: object) -> None:
        self._cleanup_inst_thread()
        if self._load_inst_btn is not None:
            self._load_inst_btn.setEnabled(True)
        with contextlib.suppress(OSError):
            if self._pending_instance_path:
                add_recent_instance(self._pending_instance_path)
        self._pending_instance_path = None
        self._close_progress_dialog()
        self.instance_loaded.emit(instance, taxonomy)

    def _on_inst_load_error(self, message: str) -> None:
        self._cleanup_inst_thread()
        if self._load_inst_btn is not None:
            self._load_inst_btn.setEnabled(True)
        self._pending_instance_path = None
        self._close_progress_dialog()
        QMessageBox.critical(self, "Instance Load Error", message)

    def _cleanup_inst_thread(self, *, wait: bool = True) -> None:
        worker, thread = self._inst_worker, self._inst_thread
        self._inst_worker = None
        self._inst_thread = None
        if not wait and worker is not None:
            worker.cancel()
        if thread is not None:
            if not wait and thread.parent() is self and (app := QCoreApplication.instance()) is not None:
                thread.setParent(app)
            thread.quit()
            if wait:
                thread.wait()

    def _on_settings(self) -> None:
        from bde_xbrl_editor.ui.widgets.loader_settings_dialog import LoaderSettingsDialog

        dialog = LoaderSettingsDialog(self._settings, self)
        if dialog.exec():
            self._settings = dialog.get_settings()
            self._loader = TaxonomyLoader(cache=self._cache, settings=self._settings)
            self._reload_catalog(show_errors=False)
            self.settings_changed.emit()

    def _show_progress_dialog(self, title: str, message: str) -> TaxonomyProgressDialog:
        if self._progress_dialog is None:
            self._progress_dialog = TaxonomyProgressDialog(self)
        self._progress_dialog.setWindowTitle(title)
        self._progress_dialog.reset()
        self._progress_dialog.setLabelText(message)
        self._progress_dialog.show()
        return self._progress_dialog

    def _close_progress_dialog(self) -> None:
        if self._progress_dialog is not None:
            self._progress_dialog.close()

    def shutdown_background_tasks(self) -> None:
        """Stop worker threads before this widget is destroyed or replaced."""
        self._cancel_catalog_check()
        self._cleanup_inst_thread(wait=False)
        self._cleanup_thread(wait=False)
        self._close_progress_dialog()

    @staticmethod
    def _input_style() -> str:
        return (
            f"QLineEdit, QComboBox {{ border: 1px solid {theme.BORDER}; border-radius: 6px;"
            f" padding: 6px 10px; background: {theme.INPUT_BG}; color: {theme.TEXT_MAIN}; }}"
            f"QLineEdit:focus {{ border-color: {_CATALOG_ACCENT}; }}"
        )

    @staticmethod
    def _primary_btn_style() -> str:
        return (
            f"QPushButton {{ background: {_CATALOG_ACCENT}; color: white; border: none;"
            f" border-radius: 6px; font-weight: 700; padding: 8px 14px; }}"
            f"QPushButton:hover {{ background: {_CATALOG_ACCENT_HOVER}; }}"
        )

    @staticmethod
    def _secondary_btn_style() -> str:
        return (
            f"QPushButton {{ background: {theme.SURFACE_BG}; color: {theme.TEXT_MAIN};"
            f" border: 1px solid {theme.BORDER}; border-radius: 6px; padding: 6px 12px; }}"
            f"QPushButton:hover {{ background: {theme.HOVER_BG}; border-color: {_CATALOG_ACCENT}; }}"
        )

    @staticmethod
    def _link_btn_style() -> str:
        return (
            f"QPushButton {{ color: {_CATALOG_ACCENT}; border: none; background: transparent;"
            f" font-size: 11px; font-weight: 650; padding: 2px 6px; }}"
            f"QPushButton:hover {{ color: {_CATALOG_ACCENT_HOVER}; background: {theme.HOVER_BG};"
            f" border-radius: 4px; }}"
            f"QPushButton:disabled {{ color: {theme.DISABLED_FG}; background: transparent; }}"
        )

    @staticmethod
    def _catalog_check_panel_style(state: str) -> str:
        if state == "updates":
            border = _UPDATE_BORDER
            background = _UPDATE_BG
        elif state == "error":
            border = "#FCA5A5"
            background = "#FEF2F2"
        elif state == "checking":
            border = theme.BORDER
            background = theme.SURFACE_ALT_BG
        else:
            border = "transparent"
            background = "transparent"
        return (
            f"QFrame#CatalogCheckPanel {{ background: {background}; border: 1px solid {border};"
            " border-radius: 8px; }}"
            "QFrame#CatalogCheckPanel QLabel { border: none; background: transparent; }"
            "QFrame#CatalogCheckPanel QPushButton { min-height: 24px; }"
        )

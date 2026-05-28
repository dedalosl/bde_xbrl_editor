"""Dialog listing taxonomy catalog files updated since last session."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from bde_xbrl_editor.taxonomy_catalog.models import CatalogChangeReport
from bde_xbrl_editor.ui import theme


class CatalogUpdatesDialog(QDialog):
    """Show catalog scrape or file-level updates detected on startup."""

    def __init__(self, report: CatalogChangeReport, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Actualizaciones en el catálogo BDE")
        self.setMinimumSize(640, 420)
        self._report = report
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet(
            f"""
            QDialog {{
                background: {theme.WINDOW_BG};
                color: {theme.TEXT_MAIN};
            }}
            QListWidget {{
                background: {theme.SURFACE_BG};
                border: 1px solid {theme.BORDER};
                border-radius: 8px;
                padding: 4px;
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        title = QLabel("Hay cambios en el catálogo de taxonomías")
        title.setStyleSheet(
            f"font-size: 17px; font-weight: 750; color: {theme.TEXT_MAIN}; background: transparent;"
        )
        layout.addWidget(title)

        parts: list[str] = []
        if self._report.scrape_is_newer and self._report.previous_last_run:
            parts.append(
                "Se detectó una nueva ejecución del scraper desde la última vez que abriste el editor."
            )
        if self._report.updated_files:
            parts.append(
                f"{len(self._report.updated_files)} archivo(s) con cambios en metadatos o marcados como actualizados."
            )
        summary = QLabel(" ".join(parts) if parts else "Revisa los archivos listados a continuación.")
        summary.setWordWrap(True)
        summary.setStyleSheet(f"color: {theme.TEXT_MUTED}; background: transparent;")
        layout.addWidget(summary)

        list_widget = QListWidget()
        for ref in self._report.updated_files:
            kind_labels = {
                "entry_point": "Punto de entrada",
                "reporting_file": "Documento reporting",
                "general_document": "Documento general",
                "related_link": "Enlace",
            }
            kind = kind_labels.get(ref.resource_kind, ref.resource_kind)
            item = QListWidgetItem(f"{ref.taxonomy_name}\n{kind}: {ref.label}")
            item.setToolTip(ref.url)
            list_widget.addItem(item)
        list_widget.setAlternatingRowColors(True)
        layout.addWidget(list_widget, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons, alignment=Qt.AlignmentFlag.AlignRight)

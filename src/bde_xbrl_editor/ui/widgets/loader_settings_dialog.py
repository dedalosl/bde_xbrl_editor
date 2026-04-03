"""LoaderSettingsDialog — allows users to view and edit LoaderSettings.

Persists settings to ~/.bde_xbrl_editor/settings.json and loads them at
startup.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from bde_xbrl_editor.taxonomy import LoaderSettings

_SETTINGS_FILE = Path.home() / ".bde_xbrl_editor" / "settings.json"


def load_saved_settings() -> LoaderSettings:
    """Load persisted LoaderSettings from disk, or return defaults."""
    if not _SETTINGS_FILE.exists():
        return LoaderSettings()
    try:
        data = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
        catalog_raw = data.get("local_catalog")
        catalog = {k: Path(v) for k, v in catalog_raw.items()} if catalog_raw else None
        return LoaderSettings(
            allow_network=bool(data.get("allow_network", False)),
            language_preference=list(data.get("language_preference", ["es", "en"])),
            local_catalog=catalog,
        )
    except Exception:  # noqa: BLE001
        return LoaderSettings()


def save_settings(settings: LoaderSettings) -> None:
    """Persist LoaderSettings to disk."""
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    catalog = (
        {k: str(v) for k, v in settings.local_catalog.items()}
        if settings.local_catalog
        else None
    )
    data = {
        "allow_network": settings.allow_network,
        "language_preference": list(settings.language_preference),
        "local_catalog": catalog,
    }
    _SETTINGS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


class LoaderSettingsDialog(QDialog):
    """Dialog for viewing and editing LoaderSettings."""

    def __init__(self, current: LoaderSettings, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Loader Settings")
        self.setMinimumWidth(640)
        self._settings = current
        self._setup_ui(current)

    def _setup_ui(self, settings: LoaderSettings) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._allow_network = QCheckBox("Allow network resolution of remote schema references")
        self._allow_network.setChecked(settings.allow_network)
        form.addRow("Network:", self._allow_network)

        self._lang_edit = QLineEdit(", ".join(settings.language_preference))
        form.addRow("Language preference (comma-separated):", self._lang_edit)

        layout.addLayout(form)

        # --- Catalog group ---
        catalog_group = QGroupBox("URL-to-Path Catalog")
        catalog_layout = QVBoxLayout(catalog_group)

        catalog_layout.addWidget(QLabel(
            "Map remote URL prefixes to local directories. "
            "The first matching prefix wins — use Move Up/Down to control evaluation order."
        ))

        # Table showing existing mappings
        self._catalog_table = QTableWidget(0, 2)
        self._catalog_table.setHorizontalHeaderLabels(["URL Prefix", "Local Path"])
        self._catalog_table.horizontalHeader().setStretchLastSection(True)
        self._catalog_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._catalog_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._catalog_table.verticalHeader().setVisible(False)
        catalog_layout.addWidget(self._catalog_table)

        # Populate from existing settings
        if settings.local_catalog:
            for url_prefix, local_path in settings.local_catalog.items():
                self._append_catalog_row(url_prefix, str(local_path))

        # Table action buttons
        table_buttons = QHBoxLayout()
        move_up_btn = QPushButton("Move Up")
        move_up_btn.clicked.connect(self._move_up)
        move_down_btn = QPushButton("Move Down")
        move_down_btn.clicked.connect(self._move_down)
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_selected)
        table_buttons.addWidget(move_up_btn)
        table_buttons.addWidget(move_down_btn)
        table_buttons.addStretch()
        table_buttons.addWidget(delete_btn)
        catalog_layout.addLayout(table_buttons)

        # Add-new-entry row
        add_group_layout = QHBoxLayout()
        self._new_url_edit = QLineEdit()
        self._new_url_edit.setPlaceholderText("URL prefix  e.g. http://www.xbrl.org/2003/")
        self._new_path_edit = QLineEdit()
        self._new_path_edit.setPlaceholderText("Local directory path")
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_path)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_entry)
        add_group_layout.addWidget(self._new_url_edit, 3)
        add_group_layout.addWidget(self._new_path_edit, 3)
        add_group_layout.addWidget(browse_btn)
        add_group_layout.addWidget(add_btn)
        catalog_layout.addLayout(add_group_layout)

        layout.addWidget(catalog_group)

        layout.addWidget(QLabel("<small>Settings are saved to ~/.bde_xbrl_editor/settings.json</small>"))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Catalog helpers
    # ------------------------------------------------------------------

    def _append_catalog_row(self, url_prefix: str, local_path: str) -> None:
        row = self._catalog_table.rowCount()
        self._catalog_table.insertRow(row)
        self._catalog_table.setItem(row, 0, QTableWidgetItem(url_prefix))
        self._catalog_table.setItem(row, 1, QTableWidgetItem(local_path))

    def _browse_path(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Select Local Directory")
        if directory:
            self._new_path_edit.setText(directory)

    def _add_entry(self) -> None:
        url = self._new_url_edit.text().strip()
        path = self._new_path_edit.text().strip()
        if not url or not path:
            return
        self._append_catalog_row(url, path)
        self._new_url_edit.clear()
        self._new_path_edit.clear()

    def _delete_selected(self) -> None:
        rows = self._catalog_table.selectionModel().selectedRows()
        for index in sorted(rows, key=lambda i: i.row(), reverse=True):
            self._catalog_table.removeRow(index.row())

    def _move_up(self) -> None:
        row = self._catalog_table.currentRow()
        if row <= 0:
            return
        self._swap_rows(row, row - 1)
        self._catalog_table.setCurrentCell(row - 1, 0)

    def _move_down(self) -> None:
        row = self._catalog_table.currentRow()
        if row < 0 or row >= self._catalog_table.rowCount() - 1:
            return
        self._swap_rows(row, row + 1)
        self._catalog_table.setCurrentCell(row + 1, 0)

    def _swap_rows(self, a: int, b: int) -> None:
        for col in range(self._catalog_table.columnCount()):
            item_a = self._catalog_table.takeItem(a, col)
            item_b = self._catalog_table.takeItem(b, col)
            self._catalog_table.setItem(a, col, item_b)
            self._catalog_table.setItem(b, col, item_a)

    # ------------------------------------------------------------------
    # Accept / get_settings
    # ------------------------------------------------------------------

    def _on_accept(self) -> None:
        settings = self.get_settings()
        save_settings(settings)
        self.accept()

    def get_settings(self) -> LoaderSettings:
        """Return the LoaderSettings as currently configured in the dialog."""
        lang_pref = [
            lang.strip() for lang in self._lang_edit.text().split(",") if lang.strip()
        ] or ["es", "en"]

        catalog: dict[str, Path] | None = None
        rows = self._catalog_table.rowCount()
        if rows > 0:
            catalog = {}
            for row in range(rows):
                url_item = self._catalog_table.item(row, 0)
                path_item = self._catalog_table.item(row, 1)
                if url_item and path_item:
                    url = url_item.text().strip()
                    path_str = path_item.text().strip()
                    if url and path_str:
                        catalog[url] = Path(path_str)

        return LoaderSettings(
            allow_network=self._allow_network.isChecked(),
            language_preference=lang_pref,
            local_catalog=catalog or None,
        )

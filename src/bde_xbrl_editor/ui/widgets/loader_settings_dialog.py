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
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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

        catalog_row = QHBoxLayout()
        catalog_val = (
            ", ".join(f"{k}={v}" for k, v in settings.local_catalog.items())
            if settings.local_catalog
            else ""
        )
        self._catalog_edit = QLineEdit(catalog_val)
        self._catalog_edit.setPlaceholderText("e.g. http://www.xbrl.org/=/local/xbrl/")
        catalog_row.addWidget(self._catalog_edit)
        form.addRow("Local catalog (URI=path pairs):", self._catalog_edit)

        layout.addLayout(form)
        layout.addWidget(QLabel("<small>Settings are saved to ~/.bde_xbrl_editor/settings.json</small>"))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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
        raw_catalog = self._catalog_edit.text().strip()
        if raw_catalog:
            catalog = {}
            for pair in raw_catalog.split(","):
                pair = pair.strip()
                if "=" in pair:
                    uri, path_str = pair.split("=", 1)
                    catalog[uri.strip()] = Path(path_str.strip())

        return LoaderSettings(
            allow_network=self._allow_network.isChecked(),
            language_preference=lang_pref,
            local_catalog=catalog or None,
        )

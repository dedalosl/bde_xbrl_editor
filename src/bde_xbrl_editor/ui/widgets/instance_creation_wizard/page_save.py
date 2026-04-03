"""Wizard page 4 — Save location picker and final instance assembly."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWizardPage,
)

from bde_xbrl_editor.instance.models import InstanceSaveError
from bde_xbrl_editor.instance.serializer import InstanceSerializer


class SavePage(QWizardPage):
    """Wizard page 4: choose save location and write the XBRL instance."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setTitle("Save Instance")
        self.setSubTitle("Choose where to save the new XBRL instance file.")

        layout = QVBoxLayout(self)

        path_layout = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setPlaceholderText("Select save location…")
        self._browse_btn = QPushButton("Browse…")
        self._browse_btn.clicked.connect(self._browse)
        path_layout.addWidget(self._path_edit)
        path_layout.addWidget(self._browse_btn)
        layout.addLayout(path_layout)

        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setWordWrap(True)
        layout.addWidget(self._error_label)
        layout.addStretch()

        self.registerField("save_path*", self._path_edit)

    def _browse(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save XBRL Instance",
            "",
            "XBRL files (*.xbrl *.xml);;All files (*)",
        )
        if path:
            self._path_edit.setText(path)
            self._error_label.setText("")

    def validatePage(self) -> bool:
        self._error_label.setText("")
        path = self._path_edit.text().strip()
        if not path:
            self._error_label.setText("Please select a save location.")
            return False

        dest = Path(path)
        if dest.exists():
            reply = QMessageBox.question(
                self,
                "File Exists",
                f"'{dest.name}' already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return False

        # Build and save the instance
        wizard = self.wizard()
        instance = wizard.property("assembled_instance")
        if instance is None:
            self._error_label.setText("Internal error: instance not assembled.")
            return False

        try:
            InstanceSerializer().save(instance, dest)
        except InstanceSaveError as exc:
            self._error_label.setText(str(exc))
            return False

        return True

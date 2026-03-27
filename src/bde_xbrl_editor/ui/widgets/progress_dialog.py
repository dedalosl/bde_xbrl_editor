"""QProgressDialog wrapper that adapts the plain-Python progress callback protocol."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QProgressDialog, QWidget


class TaxonomyProgressDialog(QProgressDialog):
    """Progress dialog for taxonomy loading operations.

    Adapts the ``progress_callback(message, current_step, total_steps)``
    protocol used by TaxonomyLoader to Qt's QProgressDialog interface.
    All updates are posted on the main thread (caller's responsibility).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Loading Taxonomy…")
        self.setLabelText("Initialising…")
        self.setMinimum(0)
        self.setMaximum(100)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setCancelButton(None)  # Loading is non-cancellable in v1
        self.setMinimumDuration(500)  # Only show if loading takes > 500 ms

    def as_callback(self):
        """Return a progress_callback function compatible with TaxonomyLoader."""

        def callback(message: str, current_step: int, total_steps: int) -> None:
            self.setLabelText(message)
            if total_steps > 0:
                self.setValue(int(current_step / total_steps * 100))

        return callback

"""Rich progress dialog for long-running taxonomy and instance loading flows."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from bde_xbrl_editor.ui import theme


class TaxonomyProgressDialog(QDialog):
    """Styled modal dialog with live progress, file context, and activity feed."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._last_activity = ""
        self._message = "Initialising…"
        self._value = 0

        self.setWindowTitle("Loading")
        self.setModal(True)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(520)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        self.setStyleSheet(
            f"""
            QDialog {{
                background: {theme.WINDOW_BG};
            }}
            QLabel {{
                border: none;
                background: transparent;
            }}
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(12)

        shell = QFrame(self)
        shell.setObjectName("ProgressShell")
        shell.setStyleSheet(
            f"""
            QFrame#ProgressShell {{
                background: {theme.SURFACE_BG};
                border: 1px solid {theme.ACCENT_SOFT};
                border-radius: 18px;
            }}
            """
        )
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(18, 18, 18, 18)
        shell_layout.setSpacing(12)
        outer.addWidget(shell)

        hero = QFrame(shell)
        hero.setObjectName("ProgressHero")
        hero.setStyleSheet(
            f"""
            QFrame#ProgressHero {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 {theme.NAV_BG_DEEP},
                    stop:1 {theme.NAV_BG_DARK}
                );
                border: none;
                border-radius: 14px;
            }}
            """
        )
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(16, 16, 16, 16)
        hero_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)

        title_wrap = QVBoxLayout()
        title_wrap.setContentsMargins(0, 0, 0, 0)
        title_wrap.setSpacing(3)

        self._eyebrow = QLabel("Load session", hero)
        self._eyebrow.setStyleSheet(
            f"color: {theme.ACCENT_SOFT}; font-size: 11px; font-weight: 700; background: transparent;"
        )
        title_wrap.addWidget(self._eyebrow)

        self._title_label = QLabel("Loading", hero)
        self._title_label.setStyleSheet(
            f"color: {theme.TEXT_INVERSE}; font-size: 22px; font-weight: 700; background: transparent;"
        )
        title_wrap.addWidget(self._title_label)

        self._context_label = QLabel("Waiting for file selection", hero)
        self._context_label.setStyleSheet(
            f"color: {theme.ACCENT_SOFT}; font-size: 11px; background: transparent;"
        )
        self._context_label.setWordWrap(True)
        title_wrap.addWidget(self._context_label)

        top_row.addLayout(title_wrap, stretch=1)

        self._status_chip = QLabel("Starting", hero)
        self._status_chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_chip.setFixedHeight(28)
        self._status_chip.setMinimumWidth(96)
        self._status_chip.setStyleSheet(
            f"""
            QLabel {{
                color: {theme.TEXT_INVERSE};
                background: rgba(255, 253, 248, 0.14);
                border: none;
                border-radius: 14px;
                font-size: 10px;
                font-weight: 700;
                padding: 0 10px;
            }}
            """
        )
        top_row.addWidget(self._status_chip, alignment=Qt.AlignmentFlag.AlignTop)
        hero_layout.addLayout(top_row)

        self._message_label = QLabel(self._message, hero)
        self._message_label.setWordWrap(True)
        self._message_label.setStyleSheet(
            f"color: {theme.TEXT_INVERSE}; font-size: 13px; background: transparent;"
        )
        hero_layout.addWidget(self._message_label)

        progress_row = QHBoxLayout()
        progress_row.setContentsMargins(0, 0, 0, 0)
        progress_row.setSpacing(10)

        self._progress_bar = QProgressBar(hero)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(10)
        self._progress_bar.setStyleSheet(
            f"""
            QProgressBar {{
                background: rgba(255, 253, 248, 0.16);
                border: none;
                border-radius: 5px;
            }}
            QProgressBar::chunk {{
                background: {theme.HEADER_BG};
                border-radius: 5px;
            }}
            """
        )
        progress_row.addWidget(self._progress_bar, stretch=1)

        self._percent_label = QLabel("0%", hero)
        self._percent_label.setStyleSheet(
            f"color: {theme.TEXT_INVERSE}; font-size: 11px; font-weight: 700; background: transparent;"
        )
        progress_row.addWidget(self._percent_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        hero_layout.addLayout(progress_row)

        shell_layout.addWidget(hero)

        activity_header = QHBoxLayout()
        activity_header.setContentsMargins(2, 0, 2, 0)
        activity_header.setSpacing(8)

        activity_title = QLabel("Recent activity", shell)
        activity_title.setStyleSheet(
            f"color: {theme.TEXT_MAIN}; font-size: 12px; font-weight: 700; background: transparent;"
        )
        activity_header.addWidget(activity_title)
        activity_header.addStretch(1)

        self._activity_count = QLabel("0 updates", shell)
        self._activity_count.setStyleSheet(
            f"color: {theme.TEXT_SUBTLE}; font-size: 10px; font-weight: 600; background: transparent;"
        )
        activity_header.addWidget(self._activity_count)
        shell_layout.addLayout(activity_header)

        self._activity_list = QListWidget(shell)
        self._activity_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._activity_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self._activity_list.setSpacing(1)
        self._activity_list.setMinimumHeight(168)
        self._activity_list.setStyleSheet(
            f"""
            QListWidget {{
                background: transparent;
                border: none;
                color: {theme.TEXT_MAIN};
                outline: none;
                padding: 0;
            }}
            QListWidget::item {{
                border: none;
                background: transparent;
                padding: 6px 2px;
                margin: 0;
            }}
            """
        )
        shell_layout.addWidget(self._activity_list, stretch=1)

    def setWindowTitle(self, title: str) -> None:  # type: ignore[override]
        super().setWindowTitle(title)
        if hasattr(self, "_title_label"):
            self._title_label.setText(title)

    def set_context(self, kind: str, path: str) -> None:
        """Attach file context so the user knows what is being processed."""
        file_path = Path(path)
        primary = file_path.name or path
        secondary = str(file_path.parent) if file_path.parent != Path(".") else ""
        self._eyebrow.setText(kind)
        if secondary:
            self._context_label.setText(f"{primary}\n{secondary}")
        else:
            self._context_label.setText(primary)

    def reset(self) -> None:
        """Clear progress state before a new session starts."""
        self._last_activity = ""
        self._activity_list.clear()
        self._activity_count.setText("0 updates")
        self._eyebrow.setText("Load session")
        self._context_label.setText("Waiting for file selection")
        self.setLabelText("Initialising…")
        self.setValue(0)

    def setLabelText(self, text: str) -> None:
        self._message = text
        self._message_label.setText(text)

    def setValue(self, value: int) -> None:
        clamped = max(0, min(value, 100))
        self._value = clamped
        self._progress_bar.setValue(clamped)
        self._percent_label.setText(f"{clamped}%")
        if clamped >= 100:
            self._status_chip.setText("Ready")
        elif clamped >= 85:
            self._status_chip.setText("Finalising")
        elif clamped > 0:
            self._status_chip.setText("In progress")
        else:
            self._status_chip.setText("Starting")

    @Slot(str, int, int)
    def update_progress(self, message: str, current_step: int, total_steps: int) -> None:
        self.setLabelText(message)
        if total_steps > 0:
            self.setValue(int(current_step / total_steps * 100))
        self._append_activity(message)

    def _append_activity(self, message: str) -> None:
        if not message or message == self._last_activity:
            return
        self._last_activity = message

        bullet = QListWidgetItem(message)
        bullet.setForeground(QColor(theme.TEXT_MAIN))
        self._activity_list.insertItem(0, bullet)
        while self._activity_list.count() > 8:
            self._activity_list.takeItem(self._activity_list.count() - 1)
        count = self._activity_list.count()
        suffix = "update" if count == 1 else "updates"
        self._activity_count.setText(f"{count} {suffix}")

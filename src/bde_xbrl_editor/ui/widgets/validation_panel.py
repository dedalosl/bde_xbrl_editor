"""ValidationWorker and ValidationPanel — UI components for Feature 005."""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from bde_xbrl_editor.performance import format_duration, format_stage_timings
from bde_xbrl_editor.ui import theme
from bde_xbrl_editor.ui.widgets.validation_results_model import (
    ValidationFilterProxy,
    ValidationResultsModel,
)
from bde_xbrl_editor.validation.models import (
    ValidationFinding,
    ValidationReport,
    ValidationSeverity,
    ValidationStatus,
)

# ---------------------------------------------------------------------------
# ValidationWorker
# ---------------------------------------------------------------------------

class ValidationWorker(QObject):
    """Runs InstanceValidator.validate_sync() on a background thread.

    Signals
    -------
    progress_changed(current, total, message)
    validation_completed(report)
    validation_failed(error_message)
    """

    progress_changed = Signal(int, int, str)
    findings_ready = Signal(object)  # tuple[ValidationFinding, ...]
    validation_completed = Signal(object)  # ValidationReport
    validation_failed = Signal(str)

    def __init__(self, taxonomy, instance, parent=None) -> None:
        super().__init__(parent)
        self._taxonomy = taxonomy
        self._instance = instance
        self._cancel_event = threading.Event()

    @Slot()
    def run(self) -> None:
        """Execute validation; emit result or error signal."""
        from bde_xbrl_editor.validation.orchestrator import InstanceValidator

        def _progress(current: int, total: int, message: str) -> None:
            self.progress_changed.emit(current, total, message)

        def _findings_ready(findings: tuple[ValidationFinding, ...]) -> None:
            self.findings_ready.emit(findings)

        try:
            validator = InstanceValidator(
                taxonomy=self._taxonomy,
                progress_callback=_progress,
                finding_callback=_findings_ready,
                cancel_event=self._cancel_event,
            )
            report = validator.validate_sync(self._instance)
            self.validation_completed.emit(report)
        except Exception as exc:  # noqa: BLE001
            self.validation_failed.emit(str(exc))

    @Slot()
    def cancel(self) -> None:
        self._cancel_event.set()


# ---------------------------------------------------------------------------
# ValidationPanel
# ---------------------------------------------------------------------------

class ValidationPanel(QWidget):
    """Dockable panel showing validation results with filter toolbar.

    Signals
    -------
    navigate_to_cell(context_ref: str, finding: ValidationFinding)
    revalidate_requested()
    """

    navigate_to_cell = Signal(str, object)
    revalidate_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._model = ValidationResultsModel(self)
        self._proxy = ValidationFilterProxy(self)
        self._proxy.setSourceModel(self._model)

        self._current_report: ValidationReport | None = None
        self._current_findings: list[ValidationFinding] = []
        self._worker: ValidationWorker | None = None
        self._thread: QThread | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        self.setStyleSheet(
            f"ValidationPanel {{ background: {theme.SURFACE_ALT_BG}; }}"
            f" QLabel {{ color: {theme.TEXT_MAIN}; }}"
            f" QToolButton {{ color: {theme.TEXT_MAIN}; background: {theme.SURFACE_BG};"
            f" border: 1px solid {theme.ACCENT_SOFT}; border-radius: 6px; padding: 4px 8px; }}"
            f" QToolButton:checked {{ background: {theme.SURFACE_BG}; border-color: {theme.BORDER_STRONG}; }}"
            f" QProgressBar {{ background: {theme.SURFACE_BG}; border: 1px solid {theme.ACCENT_SOFT};"
            f" border-radius: 4px; text-align: center; }}"
            f" QProgressBar::chunk {{ background: {theme.ACCENT}; }}"
            f" QTextEdit {{ background: {theme.INPUT_BG}; border: 1px solid {theme.ACCENT_SOFT}; border-radius: 6px; }}"
        )

        # Toolbar row
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        toolbar_card = QWidget()
        toolbar_card.setStyleSheet(
            f"background: {theme.SURFACE_BG}; border: 1px solid {theme.ACCENT_SOFT}; border-radius: 8px;"
        )
        toolbar_card_layout = QHBoxLayout(toolbar_card)
        toolbar_card_layout.setContentsMargins(10, 8, 10, 8)
        toolbar_card_layout.setSpacing(6)

        self._validate_btn = QPushButton("Validate")
        self._validate_btn.setToolTip("Run full validation on the current instance")
        self._validate_btn.clicked.connect(self.revalidate_requested)
        toolbar_card_layout.addWidget(self._validate_btn)

        toolbar_card_layout.addWidget(QLabel("Severity:"))
        self._sev_combo = QComboBox()
        self._sev_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._sev_combo.setMinimumContentsLength(7)
        self._sev_combo.setMinimumWidth(110)
        self._sev_combo.addItem("All", None)
        self._sev_combo.addItem("Pass", ValidationStatus.PASS)
        self._sev_combo.addItem("Error", ValidationSeverity.ERROR)
        self._sev_combo.addItem("Warning", ValidationSeverity.WARNING)
        self._sev_combo.currentIndexChanged.connect(self._on_severity_filter_changed)
        toolbar_card_layout.addWidget(self._sev_combo)

        toolbar_card_layout.addWidget(QLabel("Table:"))
        self._table_combo = QComboBox()
        self._table_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self._table_combo.setMinimumContentsLength(8)
        self._table_combo.setMinimumWidth(110)
        self._table_combo.addItem("All", None)
        self._table_combo.currentIndexChanged.connect(self._on_table_filter_changed)
        toolbar_card_layout.addWidget(self._table_combo)

        self._clear_filters_btn = QPushButton("Clear Filters")
        self._clear_filters_btn.clicked.connect(self._on_clear_filters)
        toolbar_card_layout.addWidget(self._clear_filters_btn)

        self._summary_label = QLabel("No results")
        toolbar_card_layout.addWidget(self._summary_label)

        toolbar_card_layout.addStretch()

        self._export_btn = QPushButton("Export…")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self.export_report)
        toolbar_card_layout.addWidget(self._export_btn)

        toolbar.addWidget(toolbar_card)
        layout.addLayout(toolbar)

        # Progress bar (hidden when idle)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setVisible(False)
        layout.addWidget(self._progress_bar)

        # Results tree — expands to fill all available vertical space
        self._tree = QTreeView()
        self._tree.setModel(self._proxy)
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self._tree.header().setStretchLastSection(True)
        self._tree.selectionModel().currentRowChanged.connect(self._on_row_selected)
        layout.addWidget(self._tree, stretch=1)

        # Collapsible detail panel — toggle button acts as section header
        self._detail_toggle_btn = QToolButton()
        self._detail_toggle_btn.setCheckable(True)
        self._detail_toggle_btn.setChecked(False)
        self._detail_toggle_btn.setText(" Details")
        self._detail_toggle_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self._detail_toggle_btn.setArrowType(Qt.ArrowType.RightArrow)
        self._detail_toggle_btn.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._detail_toggle_btn.toggled.connect(self._on_detail_toggled)
        layout.addWidget(self._detail_toggle_btn)

        self._detail_container = QWidget()
        detail_inner = QVBoxLayout(self._detail_container)
        detail_inner.setContentsMargins(0, 2, 0, 0)
        detail_inner.setSpacing(4)

        self._detail_text = QTextEdit()
        self._detail_text.setReadOnly(True)
        self._detail_text.setFixedHeight(130)
        detail_inner.addWidget(self._detail_text)

        self._goto_btn = QPushButton("Go to Cell")
        self._goto_btn.setEnabled(False)
        self._goto_btn.clicked.connect(self._on_goto_cell)
        detail_inner.addWidget(self._goto_btn)

        self._detail_container.setVisible(False)
        layout.addWidget(self._detail_container)

    @Slot(bool)
    def _on_detail_toggled(self, checked: bool) -> None:
        self._detail_container.setVisible(checked)
        self._detail_toggle_btn.setArrowType(
            Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_report(self, report: ValidationReport) -> None:
        """Populate the panel with the findings from a completed validation run."""
        self._current_report = report
        self._current_findings = list(report.findings)

        if self._model.rowCount() != len(report.findings):
            self._model.populate(report.findings)

        self._update_summary()
        self._update_table_filter_options(report.findings)
        self._export_btn.setEnabled(True)
        self._progress_bar.setVisible(False)
        self._detail_text.clear()
        self._goto_btn.setEnabled(False)

    def append_findings(self, findings: tuple[ValidationFinding, ...]) -> None:
        """Append streamed findings from the active validation run."""
        if not findings:
            return

        self._current_findings.extend(findings)
        self._model.append_findings(findings)
        self._update_summary()
        self._update_table_filter_options(tuple(self._current_findings))

    def show_progress(self, current: int, total: int, message: str) -> None:
        """Update the progress bar without clearing the current results."""
        self._progress_bar.setVisible(True)
        if total > 0:
            self._progress_bar.setValue(int(current / total * 100))
        self._summary_label.setText(message)

    def clear(self) -> None:
        self._current_report = None
        self._current_findings.clear()
        self._model.clear_findings()
        self._summary_label.setText("No results")
        self._detail_text.clear()
        self._goto_btn.setEnabled(False)
        self._export_btn.setEnabled(False)
        self._progress_bar.setVisible(False)
        self._sev_combo.blockSignals(True)
        self._sev_combo.setCurrentIndex(0)
        self._sev_combo.blockSignals(False)
        self._table_combo.blockSignals(True)
        self._table_combo.clear()
        self._table_combo.addItem("All", None)
        self._table_combo.blockSignals(False)
        self._proxy.clear_filters()

    def set_available_tables(self, tables: list[tuple[str, str]]) -> None:
        """Populate the table filter combobox. tables = list of (table_id, label)."""
        self._table_combo.blockSignals(True)
        self._table_combo.clear()
        self._table_combo.addItem("All", None)
        for table_id, label in tables:
            self._table_combo.addItem(label or table_id, table_id)
        self._table_combo.blockSignals(False)
        self._proxy.set_table_filter(None)

    def export_report(self) -> None:
        """Open a save-file dialog and export the current report."""
        if self._current_report is None:
            return

        from bde_xbrl_editor.validation.errors import ExportPermissionError  # noqa: PLC0415
        from bde_xbrl_editor.validation.exporter import ValidationReportExporter  # noqa: PLC0415

        path_str, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Validation Report",
            "validation_report",
            "Text Files (*.txt);;JSON Files (*.json)",
        )
        if not path_str:
            return

        export_path = Path(path_str)
        exporter = ValidationReportExporter()
        try:
            if "json" in selected_filter.lower() or export_path.suffix.lower() == ".json":
                exporter.export_json(self._current_report, export_path)
            else:
                exporter.export_text(self._current_report, export_path)
        except ExportPermissionError as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    # ------------------------------------------------------------------
    # Slot helpers
    # ------------------------------------------------------------------

    @Slot()
    def _on_severity_filter_changed(self) -> None:
        sev = self._sev_combo.currentData()
        self._proxy.set_severity_filter(sev)
        self._update_summary()

    @Slot()
    def _on_table_filter_changed(self) -> None:
        table_id = self._table_combo.currentData()
        self._proxy.set_table_filter(table_id)
        self._update_summary()

    @Slot()
    def _on_clear_filters(self) -> None:
        self._sev_combo.setCurrentIndex(0)
        self._table_combo.setCurrentIndex(0)
        self._proxy.clear_filters()
        self._update_summary()

    def _on_row_selected(self, current, _previous) -> None:
        if not current.isValid():
            self._detail_text.clear()
            self._goto_btn.setEnabled(False)
            return

        source_index = self._proxy.mapToSource(current)
        sev_index = self._model.index(source_index.row(), 0)
        finding: ValidationFinding | None = sev_index.data(
            __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.ItemDataRole.UserRole
        )
        if finding is None:
            self._detail_text.clear()
            self._goto_btn.setEnabled(False)
            return

        lines = [
            f"Rule ID   : {finding.rule_id}",
            f"Status    : {finding.status.value.upper()}",
            f"Source    : {finding.source}",
            f"Message   : {finding.message}",
        ]
        if finding.severity is not None:
            lines.append(f"Severity  : {finding.severity.value.upper()}")
        if finding.table_label or finding.table_id:
            lines.append(f"Table     : {finding.table_label or finding.table_id}")
        if finding.concept_qname:
            lines.append(f"Concept   : {finding.concept_qname}")
        if finding.context_ref:
            lines.append(f"Context   : {finding.context_ref}")
        if finding.rule_label:
            lines.extend([
                "",
                "Definition:",
                finding.rule_label,
            ])
            if finding.rule_label_role:
                lines.append(f"Definition Role: {finding.rule_label_role}")
        if finding.rule_message:
            lines.extend([
                "",
                "Official Message:",
                finding.rule_message,
            ])
            if finding.rule_message_role:
                lines.append(f"Message Role: {finding.rule_message_role}")
        if finding.constraint_type:
            lines.append(f"Constraint: {finding.constraint_type}")
        if finding.formula_assertion_type:
            lines.append(f"Formula Type: {finding.formula_assertion_type}")
        if finding.evaluated_rule_message:
            lines.extend([
                "",
                "Evaluated Message:",
                finding.evaluated_rule_message,
            ])
        if finding.formula_expression:
            lines.extend([
                "",
                "Formula / Test:",
                finding.formula_expression,
            ])
        if finding.formula_operands_text:
            lines.extend([
                "",
                "Operands:",
                finding.formula_operands_text,
            ])
        if finding.formula_precondition and finding.formula_precondition != "—":
            lines.extend([
                "",
                "Precondition:",
                finding.formula_precondition,
            ])

        self._detail_text.setPlainText("\n".join(lines))
        self._goto_btn.setEnabled(bool(finding.context_ref))
        self._goto_btn.setProperty("_finding", finding)

        # Auto-expand detail panel on first selection
        if not self._detail_toggle_btn.isChecked():
            self._detail_toggle_btn.setChecked(True)

    @Slot()
    def _on_goto_cell(self) -> None:
        finding: ValidationFinding | None = self._goto_btn.property("_finding")
        if finding and finding.context_ref:
            self.navigate_to_cell.emit(finding.context_ref, finding)

    def _update_summary(self) -> None:
        findings = self._current_report.findings if self._current_report is not None else tuple(self._current_findings)
        if not findings:
            self._summary_label.setText("No results")
            return
        visible = self._proxy.rowCount()
        passed = sum(1 for finding in findings if finding.status == ValidationStatus.PASS)
        errors = sum(1 for finding in findings if finding.severity == ValidationSeverity.ERROR)
        warnings = sum(1 for finding in findings if finding.severity == ValidationSeverity.WARNING)
        summary = f"{visible} shown | {passed} pass, {errors} error(s), {warnings} warning(s)"
        if self._current_report is not None and self._current_report.stage_timings:
            summary += (
                f" | {format_duration(self._current_report.total_elapsed_seconds)} total"
                f" | {format_stage_timings(self._current_report.stage_timings)}"
            )
        self._summary_label.setText(summary)

    def _update_table_filter_options(
        self,
        findings: tuple[ValidationFinding, ...],
    ) -> None:
        current_table_filter = self._table_combo.currentData()
        table_ids: list[str] = sorted({
            f.table_id for f in findings if f.table_id
        })
        self._table_combo.blockSignals(True)
        self._table_combo.clear()
        self._table_combo.addItem("All", None)
        for tid in table_ids:
            label = next(
                (f.table_label for f in findings if f.table_id == tid and f.table_label),
                tid,
            )
            self._table_combo.addItem(label, tid)
        if current_table_filter is not None:
            index = self._table_combo.findData(current_table_filter)
            self._table_combo.setCurrentIndex(index if index >= 0 else 0)
        self._table_combo.blockSignals(False)
        self._proxy.set_table_filter(self._table_combo.currentData())

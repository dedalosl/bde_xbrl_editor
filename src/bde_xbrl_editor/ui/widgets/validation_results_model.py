"""ValidationResultsModel and ValidationFilterProxy — Qt models for validation findings."""

from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor, QStandardItem, QStandardItemModel

from bde_xbrl_editor.validation.models import (
    ValidationFinding,
    ValidationSeverity,
    ValidationStatus,
)

# Column indices
COL_SEVERITY = 0
COL_STATUS = COL_SEVERITY
COL_RULE_ID = 1
COL_MESSAGE = 2
COL_TABLE = 3
COL_CONCEPT = 4

_HEADERS = ["Status", "Rule ID", "Message", "Table", "Concept"]

_COLOR_ERROR = QColor(200, 50, 50)
_COLOR_WARNING = QColor(200, 150, 0)
_COLOR_PASS = QColor(34, 139, 34)

SeverityFilterValue = ValidationSeverity | ValidationStatus | None


class ValidationResultsModel(QStandardItemModel):
    """Flat list model backing the validation results tree view.

    5 columns: Severity | Rule ID | Message | Table | Concept.
    Column 0 carries the full ValidationFinding in Qt.UserRole.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(0, len(_HEADERS), parent)
        self.setHorizontalHeaderLabels(_HEADERS)

    def populate(self, findings: tuple[ValidationFinding, ...]) -> None:
        """Replace all rows with findings from a ValidationReport."""
        self.removeRows(0, self.rowCount())
        for finding in findings:
            self._append_finding(finding)

    def _append_finding(self, finding: ValidationFinding) -> None:
        if finding.status == ValidationStatus.PASS:
            sev_text = "PASS"
            color = _COLOR_PASS
        else:
            sev_text = finding.severity.value.upper() if finding.severity else "FAIL"
            color = _COLOR_ERROR if finding.severity == ValidationSeverity.ERROR else _COLOR_WARNING

        sev_item = QStandardItem(sev_text)
        sev_item.setForeground(color)
        sev_item.setData(finding, Qt.ItemDataRole.UserRole)
        sev_item.setEditable(False)

        rule_item = QStandardItem(finding.rule_id)
        rule_item.setEditable(False)

        msg_item = QStandardItem(finding.message)
        msg_item.setEditable(False)

        table_text = finding.table_label or finding.table_id or ""
        table_item = QStandardItem(table_text)
        table_item.setEditable(False)

        concept_text = str(finding.concept_qname) if finding.concept_qname else ""
        concept_item = QStandardItem(concept_text)
        concept_item.setEditable(False)

        self.appendRow([sev_item, rule_item, msg_item, table_item, concept_item])


class ValidationFilterProxy(QSortFilterProxyModel):
    """AND-filter proxy: severity filter × table_id filter.

    Both filters default to None (show all). Setting either to a non-None
    value hides rows that don't match.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._severity_filter: SeverityFilterValue = None
        self._table_filter: str | None = None

    def set_severity_filter(self, severity: SeverityFilterValue) -> None:
        self._severity_filter = severity
        self.invalidateFilter()

    def set_table_filter(self, table_id: str | None) -> None:
        self._table_filter = table_id
        self.invalidateFilter()

    def clear_filters(self) -> None:
        self._severity_filter = None
        self._table_filter = None
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:  # type: ignore[override]
        source_model = self.sourceModel()
        if source_model is None:
            return True

        sev_index = source_model.index(source_row, COL_SEVERITY, source_parent)
        finding: ValidationFinding | None = sev_index.data(Qt.ItemDataRole.UserRole)
        if finding is None:
            return True

        if finding.status == ValidationStatus.PASS:
            if self._severity_filter not in (None, ValidationStatus.PASS):
                return False
            return self._table_filter is None or finding.table_id == self._table_filter

        if self._severity_filter == ValidationStatus.PASS:
            return False
        if self._severity_filter is not None and finding.severity != self._severity_filter:
            return False
        return not (self._table_filter is not None and finding.table_id != self._table_filter)

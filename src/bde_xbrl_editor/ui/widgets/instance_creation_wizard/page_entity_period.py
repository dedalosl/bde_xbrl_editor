"""Wizard page 1 — Entity identifier and reporting period."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWizardPage,
)

from bde_xbrl_editor.instance.models import (
    InvalidEntityIdentifierError,
    InvalidReportingPeriodError,
    ReportingEntity,
    ReportingPeriod,
)


class EntityPeriodPage(QWizardPage):
    """Wizard page 1: collect entity identifier and reporting period."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setTitle("Entity and Reporting Period")
        self.setSubTitle("Enter the entity identifier and the reporting period.")

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._identifier_edit = QLineEdit()
        self._identifier_edit.setPlaceholderText("e.g. ES0123456789")
        form.addRow("Entity Identifier *", self._identifier_edit)

        self._scheme_edit = QLineEdit()
        self._scheme_edit.setText("http://www.bde.es/")
        form.addRow("Entity Scheme *", self._scheme_edit)

        self._period_type_combo = QComboBox()
        self._period_type_combo.addItems(["instant", "duration"])
        self._period_type_combo.currentTextChanged.connect(self._on_period_type_changed)
        form.addRow("Period Type *", self._period_type_combo)

        self._instant_date_edit = QDateEdit()
        self._instant_date_edit.setCalendarPopup(True)
        self._instant_date_edit.setDate(QDate.currentDate())
        self._instant_date_edit.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Date *", self._instant_date_edit)

        self._start_date_edit = QDateEdit()
        self._start_date_edit.setCalendarPopup(True)
        self._start_date_edit.setDisplayFormat("yyyy-MM-dd")
        self._start_date_edit.hide()
        form.addRow("Start Date *", self._start_date_edit)

        self._end_date_edit = QDateEdit()
        self._end_date_edit.setCalendarPopup(True)
        self._end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self._end_date_edit.hide()
        form.addRow("End Date *", self._end_date_edit)

        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setWordWrap(True)

        layout.addLayout(form)
        layout.addWidget(self._error_label)

        # Register wizard fields for cross-page access
        self.registerField("entity_identifier*", self._identifier_edit)
        self.registerField("entity_scheme*", self._scheme_edit)

    def _on_period_type_changed(self, period_type: str) -> None:
        is_instant = period_type == "instant"
        self._instant_date_edit.setVisible(is_instant)
        self._start_date_edit.setVisible(not is_instant)
        self._end_date_edit.setVisible(not is_instant)

    def validatePage(self) -> bool:
        self._error_label.setText("")
        try:
            ReportingEntity(
                identifier=self._identifier_edit.text().strip(),
                scheme=self._scheme_edit.text().strip(),
            )
            self._build_period()
        except (InvalidEntityIdentifierError, InvalidReportingPeriodError) as exc:
            self._error_label.setText(str(exc))
            return False
        return True

    def _build_period(self) -> ReportingPeriod:
        period_type = self._period_type_combo.currentText()
        if period_type == "instant":
            qd = self._instant_date_edit.date()
            instant_date = date(qd.year(), qd.month(), qd.day())
            return ReportingPeriod(period_type="instant", instant_date=instant_date)
        else:
            qs = self._start_date_edit.date()
            qe = self._end_date_edit.date()
            return ReportingPeriod(
                period_type="duration",
                start_date=date(qs.year(), qs.month(), qs.day()),
                end_date=date(qe.year(), qe.month(), qe.day()),
            )

    def get_entity(self) -> ReportingEntity:
        return ReportingEntity(
            identifier=self._identifier_edit.text().strip(),
            scheme=self._scheme_edit.text().strip(),
        )

    def get_period(self) -> ReportingPeriod:
        return self._build_period()

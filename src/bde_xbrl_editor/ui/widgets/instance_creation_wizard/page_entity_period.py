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
from bde_xbrl_editor.instance.constants import BDE_DIM_NS
from bde_xbrl_editor.taxonomy.models import QName, TaxonomyStructure


class EntityPeriodPage(QWizardPage):
    """Wizard page 1: collect entity identifier and reporting period."""

    def __init__(self, taxonomy: TaxonomyStructure, parent=None) -> None:
        super().__init__(parent)
        self._taxonomy = taxonomy
        self.setTitle("Entity and Reporting Period")
        self.setSubTitle(
            "Enter the entity identifier, reporting period, and Agrupacion value."
        )

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._identifier_edit = QLineEdit()
        self._identifier_edit.setPlaceholderText("e.g. ES0123456789")
        self._identifier_edit.textChanged.connect(self.completeChanged)
        form.addRow("Entity Identifier *", self._identifier_edit)

        self._scheme_edit = QLineEdit()
        self._scheme_edit.setText("http://www.ecb.int/stats/money/mfi")
        self._scheme_edit.setMinimumWidth(320)
        self._scheme_edit.textChanged.connect(self.completeChanged)
        form.addRow("Entity Scheme *", self._scheme_edit)

        self._agrupacion_dim_qname = QName(BDE_DIM_NS, "Agrupacion", prefix="es-be-cm-dim")
        self._agrupacion_combo = QComboBox()
        self._populate_agrupacion_combo()
        self._agrupacion_combo.currentIndexChanged.connect(self.completeChanged)
        form.addRow("Agrupacion *", self._agrupacion_combo)

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
            if self._agrupacion_combo.count() and self._agrupacion_combo.currentData() is None:
                self._error_label.setText("Please select an Agrupacion value.")
                return False
        except (InvalidEntityIdentifierError, InvalidReportingPeriodError) as exc:
            self._error_label.setText(str(exc))
            return False
        return True

    def isComplete(self) -> bool:
        if not self._identifier_edit.text().strip():
            return False
        if not self._scheme_edit.text().strip():
            return False
        if self._agrupacion_combo.isEnabled() and self._agrupacion_combo.currentData() is None:
            return False
        return True

    def _populate_agrupacion_combo(self) -> None:
        self._agrupacion_combo.clear()
        dim_model = self._taxonomy.dimensions.get(self._agrupacion_dim_qname)
        if dim_model is None:
            self._agrupacion_combo.setEnabled(False)
            self._agrupacion_combo.addItem("Not required for this taxonomy", None)
            return

        for member in dim_model.members:
            label = self._taxonomy.labels.resolve(
                member.qname,
                language_preference=["es", "en"],
            )
            self._agrupacion_combo.addItem(label, member.qname)

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

    def get_agrupacion_member(self) -> QName | None:
        return self._agrupacion_combo.currentData()

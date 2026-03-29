"""Wizard page 3 — Z-axis dimensional configuration per table."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
    QWizardPage,
)

from bde_xbrl_editor.taxonomy.models import QName, TaxonomyStructure


class DimensionalPage(QWizardPage):
    """Wizard page 3: assign Z-axis dimension values for selected tables."""

    def __init__(self, taxonomy: TaxonomyStructure, parent=None) -> None:
        super().__init__(parent)
        self._taxonomy = taxonomy
        self.setTitle("Dimensional Configuration")
        self.setSubTitle(
            "Assign values to dimensions for each selected table. "
            "Required dimensions are marked with *."
        )

        self._layout = QVBoxLayout(self)
        self._error_label = QLabel()
        self._error_label.setStyleSheet("color: red;")
        self._error_label.setWordWrap(True)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._scroll.setWidget(self._content_widget)

        self._layout.addWidget(self._scroll)
        self._layout.addWidget(self._error_label)

        # dim_combos[table_id][dim_qname] = QComboBox
        self._dim_combos: dict[str, dict[QName, QComboBox]] = {}

    def initializePage(self) -> None:
        # Clear previous content
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._dim_combos.clear()

        selected_ids: list[str] = self.wizard().property("selected_table_ids") or []

        for tid in selected_ids:
            table = self._taxonomy.get_table(tid)
            if table is None:
                continue

            # Find Z-axis dimensions via hypercubes
            z_dims = self._get_z_dims(table.extended_link_role)
            if not z_dims:
                continue

            group = QGroupBox(f"Table: {tid}")
            form = QFormLayout(group)
            self._dim_combos[tid] = {}

            for dim_qname in z_dims:
                dim_model = self._taxonomy.dimensions.get(dim_qname)
                is_mandatory = dim_model is None or dim_model.default_member is None
                label_text = f"{dim_qname.local_name}{' *' if is_mandatory else ''}"

                combo = QComboBox()
                if not is_mandatory:
                    combo.addItem("(default)", None)
                if dim_model:
                    for member in dim_model.members:
                        member_label = self._taxonomy.labels.resolve(
                            member.qname, language_preference=["es", "en"]
                        )
                        combo.addItem(member_label, member.qname)

                self._dim_combos[tid][dim_qname] = combo
                form.addRow(label_text, combo)

            self._content_layout.addWidget(group)

        self._content_layout.addStretch()

    def _get_z_dims(self, table_elr: str) -> list[QName]:
        dims: list[QName] = []
        for hc in self._taxonomy.hypercubes:
            if hc.extended_link_role == table_elr:
                dims.extend(hc.dimensions)
        return dims

    def validatePage(self) -> bool:
        self._error_label.setText("")
        selected_ids: list[str] = self.wizard().property("selected_table_ids") or []

        for tid in selected_ids:
            table = self._taxonomy.get_table(tid)
            if table is None:
                continue

            z_dims = self._get_z_dims(table.extended_link_role)
            combos = self._dim_combos.get(tid, {})

            for dim_qname in z_dims:
                dim_model = self._taxonomy.dimensions.get(dim_qname)
                is_mandatory = dim_model is None or dim_model.default_member is None
                combo = combos.get(dim_qname)
                if combo is None:
                    continue
                selected_member = combo.currentData()
                if is_mandatory and selected_member is None:
                    self._error_label.setText(
                        f"Table '{tid}': dimension '{dim_qname.local_name}' is required."
                    )
                    return False

        return True

    def get_dimensional_configs(self) -> dict:
        from bde_xbrl_editor.instance.models import DimensionalConfiguration

        configs: dict[str, DimensionalConfiguration] = {}
        for tid, combos in self._dim_combos.items():
            assignments: dict[QName, QName] = {}
            for dim_qname, combo in combos.items():
                member = combo.currentData()
                if member is not None:
                    assignments[dim_qname] = member
            if assignments:
                configs[tid] = DimensionalConfiguration(
                    table_id=tid, dimension_assignments=assignments
                )
        return configs

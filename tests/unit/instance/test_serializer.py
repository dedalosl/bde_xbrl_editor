"""Unit tests for InstanceSerializer.to_xml() — well-formedness, structure, namespaces."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from lxml import etree

from bde_xbrl_editor.instance import (
    FilingIndicator,
    InstanceSerializer,
    ReportingEntity,
    ReportingPeriod,
    XbrlContext,
    XbrlInstance,
    XbrlUnit,
)
from bde_xbrl_editor.instance.constants import (
    FILING_IND_NS,
    LINK_NS,
    XBRLI_NS,
)
from bde_xbrl_editor.instance.context_builder import generate_context_id


def _make_minimal_instance() -> XbrlInstance:
    entity = ReportingEntity(identifier="ES0123456789", scheme="http://www.bde.es/")
    period = ReportingPeriod(period_type="instant", instant_date=date(2024, 12, 31))
    ctx_id = generate_context_id(entity, period)
    ctx = XbrlContext(
        context_id=ctx_id,
        entity=entity,
        period=period,
    )
    fi = FilingIndicator(template_id="T1", filed=True, context_ref=ctx_id)
    return XbrlInstance(
        taxonomy_entry_point=Path("/tmp/entry.xsd"),
        schema_ref_href="/tmp/entry.xsd",
        entity=entity,
        period=period,
        filing_indicators=[fi],
        included_table_ids=["T1"],
        contexts={ctx_id: ctx},
        units={
            "EUR": XbrlUnit(unit_id="EUR", measure_uri="http://www.xbrl.org/2003/iso4217:EUR"),
            "pure": XbrlUnit(unit_id="pure", measure_uri="http://www.xbrl.org/2003/instance:pure"),
        },
        _dirty=True,
    )


class TestToXml:
    def test_output_is_bytes(self):
        result = InstanceSerializer().to_xml(_make_minimal_instance())
        assert isinstance(result, bytes)

    def test_output_is_well_formed_xml(self):
        result = InstanceSerializer().to_xml(_make_minimal_instance())
        # Should not raise
        root = etree.fromstring(result)
        assert root is not None

    def test_root_is_xbrli_xbrl(self):
        result = InstanceSerializer().to_xml(_make_minimal_instance())
        root = etree.fromstring(result)
        assert root.tag == f"{{{XBRLI_NS}}}xbrl"

    def test_schema_ref_present(self):
        result = InstanceSerializer().to_xml(_make_minimal_instance())
        root = etree.fromstring(result)
        refs = root.findall(f"{{{LINK_NS}}}schemaRef")
        assert len(refs) == 1

    def test_context_present(self):
        result = InstanceSerializer().to_xml(_make_minimal_instance())
        root = etree.fromstring(result)
        contexts = root.findall(f"{{{XBRLI_NS}}}context")
        assert len(contexts) >= 1

    def test_filing_indicators_present(self):
        result = InstanceSerializer().to_xml(_make_minimal_instance())
        root = etree.fromstring(result)
        indicators = root.findall(
            f".//{{{FILING_IND_NS}}}filingIndicator"
        )
        assert len(indicators) == 1
        assert indicators[0].text == "T1"

    def test_namespace_prefixes_declared(self):
        result = InstanceSerializer().to_xml(_make_minimal_instance())
        # Check that key namespaces appear in the output
        xml_text = result.decode("utf-8")
        assert "xbrli" in xml_text
        assert "link" in xml_text
        assert "xlink" in xml_text

    def test_instant_period_serialised(self):
        result = InstanceSerializer().to_xml(_make_minimal_instance())
        xml_text = result.decode("utf-8")
        assert "2024-12-31" in xml_text

    def test_duration_period_serialised(self):
        entity = ReportingEntity(identifier="ES123", scheme="http://www.bde.es/")
        period = ReportingPeriod(
            period_type="duration",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
        )
        ctx_id = generate_context_id(entity, period)
        ctx = XbrlContext(context_id=ctx_id, entity=entity, period=period)
        inst = XbrlInstance(
            taxonomy_entry_point=Path("/tmp/entry.xsd"),
            schema_ref_href="/tmp/entry.xsd",
            entity=entity,
            period=period,
            contexts={ctx_id: ctx},
            _dirty=True,
        )
        result = InstanceSerializer().to_xml(inst)
        xml_text = result.decode("utf-8")
        assert "2024-01-01" in xml_text
        assert "2024-12-31" in xml_text

    def test_unit_elements_present(self):
        result = InstanceSerializer().to_xml(_make_minimal_instance())
        root = etree.fromstring(result)
        units = root.findall(f"{{{XBRLI_NS}}}unit")
        assert len(units) >= 1

    def test_xml_declaration_present(self):
        result = InstanceSerializer().to_xml(_make_minimal_instance())
        assert result.startswith(b"<?xml")


class TestSave:
    def test_writes_file(self, tmp_path):
        inst = _make_minimal_instance()
        path = tmp_path / "output.xbrl"
        InstanceSerializer().save(inst, path)
        assert path.exists()
        assert path.stat().st_size > 0

    def test_marks_saved(self, tmp_path):
        inst = _make_minimal_instance()
        path = tmp_path / "output.xbrl"
        InstanceSerializer().save(inst, path)
        assert inst.source_path == path
        assert inst.has_unsaved_changes is False

    def test_saved_file_is_valid_xml(self, tmp_path):
        inst = _make_minimal_instance()
        path = tmp_path / "output.xbrl"
        InstanceSerializer().save(inst, path)
        tree = etree.parse(str(path))  # noqa: S320
        assert tree.getroot() is not None

    def test_save_error_on_bad_path(self):
        from bde_xbrl_editor.instance import InstanceSaveError

        inst = _make_minimal_instance()
        with pytest.raises(InstanceSaveError):
            InstanceSerializer().save(inst, "/nonexistent/dir/output.xbrl")

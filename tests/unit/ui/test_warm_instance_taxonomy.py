"""Real-parser regressions for warm instance DTS handoff and isolation."""

from dataclasses import replace
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bde_xbrl_editor.instance.parser import InstanceParser
from bde_xbrl_editor.taxonomy import LoaderSettings, TaxonomyCache, TaxonomyLoader
from bde_xbrl_editor.taxonomy.models import Concept, QName, TaxonomyMetadata, TaxonomyStructure
from bde_xbrl_editor.ui import loading

AMOUNT = QName("urn:test", "Amount")
EXTRA = QName("urn:test", "Extra")


def taxonomy(path):
    return TaxonomyStructure(
        TaxonomyMetadata(path.stem, "1", "Test", path.resolve(), datetime.now(), ("en",)),
        {
            AMOUNT: Concept(
                AMOUNT, QName("http://www.xbrl.org/2003/instance", "decimalItemType"), "instant"
            )
        },
        None,
        {},
        {},
        {},
        (),
        {},
        (),
    )


def instance_file(tmp_path, name="b", *, linkbase=False, extra_fact=False):
    schema = tmp_path / f"{name}.xsd"
    schema.write_text('<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"/>')
    refs = ""
    if linkbase:
        (tmp_path / "extra.xml").write_text("<linkbase/>")
        refs = '<link:linkbaseRef xlink:type="simple" xlink:href="extra.xml"/>'
    extra = '<test:Extra contextRef="c">extra</test:Extra>' if extra_fact else ""
    path = tmp_path / f"{name}.xbrl"
    path.write_text(
        '<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" '
        'xmlns:link="http://www.xbrl.org/2003/linkbase" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:test="urn:test">'
        f'<link:schemaRef xlink:type="simple" xlink:href="{name}.xsd"/>{refs}'
        '<xbrli:context id="c"><xbrli:entity><xbrli:identifier scheme="urn:entity">E'
        "</xbrli:identifier></xbrli:entity><xbrli:period><xbrli:instant>2026-01-01"
        "</xbrli:instant></xbrli:period></xbrli:context>"
        f'<test:Amount contextRef="c" decimals="2">1234.56</test:Amount>{extra}</xbrli:xbrl>'
    )
    return path


def controlled_loader(monkeypatch, base):
    enriched = replace(
        base,
        concepts={
            **base.concepts,
            EXTRA: Concept(
                EXTRA, QName("http://www.xbrl.org/2003/instance", "stringItemType"), "instant"
            ),
        },
    )
    loader = TaxonomyLoader(TaxonomyCache(), LoaderSettings())
    monkeypatch.setattr(
        loader,
        "_do_load",
        Mock(
            side_effect=lambda path, progress_callback, *, seed_linkbases: (
                enriched if seed_linkbases else base
            )
        ),
    )
    monkeypatch.setattr(loading, "TaxonomyLoader", lambda **kwargs: loader)
    return loader, enriched


def warm(path, previous):
    return loading._parse_instance_with_preloaded_taxonomy(
        str(path), LoaderSettings(), previous, progress_callback=lambda *args: None
    )


def test_different_schema_returns_parser_resolved_taxonomy(monkeypatch, tmp_path):
    path = instance_file(tmp_path)
    previous = taxonomy(tmp_path / "a.xsd")
    current = taxonomy(tmp_path / "b.xsd")
    loader, _ = controlled_loader(monkeypatch, current)
    instance, result, orphaned = warm(path, previous)
    assert result is current
    assert instance.taxonomy_entry_point == current.metadata.entry_point_path
    assert instance.facts[0].value == "1234.56"
    assert orphaned == 0
    assert loader._do_load.call_count == 1


def test_same_schema_without_extensions_reuses_identity(monkeypatch, tmp_path):
    path = instance_file(tmp_path)
    current = taxonomy(tmp_path / "b.xsd")
    loader, _ = controlled_loader(monkeypatch, current)
    _, result, _ = warm(path, current)
    assert result is current
    loader._do_load.assert_not_called()


@pytest.mark.parametrize("preloaded", [False, True])
def test_instance_linkbase_enrichment_precedes_fact_parse_and_callback(
    monkeypatch, tmp_path, preloaded
):
    path = instance_file(tmp_path, linkbase=True, extra_fact=True)
    base = taxonomy(tmp_path / "b.xsd")
    loader, _ = controlled_loader(monkeypatch, base)
    ready = []
    instance, orphaned = InstanceParser(loader).load(
        path,
        preloaded_taxonomy=base if preloaded else None,
        taxonomy_resolved_callback=ready.append,
    )
    assert EXTRA in ready[0].concepts
    assert [fact.concept for fact in instance.facts] == [AMOUNT, EXTRA]
    assert orphaned == []
    assert EXTRA not in base.concepts
    assert loader._do_load.call_count == 1


def test_warm_and_cold_linkbase_handoff_match_without_duplicate_load(monkeypatch, tmp_path):
    path = instance_file(tmp_path, linkbase=True, extra_fact=True)
    base = taxonomy(tmp_path / "b.xsd")
    loader, _ = controlled_loader(monkeypatch, base)
    instance, enriched, orphaned = warm(path, base)
    assert EXTRA in enriched.concepts
    assert orphaned == 0
    messages = []
    loading._instance_load_process_entry(
        str(path), LoaderSettings(), None, SimpleNamespace(put=messages.append)
    )
    finished = next(message for message in messages if message[0] == "finished")
    assert finished[2] is enriched
    assert finished[3] == 0
    assert finished[1].facts == instance.facts
    assert loader._do_load.call_count == 1


def test_next_document_does_not_inherit_previous_instance_extensions(monkeypatch, tmp_path):
    path = instance_file(tmp_path, linkbase=True, extra_fact=True)
    base = taxonomy(tmp_path / "b.xsd")
    loader, _ = controlled_loader(monkeypatch, base)
    _, enriched, _ = warm(path, base)
    plain = instance_file(tmp_path, extra_fact=True)
    instance, result, orphaned = warm(plain, enriched)
    assert result is base
    assert EXTRA not in result.concepts
    assert orphaned == 1
    assert [fact.concept for fact in instance.facts] == [AMOUNT]
    assert EXTRA not in base.concepts
    assert loader._do_load.call_count == 2


def test_worker_completion_installs_resolved_taxonomy_in_actual_workspace(
    qtbot, monkeypatch, tmp_path
):
    from PySide6.QtCore import QThread

    from bde_xbrl_editor.ui.main_window import MainWindow
    from bde_xbrl_editor.ui.widgets import loader_settings_dialog as settings

    monkeypatch.setattr(settings, "_SETTINGS_FILE", tmp_path / "settings.json")
    settings.save_decimal_separator(",")
    monkeypatch.setattr("bde_xbrl_editor.ui.main_window.load_loader_page_mode", lambda: "classic")
    path = instance_file(tmp_path)
    old = taxonomy(tmp_path / "a.xsd")
    current = taxonomy(tmp_path / "b.xsd")
    controlled_loader(monkeypatch, current)
    window = MainWindow()
    qtbot.addWidget(
        window, before_close_func=lambda _: setattr(window._current_instance, "_dirty", False)
    )
    window._current_taxonomy = old
    worker = loading.InstanceLoadWorker(TaxonomyCache(), LoaderSettings(), path)
    worker.set_preloaded_taxonomy(old)
    worker.finished.connect(window._on_open_instance_finished)
    worker.run()
    assert window._current_taxonomy is current
    assert window._sidebar._taxonomy is current
    assert window._current_instance.facts[0].concept in current.concepts
    assert window._table_view._decimal_separator == ","
    request = Mock()
    monkeypatch.setattr(window._table_view, "request_table", request)
    table = SimpleNamespace(table_id="B", label="B")
    window._on_table_selected(table)
    assert request.call_args.kwargs["taxonomy"] is current
    assert request.call_args.kwargs["instance"] is window._current_instance
    monkeypatch.setattr(QThread, "start", lambda self: None)
    window._trigger_validation()
    assert window._validation_worker._taxonomy is current
    assert window._validation_worker._instance.facts == window._current_instance.facts
    window._cleanup_validation_thread(cancel=True)


def test_secondary_schema_enrichment_survives_warm_cold_and_next_document(monkeypatch, tmp_path):
    path = instance_file(tmp_path, extra_fact=True)
    text = path.read_text().replace(
        "<xbrli:context",
        '<link:schemaRef xlink:type="simple" xlink:href="secondary.xsd"/><xbrli:context',
        1,
    )
    path.write_text(text)
    secondary_path = tmp_path / "secondary.xsd"
    secondary_path.write_text('<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"/>')
    base = taxonomy(tmp_path / "b.xsd")
    secondary = replace(
        taxonomy(secondary_path),
        concepts={
            EXTRA: Concept(
                EXTRA, QName("http://www.xbrl.org/2003/instance", "stringItemType"), "instant"
            )
        },
    )
    loader = TaxonomyLoader(TaxonomyCache(), LoaderSettings())
    monkeypatch.setattr(
        loader,
        "_do_load",
        Mock(
            side_effect=lambda entry, progress_callback, *, seed_linkbases: (
                secondary if entry == secondary_path else base
            )
        ),
    )
    monkeypatch.setattr(loading, "TaxonomyLoader", lambda **kwargs: loader)
    instance, merged, count = warm(path, base)
    assert EXTRA in merged.concepts
    assert count == 0
    assert instance.facts[-1].concept == EXTRA
    assert EXTRA not in base.concepts
    messages = []
    loading._instance_load_process_entry(
        str(path), LoaderSettings(), None, SimpleNamespace(put=messages.append)
    )
    final = next(message for message in messages if message[0] == "finished")
    assert EXTRA in final[2].concepts
    assert final[3] == 0
    plain = instance_file(tmp_path, extra_fact=True)
    _, result, count = warm(plain, merged)
    assert result is base
    assert count == 1
    assert EXTRA not in result.concepts


def test_loader_provenance_is_immutable_cache_keyed_and_reload_preserved(monkeypatch, tmp_path):
    entry = tmp_path / "b.xsd"
    seed = tmp_path / "extra.xml"
    base = taxonomy(entry)
    loader = TaxonomyLoader(TaxonomyCache(), LoaderSettings())
    monkeypatch.setattr(loader, "_do_load", Mock(return_value=base))
    plain = loader.load(entry)
    enriched = loader.load(entry, instance_linkbase_seeds=[seed])
    assert getattr(enriched, "instance_dts_roots", ()) == (seed.resolve(),)
    assert enriched is not base
    assert getattr(base, "instance_dts_roots", ()) == ()
    assert loader.load(entry) is plain
    assert loader.load(entry, instance_linkbase_seeds=[seed]) is enriched
    reloaded = loader.reload(entry, instance_linkbase_seeds=[seed])
    assert reloaded.instance_dts_roots == enriched.instance_dts_roots
    assert loader.load(entry) is plain


def test_open_failure_preserves_current_document_and_workspace(qtbot, monkeypatch, tmp_path):
    from bde_xbrl_editor.ui.main_window import MainWindow
    from bde_xbrl_editor.ui.widgets import loader_settings_dialog as settings

    monkeypatch.setattr(settings, "_SETTINGS_FILE", tmp_path / "settings.json")
    monkeypatch.setattr("bde_xbrl_editor.ui.main_window.load_loader_page_mode", lambda: "classic")
    path = instance_file(tmp_path)
    base = taxonomy(tmp_path / "b.xsd")
    loader, _ = controlled_loader(monkeypatch, base)
    instance, _, _ = warm(path, base)
    window = MainWindow()
    qtbot.addWidget(window, before_close_func=lambda _: setattr(instance, "_dirty", False))
    window._current_taxonomy = base
    window._load_instance(instance)
    editor = window._editor
    new_path = instance_file(tmp_path, "other")
    loader._do_load.side_effect = RuntimeError("Failed new taxonomy")
    alert = Mock()
    monkeypatch.setattr("bde_xbrl_editor.ui.main_window.QMessageBox.critical", alert)
    worker = loading.InstanceLoadWorker(TaxonomyCache(), LoaderSettings(), new_path)
    worker.set_preloaded_taxonomy(base)
    worker.error.connect(window._on_open_instance_error)
    worker.finished.connect(window._on_open_instance_finished)
    worker.run()
    assert alert.call_count == 1
    assert window._current_taxonomy is base
    assert window._current_instance is instance
    assert window._editor is editor
    assert instance.facts[0].value == "1234.56"


def test_older_cached_structure_without_provenance_reuses_plain_schema(monkeypatch, tmp_path):
    path = instance_file(tmp_path)
    base = taxonomy(tmp_path / "b.xsd")
    object.__delattr__(base, "instance_dts_roots")
    loader, _ = controlled_loader(monkeypatch, taxonomy(tmp_path / "b.xsd"))
    _, result, _ = warm(path, base)
    assert result is not base
    assert result.instance_dts_roots == ()
    assert not hasattr(base, "instance_dts_roots")
    loader._do_load.assert_not_called()


@pytest.mark.parametrize("seeded", [False, True])
def test_older_seeded_cache_restores_provenance_without_mutating_shared_value(
    monkeypatch, tmp_path, seeded
):
    entry = tmp_path / "b.xsd"
    seed = tmp_path / "extra.xml"
    loader = TaxonomyLoader(TaxonomyCache(), LoaderSettings())
    monkeypatch.setattr(loader, "_do_load", Mock(return_value=taxonomy(entry)))
    seeds = [seed] if seeded else []
    old = loader.load(entry, instance_linkbase_seeds=seeds)
    object.__delattr__(old, "instance_dts_roots")
    restored = loader.load(entry, instance_linkbase_seeds=seeds)
    assert restored is not old
    assert restored.instance_dts_roots == ((seed.resolve(),) if seeded else ())
    assert not hasattr(old, "instance_dts_roots")
    assert loader.load(entry, instance_linkbase_seeds=seeds) is restored
    hydrated = loader.hydrate_deferred_formula_assertions(restored)
    assert hydrated.instance_dts_roots == restored.instance_dts_roots


def test_legacy_warm_taxonomy_can_hydrate_real_deferred_formula(monkeypatch, tmp_path):
    path = instance_file(tmp_path)
    formula = tmp_path / "deferred-formula.xml"
    formula.write_text(
        '<link:linkbase xmlns:link="http://www.xbrl.org/2003/linkbase" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" '
        'xmlns:gen="http://xbrl.org/2008/generic" '
        'xmlns:va="http://xbrl.org/2008/assertion/value">'
        '<gen:link xlink:type="extended" xlink:role="urn:rules">'
        '<va:valueAssertion xlink:type="resource" xlink:label="a1" id="a1" test="true()"/>'
        "</gen:link></link:linkbase>"
    )
    legacy = replace(taxonomy(tmp_path / "b.xsd"), linkbase_files=(formula,))
    # Prove this fixture actually enters the replace-bearing hydration branch.
    control = TaxonomyLoader(TaxonomyCache(), LoaderSettings()).hydrate_deferred_formula_assertions(
        legacy
    )
    assert len(control.formula_assertion_set.assertions) == 1
    object.__delattr__(legacy, "instance_dts_roots")
    loader, _ = controlled_loader(monkeypatch, taxonomy(tmp_path / "b.xsd"))
    _, result, _ = warm(path, legacy)
    hydrated = loader.hydrate_deferred_formula_assertions(result)
    assert len(hydrated.formula_assertion_set.assertions) == 1
    assert hydrated.instance_dts_roots == ()
    assert result is not legacy
    assert not hasattr(legacy, "instance_dts_roots")
    assert legacy.formula_assertion_set.assertions == ()
    loader._do_load.assert_not_called()

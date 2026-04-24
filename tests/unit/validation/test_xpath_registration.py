from __future__ import annotations

import logging

from bde_xbrl_editor.taxonomy.models import CustomFunctionDefinition
from bde_xbrl_editor.validation.formula.xpath_registration import (
    build_registered_parser_class,
    register_custom_functions,
)


def test_build_registered_parser_class_registers_project_functions() -> None:
    def always_true() -> bool:
        return True

    parser_class = build_registered_parser_class(
        xfi_namespace="http://example.com/xfi",
        efn_namespace="http://example.com/efn",
        iaf_namespace="http://example.com/iaf",
        xfi_functions=[("always-true", always_true)],
        efn_functions=[],
        iaf_functions=[],
    )

    parser = parser_class(namespaces={"xfi": "http://example.com/xfi"})
    token = parser.parse("xfi:always-true()")

    assert bool(token.evaluate()) is True


def test_register_custom_functions_groups_overloads_and_sets_namespace() -> None:
    registered: list[tuple[str | None, str]] = []

    class FakeParser:
        namespaces: dict[str, str] = {}

        def external_function(self, callback, *, name, prefix, sequence_types):
            registered.append((prefix, name))
            assert callback("value") == "called:2"
            assert sequence_types == ()

    definitions = (
        CustomFunctionDefinition(
            name="eg:normalize",
            namespace="http://example.com/functions",
            local_name="normalize",
            prefix="eg",
            input_names=("value",),
        ),
        CustomFunctionDefinition(
            name="eg:normalize",
            namespace="http://example.com/functions",
            local_name="normalize",
            prefix="eg",
            input_names=("left", "right"),
        ),
    )

    def make_callback(grouped_definitions: list[CustomFunctionDefinition]):
        def callback(*args):
            return f"called:{len(grouped_definitions)}"

        return callback

    parser = FakeParser()
    register_custom_functions(parser, definitions, make_callback)

    assert parser.namespaces["eg"] == "http://example.com/functions"
    assert registered == [("eg", "normalize")]


def test_register_custom_functions_logs_registration_failures(caplog) -> None:
    class RejectingParser:
        namespaces: dict[str, str] = {}

        def external_function(self, callback, *, name, prefix, sequence_types):
            raise ValueError("duplicate")

    definition = CustomFunctionDefinition(
        name="eg:bad",
        namespace="http://example.com/functions",
        local_name="bad",
        prefix="eg",
        input_names=(),
    )

    with caplog.at_level(
        logging.DEBUG,
        logger="bde_xbrl_editor.validation.formula.xpath_registration",
    ):
        register_custom_functions(RejectingParser(), (definition,), lambda _defs: lambda: None)

    assert "Skipping external XPath function registration for eg:bad" in caplog.text

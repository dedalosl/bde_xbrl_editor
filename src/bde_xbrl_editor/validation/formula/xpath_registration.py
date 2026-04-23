"""XPath parser registration helpers for formula validation.

Module boundaries:
- ``xfi_functions`` owns the actual xfi/efn/iaf function implementations.
- This module owns wiring those functions into elementpath parser instances.
- Custom function evaluation stays with ``xfi_functions`` because it depends on
  formula evaluation context; this module only registers provided callbacks.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from bde_xbrl_editor.taxonomy.models import CustomFunctionDefinition

log = logging.getLogger(__name__)

FunctionSpec = tuple[str, Callable[..., Any]]
IntervalFunctionSpec = tuple[str, Callable[..., Any], tuple[str, ...]]
CustomCallbackFactory = Callable[[list[CustomFunctionDefinition]], Callable[..., Any]]


def _register_external_function(
    parser: Any,
    callback: Callable[..., Any],
    *,
    name: str,
    prefix: str | None,
    sequence_types: tuple[str, ...] = (),
) -> None:
    """Register an XPath function, logging duplicate/incompatible bindings."""
    try:
        parser.external_function(
            callback,
            name=name,
            prefix=prefix,
            sequence_types=sequence_types,
        )
    except Exception as exc:  # noqa: BLE001
        log.debug(
            "Skipping external XPath function registration for %s:%s: %s",
            prefix,
            name,
            exc,
        )


def build_registered_parser_class(
    *,
    xfi_namespace: str,
    efn_namespace: str,
    iaf_namespace: str,
    xfi_functions: list[FunctionSpec],
    efn_functions: list[FunctionSpec],
    iaf_functions: list[IntervalFunctionSpec],
) -> type:
    """Create an elementpath XPath2Parser subclass with project functions registered."""
    import elementpath

    class XbrlFormulaParser(elementpath.XPath2Parser):
        symbol_table = dict(elementpath.XPath2Parser.symbol_table)
        function_signatures = dict(elementpath.XPath2Parser.function_signatures)

    temp = XbrlFormulaParser(
        namespaces={"xfi": xfi_namespace, "efn": efn_namespace, "iaf": iaf_namespace}
    )
    for local_name, callback in xfi_functions:
        _register_external_function(temp, callback, name=local_name, prefix="xfi")
    for local_name, callback in efn_functions:
        _register_external_function(temp, callback, name=local_name, prefix="efn")
    for local_name, callback, sequence_types in iaf_functions:
        _register_external_function(
            temp,
            callback,
            name=local_name,
            prefix="iaf",
            sequence_types=sequence_types,
        )

    XbrlFormulaParser.symbol_table = temp.symbol_table
    XbrlFormulaParser.function_signatures = temp.function_signatures
    return XbrlFormulaParser


def _custom_function_groups(
    definitions: tuple[CustomFunctionDefinition, ...],
) -> dict[tuple[str, str], list[CustomFunctionDefinition]]:
    groups: dict[tuple[str, str], list[CustomFunctionDefinition]] = {}
    for definition in definitions:
        groups.setdefault((definition.namespace, definition.local_name), []).append(definition)
    return groups


def register_custom_functions(
    parser: Any,
    definitions: tuple[CustomFunctionDefinition, ...],
    make_callback: CustomCallbackFactory,
) -> None:
    """Register linkbase-defined custom functions on a parser instance."""
    for grouped_definitions in _custom_function_groups(definitions).values():
        definition = grouped_definitions[0]
        prefix = definition.prefix
        if prefix and prefix not in parser.namespaces:
            parser.namespaces[prefix] = definition.namespace
        _register_external_function(
            parser,
            make_callback(grouped_definitions),
            name=definition.local_name,
            prefix=prefix,
        )

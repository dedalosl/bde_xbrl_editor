"""Parse linkbase-defined custom functions (variable:function + cfi:implementation)."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from bde_xbrl_editor.taxonomy.models import CustomFunctionDefinition, CustomFunctionStep
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file

_NS_VARIABLE = "http://xbrl.org/2008/variable"
_NS_CFI = "http://xbrl.org/2010/custom-function"
_NS_GENERIC = "http://xbrl.org/2008/generic"
_NS_XLINK = "http://www.w3.org/1999/xlink"

_TAG_FUNCTION = f"{{{_NS_VARIABLE}}}function"
_TAG_VARIABLE_INPUT = f"{{{_NS_VARIABLE}}}input"
_TAG_IMPLEMENTATION = f"{{{_NS_CFI}}}implementation"
_TAG_CFI_INPUT = f"{{{_NS_CFI}}}input"
_TAG_CFI_STEP = f"{{{_NS_CFI}}}step"
_TAG_CFI_OUTPUT = f"{{{_NS_CFI}}}output"
_TAG_GEN_ARC = f"{{{_NS_GENERIC}}}arc"

_ATTR_XLINK_LABEL = f"{{{_NS_XLINK}}}label"
_ATTR_XLINK_FROM = f"{{{_NS_XLINK}}}from"
_ATTR_XLINK_TO = f"{{{_NS_XLINK}}}to"
_ATTR_XLINK_ARCROLE = f"{{{_NS_XLINK}}}arcrole"

_ARCROLE_FUNCTION_IMPLEMENTATION = "http://xbrl.org/arcrole/2010/function-implementation"


def parse_custom_function_linkbase(linkbase_path: Path) -> tuple[CustomFunctionDefinition, ...]:
    """Return custom functions declared in *linkbase_path*.

    A function is recognized only when its signature resource is connected to a
    ``cfi:implementation`` resource through the standard function-implementation
    arcrole.
    """
    if not linkbase_path.exists():
        return ()

    try:
        tree = parse_xml_file(linkbase_path)
    except etree.XMLSyntaxError:
        return ()

    root = tree.getroot()
    function_index = {
        (el.get(_ATTR_XLINK_LABEL) or "").strip(): el
        for el in root.iter(_TAG_FUNCTION)
        if (el.get(_ATTR_XLINK_LABEL) or "").strip()
    }
    implementation_index = {
        (el.get(_ATTR_XLINK_LABEL) or "").strip(): el
        for el in root.iter(_TAG_IMPLEMENTATION)
        if (el.get(_ATTR_XLINK_LABEL) or "").strip()
    }

    functions: list[CustomFunctionDefinition] = []
    for arc in root.iter(_TAG_GEN_ARC):
        if (arc.get(_ATTR_XLINK_ARCROLE) or "").strip() != _ARCROLE_FUNCTION_IMPLEMENTATION:
            continue
        from_label = (arc.get(_ATTR_XLINK_FROM) or "").strip()
        to_label = (arc.get(_ATTR_XLINK_TO) or "").strip()
        function_el = function_index.get(from_label)
        implementation_el = implementation_index.get(to_label)
        if function_el is None or implementation_el is None:
            continue
        definition = _parse_function_definition(function_el, implementation_el)
        if definition is not None:
            functions.append(definition)

    return tuple(functions)


def _parse_function_definition(
    function_el: etree._Element,
    implementation_el: etree._Element,
) -> CustomFunctionDefinition | None:
    qname = (function_el.get("name") or "").strip()
    if ":" not in qname:
        return None

    prefix, local_name = qname.split(":", 1)
    namespace = (function_el.nsmap or {}).get(prefix)
    if not namespace:
        return None

    input_types = tuple(
        (input_el.get("type") or "").strip()
        for input_el in function_el.findall(_TAG_VARIABLE_INPUT)
    )
    output_type = (function_el.get("output") or "").strip() or None
    input_names = tuple(
        (input_el.get("name") or "").strip()
        for input_el in implementation_el.findall(_TAG_CFI_INPUT)
        if (input_el.get("name") or "").strip()
    )

    steps: list[CustomFunctionStep] = []
    for child in implementation_el:
        if child.tag == _TAG_CFI_STEP:
            expression = "".join(child.itertext()).strip()
            name = (child.get("name") or "").strip() or None
            if expression:
                steps.append(CustomFunctionStep(expression=expression, name=name))
        elif child.tag == _TAG_CFI_OUTPUT:
            expression = "".join(child.itertext()).strip()
            if expression:
                steps.append(CustomFunctionStep(expression=expression, is_output=True))

    if not steps:
        return None

    namespaces = {key: value for key, value in implementation_el.nsmap.items() if key and value}
    namespaces.setdefault(prefix, namespace)

    return CustomFunctionDefinition(
        name=qname,
        namespace=namespace,
        local_name=local_name,
        prefix=prefix,
        input_names=input_names,
        input_types=input_types,
        output_type=output_type,
        steps=tuple(steps),
        namespaces=namespaces,
    )

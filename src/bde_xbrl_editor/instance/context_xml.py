"""Reconcile editable dimensions with preserved context XML, without mutation."""

from copy import deepcopy

from lxml import etree

from bde_xbrl_editor.instance.constants import XBRLDI_NS, XBRLI_NS
from bde_xbrl_editor.instance.models import XbrlContext
from bde_xbrl_editor.taxonomy.models import QName
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_fragment

_EXPLICIT = f"{{{XBRLDI_NS}}}explicitMember"
_TYPED = f"{{{XBRLDI_NS}}}typedMember"


def append_preserving_namespaces(parent: etree._Element, source: etree._Element) -> etree._Element:
    """Copy in place: lxml append otherwise discards aliases used in QName text."""
    if not isinstance(source.tag, str):
        child = deepcopy(source)
        parent.append(child)
        return child
    child = etree.SubElement(parent, source.tag, attrib=dict(source.attrib), nsmap=source.nsmap)
    child.text, child.tail = source.text, source.tail
    for nested in source:
        append_preserving_namespaces(child, nested)
    return child


def _resolve(element: etree._Element, lexical: str) -> QName:
    if lexical.startswith("{"):
        return QName.from_clark(lexical)
    prefix, sep, local = lexical.partition(":")
    return QName(element.nsmap.get(prefix if sep else None, ""), local if sep else prefix)


def effective_context_containers(
    ctx: XbrlContext, ns_to_prefix: dict[str, str] | None = None
) -> dict[str, etree._Element]:
    """Return fresh XML containers; current model dimensions override source nodes."""
    containers = {}
    for name, raw in (("segment", ctx.segment_xml), ("scenario", ctx.scenario_xml)):
        if raw:
            containers[name] = parse_xml_fragment(raw)

    explicit = {d: m for d, m in ctx.dimensions.items() if d not in ctx.typed_dimensions}
    desired = set(explicit) | set(ctx.typed_dimensions)
    replacements = {}
    for dim in sorted(desired, key=str):
        name = ctx.dim_containers.get(dim, ctx.context_element)
        if name not in ("segment", "scenario"):
            raise ValueError(f"Invalid dimension container: {name}")
        if name not in containers:
            containers[name] = etree.Element(f"{{{XBRLI_NS}}}{name}")
        container = containers[name]
        is_typed = dim in ctx.typed_dimensions
        prefixes = {uri: prefix for prefix, uri in container.nsmap.items() if prefix}
        prefixes.update(ns_to_prefix or {})

        def lexical(qname: QName, prefixes=prefixes) -> str:
            if not qname.namespace:
                return qname.local_name
            if qname.namespace not in prefixes:
                candidate = "dim"
                while candidate in prefixes.values():
                    candidate += "_"
                prefixes[qname.namespace] = candidate
            return f"{prefixes[qname.namespace]}:{qname.local_name}"

        dimension_text = lexical(dim)
        member_text = lexical(explicit[dim]) if not is_typed else None
        child = etree.Element(
            _TYPED if is_typed else _EXPLICIT,
            nsmap={prefix: uri for uri, prefix in prefixes.items()},
        )
        child.set("dimension", dimension_text)
        if is_typed:
            value = ctx.typed_dimensions[dim]
            element_qname = ctx.typed_dimension_elements.get(dim, dim)
            element_tag = (
                f"{{{element_qname.namespace}}}{element_qname.local_name}"
                if element_qname.namespace
                else element_qname.local_name
            )
            raw = ctx.typed_dimension_xml.get(dim)
            source = parse_xml_fragment(raw) if raw else None
            if source is not None:
                source.tag = element_tag
                if "".join(source.itertext()).strip() != value:
                    if len(source):
                        raise ValueError(
                            f"Cannot replace complex typed dimension {dim} with a scalar value"
                        )
                    source.text = value
                append_preserving_namespaces(child, source)
            else:
                node = etree.SubElement(child, element_tag)
                node.text = value
        else:
            child.text = member_text
        replacements[dim] = child

    result = {}
    emitted = set()
    for name, container in containers.items():
        target = etree.Element(container.tag, attrib=dict(container.attrib), nsmap=container.nsmap)
        target.text, target.tail = container.text, container.tail
        for source in container:
            if source.tag in (_EXPLICIT, _TYPED):
                dim = _resolve(source, source.get("dimension", ""))
                if dim not in desired or ctx.dim_containers.get(dim, ctx.context_element) != name:
                    if source.tail:
                        if len(target):
                            target[-1].tail = (target[-1].tail or "") + source.tail
                        else:
                            target.text = (target.text or "") + source.tail
                    continue
                replacement = replacements[dim]
                replacement.tail = source.tail
                append_preserving_namespaces(target, replacement)
                emitted.add(dim)
            else:
                append_preserving_namespaces(target, source)
        for dim in sorted(desired - emitted, key=str):
            if ctx.dim_containers.get(dim, ctx.context_element) == name:
                append_preserving_namespaces(target, replacements[dim])
                emitted.add(dim)
        if len(target) or (target.text or "").strip():
            result[name] = target
    return result

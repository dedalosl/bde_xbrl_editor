"""Shared XML parsing helpers for taxonomy, instance, and conformance XML."""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from lxml import etree

_MALFORMED_PREFIXED_START_TAG_RE = re.compile(r"<\s+([A-Za-z_][\w.-]*:)")

XML_PARSER_OPTIONS = {
    "resolve_entities": False,
    "no_network": True,
    "load_dtd": False,
    "recover": False,
    "remove_blank_text": False,
}


def make_xml_parser() -> etree.XMLParser:
    """Return the project-wide XML parser with explicit safety options."""
    return etree.XMLParser(**XML_PARSER_OPTIONS)


def parse_xml_bytes(raw: bytes, *, repair_malformed_prefixed_tags: bool = False) -> etree._ElementTree:
    """Parse XML bytes with the shared parser configuration."""
    try:
        return etree.parse(BytesIO(raw), parser=make_xml_parser())  # noqa: S320
    except etree.XMLSyntaxError as exc:
        if not repair_malformed_prefixed_tags:
            raise
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise exc from None
        repaired = _MALFORMED_PREFIXED_START_TAG_RE.sub(r"<\1", text)
        if repaired == text:
            raise exc
        return etree.parse(  # noqa: S320
            BytesIO(repaired.encode("utf-8")),
            parser=make_xml_parser(),
        )


def parse_xml_text(text: str) -> etree._ElementTree:
    """Parse XML text with the shared parser configuration."""
    return parse_xml_bytes(text.encode("utf-8"))


def parse_xml_fragment(fragment: bytes | str) -> etree._Element:
    """Parse a single XML element fragment with the shared parser configuration."""
    return etree.fromstring(fragment, parser=make_xml_parser())  # noqa: S320


def parse_xml_file(path: Path) -> etree._ElementTree:
    """Parse XML, repairing known malformed prefixed start tags when possible.

    Some vendor taxonomies contain start tags such as ``< df:linkrole>``.
    These are not well-formed XML, but they can be repaired safely by removing
    the stray whitespace after ``<``.
    """
    return parse_xml_bytes(path.read_bytes(), repair_malformed_prefixed_tags=True)

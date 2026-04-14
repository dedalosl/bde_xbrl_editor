"""Shared XML parsing helpers for taxonomy files."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

from lxml import etree

_MALFORMED_PREFIXED_START_TAG_RE = re.compile(r"<\s+([A-Za-z_][\w.-]*:)")


def parse_xml_file(path: Path) -> etree._ElementTree:
    """Parse XML, repairing known malformed prefixed start tags when possible.

    Some vendor taxonomies contain start tags such as ``< df:linkrole>``.
    These are not well-formed XML, but they can be repaired safely by removing
    the stray whitespace after ``<``.
    """
    try:
        return etree.parse(str(path))  # noqa: S320
    except etree.XMLSyntaxError:
        text = path.read_text(encoding="utf-8")
        repaired = _MALFORMED_PREFIXED_START_TAG_RE.sub(r"<\1", text)
        if repaired == text:
            raise
        return etree.parse(BytesIO(repaired.encode("utf-8")))  # noqa: S320

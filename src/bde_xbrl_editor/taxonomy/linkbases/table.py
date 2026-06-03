"""Version-aware Table Linkbase parser dispatch."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import NS_TABLE_2014, NS_TABLE_PWD
from bde_xbrl_editor.taxonomy.linkbases.table_10_parser import parse_table_linkbase_10
from bde_xbrl_editor.taxonomy.linkbases.table_pwd import (
    parse_table_linkbase as parse_table_linkbase_pwd,
)
from bde_xbrl_editor.taxonomy.models import TableDefinitionPWD, TaxonomyParseError
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file


class TableLinkbaseVersion(StrEnum):
    PWD_2013 = "pwd-2013-05-17"
    REC_2014 = "rec-2014"
    UNKNOWN = "unknown"


def detect_table_linkbase_version(linkbase_path: Path) -> TableLinkbaseVersion:
    """Detect which supported table namespace appears in a linkbase."""
    try:
        root = parse_xml_file(linkbase_path).getroot()
    except etree.XMLSyntaxError as exc:
        raise TaxonomyParseError(
            file_path=str(linkbase_path),
            message=str(exc),
            line=exc.lineno,
            column=exc.offset,
        ) from exc

    namespaces: set[str] = set()
    for el in root.iter():
        tag = str(el.tag)
        if tag.startswith("{"):
            namespaces.add(tag[1:].split("}", 1)[0])
    if NS_TABLE_PWD in namespaces:
        return TableLinkbaseVersion.PWD_2013
    if NS_TABLE_2014 in namespaces:
        return TableLinkbaseVersion.REC_2014
    return TableLinkbaseVersion.UNKNOWN


def parse_table_linkbase(
    linkbase_path: Path,
    label_lookup: dict | None = None,
    language_preference: tuple[str, ...] = ("es", "en"),
) -> list[TableDefinitionPWD]:
    """Parse a table linkbase using the processor for its namespace version."""
    version = detect_table_linkbase_version(linkbase_path)
    if version == TableLinkbaseVersion.REC_2014:
        return parse_table_linkbase_10(
            linkbase_path,
            label_lookup=label_lookup,
            language_preference=language_preference,
        )
    return parse_table_linkbase_pwd(
        linkbase_path,
        label_lookup=label_lookup,
        language_preference=language_preference,
    )

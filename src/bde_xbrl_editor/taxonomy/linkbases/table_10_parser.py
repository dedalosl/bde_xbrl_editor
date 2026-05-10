"""Final Table Linkbase 1.0 parser.

The application renderer still consumes the common ``TableDefinitionPWD`` layout
model.  This processor is separate so TL 1.0 validation can evolve independently
from BDE PWD parsing while preserving the existing UI contract.
"""

from __future__ import annotations

from pathlib import Path

from bde_xbrl_editor.taxonomy.linkbases.table_pwd import parse_table_linkbase as _parse_layout
from bde_xbrl_editor.taxonomy.models import TableDefinitionPWD


def parse_table_linkbase_10(
    linkbase_path: Path,
    label_lookup: dict | None = None,
    language_preference: tuple[str, ...] = ("es", "en"),
) -> list[TableDefinitionPWD]:
    """Parse final Table Linkbase 1.0 into the renderer-compatible table model."""
    return _parse_layout(
        linkbase_path,
        label_lookup=label_lookup,
        language_preference=language_preference,
    )

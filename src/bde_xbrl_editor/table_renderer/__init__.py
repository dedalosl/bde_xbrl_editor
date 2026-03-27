"""Table renderer — public API re-exports."""

from bde_xbrl_editor.table_renderer.errors import TableLayoutError, ZIndexOutOfRangeError
from bde_xbrl_editor.table_renderer.fact_formatter import FactFormatter
from bde_xbrl_editor.table_renderer.layout_engine import TableLayoutEngine
from bde_xbrl_editor.table_renderer.models import ComputedTableLayout

__all__ = [
    "TableLayoutEngine",
    "FactFormatter",
    "ComputedTableLayout",
    "TableLayoutError",
    "ZIndexOutOfRangeError",
]

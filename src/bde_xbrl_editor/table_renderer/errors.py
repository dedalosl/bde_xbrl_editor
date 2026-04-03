"""Error hierarchy for the table renderer."""

from __future__ import annotations


class TableRenderError(Exception):
    """Base class for all table renderer errors."""


class TableLayoutError(TableRenderError):
    """Raised when a table definition is structurally invalid."""

    def __init__(self, table_id: str, reason: str) -> None:
        super().__init__(f"Table '{table_id}' layout error: {reason}")
        self.table_id = table_id
        self.reason = reason


class ZIndexOutOfRangeError(TableRenderError):
    """Raised when z_index exceeds the number of available Z-axis members."""

    def __init__(self, table_id: str, requested_z: int, max_z: int) -> None:
        super().__init__(
            f"Table '{table_id}': z_index {requested_z} out of range (max {max_z})"
        )
        self.table_id = table_id
        self.requested_z = requested_z
        self.max_z = max_z

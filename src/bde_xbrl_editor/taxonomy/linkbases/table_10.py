"""Domain objects for final Table Linkbase 1.0 processing."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

TableNodeType = Literal[
    "table",
    "breakdown",
    "ruleNode",
    "aspectNode",
    "conceptRelationshipNode",
    "dimensionRelationshipNode",
    "parameter",
    "filter",
    "other",
]


@dataclass(frozen=True)
class Table10Resource:
    label: str
    node_type: TableNodeType
    element_id: str | None = None
    namespace: str | None = None


@dataclass(frozen=True)
class Table10Arc:
    arc_type: str
    source: str
    target: str
    order: float = 1.0
    name: str | None = None


@dataclass(frozen=True)
class Table10DefinitionModel:
    """Syntax-level Table Linkbase 1.0 model used by validators."""

    source_path: Path
    resources: dict[str, Table10Resource] = field(default_factory=dict)
    arcs: tuple[Table10Arc, ...] = ()

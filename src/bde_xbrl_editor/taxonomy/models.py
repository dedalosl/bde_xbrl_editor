"""Taxonomy domain models — all immutable dataclasses.

All entities are frozen dataclasses constructed during taxonomy loading and
stored in TaxonomyStructure. None are modified after construction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# QName — fundamental identifier
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class QName:
    """Qualified XML name. Identity is (namespace, local_name); prefix is display-only."""

    namespace: str
    local_name: str
    prefix: str | None = field(default=None, compare=False, hash=False)

    def __str__(self) -> str:
        if self.prefix:
            return f"{self.prefix}:{self.local_name}"
        return f"{{{self.namespace}}}{self.local_name}"

    @classmethod
    def from_clark(cls, clark: str, prefix: str | None = None) -> QName:
        """Parse a Clark-notation string ``{namespace}local_name`` into a QName."""
        if clark.startswith("{"):
            end = clark.index("}")
            return cls(namespace=clark[1:end], local_name=clark[end + 1:], prefix=prefix)
        # No namespace (e.g., built-in XSD types without namespace)
        return cls(namespace="", local_name=clark, prefix=prefix)


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------

class TaxonomyLoadError(Exception):
    """Base class for all taxonomy load failures."""


@dataclass
class UnsupportedTaxonomyFormatError(TaxonomyLoadError):
    """Entry point does not appear to be a valid XBRL taxonomy."""

    entry_point: str
    reason: str

    def __str__(self) -> str:
        return (
            f"Unsupported taxonomy format at '{self.entry_point}': {self.reason}. "
            "Ensure the file is a valid XBRL 2.1 entry-point schema (.xsd)."
        )


@dataclass
class TaxonomyDiscoveryError(TaxonomyLoadError):
    """One or more DTS references could not be resolved."""

    entry_point: str
    failing_uris: list[tuple[str, str]]  # (uri, reason) pairs

    def __str__(self) -> str:
        details = "; ".join(f"'{u}': {r}" for u, r in self.failing_uris[:5])
        suffix = f" (and {len(self.failing_uris) - 5} more)" if len(self.failing_uris) > 5 else ""
        return (
            f"DTS discovery failed for '{self.entry_point}'. "
            f"Could not resolve: {details}{suffix}. "
            "Check that all referenced schema and linkbase files are present locally."
        )


@dataclass
class TaxonomyParseError(TaxonomyLoadError):
    """Structural parse error in a schema or linkbase file."""

    file_path: str
    message: str
    line: int | None = None
    column: int | None = None

    def __str__(self) -> str:
        loc = ""
        if self.line is not None:
            loc = f" at line {self.line}"
            if self.column is not None:
                loc += f", column {self.column}"
        return (
            f"Parse error in '{self.file_path}'{loc}: {self.message}. "
            "The file may be malformed or use an unsupported XBRL extension."
        )


# ---------------------------------------------------------------------------
# Concept model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Concept:
    """An XBRL element declaration (concept)."""

    qname: QName
    data_type: QName
    period_type: Literal["instant", "duration"]
    balance: Literal["debit", "credit"] | None = None
    abstract: bool = False
    nillable: bool = True
    substitution_group: QName | None = None
    xml_id: str | None = None  # @id attribute from the XSD element declaration


# ---------------------------------------------------------------------------
# Label model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Label:
    """A single label string for a concept in a specific language and role."""

    text: str
    language: str
    role: str
    source: Literal["standard", "generic"] = "standard"
    priority: int = 0


# ---------------------------------------------------------------------------
# Linkbase models — presentation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PresentationArc:
    """A single arc in a presentation linkbase."""

    parent: QName
    child: QName
    order: float
    extended_link_role: str
    preferred_label: str | None = None


@dataclass
class PresentationNetwork:
    """Presentation arcs for a single extended link role."""

    extended_link_role: str
    arcs: list[PresentationArc] = field(default_factory=list)

    @property
    def roots(self) -> list[QName]:
        """Return concepts that appear as parent but never as child in this ELR."""
        children = {a.child for a in self.arcs}
        parents = {a.parent for a in self.arcs}
        return sorted(parents - children, key=str)

    def children_of(self, qname: QName) -> list[QName]:
        """Return ordered children of a concept within this ELR."""
        children = [(a.order, a.child) for a in self.arcs if a.parent == qname]
        return [c for _, c in sorted(children)]


# ---------------------------------------------------------------------------
# Linkbase models — calculation
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CalculationArc:
    """A single arc in a calculation linkbase."""

    parent: QName
    child: QName
    order: float
    weight: float  # +1.0 (add) or −1.0 (subtract)
    extended_link_role: str


# ---------------------------------------------------------------------------
# Linkbase models — definition / dimensional
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DefinitionArc:
    """A single arc in a definition linkbase."""

    arcrole: str
    source: QName
    target: QName
    order: float
    extended_link_role: str
    closed: bool | None = None
    context_element: Literal["segment", "scenario"] | None = None
    usable: bool | None = None
    target_role: str | None = None  # xbrldt:targetRole — points to ELR containing dim members


@dataclass(frozen=True)
class DomainMember:
    """A member in a dimension's domain hierarchy."""

    qname: QName
    parent: QName | None
    order: float
    usable: bool = True


@dataclass(frozen=True)
class DimensionModel:
    """A single dimension axis within a hypercube."""

    qname: QName
    dimension_type: Literal["explicit", "typed"]
    default_member: QName | None = None
    domain: QName | None = None
    members: tuple[DomainMember, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class HypercubeModel:
    """A dimensional hypercube definition."""

    qname: QName
    arcrole: Literal["all", "notAll"]
    closed: bool
    context_element: Literal["segment", "scenario"]
    primary_items: tuple[QName, ...]
    dimensions: tuple[QName, ...]
    extended_link_role: str


# ---------------------------------------------------------------------------
# PWD Table Linkbase model
# ---------------------------------------------------------------------------

@dataclass
class BreakdownNode:
    """A node in the table's hierarchical breakdown structure."""

    node_type: Literal["rule", "aspect", "conceptRelationship", "dimensionRelationship"]
    label: str | None = None
    rc_code: str | None = None
    fin_code: str | None = None  # http://www.bde.es/xbrl/role/fin-code label for cell-code computation
    is_abstract: bool = False
    merge: bool = False
    span: int | None = None
    children: list[BreakdownNode] = field(default_factory=list)
    aspect_constraints: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TableDefinitionPWD:
    """A complete report table defined in the PWD Table Linkbase."""

    table_id: str
    label: str
    extended_link_role: str
    x_breakdown: BreakdownNode
    y_breakdown: BreakdownNode
    z_breakdowns: tuple[BreakdownNode, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Taxonomy metadata
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TaxonomyMetadata:
    """Descriptive metadata extracted from the entry-point schema."""

    name: str
    version: str
    publisher: str
    entry_point_path: Path
    loaded_at: datetime
    declared_languages: tuple[str, ...]
    period_type: str | None = None  # e.g. "annual", "quarterly" — BDE-specific


# ---------------------------------------------------------------------------
# Formula linkbase domain types (Feature 005 — parsed during taxonomy loading)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DimensionFilter:
    """Filter that restricts a fact variable to facts with a specific dimension value."""

    dimension_qname: QName
    member_qnames: tuple[QName, ...] = field(default_factory=tuple)
    exclude: bool = False


@dataclass(frozen=True)
class XPathFilterDefinition:
    """An XPath-expression-based filter (gf:general, pf:period test=, etc.)."""

    xpath_expr: str
    namespaces: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class BooleanFilterDefinition:
    """Recursive boolean combination of filters (bf:andFilter / bf:orFilter).

    Children may be DimensionFilter, XPathFilterDefinition, or nested
    BooleanFilterDefinition instances.  When *complement* is True the result
    of the whole subtree is negated (i.e. the arc had complement="true").
    """

    filter_type: Literal["and", "or"]
    children: tuple[Any, ...]  # DimensionFilter | XPathFilterDefinition | BooleanFilterDefinition
    complement: bool = False


@dataclass(frozen=True)
class FactVariableDefinition:
    """A bound fact variable in a formula assertion."""

    variable_name: str
    concept_filter: QName | None = None
    period_filter: Literal["instant", "duration"] | None = None
    dimension_filters: tuple[DimensionFilter, ...] = field(default_factory=tuple)
    unit_filter: QName | None = None
    fallback_value: str | None = None
    xpath_filters: tuple[XPathFilterDefinition, ...] = field(default_factory=tuple)
    boolean_filters: tuple[BooleanFilterDefinition, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FormulaAssertion:
    """Base for all formula assertion types."""

    assertion_id: str
    label: str | None
    severity: Any  # ValidationSeverity — late-bound to avoid circular import
    abstract: bool
    variables: tuple[FactVariableDefinition, ...]
    precondition_xpath: str | None
    namespaces: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ValueAssertionDefinition(FormulaAssertion):
    """formula:valueAssertion — @test XPath must be true for each binding."""
    test_xpath: str = ""


@dataclass(frozen=True)
class ExistenceAssertionDefinition(FormulaAssertion):
    """formula:existenceAssertion — at least one binding must have a non-empty fact set."""
    test_xpath: str | None = None


@dataclass(frozen=True)
class ConsistencyAssertionDefinition(FormulaAssertion):
    """formula:consistencyAssertion — formula result must match fact value within radius."""
    formula_xpath: str = ""
    absolute_radius: Decimal | None = None
    relative_radius: Decimal | None = None


@dataclass(frozen=True)
class FormulaAssertionSet:
    """Complete set of formula assertions parsed from a formula linkbase."""

    assertions: tuple[FormulaAssertion, ...] = field(default_factory=tuple)
    abstract_count: int = 0


# ---------------------------------------------------------------------------
# TaxonomyStructure — the complete immutable taxonomy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TaxonomyStructure:
    """Complete, immutable in-memory representation of a loaded XBRL taxonomy."""

    metadata: TaxonomyMetadata
    concepts: Mapping[QName, Concept]
    labels: Any  # LabelResolver — imported at runtime to avoid circular import
    presentation: Mapping[str, PresentationNetwork]
    calculation: Mapping[str, Sequence[CalculationArc]]
    definition: Mapping[str, Sequence[DefinitionArc]]
    hypercubes: Sequence[HypercubeModel]
    dimensions: Mapping[QName, DimensionModel]
    tables: Sequence[TableDefinitionPWD]
    formula_linkbase_path: Path | None = None
    formula_assertion_set: FormulaAssertionSet = field(default_factory=FormulaAssertionSet)
    # Files discovered during DTS traversal (populated by TaxonomyLoader)
    schema_files: tuple[Path, ...] = field(default_factory=tuple)
    linkbase_files: tuple[Path, ...] = field(default_factory=tuple)

    def get_table(self, table_id: str) -> TableDefinitionPWD | None:
        """Return the table with the given ID, or None if not found."""
        for t in self.tables:
            if t.table_id == table_id:
                return t
        return None


# ---------------------------------------------------------------------------
# Cache entry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TaxonomyCacheEntry:
    """A cache slot holding a parsed TaxonomyStructure."""

    entry_point_key: str
    structure: TaxonomyStructure
    cached_at: datetime
    source_path: Path

"""Instance domain model — mutable dataclasses for an open XBRL instance document."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from bde_xbrl_editor.taxonomy.models import QName

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

ContextId = str  # ctx_<sha256[:8]>
UnitId = str  # e.g. "EUR", "pure"


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class InstanceCreationError(Exception):
    """Base class for all instance creation failures."""


class InvalidReportingPeriodError(InstanceCreationError):
    """Period type incompatible with taxonomy declaration, or end_date < start_date."""

    def __init__(
        self,
        period_type_required: str,
        period_type_provided: str,
        reason: str = "",
    ) -> None:
        self.period_type_required = period_type_required
        self.period_type_provided = period_type_provided
        self.reason = reason
        super().__init__(
            f"Invalid reporting period: taxonomy requires '{period_type_required}', "
            f"got '{period_type_provided}'"
            + (f" — {reason}" if reason else "")
        )


class InvalidEntityIdentifierError(InstanceCreationError):
    """Entity identifier is empty or scheme is missing/invalid."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Invalid entity identifier: {reason}")


class MissingDimensionValueError(InstanceCreationError):
    """A mandatory Z-axis dimension has no value assigned."""

    def __init__(self, table_id: str, dimension_qname: QName) -> None:
        self.table_id = table_id
        self.dimension_qname = dimension_qname
        super().__init__(
            f"Missing mandatory dimension value for table '{table_id}': "
            f"dimension '{dimension_qname}' has no assigned member"
        )


class InvalidDimensionMemberError(InstanceCreationError):
    """Assigned dimension member is not in the allowed member list."""

    def __init__(
        self,
        table_id: str,
        dimension_qname: QName,
        provided_member: QName,
        allowed_members: list[QName],
    ) -> None:
        self.table_id = table_id
        self.dimension_qname = dimension_qname
        self.provided_member = provided_member
        self.allowed_members = allowed_members
        super().__init__(
            f"Invalid dimension member for table '{table_id}': "
            f"dimension '{dimension_qname}' — member '{provided_member}' not in allowed list"
        )


class InstanceSaveError(Exception):
    """File write failed (permission error, disk full, etc.)."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to save instance to '{path}': {reason}")


# Feature 004 error types

class InstanceParseError(Exception):
    """XML not well-formed, missing xbrli:xbrl root, or missing link:schemaRef."""

    def __init__(self, path: str, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Failed to parse instance '{path}': {reason}")


class TaxonomyResolutionError(InstanceParseError):
    """schemaRef could not be resolved to a local taxonomy path."""

    def __init__(self, schema_ref_href: str, reason: str = "") -> None:
        self.schema_ref_href = schema_ref_href
        super().__init__(
            schema_ref_href,
            f"Could not resolve taxonomy schemaRef '{schema_ref_href}'"
            + (f": {reason}" if reason else ""),
        )


class DuplicateFactError(Exception):
    """add_fact() called for a concept+context that already has a fact."""

    def __init__(self, concept: QName, context_ref: str) -> None:
        self.concept = concept
        self.context_ref = context_ref
        super().__init__(
            f"Duplicate fact: concept '{concept}' in context '{context_ref}' already exists"
        )


class InvalidFactValueError(Exception):
    """update_fact() called with a value that fails XBRL type validation."""

    def __init__(self, concept: QName, expected_type: str, provided_value: str) -> None:
        self.concept = concept
        self.expected_type = expected_type
        self.provided_value = provided_value
        super().__init__(
            f"Invalid value '{provided_value}' for concept '{concept}' "
            f"(expected type: {expected_type})"
        )


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass
class ReportingEntity:
    """Identifies the legal entity submitting this report."""

    identifier: str
    scheme: str

    def __post_init__(self) -> None:
        if not self.identifier or not self.identifier.strip():
            raise InvalidEntityIdentifierError("identifier must be non-empty")
        if not self.scheme or not self.scheme.strip():
            raise InvalidEntityIdentifierError("scheme must be a non-empty URI")


@dataclass
class ReportingPeriod:
    """The time interval this instance covers."""

    period_type: Literal["instant", "duration"]
    instant_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None

    def __post_init__(self) -> None:
        if self.period_type == "instant":
            if self.instant_date is None:
                raise InvalidReportingPeriodError(
                    "instant", "instant", "instant_date must be set for instant periods"
                )
        elif self.period_type == "duration":
            if self.start_date is None or self.end_date is None:
                raise InvalidReportingPeriodError(
                    "duration",
                    "duration",
                    "start_date and end_date must both be set for duration periods",
                )
            if self.end_date < self.start_date:
                raise InvalidReportingPeriodError(
                    "duration",
                    "duration",
                    f"end_date ({self.end_date}) must be >= start_date ({self.start_date})",
                )
        else:
            raise InvalidReportingPeriodError(
                "instant or duration",
                str(self.period_type),
                f"Unknown period_type: '{self.period_type}'",
            )


@dataclass
class DimensionalConfiguration:
    """Z-axis dimensional assignments for a single report table."""

    table_id: str
    dimension_assignments: dict[QName, QName] = field(default_factory=dict)


@dataclass
class XbrlContext:
    """One generated XBRL context element."""

    context_id: ContextId
    entity: ReportingEntity
    period: ReportingPeriod
    dimensions: dict[QName, QName] = field(default_factory=dict)
    typed_dimensions: dict[QName, str] = field(default_factory=dict)
    typed_dimension_elements: dict[QName, QName] = field(default_factory=dict)
    context_element: Literal["scenario", "segment"] = "scenario"
    # Per-dimension container: "segment" or "scenario" for each dimension QName.
    # Used to validate xbrldt:contextElement constraints on hypercubes.
    dim_containers: dict[QName, Literal["segment", "scenario"]] = field(
        default_factory=dict
    )
    # Immutable S-equal fingerprint (XBRL 2.1); set at parse time or by context_builder.
    # When None, validation uses :func:`bde_xbrl_editor.instance.s_equal.effective_s_equal_key`.
    s_equal_key: tuple | None = None
    # Serialized XML fragments for schema-based context-content validation.
    # Stored as UTF-8 bytes without tail text.
    scenario_xml: bytes | None = None
    segment_xml: bytes | None = None


@dataclass
class XbrlUnit:
    """A XBRL unit element (monetary or dimensionless)."""

    unit_id: UnitId
    measure_uri: str
    # QName of the single direct xbrli:measure when unit_form is "simple"; set at
    # parse time from element namespace scope. Optional for legacy in-memory units.
    measure_qname: QName | None = None
    # "simple" = only direct measures (one or more); "divide" = xbrli:divide present.
    unit_form: Literal["simple", "divide"] = "simple"
    # Number of direct child xbrli:measure elements when unit_form is "simple".
    simple_measure_count: int = 0
    # Resolved direct measures, preserving namespaces even when more than one exists.
    simple_measure_qnames: tuple[QName, ...] = field(default_factory=tuple)
    numerator_measure_qnames: tuple[QName, ...] = field(default_factory=tuple)
    denominator_measure_qnames: tuple[QName, ...] = field(default_factory=tuple)


@dataclass
class FilingIndicator:
    """Eurofiling filing indicator — declares a table as filed/not-filed."""

    template_id: str
    filed: bool = True
    context_ref: ContextId = ""


@dataclass
class BdeEstadoReportado:
    """One estado entry inside EstadosReportados (BDE IE_2008_02 preamble).

    Each CodigoEstado element carries a 4-digit numeric estado code and an
    optional ``blanco="true"`` attribute that signals a clearing submission.
    """

    codigo: str  # 4-digit numeric estado code (e.g. "3201")
    blanco: bool = False  # True when blanco="true" — clearing the estado
    context_ref: ContextId = ""


@dataclass
class BdePreambulo:
    """BDE-specific preamble data from the es-be-cm-pblo namespace.

    In IE_2008_02 instances these elements appear as direct children of
    ``<xbrli:xbrl>`` (no wrapper).  The parser extracts them into this
    structure so the rest of the application can read them without having
    to walk the XML tree.

    Attributes:
        entidad_presentadora: 4-digit BDE entity code (no "ES" prefix).
        tipo_envio: Submission type — "Ordinario", "Complementario", or
            "Sustitutivo".
        estados_reportados: Ordered list of reported/cleared estados.
        context_ref: The contextRef shared by all preamble elements
            (typically the dimensionless "cBasico" context).
    """

    entidad_presentadora: str = ""
    tipo_envio: str = ""
    estados_reportados: list[BdeEstadoReportado] = field(default_factory=list)
    context_ref: ContextId = ""


@dataclass
class Fact:
    """A single XBRL fact (created empty in Feature 002; populated in Feature 004)."""

    concept: QName
    context_ref: ContextId
    unit_ref: UnitId | None
    value: str
    decimals: str | None = None
    precision: str | None = None
    is_nil: bool = False


@dataclass
class OrphanedFact:
    """A fact whose concept QName is not declared in the loaded taxonomy."""

    concept_qname_str: str  # Clark notation {ns}local of the unknown concept
    context_ref: str
    unit_ref: str | None
    value: str
    decimals: str | None
    raw_element_xml: bytes  # serialised XML element for lossless round-trip


@dataclass
class EditOperation:
    """Audit trail entry for one edit operation (scaffolded in v1)."""

    operation_type: Literal["add", "update", "remove"]
    fact_index: int | None
    previous_value: str | None
    new_value: str | None
    concept: QName
    context_ref: ContextId
    timestamp: datetime = field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Root instance object
# ---------------------------------------------------------------------------


@dataclass
class XbrlInstance:
    """Root mutable object representing one open XBRL instance document."""

    taxonomy_entry_point: Path
    schema_ref_href: str
    entity: ReportingEntity
    period: ReportingPeriod
    filing_indicators: list[FilingIndicator] = field(default_factory=list)
    included_table_ids: list[str] = field(default_factory=list)
    dimensional_configs: dict[str, DimensionalConfiguration] = field(default_factory=dict)
    contexts: dict[ContextId, XbrlContext] = field(default_factory=dict)
    units: dict[UnitId, XbrlUnit] = field(default_factory=dict)
    facts: list[Fact] = field(default_factory=list)
    orphaned_facts: list[OrphanedFact] = field(default_factory=list)
    edit_history: list[EditOperation] = field(default_factory=list)
    # BDE IE_2008_02 preamble (EntidadPresentadora, TipoEnvio, EstadosReportados).
    # None when the instance was not created from a BDE IE_2008_02 source.
    bde_preambulo: BdePreambulo | None = None
    source_path: Path | None = None
    _dirty: bool = field(default=True, repr=False)

    # ------------------------------------------------------------------
    # Unsaved-change tracking
    # ------------------------------------------------------------------

    @property
    def has_unsaved_changes(self) -> bool:
        """True if there are unsaved changes since the last save."""
        return self._dirty

    # ------------------------------------------------------------------
    # Mutation methods (called by Feature 004 — Instance Editing)
    # ------------------------------------------------------------------

    def add_fact(self, fact: Fact) -> None:
        """Append a fact and mark the instance as dirty."""
        self.facts.append(fact)
        self._dirty = True

    def update_fact(self, index: int, new_value: str) -> None:
        """Update the value of an existing fact by index."""
        self.facts[index].value = new_value
        self._dirty = True

    def remove_fact(self, index: int) -> None:
        """Remove a fact by index."""
        del self.facts[index]
        self._dirty = True

    def mark_saved(self, path: Path) -> None:
        """Called by InstanceSerializer.save() to confirm a successful write."""
        self.source_path = path
        self._dirty = False

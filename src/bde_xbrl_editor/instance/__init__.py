"""XBRL Instance Creation — public API.

All other modules must import from this package, not from sub-modules directly.
"""

from __future__ import annotations

from bde_xbrl_editor.instance.context_builder import (
    build_dimensional_context,
    build_filing_indicator_context,
    deduplicate_contexts,
    generate_context_id,
)
from bde_xbrl_editor.instance.editor import InstanceEditor
from bde_xbrl_editor.instance.factory import InstanceFactory
from bde_xbrl_editor.instance.models import (
    ContextId,
    DimensionalConfiguration,
    DuplicateFactError,
    EditOperation,
    Fact,
    FilingIndicator,
    InstanceCreationError,
    InstanceParseError,
    InstanceSaveError,
    InvalidDimensionMemberError,
    InvalidEntityIdentifierError,
    InvalidFactValueError,
    InvalidReportingPeriodError,
    MissingDimensionValueError,
    OrphanedFact,
    ReportingEntity,
    ReportingPeriod,
    TaxonomyResolutionError,
    UnitId,
    XbrlContext,
    XbrlInstance,
    XbrlUnit,
)
from bde_xbrl_editor.instance.parser import InstanceParser
from bde_xbrl_editor.instance.serializer import InstanceSerializer
from bde_xbrl_editor.instance.validator import XbrlTypeValidator

__all__ = [
    # Primary entry points
    "InstanceFactory",
    "InstanceSerializer",
    # Domain model
    "XbrlInstance",
    "ReportingEntity",
    "ReportingPeriod",
    "FilingIndicator",
    "DimensionalConfiguration",
    "XbrlContext",
    "XbrlUnit",
    "Fact",
    "ContextId",
    "UnitId",
    # Feature 004 additions
    "InstanceEditor",
    "InstanceParser",
    "XbrlTypeValidator",
    "OrphanedFact",
    "EditOperation",
    # Errors
    "InstanceCreationError",
    "InstanceSaveError",
    "InstanceParseError",
    "TaxonomyResolutionError",
    "DuplicateFactError",
    "InvalidFactValueError",
    "InvalidReportingPeriodError",
    "InvalidEntityIdentifierError",
    "MissingDimensionValueError",
    "InvalidDimensionMemberError",
    # Context builder helpers (lower-level, but exposed for testing)
    "generate_context_id",
    "build_filing_indicator_context",
    "build_dimensional_context",
    "deduplicate_contexts",
]

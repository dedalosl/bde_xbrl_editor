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
from bde_xbrl_editor.instance.factory import InstanceFactory
from bde_xbrl_editor.instance.models import (
    ContextId,
    DimensionalConfiguration,
    Fact,
    FilingIndicator,
    InstanceCreationError,
    InstanceSaveError,
    InvalidDimensionMemberError,
    InvalidEntityIdentifierError,
    InvalidReportingPeriodError,
    MissingDimensionValueError,
    ReportingEntity,
    ReportingPeriod,
    UnitId,
    XbrlContext,
    XbrlInstance,
    XbrlUnit,
)
from bde_xbrl_editor.instance.serializer import InstanceSerializer

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
    # Errors
    "InstanceCreationError",
    "InstanceSaveError",
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

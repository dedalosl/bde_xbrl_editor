"""Taxonomy loading and caching — Feature 001 public API.

All downstream features must import from this module only; never from
bde_xbrl_editor.taxonomy.* sub-modules directly.
"""

from bde_xbrl_editor.taxonomy.cache import TaxonomyCache
from bde_xbrl_editor.taxonomy.constants import (
    DOCUMENTATION_ROLE,
    LABEL_ROLE,
    NEGATED_LABEL_ROLE,
    PERIOD_END_ROLE,
    PERIOD_START_ROLE,
    RC_CODE_ROLE,
    TERSE_LABEL_ROLE,
    TOTAL_LABEL_ROLE,
    VERBOSE_LABEL_ROLE,
)
from bde_xbrl_editor.taxonomy.label_resolver import LabelResolver
from bde_xbrl_editor.taxonomy.loader import TaxonomyLoader
from bde_xbrl_editor.taxonomy.models import (
    BreakdownNode,
    CalculationArc,
    Concept,
    DefinitionArc,
    DimensionModel,
    DomainMember,
    HypercubeModel,
    Label,
    PresentationArc,
    PresentationNetwork,
    QName,
    TableDefinitionPWD,
    TaxonomyCacheEntry,
    TaxonomyDiscoveryError,
    TaxonomyLoadError,
    TaxonomyMetadata,
    TaxonomyParseError,
    TaxonomyStructure,
    UnsupportedTaxonomyFormatError,
)
from bde_xbrl_editor.taxonomy.settings import LoaderSettings

__all__ = [
    # Core services
    "TaxonomyLoader",
    "TaxonomyCache",
    "LabelResolver",
    "LoaderSettings",
    # Taxonomy structure
    "TaxonomyStructure",
    "TaxonomyMetadata",
    "TaxonomyCacheEntry",
    # Domain models
    "QName",
    "Concept",
    "Label",
    "PresentationArc",
    "PresentationNetwork",
    "CalculationArc",
    "DefinitionArc",
    "HypercubeModel",
    "DimensionModel",
    "DomainMember",
    "TableDefinitionPWD",
    "BreakdownNode",
    # Error types
    "TaxonomyLoadError",
    "UnsupportedTaxonomyFormatError",
    "TaxonomyDiscoveryError",
    "TaxonomyParseError",
    # Label role constants
    "LABEL_ROLE",
    "TERSE_LABEL_ROLE",
    "VERBOSE_LABEL_ROLE",
    "DOCUMENTATION_ROLE",
    "PERIOD_START_ROLE",
    "PERIOD_END_ROLE",
    "TOTAL_LABEL_ROLE",
    "NEGATED_LABEL_ROLE",
    "RC_CODE_ROLE",
]

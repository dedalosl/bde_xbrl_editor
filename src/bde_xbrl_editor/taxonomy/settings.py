"""LoaderSettings — configuration for taxonomy loading behaviour."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class LoaderSettings:
    """Configuration passed to TaxonomyLoader.

    Attributes:
        allow_network: If False (default), any attempt to resolve a URI that
            maps to an http/https URL raises TaxonomyDiscoveryError.  (FR-009)
        language_preference: Ordered list of BCP-47 language codes tried when
            resolving labels.  Defaults to Spanish first, English fallback.
        local_catalog: Optional mapping of remote URI prefixes to local Path
            roots.  Use to redirect XBRL.org or EBA schema references to a
            local mirror without enabling full network access.
    """

    allow_network: bool = False
    language_preference: list[str] = field(default_factory=lambda: ["es", "en"])
    local_catalog: dict[str, Path] | None = None

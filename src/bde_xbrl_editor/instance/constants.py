"""Namespace and prefix constants for XBRL instance documents."""

from __future__ import annotations

XBRLI_NS = "http://www.xbrl.org/2003/instance"
LINK_NS = "http://www.xbrl.org/2003/linkbase"
XLINK_NS = "http://www.w3.org/1999/xlink"
XBRLDI_NS = "http://xbrl.org/2006/xbrldi"
ISO4217_NS = "http://www.xbrl.org/2003/iso4217"
FILING_IND_NS = "http://www.eurofiling.info/xbrl/ext/filing-indicators"
FILING_IND_PFX = "ef-find"

# The XML element where explicit dimension members are encoded in XBRL contexts.
# BDE / Eurofiling regulatory reporting uses 'scenario' (EBA convention).
# Can be overridden per-hypercube by reading HypercubeModel.context_element.
XBRLDI_CONTEXT_ELEMENT = "scenario"

"""Namespace and prefix constants for XBRL instance documents."""

from __future__ import annotations

XBRLI_NS = "http://www.xbrl.org/2003/instance"
LINK_NS = "http://www.xbrl.org/2003/linkbase"
XLINK_NS = "http://www.w3.org/1999/xlink"
XBRLDI_NS = "http://xbrl.org/2006/xbrldi"
ISO4217_NS = "http://www.xbrl.org/2003/iso4217"
FILING_IND_NS = "http://www.eurofiling.info/xbrl/ext/filing-indicators"
FILING_IND_PFX = "ef-find"

# BDE IE_2008_02 preamble namespace (EntidadPresentadora, TipoEnvio, EstadosReportados)
BDE_PBLO_NS = "http://www.bde.es/es/fr/esrs/comun/2008-06-01/preambulo"
BDE_PBLO_PFX = "es-be-cm-pblo"

# BDE IE_2008_02 dimension namespace (Agrupacion axis and members)
BDE_DIM_NS = "http://www.bde.es/es/fr/esrs/comun/2008-06-01/dimensiones"
BDE_DIM_PFX = "es-be-cm-dim"

# The XML element where explicit dimension members are encoded in XBRL contexts.
# BDE / Eurofiling regulatory reporting uses 'scenario' (EBA convention).
# Can be overridden per-hypercube by reading HypercubeModel.context_element.
XBRLDI_CONTEXT_ELEMENT = "scenario"

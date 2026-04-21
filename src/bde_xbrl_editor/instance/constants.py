"""Namespace and prefix constants for XBRL instance documents."""

from __future__ import annotations

XBRLI_NS = "http://www.xbrl.org/2003/instance"
LINK_NS = "http://www.xbrl.org/2003/linkbase"
XLINK_NS = "http://www.w3.org/1999/xlink"
XBRLDI_NS = "http://xbrl.org/2006/xbrldi"
ISO4217_NS = "http://www.xbrl.org/2003/iso4217"
FILING_IND_NS = "http://www.eurofiling.info/xbrl/ext/filing-indicators"
FILING_IND_PFX = "ef-find"

# BDE-specific namespaces (IE_2008_02 / Banco de España)
# Preamble namespace: EntidadPresentadora, TipoEnvio, EstadosReportados/CodigoEstado
BDE_PBLO_NS = "http://www.bde.es/es/fr/esrs/comun/2008-06-01/preambulo"
BDE_PBLO_PFX = "es-be-cm-pblo"
# Dimension namespace: Agrupacion axis + members (AgrupacionIndividual, etc.)
BDE_DIM_NS = "http://www.bde.es/es/fr/esrs/comun/2008-06-01/dimensiones"
BDE_DIM_PFX = "es-be-cm-dim"
BDE_SCHEMA_REF_PREFIXES = (
    "http://www.bde.es/",
    "https://www.bde.es/",
)

# The XML element where explicit dimension members are encoded in XBRL contexts.
# BDE / Eurofiling regulatory reporting uses 'scenario' (EBA convention).
# Can be overridden per-hypercube by reading HypercubeModel.context_element.
XBRLDI_CONTEXT_ELEMENT = "scenario"

# BDE Agrupacion dimension QName (Clark notation) — the axis always placed in
# xbrli:segment to declare the consolidation group type for each context.
BDE_AGRUPACION_DIM = f"{{{BDE_DIM_NS}}}Agrupacion"


def is_bde_schema_ref(schema_ref_href: str) -> bool:
    """Return True when the schemaRef points at a Banco de Espana taxonomy URL."""
    href = (schema_ref_href or "").strip()
    return href.startswith(BDE_SCHEMA_REF_PREFIXES)

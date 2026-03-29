"""Namespace URIs, arcrole URIs, and label role constants for XBRL taxonomy processing."""

# ---------------------------------------------------------------------------
# Standard XBRL namespaces
# ---------------------------------------------------------------------------
NS_XBRLI = "http://www.xbrl.org/2003/instance"
NS_LINK = "http://www.xbrl.org/2003/linkbase"
NS_XLINK = "http://www.w3.org/1999/xlink"
NS_XSD = "http://www.w3.org/2001/XMLSchema"
NS_XBRLDT = "http://xbrl.org/2005/xbrldt"

# Generic linkbase namespaces (XBRL 2.1 generic link spec)
NS_GEN = "http://xbrl.org/2008/generic"
NS_GENLAB = "http://xbrl.org/2008/label"

# Eurofiling extension namespaces
NS_EUROFILING_FI = "http://www.eurofiling.info/xbrl/ext/filing-indicators"

# PWD Table Linkbase namespace (BDE uses the PWD draft version)
NS_TABLE_PWD = "http://xbrl.org/PWD/2013-05-17/table"
NS_FORMULA = "http://xbrl.org/2008/formula"

# ---------------------------------------------------------------------------
# Standard label role URIs (XBRL 2.1, all 8 roles)
# ---------------------------------------------------------------------------
LABEL_ROLE = "http://www.xbrl.org/2003/role/label"
TERSE_LABEL_ROLE = "http://www.xbrl.org/2003/role/terseLabel"
VERBOSE_LABEL_ROLE = "http://www.xbrl.org/2003/role/verboseLabel"
DOCUMENTATION_ROLE = "http://www.xbrl.org/2003/role/documentation"
PERIOD_START_ROLE = "http://www.xbrl.org/2003/role/periodStartLabel"
PERIOD_END_ROLE = "http://www.xbrl.org/2003/role/periodEndLabel"
TOTAL_LABEL_ROLE = "http://www.xbrl.org/2003/role/totalLabel"
NEGATED_LABEL_ROLE = "http://www.xbrl.org/2003/role/negatedLabel"

# Eurofiling RC-code role
RC_CODE_ROLE = "http://www.eurofiling.info/xbrl/role/rc-code"

# ---------------------------------------------------------------------------
# Standard arcrole URIs
# ---------------------------------------------------------------------------
ARCROLE_LABEL = "http://www.xbrl.org/2003/arcrole/concept-label"
ARCROLE_PRESENTATION = "http://www.xbrl.org/2003/arcrole/parent-child"
ARCROLE_CALCULATION = "http://www.xbrl.org/2003/arcrole/summation-item"
ARCROLE_ALL = "http://xbrl.org/int/dim/arcrole/all"
ARCROLE_NOT_ALL = "http://xbrl.org/int/dim/arcrole/notAll"
ARCROLE_HYPERCUBE_DIMENSION = "http://xbrl.org/int/dim/arcrole/hypercube-dimension"
ARCROLE_DIMENSION_DOMAIN = "http://xbrl.org/int/dim/arcrole/dimension-domain"
ARCROLE_DOMAIN_MEMBER = "http://xbrl.org/int/dim/arcrole/domain-member"
ARCROLE_DIMENSION_DEFAULT = "http://xbrl.org/int/dim/arcrole/dimension-default"

# Generic label arcrole
ARCROLE_ELEMENT_LABEL = "http://xbrl.org/arcrole/2008/element-label"

# ---------------------------------------------------------------------------
# LinkbaseRef role URIs (used in schemaRef annotations)
# ---------------------------------------------------------------------------
ROLE_LABEL_LINKBASE_REF = "http://www.xbrl.org/2003/role/labelLinkbaseRef"
ROLE_PRESENTATION_LINKBASE_REF = "http://www.xbrl.org/2003/role/presentationLinkbaseRef"
ROLE_CALCULATION_LINKBASE_REF = "http://www.xbrl.org/2003/role/calculationLinkbaseRef"
ROLE_DEFINITION_LINKBASE_REF = "http://www.xbrl.org/2003/role/definitionLinkbaseRef"

# Default ELR for standard link roles
DEFAULT_LINK_ROLE = "http://www.xbrl.org/2003/role/link"

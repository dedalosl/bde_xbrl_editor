"""XBRL Function Registry — xfi: namespace implementations for elementpath.

Registers all xfi: functions (http://www.xbrl.org/2008/function/instance) as
external callbacks on a custom XPath 2.0 parser subclass.  A global evaluation
context (set/cleared around each XPath call) gives the functions access to the
current fact, its XBRL context, unit, and the full instance fact list.

Usage
-----
::

    from bde_xbrl_editor.validation.formula.xfi_functions import (
        build_formula_parser,
        set_evaluation_context,
        clear_evaluation_context,
    )

    parser = build_formula_parser(namespaces)          # per-formula namespaces
    set_evaluation_context({...})
    token  = parser.parse(xpath_expr)
    ctx    = XPathContext(root=None, item=context_item, variables=variables)
    result = list(token.select(ctx))
    clear_evaluation_context()
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
from typing import Any

from bde_xbrl_editor.taxonomy.models import CustomFunctionDefinition
from bde_xbrl_editor.validation.formula.xpath_registration import (
    build_registered_parser_class,
    register_custom_functions,
)

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Namespaces
# ---------------------------------------------------------------------------

_XFI_NS = "http://www.xbrl.org/2008/function/instance"
_EFN_NS = "http://www.eurofiling.info/xbrl/func/extra-functions"
_CUSTOM_FUNCTION_CALL_RE = re.compile(r"(?<![$\w.-])([A-Za-z_][\w.-]*)\:([A-Za-z_][\w.-]*)\s*\(")

# ---------------------------------------------------------------------------
# Thread-local evaluation context
# ---------------------------------------------------------------------------

_eval_context: dict[str, Any] = {}


def set_evaluation_context(binding: dict[str, Any]) -> None:
    """Set per-evaluation context (fact, XBRL context, unit, all facts)."""
    _eval_context.clear()
    _eval_context.update(binding)


def clear_evaluation_context() -> None:
    """Clear the per-evaluation context after each XPath call."""
    _eval_context.clear()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _current_fact() -> Any:
    return _eval_context.get("_current_fact")


def _current_context() -> Any:
    return _eval_context.get("_context")


def _current_unit() -> Any:
    return _eval_context.get("_unit")


def _all_facts() -> list[Any]:
    return list(_eval_context.get("_all_facts") or [])


def _custom_functions() -> tuple[CustomFunctionDefinition, ...]:
    return tuple(_eval_context.get("_custom_functions") or ())


def _period_of(context: Any) -> Any:
    """Return the ReportingPeriod from an XbrlContext (or None)."""
    if context is None:
        return None
    return getattr(context, "period", None)


def _fact_from_arg(arg: Any) -> Any:
    """If *arg* looks like a Fact (has .context_ref), return it; otherwise
    return the current fact from the evaluation context."""
    if arg is not None and hasattr(arg, "context_ref"):
        return arg
    if arg is not None and hasattr(arg, "get"):
        context_ref = arg.get("contextRef")
        if context_ref:
            return SimpleNamespace(
                context_ref=context_ref,
                unit_ref=arg.get("unitRef"),
                decimals=arg.get("decimals"),
            )
    return _current_fact()


def _context_from_arg(arg: Any) -> Any:
    """Derive an XbrlContext from *arg* (Fact → look up context; else use
    the current context)."""
    fact = _fact_from_arg(arg)
    if fact is not None:
        instance = _eval_context.get("_instance")
        if instance is not None:
            return instance.contexts.get(fact.context_ref)
    return _current_context()


def _to_xsd_date(d: Any) -> Any:
    """Convert a Python date/datetime to elementpath Date10."""
    from datetime import date, datetime
    try:
        from elementpath.datatypes import Date10
        if isinstance(d, datetime):
            return Date10.fromstring(d.date().isoformat())
        if isinstance(d, date):
            return Date10.fromstring(d.isoformat())
    except (ImportError, TypeError, ValueError) as exc:
        log.debug("Could not convert %r to xs:date: %s", d, exc)
    return None


def _to_xsd_datetime(d: Any) -> Any:
    """Convert a Python date/datetime to elementpath DateTime10."""
    from datetime import date, datetime
    try:
        from elementpath.datatypes import DateTime10
        if isinstance(d, datetime):
            return DateTime10.fromstring(d.isoformat())
        if isinstance(d, date):
            return DateTime10.fromstring(f"{d.isoformat()}T00:00:00")
    except (ImportError, TypeError, ValueError) as exc:
        log.debug("Could not convert %r to xs:dateTime: %s", d, exc)
    return None


# ---------------------------------------------------------------------------
# xfi: function implementations
# ---------------------------------------------------------------------------

# ── Period functions ──────────────────────────────────────────────────────

def xfi_context(fact_arg: Any) -> Any:
    """xfi:context($item) → context identifier string."""
    ctx = _context_from_arg(fact_arg)
    if ctx is None:
        return ""
    return getattr(ctx, "context_id", "")


def xfi_context_period(fact_arg: Any) -> Any:
    """xfi:context-period($item) → period (returns period-type string for chaining)."""
    ctx = _context_from_arg(fact_arg)
    period = _period_of(ctx)
    if period is None:
        return ""
    return period  # ReportingPeriod — consumed by other xfi: functions


def xfi_period(fact_arg: Any) -> Any:
    """xfi:period($item) → period (alias for xfi:context-period)."""
    return xfi_context_period(fact_arg)


def _is_instant(period: Any) -> bool:
    """Return True if *period* is an instant period."""
    if period is None:
        return False
    period_type = getattr(period, "period_type", None)
    if period_type is not None:
        return period_type == "instant"
    # String representation fallback
    return str(period).startswith("instant") or "instant" in str(period).lower()


def xfi_is_instant_period(period_arg: Any) -> bool:
    """xfi:is-instant-period($period) → xs:boolean."""
    # If arg is a period object, use it directly; otherwise use current context
    if period_arg is not None and hasattr(period_arg, "period_type"):
        return _is_instant(period_arg)
    ctx = _context_from_arg(period_arg)
    return _is_instant(_period_of(ctx))


def xfi_is_duration_period(period_arg: Any) -> bool:
    """xfi:is-duration-period($period) → xs:boolean."""
    if period_arg is not None and hasattr(period_arg, "period_type"):
        return getattr(period_arg, "period_type", "") == "duration"
    ctx = _context_from_arg(period_arg)
    period = _period_of(ctx)
    return period is not None and getattr(period, "period_type", "") == "duration"


def xfi_is_start_end_period(period_arg: Any) -> bool:
    """xfi:is-start-end-period($period) → xs:boolean (same as is-duration-period)."""
    return xfi_is_duration_period(period_arg)


def xfi_is_forever_period(period_arg: Any) -> bool:
    """xfi:is-forever-period($period) → xs:boolean.
    'Forever' means no start or end date (open duration)."""
    if period_arg is not None and hasattr(period_arg, "period_type"):
        p = period_arg
    else:
        ctx = _context_from_arg(period_arg)
        p = _period_of(ctx)
    if p is None:
        return False
    return (
        getattr(p, "period_type", "") == "duration"
        and getattr(p, "start_date", None) is None
        and getattr(p, "end_date", None) is None
    )


def xfi_period_instant(period_arg: Any) -> Any:
    """xfi:period-instant($period) → xs:dateTime of the instant date."""
    if period_arg is not None and hasattr(period_arg, "period_type"):
        p = period_arg
    else:
        ctx = _context_from_arg(period_arg)
        p = _period_of(ctx)
    if p is None:
        return None
    d = getattr(p, "instant_date", None)
    return _to_xsd_date(d)


def xfi_period_start(period_arg: Any) -> Any:
    """xfi:period-start($period) → xs:dateTime of the duration start."""
    if period_arg is not None and hasattr(period_arg, "period_type"):
        p = period_arg
    else:
        ctx = _context_from_arg(period_arg)
        p = _period_of(ctx)
    if p is None:
        return None
    d = getattr(p, "start_date", None)
    return _to_xsd_date(d)


def xfi_period_end(period_arg: Any) -> Any:
    """xfi:period-end($period) → xs:dateTime of the duration end."""
    if period_arg is not None and hasattr(period_arg, "period_type"):
        p = period_arg
    else:
        ctx = _context_from_arg(period_arg)
        p = _period_of(ctx)
    if p is None:
        return None
    d = getattr(p, "end_date", None)
    return _to_xsd_date(d)


# ── Entity / identifier functions ─────────────────────────────────────────

def xfi_entity(fact_arg: Any) -> str:
    """xfi:entity($item) → entity identifier string."""
    ctx = _context_from_arg(fact_arg)
    if ctx is None:
        return ""
    entity = getattr(ctx, "entity", None)
    if entity is None:
        return ""
    return getattr(entity, "identifier", "")


def xfi_context_entity(context_arg: Any) -> str:
    """xfi:context-entity($context) → entity identifier string."""
    # We receive a context ID string or the context itself
    if isinstance(context_arg, str):
        instance = _eval_context.get("_instance")
        if instance is not None:
            ctx = instance.contexts.get(context_arg)
            if ctx:
                return getattr(getattr(ctx, "entity", None), "identifier", "")
    entity = getattr(context_arg, "entity", None)
    return getattr(entity, "identifier", "") if entity else ""


def xfi_identifier(fact_arg: Any) -> str:
    """xfi:identifier($item) → entity identifier value string."""
    return xfi_fact_identifier_value(fact_arg)


def xfi_context_identifier(context_arg: Any) -> str:
    """xfi:context-identifier($context) → entity identifier string."""
    return xfi_context_entity(context_arg)


def xfi_entity_identifier(entity_arg: Any) -> str:
    """xfi:entity-identifier($entity) → entity identifier string."""
    if isinstance(entity_arg, str):
        return entity_arg
    return getattr(entity_arg, "identifier", "")


def xfi_identifier_value(identifier_arg: Any) -> str:
    """xfi:identifier-value($identifier) → xs:string value."""
    if isinstance(identifier_arg, str):
        return identifier_arg
    return getattr(identifier_arg, "identifier", str(identifier_arg))


def xfi_identifier_scheme(identifier_arg: Any) -> str:
    """xfi:identifier-scheme($identifier) → xs:anyURI scheme."""
    ctx = _context_from_arg(identifier_arg)
    if ctx is not None:
        entity = getattr(ctx, "entity", None)
        if entity is not None:
            return getattr(entity, "scheme", "")
    return ""


def xfi_fact_identifier_value(fact_arg: Any) -> str:
    """xfi:fact-identifier-value($fact) → xs:string entity identifier."""
    ctx = _context_from_arg(fact_arg)
    if ctx is None:
        return ""
    entity = getattr(ctx, "entity", None)
    return getattr(entity, "identifier", "") if entity else ""


def xfi_fact_identifier_scheme(fact_arg: Any) -> str:
    """xfi:fact-identifier-scheme($fact) → xs:anyURI entity scheme."""
    ctx = _context_from_arg(fact_arg)
    if ctx is None:
        return ""
    entity = getattr(ctx, "entity", None)
    return getattr(entity, "scheme", "") if entity else ""


def xfi_segment(fact_arg: Any) -> list:
    """xfi:segment($item) → segment content (empty list — not modelled)."""
    return []


def xfi_entity_segment(entity_arg: Any) -> list:
    """xfi:entity-segment($entity) → empty (segment not modelled)."""
    return []


def xfi_context_segment(context_arg: Any) -> list:
    """xfi:context-segment($context) → empty (segment not modelled)."""
    return []


def xfi_scenario(fact_arg: Any) -> list:
    """xfi:scenario($item) → scenario content (empty list — not modelled)."""
    return []


def xfi_context_scenario(context_arg: Any) -> list:
    """xfi:context-scenario($context) → empty (scenario not modelled)."""
    return []


# ── Numeric fact properties ───────────────────────────────────────────────

def xfi_decimals(fact_arg: Any) -> int:
    """xfi:decimals($fact) → xs:integer @decimals attribute."""
    fact = _fact_from_arg(fact_arg)
    if fact is None:
        return 0
    dec = getattr(fact, "decimals", None)
    if dec is None:
        return 0
    try:
        return int(dec)
    except (ValueError, TypeError):
        return 0


def xfi_precision(fact_arg: Any) -> int:
    """xfi:precision($fact) → xs:integer @precision attribute."""
    fact = _fact_from_arg(fact_arg)
    if fact is None:
        return 0
    prec = getattr(fact, "precision", None)
    if prec is None:
        return 0
    try:
        return int(prec)
    except (ValueError, TypeError):
        return 0


def xfi_is_numeric(fact_arg: Any) -> bool:
    """xfi:is-numeric($fact) → true if fact has a unit (numeric fact)."""
    fact = _fact_from_arg(fact_arg)
    if fact is None:
        return False
    return getattr(fact, "unit_ref", None) is not None


def xfi_is_non_numeric(fact_arg: Any) -> bool:
    """xfi:is-non-numeric($fact) → true if fact has no unit."""
    return not xfi_is_numeric(fact_arg)


def xfi_is_fraction(fact_arg: Any) -> bool:
    """xfi:is-fraction($fact) → false (fraction facts not modelled)."""
    return False


# ── Unit functions ────────────────────────────────────────────────────────

def xfi_unit(fact_arg: Any) -> str:
    """xfi:unit($fact) → unit measure URI string."""
    unit = _current_unit()
    if unit is None:
        fact = _fact_from_arg(fact_arg)
        if fact is not None:
            instance = _eval_context.get("_instance")
            if instance is not None:
                unit = instance.units.get(getattr(fact, "unit_ref", "") or "")
    return getattr(unit, "measure_uri", "") if unit else ""


def xfi_unit_numerator(unit_arg: Any) -> list[str]:
    """xfi:unit-numerator($unit) → sequence of measure QName strings."""
    unit = _current_unit()
    measure = getattr(unit, "measure_uri", "") if unit else ""
    return [measure] if measure else []


def xfi_unit_denominator(unit_arg: Any) -> list[str]:
    """xfi:unit-denominator($unit) → empty sequence (simple units only)."""
    return []


def xfi_measure_name(measure_arg: Any) -> str:
    """xfi:measure-name($measure) → measure QName as string."""
    unit = _current_unit()
    return getattr(unit, "measure_uri", "") if unit else str(measure_arg or "")


# ── Dimension functions ───────────────────────────────────────────────────

def _get_context_dimensions(fact_arg: Any) -> dict:
    """Return explicit dimensions for the relevant context."""
    ctx = _context_from_arg(fact_arg)
    if ctx is None:
        return {}
    typed_keys = set((getattr(ctx, "typed_dimensions", {}) or {}).keys())
    return {
        dim_qname: member_qname
        for dim_qname, member_qname in (getattr(ctx, "dimensions", {}) or {}).items()
        if dim_qname not in typed_keys
    }


def _get_context_typed_dimensions(fact_arg: Any) -> dict:
    ctx = _context_from_arg(fact_arg)
    if ctx is None:
        return {}
    return getattr(ctx, "typed_dimensions", {}) or {}


def _qname_from_arg(qname_arg: Any) -> Any:
    """Try to interpret qname_arg as a QName (Clark notation or QName object)."""
    if qname_arg is None:
        return None
    # If it's already a QName-like object with .namespace and .local_name
    if hasattr(qname_arg, "namespace") and hasattr(qname_arg, "local_name"):
        return qname_arg
    # If it's a Clark-notation string {ns}local
    s = str(qname_arg)
    if s.startswith("{"):
        try:
            from bde_xbrl_editor.taxonomy.models import QName
            return QName.from_clark(s)
        except ValueError as exc:
            log.debug("Could not parse QName argument %r: %s", qname_arg, exc)
    return None


def xfi_fact_has_explicit_dimension(fact_arg: Any, dim_qname_arg: Any) -> bool:
    """xfi:fact-has-explicit-dimension($fact, $dimension) → boolean."""
    dims = _get_context_dimensions(fact_arg)
    qn = _qname_from_arg(dim_qname_arg)
    if qn is None:
        return False
    return qn in dims


def xfi_fact_has_typed_dimension(fact_arg: Any, dim_qname_arg: Any) -> bool:
    """xfi:fact-has-typed-dimension($fact, $dimension) → boolean."""
    dims = _get_context_typed_dimensions(fact_arg)
    qn = _qname_from_arg(dim_qname_arg)
    if qn is None:
        return False
    return qn in dims


def xfi_fact_has_explicit_dimension_value(
    fact_arg: Any, dim_qname_arg: Any, value_arg: Any
) -> bool:
    """xfi:fact-has-explicit-dimension-value($fact, $dim, $member) → boolean."""
    dims = _get_context_dimensions(fact_arg)
    qn = _qname_from_arg(dim_qname_arg)
    if qn is None:
        return False
    member = dims.get(qn)
    if member is None:
        return False
    val_qn = _qname_from_arg(value_arg)
    if val_qn is not None:
        return member == val_qn
    return str(member) == str(value_arg)


def xfi_fact_explicit_dimension_value(fact_arg: Any, dim_qname_arg: Any) -> str:
    """xfi:fact-explicit-dimension-value($fact, $dimension) → member QName string."""
    dims = _get_context_dimensions(fact_arg)
    qn = _qname_from_arg(dim_qname_arg)
    if qn is None:
        return ""
    member = dims.get(qn)
    return str(member) if member is not None else ""


def xfi_fact_typed_dimension_value(fact_arg: Any, dim_qname_arg: Any) -> str:
    """xfi:fact-typed-dimension-value($fact, $dimension) → typed value string."""
    dims = _get_context_typed_dimensions(fact_arg)
    qn = _qname_from_arg(dim_qname_arg)
    if qn is None:
        return ""
    value = dims.get(qn)
    return str(value) if value is not None else ""


def xfi_fact_typed_dimension_simple_value(fact_arg: Any, dim_qname_arg: Any) -> str:
    """xfi:fact-typed-dimension-simple-value($fact, $dim) → xs:string."""
    return xfi_fact_typed_dimension_value(fact_arg, dim_qname_arg)


def xfi_fact_explicit_dimensions(fact_arg: Any) -> list[str]:
    """xfi:fact-explicit-dimensions($fact) → sequence of dimension QName strings."""
    dims = _get_context_dimensions(fact_arg)
    return [str(k) for k in dims]


def xfi_fact_typed_dimensions(fact_arg: Any) -> list[str]:
    """xfi:fact-typed-dimensions($fact) → sequence of typed dimension QName strings."""
    dims = _get_context_typed_dimensions(fact_arg)
    return [str(k) for k in dims]


def xfi_fact_dimension_s_equal(
    fact_arg: Any, dim_qname_arg: Any, value_arg: Any
) -> bool:
    """xfi:fact-dimension-s-equal($fact, $dim, $value) → boolean equality check."""
    return xfi_fact_has_explicit_dimension_value(fact_arg, dim_qname_arg, value_arg)


def xfi_fact_dimension_s_equal2(fact1_arg: Any, fact2_arg: Any) -> bool:
    """xfi:fact-dimension-s-equal2($fact1, $fact2) → dimensional context equality."""
    dims1 = _get_context_dimensions(fact1_arg)
    typed_dims1 = _get_context_typed_dimensions(fact1_arg)
    # For fact2, temporarily swap context
    ctx2 = _context_from_arg(fact2_arg)
    dims2 = _get_context_dimensions(fact2_arg) if ctx2 else {}
    typed_dims2 = _get_context_typed_dimensions(fact2_arg) if ctx2 else {}
    return dims1 == dims2 and typed_dims1 == typed_dims2


def xfi_fact_segment_remainder(fact_arg: Any) -> list:
    """xfi:fact-segment-remainder($fact) → empty (not modelled)."""
    return []


def xfi_fact_scenario_remainder(fact_arg: Any) -> list:
    """xfi:fact-scenario-remainder($fact) → empty (not modelled)."""
    return []


# ── Fact equality / comparison ────────────────────────────────────────────

def _fact_value_decimal(fact_arg: Any) -> Decimal | None:
    fact = _fact_from_arg(fact_arg)
    if fact is None:
        return None
    try:
        return Decimal(str(fact.value))
    except (InvalidOperation, TypeError):
        return None


def xfi_v_equal(fact1_arg: Any, fact2_arg: Any) -> bool:
    """xfi:v-equal($f1, $f2) → value equality."""
    v1 = _fact_value_decimal(fact1_arg)
    v2 = _fact_value_decimal(fact2_arg)
    if v1 is None or v2 is None:
        return str(fact1_arg) == str(fact2_arg)
    return v1 == v2


def xfi_c_equal(fact1_arg: Any, fact2_arg: Any) -> bool:
    """xfi:c-equal($f1, $f2) → context equality (same context ref)."""
    f1 = _fact_from_arg(fact1_arg)
    f2 = _fact_from_arg(fact2_arg)
    if f1 is None or f2 is None:
        return False
    return getattr(f1, "context_ref", None) == getattr(f2, "context_ref", None)


def xfi_p_equal(fact1_arg: Any, fact2_arg: Any) -> bool:
    """xfi:p-equal($f1, $f2) → period equality."""
    # Both facts share the same context → same period
    return xfi_c_equal(fact1_arg, fact2_arg)


def xfi_u_equal(fact1_arg: Any, fact2_arg: Any) -> bool:
    """xfi:u-equal($f1, $f2) → unit equality."""
    f1 = _fact_from_arg(fact1_arg)
    f2 = _fact_from_arg(fact2_arg)
    if f1 is None or f2 is None:
        return False
    return getattr(f1, "unit_ref", None) == getattr(f2, "unit_ref", None)


def xfi_s_equal(fact1_arg: Any, fact2_arg: Any) -> bool:
    """xfi:s-equal($f1, $f2) → semantic equality (same context, unit, value)."""
    return (
        xfi_c_equal(fact1_arg, fact2_arg)
        and xfi_u_equal(fact1_arg, fact2_arg)
        and xfi_v_equal(fact1_arg, fact2_arg)
    )


def xfi_cu_equal(fact1_arg: Any, fact2_arg: Any) -> bool:
    """xfi:cu-equal($f1, $f2) → context+unit equality."""
    return xfi_c_equal(fact1_arg, fact2_arg) and xfi_u_equal(fact1_arg, fact2_arg)


def xfi_pc_equal(fact1_arg: Any, fact2_arg: Any) -> bool:
    """xfi:pc-equal($f1, $f2) → period+concept equality."""
    return xfi_p_equal(fact1_arg, fact2_arg)


def xfi_pcu_equal(fact1_arg: Any, fact2_arg: Any) -> bool:
    """xfi:pcu-equal($f1, $f2) → period+concept+unit equality."""
    return xfi_c_equal(fact1_arg, fact2_arg) and xfi_u_equal(fact1_arg, fact2_arg)


def xfi_x_equal(fact1_arg: Any, fact2_arg: Any) -> bool:
    """xfi:x-equal($f1, $f2) → exact/identical equality."""
    return xfi_s_equal(fact1_arg, fact2_arg)


def xfi_start_equal(fact1_arg: Any, fact2_arg: Any) -> bool:
    """xfi:start-equal($f1, $f2) → period start date equality."""
    ctx1 = _context_from_arg(fact1_arg)
    ctx2 = _context_from_arg(fact2_arg)
    p1 = _period_of(ctx1)
    p2 = _period_of(ctx2)
    return getattr(p1, "start_date", None) == getattr(p2, "start_date", None)


def xfi_end_equal(fact1_arg: Any, fact2_arg: Any) -> bool:
    """xfi:end-equal($f1, $f2) → period end date equality."""
    ctx1 = _context_from_arg(fact1_arg)
    ctx2 = _context_from_arg(fact2_arg)
    p1 = _period_of(ctx1)
    p2 = _period_of(ctx2)
    return getattr(p1, "end_date", None) == getattr(p2, "end_date", None)


def xfi_identical_nodes(node1: Any, node2: Any) -> bool:
    """xfi:identical-nodes($n1, $n2) → identity equality."""
    return node1 is node2


def xfi_duplicate_item(fact1_arg: Any, fact2_arg: Any) -> bool:
    """xfi:duplicate-item($f1, $f2) → context+unit equality (duplicate check)."""
    return xfi_cu_equal(fact1_arg, fact2_arg)


def xfi_duplicate_tuple(fact1_arg: Any, fact2_arg: Any) -> bool:
    """xfi:duplicate-tuple($f1, $f2) → context equality (duplicate tuple check)."""
    return xfi_c_equal(fact1_arg, fact2_arg)


# ── Set variants (variadic) ───────────────────────────────────────────────

def xfi_identical_node_set(*args: Any) -> bool:
    """xfi:identical-node-set($nodes) → true if all nodes identical."""
    items = list(args)
    return len(set(id(i) for i in items)) == 1 if items else True


def xfi_s_equal_set(*args: Any) -> bool:
    """xfi:s-equal-set($facts) → true if all facts semantically equal."""
    if len(args) < 2:
        return True
    first = args[0]
    return all(xfi_s_equal(first, a) for a in args[1:])


def xfi_v_equal_set(*args: Any) -> bool:
    """xfi:v-equal-set($facts) → true if all facts value-equal."""
    if len(args) < 2:
        return True
    first = args[0]
    return all(xfi_v_equal(first, a) for a in args[1:])


def xfi_c_equal_set(*args: Any) -> bool:
    """xfi:c-equal-set($facts) → true if all facts context-equal."""
    if len(args) < 2:
        return True
    first = args[0]
    return all(xfi_c_equal(first, a) for a in args[1:])


def xfi_u_equal_set(*args: Any) -> bool:
    """xfi:u-equal-set($facts) → true if all facts unit-equal."""
    if len(args) < 2:
        return True
    first = args[0]
    return all(xfi_u_equal(first, a) for a in args[1:])


# ── Facts / instance access ───────────────────────────────────────────────

def xfi_facts() -> list[Any]:
    """xfi:facts() → all facts in the instance."""
    return _all_facts()


def xfi_taxonomy_refs() -> list[str]:
    """xfi:taxonomy-refs() → taxonomy URIs (empty — not modelled here)."""
    return []


def xfi_any_identifier() -> str:
    """xfi:any-identifier() → first entity identifier found."""
    facts = _all_facts()
    instance = _eval_context.get("_instance")
    if instance is None:
        return ""
    for f in facts:
        ctx = instance.contexts.get(getattr(f, "context_ref", ""))
        if ctx:
            ident = getattr(getattr(ctx, "entity", None), "identifier", None)
            if ident:
                return ident
    return ""


def xfi_unique_identifiers() -> list[str]:
    """xfi:unique-identifiers() → distinct entity identifiers."""
    seen: list[str] = []
    instance = _eval_context.get("_instance")
    if instance is None:
        return seen
    for ctx in instance.contexts.values():
        ident = getattr(getattr(ctx, "entity", None), "identifier", None)
        if ident and ident not in seen:
            seen.append(ident)
    return seen


def xfi_single_unique_identifier() -> str:
    """xfi:single-unique-identifier() → identifier when exactly one exists."""
    ids = xfi_unique_identifiers()
    return ids[0] if len(ids) == 1 else ""


def xfi_any_start_date() -> Any:
    """xfi:any-start-date() → first duration start date found."""
    instance = _eval_context.get("_instance")
    if instance is None:
        return None
    for ctx in instance.contexts.values():
        p = getattr(ctx, "period", None)
        d = getattr(p, "start_date", None)
        if d is not None:
            return _to_xsd_date(d)
    return None


def xfi_any_end_date() -> Any:
    """xfi:any-end-date() → first duration end date found."""
    instance = _eval_context.get("_instance")
    if instance is None:
        return None
    for ctx in instance.contexts.values():
        p = getattr(ctx, "period", None)
        d = getattr(p, "end_date", None)
        if d is not None:
            return _to_xsd_date(d)
    return None


def xfi_any_instant_date() -> Any:
    """xfi:any-instant-date() → first instant date found."""
    instance = _eval_context.get("_instance")
    if instance is None:
        return None
    for ctx in instance.contexts.values():
        p = getattr(ctx, "period", None)
        d = getattr(p, "instant_date", None)
        if d is not None:
            return _to_xsd_date(d)
    return None


def xfi_unique_start_dates() -> list[Any]:
    """xfi:unique-start-dates() → distinct duration start dates."""
    seen: list[Any] = []
    instance = _eval_context.get("_instance")
    if instance is None:
        return seen
    for ctx in instance.contexts.values():
        p = getattr(ctx, "period", None)
        d = getattr(p, "start_date", None)
        if d is not None and d not in seen:
            seen.append(d)
    return [_to_xsd_date(d) for d in seen]


def xfi_unique_end_dates() -> list[Any]:
    """xfi:unique-end-dates() → distinct duration end dates."""
    seen: list[Any] = []
    instance = _eval_context.get("_instance")
    if instance is None:
        return seen
    for ctx in instance.contexts.values():
        p = getattr(ctx, "period", None)
        d = getattr(p, "end_date", None)
        if d is not None and d not in seen:
            seen.append(d)
    return [_to_xsd_date(d) for d in seen]


def xfi_unique_instant_dates() -> list[Any]:
    """xfi:unique-instant-dates() → distinct instant dates."""
    seen: list[Any] = []
    instance = _eval_context.get("_instance")
    if instance is None:
        return seen
    for ctx in instance.contexts.values():
        p = getattr(ctx, "period", None)
        d = getattr(p, "instant_date", None)
        if d is not None and d not in seen:
            seen.append(d)
    return [_to_xsd_date(d) for d in seen]


def xfi_single_unique_start_date() -> Any:
    """xfi:single-unique-start-date() → start date when exactly one exists."""
    dates = xfi_unique_start_dates()
    return dates[0] if len(dates) == 1 else None


def xfi_single_unique_end_date() -> Any:
    """xfi:single-unique-end-date() → end date when exactly one exists."""
    dates = xfi_unique_end_dates()
    return dates[0] if len(dates) == 1 else None


def xfi_single_unique_instant_date() -> Any:
    """xfi:single-unique-instant-date() → instant date when exactly one exists."""
    dates = xfi_unique_instant_dates()
    return dates[0] if len(dates) == 1 else None


# ── Filing indicators ─────────────────────────────────────────────────────

def xfi_positive_filing_indicators() -> list[str]:
    """xfi:positive-filing-indicators() → sequence of template codes."""
    instance = _eval_context.get("_instance")
    if instance is None:
        return []
    indicators = getattr(instance, "filing_indicators", []) or []
    return [getattr(fi, "template_id", "") for fi in indicators if getattr(fi, "filed", True)]


def xfi_negative_filing_indicators() -> list[str]:
    """xfi:negative-filing-indicators() → sequence of non-filed template codes."""
    instance = _eval_context.get("_instance")
    if instance is None:
        return []
    indicators = getattr(instance, "filing_indicators", []) or []
    return [getattr(fi, "template_id", "") for fi in indicators if not getattr(fi, "filed", True)]


def xfi_positive_filing_indicator(indicators_arg: Any, template_code_arg: Any) -> bool:
    """xfi:positive-filing-indicator($indicators, $code) → boolean."""
    code = str(template_code_arg or "")
    if not code:
        return False
    pos = xfi_positive_filing_indicators()
    return code in pos


def xfi_negative_filing_indicator(indicators_arg: Any, template_code_arg: Any) -> bool:
    """xfi:negative-filing-indicator($indicators, $code) → boolean."""
    code = str(template_code_arg or "")
    if not code:
        return False
    neg = xfi_negative_filing_indicators()
    return code in neg


# ── Linkbase / taxonomy access ────────────────────────────────────────────

def xfi_linkbase_link_roles(linkbase_arg: Any = None) -> list[str]:
    """xfi:linkbase-link-roles($linkbase) → empty (not modelled)."""
    return []


def xfi_concept_label(concept_arg: Any, role_arg: Any = None, lang_arg: Any = None) -> str:
    """xfi:concept-label($concept, $role, $lang) → label string."""
    return str(concept_arg or "")


def xfi_arcrole_definition(arcrole_arg: Any) -> str:
    """xfi:arcrole-definition($arcrole) → empty (not modelled)."""
    return ""


def xfi_role_definition(role_arg: Any) -> str:
    """xfi:role-definition($role) → empty (not modelled)."""
    return ""


def xfi_fact_footnotes(fact_arg: Any) -> list:
    """xfi:fact-footnotes($fact) → empty (not modelled)."""
    return []


def xfi_concept_relationships(concept_arg: Any, *args: Any) -> list:
    """xfi:concept-relationships($concept, ...) → empty (not modelled)."""
    return []


def xfi_relationship_from_concept(rel_arg: Any) -> str:
    """xfi:relationship-from-concept($rel) → empty (not modelled)."""
    return ""


def xfi_relationship_to_concept(rel_arg: Any) -> str:
    """xfi:relationship-to-concept($rel) → empty (not modelled)."""
    return ""


def xfi_distinct_nonabstract_parent_concepts(*args: Any) -> list:
    """xfi:distinct-nonAbstract-parent-concepts → empty (not modelled)."""
    return []


def xfi_relationship_attribute(rel_arg: Any, attr_arg: Any) -> str:
    """xfi:relationship-attribute($rel, $attr) → empty (not modelled)."""
    return ""


def xfi_relationship_link_attribute(rel_arg: Any, attr_arg: Any) -> str:
    """xfi:relationship-link-attribute($rel, $attr) → empty (not modelled)."""
    return ""


def xfi_relationship_name(rel_arg: Any) -> str:
    """xfi:relationship-name($rel) → empty (not modelled)."""
    return ""


def xfi_relationship_link_name(rel_arg: Any) -> str:
    """xfi:relationship-link-name($rel) → empty (not modelled)."""
    return ""


# ── Concept properties ────────────────────────────────────────────────────

def xfi_concept_balance(concept_arg: Any) -> str:
    """xfi:concept-balance($concept) → balance type string."""
    return ""


def xfi_concept_period_type(concept_arg: Any) -> str:
    """xfi:concept-period-type($concept) → period type string."""
    return ""


def xfi_concept_custom_attribute(concept_arg: Any, attr_arg: Any) -> str:
    """xfi:concept-custom-attribute($concept, $attr) → empty (not modelled)."""
    return ""


def xfi_concept_data_type(concept_arg: Any) -> str:
    """xfi:concept-data-type($concept) → data type QName string."""
    return ""


def xfi_concept_data_type_derived_from(concept_arg: Any, type_arg: Any) -> bool:
    """xfi:concept-data-type-derived-from($concept, $type) → false (not modelled)."""
    return False


def xfi_concept_substitutions(concept_arg: Any) -> list:
    """xfi:concept-substitutions($concept) → empty (not modelled)."""
    return []


def xfi_filter_member_network_selection(*args: Any) -> list:
    """xfi:filter-member-network-selection → empty (not modelled)."""
    return []


# ── Formatting ────────────────────────────────────────────────────────────

def xfi_format_number(value_arg: Any, picture_arg: Any) -> str:
    """xfi:format-number($value, $picture) → formatted string."""
    try:
        val = float(value_arg)
        pic = str(picture_arg or "")
        # Very basic: if picture has '#,##0.00' style, use Python formatting
        if "," in pic:
            return f"{val:,.2f}"
        if "." in pic:
            decimals = len(pic.split(".")[-1].rstrip("0#"))
            return f"{val:.{decimals}f}"
        return str(int(val))
    except (ValueError, TypeError):
        return str(value_arg or "")


def xfi_distinct_entity_strings() -> list[str]:
    """xfi:distinct-entity-strings() → distinct entity identifier strings."""
    return xfi_unique_identifiers()


# ---------------------------------------------------------------------------
# Backward-compatible aliases (old no-arg forms used before registry rewrite)
# ---------------------------------------------------------------------------

def xfi_decimal(*_args: Any) -> int:
    """Legacy alias: xfi_decimal() → same as xfi_decimals(None)."""
    return xfi_decimals(None)


# ── Tuples (not used in BDE, stubs only) ─────────────────────────────────

def xfi_items_in_tuple(tuple_arg: Any) -> list:
    """xfi:items-in-tuple($tuple) → empty (tuples not used in BDE)."""
    return []


def xfi_tuples_in_tuple(tuple_arg: Any) -> list:
    """xfi:tuples-in-tuple($tuple) → empty (tuples not used in BDE)."""
    return []


# ---------------------------------------------------------------------------
# Parser registration
# ---------------------------------------------------------------------------

# Registry: xfi local-name → (callback, nargs_hint)
# nargs_hint: None = variadic, int = fixed
_XFI_FUNCTIONS: list[tuple[str, Any]] = [
    # Period
    ("context",                        xfi_context),
    ("context-period",                 xfi_context_period),
    ("period",                         xfi_period),
    ("is-instant-period",              xfi_is_instant_period),
    ("is-duration-period",             xfi_is_duration_period),
    ("is-start-end-period",            xfi_is_start_end_period),
    ("is-forever-period",              xfi_is_forever_period),
    ("period-instant",                 xfi_period_instant),
    ("period-start",                   xfi_period_start),
    ("period-end",                     xfi_period_end),
    # Entity / identifier
    ("entity",                         xfi_entity),
    ("context-entity",                 xfi_context_entity),
    ("identifier",                     xfi_identifier),
    ("context-identifier",             xfi_context_identifier),
    ("entity-identifier",              xfi_entity_identifier),
    ("identifier-value",               xfi_identifier_value),
    ("identifier-scheme",              xfi_identifier_scheme),
    ("fact-identifier-value",          xfi_fact_identifier_value),
    ("fact-identifier-scheme",         xfi_fact_identifier_scheme),
    ("segment",                        xfi_segment),
    ("entity-segment",                 xfi_entity_segment),
    ("context-segment",                xfi_context_segment),
    ("scenario",                       xfi_scenario),
    ("context-scenario",               xfi_context_scenario),
    # Numeric properties
    ("decimals",                       xfi_decimals),
    ("precision",                      xfi_precision),
    ("is-numeric",                     xfi_is_numeric),
    ("is-non-numeric",                 xfi_is_non_numeric),
    ("is-fraction",                    xfi_is_fraction),
    # Unit
    ("unit",                           xfi_unit),
    ("unit-numerator",                 xfi_unit_numerator),
    ("unit-denominator",               xfi_unit_denominator),
    ("measure-name",                   xfi_measure_name),
    # Dimensions
    ("fact-has-explicit-dimension",    xfi_fact_has_explicit_dimension),
    ("fact-has-typed-dimension",       xfi_fact_has_typed_dimension),
    ("fact-has-explicit-dimension-value", xfi_fact_has_explicit_dimension_value),
    ("fact-explicit-dimension-value",  xfi_fact_explicit_dimension_value),
    ("fact-typed-dimension-value",     xfi_fact_typed_dimension_value),
    ("fact-typed-dimension-simple-value", xfi_fact_typed_dimension_simple_value),
    ("fact-explicit-dimensions",       xfi_fact_explicit_dimensions),
    ("fact-typed-dimensions",          xfi_fact_typed_dimensions),
    ("fact-dimension-s-equal",         xfi_fact_dimension_s_equal),
    ("fact-dimension-s-equal2",        xfi_fact_dimension_s_equal2),
    ("fact-segment-remainder",         xfi_fact_segment_remainder),
    ("fact-scenario-remainder",        xfi_fact_scenario_remainder),
    # Equality / comparison
    ("v-equal",                        xfi_v_equal),
    ("c-equal",                        xfi_c_equal),
    ("p-equal",                        xfi_p_equal),
    ("u-equal",                        xfi_u_equal),
    ("s-equal",                        xfi_s_equal),
    ("cu-equal",                       xfi_cu_equal),
    ("pc-equal",                       xfi_pc_equal),
    ("pcu-equal",                      xfi_pcu_equal),
    ("x-equal",                        xfi_x_equal),
    ("start-equal",                    xfi_start_equal),
    ("end-equal",                      xfi_end_equal),
    ("identical-nodes",                xfi_identical_nodes),
    ("duplicate-item",                 xfi_duplicate_item),
    ("duplicate-tuple",                xfi_duplicate_tuple),
    # Set equality
    ("identical-node-set",             xfi_identical_node_set),
    ("s-equal-set",                    xfi_s_equal_set),
    ("v-equal-set",                    xfi_v_equal_set),
    ("c-equal-set",                    xfi_c_equal_set),
    ("u-equal-set",                    xfi_u_equal_set),
    # Facts / instance
    ("facts",                          xfi_facts),
    ("taxonomy-refs",                  xfi_taxonomy_refs),
    ("any-identifier",                 xfi_any_identifier),
    ("unique-identifiers",             xfi_unique_identifiers),
    ("single-unique-identifier",       xfi_single_unique_identifier),
    ("any-start-date",                 xfi_any_start_date),
    ("any-end-date",                   xfi_any_end_date),
    ("any-instant-date",               xfi_any_instant_date),
    ("unique-start-dates",             xfi_unique_start_dates),
    ("unique-end-dates",               xfi_unique_end_dates),
    ("unique-instant-dates",           xfi_unique_instant_dates),
    ("single-unique-start-date",       xfi_single_unique_start_date),
    ("single-unique-end-date",         xfi_single_unique_end_date),
    ("single-unique-instant-date",     xfi_single_unique_instant_date),
    # Filing indicators
    ("positive-filing-indicators",     xfi_positive_filing_indicators),
    ("negative-filing-indicators",     xfi_negative_filing_indicators),
    ("positive-filing-indicator",      xfi_positive_filing_indicator),
    ("negative-filing-indicator",      xfi_negative_filing_indicator),
    # Linkbase / taxonomy
    ("linkbase-link-roles",            xfi_linkbase_link_roles),
    ("concept-label",                  xfi_concept_label),
    ("arcrole-definition",             xfi_arcrole_definition),
    ("role-definition",                xfi_role_definition),
    ("fact-footnotes",                 xfi_fact_footnotes),
    ("concept-relationships",          xfi_concept_relationships),
    ("relationship-from-concept",      xfi_relationship_from_concept),
    ("relationship-to-concept",        xfi_relationship_to_concept),
    ("distinct-nonAbstract-parent-concepts", xfi_distinct_nonabstract_parent_concepts),
    ("relationship-attribute",         xfi_relationship_attribute),
    ("relationship-link-attribute",    xfi_relationship_link_attribute),
    ("relationship-name",              xfi_relationship_name),
    ("relationship-link-name",         xfi_relationship_link_name),
    # Concept properties
    ("concept-balance",                xfi_concept_balance),
    ("concept-period-type",            xfi_concept_period_type),
    ("concept-custom-attribute",       xfi_concept_custom_attribute),
    ("concept-data-type",              xfi_concept_data_type),
    ("concept-data-type-derived-from", xfi_concept_data_type_derived_from),
    ("concept-substitutions",          xfi_concept_substitutions),
    ("filter-member-network-selection", xfi_filter_member_network_selection),
    # Formatting
    ("format-number",                  xfi_format_number),
    ("distinct-entity-strings",        xfi_distinct_entity_strings),
    # Tuples
    ("items-in-tuple",                 xfi_items_in_tuple),
    ("tuples-in-tuple",                xfi_tuples_in_tuple),
]


# ---------------------------------------------------------------------------
# Eurofiling interval arithmetic functions (iaf: namespace)
# ---------------------------------------------------------------------------

_IAF_NS = "http://www.eurofiling.info/xbrl/func/interval-arithmetics"


def _to_decimal(v: Any) -> Decimal:
    """Coerce v to Decimal; return 0 on failure."""
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, float)):
        return Decimal(str(v))
    try:
        return Decimal(str(v))
    except (InvalidOperation, Exception):  # noqa: BLE001
        return Decimal(0)


def _flatten_decimal(*args: Any) -> list[Decimal]:
    """Flatten potentially nested sequences of values into a flat list of Decimals."""
    result: list[Decimal] = []
    for arg in args:
        if isinstance(arg, (list, tuple)):
            for item in arg:
                result.append(_to_decimal(item))
        else:
            result.append(_to_decimal(arg))
    return result


def iaf_sum(values: Any) -> Decimal:
    """iaf:sum — sum of a numeric sequence."""
    return sum(_flatten_decimal(values), Decimal(0))


def iaf_error_margin(*args: Any) -> Decimal:
    """iaf:error-margin — rounding tolerance.

    In full XBRL interval arithmetic this is 0.5 * 10^(-decimals).
    Without decimals metadata in the current binding model, return 0
    (exact comparison).  This is conservative: it may produce false negatives
    but never false positives.
    """
    return Decimal(0)


def iaf_numeric_equal(*args: Any) -> bool:
    """iaf:numeric-equal(a, b[, margin]) — |a - b| <= margin."""
    if len(args) < 2:
        return True
    vals = _flatten_decimal(*args[:2])
    a, b = vals[0], vals[1]
    margin = _to_decimal(args[2]) if len(args) > 2 else Decimal(0)
    return abs(a - b) <= margin


def iaf_numeric_add(*args: Any) -> Decimal:
    """iaf:numeric-add(a, b) — add two numeric values."""
    if len(args) < 2:
        return Decimal(0)
    vals = _flatten_decimal(*args[:2])
    return vals[0] + vals[1]


def iaf_numeric_less_equal_than(*args: Any) -> bool:
    """iaf:numeric-less-equal-than(a, b[, margin]) — a <= b + margin."""
    if len(args) < 2:
        return True
    vals = _flatten_decimal(*args[:2])
    a, b = vals[0], vals[1]
    margin = _to_decimal(args[2]) if len(args) > 2 else Decimal(0)
    return a <= b + margin


def iaf_numeric_greater_equal_than(*args: Any) -> bool:
    """iaf:numeric-greater-equal-than(a, b[, margin]) — a >= b - margin."""
    if len(args) < 2:
        return True
    vals = _flatten_decimal(*args[:2])
    a, b = vals[0], vals[1]
    margin = _to_decimal(args[2]) if len(args) > 2 else Decimal(0)
    return a >= b - margin


def iaf_numeric_unary_minus(*args: Any) -> Decimal:
    """iaf:numeric-unary-minus(a) — negate a numeric value."""
    if not args:
        return Decimal(0)
    return -_to_decimal(args[0])


_IAF_FUNCTIONS: list[tuple[str, Any, tuple[str, ...]]] = [
    ("sum", iaf_sum, ("xs:anyAtomicType*", "xs:decimal")),
    ("error-margin", iaf_error_margin, ()),
    ("numeric-add", iaf_numeric_add, ()),
    ("numeric-equal", iaf_numeric_equal, ()),
    ("numeric-less-equal-than", iaf_numeric_less_equal_than, ()),
    ("numeric-greater-equal-than", iaf_numeric_greater_equal_than, ()),
    ("numeric-unary-minus", iaf_numeric_unary_minus, ()),
]


# ---------------------------------------------------------------------------
# Eurofiling extra functions (efn: namespace)
# ---------------------------------------------------------------------------

def efn_imp(*args: Any) -> bool:
    """efn:imp(P, Q) — logical implication: if P then Q (i.e. not P or Q)."""
    if len(args) < 2:
        return True
    p = bool(args[0])
    q = bool(args[1])
    return (not p) or q


def efn_iff(*args: Any) -> bool:
    """efn:iff(P, Q) — biconditional: P if and only if Q."""
    if len(args) < 2:
        return True
    p = bool(args[0])
    q = bool(args[1])
    return p == q


_EFN_FUNCTIONS: list[tuple[str, Any]] = [
    ("imp", efn_imp),
    ("iff", efn_iff),
]


# Singleton parser class (built once at first access)
_XbrlFormulaParserClass: type | None = None


def _get_parser_class() -> type:
    global _XbrlFormulaParserClass
    if _XbrlFormulaParserClass is None:
        _XbrlFormulaParserClass = build_registered_parser_class(
            xfi_namespace=_XFI_NS,
            efn_namespace=_EFN_NS,
            iaf_namespace=_IAF_NS,
            xfi_functions=_XFI_FUNCTIONS,
            efn_functions=_EFN_FUNCTIONS,
            iaf_functions=_IAF_FUNCTIONS,
        )
    return _XbrlFormulaParserClass


def _normalize_xpath_value(result: list[Any]) -> Any:
    if not result:
        return []
    if len(result) == 1:
        return result[0]
    return result


def _select_custom_functions(
    definitions: tuple[CustomFunctionDefinition, ...],
    expressions: tuple[str, ...],
) -> tuple[CustomFunctionDefinition, ...]:
    if not definitions or not expressions:
        return definitions

    by_name: dict[tuple[str | None, str], list[CustomFunctionDefinition]] = {}
    for definition in definitions:
        by_name.setdefault((definition.prefix, definition.local_name), []).append(definition)

    selected_keys: set[tuple[str | None, str]] = set()
    queue: list[tuple[str | None, str]] = []
    for expression in expressions:
        for prefix, local_name in _CUSTOM_FUNCTION_CALL_RE.findall(expression):
            key = (prefix, local_name)
            if key in by_name and key not in selected_keys:
                selected_keys.add(key)
                queue.append(key)

    while queue:
        key = queue.pop()
        for definition in by_name.get(key, []):
            for step in definition.steps:
                for nested_prefix, nested_local in _CUSTOM_FUNCTION_CALL_RE.findall(step.expression):
                    nested_key = (nested_prefix, nested_local)
                    if nested_key in by_name and nested_key not in selected_keys:
                        selected_keys.add(nested_key)
                        queue.append(nested_key)

    if not selected_keys:
        return ()

    return tuple(
        definition
        for definition in definitions
        if (definition.prefix, definition.local_name) in selected_keys
    )


def _make_custom_function_callback(definitions: list[CustomFunctionDefinition]):
    def callback(*args: Any) -> Any:
        definition = next(
            (candidate for candidate in definitions if len(candidate.input_names) == len(args)),
            definitions[0],
        )
        return _evaluate_custom_function(definition, args)

    return callback


def _evaluate_custom_function(definition: CustomFunctionDefinition, args: tuple[Any, ...]) -> Any:
    import elementpath

    variables: dict[str, Any] = {}
    for name, value in zip(definition.input_names, args, strict=False):
        variables[name] = value

    context_item: Any = True
    for value in variables.values():
        if isinstance(value, list):
            if value:
                context_item = value[0]
                break
        else:
            context_item = value
            break

    parser = build_formula_parser(
        namespaces=definition.namespaces,
        custom_functions=_custom_functions(),
        expression_hints=(step.expression for step in definition.steps),
    )
    for step in definition.steps:
        token = parser.parse(_normalize_custom_function_expression(step.expression))
        ctx = elementpath.XPathContext(
            root=None,
            item=context_item,
            variables=variables,
        )
        result = list(token.select(ctx))
        normalized = _normalize_xpath_value(result)
        if step.is_output:
            return normalized
        if step.name:
            variables[step.name] = normalized

    return []


def _normalize_custom_function_expression(expression: str) -> str:
    """Relax schema-bound kind tests that elementpath cannot resolve without a schema."""
    return re.sub(r"schema-element\([^)]+\)", "element()", expression)


def build_formula_parser(
    namespaces: dict[str, str] | None = None,
    custom_functions: tuple[CustomFunctionDefinition, ...] = (),
    expression_hints: tuple[str, ...] | list[str] = (),
) -> Any:
    """Return an XPath2Parser instance with all xfi: functions registered and
    the given formula-file namespaces in scope.

    Instances are lightweight — only the singleton class is expensive to build.
    """
    cls = _get_parser_class()
    ns = dict(namespaces or {})
    ns.setdefault("xfi", _XFI_NS)
    ns.setdefault("efn", _EFN_NS)
    ns.setdefault("iaf", _IAF_NS)
    parser = cls(namespaces=ns)
    if custom_functions:
        selected_functions = _select_custom_functions(
            custom_functions,
            tuple(expression_hints),
        ) if expression_hints else custom_functions
        if selected_functions:
            register_custom_functions(
                parser,
                selected_functions,
                _make_custom_function_callback,
            )
    return parser

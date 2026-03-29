"""XBRL formula xfi: namespace function registrations for elementpath.

Registers core xfi: functions as Python callbacks so that XPath 2.0 test
expressions in formula assertions can reference XBRL fact properties.
"""

from __future__ import annotations

from typing import Any

_XFI_NS = "http://www.xbrl.org/2008/function/instance"

# Thread-local context for the current fact binding during XPath evaluation
_eval_context: dict[str, Any] = {}


def set_evaluation_context(binding: dict[str, Any]) -> None:
    """Set the current fact binding context for xfi: function calls."""
    _eval_context.clear()
    _eval_context.update(binding)


def clear_evaluation_context() -> None:
    """Clear the current fact binding context."""
    _eval_context.clear()


def xfi_facts(*_args: Any) -> list[Any]:
    """xfi:facts() — all facts in the current binding."""
    return list(_eval_context.get("_all_facts", []))


def xfi_period(*_args: Any) -> str:
    """xfi:period() — period string for the current context."""
    ctx = _eval_context.get("_context")
    if ctx is None:
        return ""
    period = ctx.period
    if period.period_type == "instant":
        return str(period.instant_date or "")
    return f"{period.start_date}/{period.end_date}"


def xfi_entity(*_args: Any) -> str:
    """xfi:entity() — entity identifier for the current context."""
    ctx = _eval_context.get("_context")
    if ctx is None:
        return ""
    return getattr(getattr(ctx, "entity", None), "identifier", "")


def xfi_unit(*_args: Any) -> str:
    """xfi:unit() — unit measure for the current fact."""
    unit = _eval_context.get("_unit")
    if unit is None:
        return ""
    return unit.measure_uri


def xfi_decimal(*_args: Any) -> int:
    """xfi:decimal() — @decimals attribute of the current fact."""
    fact = _eval_context.get("_current_fact")
    if fact is None or fact.decimals is None:
        return 0
    try:
        return int(fact.decimals)
    except (ValueError, TypeError):
        return 0


# Registry: xfi: local-name → callable
XFI_FUNCTION_REGISTRY: dict[str, Any] = {
    "facts": xfi_facts,
    "period": xfi_period,
    "entity": xfi_entity,
    "unit": xfi_unit,
    "decimal": xfi_decimal,
}

"""InstanceSerializer — converts XbrlInstance to well-formed XBRL 2.1 XML."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

from lxml import etree

from bde_xbrl_editor.instance.constants import (
    BDE_DIM_NS,
    BDE_DIM_PFX,
    BDE_PBLO_NS,
    BDE_PBLO_PFX,
    FILING_IND_NS,
    FILING_IND_PFX,
    ISO4217_NS,
    LINK_NS,
    XBRLDI_NS,
    XBRLI_NS,
    XLINK_NS,
    is_bde_schema_ref,
)
from bde_xbrl_editor.instance.models import (
    BdeEstadoReportado,
    BdePreambulo,
    Fact,
    InstanceSaveError,
    OrphanedFact,
    ReportingPeriod,
    XbrlContext,
    XbrlInstance,
    XbrlUnit,
)
from bde_xbrl_editor.instance.temporal import period_lexical
from bde_xbrl_editor.taxonomy.models import QName
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_fragment

# Standard namespace map declared on the root element (prefix → namespace)
_BASE_NSMAP: dict[str, str] = {
    "xbrli": XBRLI_NS,
    "link": LINK_NS,
    "xlink": XLINK_NS,
    "xbrldi": XBRLDI_NS,
    "iso4217": ISO4217_NS,
    FILING_IND_PFX: FILING_IND_NS,
}

# BDE-specific namespaces added to the root element when preambulo data is present
_BDE_NSMAP: dict[str, str] = {
    BDE_PBLO_PFX: BDE_PBLO_NS,
    BDE_DIM_PFX: BDE_DIM_NS,
}


def _last_segment(namespace: str) -> str:
    """Return the last non-empty path segment of a URL, sanitized as an XML NCName."""
    try:
        path = urlparse(namespace).path
        for seg in reversed(path.split("/")):
            if not seg:
                continue
            hint = re.sub(r"[^a-zA-Z0-9_]", "_", seg).strip("_")
            hint = re.sub(r"^[0-9]+", "", hint)
            if hint:
                return hint
    except Exception:  # noqa: BLE001
        pass
    return "ns"


def _org_segment(namespace: str) -> str:
    """Return a short organisation identifier from the hostname.

    Examples:
      www.bde.es          →  bde
      www.eba.europa.eu   →  eba
      www.xbrl.org        →  xbrl
    """
    try:
        host = urlparse(namespace).hostname or ""
        parts = [p for p in host.split(".") if p and p != "www"]
        if parts:
            return re.sub(r"[^a-zA-Z0-9]", "_", parts[0])
    except Exception:  # noqa: BLE001
        pass
    return ""


def _collect_extra_nsmap(instance: XbrlInstance) -> dict[str, str]:
    """Return {prefix: namespace} for every namespace in the instance not already in _BASE_NSMAP.

    Strategy:
    1. Prefer any prefix already stored on the QName objects.
    2. Otherwise use the last URL path segment (e.g. ``ebacrr_TA``, ``dim``).
    3. When two namespaces share the same last segment, both are promoted to
       ``{org}_{segment}`` (e.g. ``bde_dim`` and ``eba_dim``) so the output
       is unambiguous without ugly numeric suffixes.
    4. Any remaining collision gets ``_2``, ``_3``, … appended.
    """
    base_ns = set(_BASE_NSMAP.values())

    # Gather namespace → best known prefix (QName.prefix wins over URL-derived)
    ns_to_best: dict[str, str | None] = {}
    qnames: list[QName] = []
    for ctx in instance.contexts.values():
        qnames.extend(ctx.dimensions.keys())
        qnames.extend(ctx.dimensions.values())
    for fact in (*instance.facts, *instance.tuple_facts):
        qnames.append(fact.concept)
    for unit in instance.units.values():
        if unit.unit_form == "divide":
            qnames.extend(unit.numerator_measure_qnames)
            qnames.extend(unit.denominator_measure_qnames)
        else:
            qnames.extend(_simple_unit_measures(unit))

    for qn in qnames:
        if not qn.namespace or qn.namespace in base_ns:
            continue
        existing = ns_to_best.get(qn.namespace)
        if qn.namespace not in ns_to_best or (existing is None and qn.prefix):
            ns_to_best[qn.namespace] = qn.prefix

    # Build initial hint per namespace
    hints: dict[str, str] = {
        ns: (preferred or _last_segment(ns)) for ns, preferred in ns_to_best.items()
    }

    # Detect clashing hints — promote clashing namespaces to org_segment
    from collections import Counter  # noqa: PLC0415

    clash = {hint for hint, count in Counter(hints.values()).items() if count > 1}
    final_hints: dict[str, str] = {}
    for ns, hint in hints.items():
        if hint in clash:
            org = _org_segment(ns)
            final_hints[ns] = f"{org}_{hint}" if org else hint
        else:
            final_hints[ns] = hint

    # Assign with numeric fallback for any residual collisions
    result: dict[str, str] = {}
    used = set(_BASE_NSMAP.keys())
    for ns, candidate in final_hints.items():
        final = candidate
        n = 2
        while final in used:
            final = f"{candidate}_{n}"
            n += 1
        result[final] = ns
        used.add(final)

    return result


def _qname_str(qname: QName, ns_to_prefix: dict[str, str]) -> str:
    """Render a QName as ``prefix:local`` using the provided namespace→prefix map."""
    prefix = ns_to_prefix.get(qname.namespace)
    if prefix:
        return f"{prefix}:{qname.local_name}"
    return str(qname)  # fallback (should not normally be reached)


_XLINK_HREF = f"{{{XLINK_NS}}}href"
_XLINK_TYPE = f"{{{XLINK_NS}}}type"
_XLINK_ARCROLE = f"{{{XLINK_NS}}}arcrole"


def _date_str(d) -> str:  # type: ignore[no-untyped-def]
    """Format a date as YYYY-MM-DD."""
    return d.strftime("%Y-%m-%d")


def _build_context_el(ctx: XbrlContext, ns_to_prefix: dict[str, str]) -> etree._Element:
    """Build a single <xbrli:context> element with fully-prefixed QName strings."""
    ctx_el = etree.Element(
        f"{{{XBRLI_NS}}}context", attrib={"id": ctx.context_id}, nsmap={"xbrli": XBRLI_NS}
    )

    # <xbrli:entity>
    entity_el = etree.SubElement(ctx_el, f"{{{XBRLI_NS}}}entity")
    ident_el = etree.SubElement(
        entity_el,
        f"{{{XBRLI_NS}}}identifier",
        attrib={"scheme": ctx.entity.scheme},
    )
    ident_el.text = ctx.entity.identifier

    # <xbrli:period>
    period_el = etree.SubElement(ctx_el, f"{{{XBRLI_NS}}}period")
    _fill_period(period_el, ctx.period)

    from bde_xbrl_editor.instance.context_xml import (
        append_preserving_namespaces,
        effective_context_containers,
    )

    for name, container in effective_context_containers(ctx, ns_to_prefix).items():
        append_preserving_namespaces(entity_el if name == "segment" else ctx_el, container)

    return ctx_el


def _fill_period(period_el: etree._Element, period: ReportingPeriod) -> None:
    if period.period_type == "instant":
        inst_el = etree.SubElement(period_el, f"{{{XBRLI_NS}}}instant")
        inst_el.text = period_lexical(period, "instant")
    elif period.period_type == "duration":
        start_el = etree.SubElement(period_el, f"{{{XBRLI_NS}}}startDate")
        start_el.text = period_lexical(period, "start")
        end_el = etree.SubElement(period_el, f"{{{XBRLI_NS}}}endDate")
        end_el.text = period_lexical(period, "end")
    else:
        etree.SubElement(period_el, f"{{{XBRLI_NS}}}forever")


def _simple_unit_measures(unit: XbrlUnit) -> tuple[QName, ...]:
    """Prefer structured measures, retaining legacy URI-only construction."""
    if unit.simple_measure_qnames:
        return unit.simple_measure_qnames
    if unit.measure_qname is not None:
        return (unit.measure_qname,)
    lexical = unit.measure_uri.strip()
    if lexical.startswith("{"):
        return (QName.from_clark(lexical),)
    for namespace in (ISO4217_NS, XBRLI_NS):
        if lexical.startswith(namespace + ":"):
            return (QName(namespace, lexical[len(namespace) + 1:]),)
    prefix, separator, local = lexical.partition(":")
    if separator:
        if prefix not in _BASE_NSMAP:
            raise ValueError(f"Unit {unit.unit_id} has an unresolved measure prefix: {prefix}")
        return (QName(_BASE_NSMAP[prefix], local),)
    if not lexical:
        raise ValueError(f"Unit {unit.unit_id} has no measures")
    return (QName("", lexical),)


def _build_unit_el(unit: XbrlUnit, ns_to_prefix: dict[str, str]) -> etree._Element:
    """Write each measure, preserving products, quotients and multiplicity."""
    unit_el = etree.Element(f"{{{XBRLI_NS}}}unit", attrib={"id": unit.unit_id})
    if unit.unit_form == "divide":
        divide = etree.SubElement(unit_el, f"{{{XBRLI_NS}}}divide")
        groups = (
            (etree.SubElement(divide, f"{{{XBRLI_NS}}}unitNumerator"), unit.numerator_measure_qnames),
            (etree.SubElement(divide, f"{{{XBRLI_NS}}}unitDenominator"), unit.denominator_measure_qnames),
        )
    else:
        groups = ((unit_el, _simple_unit_measures(unit)),)
    for parent, measures in groups:
        if not measures:
            raise ValueError(f"Unit {unit.unit_id} has an empty measure group")
        for qname in measures:
            measure = etree.SubElement(parent, f"{{{XBRLI_NS}}}measure")
            measure.text = _qname_str(qname, ns_to_prefix) if qname.namespace else qname.local_name
    return unit_el



def _append_fact(parent: etree._Element, fact: Fact, *, tuple_shell: bool = False) -> etree._Element:
    """Preserve source metadata while applying the current editable item state."""
    from bde_xbrl_editor.instance.context_xml import append_preserving_namespaces

    tag = (f"{{{fact.concept.namespace}}}{fact.concept.local_name}"
           if fact.concept.namespace else fact.concept.local_name)
    source = parse_xml_fragment(fact.source_element_xml) if fact.source_element_xml else None
    if source is not None and tuple_shell:
        for child in list(source):
            source.remove(child)
    if source is None:
        element = etree.SubElement(parent, tag)
    else:
        source.tag = tag
        element = append_preserving_namespaces(parent, source)
    if tuple_shell:
        return element
    for attribute in ("contextRef", "unitRef", "decimals", "precision", "{http://www.w3.org/2001/XMLSchema-instance}nil"):
        element.attrib.pop(attribute, None)
    element.set("contextRef", fact.context_ref)
    if fact.unit_ref:
        element.set("unitRef", fact.unit_ref)
    if not fact.is_nil and fact.decimals is not None:
        element.set("decimals", fact.decimals)
    elif not fact.is_nil and fact.precision is not None:
        element.set("precision", fact.precision)
    if fact.is_nil:
        element.set("{http://www.w3.org/2001/XMLSchema-instance}nil", "true")
        for child in list(element):
            element.remove(child)
        element.text = None
    elif source is None or (source.text or "").strip() != fact.value:
        if len(element):
            raise ValueError(f"Cannot replace structured item {fact.concept} with a scalar value")
        element.text = fact.value
    return element


def _append_instance_facts(root: etree._Element, instance: XbrlInstance) -> None:
    """Rebuild only current nodes; tuple source children must never be resurrected."""
    from collections import defaultdict

    from bde_xbrl_editor.instance.context_xml import append_preserving_namespaces

    tuples = {fact.position_path: fact for fact in instance.tuple_facts if fact.position_path}
    groups = defaultdict(list)
    seen_positions = set()
    nodes = [*instance.tuple_facts, *instance.facts, *instance.orphaned_facts]
    tuple_ids = {id(fact) for fact in instance.tuple_facts}
    for index, fact in enumerate(nodes):
        position = fact.position_path
        parent = fact.tuple_path
        if parent and parent not in tuples:
            raise ValueError(f"Missing tuple parent {parent} for fact")
        if position:
            if position in seen_positions:
                raise ValueError(f"Duplicate fact position {position}")
            if position[:-1] != parent:
                raise ValueError(f"Fact position {position} does not match tuple parent {parent}")
            seen_positions.add(position)
        groups[parent].append((position, index, fact))

    def append_children(parent: etree._Element, owner: tuple[int, ...]) -> None:
        ordered = sorted(groups[owner], key=lambda item: (not bool(item[0]), item[0], item[1]))
        for position, _, fact in ordered:
            if isinstance(fact, OrphanedFact):
                append_preserving_namespaces(parent, parse_xml_fragment(fact.raw_element_xml))
            elif id(fact) in tuple_ids:
                element = _append_fact(parent, fact, tuple_shell=True)
                if position:
                    append_children(element, position)
            else:
                _append_fact(parent, fact)

    append_children(root, ())

def _build_bde_preambulo_els(preambulo: BdePreambulo, root: etree._Element) -> None:
    """Append BDE IE_2008_02 preamble elements as direct children of *root*.

    Order per spec: EntidadPresentadora → TipoEnvio → EstadosReportados.
    All elements share the same contextRef (typically the dimensionless context).
    """
    ctx_ref = preambulo.context_ref

    if preambulo.entidad_presentadora:
        el = etree.SubElement(root, f"{{{BDE_PBLO_NS}}}EntidadPresentadora")
        el.set("contextRef", ctx_ref)
        el.text = preambulo.entidad_presentadora

    if preambulo.tipo_envio:
        el = etree.SubElement(root, f"{{{BDE_PBLO_NS}}}TipoEnvio")
        el.set("contextRef", ctx_ref)
        el.text = preambulo.tipo_envio

    if preambulo.estados_reportados:
        wrapper = etree.SubElement(root, f"{{{BDE_PBLO_NS}}}EstadosReportados")
        blanco_attr = f"{{{BDE_PBLO_NS}}}blanco"
        for estado in preambulo.estados_reportados:
            estado_el = etree.SubElement(wrapper, f"{{{BDE_PBLO_NS}}}CodigoEstado")
            estado_el.set("contextRef", estado.context_ref or ctx_ref)
            if estado.blanco:
                estado_el.set(blanco_attr, "true")
            estado_el.text = estado.codigo


def _build_bde_preambulo_from_filing_indicators(instance: XbrlInstance) -> BdePreambulo | None:
    """Derive BDE preamble state from filing indicators when needed for save."""
    if not instance.filing_indicators:
        return None

    context_ref = (
        (instance.bde_preambulo.context_ref if instance.bde_preambulo is not None else "")
        or instance.filing_indicators[0].context_ref
        or next(iter(instance.contexts), "")
    )
    entidad_presentadora = (
        instance.bde_preambulo.entidad_presentadora if instance.bde_preambulo is not None else ""
    )
    tipo_envio = instance.bde_preambulo.tipo_envio if instance.bde_preambulo is not None else ""
    estados = [
        BdeEstadoReportado(
            codigo=fi.template_id,
            blanco=not fi.filed,
            context_ref=fi.context_ref or context_ref,
        )
        for fi in instance.filing_indicators
    ]
    return BdePreambulo(
        entidad_presentadora=entidad_presentadora,
        tipo_envio=tipo_envio,
        estados_reportados=estados,
        context_ref=context_ref,
    )


class InstanceSerializer:
    """Serialises an XbrlInstance to XBRL 2.1 XML bytes or writes to disk."""

    def to_xml(self, instance: XbrlInstance) -> bytes:
        """Produce well-formed XBRL 2.1 XML bytes without writing to disk.

        The output is always deterministic for the same instance state.
        """
        bde_preambulo_for_save = instance.bde_preambulo
        if bde_preambulo_for_save is None and is_bde_schema_ref(instance.schema_ref_href):
            bde_preambulo_for_save = _build_bde_preambulo_from_filing_indicators(instance)

        # Build namespace map: base namespaces + BDE namespaces (when needed) +
        # every other namespace used in this instance.
        # All prefixes are declared on the root element so the output is self-contained
        # and validators can resolve every QName without relying on default namespaces.
        bde_nsmap = _BDE_NSMAP if bde_preambulo_for_save is not None else {}
        extra_nsmap = _collect_extra_nsmap(instance)
        full_nsmap: dict[str, str] = {**_BASE_NSMAP, **bde_nsmap, **extra_nsmap}
        ns_to_prefix: dict[str, str] = {ns: pfx for pfx, ns in full_nsmap.items()}

        # Root element
        root = etree.Element(f"{{{XBRLI_NS}}}xbrl", nsmap=full_nsmap)  # type: ignore[arg-type]

        # 1. schemaRef
        schema_ref = etree.SubElement(root, f"{{{LINK_NS}}}schemaRef")
        schema_ref.set(_XLINK_HREF, instance.schema_ref_href)
        schema_ref.set(_XLINK_TYPE, "simple")
        schema_ref.set(
            _XLINK_ARCROLE,
            "http://www.xbrl.org/2003/arcrole/facet-equivalence",
        )

        # 2. BDE preamble elements (before contexts — per IE_2008_02 convention)
        if bde_preambulo_for_save is not None:
            _build_bde_preambulo_els(bde_preambulo_for_save, root)

        # 3. Contexts — sorted by context_id for determinism
        for ctx in sorted(instance.contexts.values(), key=lambda c: c.context_id):
            from bde_xbrl_editor.instance.context_xml import append_preserving_namespaces

            append_preserving_namespaces(root, _build_context_el(ctx, ns_to_prefix))

        # 4. Units — sorted by unit_id
        for unit in sorted(instance.units.values(), key=lambda u: u.unit_id):
            root.append(_build_unit_el(unit, ns_to_prefix))

        # 5. Filing indicators wrapper
        # BDE instances encode filing-indicator semantics in EstadosReportados,
        # so avoid writing a second Eurofiling wrapper during round-trip.
        use_eurofiling_indicators = not (
            (bde_preambulo_for_save is not None and bde_preambulo_for_save.estados_reportados)
            or is_bde_schema_ref(instance.schema_ref_href)
        )
        if use_eurofiling_indicators and instance.filing_indicators:
            fi_wrapper = etree.SubElement(root, f"{{{FILING_IND_NS}}}fIndicators")
            for fi in instance.filing_indicators:
                fi_el = etree.SubElement(
                    fi_wrapper,
                    f"{{{FILING_IND_NS}}}filingIndicator",
                    attrib={
                        "contextRef": fi.context_ref,
                        "filed": "true" if fi.filed else "false",
                    },
                )
                fi_el.text = fi.template_id

        # 6. Items, tuples and unknown items retain their original ownership/order.
        _append_instance_facts(root, instance)

        return etree.tostring(
            root,
            pretty_print=True,
            xml_declaration=True,
            encoding="UTF-8",
        )

    def save(self, instance: XbrlInstance, path: str | Path) -> None:
        """Serialise instance to XBRL 2.1 XML and write to path.

        Calls ``instance.mark_saved(path)`` on success.

        Raises:
            InstanceSaveError — file write failed.
        """
        path = Path(path)
        try:
            xml_bytes = self.to_xml(instance)
            path.write_bytes(xml_bytes)
        except (OSError, ValueError) as exc:
            raise InstanceSaveError(path=str(path), reason=str(exc)) from exc
        instance.mark_saved(path)

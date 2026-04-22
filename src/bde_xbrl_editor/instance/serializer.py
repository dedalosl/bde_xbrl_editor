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
    InstanceSaveError,
    ReportingPeriod,
    XbrlContext,
    XbrlInstance,
    XbrlUnit,
)
from bde_xbrl_editor.taxonomy.models import QName

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
    for fact in instance.facts:
        qnames.append(fact.concept)

    for qn in qnames:
        if not qn.namespace or qn.namespace in base_ns:
            continue
        existing = ns_to_best.get(qn.namespace)
        if qn.namespace not in ns_to_best or (existing is None and qn.prefix):
            ns_to_best[qn.namespace] = qn.prefix

    # Build initial hint per namespace
    hints: dict[str, str] = {
        ns: (preferred or _last_segment(ns))
        for ns, preferred in ns_to_best.items()
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
    ctx_el = etree.Element(f"{{{XBRLI_NS}}}context", attrib={"id": ctx.context_id})

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

    explicit_dimensions = {
        dim_qname: member_qname
        for dim_qname, member_qname in ctx.dimensions.items()
        if dim_qname not in (ctx.typed_dimensions or {})
    }

    dim_containers = ctx.dim_containers or {}
    container_dims: dict[str, dict[QName, QName]] = {"scenario": {}, "segment": {}}
    container_typed: dict[str, dict[QName, str]] = {"scenario": {}, "segment": {}}

    for dim_qname, member_qname in explicit_dimensions.items():
        container = dim_containers.get(dim_qname, ctx.context_element)
        container_dims[container][dim_qname] = member_qname

    for dim_qname, typed_value in (ctx.typed_dimensions or {}).items():
        container = dim_containers.get(dim_qname, ctx.context_element)
        container_typed[container][dim_qname] = typed_value

    for container_name in ("segment", "scenario"):
        if not container_dims[container_name] and not container_typed[container_name]:
            continue
        container_tag = (
            f"{{{XBRLI_NS}}}segment"
            if container_name == "segment"
            else f"{{{XBRLI_NS}}}scenario"
        )
        container_el = etree.SubElement(ctx_el, container_tag)
        for dim_qname, member_qname in sorted(
            container_dims[container_name].items(), key=lambda kv: str(kv[0])
        ):
            em = etree.SubElement(
                container_el,
                f"{{{XBRLDI_NS}}}explicitMember",
                attrib={"dimension": _qname_str(dim_qname, ns_to_prefix)},
            )
            em.text = _qname_str(member_qname, ns_to_prefix)
        for dim_qname, typed_value in sorted(
            container_typed[container_name].items(), key=lambda kv: str(kv[0])
        ):
            tm = etree.SubElement(
                container_el,
                f"{{{XBRLDI_NS}}}typedMember",
                attrib={"dimension": _qname_str(dim_qname, ns_to_prefix)},
            )
            typed_element_qname = (ctx.typed_dimension_elements or {}).get(dim_qname, dim_qname)
            typed_el = etree.SubElement(tm, etree.QName(typed_element_qname.namespace, typed_element_qname.local_name))
            typed_el.text = typed_value

    return ctx_el


def _fill_period(period_el: etree._Element, period: ReportingPeriod) -> None:
    if period.period_type == "instant":
        inst_el = etree.SubElement(period_el, f"{{{XBRLI_NS}}}instant")
        inst_el.text = _date_str(period.instant_date)
    else:
        start_el = etree.SubElement(period_el, f"{{{XBRLI_NS}}}startDate")
        start_el.text = _date_str(period.start_date)
        end_el = etree.SubElement(period_el, f"{{{XBRLI_NS}}}endDate")
        end_el.text = _date_str(period.end_date)


def _build_unit_el(unit: XbrlUnit) -> etree._Element:
    """Build a <xbrli:unit> element."""
    unit_el = etree.Element(f"{{{XBRLI_NS}}}unit", attrib={"id": unit.unit_id})
    measure_el = etree.SubElement(unit_el, f"{{{XBRLI_NS}}}measure")

    mq = unit.measure_qname
    if mq is not None:
        if mq.namespace == ISO4217_NS:
            measure_el.text = f"iso4217:{mq.local_name}"
        elif mq.namespace == XBRLI_NS:
            measure_el.text = f"xbrli:{mq.local_name}"
        else:
            measure_el.text = str(mq) if mq.namespace else mq.local_name
        return unit_el

    # Normalise measure URI to prefixed form if possible
    measure_uri = unit.measure_uri
    if measure_uri.startswith(ISO4217_NS + ":"):
        currency = measure_uri[len(ISO4217_NS) + 1:]
        measure_el.text = f"iso4217:{currency}"
    elif measure_uri.startswith(XBRLI_NS + ":"):
        local = measure_uri[len(XBRLI_NS) + 1:]
        measure_el.text = f"xbrli:{local}"
    else:
        measure_el.text = measure_uri

    return unit_el


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
        instance.bde_preambulo.entidad_presentadora
        if instance.bde_preambulo is not None
        else ""
    )
    tipo_envio = (
        instance.bde_preambulo.tipo_envio
        if instance.bde_preambulo is not None
        else ""
    )
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
            root.append(_build_context_el(ctx, ns_to_prefix))

        # 4. Units — sorted by unit_id
        for unit in sorted(instance.units.values(), key=lambda u: u.unit_id):
            root.append(_build_unit_el(unit))

        # 5. Filing indicators wrapper
        # BDE instances encode filing-indicator semantics in EstadosReportados,
        # so avoid writing a second Eurofiling wrapper during round-trip.
        use_eurofiling_indicators = not (
            (bde_preambulo_for_save is not None and bde_preambulo_for_save.estados_reportados)
            or is_bde_schema_ref(instance.schema_ref_href)
        )
        if use_eurofiling_indicators and instance.filing_indicators:
            fi_wrapper = etree.SubElement(
                root, f"{{{FILING_IND_NS}}}fIndicators"
            )
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

        # 6. Known facts
        for fact in instance.facts:
            concept_qname = fact.concept
            tag = (
                f"{{{concept_qname.namespace}}}{concept_qname.local_name}"
                if concept_qname.namespace
                else concept_qname.local_name
            )
            attrib: dict[str, str] = {"contextRef": fact.context_ref}
            if fact.unit_ref:
                attrib["unitRef"] = fact.unit_ref
            if fact.decimals is not None:
                attrib["decimals"] = fact.decimals
            elif fact.precision is not None:
                attrib["precision"] = fact.precision
            fact_el = etree.SubElement(root, tag, attrib=attrib)
            fact_el.text = fact.value

        # 7. Orphaned facts — preserved verbatim in original document order
        for orphan in instance.orphaned_facts:
            orphan_el = etree.fromstring(orphan.raw_element_xml)  # noqa: S320
            root.append(orphan_el)

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
        xml_bytes = self.to_xml(instance)
        try:
            path.write_bytes(xml_bytes)
        except OSError as exc:
            raise InstanceSaveError(path=str(path), reason=str(exc)) from exc
        instance.mark_saved(path)

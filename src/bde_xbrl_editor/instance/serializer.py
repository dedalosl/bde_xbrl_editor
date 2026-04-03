"""InstanceSerializer — converts XbrlInstance to well-formed XBRL 2.1 XML."""

from __future__ import annotations

from pathlib import Path

from lxml import etree

from bde_xbrl_editor.instance.constants import (
    FILING_IND_NS,
    FILING_IND_PFX,
    ISO4217_NS,
    LINK_NS,
    XBRLDI_NS,
    XBRLI_NS,
    XLINK_NS,
)
from bde_xbrl_editor.instance.models import (
    InstanceSaveError,
    ReportingPeriod,
    XbrlContext,
    XbrlInstance,
    XbrlUnit,
)

# Standard namespace map declared on the root element
_BASE_NSMAP: dict[str, str] = {
    "xbrli": XBRLI_NS,
    "link": LINK_NS,
    "xlink": XLINK_NS,
    "xbrldi": XBRLDI_NS,
    "iso4217": ISO4217_NS,
    FILING_IND_PFX: FILING_IND_NS,
}

_XLINK_HREF = f"{{{XLINK_NS}}}href"
_XLINK_TYPE = f"{{{XLINK_NS}}}type"
_XLINK_ARCROLE = f"{{{XLINK_NS}}}arcrole"


def _date_str(d) -> str:  # type: ignore[no-untyped-def]
    """Format a date as YYYY-MM-DD."""
    return d.strftime("%Y-%m-%d")


def _build_context_el(ctx: XbrlContext) -> etree._Element:
    """Build a single <xbrli:context> element."""
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

    # <xbrli:scenario> or <xbrli:segment> with xbrldi:explicitMember children
    if ctx.dimensions:
        container_tag = (
            f"{{{XBRLI_NS}}}scenario"
            if ctx.context_element == "scenario"
            else f"{{{XBRLI_NS}}}segment"
        )
        container_el = etree.SubElement(ctx_el, container_tag)
        for dim_qname, member_qname in sorted(
            ctx.dimensions.items(), key=lambda kv: str(kv[0])
        ):
            em = etree.SubElement(
                container_el,
                f"{{{XBRLDI_NS}}}explicitMember",
                attrib={"dimension": str(dim_qname)},
            )
            em.text = str(member_qname)

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


class InstanceSerializer:
    """Serialises an XbrlInstance to XBRL 2.1 XML bytes or writes to disk."""

    def to_xml(self, instance: XbrlInstance) -> bytes:
        """Produce well-formed XBRL 2.1 XML bytes without writing to disk.

        The output is always deterministic for the same instance state.
        """
        # Build namespace map — include concept namespaces from taxonomy entry point
        nsmap: dict[str | None, str] = dict(_BASE_NSMAP)  # type: ignore[arg-type]

        # Root element
        root = etree.Element(f"{{{XBRLI_NS}}}xbrl", nsmap=nsmap)

        # 1. schemaRef
        schema_ref = etree.SubElement(root, f"{{{LINK_NS}}}schemaRef")
        schema_ref.set(_XLINK_HREF, instance.schema_ref_href)
        schema_ref.set(_XLINK_TYPE, "simple")
        schema_ref.set(
            _XLINK_ARCROLE,
            "http://www.xbrl.org/2003/arcrole/facet-equivalence",
        )

        # 2. Contexts — sorted by context_id for determinism
        for ctx in sorted(instance.contexts.values(), key=lambda c: c.context_id):
            root.append(_build_context_el(ctx))

        # 3. Units — sorted by unit_id
        for unit in sorted(instance.units.values(), key=lambda u: u.unit_id):
            root.append(_build_unit_el(unit))

        # 4. Filing indicators wrapper
        if instance.filing_indicators:
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

        # 5. Known facts
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

        # 6. Orphaned facts — preserved verbatim in original document order
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

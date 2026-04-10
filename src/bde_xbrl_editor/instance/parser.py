"""InstanceParser — reads an XBRL 2.1 XML file into a populated XbrlInstance."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from lxml import etree

from bde_xbrl_editor.instance.constants import (
    BDE_PBLO_NS,
    FILING_IND_NS,
    LINK_NS,
    XBRLDI_NS,
    XBRLI_NS,
    XLINK_NS,
)
from bde_xbrl_editor.instance.models import (
    BdeCodigoEstado,
    BdePreambulo,
    ContextId,
    Fact,
    FilingIndicator,
    InstanceParseError,
    OrphanedFact,
    ReportingEntity,
    ReportingPeriod,
    TaxonomyResolutionError,
    UnitId,
    XbrlContext,
    XbrlInstance,
    XbrlUnit,
)
from bde_xbrl_editor.taxonomy.models import QName

if TYPE_CHECKING:
    from bde_xbrl_editor.taxonomy.loader import TaxonomyLoader
    from bde_xbrl_editor.taxonomy.models import TaxonomyStructure

# lxml Clark-notation tag helpers
_XBRLI_XBRL = f"{{{XBRLI_NS}}}xbrl"
_LINK_SCHEMA_REF = f"{{{LINK_NS}}}schemaRef"
_XBRLI_CONTEXT = f"{{{XBRLI_NS}}}context"
_XBRLI_UNIT = f"{{{XBRLI_NS}}}unit"
_XBRLI_ENTITY = f"{{{XBRLI_NS}}}entity"
_XBRLI_IDENTIFIER = f"{{{XBRLI_NS}}}identifier"
_XBRLI_PERIOD = f"{{{XBRLI_NS}}}period"
_XBRLI_INSTANT = f"{{{XBRLI_NS}}}instant"
_XBRLI_START = f"{{{XBRLI_NS}}}startDate"
_XBRLI_END = f"{{{XBRLI_NS}}}endDate"
_XBRLI_MEASURE = f"{{{XBRLI_NS}}}measure"
_XBRLI_SCENARIO = f"{{{XBRLI_NS}}}scenario"
_XBRLI_SEGMENT = f"{{{XBRLI_NS}}}segment"
_XBRLDI_MEMBER = f"{{{XBRLDI_NS}}}explicitMember"
_XBRLDI_TYPED_MEMBER = f"{{{XBRLDI_NS}}}typedMember"
_FILING_IND = f"{{{FILING_IND_NS}}}filingIndicator"
_XLINK_HREF = f"{{{XLINK_NS}}}href"
_XLINK_TYPE = f"{{{XLINK_NS}}}type"

# BDE IE_2008_02 preamble tag constants
_BDE_PBLO_ENTIDAD = f"{{{BDE_PBLO_NS}}}EntidadPresentadora"
_BDE_PBLO_TIPO_ENVIO = f"{{{BDE_PBLO_NS}}}TipoEnvio"
_BDE_PBLO_ESTADOS = f"{{{BDE_PBLO_NS}}}EstadosReportados"
_BDE_PBLO_CODIGO = f"{{{BDE_PBLO_NS}}}CodigoEstado"
_BDE_PBLO_BLANCO = f"{{{BDE_PBLO_NS}}}blanco"

# Known non-fact tags (skipped when iterating facts)
_NON_FACT_TAGS = frozenset([
    _LINK_SCHEMA_REF,
    _XBRLI_CONTEXT,
    _XBRLI_UNIT,
    _FILING_IND,
    f"{{{FILING_IND_NS}}}fIndicators",
    _BDE_PBLO_ENTIDAD,
    _BDE_PBLO_TIPO_ENVIO,
    _BDE_PBLO_ESTADOS,
])


def _parse_date(text: str) -> date:
    return date.fromisoformat(text.strip())


def _parse_context(el: etree._Element) -> XbrlContext:
    """Parse a single xbrli:context element into an XbrlContext."""
    context_id: ContextId = el.get("id", "")

    entity_el = el.find(_XBRLI_ENTITY)
    if entity_el is None:
        raise InstanceParseError("", f"context '{context_id}' missing xbrli:entity")
    id_el = entity_el.find(_XBRLI_IDENTIFIER)
    if id_el is None:
        raise InstanceParseError("", f"context '{context_id}' missing xbrli:identifier")
    identifier = id_el.text or ""
    scheme = id_el.get("scheme", "")
    entity = ReportingEntity(identifier=identifier, scheme=scheme)

    period_el = el.find(_XBRLI_PERIOD)
    if period_el is None:
        raise InstanceParseError("", f"context '{context_id}' missing xbrli:period")
    instant_el = period_el.find(_XBRLI_INSTANT)
    if instant_el is not None:
        period = ReportingPeriod(
            period_type="instant",
            instant_date=_parse_date(instant_el.text or ""),
        )
    else:
        start_el = period_el.find(_XBRLI_START)
        end_el = period_el.find(_XBRLI_END)
        period = ReportingPeriod(
            period_type="duration",
            start_date=_parse_date((start_el.text or "") if start_el is not None else ""),
            end_date=_parse_date((end_el.text or "") if end_el is not None else ""),
        )

    # Parse explicit and typed dimensions from scenario/segment.
    # Dimensions must be unique across BOTH segment and scenario combined.
    # NOTE: scenario is a direct child of context; segment is inside entity.
    dimensions: dict[QName, QName] = {}
    context_element: str = "scenario"
    _segment_container = entity_el.find(_XBRLI_SEGMENT) if entity_el is not None else None
    _containers: list[tuple[etree._Element, str]] = []
    if el.find(_XBRLI_SCENARIO) is not None:
        _containers.append((el.find(_XBRLI_SCENARIO), "scenario"))
    if _segment_container is not None:
        _containers.append((_segment_container, "segment"))
    for container, _ce in _containers:
        if _ce == "segment":
            context_element = "segment"
        # Explicit dimensions
        for member_el in container.findall(_XBRLDI_MEMBER):
            dim_str = member_el.get("dimension", "")
            mem_str = (member_el.text or "").strip()
            if dim_str and mem_str:
                try:
                    dim_clark = _resolve_prefixed_qname(member_el, dim_str)
                    mem_clark = _resolve_prefixed_qname(member_el, mem_str)
                    dim_qname = QName.from_clark(dim_clark)
                    if dim_qname in dimensions:
                        raise InstanceParseError(
                            "",
                            f"xbrldie:RepeatedDimensionInInstanceError: "
                            f"Dimension {dim_qname} appears more than once in "
                            f"context '{context_id}'",
                        )
                    dimensions[dim_qname] = QName.from_clark(mem_clark)
                except InstanceParseError:
                    raise
                except Exception:  # noqa: BLE001
                    pass
        # Typed dimensions (value is an XML child, not text)
        for member_el in container.findall(_XBRLDI_TYPED_MEMBER):
            dim_str = member_el.get("dimension", "")
            if dim_str:
                try:
                    dim_clark = _resolve_prefixed_qname(member_el, dim_str)
                    dim_qname = QName.from_clark(dim_clark)
                    if dim_qname in dimensions:
                        raise InstanceParseError(
                            "",
                            f"xbrldie:RepeatedDimensionInInstanceError: "
                            f"Dimension {dim_qname} appears more than once in "
                            f"context '{context_id}'",
                        )
                    # Use dim_qname itself as placeholder value for typed members
                    dimensions[dim_qname] = dim_qname
                except InstanceParseError:
                    raise
                except Exception:  # noqa: BLE001
                    pass

    return XbrlContext(
        context_id=context_id,
        entity=entity,
        period=period,
        dimensions=dimensions,
        context_element=context_element,  # type: ignore[arg-type]
    )


def _parse_unit(el: etree._Element) -> XbrlUnit:
    """Parse a single xbrli:unit element into an XbrlUnit."""
    unit_id: UnitId = el.get("id", "")
    measure_el = el.find(_XBRLI_MEASURE)
    measure_uri = (measure_el.text or "").strip() if measure_el is not None else ""
    return XbrlUnit(unit_id=unit_id, measure_uri=measure_uri)


def _resolve_prefixed_qname(el: etree._Element, prefixed: str) -> str:
    """Resolve a QName string to Clark notation using element namespace map.

    Handles both standard prefix:local notation and Clark {namespace}local notation
    (written by the serializer when the QName has no prefix).
    """
    if prefixed.startswith("{"):
        return prefixed  # Already Clark notation — pass through unchanged
    if ":" in prefixed:
        prefix, local = prefixed.split(":", 1)
        nsmap = el.nsmap or {}
        ns = nsmap.get(prefix, "")
        return f"{{{ns}}}{local}" if ns else local
    return prefixed


def _tag_to_qname(tag: str) -> QName:
    """Convert Clark notation to QName."""
    return QName.from_clark(tag)


class InstanceParser:
    """Parses an XBRL 2.1 XML file into a populated XbrlInstance."""

    def __init__(
        self,
        taxonomy_loader: TaxonomyLoader,
        manual_taxonomy_resolver: Callable[[str], Path | None] | None = None,
    ) -> None:
        self._loader = taxonomy_loader
        self._resolver = manual_taxonomy_resolver

    def load(self, path: str | Path) -> tuple[XbrlInstance, list[OrphanedFact]]:
        """Parse the XBRL instance at path and return (XbrlInstance, orphaned_facts).

        Raises:
            InstanceParseError: XML not well-formed or missing mandatory elements.
            TaxonomyResolutionError: schemaRef cannot be resolved.
        """
        path = Path(path)
        path_str = str(path)

        # Stage 1: Parse XML and validate root
        try:
            tree = etree.parse(str(path))  # noqa: S320
            root = tree.getroot()
        except etree.XMLSyntaxError as exc:
            raise InstanceParseError(path_str, f"XML syntax error: {exc}") from exc

        if root.tag != _XBRLI_XBRL:
            raise InstanceParseError(
                path_str,
                f"Root element must be xbrli:xbrl, got '{root.tag}'",
            )

        # Stage 2: Extract schemaRef and load taxonomy
        schema_ref_el = root.find(_LINK_SCHEMA_REF)
        if schema_ref_el is None:
            raise InstanceParseError(path_str, "Missing link:schemaRef element")
        schema_href = schema_ref_el.get(_XLINK_HREF, "")
        if not schema_href:
            raise InstanceParseError(path_str, "link:schemaRef missing xlink:href")

        taxonomy = self._resolve_taxonomy(path, schema_href, path_str)

        # Stage 3: Parse contexts
        contexts: dict[ContextId, XbrlContext] = {}
        for ctx_el in root.findall(_XBRLI_CONTEXT):
            try:
                ctx = _parse_context(ctx_el)
                contexts[ctx.context_id] = ctx
            except Exception as exc:  # noqa: BLE001
                raise InstanceParseError(path_str, f"Context parse error: {exc}") from exc

        # Extract entity/period from first context (or default)
        if contexts:
            first_ctx = next(iter(contexts.values()))
            instance_entity = first_ctx.entity
            instance_period = first_ctx.period
        else:
            # Fallback: minimal entity/period — will be overridden if contexts exist
            instance_entity = ReportingEntity(identifier="unknown", scheme="http://unknown")
            instance_period = ReportingPeriod(
                period_type="instant", instant_date=date.today()
            )

        # Stage 4: Parse units
        units: dict[UnitId, XbrlUnit] = {}
        for unit_el in root.findall(_XBRLI_UNIT):
            unit = _parse_unit(unit_el)
            units[unit.unit_id] = unit

        # Stage 4b: Parse BDE preamble (EntidadPresentadora, TipoEnvio, EstadosReportados)
        preambulo = _parse_preambulo(root)

        # Stage 5: Parse filing indicators
        filing_indicators: list[FilingIndicator] = []
        # They may be inside ef-find:fIndicators wrapper or directly as children
        for child in root:
            if not isinstance(child.tag, str):  # skip comments / PIs
                continue
            local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            ns = child.tag.split("}")[0][1:] if "}" in child.tag else ""
            if ns == FILING_IND_NS and local == "fIndicators":
                for fi_el in child:
                    _parse_filing_indicator(fi_el, filing_indicators)
            elif child.tag == _FILING_IND:
                _parse_filing_indicator(child, filing_indicators)

        # Stages 6–7: Parse facts
        facts: list[Fact] = []
        orphaned: list[OrphanedFact] = []
        known_concepts = taxonomy.concepts if taxonomy else {}

        for child in root:
            if not isinstance(child.tag, str):  # skip comments / PIs
                continue
            if child.tag in _NON_FACT_TAGS:
                continue
            # Skip fIndicators wrapper
            local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            ns = child.tag.split("}")[0][1:] if "}" in child.tag else ""
            if ns == FILING_IND_NS:
                continue
            if child.tag == _LINK_SCHEMA_REF:
                continue

            # It's a fact element
            context_ref = child.get("contextRef", "")
            unit_ref = child.get("unitRef")
            decimals = child.get("decimals")
            precision = child.get("precision")
            value = (child.text or "").strip()

            concept_tag = child.tag
            try:
                concept_qname = _tag_to_qname(concept_tag)
            except Exception:  # noqa: BLE001
                continue

            if concept_qname in known_concepts:
                facts.append(Fact(
                    concept=concept_qname,
                    context_ref=context_ref,
                    unit_ref=unit_ref,
                    value=value,
                    decimals=decimals,
                    precision=precision,
                ))
            else:
                raw_xml = etree.tostring(child, encoding="unicode").encode("utf-8")
                orphaned.append(OrphanedFact(
                    concept_qname_str=concept_tag,
                    context_ref=context_ref,
                    unit_ref=unit_ref,
                    value=value,
                    decimals=decimals,
                    raw_element_xml=raw_xml,
                ))

        # Build the XbrlInstance
        instance = XbrlInstance(
            taxonomy_entry_point=taxonomy.metadata.entry_point_path if taxonomy else path,
            schema_ref_href=schema_href,
            entity=instance_entity,
            period=instance_period,
            preambulo=preambulo,
            filing_indicators=filing_indicators,
            included_table_ids=[fi.template_id for fi in filing_indicators if fi.filed],
            contexts=contexts,
            units=units,
            facts=facts,
            orphaned_facts=orphaned,
            source_path=path,
            _dirty=False,
        )

        return instance, orphaned

    def _resolve_taxonomy(
        self, instance_path: Path, schema_href: str, path_str: str
    ) -> TaxonomyStructure:
        """Resolve the schemaRef href to a taxonomy path and load it."""
        # Try relative to instance file directory first
        if not schema_href.startswith(("http://", "https://", "/")):
            candidate = instance_path.parent / schema_href
            if candidate.exists():
                return self._loader.load(candidate)

        # Try catalog resolution for remote URLs (same catalog used for taxonomy loading)
        from bde_xbrl_editor.taxonomy.discovery import _is_remote, _resolve_href  # noqa: PLC0415
        if _is_remote(schema_href):
            resolved = _resolve_href(schema_href, instance_path.parent, self._loader.settings)
            if resolved is not None and resolved.exists():
                return self._loader.load(resolved)

        # Try absolute path
        abs_candidate = Path(schema_href)
        if abs_candidate.exists():
            return self._loader.load(abs_candidate)

        # Fall back to manual resolver
        if self._resolver is not None:
            resolved = self._resolver(schema_href)
            if resolved is not None and resolved.exists():
                return self._loader.load(resolved)

        raise TaxonomyResolutionError(
            schema_href,
            f"Could not find taxonomy at '{schema_href}' relative to '{instance_path.parent}'",
        )


def _parse_filing_indicator(el: etree._Element, out: list[FilingIndicator]) -> None:
    if el.tag != _FILING_IND:
        return
    context_ref = el.get("contextRef", "")
    filed_str = el.get("filed", "true").lower()
    filed = filed_str in ("true", "1", "yes")
    template_id = (el.text or "").strip()
    if template_id:
        out.append(FilingIndicator(
            template_id=template_id,
            filed=filed,
            context_ref=context_ref,
        ))


def _parse_preambulo(root: etree._Element) -> BdePreambulo | None:
    """Extract BDE IE_2008_02 preamble elements from the root xbrli:xbrl element.

    Looks for direct children:
    - ``es-be-cm-pblo:EntidadPresentadora``
    - ``es-be-cm-pblo:TipoEnvio``
    - ``es-be-cm-pblo:EstadosReportados`` (contains ``CodigoEstado`` children)

    Returns ``None`` when none of these elements are present (non-BDE instance).
    """
    entidad: str = ""
    entidad_ctx: str = ""
    tipo_envio: str = ""
    tipo_envio_ctx: str = ""
    estados: list[BdeCodigoEstado] = []

    found_any = False
    for child in root:
        if not isinstance(child.tag, str):
            continue
        if child.tag == _BDE_PBLO_ENTIDAD:
            found_any = True
            entidad = (child.text or "").strip()
            entidad_ctx = child.get("contextRef", "")
        elif child.tag == _BDE_PBLO_TIPO_ENVIO:
            found_any = True
            tipo_envio = (child.text or "").strip()
            tipo_envio_ctx = child.get("contextRef", "")
        elif child.tag == _BDE_PBLO_ESTADOS:
            found_any = True
            for codigo_el in child:
                if not isinstance(codigo_el.tag, str):
                    continue
                if codigo_el.tag != _BDE_PBLO_CODIGO:
                    continue
                codigo = (codigo_el.text or "").strip()
                if not codigo:
                    continue
                blanco_val = codigo_el.get(_BDE_PBLO_BLANCO, "false").lower()
                blanco = blanco_val in ("true", "1", "yes")
                estados.append(BdeCodigoEstado(
                    codigo=codigo,
                    blanco=blanco,
                    context_ref=codigo_el.get("contextRef", ""),
                ))

    if not found_any:
        return None

    return BdePreambulo(
        entidad_presentadora=entidad,
        entidad_context_ref=entidad_ctx,
        tipo_envio=tipo_envio,
        tipo_envio_context_ref=tipo_envio_ctx,
        estados_reportados=estados,
    )

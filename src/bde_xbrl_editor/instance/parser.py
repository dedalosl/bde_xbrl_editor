"""InstanceParser — reads an XBRL 2.1 XML file into a populated XbrlInstance."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
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
    BdeEstadoReportado,
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
from bde_xbrl_editor.instance.s_equal import build_s_equal_key_from_xml_fragments
from bde_xbrl_editor.taxonomy.models import QName
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file

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
_XBRLI_DIVIDE = f"{{{XBRLI_NS}}}divide"
_XBRLI_SCENARIO = f"{{{XBRLI_NS}}}scenario"
_XBRLI_SEGMENT = f"{{{XBRLI_NS}}}segment"
_XBRLDI_MEMBER = f"{{{XBRLDI_NS}}}explicitMember"
_XBRLDI_TYPED_MEMBER = f"{{{XBRLDI_NS}}}typedMember"
_FILING_IND = f"{{{FILING_IND_NS}}}filingIndicator"
_XLINK_HREF = f"{{{XLINK_NS}}}href"
_XLINK_TYPE = f"{{{XLINK_NS}}}type"
_LINK_FOOTNOTE_LINK = f"{{{LINK_NS}}}footnoteLink"
_LINK_LOC = f"{{{LINK_NS}}}loc"
_LINK_FOOTNOTE = f"{{{LINK_NS}}}footnote"
_LINK_FOOTNOTE_ARC = f"{{{LINK_NS}}}footnoteArc"
_LINK_DOCUMENTATION = f"{{{LINK_NS}}}documentation"
_ARCROLE_FACT_FOOTNOTE = "http://www.xbrl.org/2003/arcrole/fact-footnote"
_XLINK_LABEL = f"{{{XLINK_NS}}}label"
_XLINK_FROM = f"{{{XLINK_NS}}}from"
_XLINK_TO = f"{{{XLINK_NS}}}to"
_XLINK_ARCROLE = f"{{{XLINK_NS}}}arcrole"
_FOOTNOTE_LINK_ALLOWED_CHILD = frozenset(
    {
        _LINK_LOC,
        _LINK_FOOTNOTE,
        _LINK_FOOTNOTE_ARC,
        _LINK_DOCUMENTATION,
    }
)

# BDE IE_2008_02 preamble Clark-notation tags
_BDE_ENTIDAD = f"{{{BDE_PBLO_NS}}}EntidadPresentadora"
_BDE_TIPO_ENVIO = f"{{{BDE_PBLO_NS}}}TipoEnvio"
_BDE_ESTADOS_REPORTADOS = f"{{{BDE_PBLO_NS}}}EstadosReportados"
_BDE_CODIGO_ESTADO = f"{{{BDE_PBLO_NS}}}CodigoEstado"

# Known non-fact tags (skipped when iterating facts)
# All es-be-cm-pblo namespace elements are BDE preamble data, not XBRL facts.
_NON_FACT_TAGS = frozenset(
    [
        _LINK_SCHEMA_REF,
        _XBRLI_CONTEXT,
        _XBRLI_UNIT,
        _FILING_IND,
        f"{{{FILING_IND_NS}}}fIndicators",
        _BDE_ENTIDAD,
        _BDE_TIPO_ENVIO,
        _BDE_ESTADOS_REPORTADOS,
        _LINK_FOOTNOTE_LINK,
        _LINK_LOC,
        _LINK_FOOTNOTE,
        _LINK_FOOTNOTE_ARC,
    ]
)


def _catalog_path_candidates(local_root: Path, rel: str) -> list[Path]:
    """Return local-cache candidates for a remote schemaRef suffix.

    Banco de Espana schemaRef URLs can use ``/es/fr/xbrl/...`` while the local
    cache stores the same DTS under ``/es/xbrl/...``.  Prefer the direct mapping
    and fall back to the normalized cache path when needed.
    """
    rel = rel.lstrip("/")
    candidates = [(local_root / rel).resolve()]

    parts = Path(rel).parts
    if len(parts) >= 3 and parts[1] == "fr" and parts[2] == "xbrl":
        alt_rel = Path(parts[0], *parts[2:])
        alt_candidate = (local_root / alt_rel).resolve()
        if alt_candidate not in candidates:
            candidates.append(alt_candidate)

    return candidates


def _reject_xbrli_in_segment_or_scenario(container: etree._Element, context_id: ContextId) -> None:
    """XBRL 2.1: segment and scenario open content must not use xbrli:* elements."""
    for el in container.iter():
        if el is container:
            continue
        if isinstance(el.tag, str) and el.tag.startswith(f"{{{XBRLI_NS}}}"):
            raise InstanceParseError(
                "",
                f"Illegal element in xbrli namespace inside segment or scenario "
                f"of context '{context_id}' ({el.tag})",
            )


def _parse_date_boundary(text: str, *, date_only_is_end_boundary: bool = False) -> date:
    stripped = text.strip()
    if "T" not in stripped:
        parsed = date.fromisoformat(stripped)
        return parsed + timedelta(days=1) if date_only_is_end_boundary else parsed

    day, time = stripped.split("T", 1)
    parsed = date.fromisoformat(day)
    return parsed + timedelta(days=1) if time.startswith("24:00:00") else parsed


def _parse_date(text: str) -> date:
    stripped = text.strip()
    # XBRL allows ISO 8601 datetime strings for instant dates (e.g. "2009-01-01T00:00:00").
    # The editor model stores dates, so keep the lexical calendar date here and
    # apply end-boundary semantics only to S-equality keys.
    if "T" in stripped:
        stripped = stripped.split("T")[0]
    return date.fromisoformat(stripped)


def _period_s_equal_key(period_el: etree._Element) -> tuple:
    instant_el = period_el.find(_XBRLI_INSTANT)
    if instant_el is not None:
        return (
            "instant",
            _parse_date_boundary(
                instant_el.text or "",
                date_only_is_end_boundary=True,
            ).isoformat(),
        )

    start_el = period_el.find(_XBRLI_START)
    end_el = period_el.find(_XBRLI_END)
    return (
        "duration",
        _parse_date_boundary((start_el.text or "") if start_el is not None else "").isoformat(),
        _parse_date_boundary(
            (end_el.text or "") if end_el is not None else "",
            date_only_is_end_boundary=True,
        ).isoformat(),
    )


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
    typed_dimensions: dict[QName, str] = {}
    typed_dimension_elements: dict[QName, QName] = {}
    dim_containers: dict[QName, str] = {}
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
        _reject_xbrli_in_segment_or_scenario(container, context_id)
        # Explicit dimensions
        for member_el in container.findall(_XBRLDI_MEMBER):
            dim_str = member_el.get("dimension", "")
            mem_str = (member_el.text or "").strip()
            if dim_str and mem_str:
                dim_qname = _parse_dimension_qname(
                    member_el,
                    dim_str,
                    context_id=context_id,
                    role="explicit dimension",
                )
                if dim_qname in dimensions:
                    raise InstanceParseError(
                        "",
                        f"xbrldie:RepeatedDimensionInInstanceError: "
                        f"Dimension {dim_qname} appears more than once in "
                        f"context '{context_id}'",
                    )
                dimensions[dim_qname] = _parse_dimension_qname(
                    member_el,
                    mem_str,
                    context_id=context_id,
                    role=f"explicit dimension member for {dim_str}",
                )
                dim_containers[dim_qname] = _ce
        # Typed dimensions (value is an XML child, not text)
        for member_el in container.findall(_XBRLDI_TYPED_MEMBER):
            dim_str = member_el.get("dimension", "")
            if dim_str:
                dim_qname = _parse_dimension_qname(
                    member_el,
                    dim_str,
                    context_id=context_id,
                    role="typed dimension",
                )
                if dim_qname in dimensions:
                    raise InstanceParseError(
                        "",
                        f"xbrldie:RepeatedDimensionInInstanceError: "
                        f"Dimension {dim_qname} appears more than once in "
                        f"context '{context_id}'",
                    )
                # Preserve typed-member lexical content and child element while also
                # keeping the legacy placeholder in dimensions for validators that
                # still use member_qname == dim_qname to identify typed dimensions.
                dimensions[dim_qname] = dim_qname
                child_el = next((child for child in member_el if isinstance(child.tag, str)), None)
                if child_el is not None:
                    typed_dimensions[dim_qname] = "".join(child_el.itertext()).strip()
                    typed_dimension_elements[dim_qname] = _tag_to_qname(str(child_el.tag))
                else:
                    typed_dimensions[dim_qname] = (member_el.text or "").strip()
                dim_containers[dim_qname] = _ce

    scenario_el = el.find(_XBRLI_SCENARIO)
    segment_el = entity_el.find(_XBRLI_SEGMENT) if entity_el is not None else None
    scenario_xml = (
        etree.tostring(scenario_el, encoding="utf-8", with_tail=False)
        if scenario_el is not None
        else None
    )
    segment_xml = (
        etree.tostring(segment_el, encoding="utf-8", with_tail=False)
        if segment_el is not None
        else None
    )
    s_equal_key = build_s_equal_key_from_xml_fragments(
        entity,
        period,
        scenario_el,
        segment_el,
        period_key=_period_s_equal_key(period_el),
    )

    return XbrlContext(
        context_id=context_id,
        entity=entity,
        period=period,
        dimensions=dimensions,
        typed_dimensions=typed_dimensions,
        typed_dimension_elements=typed_dimension_elements,
        context_element=context_element,  # type: ignore[arg-type]
        dim_containers=dim_containers,  # type: ignore[arg-type]
        s_equal_key=s_equal_key,
        scenario_xml=scenario_xml,
        segment_xml=segment_xml,
    )


def _parse_measure_qname(measure_el: etree._Element, measure_text: str) -> QName | None:
    """Resolve the QName of an xbrli:measure element (prefix or Clark notation)."""
    if not measure_text:
        return None
    if measure_text.startswith("{"):
        return QName.from_clark(measure_text)
    if ":" in measure_text:
        return QName.from_clark(_resolve_prefixed_qname(measure_el, measure_text))
    return QName(namespace="", local_name=measure_text)


def _parse_unit(el: etree._Element) -> XbrlUnit:
    """Parse a single xbrli:unit element into an XbrlUnit."""
    unit_id: UnitId = el.get("id", "")
    children = [c for c in el if isinstance(c.tag, str)]
    has_divide = any(c.tag == _XBRLI_DIVIDE for c in children)
    if has_divide:
        return XbrlUnit(
            unit_id=unit_id,
            measure_uri="",
            measure_qname=None,
            unit_form="divide",
            simple_measure_count=0,
        )

    direct_measures = [c for c in children if c.tag == _XBRLI_MEASURE]
    count = len(direct_measures)
    if count != 1:
        joined = " ".join((m.text or "").strip() for m in direct_measures if (m.text or "").strip())
        return XbrlUnit(
            unit_id=unit_id,
            measure_uri=joined,
            measure_qname=None,
            unit_form="simple",
            simple_measure_count=count,
        )

    measure_el = direct_measures[0]
    measure_uri = (measure_el.text or "").strip()
    mq = _parse_measure_qname(measure_el, measure_uri)
    return XbrlUnit(
        unit_id=unit_id,
        measure_uri=measure_uri,
        measure_qname=mq,
        unit_form="simple",
        simple_measure_count=1,
    )


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


def _parse_dimension_qname(
    el: etree._Element,
    raw_value: str,
    *,
    context_id: ContextId,
    role: str,
) -> QName:
    """Parse a dimension/member QName and surface bad lexical values clearly."""
    value = raw_value.strip()
    try:
        if not value:
            raise ValueError("empty QName")
        if value.startswith("{"):
            qname = QName.from_clark(value)
        elif ":" in value:
            prefix, local = value.split(":", 1)
            namespace = (el.nsmap or {}).get(prefix)
            if not prefix or not local:
                raise ValueError("QName prefix and local name must both be present")
            if namespace is None:
                raise ValueError(f"prefix '{prefix}' is not declared")
            qname = QName(namespace=namespace, local_name=local, prefix=prefix)
        else:
            qname = QName(namespace="", local_name=value)
        if not qname.local_name:
            raise ValueError("QName local name is empty")
        return qname
    except ValueError as exc:
        raise InstanceParseError(
            "",
            f"Invalid {role} QName '{raw_value}' in context '{context_id}': {exc}",
        ) from exc


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

    def load(
        self,
        path: str | Path,
        progress_callback: Callable[[str, int, int], None] | None = None,
        taxonomy_resolved_callback: Callable[[TaxonomyStructure], None] | None = None,
        preloaded_taxonomy: TaxonomyStructure | None = None,
    ) -> tuple[XbrlInstance, list[OrphanedFact]]:
        """Parse the XBRL instance at path and return (XbrlInstance, orphaned_facts).

        Raises:
            InstanceParseError: XML not well-formed or missing mandatory elements.
            TaxonomyResolutionError: schemaRef cannot be resolved.
        """
        path = Path(path)
        path_str = str(path)

        def progress(message: str, current: int, total: int = 100) -> None:
            if progress_callback is not None:
                progress_callback(message, current, total)

        # Stage 1: Parse XML and validate root
        progress("Parsing instance XML…", 5)
        try:
            tree = parse_xml_file(path)
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

        progress("Resolving instance taxonomy…", 12)

        def taxonomy_progress(message: str, current: int, total: int) -> None:
            if total <= 0:
                progress(f"Loading taxonomy… {message}", 45)
                return
            # Map taxonomy loader progress into the middle of the instance load lifecycle.
            mapped = 12 + int((current / total) * 58)
            progress(f"Loading taxonomy… {message}", min(mapped, 70))

        resolved_taxonomy_path = self._resolve_taxonomy_path(path, schema_href)
        if (
            preloaded_taxonomy is not None
            and resolved_taxonomy_path is not None
            and resolved_taxonomy_path == preloaded_taxonomy.metadata.entry_point_path.resolve()
        ):
            progress("Reusing loaded taxonomy…", 22)
            taxonomy = preloaded_taxonomy
        else:
            taxonomy = self._resolve_taxonomy(
                path,
                schema_href,
                path_str,
                progress_callback=taxonomy_progress,
                resolved_taxonomy_path=resolved_taxonomy_path,
            )
        if taxonomy_resolved_callback is not None:
            taxonomy_resolved_callback(taxonomy)
        progress(
            f"Taxonomy ready — {len(taxonomy.tables)} tables, {len(taxonomy.concepts)} concepts",
            72,
        )

        # Stage 3: Parse contexts
        progress("Reading contexts…", 78)
        contexts: dict[ContextId, XbrlContext] = {}
        for ctx_el in root.findall(_XBRLI_CONTEXT):
            try:
                ctx = _parse_context(ctx_el)
                contexts[ctx.context_id] = ctx
            except Exception as exc:  # noqa: BLE001
                raise InstanceParseError(path_str, f"Context parse error: {exc}") from exc
        progress(f"Contexts loaded — {len(contexts)} available", 82)

        # Extract entity/period from first context (or default)
        if contexts:
            first_ctx = next(iter(contexts.values()))
            instance_entity = first_ctx.entity
            instance_period = first_ctx.period
        else:
            # Fallback: minimal entity/period — will be overridden if contexts exist
            instance_entity = ReportingEntity(identifier="unknown", scheme="http://unknown")
            instance_period = ReportingPeriod(period_type="instant", instant_date=date.today())

        # Stage 4: Parse units
        progress("Reading units…", 84)
        units: dict[UnitId, XbrlUnit] = {}
        for unit_el in root.findall(_XBRLI_UNIT):
            unit = _parse_unit(unit_el)
            units[unit.unit_id] = unit
        progress(f"Units loaded — {len(units)} available", 87)

        # Stage 4b: Validate footnote link references and arc from/to constraints
        footnote_errors: list[str] = []
        all_context_ids = set(contexts.keys())
        all_unit_ids = set(units.keys())
        for footnote_link in root.findall(_LINK_FOOTNOTE_LINK):
            loc_labels: dict[str, str] = {}
            footnote_resources: set[str] = set()
            for child_el in footnote_link:
                if not isinstance(child_el.tag, str):
                    continue
                if (
                    child_el.tag not in _FOOTNOTE_LINK_ALLOWED_CHILD
                    and child_el.get(_XLINK_TYPE, "") == "locator"
                ):
                    footnote_errors.append(
                        "Invalid locator in footnote extended link: only link:loc may "
                        f"be used as an xlink:type='locator' child (found '{child_el.tag}')"
                    )
            for loc_el in footnote_link.findall(_LINK_LOC):
                label = loc_el.get(_XLINK_LABEL, "")
                href = loc_el.get(_XLINK_HREF, "")
                if label and href:
                    loc_labels[label] = href
                if href.startswith("#"):
                    target_id = href[1:]
                    if target_id in all_context_ids:
                        footnote_errors.append(
                            f"link:loc xlink:href='{href}' references context element (not allowed)"
                        )
                    elif target_id in all_unit_ids:
                        footnote_errors.append(
                            f"link:loc xlink:href='{href}' references unit element (not allowed)"
                        )
                elif href and "#" in href:
                    doc_part, _ = href.split("#", 1)
                    instance_filename = path.name
                    if doc_part and doc_part != instance_filename:
                        footnote_errors.append(
                            f"link:loc xlink:href='{doc_part}#...' references external document (not allowed)"
                        )
            for fn_el in footnote_link.findall(_LINK_FOOTNOTE):
                label = fn_el.get(_XLINK_LABEL, "")
                if label:
                    footnote_resources.add(label)
                if fn_el.get("{http://www.w3.org/XML/1998/namespace}lang") is None:
                    footnote_errors.append("link:footnote is missing required xml:lang attribute")
            endpoint_labels = set(loc_labels) | footnote_resources
            for arc_el in footnote_link.findall(_LINK_FOOTNOTE_ARC):
                arcrole = arc_el.get(_XLINK_ARCROLE, "")
                arc_from = arc_el.get(_XLINK_FROM, "")
                arc_to = arc_el.get(_XLINK_TO, "")
                if arcrole == _ARCROLE_FACT_FOOTNOTE:
                    if arc_from and arc_from not in loc_labels:
                        footnote_errors.append(
                            f"link:footnoteArc xlink:from='{arc_from}' does not match any loc xlink:label in the same extended link"
                        )
                    if arc_to and arc_to not in footnote_resources:
                        footnote_errors.append(
                            f"link:footnoteArc xlink:to='{arc_to}' does not match any footnote xlink:label in the same extended link"
                        )
                else:
                    if arc_from and arc_from not in endpoint_labels:
                        footnote_errors.append(
                            f"link:footnoteArc xlink:from='{arc_from}' does not match any "
                            "loc or footnote xlink:label in the same extended link"
                        )
                    if arc_to and arc_to not in endpoint_labels:
                        footnote_errors.append(
                            f"link:footnoteArc xlink:to='{arc_to}' does not match any "
                            "loc or footnote xlink:label in the same extended link"
                        )
        if footnote_errors:
            raise InstanceParseError(
                path_str, "xbrli:InvalidFootnoteLinkReference: " + "; ".join(footnote_errors)
            )

        # Stage 5: Scan top-level children without materialising a second list of
        # elements. Large filings can have many fact elements under the root.
        total_root_children = sum(1 for child in root if isinstance(child.tag, str))
        if total_root_children:
            progress(f"Reading filing metadata… 0/{total_root_children}", 88)
        else:
            progress("Reading filing metadata… none found", 88)

        entidad = ""
        tipo_envio = ""
        estados: list[BdeEstadoReportado] = []
        preambulo_context_ref = ""
        found_preambulo = False
        filing_indicators: list[FilingIndicator] = []
        facts: list[Fact] = []
        orphaned: list[OrphanedFact] = []
        known_concepts = taxonomy.concepts if taxonomy else {}
        facts_seen = 0

        metadata_progress_every = max(total_root_children // 20, 1) if total_root_children else 1
        blanco_attr = f"{{{BDE_PBLO_NS}}}blanco"

        index = 0
        for child in root:
            if not isinstance(child.tag, str):
                continue
            index += 1
            tag = child.tag

            if tag == _BDE_ENTIDAD:
                found_preambulo = True
                entidad = (child.text or "").strip()
                preambulo_context_ref = preambulo_context_ref or child.get("contextRef", "")
            elif tag == _BDE_TIPO_ENVIO:
                found_preambulo = True
                tipo_envio = (child.text or "").strip()
                preambulo_context_ref = preambulo_context_ref or child.get("contextRef", "")
            elif tag == _BDE_ESTADOS_REPORTADOS:
                found_preambulo = True
                for estado_el in child:
                    if not isinstance(estado_el.tag, str) or estado_el.tag != _BDE_CODIGO_ESTADO:
                        continue
                    codigo = (estado_el.text or "").strip()
                    if not codigo:
                        continue
                    blanco_val = estado_el.get(blanco_attr, "false").lower()
                    estado_ctx = estado_el.get("contextRef", "") or preambulo_context_ref
                    estados.append(
                        BdeEstadoReportado(
                            codigo=codigo,
                            blanco=blanco_val in ("true", "1", "yes"),
                            context_ref=estado_ctx,
                        )
                    )
            else:
                local = tag.split("}")[-1] if "}" in tag else tag
                ns = tag.split("}")[0][1:] if "}" in tag else ""
                if ns == FILING_IND_NS and local == "fIndicators":
                    for fi_el in child:
                        _parse_filing_indicator(fi_el, filing_indicators)
                elif tag == _FILING_IND:
                    _parse_filing_indicator(child, filing_indicators)

                if (
                    tag not in _NON_FACT_TAGS
                    and ns not in (FILING_IND_NS, BDE_PBLO_NS)
                    and tag != _LINK_SCHEMA_REF
                    and "contextRef" in child.attrib
                ):
                    facts_seen += 1
                    context_ref = child.get("contextRef", "")
                    unit_ref = child.get("unitRef")
                    decimals = child.get("decimals")
                    precision = child.get("precision")
                    value = (child.text or "").strip()

                    concept_tag = child.tag
                    try:
                        concept_qname = _tag_to_qname(concept_tag)
                    except ValueError as exc:
                        raise InstanceParseError(
                            path_str,
                            f"Fact QName parse error in context '{context_ref}' "
                            f"for element '{concept_tag}': {exc}",
                        ) from exc

                    if concept_qname in known_concepts:
                        facts.append(
                            Fact(
                                concept=concept_qname,
                                context_ref=context_ref,
                                unit_ref=unit_ref,
                                value=value,
                                decimals=decimals,
                                precision=precision,
                            )
                        )
                    else:
                        raw_xml = etree.tostring(child, encoding="unicode").encode("utf-8")
                        orphaned.append(
                            OrphanedFact(
                                concept_qname_str=concept_tag,
                                context_ref=context_ref,
                                unit_ref=unit_ref,
                                value=value,
                                decimals=decimals,
                                raw_element_xml=raw_xml,
                            )
                        )

            if total_root_children and (
                index == total_root_children or index == 1 or index % metadata_progress_every == 0
            ):
                mapped_progress = 88 + int((index / total_root_children) * 11)
                if facts_seen > 0:
                    message = f"Reading facts… {facts_seen} parsed"
                else:
                    message = f"Reading filing metadata… {index}/{total_root_children}"
                progress(
                    message,
                    min(mapped_progress, 99),
                )

        bde_preambulo = None
        if found_preambulo:
            bde_preambulo = BdePreambulo(
                entidad_presentadora=entidad,
                tipo_envio=tipo_envio,
                estados_reportados=estados,
                context_ref=preambulo_context_ref,
            )

        # BDE instances encode filing-indicator semantics with CodigoEstado
        # values, so prefer those and only fall back to Eurofiling wrappers.
        if bde_preambulo is not None and bde_preambulo.estados_reportados:
            filing_indicators = _parse_bde_filing_indicators(bde_preambulo)
        progress(
            f"Filing indicators ready — {len(filing_indicators)} found",
            99 if total_root_children else 92,
        )
        progress(
            f"Facts indexed — {len(facts)} resolved, {len(orphaned)} orphaned",
            99,
        )

        # Build the XbrlInstance
        instance = XbrlInstance(
            taxonomy_entry_point=taxonomy.metadata.entry_point_path if taxonomy else path,
            schema_ref_href=schema_href,
            entity=instance_entity,
            period=instance_period,
            filing_indicators=filing_indicators,
            included_table_ids=[fi.template_id for fi in filing_indicators if fi.filed],
            contexts=contexts,
            units=units,
            facts=facts,
            orphaned_facts=orphaned,
            bde_preambulo=bde_preambulo,
            source_path=path,
            _dirty=False,
        )

        progress("Instance parsed successfully", 99)
        return instance, orphaned

    def _resolve_taxonomy_path(
        self,
        instance_path: Path,
        schema_href: str,
    ) -> Path | None:
        """Resolve schemaRef href to a local taxonomy path when possible."""
        is_remote = schema_href.startswith(("http://", "https://"))

        if not is_remote and not schema_href.startswith("/"):
            candidate = (instance_path.parent / schema_href).resolve()
            if candidate.exists():
                return candidate

        if not is_remote:
            abs_candidate = Path(schema_href).resolve()
            if abs_candidate.exists():
                return abs_candidate

        if is_remote:
            catalog = self._loader.settings.local_catalog
            if catalog:
                for prefix, local_root in catalog.items():
                    if schema_href.startswith(prefix):
                        rel = schema_href[len(prefix) :].lstrip("/")
                        for candidate in _catalog_path_candidates(local_root, rel):
                            if candidate.exists():
                                return candidate

        if self._resolver is not None:
            resolved = self._resolver(schema_href)
            if resolved is not None and resolved.exists():
                return resolved.resolve()

        return None

    def _resolve_taxonomy(
        self,
        instance_path: Path,
        schema_href: str,
        path_str: str,
        progress_callback: Callable[[str, int, int], None] | None = None,
        resolved_taxonomy_path: Path | None = None,
    ) -> TaxonomyStructure:
        """Resolve the schemaRef href to a taxonomy path and load it."""
        if resolved_taxonomy_path is None:
            resolved_taxonomy_path = self._resolve_taxonomy_path(instance_path, schema_href)
        if resolved_taxonomy_path is not None:
            return self._loader.load(resolved_taxonomy_path, progress_callback=progress_callback)

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
        out.append(
            FilingIndicator(
                template_id=template_id,
                filed=filed,
                context_ref=context_ref,
            )
        )


def _parse_bde_filing_indicators(
    preambulo: BdePreambulo | None,
) -> list[FilingIndicator]:
    """Build filing indicators from BDE EstadosReportados when present.

    BDE instances encode filing-indicator semantics with 4-digit CodigoEstado
    values. ``blanco="true"`` marks the table as empty/not filed; the default is
    ``false`` which means the table contains data.
    """
    if preambulo is None or not preambulo.estados_reportados:
        return []

    return [
        FilingIndicator(
            template_id=estado.codigo,
            filed=not estado.blanco,
            context_ref=estado.context_ref or preambulo.context_ref,
        )
        for estado in preambulo.estados_reportados
        if estado.codigo
    ]


def _parse_bde_preambulo(root: etree._Element) -> BdePreambulo | None:
    """Extract BDE IE_2008_02 preamble elements from the document root.

    BDE instances carry three types of preamble data as direct children of
    ``<xbrli:xbrl>`` in the ``es-be-cm-pblo`` namespace:

    * ``EntidadPresentadora`` — 4-digit entity code (no "ES" prefix).
    * ``TipoEnvio`` — submission type (Ordinario / Complementario / Sustitutivo).
    * ``EstadosReportados`` — wrapper containing one or more ``CodigoEstado``
      elements, each optionally carrying ``es-be-cm-pblo:blanco="true"`` to
      signal a clearing submission for that estado.

    The Agrupacion consolidation group is NOT a preamble element — it is a
    proper XBRL explicit dimension declared in the ``es-be-cm-dim`` namespace
    and encoded as ``<xbrldi:explicitMember>`` inside ``<xbrli:segment>``.
    It is therefore parsed as a regular dimension by ``_parse_context()``.

    Returns ``None`` when no preamble elements are present (non-BDE instance).
    """
    entidad = ""
    tipo_envio = ""
    estados: list[BdeEstadoReportado] = []
    context_ref = ""
    found_any = False

    for child in root:
        if not isinstance(child.tag, str):
            continue
        tag = child.tag

        if tag == _BDE_ENTIDAD:
            found_any = True
            entidad = (child.text or "").strip()
            context_ref = context_ref or child.get("contextRef", "")

        elif tag == _BDE_TIPO_ENVIO:
            found_any = True
            tipo_envio = (child.text or "").strip()
            context_ref = context_ref or child.get("contextRef", "")

        elif tag == _BDE_ESTADOS_REPORTADOS:
            found_any = True
            # CodigoEstado children: each declares one estado code.
            # blanco="true" signals that the estado is being cleared.
            blanco_attr = f"{{{BDE_PBLO_NS}}}blanco"
            for estado_el in child:
                if not isinstance(estado_el.tag, str):
                    continue
                if estado_el.tag != _BDE_CODIGO_ESTADO:
                    continue
                codigo = (estado_el.text or "").strip()
                if not codigo:
                    continue
                blanco_val = estado_el.get(blanco_attr, "false").lower()
                blanco = blanco_val in ("true", "1", "yes")
                estado_ctx = estado_el.get("contextRef", "") or context_ref
                estados.append(
                    BdeEstadoReportado(
                        codigo=codigo,
                        blanco=blanco,
                        context_ref=estado_ctx,
                    )
                )

    if not found_any:
        return None

    return BdePreambulo(
        entidad_presentadora=entidad,
        tipo_envio=tipo_envio,
        estados_reportados=estados,
        context_ref=context_ref,
    )

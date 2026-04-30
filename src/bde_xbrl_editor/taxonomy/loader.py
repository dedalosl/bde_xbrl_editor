"""TaxonomyLoader — orchestrates full DTS discovery, parsing, and assembly.

Progress is reported via a plain Python callback (no Qt dependency) so the
taxonomy module remains PySide6-free.
"""

from __future__ import annotations

import os
import re
from collections import deque
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from lxml import etree

from bde_xbrl_editor.taxonomy.cache import TaxonomyCache
from bde_xbrl_editor.taxonomy.constants import (
    ARCROLE_ALL,
    ARCROLE_ASSERTION_SATISFIED_MESSAGE,
    ARCROLE_ASSERTION_UNSATISFIED_MESSAGE,
    ARCROLE_DIMENSION_DEFAULT,
    ARCROLE_DIMENSION_DOMAIN,
    ARCROLE_DOMAIN_MEMBER,
    ARCROLE_ELEMENT_LABEL,
    ARCROLE_HYPERCUBE_DIMENSION,
    ARCROLE_NOT_ALL,
    NS_LINK,
    NS_TABLE_NAMESPACES,
    NS_XBRLDT,
    NS_XBRLI,
)
from bde_xbrl_editor.taxonomy.discovery import _should_skip_linkbase, discover_dts
from bde_xbrl_editor.taxonomy.label_resolver import LabelResolver
from bde_xbrl_editor.taxonomy.linkbases.assertion_resources import (
    parse_assertion_resource_linkbase,
)
from bde_xbrl_editor.taxonomy.linkbases.calculation import parse_calculation_linkbase
from bde_xbrl_editor.taxonomy.linkbases.custom_functions import (
    parse_custom_function_linkbase,
)
from bde_xbrl_editor.taxonomy.linkbases.definition import parse_definition_linkbase
from bde_xbrl_editor.taxonomy.linkbases.formula import (
    linkbase_contains_formula_assertions,
    parse_assertion_table_mappings,
    parse_formula_linkbase,
)
from bde_xbrl_editor.taxonomy.linkbases.generic_label import parse_generic_label_linkbase
from bde_xbrl_editor.taxonomy.linkbases.label import parse_label_linkbase
from bde_xbrl_editor.taxonomy.linkbases.presentation import (
    PresentationLinkbaseParseResult,
    parse_presentation_linkbase,
)
from bde_xbrl_editor.taxonomy.linkbases.table_pwd import parse_table_linkbase
from bde_xbrl_editor.taxonomy.models import (
    AssertionTextResource,
    Concept,
    CustomFunctionDefinition,
    DimensionModel,
    DomainMember,
    QName,
    TaxonomyMetadata,
    TaxonomyParseError,
    TaxonomyStructure,
    UnsupportedTaxonomyFormatError,
)
from bde_xbrl_editor.taxonomy.schema import (
    XBRL_SG_ROOTS,
    build_global_named_type_registry,
    extract_concept_enumerations_for_schema,
    extract_monetary_value_type_qnames,
    parse_schema_raw,
)
from bde_xbrl_editor.taxonomy.settings import LoaderSettings
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file

ProgressCallback = Callable[[str, int, int], None]

# Total loading steps for progress reporting (at least 6)
_TOTAL_STEPS = 7

_NS_XLINK = "http://www.w3.org/1999/xlink"
_XLINK_HREF = f"{{{_NS_XLINK}}}href"

_XBRLI_PREFIX_COLON_RE = re.compile(r"\bxbrli\s*:")
_XBRLI_INSTANCE_IMPORT_NS_RE = re.compile(
    r"""namespace\s*=\s*["']http://www\.xbrl\.org/2003/instance["']""",
    re.IGNORECASE,
)


def _schema_declares_xsd_model_tags(path: Path) -> bool:
    """True when the file looks like a vocabulary/taxonomy schema (not an empty shell)."""
    try:
        snippet = path.read_text(encoding="utf-8", errors="ignore")[:524_288]
    except OSError:
        return False
    return bool(
        re.search(r"<\s*(?:xs:)?(?:element|simpleType|complexType)\b", snippet, re.IGNORECASE)
    )


def _schema_text_references_xbrl_linkbase_namespace(path: Path) -> bool:
    """True when the XSD text references the XBRL linkbase namespace URI."""
    try:
        snippet = path.read_text(encoding="utf-8", errors="ignore")[:524_288]
    except OSError:
        return False
    return NS_LINK in snippet


def _schema_embeds_linkbase_or_role_declarations(path: Path) -> bool:
    """Return True when XSD text contains XBRL link metadata from the DTS model."""
    try:
        snippet = path.read_text(encoding="utf-8", errors="ignore")[:524_288]
    except OSError:
        return False
    return any(
        marker in snippet
        for marker in (
            "link:linkbaseRef",
            "link:roleType",
            "link:arcroleType",
        )
    )


def _schema_text_references_xbrl_instance_model(path: Path) -> bool:
    """Return True when XSD text ties to the XBRL instance schema model.

    Segment-only vocabulary schemas (XBRL conformance 302.01) often declare
    ``xmlns:xbrli`` for documentation but do not reference ``xbrli:`` QNames or
    import the instance namespace. Stub files such as ``Nautilus.xsd`` do, and
    must still be rejected when they yield no item/tuple concepts.
    """
    try:
        snippet = path.read_text(encoding="utf-8", errors="ignore")[:524_288]
    except OSError:
        return False
    return bool(_XBRLI_PREFIX_COLON_RE.search(snippet))


def _sniff_linkbase_type(path: Path) -> str:
    """Return a crude type string for a linkbase file: label/generic/pres/calc/def/table/unknown.

    Formula / validation assertions are **not** classified here; they are detected
    structurally via :func:`linkbase_contains_formula_assertions` on every discovered
    ``.xml`` linkbase (see ``_do_load``).
    """
    name = path.stem.lower()
    if re.search(r"(?:^|[-_])pre(?:sentation)?(?:$|[-_])", name):
        return "pres"
    if "label" in name or "lab" in name:
        if "gen" in name:
            return "generic"
        return "label"
    if "pres" in name or "presentation" in name:
        return "pres"
    if "calc" in name or "calculation" in name:
        return "calc"
    if "def" in name or "definition" in name:
        return "def"
    if "table" in name or "tbl" in name or "rend" in name:
        return "table"

    try:
        ctx = etree.iterparse(BytesIO(path.read_bytes()), events=("start",))
        for _, el in ctx:
            tag = str(el.tag)
            local = tag.split("}")[-1] if "}" in tag else tag
            if local == "presentationLink":
                return "pres"
            if any(table_ns in tag for table_ns in NS_TABLE_NAMESPACES):
                return "table"
    except Exception:  # noqa: BLE001
        pass
    return "unknown"


def _classify_linkbases(linkbase_paths: list[Path]) -> dict[str, list[Path]]:
    """Group linkbase paths by type while preserving the original order."""
    classified = {
        "label": [],
        "generic": [],
        "pres": [],
        "calc": [],
        "def": [],
        "table": [],
        "unknown": [],
    }
    for path in linkbase_paths:
        lb_type = _sniff_linkbase_type(path)
        classified.setdefault(lb_type, []).append(path)
    return classified


def _find_companion_tab_presentation_linkbases(
    entry_point: Path,
    known_linkbases: list[Path],
) -> list[Path]:
    """Find sibling ``tab/*pre*.xml`` files that DTS discovery may miss."""
    known = set(known_linkbases)
    search_roots: list[Path] = []
    if entry_point.parent.name in {"mod", "tab"}:
        search_roots.append(entry_point.parent.parent)
    search_roots.append(entry_point.parent)

    discovered: list[Path] = []
    seen: set[Path] = set()
    for root in search_roots:
        tab_dir = root / "tab"
        if not tab_dir.is_dir():
            continue
        for path in sorted(tab_dir.glob("*pre*.xml")):
            if path in known or path in seen:
                continue
            if _sniff_linkbase_type(path) != "pres":
                continue
            seen.add(path)
            discovered.append(path)
    return discovered


def _build_group_table_order(
    presentation_results: list[PresentationLinkbaseParseResult],
) -> dict[str, int]:
    """Compute flat table order from already-parsed presentation metadata."""
    children: dict[str, list[tuple[float, str]]] = {}
    rend_fragments: set[str] = set()
    fallback_roots: list[str] = []
    child_fragments: set[str] = set()

    for result in presentation_results:
        for parent, child_entries in result.group_table_children.items():
            children.setdefault(parent, []).extend(child_entries)
            child_fragments.update(child for _, child in child_entries)
        rend_fragments.update(result.group_table_rend_fragments)
        if (
            result.group_table_root_fragment is not None
            and result.group_table_root_fragment not in fallback_roots
        ):
            fallback_roots.append(result.group_table_root_fragment)

    if not children:
        return {}

    for parent in children:
        children[parent].sort(key=lambda item: item[0])

    root_fragments = [parent for parent in children if parent not in child_fragments]
    if not root_fragments:
        root_fragments = [root for root in fallback_roots if root in children]
    else:
        for root in fallback_roots:
            if root in children and root not in root_fragments:
                root_fragments.append(root)

    if not root_fragments:
        root_fragments = list(children)

    flat_order: dict[str, int] = {}
    counter = 0
    visited: set[str] = set()

    for root_fragment in root_fragments:
        stack: list[str] = [root_fragment]
        while stack:
            node = stack.pop()
            if node in visited:
                continue
            visited.add(node)
            if node in rend_fragments:
                flat_order[node] = counter
                counter += 1
            for _, child_frag in reversed(children.get(node, [])):
                if child_frag not in visited:
                    stack.append(child_frag)
    return flat_order


def _preferred_group_table_results(
    presentation_results: list[tuple[Path, PresentationLinkbaseParseResult]],
) -> list[PresentationLinkbaseParseResult]:
    """Choose the presentation results that should drive table ordering.

    When a taxonomy ships both a module-level ``*-pre.xml`` and a dedicated
    ``tab/tab-pre.xml``, the latter reflects the table browser order users
    expect. Prefer presentation linkbases discovered under a ``tab`` folder
    when they provide ``group-table`` metadata; otherwise fall back to every
    presentation result that contains such metadata.
    """

    tab_results = [
        result
        for path, result in presentation_results
        if result.group_table_children and "tab" in path.parts
    ]
    if tab_results:
        return tab_results
    return [result for _path, result in presentation_results if result.group_table_children]


def _find_cache_root(entry_point: Path) -> Path | None:
    """Return the nearest ancestor named ``cache`` for *entry_point*, if any."""
    for parent in entry_point.resolve().parents:
        if parent.name == "cache":
            return parent
    return None


def _infer_local_catalog_from_cache(entry_point: Path) -> dict[str, Path]:
    """Infer URL-prefix mappings from a mirrored on-disk taxonomy cache.

    When users open an entry point directly from ``cache/<host>/...``, downstream
    schemas often jump back to remote HTTP URLs for sibling hosts such as
    ``www.eba.europa.eu`` or ``www.eurofiling.info``. Treat every host directory
    under the shared ``cache`` root as a local mirror so those remote imports can
    still resolve without requiring manual loader settings.
    """
    cache_root = _find_cache_root(entry_point)
    if cache_root is None or not cache_root.is_dir():
        return {}

    catalog: dict[str, Path] = {}
    for host_dir in sorted(cache_root.iterdir()):
        if not host_dir.is_dir():
            continue
        host = host_dir.name.strip()
        if not host:
            continue
        for scheme in ("http", "https", "ftp"):
            catalog[f"{scheme}://{host}/"] = host_dir
    return catalog


def _build_concept_id_map(concepts: dict[QName, Concept]) -> dict[str, QName]:
    """Build a map from XML id-style fragment → QName.

    XBRL uses element @id attributes of the form "{prefix}_{localName}" or
    just "{localName}" as XLink locator href fragments.

    This map is the *fallback* used by parse_definition_linkbase when the
    primary namespace-qualified lookup (which uses the schema URL from the
    locator href) cannot resolve a concept — e.g. because the schema that
    declares it was not reached via xs:import discovery.

    When multiple concepts share the same xml:id (e.g. a dimension in
    dict/dim/dim.xsd and a domain member in dict/dom/exp.xsd both declare
    id="eba_NAC"), xbrldt:dimensionItem / xbrldt:hypercubeItem concepts must
    win so that the fallback still returns the structurally-correct concept.
    Achieve this by sorting so dimensional concepts are written last and
    therefore overwrite any earlier entry with the same key.
    """

    def _sg_priority(item: tuple[QName, Concept]) -> int:
        sg = item[1].substitution_group
        return 1 if (sg and sg.namespace == NS_XBRLDT) else 0

    id_map: dict[str, QName] = {}
    for qname, concept in sorted(concepts.items(), key=_sg_priority):
        # Standard XBRL id: prefixed or bare local name
        id_map[qname.local_name] = qname
        if qname.prefix:
            id_map[f"{qname.prefix}_{qname.local_name}"] = qname
        # Also add namespace-derived prefix
        ns_short = qname.namespace.rstrip("/").split("/")[-1].replace("-", "").replace(".", "")[:8]
        id_map[f"{ns_short}_{qname.local_name}"] = qname
        # Use the actual @id attribute from the XSD element (most reliable)
        if concept.xml_id:
            id_map[concept.xml_id] = qname
    return id_map


def _extract_metadata(entry_point: Path, declared_languages: list[str]) -> TaxonomyMetadata:
    """Extract taxonomy name, version, publisher from the entry-point schema annotations."""
    name = entry_point.stem
    version = ""
    publisher = ""
    period_type = None

    try:
        tree = parse_xml_file(entry_point)
        root = tree.getroot()
        # Try to find annotation/documentation with taxonomy info
        for doc in root.iter("{http://www.w3.org/2001/XMLSchema}documentation"):
            text = (doc.text or "").strip()
            if text:
                name = text[:80]
                break
        # Version from schema @version attribute
        version = root.get("version", "")
    except Exception:  # noqa: BLE001
        pass

    return TaxonomyMetadata(
        name=name or entry_point.stem,
        version=version or "unknown",
        publisher=publisher or "unknown",
        entry_point_path=entry_point,
        loaded_at=datetime.now(),
        declared_languages=tuple(sorted(set(declared_languages))),
        period_type=period_type,
    )


def _best_assertion_resources(
    resources: list[AssertionTextResource],
    *,
    arcrole: str,
    language_preference: list[str],
) -> tuple[AssertionTextResource, ...]:
    """Select the best assertion resources for one arcrole."""
    matched = [resource for resource in resources if resource.arcrole == arcrole]
    if not matched:
        return ()

    for language in language_preference:
        localized = [resource for resource in matched if resource.language == language]
        if localized:
            return tuple(sorted(localized, key=lambda item: item.priority, reverse=True))

    return tuple(sorted(matched, key=lambda item: item.priority, reverse=True))


_SG_HYPERCUBE = QName(NS_XBRLDT, "hypercubeItem")
_SG_DIMENSION = QName(NS_XBRLDT, "dimensionItem")

# XBRL 2.1 §5.1.3 — predefined roles that are always resolved without needing a roleRef.
_PREDEFINED_XBRL_ROLES: frozenset[str] = frozenset(
    {
        "http://www.xbrl.org/2003/role/link",
        "http://www.xbrl.org/2003/role/label",
        "http://www.xbrl.org/2003/role/terseLabel",
        "http://www.xbrl.org/2003/role/verboseLabel",
        "http://www.xbrl.org/2003/role/positiveLabel",
        "http://www.xbrl.org/2003/role/positiveTerseLabel",
        "http://www.xbrl.org/2003/role/positiveVerboseLabel",
        "http://www.xbrl.org/2003/role/negativeLabel",
        "http://www.xbrl.org/2003/role/negativeTerseLabel",
        "http://www.xbrl.org/2003/role/negativeVerboseLabel",
        "http://www.xbrl.org/2003/role/zeroLabel",
        "http://www.xbrl.org/2003/role/zeroTerseLabel",
        "http://www.xbrl.org/2003/role/zeroVerboseLabel",
        "http://www.xbrl.org/2003/role/totalLabel",
        "http://www.xbrl.org/2003/role/periodStartLabel",
        "http://www.xbrl.org/2003/role/periodEndLabel",
        "http://www.xbrl.org/2003/role/documentation",
        "http://www.xbrl.org/2003/role/definitionGuidance",
        "http://www.xbrl.org/2003/role/disclosureGuidance",
        "http://www.xbrl.org/2003/role/presentationGuidance",
        "http://www.xbrl.org/2003/role/measurementGuidance",
        "http://www.xbrl.org/2003/role/commentaryGuidance",
        "http://www.xbrl.org/2003/role/exampleGuidance",
        "http://www.xbrl.org/2003/role/reference",
        "http://www.xbrl.org/2003/role/definitionRef",
        "http://www.xbrl.org/2003/role/disclosureRef",
        "http://www.xbrl.org/2003/role/mandatoryDisclosureRef",
        "http://www.xbrl.org/2003/role/recommendedDisclosureRef",
        "http://www.xbrl.org/2003/role/unspecifiedDisclosureRef",
        "http://www.xbrl.org/2003/role/presentationRef",
        "http://www.xbrl.org/2003/role/measurementRef",
        "http://www.xbrl.org/2003/role/commentaryRef",
        "http://www.xbrl.org/2003/role/exampleRef",
    }
)


def _check_dimensional_constraints(
    concepts: dict[QName, Concept],
    definition_arcs: dict[str, list],
    declared_roles: set[str] | None = None,
) -> None:
    """Check XBRL Dimensions 1.0 taxonomy structure constraints (xbrldte:* errors).

    Raises TaxonomyParseError with the appropriate xbrldte: error code in the
    message when a constraint is violated. The conformance runner's
    _match_outcome() detects these codes in the exception message.
    """
    # Build substitution group chain map for transitive closure computation.
    sg_map: dict[QName, QName] = {
        q: c.substitution_group for q, c in concepts.items() if c.substitution_group is not None
    }

    # Compute transitive hypercube and dimension sets — a concept is a hypercube
    # (dimension) item if its substitution group chain reaches xbrldt:hypercubeItem
    # (xbrldt:dimensionItem), regardless of how many hops.
    hypercube_qnames: set[QName] = set()
    dimension_qnames: set[QName] = set()
    for q in concepts:
        sg = sg_map.get(q)
        while sg is not None:
            if sg == _SG_HYPERCUBE:
                hypercube_qnames.add(q)
                break
            if sg == _SG_DIMENSION:
                dimension_qnames.add(q)
                break
            sg = sg_map.get(sg)

    # Check 1: hypercube items (including transitive) must be abstract
    # (xbrldte:HypercubeElementIsNotAbstractError)
    for qname in hypercube_qnames:
        if not concepts[qname].abstract:
            raise TaxonomyParseError(
                file_path="",
                message=(
                    f"xbrldte:HypercubeElementIsNotAbstractError: "
                    f"Hypercube element {qname} must be abstract"
                ),
            )

    # Check 2: dimension items (including transitive) must be abstract
    # (xbrldte:DimensionElementIsNotAbstractError)
    for qname in dimension_qnames:
        if not concepts[qname].abstract:
            raise TaxonomyParseError(
                file_path="",
                message=(
                    f"xbrldte:DimensionElementIsNotAbstractError: "
                    f"Dimension element {qname} must be abstract"
                ),
            )

    dim_and_hc: set[QName] = hypercube_qnames | dimension_qnames

    # Track cross-ELR dimension-default combinations to detect too many defaults.
    # Per XBRL Dimensions §2.7.1.1, dimension-default relationships are NOT scoped
    # by ELR — a dimension may only have one default across the entire DTS.
    dim_defaults_seen: dict[QName, set[QName]] = {}

    for _elr, arcs in definition_arcs.items():
        for arc in arcs:
            arcrole = arc.arcrole

            # Check 3: source of hypercube-dimension arc must be a hypercube
            # (xbrldte:HypercubeDimensionSourceError)
            # Only enforced when the source concept is known to us — if its
            # declaring schema was not loaded (e.g. remote schema not cached)
            # the concept is absent from `concepts` and we cannot verify.
            if arcrole == ARCROLE_HYPERCUBE_DIMENSION:
                if arc.source in concepts and arc.source not in hypercube_qnames:
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:HypercubeDimensionSourceError: "
                            f"Source of hypercube-dimension arc must be a hypercube item, "
                            f"got {arc.source}"
                        ),
                    )
                # Check 4: target of hypercube-dimension arc must be a dimension
                # (xbrldte:HypercubeDimensionTargetError)
                if arc.target in concepts and arc.target not in dimension_qnames:
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:HypercubeDimensionTargetError: "
                            f"Target of hypercube-dimension arc must be a dimension item, "
                            f"got {arc.target}"
                        ),
                    )
                # Check: targetRole must be a declared role (xbrldte:TargetRoleNotResolvedError)
                if (
                    declared_roles is not None
                    and arc.target_role is not None
                    and arc.target_role not in declared_roles
                ):
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:TargetRoleNotResolvedError: "
                            f"targetRole '{arc.target_role}' is not declared via a roleRef"
                        ),
                    )

            # Check 5: all/notAll arc constraints
            if arcrole in (ARCROLE_ALL, ARCROLE_NOT_ALL):
                # Check 5a: source must not be a hypercube or dimension item
                # (xbrldte:HasHypercubeSourceError)
                if arc.source in concepts and arc.source in dim_and_hc:
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:HasHypercubeSourceError: "
                            f"Source of hasHypercube arc must be a primary item, "
                            f"got {arc.source}"
                        ),
                    )
                # Check 5b: target must be a hypercube (xbrldte:HasHypercubeTargetError)
                if arc.target in concepts and arc.target not in hypercube_qnames:
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:HasHypercubeTargetError: "
                            f"Target of hasHypercube arc must be a hypercube item, "
                            f"got {arc.target}"
                        ),
                    )
                # Check 6: all/notAll arc must have contextElement attribute
                # (xbrldte:HasHypercubeMissingContextElementAttributeError)
                if arc.context_element is None:
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            "xbrldte:HasHypercubeMissingContextElementAttributeError: "
                            "hasHypercube arc missing xbrldt:contextElement attribute"
                        ),
                    )
                # Check: targetRole must be a declared role (xbrldte:TargetRoleNotResolvedError)
                if (
                    declared_roles is not None
                    and arc.target_role is not None
                    and arc.target_role not in declared_roles
                ):
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:TargetRoleNotResolvedError: "
                            f"targetRole '{arc.target_role}' is not declared via a roleRef"
                        ),
                    )

            # Check 7: source of dimension-domain arc must be a dimension item
            # (xbrldte:DimensionDomainSourceError)
            if arcrole == ARCROLE_DIMENSION_DOMAIN:
                if arc.source in concepts and arc.source not in dimension_qnames:
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:DimensionDomainSourceError: "
                            f"Source of dimension-domain arc must be a dimension item, "
                            f"got {arc.source}"
                        ),
                    )
                # Check: target of dimension-domain arc must not be a hypercube or dimension
                # (xbrldte:DimensionDomainTargetError)
                if arc.target in concepts and arc.target in dim_and_hc:
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:DimensionDomainTargetError: "
                            f"Target of dimension-domain arc must not be a hypercube or "
                            f"dimension item, got {arc.target}"
                        ),
                    )
                # Check: targetRole must be a declared role (xbrldte:TargetRoleNotResolvedError)
                if (
                    declared_roles is not None
                    and arc.target_role is not None
                    and arc.target_role not in declared_roles
                ):
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:TargetRoleNotResolvedError: "
                            f"targetRole '{arc.target_role}' is not declared via a roleRef"
                        ),
                    )

            # Check: domain-member arc source/target must not be hypercube or dimension
            if arcrole == ARCROLE_DOMAIN_MEMBER:
                if arc.source in concepts and arc.source in dim_and_hc:
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:DomainMemberSourceError: "
                            f"Source of domain-member arc must not be a hypercube or "
                            f"dimension item, got {arc.source}"
                        ),
                    )
                if arc.target in concepts and arc.target in dim_and_hc:
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:DomainMemberTargetError: "
                            f"Target of domain-member arc must not be a hypercube or "
                            f"dimension item, got {arc.target}"
                        ),
                    )
                # Check: targetRole must be a declared role (xbrldte:TargetRoleNotResolvedError)
                if (
                    declared_roles is not None
                    and arc.target_role is not None
                    and arc.target_role not in declared_roles
                ):
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:TargetRoleNotResolvedError: "
                            f"targetRole '{arc.target_role}' is not declared via a roleRef"
                        ),
                    )

            # Check 8: dimension-default arcs
            # (xbrldte:TooManyDefaultMembersError, DimensionDefaultSourceError,
            #  DimensionDefaultTargetError)
            if arcrole == ARCROLE_DIMENSION_DEFAULT:
                # Source must be a dimension item (xbrldte:DimensionDefaultSourceError)
                if arc.source in concepts and arc.source not in dimension_qnames:
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:DimensionDefaultSourceError: "
                            f"Source of dimension-default arc must be a dimension item, "
                            f"got {arc.source}"
                        ),
                    )
                # Target must not be a hypercube or dimension item (xbrldte:DimensionDefaultTargetError)
                if arc.target in concepts and arc.target in dim_and_hc:
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:DimensionDefaultTargetError: "
                            f"Target of dimension-default arc must not be a hypercube or "
                            f"dimension item, got {arc.target}"
                        ),
                    )
                # Track per-dimension (cross-ELR) to detect too many defaults.
                targets = dim_defaults_seen.setdefault(arc.source, set())
                targets.add(arc.target)
                if len(targets) > 1:
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:TooManyDefaultMembersError: "
                            f"Dimension {arc.source} has more than one default member "
                            f"across the DTS"
                        ),
                    )


def _rebuild_dimensions(
    definition_arcs: dict[str, list],
    concepts: dict[QName, Concept],
) -> dict[QName, DimensionModel]:
    """Build DimensionModel objects by BFS-walking the complete merged definition arc set.

    The per-file approach in parse_definition_linkbase cannot associate domain-member
    arcs from extension linkbases (where dim_domain is not yet known) with their
    parent dimensions.  By using the globally merged definition_arcs we see all arcs
    across all files and correctly populate every dimension's member set.
    """
    # dimension → list of (root domain concept, order, domain_usable)
    # Preserves xbrldt:usable on the dimension-domain arc for the domain root.
    # Some taxonomies declare multiple direct roots for one explicit dimension.
    dim_domain_roots: dict[QName, list[tuple[QName, float, bool]]] = {}
    dim_defaults: dict[QName, QName] = {}
    # Children in the domain-member arc graph, indexed by parent concept.
    # For duplicate (parent, child) pairs (e.g. after arc override/prohibition),
    # usability is ANDed across all arcs — if any arc marks a member non-usable,
    # it is treated as non-usable overall.
    dm_children_usable: dict[QName, dict[QName, tuple[float, bool]]] = {}

    for _elr, arcs in definition_arcs.items():
        for arc in arcs:
            if arc.arcrole == ARCROLE_DIMENSION_DOMAIN:
                domain_usable = arc.usable if arc.usable is not None else True
                dim_domain_roots.setdefault(arc.source, []).append(
                    (arc.target, arc.order, domain_usable)
                )
            elif arc.arcrole == ARCROLE_DOMAIN_MEMBER:
                usable = arc.usable if arc.usable is not None else True
                parent_map = dm_children_usable.setdefault(arc.source, {})
                if arc.target in parent_map:
                    prev_order, prev_usable = parent_map[arc.target]
                    parent_map[arc.target] = (prev_order, prev_usable and usable)
                else:
                    parent_map[arc.target] = (arc.order, usable)
            elif arc.arcrole == ARCROLE_DIMENSION_DEFAULT:
                dim_defaults[arc.source] = arc.target

    # Flatten the AND-merged children map into a list form for BFS.
    dm_children: dict[QName, list[tuple[QName, float, bool]]] = {
        parent: [(child, order, usable) for child, (order, usable) in child_map.items()]
        for parent, child_map in dm_children_usable.items()
    }

    dimensions: dict[QName, DimensionModel] = {}
    for dim_q, roots in dim_domain_roots.items():
        # BFS from every root domain concept to collect all members transitively.
        all_members: list[DomainMember] = []
        visited: set[QName] = set()
        # queue entries: (concept, parent, order, usable)
        queue: list[tuple[QName, QName | None, float, bool]] = sorted(
            [(domain_q, None, order, domain_usable) for domain_q, order, domain_usable in roots],
            key=lambda item: item[2],
        )
        while queue:
            current_q, parent_q, order, usable = queue.pop(0)
            if current_q in visited:
                continue
            visited.add(current_q)
            all_members.append(
                DomainMember(qname=current_q, parent=parent_q, order=order, usable=usable)
            )
            for child_q, child_order, child_usable in dm_children.get(current_q, []):
                if child_q not in visited:
                    queue.append((child_q, current_q, child_order, child_usable))

        dimensions[dim_q] = DimensionModel(
            qname=dim_q,
            dimension_type="typed"
            if concepts.get(dim_q) and concepts[dim_q].typed_domain_ref
            else "explicit",
            default_member=dim_defaults.get(dim_q),
            domain=roots[0][0],
            members=tuple(all_members),
        )

    return dimensions


def _member_qname_to_expanded_name_uri(member: QName) -> str:
    """EE 2.0 expanded name URI: ``namespace-uri#localname``."""
    return f"{member.namespace}#{member.local_name}"


def _collect_enumeration_domain_members(
    linkrole: str,
    domain_head: QName,
    *,
    head_usable: bool,
    definition_arcs: dict[str, list],
) -> list[QName]:
    """Domain of allowed values per Extensible Enumerations 1.0/2.0 (XDT domain-member walk)."""
    queue: deque[tuple[QName, str]] = deque([(domain_head, linkrole)])
    seen_states: set[tuple[QName, str]] = set()
    emitted: set[QName] = set()
    result: list[QName] = []

    while queue:
        node, elr = queue.popleft()
        state = (node, elr)
        if state in seen_states:
            continue
        seen_states.add(state)

        if node == domain_head:
            if head_usable and node not in emitted:
                emitted.add(node)
                result.append(node)
        elif node not in emitted:
            emitted.add(node)
            result.append(node)

        for arc in definition_arcs.get(elr, []):
            if arc.arcrole != ARCROLE_DOMAIN_MEMBER or arc.source != node:
                continue
            if arc.usable is False:
                continue
            next_elr = arc.target_role or elr
            queue.append((arc.target, next_elr))

    return result


def _apply_extensible_enumeration_values(
    concepts: dict[QName, Concept],
    definition_arcs: dict[str, list],
) -> dict[QName, Concept]:
    """Populate ``enumeration_values`` from EE domain-member networks (overrides XSD-only enums)."""
    updated: dict[QName, Concept] = {}
    for qn, c in concepts.items():
        if not c.enumeration_linkrole or c.enumeration_domain is None:
            updated[qn] = c
            continue
        members = _collect_enumeration_domain_members(
            c.enumeration_linkrole,
            c.enumeration_domain,
            head_usable=c.enumeration_head_usable,
            definition_arcs=definition_arcs,
        )
        if not members:
            updated[qn] = c
            continue
        uris = tuple(_member_qname_to_expanded_name_uri(m) for m in members)
        updated[qn] = replace(c, enumeration_values=uris)
    return updated


def _schema_parse_workers(schema_count: int) -> int:
    """Return a bounded worker count for concurrent schema parsing."""
    if schema_count <= 1:
        return 1
    cpu_count = os.cpu_count() or 1
    return max(1, min(schema_count, cpu_count, 8))


def _linkbase_parse_workers(linkbase_count: int) -> int:
    """Return a bounded worker count for concurrent linkbase parsing."""
    if linkbase_count <= 1:
        return 1
    cpu_count = os.cpu_count() or 1
    return max(1, min(linkbase_count, cpu_count, 8))


def _run_path_jobs(
    paths: list[Path],
    parse_fn: Callable[[Path], Any],
    *,
    workers: int,
    error_message_factory: Callable[[Exception], str] | None = None,
) -> list[tuple[Path, Any]]:
    """Run independent file parses concurrently while preserving input order."""
    if not paths:
        return []
    if workers <= 1 or len(paths) <= 1:
        results: list[tuple[Path, Any]] = []
        for path in paths:
            try:
                results.append((path, parse_fn(path)))
            except TaxonomyParseError:
                raise
            except Exception as exc:  # noqa: BLE001
                message = (
                    error_message_factory(exc)
                    if error_message_factory is not None
                    else f"Unexpected error: {exc}"
                )
                raise TaxonomyParseError(file_path=str(path), message=message) from exc
        return results

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures: list[Future[Any]] = [executor.submit(parse_fn, path) for path in paths]
        results = []
        for path, future in zip(paths, futures, strict=False):
            try:
                results.append((path, future.result()))
            except TaxonomyParseError:
                raise
            except Exception as exc:  # noqa: BLE001
                message = (
                    error_message_factory(exc)
                    if error_message_factory is not None
                    else f"Unexpected error: {exc}"
                )
                raise TaxonomyParseError(file_path=str(path), message=message) from exc
        return results


class TaxonomyLoader:
    """Orchestrates taxonomy loading from a local filesystem path.

    A single loader can be reused for multiple load() / reload() calls.
    The TaxonomyCache is the shared state; the loader is stateless between calls.
    """

    def __init__(self, cache: TaxonomyCache, settings: LoaderSettings | None = None) -> None:
        self._cache = cache
        self._settings = settings or LoaderSettings()
        self._last_skipped_urls: list[str] = []

    @property
    def last_skipped_urls(self) -> list[str]:
        """Remote URLs that were skipped (not in local catalog) during the last load."""
        return self._last_skipped_urls

    @property
    def settings(self) -> LoaderSettings:
        return self._settings

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(
        self,
        entry_point: str | Path,
        progress_callback: ProgressCallback | None = None,
    ) -> TaxonomyStructure:
        """Load the taxonomy at entry_point.

        Returns a cached TaxonomyStructure if already loaded.

        Raises:
            UnsupportedTaxonomyFormatError — not a valid XBRL taxonomy.
            TaxonomyDiscoveryError — DTS references unresolvable.
            TaxonomyParseError — structural parse error.
        """
        entry_point = Path(entry_point).resolve()
        cache_key = str(entry_point)

        cached = self._cache.get(cache_key)
        if cached is not None:
            if progress_callback:
                progress_callback(
                    (
                        "Loaded from cache — "
                        f"{len(cached.tables)} tables, {len(cached.concepts)} concepts"
                    ),
                    _TOTAL_STEPS,
                    _TOTAL_STEPS,
                )
            return cached

        structure = self._do_load(entry_point, progress_callback)
        self._cache.put(cache_key, structure)
        return structure

    def reload(
        self,
        entry_point: str | Path,
        progress_callback: ProgressCallback | None = None,
    ) -> TaxonomyStructure:
        """Force-reload the taxonomy, bypassing and replacing the cache entry."""
        entry_point = Path(entry_point).resolve()
        cache_key = str(entry_point)
        self._cache.invalidate(cache_key)
        structure = self._do_load(entry_point, progress_callback)
        self._cache.put(cache_key, structure)
        return structure

    # ------------------------------------------------------------------
    # Internal loading pipeline
    # ------------------------------------------------------------------

    def _do_load(self, entry_point: Path, cb: ProgressCallback | None) -> TaxonomyStructure:
        def progress(msg: str, step: int) -> None:
            if cb:
                cb(msg, step, _TOTAL_STEPS)

        inferred_catalog = _infer_local_catalog_from_cache(entry_point)
        if self._settings.local_catalog:
            local_catalog = dict(self._settings.local_catalog)
            for prefix, local_root in inferred_catalog.items():
                local_catalog.setdefault(prefix, local_root)
        else:
            local_catalog = inferred_catalog or None
        effective_settings = (
            self._settings
            if local_catalog == self._settings.local_catalog
            else replace(self._settings, local_catalog=local_catalog)
        )

        # Step 1: DTS discovery
        progress("Discovering DTS…", 1)
        schema_paths, linkbase_paths, skipped_urls, include_ns_map, discovered_roles = discover_dts(
            entry_point,
            effective_settings,
            progress_callback=(lambda message, _current, _total: progress(message, 1)),
        )
        companion_tab_linkbases = _find_companion_tab_presentation_linkbases(
            entry_point,
            linkbase_paths,
        )
        all_linkbase_paths = list(linkbase_paths)
        all_linkbase_paths.extend(companion_tab_linkbases)
        self._last_skipped_urls: list[str] = skipped_urls
        progress(
            f"DTS discovered — {len(schema_paths)} schemas, {len(all_linkbase_paths)} linkbases",
            1,
        )
        classified_linkbases = _classify_linkbases(all_linkbase_paths)
        label_linkbases = classified_linkbases["label"]
        generic_label_linkbases = classified_linkbases["generic"]
        presentation_linkbases = classified_linkbases["pres"]
        calculation_linkbases = classified_linkbases["calc"]
        definition_linkbases = classified_linkbases["def"]
        table_linkbases = classified_linkbases["table"]
        formula_linkbases = list(
            dict.fromkeys(
                p
                for p in all_linkbase_paths
                if p.suffix.lower() in (".xml", ".xbrl")
                and not _should_skip_linkbase(p)
                and linkbase_contains_formula_assertions(p)
            )
        )
        linkbase_workers = _linkbase_parse_workers(len(all_linkbase_paths))

        # Step 2: Parse schemas → concepts (with cross-schema transitive SG resolution)
        progress("Parsing schemas…", 2)
        # Collect every xs:element-with-SG from every schema as raw candidates.
        # We defer filtering to after all schemas are collected so that
        # cross-schema transitive chains (A substitutes B substitutes xbrli:item,
        # where A and B live in different files) are resolved correctly.
        all_candidates: dict[QName, tuple[Concept, QName]] = {}
        # schema_path_to_ns: local abs path → targetNamespace (used to build the
        # namespace-qualified concept map for unambiguous locator resolution).
        schema_path_to_ns: dict[str, str] = {}
        schema_workers = _schema_parse_workers(len(schema_paths))
        parsed_schemas = _run_path_jobs(
            schema_paths,
            lambda schema_path: parse_schema_raw(schema_path, include_ns_map.get(schema_path)),
            workers=schema_workers,
        )

        for schema_path, (raw, target_ns) in parsed_schemas:
            all_candidates.update(raw)
            if target_ns:
                schema_path_to_ns[str(schema_path)] = target_ns
        schema_substitution_groups = {
            qname: substitution_group
            for qname, (_concept, substitution_group) in all_candidates.items()
        }

        # Transitive closure: start with concepts whose SG is a known XBRL root,
        # then iteratively promote candidates whose SG is already resolved.
        concepts: dict[QName, Concept] = {
            qn: c for qn, (c, sg) in all_candidates.items() if sg in XBRL_SG_ROOTS
        }
        pending = [(qn, c, sg) for qn, (c, sg) in all_candidates.items() if sg not in XBRL_SG_ROOTS]
        prev = -1
        while prev != len(concepts):
            prev = len(concepts)
            still_pending = []
            for qn, c, sg in pending:
                if sg in concepts:
                    concepts[qn] = c
                else:
                    still_pending.append((qn, c, sg))
            pending = still_pending

        if not concepts:
            # Allow empty item/tuple maps only for tiny segment-extension entry
            # points (no linkbases, no xbrli QName/import wiring) — conformance
            # 302.01.  Schemas that reference linkbases or the XBRL instance model
            # must still surface as unsupported when nothing resolved to a concept.
            segment_style_taxonomy = (
                bool(schema_paths)
                and not linkbase_paths
                and any(_schema_declares_xsd_model_tags(p) for p in schema_paths)
                and not any(
                    _schema_text_references_xbrl_instance_model(p)
                    or _schema_embeds_linkbase_or_role_declarations(p)
                    or _schema_text_references_xbrl_linkbase_namespace(p)
                    for p in schema_paths
                )
            )
            if not segment_style_taxonomy:
                raise UnsupportedTaxonomyFormatError(
                    entry_point=str(entry_point),
                    reason="No XBRL concepts found — file may not be a valid XBRL taxonomy entry point",
                )
        progress(f"Schemas parsed — {len(concepts)} concepts ready", 2)

        monetary_workers = _schema_parse_workers(len(schema_paths))
        parsed_monetary_types = _run_path_jobs(
            schema_paths,
            lambda p: extract_monetary_value_type_qnames(p, include_ns_map.get(p)),
            workers=monetary_workers,
        )
        monetary_derived_types: set[QName] = set()
        for _path, mt_set in parsed_monetary_types:
            monetary_derived_types.update(mt_set)

        type_enum_registry = build_global_named_type_registry(schema_paths, include_ns_map)
        enum_workers = _schema_parse_workers(len(schema_paths))
        parsed_concept_enums = _run_path_jobs(
            schema_paths,
            lambda p: extract_concept_enumerations_for_schema(
                p, include_ns_map.get(p), type_enum_registry
            ),
            workers=enum_workers,
        )
        enum_by_concept: dict[QName, tuple[str, ...]] = {}
        for _path, emap in parsed_concept_enums:
            for qn, vals in emap.items():
                if vals:
                    enum_by_concept[qn] = vals

        def _concept_is_monetary_item(c: Concept) -> bool:
            if c.data_type.namespace == NS_XBRLI and c.data_type.local_name == "monetaryItemType":
                return True
            return c.data_type in monetary_derived_types

        concepts = {
            qn: replace(
                c,
                monetary_item_type=_concept_is_monetary_item(c),
                enumeration_values=enum_by_concept.get(qn, ()),
            )
            for qn, c in concepts.items()
        }

        concept_id_map = _build_concept_id_map(concepts)

        # Build namespace-qualified map: "{namespace}#{xml_id}" → QName
        # Used by parse_definition_linkbase to resolve locator hrefs unambiguously
        # when two concepts share the same xml_id in different namespaces.
        ns_qualified_map: dict[str, QName] = {}
        for qname, concept in concepts.items():
            if concept.xml_id and qname.namespace:
                ns_qualified_map[f"{qname.namespace}#{concept.xml_id}"] = qname

        # Build a merged URL+path → namespace map for locator href resolution.
        # Keys are both the absolute local path string and, when the local_catalog
        # is configured, the corresponding HTTP URL string.
        schema_ns_map: dict[str, str] = dict(schema_path_to_ns)
        if effective_settings.local_catalog:
            for url_prefix, local_root in effective_settings.local_catalog.items():
                url_prefix_stripped = url_prefix.rstrip("/")
                for path_str, ns in schema_path_to_ns.items():
                    try:
                        rel = Path(path_str).relative_to(local_root)
                        url = f"{url_prefix_stripped}/{rel.as_posix()}"
                        schema_ns_map[url] = ns
                    except ValueError:
                        pass

        # Step 3: Parse label linkbases
        progress("Parsing label linkbases…", 3)
        standard_labels: dict[QName, list] = {}
        generic_labels: dict[QName, list] = {}
        formula_linkbase_path: Path | None = None

        if formula_linkbases:
            formula_linkbase_path = formula_linkbases[0]

        parsed_label_linkbases = _run_path_jobs(
            label_linkbases,
            lambda lb_path: parse_label_linkbase(
                lb_path,
                concept_id_map,
                ns_qualified_map=ns_qualified_map,
                schema_ns_map=schema_ns_map,
            ),
            workers=linkbase_workers,
        )
        for _lb_path, parsed in parsed_label_linkbases:
            for qname, labels in parsed.items():
                standard_labels.setdefault(qname, []).extend(labels)

        parsed_generic_label_linkbases = _run_path_jobs(
            generic_label_linkbases,
            lambda lb_path: parse_generic_label_linkbase(
                lb_path,
                concept_id_map,
                ns_qualified_map=ns_qualified_map,
                schema_ns_map=schema_ns_map,
            ),
            workers=linkbase_workers,
        )
        for _lb_path, parsed in parsed_generic_label_linkbases:
            for qname, labels in parsed.items():
                generic_labels.setdefault(qname, []).extend(labels)

        declared_languages: list[str] = list(
            {
                lb.language
                for labels in list(standard_labels.values()) + list(generic_labels.values())
                for lb in labels
                if lb.language
            }
        )

        label_resolver = LabelResolver.build(
            standard_labels,
            generic_labels,
            self._settings.language_preference,
        )
        progress(f"Labels resolved — {len(declared_languages)} language set(s) available", 3)

        # Step 4: Parse structural linkbases
        progress("Parsing structural linkbases…", 4)
        presentation: dict[str, Any] = {}
        calculation: dict[str, Any] = {}
        definition_arcs: dict[str, Any] = {}
        hypercubes: list[Any] = []

        parsed_presentation_linkbases = _run_path_jobs(
            presentation_linkbases,
            lambda lb_path: parse_presentation_linkbase(lb_path, concept_id_map),
            workers=linkbase_workers,
        )
        presentation_parse_results: list[tuple[Path, PresentationLinkbaseParseResult]] = []
        for _lb_path, result in parsed_presentation_linkbases:
            presentation.update(result.networks)
            presentation_parse_results.append((_lb_path, result))

        parsed_calculation_linkbases = _run_path_jobs(
            calculation_linkbases,
            lambda lb_path: parse_calculation_linkbase(lb_path, concept_id_map),
            workers=linkbase_workers,
        )
        for _lb_path, arcs in parsed_calculation_linkbases:
            for elr, arc_list in arcs.items():
                calculation.setdefault(elr, []).extend(arc_list)

        parsed_definition_linkbases = _run_path_jobs(
            definition_linkbases,
            lambda lb_path: parse_definition_linkbase(
                lb_path,
                concept_id_map,
                ns_qualified_map=ns_qualified_map,
                schema_ns_map=schema_ns_map,
            ),
            workers=linkbase_workers,
        )
        for _lb_path, (arcs_by_elr, hcs, _dims) in parsed_definition_linkbases:
            for elr, arc_list in arcs_by_elr.items():
                definition_arcs.setdefault(elr, []).extend(arc_list)
            hypercubes.extend(hcs)

        concepts = _apply_extensible_enumeration_values(concepts, definition_arcs)

        # Build dimensions once from the complete merged arc set so that
        # domain-member arcs in extension linkbases are correctly associated
        # with their parent dimensions (which may be declared in a different file).
        dimensions = _rebuild_dimensions(definition_arcs, concepts)

        # Step 4b: XBRL Dimensions 1.0 taxonomy constraint checks (xbrldte:* errors)
        declared_roles = set(_PREDEFINED_XBRL_ROLES)
        declared_roles.update(discovered_roles)
        _check_dimensional_constraints(concepts, definition_arcs, declared_roles=declared_roles)
        progress(
            f"Structure mapped — {len(dimensions)} dimensions, {len(hypercubes)} hypercubes",
            4,
        )

        # Step 5: Parse table linkbases
        progress("Parsing table linkbases…", 5)
        tables: list[Any] = []
        parsed_table_linkbases = _run_path_jobs(
            table_linkbases,
            lambda lb_path: parse_table_linkbase(
                lb_path,
                language_preference=tuple(effective_settings.language_preference),
            ),
            workers=linkbase_workers,
            error_message_factory=lambda exc: f"Unexpected error parsing table linkbase: {exc}",
        )
        for _lb_path, parsed_tables in parsed_table_linkbases:
            tables.extend(parsed_tables)

        # Sort tables by the order attribute on group-table arcs in presentation linkbases.
        group_table_order = _build_group_table_order(
            _preferred_group_table_results(presentation_parse_results)
        )
        if group_table_order:
            tables.sort(key=lambda t: group_table_order.get(t.table_id, float("inf")))
        progress(f"Tables prepared — {len(tables)} available", 5)

        # Step 6: Parse formula linkbase (if present)
        progress("Assembling taxonomy structure…", 6)
        from bde_xbrl_editor.taxonomy.models import (  # noqa: PLC0415
            FormulaAssertion,
            FormulaAssertionSet,
        )

        formula_assertion_set: FormulaAssertionSet
        if formula_linkbases:
            all_assertions: list[FormulaAssertion] = []
            parsed_formula_linkbases = _run_path_jobs(
                formula_linkbases,
                parse_formula_linkbase,
                workers=linkbase_workers,
            )
            for _flp, fas in parsed_formula_linkbases:
                all_assertions.extend(fas.assertions)

            parsed_assertion_resource_linkbases = _run_path_jobs(
                all_linkbase_paths,
                parse_assertion_resource_linkbase,
                workers=linkbase_workers,
            )
            assertion_resources: dict[str, list[AssertionTextResource]] = {}
            for _resource_path, resource_map in parsed_assertion_resource_linkbases:
                for assertion_id, resources in resource_map.items():
                    assertion_resources.setdefault(assertion_id, []).extend(resources)

            parsed_assertion_table_linkbases = _run_path_jobs(
                all_linkbase_paths,
                parse_assertion_table_mappings,
                workers=linkbase_workers,
            )
            assertion_table_ids: dict[str, str] = {}
            for _mapping_path, table_map in parsed_assertion_table_linkbases:
                for assertion_id, table_id in table_map.items():
                    assertion_table_ids.setdefault(assertion_id, table_id)

            table_labels = {
                table.table_id: (table.display_code or table.table_id) for table in tables
            }

            language_preference = [*declared_languages, "es", "en"]
            enriched_assertions: list[FormulaAssertion] = []
            for assertion in all_assertions:
                resources = assertion_resources.get(assertion.assertion_id, [])
                table_id = assertion_table_ids.get(assertion.assertion_id)
                enriched_assertions.append(
                    replace(
                        assertion,
                        table_id=table_id,
                        table_label=table_labels.get(table_id) if table_id else None,
                        label_resources=_best_assertion_resources(
                            resources,
                            arcrole=ARCROLE_ELEMENT_LABEL,
                            language_preference=language_preference,
                        ),
                        message_resources=(
                            _best_assertion_resources(
                                resources,
                                arcrole=ARCROLE_ASSERTION_UNSATISFIED_MESSAGE,
                                language_preference=language_preference,
                            )
                            + _best_assertion_resources(
                                resources,
                                arcrole=ARCROLE_ASSERTION_SATISFIED_MESSAGE,
                                language_preference=language_preference,
                            )
                        ),
                    )
                )
            formula_assertion_set = FormulaAssertionSet(assertions=tuple(enriched_assertions))
        else:
            formula_assertion_set = FormulaAssertionSet()

        parsed_custom_function_linkbases = _run_path_jobs(
            all_linkbase_paths,
            parse_custom_function_linkbase,
            workers=linkbase_workers,
        )
        custom_functions: list[CustomFunctionDefinition] = []
        seen_custom_functions: set[tuple[str, tuple[str, ...]]] = set()
        for _custom_linkbase_path, definitions in parsed_custom_function_linkbases:
            for definition in definitions:
                key = (definition.name, definition.input_types)
                if key in seen_custom_functions:
                    continue
                seen_custom_functions.add(key)
                custom_functions.append(definition)

        metadata = _extract_metadata(entry_point, declared_languages)
        progress(f"Assembled {metadata.name} v{metadata.version}", 6)

        # Step 7: Assemble TaxonomyStructure
        structure = TaxonomyStructure(
            metadata=metadata,
            concepts=concepts,
            labels=label_resolver,
            presentation=presentation,
            calculation=calculation,
            definition=definition_arcs,
            hypercubes=hypercubes,
            dimensions=dimensions,
            tables=tables,
            formula_linkbase_path=formula_linkbase_path,
            formula_assertion_set=formula_assertion_set,
            custom_functions=tuple(custom_functions),
            schema_files=tuple(sorted(schema_paths)),
            linkbase_files=tuple(sorted(all_linkbase_paths)),
            schema_substitution_groups=schema_substitution_groups,
        )

        progress("Taxonomy loaded successfully", _TOTAL_STEPS)
        return structure

"""TaxonomyLoader — orchestrates full DTS discovery, parsing, and assembly.

Progress is reported via a plain Python callback (no Qt dependency) so the
taxonomy module remains PySide6-free.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from lxml import etree

from bde_xbrl_editor.taxonomy.cache import TaxonomyCache
from bde_xbrl_editor.taxonomy.constants import (
    ARCROLE_ALL,
    ARCROLE_DIMENSION_DEFAULT,
    ARCROLE_DIMENSION_DOMAIN,
    ARCROLE_DOMAIN_MEMBER,
    ARCROLE_HYPERCUBE_DIMENSION,
    ARCROLE_NOT_ALL,
    NS_FORMULA,
    NS_TABLE_PWD,
    NS_XBRLDT,
)
from bde_xbrl_editor.taxonomy.discovery import discover_dts
from bde_xbrl_editor.taxonomy.label_resolver import LabelResolver
from bde_xbrl_editor.taxonomy.linkbases.calculation import parse_calculation_linkbase
from bde_xbrl_editor.taxonomy.linkbases.definition import parse_definition_linkbase
from bde_xbrl_editor.taxonomy.linkbases.formula import parse_formula_linkbase
from bde_xbrl_editor.taxonomy.linkbases.generic_label import parse_generic_label_linkbase
from bde_xbrl_editor.taxonomy.linkbases.label import parse_label_linkbase
from bde_xbrl_editor.taxonomy.linkbases.presentation import parse_presentation_linkbase
from bde_xbrl_editor.taxonomy.linkbases.table_pwd import parse_table_linkbase
from bde_xbrl_editor.taxonomy.models import (
    Concept,
    DimensionModel,
    DomainMember,
    QName,
    TaxonomyMetadata,
    TaxonomyParseError,
    TaxonomyStructure,
    UnsupportedTaxonomyFormatError,
)
from bde_xbrl_editor.taxonomy.schema import XBRL_SG_ROOTS, parse_schema_raw
from bde_xbrl_editor.taxonomy.settings import LoaderSettings

ProgressCallback = Callable[[str, int, int], None]

# Total loading steps for progress reporting (at least 6)
_TOTAL_STEPS = 7

_NS_XLINK = "http://www.w3.org/1999/xlink"
_XLINK_HREF = f"{{{_NS_XLINK}}}href"


def _sniff_linkbase_type(path: Path) -> str:
    """Return a crude type string for a linkbase file: label/generic/pres/calc/def/table/formula/unknown."""
    name = path.stem.lower()
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
    if "formula" in name or "form" in name:
        return "formula"

    # BDE places all formula linkbases under a subdirectory named "formula/"
    if path.parent.name.lower() == "formula":
        return "formula"

    # Fallback: scan child elements for formula/assertion namespaces
    _FORMULA_NS = {
        "http://xbrl.org/2008/formula",
        "http://xbrl.org/2008/assertion/value",
        "http://xbrl.org/2008/assertion/existence",
        "http://xbrl.org/2008/assertion/consistency",
    }
    try:
        ctx = etree.iterparse(str(path), events=("start",))
        for _, el in ctx:
            tag = str(el.tag)
            if NS_TABLE_PWD in tag:
                return "table"
            ns = tag[1:tag.index("}")] if tag.startswith("{") else ""
            if ns in _FORMULA_NS or NS_FORMULA in tag:
                return "formula"
    except Exception:  # noqa: BLE001
        pass
    return "unknown"


_ARCROLE_GROUP_TABLE = "http://www.eurofiling.info/xbrl/arcrole/group-table"
_NS_XLINK_FULL = "http://www.w3.org/1999/xlink"


def _parse_group_table_order(linkbase_paths: list[Path]) -> dict[str, int]:
    """Parse presentation linkbases for group-table arcrole arcs.

    The BDE taxonomy uses a two-level tree in the presentation linkbase:
      root_concept --[order=N]--> table_group --[order=M]--> table
    or directly:
      root_concept --[order=N]--> table

    This function performs a DFS traversal of that tree (ordered by arc order)
    and assigns each leaf table a flat sequential position (0, 1, 2, ...).

    Returns a mapping of table XML id (fragment) → flat display position.
    Used to sort TaxonomyStructure.tables in the intended display order.
    Tables not referenced in any presentation linkbase are placed last.
    """
    # children[parent_fragment] = [(order, child_fragment)]
    children: dict[str, list[tuple[float, str]]] = {}
    # label_to_href_fragment: xlink:label → href#fragment (only for *-rend.xml locs)
    label_to_fragment: dict[str, str] = {}
    # label_to_is_rend: whether the locator points to a *-rend.xml (i.e., a real table)
    label_is_rend: set[str] = set()
    # Root concept fragment (the "from" side of root→group/table arcs)
    root_fragment: str | None = None

    for lb_path in linkbase_paths:
        lb_type = _sniff_linkbase_type(lb_path)
        if lb_type not in ("pres", "unknown"):
            continue
        try:
            tree = etree.parse(str(lb_path))  # noqa: S320
        except Exception:  # noqa: BLE001
            continue
        root_el = tree.getroot()
        # Build label → href-fragment map from all loc elements
        local_label_to_fragment: dict[str, str] = {}
        local_label_is_rend: set[str] = set()
        for loc in root_el.iter():
            if not isinstance(loc.tag, str):
                continue
            if loc.tag.split("}")[-1] != "loc":
                continue
            label = loc.get(f"{{{_NS_XLINK_FULL}}}label") or ""
            href = loc.get(f"{{{_NS_XLINK_FULL}}}href") or ""
            if label and "#" in href:
                fragment = href.split("#", 1)[1]
                local_label_to_fragment[label] = fragment
                if "-rend.xml" in href:
                    local_label_is_rend.add(label)
        label_to_fragment.update(local_label_to_fragment)
        label_is_rend.update(local_label_is_rend)
        # Collect group-table arcs
        for arc in root_el.iter():
            if not isinstance(arc.tag, str):
                continue
            if arc.tag.split("}")[-1] != "arc":
                continue
            if arc.get(f"{{{_NS_XLINK_FULL}}}arcrole") != _ARCROLE_GROUP_TABLE:
                continue
            from_label = arc.get(f"{{{_NS_XLINK_FULL}}}from") or ""
            to_label = arc.get(f"{{{_NS_XLINK_FULL}}}to") or ""
            from_frag = local_label_to_fragment.get(from_label, from_label)
            to_frag = local_label_to_fragment.get(to_label)
            if not to_frag:
                continue
            try:
                arc_order = float(arc.get("order", "1"))
            except (TypeError, ValueError):
                arc_order = 1.0
            children.setdefault(from_frag, []).append((arc_order, to_frag))
            # The first "from" side that is NOT a rend table is the root
            if root_fragment is None and from_label not in local_label_is_rend:
                root_fragment = from_frag

    if not children or root_fragment is None:
        return {}

    # Sort children by arc order
    for parent in children:
        children[parent].sort(key=lambda x: x[0])

    # Pre-order DFS traversal to assign flat positions to leaf tables.
    # Stack holds items in LIFO order; push children in reverse so the first
    # child (lowest order) is processed next.
    rend_fragments = set(label_to_fragment[lbl] for lbl in label_is_rend)
    flat_order: dict[str, int] = {}
    counter = 0
    stack: list[str] = [root_fragment]
    visited: set[str] = set()
    while stack:
        node = stack.pop()  # LIFO
        if node in visited:
            continue
        visited.add(node)
        if node in rend_fragments:
            flat_order[node] = counter
            counter += 1
        # Push children in REVERSE order so first child (lowest arc order) is on top
        node_children = children.get(node, [])
        for _, child_frag in reversed(node_children):
            if child_frag not in visited:
                stack.append(child_frag)
    return flat_order


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
        tree = etree.parse(str(entry_point))  # noqa: S320
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


_SG_HYPERCUBE = QName(NS_XBRLDT, "hypercubeItem")
_SG_DIMENSION = QName(NS_XBRLDT, "dimensionItem")


def _check_dimensional_constraints(
    concepts: dict[QName, Concept],
    definition_arcs: dict[str, list],
) -> None:
    """Check XBRL Dimensions 1.0 taxonomy structure constraints (xbrldte:* errors).

    Raises TaxonomyParseError with the appropriate xbrldte: error code in the
    message when a constraint is violated. The conformance runner's
    _match_outcome() detects these codes in the exception message.
    """
    # Build lookup: qname → concept
    # Check 1: hypercube items must be abstract (xbrldte:HypercubeElementIsNotAbstractError)
    for qname, concept in concepts.items():
        sg = concept.substitution_group
        if sg and sg.namespace == NS_XBRLDT and sg.local_name == "hypercubeItem" and not concept.abstract:
            raise TaxonomyParseError(
                file_path="",
                message=(
                    f"xbrldte:HypercubeElementIsNotAbstractError: "
                    f"Hypercube element {qname} must be abstract"
                ),
            )
        # Check 2: dimension items must be abstract (xbrldte:DimensionElementIsNotAbstractError)
        if sg and sg.namespace == NS_XBRLDT and sg.local_name == "dimensionItem" and not concept.abstract:
            raise TaxonomyParseError(
                file_path="",
                message=(
                    f"xbrldte:DimensionElementIsNotAbstractError: "
                    f"Dimension element {qname} must be abstract"
                ),
            )

    # Build sets of hypercube/dimension QNames for arc checks
    hypercube_qnames = {
        q for q, c in concepts.items()
        if c.substitution_group and c.substitution_group.namespace == NS_XBRLDT
        and c.substitution_group.local_name == "hypercubeItem"
    }
    dimension_qnames = {
        q for q, c in concepts.items()
        if c.substitution_group and c.substitution_group.namespace == NS_XBRLDT
        and c.substitution_group.local_name == "dimensionItem"
    }

    # Build per-ELR dimension-default tracking to detect too many defaults
    # (xbrldte:TooManyDefaultMembersError)
    # Maps (elr, dim_qname) → set of distinct default-member QNames seen.
    # Duplicate arcs with the same (elr, source, target) in different linkbases
    # are silently skipped per XBRL arc-equivalence rules; only genuinely distinct
    # default members for the same dimension in the same ELR are an error.
    dim_defaults_seen: dict[tuple[str, QName], set[QName]] = {}

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

            # Check 5: target of all/notAll arc must be a hypercube
            # (xbrldte:HasHypercubeTargetError)
            if arcrole in (ARCROLE_ALL, ARCROLE_NOT_ALL):
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

            # Check 7: source of dimension-domain arc must be a dimension item
            # (xbrldte:DimensionDomainSourceError)
            if arcrole == ARCROLE_DIMENSION_DOMAIN and arc.source in concepts and arc.source not in dimension_qnames:
                raise TaxonomyParseError(
                    file_path="",
                    message=(
                        f"xbrldte:DimensionDomainSourceError: "
                        f"Source of dimension-domain arc must be a dimension item, "
                        f"got {arc.source}"
                    ),
                )

            # Check 8: dimension-default arcs — track for too many defaults
            # (xbrldte:TooManyDefaultMembersError)
            if arcrole == ARCROLE_DIMENSION_DEFAULT:
                key = (_elr, arc.source)
                targets = dim_defaults_seen.setdefault(key, set())
                targets.add(arc.target)
                if len(targets) > 1:
                    raise TaxonomyParseError(
                        file_path="",
                        message=(
                            f"xbrldte:TooManyDefaultMembersError: "
                            f"Dimension {arc.source} has more than one default member "
                            f"in ELR {_elr}"
                        ),
                    )



def _rebuild_dimensions(definition_arcs: dict[str, list]) -> dict[QName, DimensionModel]:
    """Build DimensionModel objects by BFS-walking the complete merged definition arc set.

    The per-file approach in parse_definition_linkbase cannot associate domain-member
    arcs from extension linkbases (where dim_domain is not yet known) with their
    parent dimensions.  By using the globally merged definition_arcs we see all arcs
    across all files and correctly populate every dimension's member set.
    """
    dim_domain: dict[QName, QName] = {}  # dimension → root domain concept
    dim_defaults: dict[QName, QName] = {}
    # Children in the domain-member arc graph, indexed by parent concept
    dm_children: dict[QName, list[tuple[QName, float, bool]]] = {}

    for _elr, arcs in definition_arcs.items():
        for arc in arcs:
            if arc.arcrole == ARCROLE_DIMENSION_DOMAIN:
                if arc.source not in dim_domain:
                    dim_domain[arc.source] = arc.target
            elif arc.arcrole == ARCROLE_DOMAIN_MEMBER:
                usable = arc.usable if arc.usable is not None else True
                dm_children.setdefault(arc.source, []).append(
                    (arc.target, arc.order, usable)
                )
            elif arc.arcrole == ARCROLE_DIMENSION_DEFAULT:
                dim_defaults[arc.source] = arc.target

    dimensions: dict[QName, DimensionModel] = {}
    for dim_q, domain_q in dim_domain.items():
        # BFS from the root domain concept to collect all members transitively
        all_members: list[DomainMember] = []
        visited: set[QName] = set()
        # queue entries: (concept, parent, order, usable)
        queue: list[tuple[QName, QName | None, float, bool]] = [
            (domain_q, None, 1.0, True)
        ]
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
            dimension_type="explicit",
            default_member=dim_defaults.get(dim_q),
            domain=domain_q,
            members=tuple(all_members),
        )

    return dimensions


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
                progress_callback("Loaded from cache", _TOTAL_STEPS, _TOTAL_STEPS)
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

        # Step 1: DTS discovery
        progress("Discovering DTS…", 1)
        schema_paths, linkbase_paths, skipped_urls, include_ns_map = discover_dts(
            entry_point, self._settings, progress_callback=None,
        )
        self._last_skipped_urls: list[str] = skipped_urls

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
        for schema_path in schema_paths:
            ns_override = include_ns_map.get(schema_path)
            try:
                raw, target_ns = parse_schema_raw(schema_path, ns_override)
                all_candidates.update(raw)
                if target_ns:
                    schema_path_to_ns[str(schema_path)] = target_ns
            except TaxonomyParseError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise TaxonomyParseError(
                    file_path=str(schema_path),
                    message=f"Unexpected error: {exc}",
                ) from exc

        # Transitive closure: start with concepts whose SG is a known XBRL root,
        # then iteratively promote candidates whose SG is already resolved.
        concepts: dict[QName, Concept] = {
            qn: c for qn, (c, sg) in all_candidates.items() if sg in XBRL_SG_ROOTS
        }
        pending = [
            (qn, c, sg) for qn, (c, sg) in all_candidates.items() if sg not in XBRL_SG_ROOTS
        ]
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
            raise UnsupportedTaxonomyFormatError(
                entry_point=str(entry_point),
                reason="No XBRL concepts found — file may not be a valid XBRL taxonomy entry point",
            )

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
        if self._settings.local_catalog:
            for url_prefix, local_root in self._settings.local_catalog.items():
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
        formula_linkbase_paths: list[Path] = []

        for lb_path in linkbase_paths:
            lb_type = _sniff_linkbase_type(lb_path)
            if lb_type == "formula":
                formula_linkbase_paths.append(lb_path)
                if formula_linkbase_path is None:
                    formula_linkbase_path = lb_path
                continue
            if lb_type == "label":
                parsed = parse_label_linkbase(lb_path, concept_id_map)
                for qname, labels in parsed.items():
                    standard_labels.setdefault(qname, []).extend(labels)
            elif lb_type == "generic":
                parsed = parse_generic_label_linkbase(lb_path, concept_id_map)
                for qname, labels in parsed.items():
                    generic_labels.setdefault(qname, []).extend(labels)

        declared_languages: list[str] = list({
            lb.language
            for labels in list(standard_labels.values()) + list(generic_labels.values())
            for lb in labels
            if lb.language
        })

        label_resolver = LabelResolver.build(
            standard_labels, generic_labels,
            self._settings.language_preference,
        )

        # Step 4: Parse structural linkbases
        progress("Parsing structural linkbases…", 4)
        presentation: dict[str, Any] = {}
        calculation: dict[str, Any] = {}
        definition_arcs: dict[str, Any] = {}
        hypercubes: list[Any] = []

        for lb_path in linkbase_paths:
            lb_type = _sniff_linkbase_type(lb_path)
            try:
                if lb_type == "pres":
                    nets = parse_presentation_linkbase(lb_path, concept_id_map)
                    presentation.update(nets)
                elif lb_type == "calc":
                    arcs = parse_calculation_linkbase(lb_path, concept_id_map)
                    for elr, arc_list in arcs.items():
                        calculation.setdefault(elr, []).extend(arc_list)
                elif lb_type == "def":
                    arcs_by_elr, hcs, _dims = parse_definition_linkbase(
                        lb_path, concept_id_map,
                        ns_qualified_map=ns_qualified_map,
                        schema_ns_map=schema_ns_map,
                    )
                    for elr, arc_list in arcs_by_elr.items():
                        definition_arcs.setdefault(elr, []).extend(arc_list)
                    hypercubes.extend(hcs)
            except TaxonomyParseError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise TaxonomyParseError(
                    file_path=str(lb_path),
                    message=f"Unexpected error: {exc}",
                ) from exc

        # Build dimensions once from the complete merged arc set so that
        # domain-member arcs in extension linkbases are correctly associated
        # with their parent dimensions (which may be declared in a different file).
        dimensions = _rebuild_dimensions(definition_arcs)

        # Step 4b: XBRL Dimensions 1.0 taxonomy constraint checks (xbrldte:* errors)
        _check_dimensional_constraints(concepts, definition_arcs)

        # Step 5: Parse table linkbases
        progress("Parsing table linkbases…", 5)
        tables: list[Any] = []
        for lb_path in linkbase_paths:
            lb_type = _sniff_linkbase_type(lb_path)
            if lb_type == "table":
                try:
                    parsed_tables = parse_table_linkbase(lb_path)
                    tables.extend(parsed_tables)
                except TaxonomyParseError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    raise TaxonomyParseError(
                        file_path=str(lb_path),
                        message=f"Unexpected error parsing table linkbase: {exc}",
                    ) from exc

        # Sort tables by the order attribute on group-table arcs in presentation linkbases.
        group_table_order = _parse_group_table_order(list(linkbase_paths))
        if group_table_order:
            tables.sort(key=lambda t: group_table_order.get(t.table_id, float("inf")))

        # Step 6: Parse formula linkbase (if present)
        progress("Assembling taxonomy structure…", 6)
        from bde_xbrl_editor.taxonomy.models import (  # noqa: PLC0415
            FormulaAssertion,
            FormulaAssertionSet,
        )

        formula_assertion_set: FormulaAssertionSet
        if formula_linkbase_paths:
            all_assertions: list[FormulaAssertion] = []
            for flp in formula_linkbase_paths:
                fas = parse_formula_linkbase(flp)
                all_assertions.extend(fas.assertions)
            formula_assertion_set = FormulaAssertionSet(assertions=tuple(all_assertions))
        else:
            formula_assertion_set = FormulaAssertionSet()

        metadata = _extract_metadata(entry_point, declared_languages)

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
            schema_files=tuple(sorted(schema_paths)),
            linkbase_files=tuple(sorted(linkbase_paths)),
        )

        progress("Taxonomy loaded successfully", _TOTAL_STEPS)
        return structure

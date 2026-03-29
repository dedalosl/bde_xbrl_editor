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
    NS_FORMULA,
    NS_TABLE_PWD,
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
    QName,
    TaxonomyMetadata,
    TaxonomyParseError,
    TaxonomyStructure,
    UnsupportedTaxonomyFormatError,
)
from bde_xbrl_editor.taxonomy.schema import parse_schema
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
    if "table" in name or "tbl" in name:
        return "table"
    if "formula" in name or "form" in name:
        return "formula"

    # Try to detect by root element namespace
    try:
        ctx = etree.iterparse(str(path), events=("start",))
        for _, el in ctx:
            if NS_TABLE_PWD in str(el.tag):
                return "table"
            if NS_FORMULA in str(el.tag):
                return "formula"
            break
    except Exception:  # noqa: BLE001
        pass
    return "unknown"


def _build_concept_id_map(concepts: dict[QName, Concept]) -> dict[str, QName]:
    """Build a map from XML id-style fragment → QName.

    XBRL uses element @id attributes of the form "{prefix}_{localName}" or
    just "{localName}" as XLink locator href fragments.
    """
    id_map: dict[str, QName] = {}
    for qname in concepts:
        # Standard XBRL id: prefixed or bare local name
        id_map[qname.local_name] = qname
        if qname.prefix:
            id_map[f"{qname.prefix}_{qname.local_name}"] = qname
        # Also add namespace-derived prefix
        ns_short = qname.namespace.rstrip("/").split("/")[-1].replace("-", "").replace(".", "")[:8]
        id_map[f"{ns_short}_{qname.local_name}"] = qname
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
        schema_paths, linkbase_paths, skipped_urls = discover_dts(
            entry_point, self._settings, progress_callback=None
        )
        self._last_skipped_urls: list[str] = skipped_urls

        # Step 2: Parse schemas → concepts
        progress("Parsing schemas…", 2)
        concepts: dict[QName, Concept] = {}
        for schema_path in schema_paths:
            try:
                parsed = parse_schema(schema_path)
                concepts.update(parsed)
            except TaxonomyParseError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise TaxonomyParseError(
                    file_path=str(schema_path),
                    message=f"Unexpected error: {exc}",
                ) from exc

        if not concepts:
            raise UnsupportedTaxonomyFormatError(
                entry_point=str(entry_point),
                reason="No XBRL concepts found — file may not be a valid XBRL taxonomy entry point",
            )

        concept_id_map = _build_concept_id_map(concepts)

        # Step 3: Parse label linkbases
        progress("Parsing label linkbases…", 3)
        standard_labels: dict[QName, list] = {}
        generic_labels: dict[QName, list] = {}
        formula_linkbase_path: Path | None = None

        for lb_path in linkbase_paths:
            lb_type = _sniff_linkbase_type(lb_path)
            if lb_type == "formula":
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
        dimensions: dict[Any, Any] = {}

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
                    arcs_by_elr, hcs, dims = parse_definition_linkbase(lb_path, concept_id_map)
                    for elr, arc_list in arcs_by_elr.items():
                        definition_arcs.setdefault(elr, []).extend(arc_list)
                    hypercubes.extend(hcs)
                    dimensions.update(dims)
            except TaxonomyParseError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise TaxonomyParseError(
                    file_path=str(lb_path),
                    message=f"Unexpected error: {exc}",
                ) from exc

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

        # Step 6: Parse formula linkbase (if present)
        progress("Assembling taxonomy structure…", 6)
        from bde_xbrl_editor.taxonomy.models import FormulaAssertionSet  # noqa: PLC0415

        formula_assertion_set: FormulaAssertionSet
        if formula_linkbase_path is not None:
            formula_assertion_set = parse_formula_linkbase(formula_linkbase_path)
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
        )

        progress("Taxonomy loaded successfully", _TOTAL_STEPS)
        return structure

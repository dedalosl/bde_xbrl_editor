"""Taxonomy relationship-set checks for XBRL linkbase declarations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from lxml import etree

from bde_xbrl_editor.taxonomy.constants import NS_LINK, NS_XLINK
from bde_xbrl_editor.taxonomy.models import TaxonomyStructure
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity

_XLINK_TYPE = f"{{{NS_XLINK}}}type"
_XLINK_HREF = f"{{{NS_XLINK}}}href"
_XLINK_LABEL = f"{{{NS_XLINK}}}label"
_XLINK_FROM = f"{{{NS_XLINK}}}from"
_XLINK_TO = f"{{{NS_XLINK}}}to"
_XLINK_ROLE = f"{{{NS_XLINK}}}role"
_XLINK_ARCROLE = f"{{{NS_XLINK}}}arcrole"
_ROLE_TYPE = f"{{{NS_LINK}}}roleType"
_ARCROLE_TYPE = f"{{{NS_LINK}}}arcroleType"
_USED_ON = f"{{{NS_LINK}}}usedOn"
_ARCROLE_REF = f"{{{NS_LINK}}}arcroleRef"
_LOC = f"{{{NS_LINK}}}loc"

_STANDARD_ARCROLE_CYCLES = {
    "http://www.xbrl.org/2003/arcrole/parent-child": "undirected",
    "http://www.xbrl.org/2003/arcrole/summation-item": "any",
    "https://xbrl.org/2023/arcrole/summation-item": "any",
    "http://www.xbrl.org/2003/arcrole/general-special": "undirected",
    "http://www.xbrl.org/2003/arcrole/essence-alias": "undirected",
    "http://www.xbrl.org/2003/arcrole/similar-tuples": "undirected",
    "http://www.xbrl.org/2003/arcrole/requires-element": "undirected",
    "http://www.xbrl.org/2003/arcrole/concept-label": "any",
    "http://www.xbrl.org/2003/arcrole/concept-reference": "any",
    "http://xbrl.org/int/dim/arcrole/all": "none",
    "http://xbrl.org/int/dim/arcrole/notAll": "none",
    "http://xbrl.org/int/dim/arcrole/hypercube-dimension": "none",
    "http://xbrl.org/int/dim/arcrole/dimension-domain": "none",
    "http://xbrl.org/int/dim/arcrole/domain-member": "undirected",
    "http://xbrl.org/int/dim/arcrole/dimension-default": "none",
}
_STANDARD_ARC_ELEMENTS = {
    "calculationArc",
    "definitionArc",
    "labelArc",
    "presentationArc",
    "referenceArc",
}
_STANDARD_LINK_ELEMENTS = {
    "calculationLink",
    "definitionLink",
    "footnoteLink",
    "labelLink",
    "presentationLink",
    "referenceLink",
}
_STANDARD_ROLE_ELEMENTS = _STANDARD_LINK_ELEMENTS | {"footnote", "label", "reference"}


@dataclass(frozen=True)
class _ArcroleDeclaration:
    uri: str
    cycles_allowed: str
    used_on: frozenset[str]
    source_path: Path
    xml_id: str | None

    @property
    def signature(self) -> tuple[str, frozenset[str]]:
        return (self.cycles_allowed, self.used_on)


@dataclass(frozen=True)
class _ArcUse:
    arcrole: str
    link_tag: str
    arc_tag: str
    extended_link_role: str
    source: str
    target: str
    source_path: Path
    priority: int


@dataclass(frozen=True)
class _RoleDeclaration:
    uri: str
    used_on: frozenset[str]


def _finding(rule_id: str, message: str) -> ValidationFinding:
    return ValidationFinding(
        rule_id=rule_id,
        severity=ValidationSeverity.ERROR,
        message=message,
        source="relationships",
    )


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _used_on_key(raw: str, ns_map: dict[str | None, str]) -> str:
    if ":" not in raw:
        return raw
    prefix, local = raw.split(":", 1)
    namespace = ns_map.get(prefix)
    return f"{{{namespace}}}{local}" if namespace else local


def _tag_key(tag: str) -> str:
    return tag if tag.startswith("{") else _local_name(tag)


def _load_roots(paths: tuple[Path, ...]) -> list[tuple[Path, etree._Element]]:
    roots: list[tuple[Path, etree._Element]] = []
    for path in paths:
        if not path.exists():
            continue
        try:
            roots.append((path, parse_xml_file(path).getroot()))
        except etree.XMLSyntaxError:
            continue
    return roots


def _resource_node_id(path: Path, link_el: etree._Element, resource_el: etree._Element) -> str:
    line = resource_el.sourceline if resource_el.sourceline is not None else "unknown"
    link_line = link_el.sourceline if link_el.sourceline is not None else "unknown"
    label = resource_el.get(_XLINK_LABEL, "")
    return f"{path.resolve().as_posix()}#resource:{link_line}:{line}:{label}"


def _link_local_node_id(path: Path, link_el: etree._Element, label: str) -> str:
    line = link_el.sourceline if link_el.sourceline is not None else "unknown"
    return f"{path.resolve().as_posix()}#link-label:{line}:{label}"


class _HrefResolver:
    def __init__(self, paths: tuple[Path, ...]) -> None:
        self._loaded_paths = tuple(path.resolve() for path in paths if path.exists())

    def canonicalize(self, href: str, base_path: Path) -> str:
        file_part, sep, fragment = href.partition("#")
        if not sep:
            return href
        parsed = urlparse(file_part)
        if parsed.scheme in {"http", "https"}:
            remote_suffix = (
                Path(parsed.netloc, parsed.path.lstrip("/"))
                if parsed.netloc and parsed.path
                else None
            )
            if remote_suffix is not None:
                for path in self._loaded_paths:
                    if (
                        len(path.parts) >= len(remote_suffix.parts)
                        and path.parts[-len(remote_suffix.parts) :] == remote_suffix.parts
                    ):
                        return f"{path.as_posix()}#{fragment}"
            return href
        if file_part:
            return f"{(base_path.parent / file_part).resolve().as_posix()}#{fragment}"
        return f"{base_path.resolve().as_posix()}#{fragment}"


def _collect_arcrole_declarations(
    roots: list[tuple[Path, etree._Element]],
) -> dict[str, list[_ArcroleDeclaration]]:
    declarations: dict[str, list[_ArcroleDeclaration]] = defaultdict(list)
    for path, root in roots:
        for el in root.iter(_ARCROLE_TYPE):
            uri = (el.get("arcroleURI") or "").strip()
            if not uri:
                continue
            used_on = frozenset(
                _used_on_key((child.text or "").strip(), child.nsmap or {})
                for child in el.iterchildren(_USED_ON)
                if (child.text or "").strip()
            )
            declarations[uri].append(
                _ArcroleDeclaration(
                    uri=uri,
                    cycles_allowed=(el.get("cyclesAllowed") or "any").strip() or "any",
                    used_on=used_on,
                    source_path=path,
                    xml_id=el.get("id") or None,
                )
            )
    return declarations


def _collect_role_declarations(
    roots: list[tuple[Path, etree._Element]],
) -> dict[str, list[_RoleDeclaration]]:
    declarations: dict[str, list[_RoleDeclaration]] = defaultdict(list)
    for _path, root in roots:
        for el in root.iter(_ROLE_TYPE):
            uri = (el.get("roleURI") or "").strip()
            if not uri:
                continue
            used_on = frozenset(
                _used_on_key((child.text or "").strip(), child.nsmap or {})
                for child in el.iterchildren(_USED_ON)
                if (child.text or "").strip()
            )
            declarations[uri].append(_RoleDeclaration(uri=uri, used_on=used_on))
    return declarations


def _declaration_by_href(
    href: str,
    base_path: Path,
    declarations: dict[str, list[_ArcroleDeclaration]],
) -> _ArcroleDeclaration | None:
    file_part, sep, fragment = href.partition("#")
    if not sep or not fragment:
        return None
    parsed = urlparse(file_part)
    target_path = (
        None
        if parsed.scheme in {"http", "https"}
        else (base_path.parent / file_part).resolve()
        if file_part
        else base_path.resolve()
    )
    remote_suffix = (
        Path(parsed.netloc, parsed.path.lstrip("/"))
        if parsed.scheme in {"http", "https"} and parsed.netloc and parsed.path
        else None
    )
    for decls in declarations.values():
        for decl in decls:
            source_path = decl.source_path.resolve()
            if target_path is not None and source_path == target_path and decl.xml_id == fragment:
                return decl
            if (
                remote_suffix is not None
                and decl.xml_id == fragment
                and len(source_path.parts) >= len(remote_suffix.parts)
                and source_path.parts[-len(remote_suffix.parts) :] == remote_suffix.parts
            ):
                return decl
    return None


def _collect_arcs(
    roots: list[tuple[Path, etree._Element]],
    declarations: dict[str, list[_ArcroleDeclaration]],
    href_resolver: _HrefResolver,
) -> tuple[list[_ArcUse], set[str], list[ValidationFinding]]:
    arcs: list[_ArcUse] = []
    prohibited: dict[tuple[str, str, str, str, str, str], int] = {}
    referenced_arcroles: set[str] = set()
    findings: list[ValidationFinding] = []

    for path, root in roots:
        for ref in root.iter(_ARCROLE_REF):
            arcrole_uri = (ref.get("arcroleURI") or "").strip()
            href = (ref.get(_XLINK_HREF) or "").strip()
            decl = _declaration_by_href(href, path, declarations) if href else None
            if decl is not None and arcrole_uri and decl.uri != arcrole_uri:
                findings.append(
                    _finding(
                        "xbrl:arcrole-ref-mismatch",
                        f"arcroleRef '{arcrole_uri}' points to declaration '{decl.uri}'",
                    )
                )
            elif arcrole_uri and (decl is not None or arcrole_uri in declarations):
                referenced_arcroles.add(arcrole_uri)

        for link_el in root.iter():
            if not isinstance(link_el.tag, str) or link_el.get(_XLINK_TYPE) != "extended":
                continue
            link_tag = _local_name(link_el.tag)
            elr = link_el.get(_XLINK_ROLE, "http://www.xbrl.org/2003/role/link")
            locs = {
                loc.get(_XLINK_LABEL, ""): href_resolver.canonicalize(
                    loc.get(_XLINK_HREF, ""),
                    path,
                )
                for loc in link_el.iterchildren(_LOC)
            }
            resources = {
                child.get(_XLINK_LABEL, ""): _resource_node_id(path, link_el, child)
                for child in link_el.iterchildren()
                if isinstance(child.tag, str)
                and child.get(_XLINK_TYPE) == "resource"
                and child.get(_XLINK_LABEL)
            }
            for arc_el in link_el.iterchildren():
                if not isinstance(arc_el.tag, str) or arc_el.get(_XLINK_TYPE) != "arc":
                    continue
                arcrole = (arc_el.get(_XLINK_ARCROLE) or "").strip()
                if not arcrole:
                    continue
                frm = arc_el.get(_XLINK_FROM, "")
                to = arc_el.get(_XLINK_TO, "")
                source = (
                    locs.get(frm)
                    or resources.get(frm)
                    or _link_local_node_id(path, link_el, frm)
                )
                target = (
                    locs.get(to)
                    or resources.get(to)
                    or _link_local_node_id(path, link_el, to)
                )
                try:
                    priority = int(arc_el.get("priority", "0"))
                except ValueError:
                    priority = 0
                if (arc_el.get("use") or "optional") == "prohibited":
                    key = (arcrole, link_tag, _local_name(arc_el.tag), elr, source, target)
                    prohibited[key] = max(priority, prohibited.get(key, priority))
                    continue
                arcs.append(
                    _ArcUse(
                        arcrole=arcrole,
                        link_tag=link_tag,
                        arc_tag=_local_name(arc_el.tag),
                        extended_link_role=elr,
                        source=source,
                        target=target,
                        source_path=path,
                        priority=priority,
                    )
                )
    arcs = [
        arc
        for arc in arcs
        if (
            arc.arcrole,
            arc.link_tag,
            arc.arc_tag,
            arc.extended_link_role,
            arc.source,
            arc.target,
        )
        not in prohibited
        or prohibited[
            (
                arc.arcrole,
                arc.link_tag,
                arc.arc_tag,
                arc.extended_link_role,
                arc.source,
                arc.target,
            )
        ]
        < arc.priority
    ]
    return arcs, referenced_arcroles, findings


def _has_directed_cycle(edges: set[tuple[str, str]]) -> bool:
    graph: dict[str, set[str]] = defaultdict(set)
    for source, target in edges:
        graph[source].add(target)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for child in graph.get(node, ()):
            if visit(child):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def _has_undirected_cycle(edges: set[tuple[str, str]]) -> bool:
    parent: dict[str, str] = {}

    def find(node: str) -> str:
        parent.setdefault(node, node)
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for source, target in edges:
        if source == target:
            return True
        root_source = find(source)
        root_target = find(target)
        if root_source == root_target:
            return True
        parent[root_source] = root_target
    return False


class RelationshipSetValidator:
    """Validate DTS role/arcrole declarations and relationship cycles."""

    def validate_taxonomy(self, taxonomy: TaxonomyStructure) -> list[ValidationFinding]:
        loaded_paths = tuple(taxonomy.schema_files) + tuple(taxonomy.linkbase_files)
        roots = _load_roots(loaded_paths)
        href_resolver = _HrefResolver(loaded_paths)
        role_declarations = _collect_role_declarations(roots)
        declarations = _collect_arcrole_declarations(roots)
        arcs, referenced_arcroles, findings = _collect_arcs(
            roots,
            declarations,
            href_resolver,
        )

        for _path, root in roots:
            for el in root.iter():
                if not isinstance(el.tag, str):
                    continue
                role_uri = (el.get(_XLINK_ROLE) or "").strip()
                if not role_uri or role_uri not in role_declarations:
                    continue
                tag = _local_name(el.tag)
                if tag not in _STANDARD_ROLE_ELEMENTS:
                    continue
                used_on = set().union(*(decl.used_on for decl in role_declarations[role_uri]))
                if used_on and _tag_key(el.tag) not in used_on and tag not in used_on:
                    findings.append(
                        _finding(
                            "xbrl:role-used-on",
                            f"Role '{role_uri}' is used on {tag}, "
                            f"but is declared for {sorted(used_on)}",
                        )
                    )

        for uri, decls in declarations.items():
            signatures = {decl.signature for decl in decls}
            source_paths = [decl.source_path.resolve() for decl in decls]
            if len(signatures) > 1 or len(source_paths) != len(set(source_paths)):
                findings.append(
                    _finding(
                        "xbrl:arcrole-declaration-duplicate",
                        f"Arcrole '{uri}' is declared with non-equivalent definitions",
                    )
                )

        for arc in arcs:
            decls = declarations.get(arc.arcrole, [])
            declared_and_referenced = bool(decls) and arc.arcrole in referenced_arcroles
            if declared_and_referenced:
                used_on = set().union(*(decl.used_on for decl in decls))
                arc_key = f"{{{NS_LINK}}}{arc.arc_tag}"
                if (
                    used_on
                    and arc.arc_tag in _STANDARD_ARC_ELEMENTS
                    and arc.arc_tag not in used_on
                    and arc_key not in used_on
                ):
                    findings.append(
                        _finding(
                            "xbrl:arcrole-used-on",
                            f"Arcrole '{arc.arcrole}' is used on {arc.arc_tag}, "
                            f"but is declared for {sorted(used_on)}",
                        )
                    )
            elif arc.arcrole not in _STANDARD_ARCROLE_CYCLES and arc.arc_tag in _STANDARD_ARC_ELEMENTS:
                findings.append(
                    _finding(
                        "xbrl:arcrole-undeclared",
                        f"Arcrole '{arc.arcrole}' is used but not declared in the DTS",
                    )
                )

        edges_by_base_set: dict[tuple[str, str, str, str], set[tuple[str, str]]] = defaultdict(set)
        for arc in arcs:
            if not arc.source or not arc.target:
                continue
            key = (arc.arcrole, arc.link_tag, arc.arc_tag, arc.extended_link_role)
            edges_by_base_set[key].add((arc.source, arc.target))

        for (arcrole, link_tag, arc_tag, elr), edges in edges_by_base_set.items():
            if arcrole not in _STANDARD_ARCROLE_CYCLES and arcrole not in referenced_arcroles:
                continue
            decl = declarations.get(arcrole, [None])[0]
            cycles_allowed = (
                decl.cycles_allowed
                if decl is not None
                else _STANDARD_ARCROLE_CYCLES.get(arcrole, "any")
            )
            if cycles_allowed == "any":
                continue
            if cycles_allowed == "none" and _has_undirected_cycle(edges):
                findings.append(
                    _finding(
                        "xbrl:relationship-cycle",
                        f"Relationship set {arcrole} in {link_tag}/{arc_tag} "
                        f"({elr}) contains a cycle but declares cyclesAllowed='none'",
                    )
                )
            elif cycles_allowed == "undirected" and _has_directed_cycle(edges):
                findings.append(
                    _finding(
                        "xbrl:relationship-directed-cycle",
                        f"Relationship set {arcrole} in {link_tag}/{arc_tag} "
                        f"({elr}) contains a directed cycle",
                    )
                )

        return findings

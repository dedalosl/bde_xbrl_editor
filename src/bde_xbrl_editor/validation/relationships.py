"""Taxonomy relationship-set checks for XBRL linkbase declarations."""

from __future__ import annotations

import re
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
_ROLE_REF = f"{{{NS_LINK}}}roleRef"
_LOC = f"{{{NS_LINK}}}loc"
_LABEL = f"{{{NS_LINK}}}label"
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_NCNAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")

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
_STANDARD_ARCROLE_ALLOWED_ON = {
    "http://www.xbrl.org/2003/arcrole/parent-child": {"presentationArc"},
    "http://www.xbrl.org/2003/arcrole/summation-item": {"calculationArc"},
    "https://xbrl.org/2023/arcrole/summation-item": {"calculationArc"},
    "http://www.xbrl.org/2003/arcrole/general-special": {"definitionArc"},
    "http://www.xbrl.org/2003/arcrole/essence-alias": {"definitionArc"},
    "http://www.xbrl.org/2003/arcrole/similar-tuples": {"definitionArc"},
    "http://www.xbrl.org/2003/arcrole/requires-element": {"definitionArc"},
    "http://www.xbrl.org/2003/arcrole/concept-label": {"labelArc"},
    "http://www.xbrl.org/2003/arcrole/concept-reference": {"referenceArc"},
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
_STANDARD_ROLE_ALLOWED_ON = {
    "http://www.xbrl.org/2003/role/link": _STANDARD_LINK_ELEMENTS,
    "http://www.xbrl.org/2003/role/label": {"label"},
    "http://www.xbrl.org/2003/role/terseLabel": {"label"},
    "http://www.xbrl.org/2003/role/verboseLabel": {"label"},
    "http://www.xbrl.org/2003/role/positiveLabel": {"label"},
    "http://www.xbrl.org/2003/role/negativeLabel": {"label"},
    "http://www.xbrl.org/2003/role/zeroLabel": {"label"},
    "http://www.xbrl.org/2003/role/totalLabel": {"label"},
    "http://www.xbrl.org/2003/role/periodStartLabel": {"label"},
    "http://www.xbrl.org/2003/role/periodEndLabel": {"label"},
    "http://www.xbrl.org/2003/role/documentation": {"label", "reference"},
}


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
    use: str = "optional"
    source_from_loc: bool = False
    target_from_loc: bool = False
    target_from_resource: bool = False


@dataclass(frozen=True)
class _RoleDeclaration:
    uri: str
    used_on: frozenset[str]
    source_path: Path
    xml_id: str | None

    @property
    def signature(self) -> frozenset[str]:
        return self.used_on


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
        namespace = ns_map.get(None)
        return f"{{{namespace}}}{raw}" if namespace else raw
    prefix, local = raw.split(":", 1)
    namespace = ns_map.get(prefix)
    return f"{{{namespace}}}{local}" if namespace else local


def _tag_key(tag: str) -> str:
    return tag if tag.startswith("{") else _local_name(tag)


def _has_inherited_xml_lang(el: etree._Element) -> bool:
    current: etree._Element | None = el
    while current is not None:
        if current.get(_XML_LANG) is not None:
            return True
        current = current.getparent()
    return False


def _is_absolute_uri(raw: str) -> bool:
    parsed = urlparse(raw)
    return bool(parsed.scheme) and not raw.startswith("#")


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


def _used_on_values(el: etree._Element) -> list[str]:
    return [
        _used_on_key((child.text or "").strip(), child.nsmap or {})
        for child in el.iterchildren(_USED_ON)
        if (child.text or "").strip()
    ]


def _collect_declaration_findings(
    roots: list[tuple[Path, etree._Element]],
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for _path, root in roots:
        for el in root.iter():
            if not isinstance(el.tag, str):
                continue
            if el.tag == _ROLE_TYPE:
                xml_id = (el.get("id") or "").strip()
                if xml_id and not _NCNAME_RE.fullmatch(xml_id):
                    findings.append(_finding("xbrl:role-type-id", "roleType id is not an NCName"))
                role_uri = (el.get("roleURI") or "").strip()
                if not role_uri:
                    findings.append(
                        _finding("xbrl:role-type-uri", "roleType roleURI is missing or empty")
                    )
                used_on = _used_on_values(el)
                if len(used_on) != len(set(used_on)):
                    findings.append(
                        _finding(
                            "xbrl:role-used-on-duplicate", "roleType has duplicate usedOn values"
                        )
                    )
            elif el.tag == _ARCROLE_TYPE:
                xml_id = (el.get("id") or "").strip()
                if xml_id and not _NCNAME_RE.fullmatch(xml_id):
                    findings.append(
                        _finding("xbrl:arcrole-type-id", "arcroleType id is not an NCName")
                    )
                arcrole_uri = (el.get("arcroleURI") or "").strip()
                if not arcrole_uri or not _is_absolute_uri(arcrole_uri):
                    findings.append(
                        _finding(
                            "xbrl:arcrole-type-uri",
                            "arcroleType arcroleURI is missing or not absolute",
                        )
                    )
                cycles_allowed = (el.get("cyclesAllowed") or "").strip()
                if cycles_allowed not in {"any", "undirected", "none"}:
                    findings.append(
                        _finding(
                            "xbrl:arcrole-cycles-allowed",
                            "arcroleType cyclesAllowed must be any, undirected, or none",
                        )
                    )
                used_on = _used_on_values(el)
                if len(used_on) != len(set(used_on)):
                    findings.append(
                        _finding(
                            "xbrl:arcrole-used-on-duplicate",
                            "arcroleType has duplicate usedOn values",
                        )
                    )
            elif _local_name(el.tag) in {"roleType", "arcroleType"} and not el.tag.startswith(
                f"{{{NS_LINK}}}"
            ):
                findings.append(
                    _finding(
                        "xbrl:appinfo-declaration-element",
                        f"{_local_name(el.tag)} is not in the XBRL linkbase namespace",
                    )
                )
    return findings


def _collect_role_declarations(
    roots: list[tuple[Path, etree._Element]],
) -> dict[str, list[_RoleDeclaration]]:
    declarations: dict[str, list[_RoleDeclaration]] = defaultdict(list)
    for path, root in roots:
        for el in root.iter(_ROLE_TYPE):
            uri = (el.get("roleURI") or "").strip()
            if not uri:
                continue
            used_on = frozenset(
                _used_on_key((child.text or "").strip(), child.nsmap or {})
                for child in el.iterchildren(_USED_ON)
                if (child.text or "").strip()
            )
            declarations[uri].append(
                _RoleDeclaration(uri=uri, used_on=used_on, source_path=path, xml_id=el.get("id"))
            )
    return declarations


def _role_declaration_by_href(
    href: str,
    base_path: Path,
    declarations: dict[str, list[_RoleDeclaration]],
) -> _RoleDeclaration | None:
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
    for decls in declarations.values():
        for decl in decls:
            if (
                target_path is not None
                and decl.source_path.resolve() == target_path
                and decl.xml_id == fragment
            ):
                return decl
    return None


def _collect_role_ref_findings(
    roots: list[tuple[Path, etree._Element]],
    declarations: dict[str, list[_RoleDeclaration]],
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for path, root in roots:
        refs_by_parent: dict[int, set[str]] = defaultdict(set)
        for ref in root.iter(_ROLE_REF):
            role_uri = (ref.get("roleURI") or "").strip()
            parent = ref.getparent()
            parent_id = id(parent) if parent is not None else id(root)
            if role_uri in refs_by_parent[parent_id]:
                findings.append(
                    _finding("xbrl:duplicate-role-ref", f"Duplicate roleRef '{role_uri}'")
                )
                continue
            refs_by_parent[parent_id].add(role_uri)
            href = (ref.get(_XLINK_HREF) or "").strip()
            decl = _role_declaration_by_href(href, path, declarations) if href else None
            if decl is not None and role_uri and decl.uri != role_uri:
                findings.append(
                    _finding(
                        "xbrl:role-ref-mismatch",
                        f"roleRef '{role_uri}' points to declaration '{decl.uri}'",
                    )
                )
    return findings


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


def _is_schema_concept_href(href: str) -> bool:
    lowered = href.lower()
    return ".xsd#" in lowered or lowered.endswith(".xsd")


def _arc_equivalence_key(arc: _ArcUse) -> tuple[str, str, str, str, str, str]:
    return (
        arc.arcrole,
        arc.link_tag,
        arc.arc_tag,
        arc.extended_link_role,
        arc.source,
        arc.target,
    )


def _effective_relationship_arcs(all_arcs: list[_ArcUse]) -> list[_ArcUse]:
    """Resolve equivalent arcs by priority tier (summation-item override semantics)."""
    groups: dict[tuple[str, str, str, str, str, str], list[_ArcUse]] = defaultdict(list)
    for arc in all_arcs:
        groups[_arc_equivalence_key(arc)].append(arc)

    effective: list[_ArcUse] = []
    for group in groups.values():
        max_pri = max(arc.priority for arc in group)
        tier = [arc for arc in group if arc.priority == max_pri]
        if any(arc.use == "prohibited" for arc in tier):
            continue
        optional = [arc for arc in tier if arc.use != "prohibited"]
        if optional:
            effective.append(optional[0])
    return effective


def _collect_arc_override_findings(all_arcs: list[_ArcUse]) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    prohibited_by_equiv: dict[tuple[str, str, str, str, str, str], int] = {}

    for arc in all_arcs:
        if arc.use == "prohibited":
            key = _arc_equivalence_key(arc)
            prohibited_by_equiv[key] = max(prohibited_by_equiv.get(key, 0), arc.priority)

    for arc in all_arcs:
        equiv_key = _arc_equivalence_key(arc)
        if (
            arc.arc_tag in {"labelArc", "referenceArc"}
            and arc.use != "prohibited"
            and equiv_key in prohibited_by_equiv
        ):
            findings.append(
                _finding(
                    "xbrl:arc-override-reinstated",
                    "A prohibited relationship was reinstated by a non-prohibited arc.",
                )
            )
            continue

        if arc.arc_tag not in {"labelArc", "referenceArc"}:
            continue

        if (
            arc.source_from_loc
            and arc.target_from_loc
            and not arc.target_from_resource
            and _is_schema_concept_href(arc.source)
            and _is_schema_concept_href(arc.target)
        ):
            findings.append(
                _finding(
                    "xbrl:arc-override-concept-to-concept",
                    f"{arc.arc_tag} must not relate one schema concept directly to another.",
                )
            )
            continue

        if (
            arc.use != "prohibited"
            and arc.source_from_loc
            and arc.target_from_loc
            and not arc.target_from_resource
            and _is_schema_concept_href(arc.source)
            and not _is_schema_concept_href(arc.target)
        ):
            findings.append(
                _finding(
                    "xbrl:arc-override-missing-prohibited",
                    f"Overriding {arc.arc_tag} must use use=\"prohibited\".",
                )
            )
    return findings


def _collect_arcs(
    roots: list[tuple[Path, etree._Element]],
    declarations: dict[str, list[_ArcroleDeclaration]],
    href_resolver: _HrefResolver,
) -> tuple[list[_ArcUse], set[str], list[ValidationFinding]]:
    all_arcs: list[_ArcUse] = []
    referenced_arcroles: set[str] = set()
    findings: list[ValidationFinding] = []

    for path, root in roots:
        arcrole_refs_by_parent: dict[int, set[str]] = defaultdict(set)
        for ref in root.iter(_ARCROLE_REF):
            arcrole_uri = (ref.get("arcroleURI") or "").strip()
            parent = ref.getparent()
            parent_id = id(parent) if parent is not None else id(root)
            if arcrole_uri in arcrole_refs_by_parent[parent_id]:
                findings.append(
                    _finding("xbrl:duplicate-arcrole-ref", f"Duplicate arcroleRef '{arcrole_uri}'")
                )
                continue
            arcrole_refs_by_parent[parent_id].add(arcrole_uri)
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
                    locs.get(frm) or resources.get(frm) or _link_local_node_id(path, link_el, frm)
                )
                target = locs.get(to) or resources.get(to) or _link_local_node_id(path, link_el, to)
                try:
                    priority = int(arc_el.get("priority", "0"))
                except ValueError:
                    priority = 0
                use = (arc_el.get("use") or "optional").strip() or "optional"
                arc_use = _ArcUse(
                    arcrole=arcrole,
                    link_tag=link_tag,
                    arc_tag=_local_name(arc_el.tag),
                    extended_link_role=elr,
                    source=source,
                    target=target,
                    source_path=path,
                    priority=priority,
                    use=use,
                    source_from_loc=frm in locs,
                    target_from_loc=to in locs,
                    target_from_resource=to in resources,
                )
                equiv_key = (
                    arcrole,
                    link_tag,
                    arc_use.arc_tag,
                    elr,
                    source,
                    target,
                )
                all_arcs.append(arc_use)
    arcs = _effective_relationship_arcs(all_arcs)
    findings.extend(_collect_arc_override_findings(all_arcs))
    return arcs, referenced_arcroles, findings


def _collect_preferred_label_findings(
    roots: list[tuple[Path, etree._Element]],
    href_resolver: _HrefResolver,
) -> list[ValidationFinding]:
    label_roles_by_concept: dict[str, set[str]] = defaultdict(set)
    presentation_arcs: list[tuple[str, str]] = []

    for path, root in roots:
        for link_el in root.iter():
            if not isinstance(link_el.tag, str) or link_el.get(_XLINK_TYPE) != "extended":
                continue
            link_tag = _local_name(link_el.tag)
            locs = {
                loc.get(_XLINK_LABEL, ""): href_resolver.canonicalize(
                    loc.get(_XLINK_HREF, ""),
                    path,
                )
                for loc in link_el.iterchildren(_LOC)
            }
            if link_tag == "labelLink":
                resource_roles = {
                    child.get(_XLINK_LABEL, ""): child.get(_XLINK_ROLE, "")
                    for child in link_el.iterchildren()
                    if isinstance(child.tag, str)
                    and child.get(_XLINK_TYPE) == "resource"
                    and _local_name(child.tag) == "label"
                    and child.get(_XLINK_LABEL)
                }
                for arc_el in link_el.iterchildren():
                    if (
                        not isinstance(arc_el.tag, str)
                        or arc_el.get(_XLINK_TYPE) != "arc"
                        or arc_el.get(_XLINK_ARCROLE)
                        != "http://www.xbrl.org/2003/arcrole/concept-label"
                    ):
                        continue
                    concept = locs.get(arc_el.get(_XLINK_FROM, ""))
                    role = resource_roles.get(arc_el.get(_XLINK_TO, ""))
                    if concept and role:
                        label_roles_by_concept[concept].add(role)
            elif link_tag == "presentationLink":
                for arc_el in link_el.iterchildren():
                    if not isinstance(arc_el.tag, str) or arc_el.get(_XLINK_TYPE) != "arc":
                        continue
                    preferred = (arc_el.get("preferredLabel") or "").strip()
                    if not preferred:
                        continue
                    target = locs.get(arc_el.get(_XLINK_TO, ""))
                    if target:
                        presentation_arcs.append((target, preferred))

    findings: list[ValidationFinding] = []
    for target, preferred in presentation_arcs:
        if preferred not in label_roles_by_concept.get(target, set()):
            findings.append(
                _finding(
                    "xbrl:preferred-label-missing",
                    f"Presentation arc target '{target}' has no label role '{preferred}'",
                )
            )
    return findings


def _collect_label_resource_findings(
    roots: list[tuple[Path, etree._Element]],
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for _path, root in roots:
        for label in root.iter(_LABEL):
            if label.get(_XLINK_TYPE) == "resource" and not _has_inherited_xml_lang(label):
                findings.append(
                    _finding("xbrl:label-language", "link:label resource is missing xml:lang")
                )
    return findings


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
        findings: list[ValidationFinding] = []
        findings.extend(_collect_declaration_findings(roots))
        findings.extend(_collect_label_resource_findings(roots))
        arcs, referenced_arcroles, arc_findings = _collect_arcs(
            roots,
            declarations,
            href_resolver,
        )
        findings.extend(arc_findings)
        findings.extend(_collect_role_ref_findings(roots, role_declarations))
        findings.extend(_collect_preferred_label_findings(roots, href_resolver))

        for uri, decls in role_declarations.items():
            signatures = {decl.signature for decl in decls}
            source_paths = [decl.source_path.resolve() for decl in decls]
            if len(signatures) > 1 or len(source_paths) != len(set(source_paths)):
                findings.append(
                    _finding(
                        "xbrl:role-declaration-duplicate",
                        f"Role '{uri}' is declared with non-equivalent definitions",
                    )
                )

        for _path, root in roots:
            for el in root.iter():
                if not isinstance(el.tag, str):
                    continue
                role_uri = (el.get(_XLINK_ROLE) or "").strip()
                tag = _local_name(el.tag)
                standard_allowed = _STANDARD_ROLE_ALLOWED_ON.get(role_uri)
                if standard_allowed is not None and tag in _STANDARD_ROLE_ELEMENTS:
                    if tag not in standard_allowed:
                        findings.append(
                            _finding(
                                "xbrl:standard-role-used-on",
                                f"Standard role '{role_uri}' is not defined for {tag}",
                            )
                        )
                    continue
                if not role_uri or role_uri not in role_declarations:
                    continue
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
            standard_arc_allowed = _STANDARD_ARCROLE_ALLOWED_ON.get(arc.arcrole)
            if (
                standard_arc_allowed is not None
                and arc.arc_tag in _STANDARD_ARC_ELEMENTS
                and arc.arc_tag not in standard_arc_allowed
            ):
                findings.append(
                    _finding(
                        "xbrl:standard-arcrole-used-on",
                        f"Standard arcrole '{arc.arcrole}' is not defined for {arc.arc_tag}",
                    )
                )
                continue
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
            elif (
                arc.arcrole not in _STANDARD_ARCROLE_CYCLES
                and arc.arc_tag in _STANDARD_ARC_ELEMENTS
            ):
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
            if (
                arc.link_tag not in _STANDARD_LINK_ELEMENTS
                or arc.arc_tag not in _STANDARD_ARC_ELEMENTS
            ):
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

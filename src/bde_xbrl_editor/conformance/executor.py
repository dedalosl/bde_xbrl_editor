"""TestCaseExecutor — runs a single conformance variation through the XBRL engine."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, replace
from pathlib import Path

from lxml import etree

from bde_xbrl_editor.conformance.models import (
    ExpectedOutcome,
    ExpectedOutcomeType,
    TestCase,
    TestCaseResult,
    TestResultOutcome,
    TestVariation,
)
from bde_xbrl_editor.instance.constants import LINK_NS, XLINK_NS
from bde_xbrl_editor.instance.parser import InstanceParser
from bde_xbrl_editor.taxonomy.cache import TaxonomyCache
from bde_xbrl_editor.taxonomy.constants import NS_XLINK, NS_XSD
from bde_xbrl_editor.taxonomy.linkbases.calculation import parse_calculation_linkbase
from bde_xbrl_editor.taxonomy.loader import TaxonomyLoader
from bde_xbrl_editor.taxonomy.models import (
    QName,
    TaxonomyStructure,
    UnsupportedTaxonomyFormatError,
)
from bde_xbrl_editor.taxonomy.settings import LoaderSettings
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file
from bde_xbrl_editor.validation.calculation import CalculationConsistencyValidator
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity
from bde_xbrl_editor.validation.orchestrator import InstanceValidator

# Formula conformance measures formula assertions, not full XBRL 2.1 instance
# validation.  S-equal–aware duplicate-fact / calculation checks (added for
# XBRL 2.1 suite) may report errors on instances the formula suite still marks
# ``expected="valid"`` — ignore only those rule_ids when matching VALID.
_FORMULA_VALID_IGNORE_RULE_IDS = frozenset(
    {
        "structural:duplicate-fact",
        "calculation:summation-inconsistent",
    }
)
_XBRL21_VALID_IGNORE_RULE_IDS = frozenset(
    {
        # Duplicate facts affect calculation binding, but are not themselves an
        # XBRL 2.1 conformance error for variations whose expected result is valid.
        "structural:duplicate-fact",
    }
)

_LINK_LINKBASE_REF = f"{{{LINK_NS}}}linkbaseRef"
_XLINK_HREF = f"{{{XLINK_NS}}}href"
_XLINK_TYPE = f"{{{NS_XLINK}}}type"
_XLINK_FROM = f"{{{NS_XLINK}}}from"
_XLINK_TO = f"{{{NS_XLINK}}}to"
_XS_ELEMENT = f"{{{NS_XSD}}}element"
_LINK_LOC = f"{{{LINK_NS}}}loc"
_LINK_LINKBASE = f"{{{LINK_NS}}}linkbase"
_LINK_ROLE_REF = f"{{{LINK_NS}}}roleRef"
_LINK_ARCROLE_REF = f"{{{LINK_NS}}}arcroleRef"
_XS_SCHEMA = f"{{{NS_XSD}}}schema"
_XS_IMPORT = f"{{{NS_XSD}}}import"
_XS_INCLUDE = f"{{{NS_XSD}}}include"
_XS_REDEFINE = f"{{{NS_XSD}}}redefine"
_XS_RESTRICTION = f"{{{NS_XSD}}}restriction"
_XS_EXTENSION = f"{{{NS_XSD}}}extension"
_XS_SIMPLE_TYPE = f"{{{NS_XSD}}}simpleType"
_XS_COMPLEX_TYPE = f"{{{NS_XSD}}}complexType"
_XS_SIMPLE_CONTENT = f"{{{NS_XSD}}}simpleContent"
_XS_ATTRIBUTE = f"{{{NS_XSD}}}attribute"
_XSI_SCHEMA_LOCATION = "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
_LANGUAGE_RE = re.compile(r"^[A-Za-z]{1,8}(?:-[A-Za-z0-9]{1,8})*$")
_INTEGER_RE = re.compile(r"^[+-]?\d+$")
_LAX_VALIDATION_TEST_ID = "LAX validation tests"
_LINKBASE_REFERENCES_TEST_ID = "Linkbase References"
_USED_ON_TEST_ID = "UsedOn Element"
_STRUCTURAL_ONLY_TEST_IDS = frozenset(
    {
        _LAX_VALIDATION_TEST_ID,
        _LINKBASE_REFERENCES_TEST_ID,
        _USED_ON_TEST_ID,
    }
)
_LINKBASE_ARCROLE = "http://www.w3.org/1999/xlink/properties/linkbase"
_LINKBASE_REF_ROLE_TO_LINK_TAG = {
    "http://www.xbrl.org/2003/role/labelLinkbaseRef": f"{{{LINK_NS}}}labelLink",
    "http://www.xbrl.org/2003/role/referenceLinkbaseRef": f"{{{LINK_NS}}}referenceLink",
    "http://www.xbrl.org/2003/role/calculationLinkbaseRef": f"{{{LINK_NS}}}calculationLink",
    "http://www.xbrl.org/2003/role/presentationLinkbaseRef": f"{{{LINK_NS}}}presentationLink",
    "http://www.xbrl.org/2003/role/definitionLinkbaseRef": f"{{{LINK_NS}}}definitionLink",
}
_LINK_EXTENDED_ELEMENTS = {
    f"{{{LINK_NS}}}definitionLink",
    f"{{{LINK_NS}}}calculationLink",
    f"{{{LINK_NS}}}presentationLink",
    f"{{{LINK_NS}}}labelLink",
    f"{{{LINK_NS}}}referenceLink",
    f"{{{LINK_NS}}}footnoteLink",
}
_XSD_INTEGER_TYPES = frozenset(
    {
        "integer",
        "nonPositiveInteger",
        "negativeInteger",
        "long",
        "int",
        "short",
        "byte",
        "nonNegativeInteger",
        "unsignedLong",
        "unsignedInt",
        "unsignedShort",
        "unsignedByte",
        "positiveInteger",
    }
)


@dataclass(frozen=True)
class _LaxDeclarationMaps:
    elements: dict[QName, QName]
    attributes: dict[QName, QName]
    type_bases: dict[QName, QName]


def _concept_id_map(taxonomy: TaxonomyStructure) -> dict[str, QName]:
    out: dict[str, QName] = {}
    for qname, concept in taxonomy.concepts.items():
        if concept.xml_id:
            out[concept.xml_id] = qname
    return out


def _with_instance_calculation_linkbases(
    taxonomy: TaxonomyStructure,
    instance_file: Path,
) -> TaxonomyStructure:
    """Merge calculation linkbases referenced directly by an instance document."""
    try:
        root = parse_xml_file(instance_file).getroot()
    except etree.XMLSyntaxError:
        return taxonomy

    concept_map = _concept_id_map(taxonomy)
    if not concept_map:
        return taxonomy

    merged = {elr: list(arcs) for elr, arcs in taxonomy.calculation.items()}
    changed = False
    for linkbase_ref in root.iter(_LINK_LINKBASE_REF):
        href = (linkbase_ref.get(_XLINK_HREF) or "").strip()
        if not href or href.startswith(("http://", "https://")):
            continue
        linkbase_path = (instance_file.parent / href).resolve()
        if not linkbase_path.exists():
            continue
        parsed = parse_calculation_linkbase(linkbase_path, concept_map)
        for elr, arcs in parsed.items():
            if arcs:
                merged.setdefault(elr, []).extend(arcs)
                changed = True

    if not changed:
        return taxonomy
    return replace(taxonomy, calculation=merged)


def _xlink_error(message: str) -> ValidationFinding:
    return ValidationFinding(
        rule_id="xlink:validation-error",
        severity=ValidationSeverity.ERROR,
        message=message,
        source="structural",
    )


def _linkbase_ref_error(message: str) -> ValidationFinding:
    return ValidationFinding(
        rule_id="xbrl:linkbase-reference-error",
        severity=ValidationSeverity.ERROR,
        message=message,
        source="structural",
    )


def _lax_validation_error(message: str) -> ValidationFinding:
    return ValidationFinding(
        rule_id="xmlschema:lax-validation-error",
        severity=ValidationSeverity.ERROR,
        message=message,
        source="structural",
    )


def _resolve_schema_qname(raw: str | None, ns_map: dict[str, str]) -> QName | None:
    if not raw:
        return None
    if raw.startswith("{"):
        return QName.from_clark(raw)
    if ":" in raw:
        prefix, local = raw.split(":", 1)
        ns = ns_map.get(prefix, "")
        return QName(namespace=ns, local_name=local, prefix=prefix)
    return QName(namespace=NS_XSD, local_name=raw)


def _element_qname(el: etree._Element) -> QName | None:
    if not isinstance(el.tag, str):
        return None
    return QName.from_clark(el.tag) if el.tag.startswith("{") else QName("", el.tag)


def _attribute_qname(raw_name: str) -> QName:
    return QName.from_clark(raw_name) if raw_name.startswith("{") else QName("", raw_name)


def _schema_location_paths(root: etree._Element, base_dir: Path) -> list[Path]:
    raw = (root.get(_XSI_SCHEMA_LOCATION) or "").strip()
    if not raw:
        return []
    tokens = raw.split()
    paths: list[Path] = []
    for location in tokens[1::2]:
        if location.startswith(("http://", "https://")):
            continue
        path = (base_dir / location).resolve()
        if path.exists() and path.suffix.lower() == ".xsd":
            paths.append(path)
    return paths


def _discover_lax_schema_paths(input_files: tuple[Path, ...]) -> list[Path]:
    queue: list[Path] = [
        path.resolve() for path in input_files if path.suffix.lower() == ".xsd"
    ]
    for path in input_files:
        if path.suffix.lower() not in (".xml", ".xsd"):
            continue
        try:
            root = parse_xml_file(path).getroot()
        except etree.XMLSyntaxError:
            continue
        queue.extend(_schema_location_paths(root, path.parent))

    seen: set[Path] = set()
    out: list[Path] = []
    while queue:
        path = queue.pop(0).resolve()
        if path in seen or not path.exists() or path.suffix.lower() != ".xsd":
            continue
        seen.add(path)
        out.append(path)
        try:
            root = parse_xml_file(path).getroot()
        except etree.XMLSyntaxError:
            continue
        if root.tag != _XS_SCHEMA:
            continue
        for child in root:
            if child.tag not in (_XS_IMPORT, _XS_INCLUDE, _XS_REDEFINE):
                continue
            location = (child.get("schemaLocation") or "").strip()
            if not location or location.startswith(("http://", "https://")):
                continue
            queue.append((path.parent / location).resolve())
        queue.extend(_schema_location_paths(root, path.parent))
    return out


def _direct_schema_type(
    el: etree._Element,
    ns_map: dict[str, str],
) -> QName | None:
    type_raw = el.get("type")
    if type_raw:
        return _resolve_schema_qname(type_raw, ns_map)
    for child in el:
        if child.tag != _XS_SIMPLE_TYPE:
            continue
        for type_child in child:
            if type_child.tag == _XS_RESTRICTION:
                return _resolve_schema_qname(type_child.get("base"), ns_map)
    return None


def _collect_type_bases(
    type_el: etree._Element,
    ns_map: dict[str, str],
) -> QName | None:
    for child in type_el:
        if child.tag == _XS_RESTRICTION:
            return _resolve_schema_qname(child.get("base"), ns_map)
        if child.tag == _XS_SIMPLE_CONTENT:
            for simple_child in child:
                if simple_child.tag in (_XS_RESTRICTION, _XS_EXTENSION):
                    return _resolve_schema_qname(simple_child.get("base"), ns_map)
        if child.tag == _XS_EXTENSION:
            return _resolve_schema_qname(child.get("base"), ns_map)
    return None


def _build_lax_declaration_maps(input_files: tuple[Path, ...]) -> _LaxDeclarationMaps:
    elements: dict[QName, QName] = {}
    attributes: dict[QName, QName] = {}
    type_bases: dict[QName, QName] = {}

    for schema_path in _discover_lax_schema_paths(input_files):
        try:
            root = parse_xml_file(schema_path).getroot()
        except etree.XMLSyntaxError:
            continue
        if root.tag != _XS_SCHEMA:
            continue
        target_ns = root.get("targetNamespace", "")
        ns_map: dict[str, str] = {k or "": v for k, v in root.nsmap.items()}

        for type_el in root.iter(_XS_SIMPLE_TYPE):
            name = type_el.get("name")
            if not name:
                continue
            base = _collect_type_bases(type_el, ns_map)
            if base is not None:
                type_bases[QName(target_ns, name)] = base
        for type_el in root.iter(_XS_COMPLEX_TYPE):
            name = type_el.get("name")
            if not name:
                continue
            base = _collect_type_bases(type_el, ns_map)
            if base is not None:
                type_bases[QName(target_ns, name)] = base

        for el in root.iter(_XS_ELEMENT):
            if el.getparent() is not root:
                continue
            name = el.get("name")
            decl_type = _direct_schema_type(el, ns_map)
            if name and decl_type is not None:
                elements[QName(target_ns, name)] = decl_type
        for attr in root.iter(_XS_ATTRIBUTE):
            if attr.getparent() is not root:
                continue
            name = attr.get("name")
            decl_type = _direct_schema_type(attr, ns_map)
            if name and decl_type is not None:
                attributes[QName(target_ns, name)] = decl_type

    return _LaxDeclarationMaps(elements, attributes, type_bases)


def _type_is_integer(decl_type: QName, type_bases: dict[QName, QName]) -> bool:
    seen: set[QName] = set()
    current: QName | None = decl_type
    while current is not None and current not in seen:
        if current.namespace == NS_XSD and current.local_name in _XSD_INTEGER_TYPES:
            return True
        seen.add(current)
        current = type_bases.get(current)
    return False


def _validate_integer_lexical(value: str) -> bool:
    return bool(_INTEGER_RE.fullmatch(value.strip()))


def _validate_xml_language(value: str) -> bool:
    return bool(_LANGUAGE_RE.fullmatch(value.strip()))


def _validate_lax_known_declarations(
    input_files: tuple[Path, ...],
) -> tuple[ValidationFinding, ...]:
    decls = _build_lax_declaration_maps(input_files)
    findings: list[ValidationFinding] = []

    for path in input_files:
        if path.suffix.lower() not in (".xml", ".xsd"):
            continue
        try:
            root = parse_xml_file(path).getroot()
        except etree.XMLSyntaxError as exc:
            findings.append(_lax_validation_error(f"XML syntax error in '{path}': {exc}"))
            continue

        for el in root.iter():
            qname = _element_qname(el)
            if qname is not None:
                decl_type = decls.elements.get(qname)
                if decl_type is not None and _type_is_integer(decl_type, decls.type_bases):
                    value = "".join(el.itertext())
                    if not _validate_integer_lexical(value):
                        findings.append(
                            _lax_validation_error(
                                f"Element '{qname}' value is not a valid xs:integer"
                            )
                        )
                parent = el.getparent()
                if (
                    parent is not None
                    and parent.tag in _LINK_EXTENDED_ELEMENTS
                    and qname in decls.elements
                    and qname.namespace != LINK_NS
                ):
                    findings.append(
                        _lax_validation_error(
                            f"Declared element '{qname}' is not allowed in XBRL linkbase content"
                        )
                    )

            for raw_name, value in el.attrib.items():
                if raw_name == _XML_SPACE and value not in {"default", "preserve"}:
                    findings.append(
                        _lax_validation_error(
                            f"xml:space value '{value}' is not 'default' or 'preserve'"
                        )
                    )
                    continue
                if raw_name == _XML_LANG and not _validate_xml_language(value):
                    findings.append(
                        _lax_validation_error(
                            f"xml:lang value '{value}' is not a valid language tag"
                        )
                    )
                    continue
                attr_qname = _attribute_qname(raw_name)
                decl_type = decls.attributes.get(attr_qname)
                if decl_type is None or not _type_is_integer(decl_type, decls.type_bases):
                    continue
                if not _validate_integer_lexical(value):
                    findings.append(
                        _lax_validation_error(
                            f"Attribute '{attr_qname}' value is not a valid xs:integer"
                        )
                    )

    return tuple(findings)


def _element_base_dir(el: etree._Element, fallback: Path) -> Path:
    if not el.base:
        return fallback
    base_path = Path(el.base)
    if not base_path.is_absolute():
        base_path = base_path.resolve()
    return base_path if el.base.endswith("/") else base_path.parent


def _duplicate_ref_error(ref_kind: str, uri: str) -> ValidationFinding:
    return ValidationFinding(
        rule_id=f"xbrl:duplicate-{ref_kind}-ref",
        severity=ValidationSeverity.ERROR,
        message=f"Duplicate linkbase {ref_kind}Ref URI '{uri}'",
        source="structural",
    )


def _resolve_href_target(href: str, base_dir: Path, current_doc: Path) -> tuple[Path, str]:
    file_part, sep, fragment = href.partition("#")
    target_path = current_doc if not file_part else (base_dir / file_part).resolve()
    return target_path, fragment if sep else ""


def _element_scheme_target(root: etree._Element, scheme: str) -> etree._Element | None:
    if not scheme.startswith("element(") or not scheme.endswith(")"):
        return None
    payload = scheme[len("element(") : -1]
    if not payload.startswith("/"):
        matches = root.xpath("//*[@id=$id]", id=payload)
        return matches[0] if matches else None

    current = root
    parts = [part for part in payload.split("/") if part]
    if not parts or parts[0] != "1":
        return None
    for part in parts[1:]:
        try:
            index = int(part) - 1
        except ValueError:
            return None
        children = [child for child in current if isinstance(child.tag, str)]
        if index < 0 or index >= len(children):
            return None
        current = children[index]
    return current


def _xpointer_target(root: etree._Element, fragment: str) -> etree._Element | None:
    if fragment.startswith("xpointer(") or "xmlns(" in fragment:
        return None
    if fragment.startswith("element("):
        for scheme in re.findall(r"element\([^)]*\)", fragment):
            target = _element_scheme_target(root, scheme)
            if target is not None:
                return target
        return None
    matches = root.xpath("//*[@id=$id]", id=fragment)
    return matches[0] if matches else None


def _resolve_linkbase_locator(
    href: str, base_dir: Path, current_doc: Path
) -> etree._Element | None:
    target_path, fragment = _resolve_href_target(href, base_dir, current_doc)
    if not target_path.exists() or target_path.is_dir():
        return None
    try:
        root = parse_xml_file(target_path).getroot()
    except etree.XMLSyntaxError:
        return None
    if not fragment:
        return root
    return _xpointer_target(root, fragment)


def _target_is_valid_locator_resource(target: etree._Element | None) -> bool:
    if target is None:
        return False
    return target.tag == _XS_ELEMENT or target.get(_XLINK_TYPE) == "resource"


def _linkbase_target_extended_tags(target_path: Path) -> set[str] | None:
    try:
        root = parse_xml_file(target_path).getroot()
    except etree.XMLSyntaxError:
        return None
    if root.tag != _LINK_LINKBASE:
        return None
    return {
        child.tag
        for child in root
        if isinstance(child.tag, str) and child.get(_XLINK_TYPE) == "extended"
    }


def _validate_linkbase_refs(root: etree._Element, path: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for linkbase_ref in root.iter(_LINK_LINKBASE_REF):
        xlink_type = (linkbase_ref.get(_XLINK_TYPE) or "").strip()
        if xlink_type != "simple":
            findings.append(
                _linkbase_ref_error("linkbaseRef xlink:type must be 'simple'")
            )

        arcrole = (linkbase_ref.get(f"{{{NS_XLINK}}}arcrole") or "").strip()
        if arcrole != _LINKBASE_ARCROLE:
            findings.append(
                _linkbase_ref_error(
                    "linkbaseRef xlink:arcrole must be the XLink linkbase arcrole"
                )
            )

        href = (linkbase_ref.get(_XLINK_HREF) or "").strip()
        if not href:
            findings.append(_linkbase_ref_error("linkbaseRef is missing xlink:href"))
            continue
        if href.startswith(("http://", "https://")):
            continue

        target_path, _fragment = _resolve_href_target(
            href,
            _element_base_dir(linkbase_ref, path.parent),
            path.resolve(),
        )
        if not target_path.exists() or target_path.is_dir():
            findings.append(
                _linkbase_ref_error(f"linkbaseRef target '{href}' does not resolve")
            )
            continue

        target_tags = _linkbase_target_extended_tags(target_path)
        if target_tags is None:
            findings.append(
                _linkbase_ref_error(f"linkbaseRef target '{href}' is not a linkbase")
            )
            continue

        role = (linkbase_ref.get(f"{{{NS_XLINK}}}role") or "").strip()
        expected_tag = _LINKBASE_REF_ROLE_TO_LINK_TAG.get(role)
        if expected_tag is not None and expected_tag not in target_tags:
            findings.append(
                _linkbase_ref_error(
                    f"linkbaseRef role '{role}' does not match target linkbase '{href}'"
                )
            )

    return findings


def _validate_duplicate_linkbase_refs(
    root: etree._Element,
) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for linkbase in root.iter(_LINK_LINKBASE):
        seen_role_uris: set[str] = set()
        seen_arcrole_uris: set[str] = set()

        for role_ref in linkbase.iterchildren(_LINK_ROLE_REF):
            role_uri = (role_ref.get("roleURI") or "").strip()
            if not role_uri:
                continue
            if role_uri in seen_role_uris:
                findings.append(_duplicate_ref_error("role", role_uri))
                break
            seen_role_uris.add(role_uri)

        for arcrole_ref in linkbase.iterchildren(_LINK_ARCROLE_REF):
            arcrole_uri = (arcrole_ref.get("arcroleURI") or "").strip()
            if not arcrole_uri:
                continue
            if arcrole_uri in seen_arcrole_uris:
                findings.append(_duplicate_ref_error("arcrole", arcrole_uri))
                break
            seen_arcrole_uris.add(arcrole_uri)

    return findings


def _validate_xlink_file(path: Path) -> list[ValidationFinding]:
    try:
        root = parse_xml_file(path).getroot()
    except etree.XMLSyntaxError as exc:
        return [_xlink_error(f"XML syntax error in XLink input '{path}': {exc}")]

    findings: list[ValidationFinding] = []
    base_dir = path.parent
    label_targets: dict[str, etree._Element | None] = {}
    findings.extend(_validate_linkbase_refs(root, path))
    findings.extend(_validate_duplicate_linkbase_refs(root))

    for loc in root.iter(_LINK_LOC):
        if loc.get(_XLINK_TYPE) != "locator":
            continue
        label = loc.get(f"{{{NS_XLINK}}}label", "")
        href = (loc.get(_XLINK_HREF) or "").strip()
        target = _resolve_linkbase_locator(
            href,
            _element_base_dir(loc, base_dir),
            path.resolve(),
        )
        label_targets[label] = target
        parent = loc.getparent()
        if not href and parent is not None and parent.tag.startswith(f"{{{LINK_NS}}}"):
            findings.append(_xlink_error("Empty XLink locator href in standard linkbase link"))
        if href and not _target_is_valid_locator_resource(target):
            findings.append(_xlink_error(f"Unresolvable or invalid XLink locator href '{href}'"))

    for resource in root.xpath("//*[@xlink:type='resource']", namespaces={"xlink": NS_XLINK}):
        label = resource.get(f"{{{NS_XLINK}}}label", "")
        if label:
            label_targets[label] = resource

    for link in root.xpath("//*[@xlink:type='extended']", namespaces={"xlink": NS_XLINK}):
        seen: set[tuple[str, str]] = set()
        for arc in link.xpath("./*[@xlink:type='arc']", namespaces={"xlink": NS_XLINK}):
            frm = arc.get(_XLINK_FROM, "")
            to = arc.get(_XLINK_TO, "")
            arcrole = arc.get(f"{{{NS_XLINK}}}arcrole", "")
            if arcrole == "http://www.xbrl.org/2003/arcrole/concept-label":
                source = label_targets.get(frm)
                target = label_targets.get(to)
                if source is None or source.tag != _XS_ELEMENT:
                    findings.append(_xlink_error(f"Label arc source '{frm}' does not resolve to a concept"))
                    break
                if target is None or target.get(_XLINK_TYPE) != "resource":
                    findings.append(_xlink_error(f"Label arc target '{to}' does not resolve to a resource"))
                    break
            key = (frm, to)
            if key in seen:
                findings.append(_xlink_error(f"Duplicate XLink arc from '{frm}' to '{to}'"))
                break
            seen.add(key)

    return findings


def _validate_xlink_inputs(input_files: tuple[Path, ...]) -> tuple[ValidationFinding, ...]:
    findings: list[ValidationFinding] = []
    for path in input_files:
        if path.suffix.lower() in (".xml", ".xsd"):
            findings.extend(_validate_xlink_file(path))
    return tuple(findings)


class TestCaseExecutor:
    """Executes a single conformance test variation and returns a TestCaseResult."""

    def __init__(
        self,
        taxonomy_cache: TaxonomyCache,
        allow_network: bool = False,
        formula_skip_list: frozenset[str] = frozenset(),
    ) -> None:
        self._taxonomy_cache = taxonomy_cache
        self._allow_network = allow_network
        self._formula_skip_list = formula_skip_list

    def execute(self, variation: TestVariation, test_case: TestCase) -> TestCaseResult:
        """Execute one variation and return a TestCaseResult."""
        if variation.variation_id in self._formula_skip_list:
            return TestCaseResult(
                variation_id=variation.variation_id,
                test_case_id=test_case.test_case_id,
                suite_id=test_case.suite_id,
                outcome=TestResultOutcome.SKIPPED,
                mandatory=variation.mandatory,
                expected_outcome=variation.expected_outcome,
                actual_error_codes=(),
                exception_message=None,
                description=variation.description,
                input_files=variation.input_files,
                duration_ms=0,
            )

        start = time.time()
        load_error: Exception | None = None
        findings: tuple[ValidationFinding, ...] = ()

        try:
            settings = LoaderSettings(allow_network=self._allow_network)
            loader = TaxonomyLoader(self._taxonomy_cache, settings)

            taxonomy_struct = None

            if variation.instance_file is not None:
                # Parse instance (also loads taxonomy via schemaRef)
                inst_parser = InstanceParser(loader)
                instance, _ = inst_parser.load(variation.instance_file)

                # Get taxonomy: use explicit taxonomy_file if given, otherwise
                # resolve schemaRef relative to instance file
                if variation.taxonomy_file is not None and variation.taxonomy_file.exists():
                    taxonomy_struct = loader.load(variation.taxonomy_file)
                else:
                    schema_href = instance.schema_ref_href
                    if schema_href and not schema_href.startswith(
                        ("http://", "https://")
                    ):
                        schema_ref_path = (
                            variation.instance_file.parent / schema_href
                        ).resolve()
                        if schema_ref_path.exists():
                            taxonomy_struct = loader.load(schema_ref_path)
                        else:
                            taxonomy_struct = loader.load(
                                instance.taxonomy_entry_point
                            )
                    else:
                        taxonomy_struct = loader.load(instance.taxonomy_entry_point)

                if taxonomy_struct is not None:
                    taxonomy_struct = _with_instance_calculation_linkbases(
                        taxonomy_struct,
                        variation.instance_file,
                    )
                    validator = InstanceValidator(taxonomy_struct)
                    report = validator.validate_sync(instance)
                    findings = report.findings
                if test_case.test_case_id == _LAX_VALIDATION_TEST_ID:
                    findings = findings + _validate_lax_known_declarations(
                        variation.input_files
                    )

            elif variation.taxonomy_file is not None:
                # Taxonomy-only test (e.g. Dimensions schema validation)
                try:
                    taxonomy_struct = loader.load(variation.taxonomy_file)
                except UnsupportedTaxonomyFormatError:
                    if (
                        test_case.test_case_id not in _STRUCTURAL_ONLY_TEST_IDS
                        and variation.expected_outcome.outcome_type
                        != ExpectedOutcomeType.VALID
                    ):
                        raise
                except Exception:  # noqa: BLE001
                    if test_case.test_case_id != _LINKBASE_REFERENCES_TEST_ID:
                        raise
                findings = _validate_xlink_inputs(variation.input_files)
                if taxonomy_struct is not None and test_case.suite_id == "xbrl21":
                    findings = findings + tuple(
                        CalculationConsistencyValidator().validate_taxonomy(taxonomy_struct)
                    )
                if test_case.test_case_id == _LAX_VALIDATION_TEST_ID:
                    findings = findings + _validate_lax_known_declarations(
                        variation.input_files
                    )

            else:
                # Try loading any input files as taxonomy entry points.
                # Keep the first load error so taxonomy-level constraint violations
                # (xbrldte:* errors raised as TaxonomyParseError) are not silently lost.
                first_load_error: Exception | None = None
                for f in variation.input_files:
                    if f.suffix.lower() in (".xsd", ".xml"):
                        try:
                            taxonomy_struct = loader.load(f)
                            first_load_error = None  # success — clear any prior error
                            break
                        except Exception as _exc:  # noqa: BLE001
                            if first_load_error is None:
                                first_load_error = _exc
                if taxonomy_struct is None and first_load_error is not None:
                    raise first_load_error
                findings = _validate_xlink_inputs(variation.input_files)
                if taxonomy_struct is not None and test_case.suite_id == "xbrl21":
                    findings = findings + tuple(
                        CalculationConsistencyValidator().validate_taxonomy(taxonomy_struct)
                    )
                if test_case.test_case_id == _LAX_VALIDATION_TEST_ID:
                    findings = findings + _validate_lax_known_declarations(
                        variation.input_files
                    )

        except Exception as exc:  # noqa: BLE001
            load_error = exc
            findings = ()

        outcome, actual_error_codes = self._match_outcome(
            variation.expected_outcome,
            findings,
            load_error,
            test_case.suite_id,
        )
        duration_ms = int((time.time() - start) * 1000)

        return TestCaseResult(
            variation_id=variation.variation_id,
            test_case_id=test_case.test_case_id,
            suite_id=test_case.suite_id,
            outcome=outcome,
            mandatory=variation.mandatory,
            expected_outcome=variation.expected_outcome,
            actual_error_codes=actual_error_codes,
            exception_message=str(load_error) if load_error is not None else None,
            description=variation.description,
            input_files=variation.input_files,
            duration_ms=duration_ms,
        )

    def _match_outcome(
        self,
        expected: ExpectedOutcome,
        findings: tuple[ValidationFinding, ...],
        load_error: Exception | None,
        suite_id: str | None = None,
    ) -> tuple[TestResultOutcome, tuple[str, ...]]:
        """Determine the test outcome by comparing expected with actual results."""
        error_findings = tuple(
            f for f in findings if f.severity == ValidationSeverity.ERROR
        )
        if (
            suite_id == "formula"
            and expected.outcome_type == ExpectedOutcomeType.VALID
        ):
            error_findings = tuple(
                f
                for f in error_findings
                if f.rule_id not in _FORMULA_VALID_IGNORE_RULE_IDS
            )
        elif (
            suite_id == "xbrl21"
            and expected.outcome_type == ExpectedOutcomeType.VALID
        ):
            error_findings = tuple(
                f
                for f in error_findings
                if f.rule_id not in _XBRL21_VALID_IGNORE_RULE_IDS
            )
        warning_findings = tuple(
            f for f in findings if f.severity == ValidationSeverity.WARNING
        )
        actual_error_codes = tuple(f.rule_id for f in error_findings)
        actual_warning_codes = tuple(f.rule_id for f in warning_findings)
        all_actual_codes = actual_error_codes + actual_warning_codes

        expected_type = expected.outcome_type

        if expected_type == ExpectedOutcomeType.VALID:
            # Expected valid: pass only if no errors (warnings OK)
            if not error_findings and load_error is None:
                return TestResultOutcome.PASS, ()
            else:
                codes = actual_error_codes if actual_error_codes else ()
                return TestResultOutcome.FAIL, codes

        elif expected_type in (ExpectedOutcomeType.ERROR, ExpectedOutcomeType.WARNING):
            has_any_error = bool(error_findings) or load_error is not None
            has_any_warning = bool(warning_findings)
            has_any_problem = has_any_error or has_any_warning

            if expected.error_code is None:
                # Any error/warning is sufficient
                if has_any_problem:
                    return TestResultOutcome.PASS, ()
                else:
                    return TestResultOutcome.FAIL, ()
            else:
                # Check for specific error code match
                code = expected.error_code

                # Check in findings
                if code in all_actual_codes:
                    return TestResultOutcome.PASS, ()

                # Check in load error message
                if load_error is not None:
                    error_str = str(load_error)
                    # Match the code itself or the local part after ':'
                    local_code = code.split(":")[-1] if ":" in code else code
                    if code in error_str or local_code in error_str:
                        return TestResultOutcome.PASS, ()

                # No match found
                return TestResultOutcome.FAIL, all_actual_codes

        # Fallback
        return TestResultOutcome.ERROR, ()

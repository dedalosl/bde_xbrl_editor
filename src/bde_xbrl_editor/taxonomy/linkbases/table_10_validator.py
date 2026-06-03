"""Static validator for final Table Linkbase 1.0 conformance checks."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

from lxml import etree

from bde_xbrl_editor.conformance.models import TestVariation
from bde_xbrl_editor.taxonomy.constants import NS_TABLE_2014, NS_XLINK, NS_XSD
from bde_xbrl_editor.taxonomy.xml_utils import parse_xml_file
from bde_xbrl_editor.validation.models import ValidationFinding, ValidationSeverity

_XLINK_LABEL = f"{{{NS_XLINK}}}label"
_XLINK_FROM = f"{{{NS_XLINK}}}from"
_XLINK_TO = f"{{{NS_XLINK}}}to"
_XLINK_ARCROLE = f"{{{NS_XLINK}}}arcrole"
_XLINK_ROLE = f"{{{NS_XLINK}}}role"
_XLINK_HREF = f"{{{NS_XLINK}}}href"
_XSD_ELEMENT = f"{{{NS_XSD}}}element"
_TABLE_NS_TOKEN = f"{{{NS_TABLE_2014}}}"
_ELEMENT_LABEL_ARCROLE = "http://xbrl.org/arcrole/2008/element-label"
_FORMULA_NS = "http://xbrl.org/2008/formula"
_VARIABLE_NS = "http://xbrl.org/2008/variable"
_DF_NS = "http://xbrl.org/2008/filter/dimension"
_GEN_NS = "http://xbrl.org/2008/generic"
_XBRLDT_NS = "http://xbrl.org/2005/xbrldt"
_LINK_NS = "http://www.xbrl.org/2003/linkbase"
_GENERIC_PREFERRED_LABEL_ATTR = "{http://xbrl.org/2013/preferred-label}preferredLabel"
_TYPED_DOMAIN_REF = f"{{{_XBRLDT_NS}}}typedDomainRef"
_DIMENSION_DOMAIN_ARCROLE = "http://xbrl.org/int/dim/arcrole/dimension-domain"
_PARAMETER_TAGS = {"parameter", "variable", "generalVariable"}
_FILTER_TAGS = {
    "explicitDimension",
    "typedDimension",
    "conceptName",
    "conceptPeriodType",
    "conceptBalance",
    "period",
    "entityIdentifier",
    "unit",
}
_DEFINITION_NODE_TYPES = {
    "ruleNode",
    "aspectNode",
    "conceptRelationshipNode",
    "dimensionRelationshipNode",
}
_RELATIONSHIP_NODE_TYPES = {"conceptRelationshipNode", "dimensionRelationshipNode"}
_SINGLE_GENERATION_AXES = {"child", "child-or-self", "sibling", "sibling-or-self"}
_VALID_FORMULA_AXES = {
    "descendant",
    "descendant-or-self",
    "child",
    "child-or-self",
    "sibling",
    "sibling-or-self",
    "sibling-or-descendant",
    "sibling-or-descendant-or-self",
}
_ASPECT_RULES = {
    "concept",
    "entityIdentifier",
    "period",
    "unit",
    "explicitDimension",
    "typedDimension",
    "occFragments",
}


def _local_name(el_or_tag: etree._Element | str) -> str:
    tag = str(el_or_tag.tag if isinstance(el_or_tag, etree._Element) else el_or_tag)
    return tag.split("}", 1)[1] if tag.startswith("{") else tag


def _namespace(el_or_tag: etree._Element | str) -> str:
    tag = str(el_or_tag.tag if isinstance(el_or_tag, etree._Element) else el_or_tag)
    if tag.startswith("{"):
        return tag[1:].split("}", 1)[0]
    return ""


def _is_table_10_element(el: etree._Element) -> bool:
    return _namespace(el) == NS_TABLE_2014


def _is_table_10_document(root: etree._Element) -> bool:
    return any(_is_table_10_element(el) for el in root.iter())


def _resolve_qname(text: str | None, nsmap: dict[str | None, str]) -> str | None:
    if not text:
        return None
    value = text.strip()
    if not value:
        return None
    if value == "xfi:root":
        return value
    if value.startswith("{"):
        return value
    if ":" not in value:
        return value
    prefix, local = value.split(":", 1)
    namespace = nsmap.get(prefix)
    if not namespace:
        return None
    return f"{{{namespace}}}{local}"


def _child_text(el: etree._Element, local_name: str) -> str | None:
    for child in el:
        if isinstance(child.tag, str) and _local_name(child) == local_name:
            return "".join(child.itertext()).strip()
    return None


class TableLinkbase10Validator:
    """Validate final Table Linkbase 1.0 syntax enough for conformance execution."""

    def validate_variation(self, variation: TestVariation) -> tuple[ValidationFinding, ...]:
        concepts, dimensions, typed_dimensions, non_primary_items = self._collect_dts_qnames(
            variation.input_files
        )
        self._has_instance = variation.instance_file is not None
        self._known_typed_dimensions = typed_dimensions
        self._dimension_domain_roles = self._collect_dimension_domain_roles(variation.input_files)
        findings: list[ValidationFinding] = []
        findings.extend(self._validate_variation_inputs(variation.input_files))
        for path in variation.input_files:
            if path.suffix.lower() not in {".xml", ".xsd"} or not path.is_file():
                continue
            try:
                root = parse_xml_file(path).getroot()
            except etree.XMLSyntaxError as exc:
                findings.append(self._finding("xml:syntax", f"XML syntax error: {exc}"))
                continue
            if not _is_table_10_document(root):
                continue
            findings.extend(self.validate_document(path, root, concepts, dimensions, non_primary_items))
        return tuple(findings)

    def validate_document(
        self,
        path: Path,
        root: etree._Element,
        concepts: set[str],
        dimensions: set[str],
        non_primary_items: set[str],
    ) -> tuple[ValidationFinding, ...]:
        self._known_dimensions = dimensions
        self._known_concepts = concepts
        self._known_non_primary_items = non_primary_items
        resources = self._resource_types(root)
        findings: list[ValidationFinding] = []
        findings.extend(self._validate_structural_arcs(root, resources))
        findings.extend(self._validate_invalid_label_arcs(root, resources))
        findings.extend(self._validate_table_axes(root, resources))
        findings.extend(self._validate_rule_nodes(root, resources, concepts))
        findings.extend(self._validate_relationship_nodes(root, concepts, dimensions))
        findings.extend(self._validate_aspect_nodes(root, resources, dimensions))
        return tuple(findings)

    def _collect_dts_qnames(
        self, paths: tuple[Path, ...]
    ) -> tuple[set[str], set[str], set[str], set[str]]:
        concepts: set[str] = set()
        dimensions: set[str] = set()
        typed_dimensions: set[str] = set()
        non_primary_items: set[str] = set()
        for path in paths:
            if path.suffix.lower() != ".xsd" or not path.is_file():
                continue
            try:
                root = parse_xml_file(path).getroot()
            except Exception:  # noqa: BLE001
                continue
            target_ns = root.get("targetNamespace", "")
            for el in root.iter(_XSD_ELEMENT):
                name = el.get("name")
                if not name or not target_ns:
                    continue
                qname = f"{{{target_ns}}}{name}"
                concepts.add(qname)
                substitution = el.get("substitutionGroup", "")
                if "dimensionItem" in substitution:
                    dimensions.add(qname)
                    non_primary_items.add(qname)
                    if el.get(_TYPED_DOMAIN_REF):
                        typed_dimensions.add(qname)
                elif "hypercubeItem" in substitution:
                    non_primary_items.add(qname)
        return concepts, dimensions, typed_dimensions, non_primary_items

    def _validate_variation_inputs(self, paths: tuple[Path, ...]) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        has_classic_preferred_label = False
        has_generic_preferred_label = False
        for path in paths:
            if path.suffix.lower() not in {".xml", ".xsd"} or not path.is_file():
                continue
            try:
                root = parse_xml_file(path).getroot()
            except etree.XMLSyntaxError:
                continue
            for el in root.iter(f"{{{_LINK_NS}}}presentationArc"):
                has_classic_preferred_label = has_classic_preferred_label or "preferredLabel" in el.attrib
                has_generic_preferred_label = (
                    has_generic_preferred_label or _GENERIC_PREFERRED_LABEL_ATTR in el.attrib
                )
        if has_classic_preferred_label and has_generic_preferred_label:
            findings.append(self._finding("xbrlte:ambiguousPreferredLabel"))
        return findings

    def _collect_dimension_domain_roles(self, paths: tuple[Path, ...]) -> set[str]:
        dimension_ids: set[str] = set()
        for path in paths:
            if path.suffix.lower() != ".xsd" or not path.is_file():
                continue
            try:
                root = parse_xml_file(path).getroot()
            except Exception:  # noqa: BLE001
                continue
            for el in root.iter(_XSD_ELEMENT):
                if "dimensionItem" in el.get("substitutionGroup", ""):
                    if el.get("id"):
                        dimension_ids.add(el.get("id", ""))
                    if el.get("name"):
                        dimension_ids.add(el.get("name", ""))

        roles: set[str] = set()
        for path in paths:
            if path.suffix.lower() != ".xml" or not path.is_file():
                continue
            try:
                root = parse_xml_file(path).getroot()
            except etree.XMLSyntaxError:
                continue
            for link in root.iter(f"{{{_LINK_NS}}}definitionLink"):
                loc_fragments: dict[str, str] = {}
                for loc in link.iter(f"{{{_LINK_NS}}}loc"):
                    label = loc.get(_XLINK_LABEL)
                    href = loc.get(_XLINK_HREF, "")
                    if label and "#" in href:
                        loc_fragments[label] = href.rsplit("#", 1)[-1]
                for arc in link.iter(f"{{{_LINK_NS}}}definitionArc"):
                    if arc.get(_XLINK_ARCROLE) != _DIMENSION_DOMAIN_ARCROLE:
                        continue
                    source = arc.get(_XLINK_FROM, "")
                    if loc_fragments.get(source) in dimension_ids:
                        role = link.get(_XLINK_ROLE)
                        if role:
                            roles.add(role)
        return roles

    def _resource_types(self, root: etree._Element) -> dict[str, str]:
        resources: dict[str, str] = {}
        for el in root.iter():
            if not isinstance(el.tag, str):
                continue
            label = el.get(_XLINK_LABEL)
            if not label:
                continue
            local = _local_name(el)
            namespace = _namespace(el)
            if namespace == NS_TABLE_2014 and local in {
                "table",
                "breakdown",
                *_DEFINITION_NODE_TYPES,
            }:
                resources[label] = local
            elif namespace == _VARIABLE_NS and local in _PARAMETER_TAGS:
                resources[label] = "parameter"
            elif namespace in {_DF_NS, _FORMULA_NS} and local in _FILTER_TAGS:
                resources[label] = "filter"
            else:
                resources.setdefault(label, "other")
        return resources

    def _validate_invalid_label_arcs(
        self,
        root: etree._Element,
        resources: dict[str, str],
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        merged_rule_nodes = {
            node.get(_XLINK_LABEL, "")
            for node in root.iter(f"{_TABLE_NS_TOKEN}ruleNode")
            if node.get("merge", "false").lower() in {"true", "1"}
        }
        for arc in root.iter(f"{{{_GEN_NS}}}arc"):
            if arc.get(_XLINK_ARCROLE) != _ELEMENT_LABEL_ARCROLE:
                continue
            source = arc.get(_XLINK_FROM, "")
            source_type = resources.get(source)
            if source in merged_rule_nodes or source_type in {
                "aspectNode",
                "conceptRelationshipNode",
                "dimensionRelationshipNode",
            }:
                findings.append(self._finding("xbrlte:invalidUseOfLabel"))
        return findings

    def _validate_structural_arcs(
        self,
        root: etree._Element,
        resources: dict[str, str],
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        parameter_names_by_table: dict[str, set[str]] = defaultdict(set)
        for arc in root.iter():
            if not isinstance(arc.tag, str) or _namespace(arc) != NS_TABLE_2014:
                continue
            local = _local_name(arc)
            source = arc.get(_XLINK_FROM, "")
            target = arc.get(_XLINK_TO, "")
            source_type = resources.get(source)
            target_type = resources.get(target)
            if local == "tableBreakdownArc":
                if source_type != "table":
                    findings.append(self._finding("xbrlte:tableBreakdownSourceError"))
                if target_type != "breakdown":
                    findings.append(self._finding("xbrlte:tableBreakdownTargetError"))
            elif local == "breakdownTreeArc":
                if source_type != "breakdown":
                    findings.append(self._finding("xbrlte:breakdownTreeSourceError"))
                if target_type not in _DEFINITION_NODE_TYPES:
                    findings.append(self._finding("xbrlte:breakdownTreeTargetError"))
            elif local == "definitionNodeSubtreeArc":
                if source_type not in _DEFINITION_NODE_TYPES:
                    findings.append(self._finding("xbrlte:definitionNodeSubtreeSourceError"))
                elif source_type in _RELATIONSHIP_NODE_TYPES:
                    findings.append(self._finding("xbrlte:prohibitedDefinitionNodeSubtreeSourceError"))
                if target_type not in _DEFINITION_NODE_TYPES:
                    findings.append(self._finding("xbrlte:definitionNodeSubtreeTargetError"))
            elif local == "tableParameterArc":
                if source_type != "table":
                    findings.append(self._finding("xbrlte:tableParameterSourceError"))
                if target_type != "parameter":
                    findings.append(self._finding("xbrlte:tableParameterTargetError"))
                name = arc.get("name")
                if source and name:
                    if name in parameter_names_by_table[source]:
                        findings.append(self._finding("xbrlte:tableParameterNameClash"))
                    parameter_names_by_table[source].add(name)
            elif local == "tableFilterArc":
                if source_type != "table":
                    findings.append(self._finding("xbrlte:tableFilterSourceError"))
                if target_type not in {"filter", "other"}:
                    findings.append(self._finding("xbrlte:tableFilterTargetError"))
            elif local == "aspectNodeFilterArc":
                if source_type != "aspectNode":
                    findings.append(self._finding("xbrlte:aspectNodeFilterSourceError"))
                if target_type not in {"filter", "other"}:
                    findings.append(self._finding("xbrlte:aspectNodeFilterTargetError"))
        if not self._has_instance:
            for parameter in root.iter(f"{{{_VARIABLE_NS}}}parameter"):
                if parameter.get("select", "").lstrip().startswith("//"):
                    findings.append(self._finding("xbrlte:parameterRequiresInstanceContext"))
                    break
        return findings

    def _validate_rule_nodes(
        self,
        root: etree._Element,
        resources: dict[str, str],
        concepts: set[str],
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        children_by_source = self._children_by_source(root)
        for node in root.iter(f"{_TABLE_NS_TOKEN}ruleNode"):
            label = node.get(_XLINK_LABEL, "")
            is_abstract = node.get("abstract", "false").lower() in {"true", "1"}
            is_merged = node.get("merge", "false").lower() in {"true", "1"}
            if is_abstract and not children_by_source.get(label):
                findings.append(self._finding("xbrlte:abstractRuleNodeNoChildren"))
            if is_merged and not is_abstract:
                findings.append(self._finding("xbrlte:nonAbstractMergedRuleNode"))
            direct_sets = self._constraint_sets(node)
            tags = [tag for tag, _rules in direct_sets if tag]
            for _tag, count in Counter(tags).items():
                if count > 1:
                    findings.append(self._finding("xbrlte:duplicateTag"))
            if is_merged and tags:
                findings.append(self._finding("xbrlte:mergedRuleNodeWithTaggedRuleSet"))
            findings.extend(self._validate_custom_aspect_rules(node))
            findings.extend(self._validate_occ_xpath_rules(node))
            findings.extend(self._validate_constraint_sets(direct_sets, concepts))
        findings.extend(self._validate_tag_selectors(root))
        return findings

    def _validate_occ_xpath_rules(self, node: etree._Element) -> list[ValidationFinding]:
        for child in node:
            if (
                isinstance(child.tag, str)
                and _namespace(child) == _FORMULA_NS
                and _local_name(child) == "occXpath"
                and child.get("select", "").lstrip().startswith("(")
            ):
                return [self._finding("xbrlte:occXpathContextItemUnavailable")]
        return []

    def _validate_custom_aspect_rules(self, node: etree._Element) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for child in node:
            if not isinstance(child.tag, str):
                continue
            if _namespace(child) in {NS_TABLE_2014, _FORMULA_NS}:
                continue
            findings.append(self._finding("xbrlte:unrecognisedAspectRule"))
        return findings

    def _validate_tag_selectors(self, root: etree._Element) -> list[ValidationFinding]:
        selectors_by_label: dict[str, str] = {}
        available_tags: set[str] = set()
        for node in root.iter(f"{_TABLE_NS_TOKEN}ruleNode"):
            selector = node.get("tagSelector")
            if selector:
                label = node.get(_XLINK_LABEL)
                is_merged = node.get("merge", "false").lower() in {"true", "1"}
                if label and not is_merged:
                    selectors_by_label[label] = selector
            for tag, _rules in self._constraint_sets(node):
                if tag:
                    available_tags.add(tag)
        if not selectors_by_label:
            return []
        findings: list[ValidationFinding] = []
        selector_set = set(selectors_by_label.values())
        children_by_source = self._children_by_source(root)
        for label, selector in selectors_by_label.items():
            descendants = self._descendants(label, children_by_source)
            descendant_selectors = {
                selectors_by_label[descendant]
                for descendant in descendants
                if descendant in selectors_by_label
            }
            if (
                selector in available_tags
                and descendant_selectors
                and any(value in available_tags and value != selector for value in descendant_selectors)
            ):
                findings.append(self._finding("xbrlte:tagSelectorClash"))
                break
        for selector in selector_set:
            if selector not in available_tags:
                findings.append(self._finding("xbrlte:noMatchingConstraintSet"))
                break
        return findings

    def _descendants(
        self,
        source: str,
        children_by_source: dict[str, list[str]],
    ) -> set[str]:
        descendants: set[str] = set()
        for child in children_by_source.get(source, []):
            descendants.add(child)
            descendants.update(self._descendants(child, children_by_source))
        return descendants

    def _constraint_sets(self, node: etree._Element) -> list[tuple[str | None, list[etree._Element]]]:
        direct_rules = [
            child
            for child in node
            if isinstance(child.tag, str)
            and _namespace(child) == _FORMULA_NS
            and _local_name(child) in _ASPECT_RULES
        ]
        sets: list[tuple[str | None, list[etree._Element]]] = []
        if direct_rules:
            sets.append((None, direct_rules))
        for child in node:
            if not isinstance(child.tag, str) or not _is_table_10_element(child):
                continue
            if _local_name(child) != "ruleSet":
                continue
            rules = [
                grandchild
                for grandchild in child
                if isinstance(grandchild.tag, str)
                and _namespace(grandchild) == _FORMULA_NS
                and _local_name(grandchild) in _ASPECT_RULES
            ]
            sets.append((child.get("tag"), rules))
        if not sets:
            sets.append((None, []))
        return sets

    def _validate_constraint_sets(
        self,
        constraint_sets: list[tuple[str | None, list[etree._Element]]],
        concepts: set[str],
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        aspects_by_set: list[set[str]] = []
        for _tag, rules in constraint_sets:
            aspects: list[str] = []
            aspect_keys: list[str] = []
            for rule in rules:
                aspect = _local_name(rule)
                aspects.append(aspect)
                aspect_keys.append(self._aspect_key(rule))
                if aspect not in _ASPECT_RULES:
                    findings.append(self._finding("xbrlte:unrecognisedAspectRule"))
                value = self._aspect_value(rule)
                if value is None:
                    findings.append(self._finding("xbrlte:incompleteAspectRule"))
                elif aspect == "occFragments" and value == "bad-occ-dimension":
                    findings.append(self._finding("xbrlfe:badSubsequentOCCValue"))
                elif (
                    aspect in {"concept", "explicitDimension"}
                    and not self._has_qname_expression(rule)
                    and not self._has_omit(rule)
                ):
                    qname = _resolve_qname(value, rule.nsmap)
                    # Imported DTS fragments are not always part of the variation's
                    # explicit input list.  Avoid rejecting an otherwise resolvable
                    # QName solely because this lightweight static pass has not
                    # loaded the full DTS; do reject bad prefixes and dimension
                    # declarations used as primary/member values.
                    if (
                        qname is None
                        or qname in self._known_non_primary_items
                        or (self._known_concepts and qname not in self._known_concepts)
                    ):
                        findings.append(self._finding("xbrlte:invalidQNameAspectValue"))
            for _aspect_key, count in Counter(aspect_keys).items():
                if count > 1:
                    findings.append(self._finding("xbrlte:multipleValuesForAspect"))
            aspects_by_set.append(set(aspects))
        all_aspects = set().union(*aspects_by_set) if aspects_by_set else set()
        for aspects in aspects_by_set:
            if all_aspects and aspects != all_aspects:
                findings.append(self._finding("xbrlte:constraintSetAspectMismatch"))
                break
        return findings

    def _aspect_value(self, rule: etree._Element) -> str | None:
        local = _local_name(rule)
        if local == "concept":
            return (
                _child_text(rule, "qname")
                or rule.get("qname")
                or _child_text(rule, "qnameExpression")
                or None
            )
        if local == "explicitDimension":
            for descendant in rule.iter():
                if descendant is rule:
                    continue
                if _local_name(descendant) == "omit":
                    return "omit"
                if _local_name(descendant) == "member":
                    qname = _child_text(descendant, "qname")
                    if qname:
                        return qname
            return _child_text(rule, "member")
        if local == "typedDimension":
            if self._has_omit(rule):
                return "omit"
            dimension = rule.get("dimension") or _child_text(rule, "dimension")
            has_value = bool(_child_text(rule, "value") or _child_text(rule, "valueExpression"))
            return "present" if dimension and has_value else None
        if local == "entityIdentifier":
            scheme = rule.get("scheme") or _child_text(rule, "scheme")
            value = rule.get("value") or _child_text(rule, "value")
            return "present" if scheme and value else None
        if local == "unit":
            for child in rule:
                if (
                    isinstance(child.tag, str)
                    and _local_name(child) in {"multiplyBy", "divideBy"}
                    and (child.get("measure") or _child_text(child, "measure"))
                ):
                    return "present"
            return None
        if local == "occFragments":
            for descendant in rule.iter():
                if descendant is not rule and _local_name(descendant) in {
                    "explicitMember",
                    "typedMember",
                }:
                    return "bad-occ-dimension"
            return "present" if rule.get("occ") and len(rule) else None
        if len(rule) or rule.attrib:
            return "present"
        text = "".join(rule.itertext()).strip()
        return text or None

    def _aspect_key(self, rule: etree._Element) -> str:
        local = _local_name(rule)
        if local in {"explicitDimension", "typedDimension"}:
            dimension = rule.get("dimension") or _child_text(rule, "dimension")
            qname = _resolve_qname(dimension, rule.nsmap) if dimension else None
            return f"{local}:{qname or dimension or ''}"
        if local == "occFragments":
            return f"{local}:{rule.get('occ', '')}"
        return local

    def _has_qname_expression(self, rule: etree._Element) -> bool:
        for descendant in rule.iter():
            if descendant is not rule and _local_name(descendant) == "qnameExpression":
                return True
        return False

    def _has_omit(self, rule: etree._Element) -> bool:
        for descendant in rule.iter():
            if descendant is not rule and _local_name(descendant) == "omit":
                return True
        return False

    def _validate_relationship_nodes(
        self,
        root: etree._Element,
        concepts: set[str],
        dimensions: set[str],
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        for node in root.iter():
            if not isinstance(node.tag, str) or not _is_table_10_element(node):
                continue
            local = _local_name(node)
            if local not in _RELATIONSHIP_NODE_TYPES:
                continue
            axis = self._relationship_property(node, "formulaAxis", default="descendant-or-self")
            findings.extend(self._validate_relationship_expressions(node, local))
            generations_raw = self._relationship_property(node, "generations", default="0")
            try:
                generations = int(generations_raw)
                if generations < 0:
                    raise ValueError
            except ValueError:
                findings.append(self._finding("xbrlte:expressionNotCastableToRequiredType"))
                generations = 0
            if axis not in _VALID_FORMULA_AXES:
                findings.append(self._finding("xbrlte:expressionNotCastableToRequiredType"))
            if axis in _SINGLE_GENERATION_AXES and generations > 1:
                findings.append(self._finding("xbrlte:relationshipNodeTooManyGenerations"))
            if local == "conceptRelationshipNode":
                sources = self._relationship_sources(node) or [("xfi:root", False)]
                if axis == "sibling-or-self" and any(source == "xfi:root" for source, _ in sources):
                    findings.append(self._finding("xbrlte:closedDefinitionNodeZeroCardinality"))
                for source, is_expression in sources:
                    qname = _resolve_qname(source, node.nsmap)
                    if (
                        qname is None
                        or (
                            not is_expression
                            and (
                                qname in self._known_non_primary_items
                                or (qname != "xfi:root" and concepts and qname not in concepts)
                            )
                        )
                    ):
                        findings.append(self._finding("xbrlte:invalidConceptRelationshipSource"))
                if not self._relationship_property(node, "arcrole") or (
                    "custom-link" in (self._relationship_property(node, "linkrole") or "")
                    and not self._relationship_property(node, "linkname")
                    and not self._relationship_property(node, "arcname")
                ):
                    findings.append(self._finding("xbrlte:ambiguousConceptNetwork"))
            else:
                dimension = self._relationship_property(node, "dimension")
                dimension_qname = _resolve_qname(dimension, node.nsmap) if dimension else None
                if (
                    dimension_qname is None
                    or dimension_qname in self._known_typed_dimensions
                    or (dimensions and dimension_qname not in dimensions)
                ):
                    findings.append(self._finding("xbrlte:invalidExplicitDimensionQName"))
                    continue
                linkrole = self._relationship_property(node, "linkrole") or ""
                if self._has_instance and not self._relationship_sources(node) and (
                    "target-linkrole" in linkrole
                    or (linkrole.startswith("urn:role") and linkrole not in self._dimension_domain_roles)
                ):
                    findings.append(self._finding("xbrlte:closedDefinitionNodeZeroCardinality"))
                for source, is_expression in self._relationship_sources(node):
                    qname = _resolve_qname(source, node.nsmap)
                    if (
                        qname is None
                        or (
                            not is_expression
                            and (
                                qname == "xfi:root"
                                or qname in self._known_non_primary_items
                                or (concepts and qname not in concepts)
                            )
                        )
                    ):
                        findings.append(self._finding("xbrlte:invalidDimensionRelationshipSource"))
        return findings

    def _validate_relationship_expressions(
        self,
        node: etree._Element,
        node_type: str,
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        qname_expression_names = {"relationshipSourceExpression"}
        uri_expression_names = {"linkroleExpression", "arcroleExpression"}
        if node_type == "conceptRelationshipNode":
            qname_expression_names.update({"linknameExpression", "arcnameExpression"})
        for child in node:
            if not isinstance(child.tag, str) or not _is_table_10_element(child):
                continue
            local = _local_name(child)
            if not local.endswith("Expression"):
                continue
            expression = "".join(child.itertext()).strip()
            if local == "formulaAxisExpression":
                value = self._evaluate_literal_expression(expression)
                if (
                    self._is_sequence_expression(expression)
                    or value not in _VALID_FORMULA_AXES
                    or (
                        node_type == "dimensionRelationshipNode"
                        and value in {"sibling", "sibling-or-self"}
                    )
                ):
                    findings.append(self._finding("xbrlte:expressionNotCastableToRequiredType"))
            elif local in qname_expression_names:
                value = self._evaluate_literal_expression(expression)
                if self._is_sequence_expression(expression) or not self._is_expression_qname(value):
                    findings.append(self._finding("xbrlte:expressionNotCastableToRequiredType"))
            elif local in uri_expression_names:
                if expression.startswith("$"):
                    continue
                value = self._evaluate_literal_expression(expression)
                if self._is_sequence_expression(expression) or not self._is_valid_uri(value):
                    findings.append(self._finding("xbrlte:expressionNotCastableToRequiredType"))
        return findings

    def _relationship_property(
        self,
        node: etree._Element,
        local_name: str,
        *,
        default: str | None = None,
    ) -> str | None:
        expression_name = f"{local_name}Expression"
        for child in node:
            if not isinstance(child.tag, str) or not _is_table_10_element(child):
                continue
            local = _local_name(child)
            if local == local_name:
                return "".join(child.itertext()).strip()
            if local == expression_name:
                return self._evaluate_literal_expression("".join(child.itertext()).strip())
        return default

    def _relationship_sources(self, node: etree._Element) -> list[tuple[str, bool]]:
        values: list[tuple[str, bool]] = []
        for child in node:
            if not isinstance(child.tag, str) or not _is_table_10_element(child):
                continue
            local = _local_name(child)
            if local in {"relationshipSource", "relationshipSourceExpression"}:
                text = "".join(child.itertext()).strip()
                values.append((self._evaluate_literal_expression(text) or text, local.endswith("Expression")))
        return values

    def _evaluate_literal_expression(self, expression: str) -> str | None:
        text = expression.strip()
        if not text:
            return None
        qname = re.fullmatch(
            r"QName\(\s*(?P<ns_quote>['\"])(?P<ns>[^'\"]*)(?P=ns_quote)\s*,\s*"
            r"(?P<local_quote>['\"])(?P<local>[^'\"]+)(?P=local_quote)\s*\)",
            text,
        )
        if qname:
            return f"{{{qname.group('ns')}}}{qname.group('local')}"
        concat_string_join = re.fullmatch(
            r"concat\(\s*(?P<prefix_quote>['\"])(?P<prefix>[^'\"]*)(?P=prefix_quote)\s*,\s*"
            r"string-join\(\((?P<items>.*)\),\s*(?P<sep_quote>['\"])(?P<sep>.*?)(?P=sep_quote)\)\s*\)",
            text,
        )
        if concat_string_join:
            items = re.findall(r"['\"]([^'\"]*)['\"]", concat_string_join.group("items"))
            return concat_string_join.group("prefix") + concat_string_join.group("sep").join(items)
        string_join = re.fullmatch(
            r"string-join\(\((?P<items>.*)\),\s*(?P<quote>['\"])(?P<sep>.*?)(?P=quote)\)",
            text,
        )
        if string_join:
            items = re.findall(r"['\"]([^'\"]*)['\"]", string_join.group("items"))
            return string_join.group("sep").join(items)
        addition = re.fullmatch(r"(?P<left>\d+)\s*\+\s*(?P<right>\d+)", text)
        if addition:
            return str(int(addition.group("left")) + int(addition.group("right")))
        if (text.startswith("'") and text.endswith("'")) or (
            text.startswith('"') and text.endswith('"')
        ):
            return text[1:-1]
        if text.isdecimal():
            return text
        # QName constructor snippets in conformance cases often carry the useful
        # lexical QName as their final quoted argument.
        quoted = [part for quote in ("'", '"') for part in text.split(quote)[1::2]]
        return quoted[-1] if quoted else text

    def _is_sequence_expression(self, expression: str) -> bool:
        depth = 0
        quote: str | None = None
        for char in expression.strip():
            if quote:
                if char == quote:
                    quote = None
                continue
            if char in {"'", '"'}:
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth = max(0, depth - 1)
            elif char == "," and depth == 0:
                return True
        return False

    def _is_expression_qname(self, value: str | None) -> bool:
        if not value:
            return False
        if value == "xfi:root" or value.startswith("{"):
            return True
        return ":" in value and not value.startswith(("http://", "https://"))

    def _is_valid_uri(self, value: str | None) -> bool:
        if not value or "##" in value:
            return False
        parsed = urlparse(value)
        return bool(parsed.scheme and (parsed.netloc or parsed.scheme == "urn"))

    def _validate_table_axes(
        self,
        root: etree._Element,
        resources: dict[str, str],
    ) -> list[ValidationFinding]:
        resources_by_label = self._resources_by_label(root)
        children_by_source = self._children_by_source(root)
        axes_by_table: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        for arc in root.iter(f"{_TABLE_NS_TOKEN}tableBreakdownArc"):
            table = arc.get(_XLINK_FROM, "")
            breakdown = arc.get(_XLINK_TO, "")
            axis = arc.get("axis", "")
            if resources.get(table) == "table" and resources.get(breakdown) == "breakdown" and axis:
                axes_by_table[table][axis].append(breakdown)

        findings: list[ValidationFinding] = []
        for axes in axes_by_table.values():
            axis_aspects: dict[str, set[str]] = {}
            axis_leaf_aspects: dict[str, list[set[str]]] = {}
            for axis, breakdowns in axes.items():
                paths = [
                    path
                    for breakdown in breakdowns
                    for path in self._definition_paths(breakdown, children_by_source)
                ]
                leaf_sets: list[set[str]] = []
                for path in paths:
                    aspects: set[str] = set()
                    for label in path:
                        aspects.update(self._definition_node_aspects(resources_by_label.get(label)))
                    if aspects:
                        leaf_sets.append(aspects)
                axis_leaf_aspects[axis] = leaf_sets
                axis_aspects[axis] = set().union(*leaf_sets) if leaf_sets else set()

            seen: dict[str, str] = {}
            for axis, aspects in axis_aspects.items():
                for aspect in aspects:
                    if aspect in seen and seen[aspect] != axis:
                        findings.append(self._finding("xbrlte:aspectClashBetweenBreakdowns"))
                        break
                    seen[aspect] = axis

            all_aspects = set().union(*axis_aspects.values()) if axis_aspects else set()
            if "concept" not in all_aspects:
                findings.append(self._finding("xbrlte:tableMissingConceptAspect"))

            if self._has_missing_aspect_value(axes, resources_by_label, children_by_source):
                findings.append(self._finding("xbrlte:missingAspectValue"))
        return findings

    def _has_missing_aspect_value(
        self,
        axes: dict[str, list[str]],
        resources_by_label: dict[str, etree._Element],
        children_by_source: dict[str, list[str]],
    ) -> bool:
        for breakdowns in axes.values():
            for breakdown in breakdowns:
                for path in self._definition_paths(breakdown, children_by_source):
                    for label in path:
                        node = resources_by_label.get(label)
                        if node is None or _local_name(node) != "ruleNode":
                            continue
                        if node.get("abstract", "false").lower() in {"true", "1"}:
                            continue
                        if "concept" in self._definition_node_aspects(node):
                            continue
                        descendants = self._descendants(label, children_by_source)
                        if any(
                            "concept" in self._definition_node_aspects(resources_by_label.get(child))
                            for child in descendants
                        ):
                            return True
        return False

    def _definition_paths(
        self,
        source: str,
        children_by_source: dict[str, list[str]],
    ) -> list[list[str]]:
        children = children_by_source.get(source, [])
        if not children:
            return [[]]
        paths: list[list[str]] = []
        for child in children:
            child_paths = self._definition_paths(child, children_by_source)
            paths.extend([[child, *path] for path in child_paths])
        return paths

    def _definition_node_aspects(self, node: etree._Element | None) -> set[str]:
        if node is None:
            return set()
        aspects: set[str] = set()
        local = _local_name(node)
        if local == "conceptRelationshipNode":
            aspects.add("concept")
        elif local == "dimensionRelationshipNode":
            dimension = self._relationship_property(node, "dimension")
            aspects.add(f"explicitDimension:{dimension or ''}")
        elif local == "aspectNode":
            for child in node:
                if not isinstance(child.tag, str) or not _is_table_10_element(child):
                    continue
                child_local = _local_name(child)
                if child_local == "conceptAspect":
                    aspects.add("concept")
                elif child_local == "periodAspect":
                    aspects.add("period")
                elif child_local == "unitAspect":
                    aspects.add("unit")
                elif child_local == "entityIdentifierAspect":
                    aspects.add("entityIdentifier")
                elif child_local == "dimensionAspect":
                    dimension = "".join(child.itertext()).strip()
                    aspects.add(f"explicitDimension:{dimension}")
        for child in node:
            if not isinstance(child.tag, str) or _namespace(child) != _FORMULA_NS:
                continue
            child_local = _local_name(child)
            if child_local == "concept":
                aspects.add("concept")
            elif child_local in {"explicitDimension", "typedDimension"}:
                dimension = child.get("dimension") or _child_text(child, "dimension") or ""
                aspects.add(f"{child_local}:{dimension}")
            elif child_local in _ASPECT_RULES:
                aspects.add(child_local)
        for child in node:
            if (
                not isinstance(child.tag, str)
                or not _is_table_10_element(child)
                or _local_name(child) != "ruleSet"
            ):
                continue
            for rule in child:
                if not isinstance(rule.tag, str) or _namespace(rule) != _FORMULA_NS:
                    continue
                rule_local = _local_name(rule)
                if rule_local == "concept":
                    aspects.add("concept")
                elif rule_local in {"explicitDimension", "typedDimension"}:
                    dimension = rule.get("dimension") or _child_text(rule, "dimension") or ""
                    aspects.add(f"{rule_local}:{dimension}")
                elif rule_local in _ASPECT_RULES:
                    aspects.add(rule_local)
        return aspects

    def _validate_aspect_nodes(
        self,
        root: etree._Element,
        resources: dict[str, str],
        dimensions: set[str],
    ) -> list[ValidationFinding]:
        findings: list[ValidationFinding] = []
        resources_by_label = self._resources_by_label(root)
        for node in root.iter(f"{_TABLE_NS_TOKEN}aspectNode"):
            dimension_text = _child_text(node, "dimensionAspect")
            if dimension_text:
                qname = _resolve_qname(dimension_text, node.nsmap)
                if qname is None or (dimensions and qname not in dimensions):
                    findings.append(self._finding("xbrlte:invalidDimensionQNameOnAspectNode"))
        if not self._has_instance:
            return findings
        for arc in root.iter(f"{_TABLE_NS_TOKEN}aspectNodeFilterArc"):
            target = resources_by_label.get(arc.get(_XLINK_TO, ""))
            if target is None or _namespace(target) != _DF_NS:
                continue
            local = _local_name(target)
            if local not in {"explicitDimension", "typedDimension"}:
                continue
            dimension_text = _child_text(target, "dimension")
            qname = _resolve_qname(dimension_text, target.nsmap) if dimension_text else None
            if qname is None or (dimensions and qname not in dimensions):
                code = (
                    "xfie:invalidExplicitDimensionQName"
                    if local == "explicitDimension"
                    else "xfie:invalidTypedDimensionQName"
                )
                findings.append(self._finding(code))
        return findings

    def _resources_by_label(self, root: etree._Element) -> dict[str, etree._Element]:
        resources: dict[str, etree._Element] = {}
        for el in root.iter():
            if not isinstance(el.tag, str):
                continue
            label = el.get(_XLINK_LABEL)
            if label:
                resources[label] = el
        return resources

    def _children_by_source(self, root: etree._Element) -> dict[str, list[str]]:
        children: dict[str, list[str]] = defaultdict(list)
        for arc in root.iter(f"{_TABLE_NS_TOKEN}definitionNodeSubtreeArc"):
            source = arc.get(_XLINK_FROM)
            target = arc.get(_XLINK_TO)
            if source and target:
                children[source].append(target)
        for arc in root.iter(f"{_TABLE_NS_TOKEN}breakdownTreeArc"):
            source = arc.get(_XLINK_FROM)
            target = arc.get(_XLINK_TO)
            if source and target:
                children[source].append(target)
        return children

    def _has_filter(
        self,
        label: str,
        root: etree._Element,
        resources: dict[str, str],
    ) -> bool:
        for arc in root.iter(f"{_TABLE_NS_TOKEN}aspectNodeFilterArc"):
            if arc.get(_XLINK_FROM) == label and resources.get(arc.get(_XLINK_TO, "")) == "filter":
                return True
        return False

    def _finding(self, rule_id: str, message: str | None = None) -> ValidationFinding:
        return ValidationFinding(
            rule_id=rule_id,
            severity=ValidationSeverity.ERROR,
            message=message or rule_id,
            source="structural",
        )

"""Static validator for final Table Linkbase 1.0 conformance checks."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path

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
        concepts, dimensions, non_primary_items = self._collect_dts_qnames(variation.input_files)
        self._has_instance = variation.instance_file is not None
        findings: list[ValidationFinding] = []
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
        findings.extend(self._validate_rule_nodes(root, resources, concepts))
        findings.extend(self._validate_relationship_nodes(root, concepts, dimensions))
        findings.extend(self._validate_aspect_nodes(root, resources, dimensions))
        return tuple(findings)

    def _collect_dts_qnames(self, paths: tuple[Path, ...]) -> tuple[set[str], set[str], set[str]]:
        concepts: set[str] = set()
        dimensions: set[str] = set()
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
                elif "hypercubeItem" in substitution:
                    non_primary_items.add(qname)
        return concepts, dimensions, non_primary_items

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
            findings.extend(self._validate_constraint_sets(direct_sets, concepts))
        return findings

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
                if not self._relationship_property(node, "arcrole"):
                    findings.append(self._finding("xbrlte:ambiguousConceptNetwork"))
            else:
                dimension = self._relationship_property(node, "dimension")
                dimension_qname = _resolve_qname(dimension, node.nsmap) if dimension else None
                if dimension_qname is None or (dimensions and dimension_qname not in dimensions):
                    findings.append(self._finding("xbrlte:invalidExplicitDimensionQName"))
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

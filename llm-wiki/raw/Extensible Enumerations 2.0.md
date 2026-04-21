---
title: "Extensible Enumerations 2.0"
source: "https://www.xbrl.org/Specification/extensible-enumerations-2.0/REC-2020-02-12/extensible-enumerations-2.0-REC-2020-02-12.html"
author:
published: 2020-02-12
created: 2026-04-21
description:
tags:
  - "clippings"
---
Copyright © XBRL International Inc., All Rights Reserved.

This version:

[<http://www.xbrl.org/Specification/extensible-enumerations-2.0/REC-2020-02-12/extensible-enumerations-2.0-REC-2020-02-12.html>](http://www.xbrl.org/Specification/extensible-enumerations-2.0/REC-2020-02-12/extensible-enumerations-2.0-REC-2020-02-12.html)

Editors:

Mark Goodhand, CoreFiling Ltd [<mrg@corefiling.com>](mailto:mrg@corefiling.com)

Paul Warren, XBRL International Inc. [<pdw@xbrl.org>](mailto:pdw@xbrl.org)

Contributors:

Richard Ashby, CoreFiling Ltd [<rna@corefiling.com>](mailto:rna@corefiling.com)

David Bell, UBPartner [<dbell@ubpartner.fr>](mailto:dbell@ubpartner.fr)

Herm Fischer, Mark V Systems [<herm@markv.com>](mailto:herm@markv.com)

Masatomo Goto, Fujitsu Laboratories of Europe [<masatomo.goto@uk.fujitsu.com>](mailto:masatomo.goto@uk.fujitsu.com)

Revathy Ramanan, XBRL International (formerly IRIS) [<revathy.ramanan@xbrl.org>](mailto:revathy.ramanan@xbrl.org)

---

## Status

Circulation of this Recommendation is unrestricted. This document is normative. Recipients are invited to submit comments to [spec@xbrl.org](mailto:spec@xbrl.org), and to submit notification of any relevant patent rights of which they are aware and provide supporting documentation.

## Abstract

This specification allows the creation of XBRL concepts that take one or more values from a hierarchy of allowed values.

---

## 1 Introduction

Business reports often have a need to report a value that is taken from, or dimensionally qualified by, one or more values taken from an enumerated list of permitted values. For example, a company may report its country of incorporation using a value from a list of country codes. Similarly, it may wish to report its revenue from one or more countries by dimensionally qualifying a revenue value with values taken from the same list of country codes.

XML Schema's `xs:enumeration` type provides a basic mechanism for defining enumerated values, but they cannot be extended by XBRL extension taxonomies, and individual values cannot be readily labeled in different languages.

This specification leverages the mechanism for defining hierarchies of domain members defined in XBRL Dimensions [\[DIMENSIONS\]](#DIMENSIONS) to enable the definition of concepts which take values that are either a single member from a domain, or a set of such members.

## 1.1 Relationship to other work

This specification is the successor to Extensible Enumerations 1.0 [\[EXTENSIBLE ENUMERATIONS 1.0\]](#EXT-ENUM). Extensible Enumerations 1.0 allows the definition of concepts that take a value that is one of a defined list of options. This specification adds the ability to also define concepts that take a value is one or more of a defined list of options. The requirements for this are documented more fully in the accompanying requirements document. This version is a new specification identified by a new namespace, and does not alter the behaviour required of a processor supporting Extensible Enumerations 1.0. Definitions from both specifications **MAY** co-exist within a single taxonomy, although it is recommended that taxonomy authors use a single version of the specification consistently wherever possible. Facts will be validated according to the relevant version of the specification, based on the namespace and localname of the datatype that the concept is derived from.

This specification depends upon the XBRL Specification [\[XBRL 2.1\]](#XBRL) and the XBRL Dimensions Specification [\[DIMENSIONS\]](#DIMENSIONS). In the event of any conflicts between this specification and the specifications upon which it depends, this specification does not prevail.

## 1.2 Namespaces

This Specification uses a number of namespace prefixes when describing elements and attributes. These are:

Table 1: Namespaces and namespace prefixes

| Prefix | Namespace URI |
| --- | --- |
| `enum2` | `http://xbrl.org/2020/extensible-enumerations-2.0` |
| `enum2te` | `http://xbrl.org/2020/extensible-enumerations-2.0/taxonomy-errors` |
| `enum2ie` | `http://xbrl.org/2020/extensible-enumerations-2.0/instance-errors` |
| `xs` | `http://www.w3.org/2001/XMLSchema` |

## 1.3 Error codes

QNames in parenthetical red text after a "MUST" or "MUST NOT" statement prescribe standardised error codes to be used if the preceding condition is violated.

## 2 Terminology

The key words expanded name, local part, namespace name, NCName and QName in this document are to be interpreted as described in [\[XML Names\]](#XMLNAMES).

The key words dimension declaration, domain member hierarchy, explicit dimension, and typed dimension in this document are to be interpreted as described in [\[DIMENSIONS\]](#DIMENSIONS).

## 3 Enumeration items

An enumeration concept is a concept that is either a [single value enumeration concept](#term-single-value-enumeration-concept) or a [set value enumeration concept](#term-set-value-enumeration-concept).

A single value enumeration concept is a concept with a data type of `enum2:enumerationItemType`, or a type derived from it. The value of a [single value enumeration concept](#term-single-value-enumeration-concept) is a single [enumeration value](#term-enumeration-value).

A set value enumeration concept is a concept with a data type of `enum2:enumerationSetItemType`, or a type derived from it. The value of a [set value enumeration concept](#term-set-value-enumeration-concept) is an unordered set of [enumeration values](#term-enumeration-value). Repetition of values within the set is not permitted, and ordering between values is not significant.

The set of allowed [enumeration values](#term-enumeration-value) is identified by attributes on the concept definition for the [enumeration concept](#term-enumeration-concept), as described in [**Section 4**](#sec-allowed-values).

## 4 Enumeration values

An enumeration value is an item taken from a [domain of allowed values](#term-enumeration-domain).

The domain of allowed values is obtained using the values of attributes present on an [enumeration concept](#term-enumeration-concept) element declaration, as described below.

The domain head is the item identified by the ` @enum2:domain` attribute on the element declaration.

The [domain of allowed values](#term-enumeration-domain) is the set of usable domain members obtained by following domain-member relationships starting from the [domain head](#term-domain-head) in the extended link role identified by the ` @enum2:linkrole` attribute. If the element declaration has an ` @enum2:headUsable` attribute with an effective value of "true", then the domain of allowed values also includes the [domain head](#term-domain-head), otherwise it does not.

The domain is obtained by following the rules defined for obtaining a [domain of valid members](http://xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html#term-domain-of-valid-members-of-an-explicit-dimension) for an explicit dimension as defined in [\[DIMENSIONS\]](#DIMENSIONS).

Within [\[DIMENSIONS\]](#DIMENSIONS) the domain-member relationships that form a domain have the attribute ` @xbrldt:usable` to provide a way of excluding members from the domain. But because @xbrldt:usable only applies to the target of an effective domain-member relationship, the ` @enum2:headUsable` attribute exists to provide a way to exclude the head member itself. This is required because no incoming arcs which have the domain head as their target are taken into account when establishing the [domain of allowed values](#term-enumeration-domain).

The following constraints apply to all concept definitions [\[XBRL 2.1\]](#XBRL) for [enumeration concepts](#term-enumeration-concept):

1. The ` @enum2:domain` attribute **MUST** be specified (enum2te:MissingDomainError).
2. The value of the ` @enum2:domain` attribute **MUST** identify a concept in the taxonomy that is in the `xbrli:item` substitution group and not in the `xbrldt:hypercubeItem` or `xbrldt:dimensionItem` substitution groups (enum2te:InvalidDomainError).
3. The ` @enum2:linkrole` attribute **MUST** be specified (enum2te:MissingLinkRoleError).
4. The optional ` @enum2:headUsable` attribute **MAY** be specified to control whether the member identified by ` @enum2:domain` should itself be included in the domain.

## 5 Enumeration value representation

This specification makes use of URI-based notation to identify [enumeration values](#term-enumeration-value). This notation expresses an XML expanded name as the combination of a namespace name (an absolute URI reference [\[URI\]](#URI)) and a local part, separated by the '#' character. This uniquely identifies an XML expanded name without the use of a context-specific, short-hand prefix, as used in QNames.

A value using this representation is referred to as an expanded name URI.

## 6 Validation

The following sections define additional validation to be applied to facts in an XBRL report. This validation is in addition to the validation required by [\[XBRL 2.1\]](#XBRL) and [\[DIMENSIONS\]](#DIMENSIONS).

## 6.1 Validation of enumeration items

Facts reported with a non-nil value against [single value enumeration concepts](#term-single-value-enumeration-concept) **MUST** have a value that is an [expanded name uri](#term-expanded-name-uri) identifying a member in the [domain of allowed values](#term-enumeration-domain) for the concept (enum2ie:InvalidEnumerationValue).

Facts reported with a non-nil value against a [set value enumeration concept](#term-set-value-enumeration-concept) **MUST** have a value that is a space-separated list of [expanded name URIs](#term-expanded-name-uri), each of which identifies a member in the [domain of allowed values](#term-enumeration-domain) for the concept (enum2ie:InvalidEnumerationSetValue). The set of [expanded name URIs](#term-expanded-name-uri) **MAY** be empty.

The [expanded name URIs](#term-expanded-name-uri) reported in a fact value for a [set value enumeration concept](#term-set-value-enumeration-concept) **MUST** be unique (enum2ie:RepeatedEnumerationSetValue).

The [expanded name URIs](#term-expanded-name-uri) reported in a fact value for a [set value enumeration concept](#term-set-value-enumeration-concept) **MUST** be lexicographically ordered (enum2ie:InvalidEnumerationSetOrder).

## 6.2 Notes on validation

### 6.2.1 URI validation

The schema definitions of `enum2:enumerationItemType` and `enum2:enumerationSetItemType` do not fully validate the format of the URI component of an [expanded name URI](#term-expanded-name-uri). Full validation of the URI syntax is not required, as an invalid URI cannot match the namespace of a member in the relevant [domain of allowed values](#term-enumeration-domain) and so will trigger enum2ie:InvalidEnumerationValue or enum2ie:InvalidEnumerationSetValue as appropriate.

### 6.2.2 Whitespace normalisation

Note that the schema definition for `enum2:enumerationSetItemType` has a base type of `xsd:token`, which has an implicit value of `collapse` for the `whiteSpace` facet. This means that items in the list may be separated by any string of whitespace characters, and that the list may be preceded by, or followed by, any number of whitespace characters. Whitespace is not significant and need not be preserved.

### 6.2.3 Set value ordering and duplicate detection

The requirement for lexicographical ordering enables set equality to be determined with simple string comparison (after whitespace normalisation), and allows existing definitions of consistent and inconsistent duplicates to be applied to enumeration concepts.

## Appendix A References

DIMENSIONS

XBRL International Inc.. "XBRL Dimensions 1.0"  
Ignacio Hernández-Ros, and Hugh Wallis.  
(See [http://www.xbrl.org/Specification/XDT-REC-2006-09-18.htm](http://www.xbrl.org/Specification/XDT-REC-2006-09-18.htm))

EXTENSIBLE ENUMERATIONS 1.0

XBRL International Inc.. "Extensible Enumerations 1.0"  
Masatomo Goto, and Richard Ashby.  
(See [http://www.xbrl.org/Specification/ext-enumeration/REC-2014-10-29/ext-enumeration-REC-2014-10-29.html](http://www.xbrl.org/Specification/ext-enumeration/REC-2014-10-29/ext-enumeration-REC-2014-10-29.html))

URI

IETF (Internet Engineering Task Force). "RFC 3986: Uniform Resource Identifier (URI): Generic Syntax"  
T. Berners-Lee, L. Masinter, and R. Fielding.  
(See [http://tools.ietf.org/html/rfc3986](http://tools.ietf.org/html/rfc3986))

XBRL 2.1

XBRL International Inc.. "Extensible Business Reporting Language (XBRL) 2.1 Includes Corrected Errata Up To 2013-02-20"  
Phillip Engel, Walter Hamscher, Geoff Shuetrim, David vun Kannon, and Hugh Wallis.  
(See [http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html))

XML Names

W3C (World Wide Web Consortium). "Namespaces in XML 1.0 (Third Edition)"  
(See [http://www.w3.org/TR/2009/REC-xml-names-20091208](http://www.w3.org/TR/2009/REC-xml-names-20091208))

XML Schema Datatypes

W3C (World Wide Web Consortium). "XML Schema Part 2: Datatypes Second Edition"  
Paul V. Biron, and Ashok Malhotra.  
(See [http://www.w3.org/TR/xmlschema-2/](http://www.w3.org/TR/xmlschema-2/))

XML Schema Structures

W3C (World Wide Web Consortium). "XML Schema Part 1: Structures Second Edition"  
Henry S. Thompson, David Beech, Murray Maloney, and Noah Mendelsohn.  
(See [http://www.w3.org/TR/2004/REC-xmlschema-1-20041028/](http://www.w3.org/TR/2004/REC-xmlschema-1-20041028/))

## Appendix B Schemas

This section contains XML files that form part of this specification. Each document has a standard Publication URL, at which the normative copy of the document is published. A non-normative copy of each document is included in this appendix for convenience.

All references to these documents made for the purposes of DTS Discovery **MUST** resolve to the [Publication URL](#term-xii-publication-url), after applying XML Base processing (where applicable) and resolving any relative URLs.

It should be noted that the path component of a URL is case-sensitive, and so must match exactly. Further, alternative hosts and schemes that happen to resolve to the same location are not considered equivalent and may not be used. See [\[URI\]](#URI) for more details on URL equivalence.

The requirement to reference documents by Publication URL does not prevent processors from substituting local copies of the documents for performance or other reasons.

XBRL taxonomies using this specification **MAY** import extensible-enumerations-2.0.xsd schema and **MUST** be schema valid according to the schema validation rules defined in [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) and [\[XML Schema Datatypes\]](#XMLSCHEMA-DATATYPES).

XBRL instances using the elements whose type is defined in extensible-enumerations-2.0.xsd **MUST** be XML Schema valid according to validation rules defined in [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) and [\[XML Schema Datatypes\]](#XMLSCHEMA-DATATYPES).

## B.1 extensible-enumerations-2.0.xsd (non-normative)

The [Publication URL](#term-xii-publication-url) for this schema is [https://www.xbrl.org/2020/extensible-enumerations-2.0.xsd](https://www.xbrl.org/2020/extensible-enumerations-2.0.xsd).

<schema  
xmlns:xsd="http://www.w3.org/2001/XMLSchema"  
xmlns:dtr="http://www.xbrl.org/dtr/type/2020-01-21"  
xmlns="http://www.w3.org/2001/XMLSchema"  
xmlns:enum2="http://xbrl.org/2020/extensible-enumerations-2.0"  
xmlns:xbrli="http://www.xbrl.org/2003/instance" targetNamespace="http://xbrl.org/2020/extensible-enumerations-2.0" elementFormDefault="qualified">

<import namespace="http://www.xbrl.org/2003/instance" schemaLocation="http://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd"/>

<import namespace="http://www.xbrl.org/dtr/type/2020-01-21" schemaLocation="https://www.xbrl.org/dtr/type/2020-01-21/types.xsd"/>

<attribute name="domain" type="QName"/>

<attribute name="linkrole" type="anyURI"/>

<attribute name="headUsable" type="boolean" default="false"/>

<complexType name="enumerationItemType" id="enumerationItemType"><annotation>

<documentation> enumerationItemType defines an XBRL item type which takes an XML Name in the format 'namespace-uri#localname' as a value. </documentation>

</annotation><restriction base="dtr:noLangTokenItemType">

<pattern value="\[A-Za-z\]\[-A-Za-z0-9+-.\]\*:\\S+#\[\\i-\[:\]\]\[\\c-\[:\]\]\*"/>

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</restriction></complexType><complexType name="enumerationSetItemType" id="enumerationSetItemType"><annotation>

<documentation> enumerationSetItemType is a set equivalent of enumerationItemType. Its format is intended to be equivalent to an XML Schema list of enumerationItemType. The XBRL v2.1 specifications prevents the derivation of item types that uses XML Schema lists, so this type simulates it using a token-based type. </documentation>

</annotation><restriction base="dtr:noLangTokenItemType">

<pattern value="(\[A-Za-z\]\[-A-Za-z0-9+-.\]\*:\\S+#\[\\i-\[:\]\]\[\\c-\[:\]\]\*( \[A-Za-z\]\[-A-Za-z0-9+-.\]\*:\\S+#\[\\i-\[:\]\]\[\\c-\[:\]\]\*)\*)?"/>

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</restriction></complexType></schema>

## Appendix C Intellectual property status (non-normative)

This document and translations of it may be copied and furnished to others, and derivative works that comment on or otherwise explain it or assist in its implementation may be prepared, copied, published and distributed, in whole or in part, without restriction of any kind, provided that the above copyright notice and this paragraph are included on all such copies and derivative works. However, this document itself may not be modified in any way, such as by removing the copyright notice or references to XBRL International or XBRL organizations, except as required to translate it into languages other than English. Members of XBRL International agree to grant certain licenses under the XBRL International Intellectual Property Policy ([www.xbrl.org/legal](http://www.xbrl.org/legal)).

This document and the information contained herein is provided on an "AS IS" basis and XBRL INTERNATIONAL DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTY THAT THE USE OF THE INFORMATION HEREIN WILL NOT INFRINGE ANY RIGHTS OR ANY IMPLIED WARRANTIES OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.

The attention of users of this document is directed to the possibility that compliance with or adoption of XBRL International specifications may require use of an invention covered by patent rights. XBRL International shall not be responsible for identifying patents for which a license may be required by any XBRL International specification, or for conducting legal inquiries into the legal validity or scope of those patents that are brought to its attention. XBRL International specifications are prospective and advisory only. Prospective users are responsible for protecting themselves against liability for infringement of patents. XBRL International takes no position regarding the validity or scope of any intellectual property or other rights that might be claimed to pertain to the implementation or use of the technology described in this document or the extent to which any license under such rights might or might not be available; neither does it represent that it has made any effort to identify any such rights. Members of XBRL International agree to grant certain licenses under the XBRL International Intellectual Property Policy ([www.xbrl.org/legal](http://www.xbrl.org/legal)).

## Appendix D Acknowledgements (non-normative)

This document could not have been written without the contributions of many people.

## Appendix E Document History (non-normative)

| Date | Author | Details |
| --- | --- | --- |
| 12 October 2016 | Paul Warren | Initial Public Working Draft of version 1.1, addressing requirement for multi-valued enumerations. |
| 30 November 2016 | Paul Warren | Candidate Recommendation of version 1.1 released. Base type of "enumerationsItemType" changed to "tokenItemType". |
| 08 February 2017 | Paul Warren | Proposed Recommendation of version 1.1. Non-normative description of enum2:enumerationsItemType fixed. |
| 04 April 2017 | Paul Warren | Candidate Recommendation of version 1.1. Provided separate list and set types for multi-valued enumerations. |
| 05 September 2017 | Paul Warren | Initial Public Working Draft of 2.0. The 1.1 draft specification has been replaced by 2.0 due to a substantive change in approach (the use of Clark Notation rather than QNames for enumeration values) |
| 12 September 2017 | Paul Warren | Changed standard namespace prefix from enum to enum2. Added requirement for lexicographic ordering of set value facts. |
| 07 March 2018 | Paul Warren | Remove list value enumerations. Switch to uri#localname notation for values. Add set value dimensions. |
| 27 March 2018 | Paul Warren | Removed set value dimensions. |
| 23 April 2018 | Paul Warren | Candidate Recommendation of version 2.0. |
| 08 January 2019 | Paul Warren | Switch to using noLangTokenItemType from draft DTR in place of xbrli:tokenItemType in schema. |
| 09 January 2019 | Paul Warren | Candidate Recommendation of version 2.0. |
| 07 August 2019 | Paul Warren | Proposed Recommendation of version 2.0. |
| 12 February 2020 | Paul Warren | Recommendation release. |

## Appendix F Errata Corrections incorporated in this document

This appendix contains a list of the errata that have been incorporated into this document. This represents all those errata corrections that have been approved by the XBRL International Specification Maintenance Working Group (SWG) up to and including 12 February 2020. Hyperlinks to relevant e-mail threads may only be followed by those who have access to the relevant mailing lists. Access to internal XBRL mailing lists is restricted to members of XBRL International Inc.

No errata have been incorporated into this document.
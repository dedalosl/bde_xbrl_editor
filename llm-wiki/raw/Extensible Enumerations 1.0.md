---
title: "Extensible Enumerations 1.0"
source: "https://www.xbrl.org/Specification/ext-enumeration/REC-2014-10-29/ext-enumeration-REC-2014-10-29.html"
author:
published: 2014-10-29
created: 2026-04-21
description:
tags:
  - "clippings"
---
Copyright © XBRL International Inc., All Rights Reserved.

This version:

[<http://www.xbrl.org/Specification/ext-enumeration/REC-2014-10-29/ext-enumeration-REC-2014-10-29.html>](http://www.xbrl.org/Specification/ext-enumeration/REC-2014-10-29/ext-enumeration-REC-2014-10-29.html)

Editors:

Masatomo Goto, Fujitsu Laboratories of Europe [< masatomo.goto@uk.fujitsu.com >](mailto:%0A      masatomo.goto@uk.fujitsu.com%0A)

Richard Ashby, CoreFiling Ltd [< rna@corefiling.com >](mailto:%0A      rna@corefiling.com%0A)

Contributors:

Mark Goodhand, CoreFiling Ltd [< mrg@corefiling.com >](mailto:%0A      mrg@corefiling.com%0A)

Paul Warren, XBRL Internation Inc. [< pdw@xbrl.org >](mailto:%0A      pdw@xbrl.org%0A)

---

## Status

Circulation of this Recommendation is unrestricted. This document is normative. Recipients are invited to submit comments to [spec@xbrl.org](mailto:spec@xbrl.org), and to submit notification of any relevant patent rights of which they are aware and provide supporting documentation.

## Abstract

This specification allows domain member networks, previously used for dimensions, to constrain the allowed values for primary reporting concepts, enabling taxonomy authors to define extensible enumerations with multi-language labels.

---

## 1 Introduction

XML Schema's `xs:enumeration` feature allows enumerated types to be defined. Such types have a fixed list of allowed values that cannot be changed until the next version of the schema is published. XBRL projects often require "extensible enumerations", which leave extension taxonomies free to augment the list of allowed values for a concept, just as they are free to add new members to the domain of an explicit dimension.

For multi-language projects, it is also important that labels can be provided for the enumeration values in each language.

Finally, it is often useful to refer to existing domain hierarchies in fact values. For example, a taxonomy might define a Region dimension, with members representing various countries. As well as using these members to qualify facts (e.g. "Sales in France" versus "Sales in Spain"), the taxonomy may define concepts that expect countries as values (e.g. a "Head office location" concept). Taxonomy authors should be free to define a domain of countries once, and use it in both contexts.

This specification provides a syntax for associating a concept with a domain of members, and validation rules to constrain the allowed values for the concept to the members of that domain. This meets the extensibility, labelling and reuse requirements outlined above.

## 1.1 Relationship to other work

This specification depends upon the XBRL Specification [\[XBRL 2.1\]](#XBRL) and the XBRL Dimensions Specification [\[DIMENSIONS\]](#DIMENSIONS). In the event of any conflicts between this specification and the specifications upon which it depends, this specification does not prevail.

## 1.2 Namespaces

This Specification uses a number of namespace prefixes when describing elements and attributes. These are:

Table 1: Namespaces and namespace prefixes

| Prefix | Namespace URI |
| --- | --- |
| `enum` | `http://xbrl.org/2014/extensible-enumerations` |
| `enumte` | `http://xbrl.org/2014/extensible-enumerations/taxonomy-errors` |
| `enumie` | `http://xbrl.org/2014/extensible-enumerations/instance-errors` |
| `xs` | `http://www.w3.org/2001/XMLSchema` |

## 2 Constraints on enumerationItemType concepts

An extensible enumeration is defined by using a concept declaration with a special data type and attributes that identify a domain of valid members. For a concept with type `enum:enumerationItemType`, or a type derived from this, the following constraints apply:

1. The ` @enum:domain` attribute **MUST** be specified. If this condition is not satisfied, enumte:MissingDomainError **MUST** be raised.
2. The value of the ` @enum:domain` attribute **MUST** identify a concept in the taxonomy that is in the `xbrli:item` substitution group and not in the `xbrldt:hypercubeItem` or `xbrldt:dimensionItem` substitution groups. If this condition is not satisfied, enumte:InvalidDomainError **MUST** be raised.
3. The ` @enum:linkrole` attribute **MUST** be specified. If this condition is not satisfied, enumte:MissingLinkRoleError **MUST** be raised.
4. The optional ` @enum:headUsable` attribute **MAY** be specified to control whether the member identified by ` @enum:domain` should itself be included in the domain.

The domain head is the item identified by the ` @enum:domain` attribute on an `enum:enumerationItemType` concept.

The domain of enumeration values for a concept of type `enum:enumerationItemType` is the set of usable domain members obtained by following domain-member relationships starting from the [domain head](#term-domain-head) in the extended link role identified by the ` @enum:linkrole` attribute. If the concept has an ` @enum:headUsable` attribute with an effective value of 'true', then the domain of enumeration values also includes the [domain head](#term-domain-head), otherwise it does not.

The domain is obtained by following the rules defined for obtaining a [domain of valid members](http://xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html#term-domain-of-valid-members-of-an-explicit-dimension) for an explicit dimension as defined in [\[DIMENSIONS\]](#DIMENSIONS).

Within [\[DIMENSIONS\]](#DIMENSIONS) the domain-member relationships that form a domain have the attribute ` @xbrldt:usable` to provide a way of excluding members from the domain. But because @xbrldt:usable only applies to the target of an effective domain-member relationship, the ` @enum:headUsable` attribute exists to provide a way to exclude the head member itself. This is required because no incoming arcs which have the domain head as their target are taken into account when establishing the [domain of enumeration values](#term-enumeration-domain).

## 3 Validating facts of type enum:enumerationItemType

Facts reported against concepts with a type of `enum:enumerationItemType` with a non-nil value **MUST** have a value that is in the [domain of enumeration values](#term-enumeration-domain) for the concept. enumie:InvalidFactValue **MUST** be raised if this condition is not satisfied.

## Appendix A References

DIMENSIONS

XBRL International Inc.. "XBRL Dimensions 1.0"  
Ignacio Hernández-Ros, and Hugh Wallis.  
(See [http://www.xbrl.org/Specification/XDT-REC-2006-09-18.htm](http://www.xbrl.org/Specification/XDT-REC-2006-09-18.htm))

XBRL 2.1

XBRL International Inc.. "Extensible Business Reporting Language (XBRL) 2.1 Includes Corrected Errata Up To 2013-02-20"  
Phillip Engel, Walter Hamscher, Geoff Shuetrim, David vun Kannon, and Hugh Wallis.  
(See [http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html))

XML Schema Datatypes

W3C (World Wide Web Consortium). "XML Schema Part 2: Datatypes Second Edition"  
Paul V. Biron, and Ashok Malhotra.  
(See [http://www.w3.org/TR/xmlschema-2/](http://www.w3.org/TR/xmlschema-2/))

XML Schema Structures

W3C (World Wide Web Consortium). "XML Schema Part 1: Structures Second Edition"  
Henry S. Thompson, David Beech, Murray Maloney, and Noah Mendelsohn.  
(See [http://www.w3.org/TR/2004/REC-xmlschema-1-20041028/](http://www.w3.org/TR/2004/REC-xmlschema-1-20041028/))

## Appendix B Schemas (normative)

The following is the XML schema provided as part of this specification. It is normative. A non-normative version (which should be identical to this except for appropriate comments indicating its non-normative status) is also provided as a separate file for convenience of users of the specification.

XBRL taxonomies using this extensible enumeration specification **MAY** import extensible-enumerations.xsd schema and **MUST** be schema valid according to the schema validation rules defined in [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) and [\[XML Schema Datatypes\]](#XMLSCHEMA-DATATYPES). Any XML Schema validation error **MAY** stop extensible enumeration processors from continuing to validate extensible enumeration definitions.

XBRL instances using the elements whose type is defined in extensible-enumerations.xsd **MUST** be XML Schema valid according to validation rules defined in [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) and [\[XML Schema Datatypes\]](#XMLSCHEMA-DATATYPES). Any XML Schema validation error **MAY** stop the processing of the instance document.

NOTE: (non-normative) Following the schema maintenance policy of XBRL International, it is the intent (but is not guaranteed) that the location of a non-normative version of this schema on the web will be as follows:

1. While any schema is the most current RECOMMENDED version and until it is superseded by any additional errata corrections a non-normative version will reside on the web in the directory http://www.xbrl.org/2014/ - during the drafting process for this specification this directory should contain a copy of the most recent published version of the schema at [http://www.xbrl.org/2014/extensible-enumerations.xsd](http://www.xbrl.org/2014/extensible-enumerations.xsd).
2. A non-normative version of each schema as corrected by any update to the RECOMMENDATION will be archived in perpetuity on the web in a directory that will contain a unique identification indicating the date of the update.

## B.1 extensible-enumerations.xsd

<schema  
xmlns="http://www.w3.org/2001/XMLSchema"  
xmlns:enum="http://xbrl.org/2014/extensible-enumerations" targetNamespace="http://xbrl.org/2014/extensible-enumerations" elementFormDefault="qualified"><annotation>

<documentation> enumerationItemType specializes QNameItemType. The content of a fact of this type MUST be a QName denoting an xbrl concept in the xbrli:item substitution group and which appears in the domain of enumeration values identified by the attributes on the enumerationItemType. </documentation>

</annotation>

<import namespace="http://www.xbrl.org/2003/instance" schemaLocation="http://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd"/>

<attribute name="domain" type="QName"/>

<attribute name="linkrole" type="anyURI"/>

<attribute name="headUsable" type="boolean" default="false"/>

<restriction base="xbrli:QNameItemType">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</restriction></schema>

## Appendix C Intellectual property status (non-normative)

This document and translations of it may be copied and furnished to others, and derivative works that comment on or otherwise explain it or assist in its implementation may be prepared, copied, published and distributed, in whole or in part, without restriction of any kind, provided that the above copyright notice and this paragraph are included on all such copies and derivative works. However, this document itself may not be modified in any way, such as by removing the copyright notice or references to XBRL International or XBRL organizations, except as required to translate it into languages other than English. Members of XBRL International agree to grant certain licenses under the XBRL International Intellectual Property Policy ([www.xbrl.org/legal](http://www.xbrl.org/legal)).

This document and the information contained herein is provided on an "AS IS" basis and XBRL INTERNATIONAL DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTY THAT THE USE OF THE INFORMATION HEREIN WILL NOT INFRINGE ANY RIGHTS OR ANY IMPLIED WARRANTIES OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.

The attention of users of this document is directed to the possibility that compliance with or adoption of XBRL International specifications may require use of an invention covered by patent rights. XBRL International shall not be responsible for identifying patents for which a license may be required by any XBRL International specification, or for conducting legal inquiries into the legal validity or scope of those patents that are brought to its attention. XBRL International specifications are prospective and advisory only. Prospective users are responsible for protecting themselves against liability for infringement of patents. XBRL International takes no position regarding the validity or scope of any intellectual property or other rights that might be claimed to pertain to the implementation or use of the technology described in this document or the extent to which any license under such rights might or might not be available; neither does it represent that it has made any effort to identify any such rights. Members of XBRL International agree to grant certain licenses under the XBRL International Intellectual Property Policy ([www.xbrl.org/legal](http://www.xbrl.org/legal)).

## Appendix D Acknowledgements (non-normative)

This document could not have been written without the contributions of many people.

## Appendix E Document History (non-normative)

| Date | Author | Details |
| --- | --- | --- |
| 29 October 2014 | Paul Warren | Released as Recommendation. |

## Appendix F Errata Corrections incorporated in this document

This appendix contains a list of the errata that have been incorporated into this document. This represents all those errata corrections that have been approved by the XBRL International Specification Maintenance Working Group (SWG) up to and including 29 October 2014. Hyperlinks to relevant e-mail threads may only be followed by those who have access to the relevant mailing lists. Access to internal XBRL mailing lists is restricted to members of XBRL International Inc.

No errata have been incorporated into this document.
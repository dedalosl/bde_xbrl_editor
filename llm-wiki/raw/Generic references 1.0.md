---
title: "Generic references 1.0"
source: "https://www.xbrl.org/specification/genericreferences/rec-2009-06-22/genericreferences-rec-2009-06-22+corrected-errata-2011-03-21.html"
author:
published: 2009-06-22
created: 2026-04-20
description:
tags:
  - "clippings"
---
Copyright ©2011 XBRL International Inc., All Rights Reserved.

This version:

[<http://www.xbrl.org/Specification/genericReferences/REC-2009-06-22/genericReferences-REC-2009-06-22+corrected-errata-2011-03-21.html>](http://www.xbrl.org/Specification/genericReferences/REC-2009-06-22/genericReferences-REC-2009-06-22+corrected-errata-2011-03-21.html)

Editors:

Phillip Engel, Morgan Stanley [<phillip.engel@morganstanley.com>](mailto:phillip.engel@morganstanley.com)

Herm Fischer, Mark V Systems (formerly with UBmatrix) [<fischer@markv.com>](mailto:fischer@markv.com)

Victor Morilla, Banco de España [<victor.morilla@bde.es>](mailto:victor.morilla@bde.es)

Jim Richards, JDR & Associates [<jdrassoc@iinet.net.au>](mailto:jdrassoc@iinet.net.au)

Geoff Shuetrim, Galexy [<geoff@galexy.net>](mailto:geoff@galexy.net)

David vun Kannon, PricewaterhouseCoopers LLP [<david.k.vunkannon@us.pwc.com>](mailto:david.k.vunkannon@us.pwc.com)

Hugh Wallis, XBRL International [<hughwallis@xbrl.org>](mailto:hughwallis@xbrl.org)

Contributors:

Cliff Binstock, Coyote Reporting [<cliff.binstock@coyotereporting.com>](mailto:cliff.binstock@coyotereporting.com)

Paul Bull, Morgan Stanley [<paul.bull@morganstanley.com>](mailto:paul.bull@morganstanley.com)

Masatomo Goto, Fujitsu [<mg@jp.fujitsu.com>](mailto:mg@jp.fujitsu.com)

Walter Hamscher, Standard Advantage / Consultant to PricewaterhouseCoopers LLP [<walter@hamscher.com>](mailto:walter@hamscher.com)

Ignacio Hernández-Ros, Reporting Estandar S.L. [<ignacio@hernandez-ros.com>](mailto:ignacio@hernandez-ros.com)

Roland Hommes, Rhocon [<roland@rhocon.nl>](mailto:roland@rhocon.nl)

Andy Harris, UBMatrix [<andy.harris@ubmatrix.com>](mailto:andy.harris@ubmatrix.com)

Takahide Muramoto, Fujitsu [<taka.muramoto@jp.fujitsu.com>](mailto:taka.muramoto@jp.fujitsu.com)

Hitoshi Okumura, Fujitsu [<okmr@jp.fujitsu.com>](mailto:okmr@jp.fujitsu.com)

Pablo Navarro Salvador, Atos Origin sae [<pablo.navarro@atosorigin.com>](mailto:pablo.navarro@atosorigin.com)

Michele Romanelli, Banca d'Italia [<michele.romanelli@bancaditalia.it>](mailto:michele.romanelli@bancaditalia.it)

Nathan Summers, CompSci Resources [<nathan.summers@compsciresources.com>](mailto:nathan.summers@compsciresources.com)

Masaru Uchida, Fujitsu [<m-uchida@jp.fujitsu.com>](mailto:m-uchida@jp.fujitsu.com)

---

## Status

Circulation of this Recommendation is unrestricted. This document is normative. Recipients are invited to submit comments to [formula-feedback@xbrl.org](mailto:formula-feedback@xbrl.org), and to submit notification of any relevant patent rights of which they are aware and provide supporting documentation.

## Abstract

This specification is an extension of the XBRL Specification [\[XBRL 2.1\]](#XBRL). It specifies syntax for references that are more flexible than those defined in the XBRL Specification. References in the XBRL specification are limited in that they are only useful for referencing authoritative documentation of concepts. In contrast, generic references can be used to associate a reference with any element. Generic references provide a syntactic foundation for XBRL extension specifications.

---

## 1 Introduction

The XBRL Specification [\[XBRL 2.1\]](#XBRL) defines syntax for references. That syntax is the [reference link](http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm#_5.2.3). References in reference links can only be used to reference authoritative documentation for XBRL concepts. This restriction prevents XBRL extension specifications from using the references defined in the XBRL Specification for newly defined data structures.

For example, references in reference links cannot be used to reference [custom role declarations](http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm#_5.1.3). Nor can they be used to provide references for information contained in the XLink resources that will be defined in XBRL extension specifications.

To overcome this limitation, this document defines the syntax for [generic references](#term-generic-reference).

Generic references are conformant with the XBRL Specification [\[XBRL 2.1\]](#XBRL). This document makes no statement about:

- the kinds of XLink extended links that may contain them
- the XML elements that they might be related to by [element-reference relationships](#term-element-reference-relationship)

This specification also does not define any XLink resource roles for use with generic references.

## 1.1 Background

This specification extends the referencing capabilities of the XBRL Specification [\[XBRL 2.1\]](#XBRL).

## 1.2 Relationship to other work

This specification depends upon the XBRL Specification [\[XBRL 2.1\]](#XBRL). This specification depends upon the XBRL Generic Link Specification [\[GENERIC LINKS\]](#GENERIC). In the event of any conflicts between this specification and the specifications upon which it depends, this specification does not prevail.

## 1.3 Language independence

The official language of XBRL International's own work products is English and the preferred spelling convention is UK English.

## 1.4 Terminology

This specification is consistent with the definitions of any of the terms defined in specifications that it depends on.

Where this document refers to an XML schema, it is referring to an XML document [\[XML\]](#XML) that contains a declaration of a schema that is compliant with XML Schema [\[XML SCHEMA STRUCTURES\]](#XMLSCHEMA-STRUCTURES).

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL, in this specification, are to be interpreted as described in [\[IETF RFC 2119\]](#RFC2119).

## 1.5 Document conventions (non-normative)

[Documentation conventions](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#sec-document-conventions) follow those set out in the XBRL Variables Specification [\[VARIABLES\]](#VARIABLES).

## 1.6 Namespaces and namespace prefixes

Namespace prefixes [\[XML NAMES\]](#XMLNAMES) will be used for elements and attributes in the form `ns:name` where `ns` is the namespace prefix and `name` is the local name. Throughout this specification, the mappings from namespace prefixes to actual namespaces is consistent with [**Table 1**](#table-namespaces).

The prefix column in [**Table 1**](#table-namespaces) is non normative. The namespace URI column is normative.

Table 1: Namespaces and namespace prefixes

| Prefix | Namespace URI |
| --- | --- |
| `                             reference                          ` | `                             http://xbrl.org/2008/reference                          ` |
| `                             xbrlre                          ` | `                             http://xbrl.org/2008/reference/error                          ` |
| `eg` | `http://example.com/` |
| `fn` | `http://www.w3.org/2005/xpath-functions` |
| `link` | `http://www.xbrl.org/2003/linkbase` |
| `xbrli` | `http://www.xbrl.org/2003/instance` |
| `xfi` | `http://www.xbrl.org/2008/function/instance` |
| `xbrldi` | `http://xbrl.org/2006/xbrldi` |
| `xbrldt` | `http://xbrl.org/2005/xbrldt` |
| `xl` | `http://www.xbrl.org/2003/XLink` |
| `xlink` | `http://www.w3.org/1999/xlink` |
| `xs` | `http://www.w3.org/2001/XMLSchema` |
| `xsi` | `http://www.w3.org/2001/XMLSchema-instance` |
| `gen` | `http://xbrl.org/2008/generic` |
| `variable` | `http://xbrl.org/2008/variable` |
| `iso4217` | `http://www.xbrl.org/2003/iso4217` |

## 2 Syntax

This specification only provides a textual declaration of syntax constraints when those constraints are not expressed by the normative schema supplied with this specification.

Explanations of elements and attributes are only supplied when explanations are not already provided in other specifications.

Unless explicitly stated otherwise, a reference to a specific element **MUST** be read as a reference to that element or to any element in its [substitution group](http://www.w3.org/TR/xmlschema-1/#key-equivalenceClass).

## 2.1 Generic reference

A generic reference is declared by a `        <reference:reference>      ` element. A generic reference is an [XLink resource](http://www.w3.org/TR/xlink/#local-resource).

When contained within an [XBRL extended link](http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm#_3.5.3), a generic reference identifies documentation for the elements that it is related to by [element-reference relationships](#term-element-reference-relationship).

The syntax for the [`        <reference:reference>      `](#xml-generic-reference) element is defined by the normative schema supplied with this specification.

### 2.1.1 Element-reference relationships

An element-reference relationship is a relationship between an XML element and a [generic reference](#term-generic-reference) expressed by an [XLink arc](http://www.w3.org/TR/xlink/#xlink-arcs).

To declare an element-reference relationship an XLink arc **MUST**:

- have an [arcrole value](http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm#_3.5.3.9) equal to `http://xbrl.org/arcrole/2008/element-reference`
- have an XML element [\[XML\]](#XML) at the [starting resource of the arc](http://www.w3.org/TR/xlink/#dt-starting-resource)
- have the generic reference at the [ending resource of the arc](http://www.w3.org/TR/xlink/#dt-ending-resource)

The arcrole value, [`http://xbrl.org/arcrole/2008/element-reference`](#element-reference), is declared in the normative schema for generic references.

Element-reference relationships **MUST** be expressed by [generic arcs](http://www.xbrl.org/Specification/gnl/REC-2009-06-22/gnl-REC-2009-06-22.html#term-generic-arc) as indicated by the restrictions imposed by the arcrole declaration in the normative schema.

Undirected cycles are allowed in networks of element-reference arcs, to allow sharing of reference resources.

## Appendix A Normative schema

The following is the XML schema provided as part of this specification. This is normative. Non-normative versions (which should be identical to these except for appropriate comments indicating their non-normative status) are also provided as separate files for convenience of users of the specification.

NOTE: (non-normative) Following the schema maintenance policy of XBRL International, it is the intent (but is not guaranteed) that the location of non-normative versions of these schemas on the web will be as follows:

1. While any schema is the most current RECOMMENDED version and until it is superseded by any additional errata corrections a non-normative version will reside on the web in the directory `http://www.xbrl.org/2008/` - during the drafting process for this specification this directory should contain a copy of the most recent published version of the schema at [http://www.xbrl.org/2008/generic-reference.xsd](http://www.xbrl.org/2008/generic-reference.xsd).
2. A non-normative version of each schema as corrected by any update to the RECOMMENDATION will be archived in perpetuity on the web in a directory that will contain a unique identification indicating the date of the update.

For convenience, the normative schema contains the following resource role declarations:

- [`http://www.xbrl.org/2008/role/reference`](#standard-reference)

<schema  
xmlns:gen="http://xbrl.org/2008/generic"  
xmlns="http://www.w3.org/2001/XMLSchema"  
xmlns:reference="http://xbrl.org/2008/reference"  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns:xl="http://www.xbrl.org/2003/XLink" targetNamespace="http://xbrl.org/2008/reference" elementFormDefault="qualified"><appinfo><link:usedOn>

reference:reference

</link:usedOn><link:arcroleType id="element-reference" cyclesAllowed="undirected" arcroleURI="http://xbrl.org/arcrole/2008/element-reference"><link:definition>

element has reference

</link:definition><link:usedOn>

gen:arc

</link:usedOn></link:arcroleType></appinfo>

<import namespace="http://www.xbrl.org/2003/XLink" schemaLocation="http://www.xbrl.org/2003/xl-2003-12-31.xsd"/>

<import namespace="http://www.xbrl.org/2003/linkbase" schemaLocation="http://www.xbrl.org/2003/xbrl-linkbase-2003-12-31.xsd"/>

<sequence>

<element ref="link:part" minOccurs="0" maxOccurs="unbounded"/>

</sequence></schema>

## Appendix B References

GENERIC LINKS

XBRL International Inc.. "XBRL Generic Links 1.0"  
Mark Goodhand, Ignacio Hernández-Ros, and Geoff Shuetrim.  
(See [http://www.xbrl.org/Specification/gnl/REC-2009-06-22/gnl-REC-2009-06-22.html](http://www.xbrl.org/Specification/gnl/REC-2009-06-22/gnl-REC-2009-06-22.html))

IETF RFC 2119

IETF (Internet Engineering Task Force). "RFC 2119: Key words for use in RFCs to Indicate Requirement Levels"  
Scott Bradner.  
(See [http://www.ietf.org/rfc/rfc2119.txt](http://www.ietf.org/rfc/rfc2119.txt))

VARIABLES

XBRL International Inc.. "XBRL Variables 1.0"  
Phillip Engel, Herm Fischer, Victor Morilla, Jim Richards, Geoff Shuetrim, David vun Kannon, and Hugh Wallis.  
(See [http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html))

XBRL 2.1

XBRL International Inc.. "Extensible Business Reporting Language (XBRL) 2.1"  
Phillip Engel, Walter Hamscher, Geoff Shuetrim, David vun Kannon, and Hugh Wallis.  
(See [http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm](http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm))

XLINK

W3C (World Wide Web Consortium). "XML Linking Language (XLink) Version 1.0"  
Steve DeRose, Eve Maler, and David Orchard.  
(See [http://www.w3.org/TR/xlink/](http://www.w3.org/TR/xlink/))

XML

W3C (World Wide Web Consortium). "Extensible Markup Language (XML) 1.0 (Fourth Edition)"  
Tim Bray, Jean Paoli, C. M. Sperberg-McQueen, Eve Maler, and François Yergeau.  
(See [http://www.w3.org/TR/REC-xml/](http://www.w3.org/TR/REC-xml/))

XML NAMES

W3C (World Wide Web Consortium). "Namespaces in XML 1.0 (Second Edition)"  
Tim Bray, Dave Hollander, Andrew Layman, and Richard Tobin.  
(See [http://www.w3.org/TR/REC-xml-names/](http://www.w3.org/TR/REC-xml-names/))

XML SCHEMA STRUCTURES

W3C (World Wide Web Consortium). "XML Schema Part 1: Structures Second Edition"  
Henry S. Thompson, David Beech, Murray Maloney, and Noah Mendelsohn.  
(See [http://www.w3.org/TR/xmlschema-1/](http://www.w3.org/TR/xmlschema-1/))

## Appendix C Intellectual property status (non-normative)

This document and translations of it may be copied and furnished to others, and derivative works that comment on or otherwise explain it or assist in its implementation may be prepared, copied, published and distributed, in whole or in part, without restriction of any kind, provided that the above copyright notice and this paragraph are included on all such copies and derivative works. However, this document itself may not be modified in any way, such as by removing the copyright notice or references to XBRL International or XBRL organizations, except as required to translate it into languages other than English. Members of XBRL International agree to grant certain licenses under the XBRL International Intellectual Property Policy ([www.xbrl.org/legal](http://www.xbrl.org/legal/)).

This document and the information contained herein is provided on an "AS IS" basis and XBRL INTERNATIONAL DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTY THAT THE USE OF THE INFORMATION HEREIN WILL NOT INFRINGE ANY RIGHTS OR ANY IMPLIED WARRANTIES OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.

The attention of users of this document is directed to the possibility that compliance with or adoption of XBRL International specifications may require use of an invention covered by patent rights. XBRL International shall not be responsible for identifying patents for which a license may be required by any XBRL International specification, or for conducting legal inquiries into the legal validity or scope of those patents that are brought to its attention. XBRL International specifications are prospective and advisory only. Prospective users are responsible for protecting themselves against liability for infringement of patents. XBRL International takes no position regarding the validity or scope of any intellectual property or other rights that might be claimed to pertain to the implementation or use of the technology described in this document or the extent to which any license under such rights might or might not be available; neither does it represent that it has made any effort to identify any such rights. Members of XBRL International agree to grant certain licenses under the XBRL International Intellectual Property Policy ([www.xbrl.org/legal](http://www.xbrl.org/legal/)).

## Appendix D Acknowledgements (non-normative)

This document could not have been written without the contributions of many people including the participants in the Formula Working Group.

## Appendix E Document history (non-normative)

| Date | Author | Details |
| --- | --- | --- |
| 18 December 2007 | Geoff Shuetrim | First internal working draft created. |
| 25 April 2007 | Geoff Shuetrim | Added a date to the element-reference arcrole to support easier versioning. |
| 07 May 2007 | Geoff Shuetrim | Removed the requirement that relationships be defined in terms of the concrete arc elements that express them. This entailed also removing the element-reference arcrole declaration from the normative schema. |
| 24 July 2007 | Hugh Wallis | Edited for public working draft publication. |
| 05 November 2007 | Geoff Shuetrim | Converted the specification to XML format.  Added in the definitions and the hyperlinks to the relevant sections of the normative schema.  Reinstated the element-reference arcrole declaration, thus forcing all element-reference relationships to be expressed with generic arcs. |
| 12 November 2007 | Geoff Shuetrim | Linked all of the external terminology references back to bibliographic citations. |
| 31 January 2008 | Geoff Shuetrim | Standardised the format of the hyperlinks to the normative schema. |
| 01 February 2008 | Geoff Shuetrim | Corrected the element-reference arcrole values to reflect the values in the normative schema as suggested by [**Masatomo Goto**](#person-goto). |
| 01 April 2008 | Geoff Shuetrim | Made the URL in the schema location for the XBRL 2.1 linkbase schema in the normative schema absolute. |
| 15 December 2008 | Geoff Shuetrim | Corrected formatting problems with hyperlinks.  Updated references to the latest errata-corrected version of the XBRL 2.1 specification. |
| 21 March 2011 | Herm Fischer | Changed element-reference arcrole to allow undirected cycles (e.g., sharing of references). |

## Appendix F Errata corrections in this document

This appendix contains a list of the errata that have been incorporated into this document. This represents all those errata corrections that have been approved by the XBRL International Formula Working Group up to and including 21 March 2011. Hyperlinks to relevant e-mail threads may only be followed by those who have access to the relevant mailing lists. Access to internal XBRL mailing lists is restricted to members of XBRL International Inc.

| Number | Date | Sections | Details |
| --- | --- | --- | --- |
| 1. | 21 March 2011 | [**Section 2.1.1**](#sec-element-reference-relationship) | Changed element-reference arcrole to allow undirected cycles (e.g., sharing of references). |
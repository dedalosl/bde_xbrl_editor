---
title: "XBRL Generic Links 1.0"
source: "https://www.xbrl.org/specification/gnl/rec-2009-06-22/gnl-rec-2009-06-22.html"
author:
published: 2009-06-22
created: 2026-04-20
description:
tags:
  - "clippings"
---
Copyright ©2009 XBRL International Inc., All Rights Reserved.

---

## Status

Circulation of this Recommendation is unrestricted. This document is normative. Recipients are invited to submit comments to [specification-feedback@xbrl.org](mailto:specification-feedback@xbrl.org), and to submit notification of any relevant patent rights of which they are aware and provide supporting documentation.

## Abstract

XBRL reports make business information available in an open, structured, machine-readable form. The data points in a report can be qualified by any number of dimensions, but are always associated with a time period, a business entity (such as a corporation), and a reporting concept, such as revenue.

The reporting concepts are defined in XBRL taxonomies. Beyond defining a vocabulary for reports, taxonomies contain valuable metadata -- relationships between concepts, human-readable labels, and links to authoritative literature.

This specification aims to facilitate the creation of new kinds of metadata by providing additional concrete linking components, as well as guidance for the definition of custom linking components.

---

## 1 Introduction

XBRL taxonomies make extensive use of XLink [\[XLINK\]](#XLINK) to declare various kinds of relationships that supplement the information and constraints provided by XML Schema. The XBRL 2.1 Specification [\[XBRL 2.1\]](#XBRL) defines a number of standard XLink extended links, arcs, roles and arcroles for use with concepts, the basic building blocks of an XBRL taxonomy. These include the following elements:

- `        <link:labelLink>      ` and `        <link:labelArc>      ` for attaching labels to XBRL concepts.
- `        <link:referenceLink>      ` and `        <link:referenceArc>      ` for associating XBRL concepts with references to authoritative literature.
- `        <link:calculationLink>      ` and `        <link:calculationArc>      ` for defining arithmetic relationships between XBRL concepts.
- `        <link:presentationLink>      ` and `        <link:presentationArc>      ` for organising XBRL concepts into trees for presentation.

While these constructs are useful (indeed because they are so useful) one quickly finds oneself wishing to use the power of XLink to associate information with, and express relationships between XML elements that are not XBRL concepts.

This specification defines an extended link (`        <gen:link>      `) and an arc (`        <gen:arc>      `) which are capable of establishing relationships between arbitrary XML elements.

This specification does not in any way alter the XBRL Specification [\[XBRL 2.1\]](#XBRL). In particular, [\[XBRL 3.5\]](http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm#_3.5), which defines the general semantics for XBRL relationships (how they are defined, partitioned, prohibited, and reintroduced) and [\[XBRL 3.2\]](http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm#_3.2), which defines the rules of DTS discovery, apply to generic extended links, arcs, and resources in the same way that they apply to the standard arcs and resources.

However, this specification does specify a few additional constraints, which are clearly marked. As a starting point, all processors claiming conformance with this specification **MUST** enforce the constraints expressed in the Schema for generic links in [**Appendix A**](#sec-schemas).

Finally, in [**Appendix B**](#sec-custom), this specification provides some non-normative guidance for the creation of custom linking constructs.

## 1.1 Background

Many extensions of the XBRL Specification [\[XBRL 2.1\]](#XBRL) make use of custom link syntax. This specification provides guidance on the use of custom links and provides concrete syntax that can be leveraged by extensions of the XBRL Specification.

## 1.2 Relationship to other work

This specification depends upon the XBRL Specification [\[XBRL 2.1\]](#XBRL). In the event of any conflicts between this specification and the specifications upon which it depends, this specification does not prevail.

## 1.3 Language independence

The official language of XBRL International's own work products is English and the preferred spelling convention is UK English.

## 1.4 Terminology

This specification is consistent with the definitions of any of the terms defined in specifications that it depends on.

## 1.5 Document conventions (non-normative)

[Documentation conventions](https://www.xbrl.org/specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#sec-document-conventions) follow those set out in the XBRL Variables Specification [\[VARIABLES\]](#VARIABLES).

## 1.6 Namespaces and namespace prefixes

Namespace prefixes [\[XML NAMES\]](#XMLNAMES) will be used for elements and attributes in the form `ns:name` where `ns` is the namespace prefix and `name` is the local name. Throughout this specification, the mappings from namespace prefixes to actual namespaces is consistent with [**Table 1**](#table-namespaces).

The prefix column in [**Table 1**](#table-namespaces) is non normative. The namespace URI column is normative.

Table 1: Namespaces and namespace prefixes

| Prefix | Namespace URI |
| --- | --- |
| `                             gen                          ` | `                             http://xbrl.org/2008/generic                          ` |
| `                             xbrlgene                          ` | `                             http://xbrl.org/2008/generic/error                          ` |
| `link` | `http://www.xbrl.org/2003/linkbase` |
| `xlink` | `http://www.w3.org/1999/xlink` |
| `eg` | `http://example.com/` |

## 2 Syntax

This section defines some concrete linking components that can be used to establish relationships involving arbitrary XML elements.

## 2.1 Generic links

A generic link is an XBRL extended link that is in the substitution group of the `        <gen:link>      ` element.

The syntax for the [`        <gen:link>      `](#xml-gen-link) element is defined by the normative schema supplied with this specification.

Generic links can be used in any XBRL linkbase [\[XBRL 3.5.2\]](http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm#_3.5.2), subject to the restrictions imposed by `       @xlink:role` attributes on any `        <link:linkbaseRef>      ` elements that reference the linkbase [\[XBRL 4.3.4\]](http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm#_4.3.4).

### 2.1.1 @xlink:role attributes on generic links

The `       @xlink:role` attribute serves the same purpose on generic links as it serves on the standard extended links defined by the XBRL 2.1 specification -- it partitions relationships of the same type into disjoint networks.

The value, `V`, of the `       @xlink:role` attribute on a generic link **MUST** be an absolute URI.

Error code xbrlgene:nonAbsoluteLinkRoleURI **MUST** be thrown if `V` is not an absolute URI.

If the value `V` is not the standard extended link role (`http://www.xbrl.org/2003/role/link`), then the ancestor `        <link:linkbase>      ` element of the generic link **MUST** have a child `        <link:roleRef>      ` element with `V` as the value of its `       @roleURI` attribute.

Error code xbrlgene:missingRoleRefForLinkRole **MUST** be thrown if the ancestor `        <link:linkbase>      ` element of the generic link does not have a child `        <link:roleRef>      ` element with `V` as the value of its `       @roleURI` attribute.

The `        <link:roleType>      ` element pointed to by the `        <link:roleRef>      ` element with `       @roleURI` attribute equal to `V` **MUST** contain a `        <link:usedOn>      ` child element with a QName value that has namespace equal to the namespace of the generic link and that has local name equal to the local name of the generic link.

Error code xbrlgene:missingLinkRoleUsedOnValue **MUST** be thrown if the `        <link:roleType>      ` element pointed to by the `        <link:roleRef>      ` element with `       @roleURI` attribute equal to `V` does not contain a `        <link:usedOn>      ` child element with a QName value that has namespace equal to the namespace of the generic link and that has local name equal to the local name of the generic link.

### 2.1.2 @xlink:role attributes on resources in generic links

If a resource in a generic link has a `       @xlink:role` attribute, then the value, `V`, of that `       @xlink:role` attribute **MUST** be an absolute URI.

Error code xbrlgene:nonAbsoluteResourceRoleURI **MUST** be thrown if `V` is not an absolute URI.

The ancestor `        <link:linkbase>      ` element of the resource **MUST** have a child `        <link:roleRef>      ` element with `V` as the value of its `       @roleURI` attribute.

Error code xbrlgene:missingRoleRefForResourceRole **MUST** be thrown if the ancestor `        <link:linkbase>      ` element of the resource does not have a child `        <link:roleRef>      ` element with `V` as the value of its `       @roleURI` attribute.

The `        <link:roleType>      ` element pointed to by the `        <link:roleRef>      ` element with `       @roleURI` attribute equal to `V` **MUST** contain a `        <link:usedOn>      ` child element with a QName value with a namespace equal to the namespace of the resource and with a local name equal to the local name of the resource.

Error code xbrlgene:missingResourceRoleUsedOnValue **MUST** be thrown if the `        <link:roleType>      ` element pointed to by the `        <link:roleRef>      ` element with `       @roleURI` attribute equal to `V` does not contain a `        <link:usedOn>      ` child element with a QName value that has namespace equal to the namespace of the resource and that has local name equal to the local name of the resource.

### 2.1.3 Locators in generic links

Although the normative schema in [**Appendix A**](#sec-schemas) allows any element that is in the substitution group for the `        <link:loc>      ` element to appear within a generic link, users should be aware that DTS discovery [\[XBRL 3.2\]](http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm#_3.2) is only defined for locators expressed by the `        <link:loc>      ` element. Any schema or linkbase referenced only by locators expressed by elements other than `        <link:loc>      ` will not be included in the DTS.

The targets of `       @xlink:href` attributes on `        <link:loc>      ` elements in generic links are not constrained by this specification; locators in generic links **MAY** point to arbitrary XML elements.

## 2.2 Generic arcs

A generic arc is an XBRL arc that is in the substitution group of the `        <gen:arc>      ` element.

The syntax for the [`        <gen:arc>      `](#xml-gen-arc) element is defined by the normative schema supplied with this specification.

Generic arcs typically appear inside [generic links](#term-generic-link), but **MAY** appear elsewhere.

### 2.2.1 xlink:arcrole attributes on generic arcs

The value, `V`, of the `       @xlink:arcrole` attribute on an generic arc **MUST** be an absolute URI.

Error code xbrlgene:nonAbsoluteArcRoleURI **MUST** be thrown if `V` is not an absolute URI.

The ancestor `        <link:linkbase>      ` element of the generic arc **MUST** have a child `        <link:arcroleRef>      ` element with `V` as the value of its `       @arcroleURI` attribute.

Error code xbrlgene:missingRoleRefForArcRole **MUST** be thrown if the ancestor `        <link:linkbase>      ` element of the generic arc does not have a child `        <link:arcroleRef>      ` element with `V` as the value of its `       @arcroleURI` attribute.

The `        <link:arcroleType>      ` element pointed to by the `        <link:arcroleRef>      ` element with `       @arcroleURI` attribute equal to `V` **MUST** contain a `        <link:usedOn>      ` child element with a QName value that has namespace equal to the namespace of the generic arc and that has local name equal to the local name of the generic arc.

Error code xbrlgene:missingArcRoleUsedOnValue **MUST** be thrown if the `        <link:arcroleType>      ` element pointed to by the `        <link:arcroleRef>      ` element with `       @arcroleURI` attribute equal to `V` does not contain a `        <link:usedOn>      ` child element with a QName value that has namespace equal to the namespace of the generic arc and that has local name equal to the local name of the generic arc.

The constraints implied by the `       @cyclesAllowed` attribute on the `        <link:arcroleType>      ` element **MUST** be enforced (according to the rules of [\[XBRL 5.1.4.3\]](http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm#_5.1.4.3)) for all networks of relationships in the DTS that have arcrole `V`.

Error code xbrlgene:violatedCyclesConstraint **MUST** be thrown if the constraints implied by the `       @cyclesAllowed` attribute on the `        <link:arcroleType>      ` element are not satisfied (according to the rules of [\[XBRL 5.1.4.3\]](http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm#_5.1.4.3)) for all networks of relationships in the DTS that have arcrole `V`.

## Appendix A Normative schema

The following is the XML schema provided as part of this specification. This is normative. Non-normative versions (which should be identical to these except for appropriate comments indicating their non-normative status) are also provided as separate files for convenience of users of the specification.

NOTE: (non-normative) Following the schema maintenance policy of XBRL International, it is the intent (but is not guaranteed) that the location of non-normative versions of these schemas on the web will be as follows:

1. While any schema is the most current RECOMMENDED version and until it is superseded by any additional errata corrections a non-normative version will reside on the web in the directory `http://www.xbrl.org/2008/` - during the drafting process for this specification this directory should contain a copy of the most recent published version of the schema at [http://www.xbrl.org/2008/generic-link.xsd](http://www.xbrl.org/2008/generic-link.xsd).
2. A non-normative version of each schema as corrected by any update to the RECOMMENDATION will be archived in perpetuity on the web in a directory that will contain a unique identification indicating the date of the update.

For convenience, the normative schema contains the following link role declarations:

- [`http://www.xbrl.org/2008/role/link`](#standard-link-role)
<schema xmlns:gen="http://xbrl.org/2008/generic" xmlns:xl="http://www.xbrl.org/2003/XLink" xmlns="http://www.w3.org/2001/XMLSchema" xmlns:link="http://www.xbrl.org/2003/linkbase" targetNamespace="http://xbrl.org/2008/generic" elementFormDefault="qualified"><link:usedOn>

gen:link

</link:usedOn>

<import namespace="http://www.xbrl.org/2003/XLink" schemaLocation="http://www.xbrl.org/2003/xl-2003-12-31.xsd"/>

<import namespace="http://www.xbrl.org/2003/linkbase" schemaLocation="http://www.xbrl.org/2003/xbrl-linkbase-2003-12-31.xsd"/>

<element id="xml-gen-arc" name="arc" substitutionGroup="xl:arc" type="gen:genericArcType"/>

<extension base="xl:arcType">

<attribute name="id" type="ID"/>

</extension><restriction base="xl:extendedType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="xl:documentation"/>

<element ref="link:loc"/>

<element ref="gen:arc"/>

<element ref="xl:resource"/>

</choice>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction><extension base="gen:linkType">

<anyAttribute namespace="##other"/>

</extension>

<element id="xml-gen-link" name="link" substitutionGroup="xl:extended" type="gen:linkTypeWithOpenAttrs"/>

</schema>

## Appendix B Defining Custom Linking Components (non-normative)

## B.1 Custom extended links

A custom extended link is an extended link that is in the substitution group for the abstract `        <xl:extended>      ` element and that is not one of the concrete extended link elements defined in the XBRL Specification [\[XBRL 2.1\]](#XBRL).

It should not generally be necessary to define custom extended links. A custom extended link should only be defined when tight control over the content model is desired.

For example, you may want to define a custom extended link whose sole purpose is to force discovery of a document:

Example 1: XML Schema content model for an extended link that can force document discovery

<xsd:restriction base="xl:extendedType"><xsd:choice maxOccurs="unbounded">

<xsd:element ref="xl:documentation"/>

<xsd:element ref="link:loc"/>

</xsd:choice>

<xsd:anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</xsd:restriction>

XBRL forbids the use of `        <link:linkbaseRef>      ` element within linkbases, but a locator within an element like that in [**Example 1**](#example-extended-link-forcing-document-discovery) achieves the same effect. Here it is not appropriate to include resources and arcs; the content model only allows locator, and optional documentation elements.

## B.2 Custom arcs

A custom arc is an element that is in the substitution group for the abstract `        <xl:arc>      ` element and that is not one of the concrete arcs defined in the XBRL Specification [\[XBRL 2.1\]](#XBRL).

While custom extended links are rarely required, custom arcs are useful whenever you want to define a type of relationship that has required attributes in addition to those defined in the XLink namespace `http://www.w3.org/1999/xlink`. Using a custom arc, the occurrence constraints for those attributes can be specified using XML Schema [\[SCHEMA-1\]](http://www.w3.org/TR/xmlschema-1/).

Note: To be usable within [generic links](#term-generic-link), custom arcs must be in the substitution group for the `        <gen:arc>      ` element.

## B.3 Custom resources

A custom resource is an element that is in the substitution group for the abstract `        <xl:resource>      ` element and that is not one of the concrete resources defined in the XBRL Specification [\[XBRL 2.1\]](#XBRL).

It will also be quite common to define custom resources, sometimes with complex content models, possibly allowing mixed content. An obvious example would be a generic XHTML resource, akin to the `        <link:label>      ` element, but used in conjunction with generic links and generic arcs so that semantics are determined by the arcrole alone, rather than spread across the resource (`        <link:label>      `, the arcrole - `http://www.xbrl.org/2003/arcrole/concept-label`, the arc - `        <link:labelArc>      `, and the extended link - `        <link:labelLink>      `).

On the other hand, if control over resource roles is desired (to distinguish between a terse and a verbose label, for example), then a concrete, specialised element (possibly derived from a generic XHTML resource) may be appropriate as shown in [**Example 2**](#example-audit-link).

Note that [**Example 2**](#example-audit-link) also includes a custom link element but only requires the `        <gen:arc>      ` element defined in this specification.

Example 2: A custom link capturing an audit opinion that is tied to specific facts in an XBRL instance

Custom audit opinion linkbase relating the audit opinion to three of the facts in the audited XBRL instance. Naturally, the custom link could be expanded to relate different opinion resources to different sets of facts in the XBRL instance that has been audited.

<link:linkbase xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:o="http://example.com/opinion/2008" xmlns:gen="http://xbrl.org/2008/generic" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:link="http://www.xbrl.org/2003/linkbase" xmlns="http://www.w3.org/1999/xhtml" xsi:schemaLocation="http://example.com/opinion.xsd">

<link:arcroleRef xlink:type="simple" xlink:href="http://www.example.com/opinion.xsd#o2f" arcroleURI="http://example.com/2008/role/o2f"/>

<o:opinionLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/link"><o:opinion xlink:type="resource" xlink:label="opinion" xlink:role="http://www.xbrl.org/2003/role/link" xml:lang="en"><b>

Report of Independent Registered Public Accounting Firm

</b><p>

To the Board of Directors and Shareowners

</p><p>

of ACME Corporation:

</p><p>

We have examined the accompanying XBRL-Related Documents of ACME Corporation (the "Corporation"), which reflect the data presented in the Corporation’s Quarterly Report on Form 10-Q for the quarter and six-months ended December 31, 2007. The Corporation’s management is responsible for the XBRL-Related Documents. Our responsibility is to express an opinion based on our examination.

</p><p>

We have also reviewed, in accordance with the standards of the Public Company Accounting Oversight Board (United States), the financial statements of the Corporation as of December 31, 2007, and for the three and six-month periods then ended, the objective of which was the expression of limited assurance on such financial statements, and issued our report thereon dated April 1, 2007. A review of financial statements is substantially less in scope than an audit conducted in accordance with the standards of the Public Company Accounting Oversight Board (United States), the objective of which is the expression of an opinion regarding the financial statements taken as a whole. Accordingly, we do not express such an opinion.

</p><p>

In addition, we have previously audited, in accordance with the standards of the Public Company Accounting Oversight Board (United States), the consolidated balance sheet as of June 30, 2007, and the related consolidated statements of operations, of cash flows and of changes in shareowners’ equity for the year then ended, management’s assessment of the effectiveness of the Corporation’s internal control over financial reporting as of June 30, 2007 and the effectiveness of the Corporation’s internal control over financial reporting as of June 30, 2007, and in our report dated August 31, 2007, except for Notes 1, 10 and 16 for which the date is May 6, 2005, we expressed unqualified opinions thereon. We were not engaged to and did not conduct a review of the information contained in Part I, Items 2, 3 and 4 and Part II, Items 1, 2 and 6 of the Corporation’s Quarterly Report on Form 10-Q for the quarter and nine-months ended December 31, 2007, the objective of which would have been the expression of limited assurance on such aforementioned information. Accordingly, we do not express an opinion or any other assurance on such aforementioned information.

</p><p>

Our examination of the XBRL-Related Documents was conducted in accordance with the standards of the Public Company Accounting Oversight Board (United States) and, accordingly, included examining, on a test basis, evidence supporting the XBRL-Related Documents. Our examination also included evaluating the XBRL-Related Documents for conformity with the applicable XBRL taxonomies and specifications and the content and format requirements of the Securities and Exchange Commission. We believe that our examination provides a reasonable basis for our opinion.

</p><p>

In our opinion, the XBRL-Related Documents of the Corporation referred to above accurately reflect, in all material respects, the data presented in the Corporation’s Quarterly Report on Form 10-Q for the quarter and six months ended December 31, 2007, in conformity with the US GAAP—Commercial and Industrial Taxonomy, US Financial Reporting—Management’s Discussion and Analysis Taxonomy, US Financial Reporting—Accountant’s Report Taxonomy, US Financial Reporting—SEC Certifications Taxonomy, extensions specific to ACME Corporation, and the XBRL Specifications (Version 2.1).

</p></o:opinion>

<gen:arc xlink:type="arc" xlink:arcrole="http://example.com/2008/role/o2f" xlink:from="opinion" xlink:to="fact" order="1.0"/>

<link:loc xlink:type="locator" xlink:href="http://example.com/xbrl/instance.xml#assets" xlink:label="fact"/>

<link:loc xlink:type="locator" xlink:href="http://example.com/xbrl/instance.xml#liabilities" xlink:label="fact"/>

<link:loc xlink:type="locator" xlink:href="http://example.com/xbrl/instance.xml#equity" xlink:label="fact"/>

</o:opinionLink></link:linkbase>

Supporting XML schema (assumed in the audit link to have URL: `http://www.example.com/opinion.xsd`).

<xs:schema xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:gen="http://xbrl.org/2008/generic" xmlns:o="http://xbrl.us/opinion/2008" xmlns:xl="http://www.xbrl.org/2003/XLink" xmlns:link="http://www.xbrl.org/2003/linkbase" targetNamespace="http://example.com/opinion/2008" attributeFormDefault="unqualified" elementFormDefault="qualified"><link:arcroleType arcroleURI="http://example.com/2008/role/o2f" cyclesAllowed="any" id="o2f"><link:definition>

Arc from an opinion to a fact.

</link:definition><link:usedOn>

gen:arc

</link:usedOn></link:arcroleType>

<xs:import namespace="http://www.w3.org/1999/xlink" schemaLocation="http://www.xbrl.org/2003/xlink-2003-12-31.xsd"/>

<xs:import namespace="http://www.xbrl.org/2003/XLink" schemaLocation="http://www.xbrl.org/2003/xl-2003-12-31.xsd"/>

<xs:import namespace="http://www.xbrl.org/2003/linkbase" schemaLocation="http://www.xbrl.org/2003/xbrl-linkbase-2003-12-31.xsd"/>

<xs:import namespace="http://xbrl.org/2008/generic" schemaLocation="http://www.xbrl.org/2008/generic-link.xsd"/>

<xs:restriction base="xl:extendedType"><xs:choice maxOccurs="unbounded" minOccurs="0">

<xs:element ref="xl:documentation"/>

<xs:element ref="link:loc"/>

<xs:element ref="gen:arc"/>

<xs:element ref="o:opinion"/>

</xs:choice>

<xs:attribute fixed="extended" use="required" ref="xlink:type"/>

<xs:attribute use="required" ref="xlink:role"/>

<xs:attribute use="optional" ref="xlink:title"/>

<xs:attribute name="id" use="optional" type="xs:ID"/>

<xs:anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</xs:restriction><xs:extension base="xl:resourceType"><xs:sequence>

<xs:any maxOccurs="unbounded" minOccurs="0" namespace="http://www.w3.org/1999/xhtml" processContents="skip"/>

</xs:sequence>

<xs:anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</xs:extension></xs:schema>

The custom link in [**Example 2**](#example-audit-link) defines relationships from a custom resource to specific facts in an XBRL instance. However, the referenced XBRL instance is not in any DTS that includes this custom link, and should not be processed \*as\* an XBRL instance (unless it was also the starting point for processing). Any XBRL validation checks, beyond those required by XML Schema constraints, should not apply to such a non-entry point XBRL instance, and DTS discovery should not proceed further from it.

## Appendix C References

VARIABLES

XBRL International Inc.. "XBRL Variables 1.0"  
Phillip Engel, Herm Fischer, Victor Morilla, Jim Richards, Geoff Shuetrim, David vun Kannon, and Hugh Wallis.  
(See [../../variables/REC-2009-06-22/variables-REC-2009-06-22.html](https://www.xbrl.org/specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html))

XBRL 2.1

XBRL International Inc.. "Extensible Business Reporting Language (XBRL) 2.1"  
Phillip Engel, Walter Hamscher, Geoff Shuetrim, David vun Kannon, and Hugh Wallis.  
(See [http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm](http://www.xbrl.org/Specification/XBRL-RECOMMENDATION-2003-12-31+Corrected-Errata-2008-07-02.htm))

XLINK

W3C (World Wide Web Consortium). "XML Linking Language (XLink) Version 1.0"  
Steve DeRose, Eve Maler, and David Orchard.  
(See [http://www.w3.org/TR/xlink/](http://www.w3.org/TR/xlink/))

XML NAMES

W3C (World Wide Web Consortium). "Namespaces in XML 1.0 (Second Edition)"  
Tim Bray, Dave Hollander, Andrew Layman, and Richard Tobin.  
(See [http://www.w3.org/TR/REC-xml-names/](http://www.w3.org/TR/REC-xml-names/))

XML SCHEMA STRUCTURES

W3C (World Wide Web Consortium). "XML Schema Part 1: Structures Second Edition"  
Henry S. Thompson, David Beech, Murray Maloney, and Noah Mendelsohn.  
(See [http://www.w3.org/TR/xmlschema-1/](http://www.w3.org/TR/xmlschema-1/))

## Appendix D Intellectual property status (non-normative)

This document and translations of it may be copied and furnished to others, and derivative works that comment on or otherwise explain it or assist in its implementation may be prepared, copied, published and distributed, in whole or in part, without restriction of any kind, provided that the above copyright notice and this paragraph are included on all such copies and derivative works. However, this document itself may not be modified in any way, such as by removing the copyright notice or references to XBRL International or XBRL organizations, except as required to translate it into languages other than English. Members of XBRL International agree to grant certain licenses under the XBRL International Intellectual Property Policy ([www.xbrl.org/legal](http://www.xbrl.org/legal/)).

This document and the information contained herein is provided on an "AS IS" basis and XBRL INTERNATIONAL DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTY THAT THE USE OF THE INFORMATION HEREIN WILL NOT INFRINGE ANY RIGHTS OR ANY IMPLIED WARRANTIES OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.

The attention of users of this document is directed to the possibility that compliance with or adoption of XBRL International specifications may require use of an invention covered by patent rights. XBRL International shall not be responsible for identifying patents for which a license may be required by any XBRL International specification, or for conducting legal inquiries into the legal validity or scope of those patents that are brought to its attention. XBRL International specifications are prospective and advisory only. Prospective users are responsible for protecting themselves against liability for infringement of patents. XBRL International takes no position regarding the validity or scope of any intellectual property or other rights that might be claimed to pertain to the implementation or use of the technology described in this document or the extent to which any license under such rights might or might not be available; neither does it represent that it has made any effort to identify any such rights. Members of XBRL International agree to grant certain licenses under the XBRL International Intellectual Property Policy ([www.xbrl.org/legal](http://www.xbrl.org/legal)).

## Appendix E Acknowledgements (non-normative)

The editors thank the members of the various XBRL working groups for supporting the creation of this document, and for providing valuable feedback on internal drafts.

## Appendix F Document history (non-normative)

| Date | Author | Details |
| --- | --- | --- |
| 26 June 2006 | Ignacio Hernandez-Ros | Created initial draft. |
| 08 November 2006 | Geoff Shuetrim | Narrowed scope to the specific concrete syntax constructs to be defined in the specification. Inserted updated versions of the syntax definitions provided by [**Mark Goodhand**](#person-mrg). |
| 24 July 2007 | Mark Goodhand | Released as a public working draft. |
| 01 November 2007 | Mark Goodhand | The schema now allows only arcs substitutable for generic arcs to appear in generic links. |
| 01 November 2007 | Mark Goodhand | The date in the namespace has changed from 2007 to 2008. |
| 08 February 2008 | Geoff Shuetrim | Editorial changes in preparation for publication as a second public working draft.  Added comments requesting definitions of custom extended links, custom arcs and custom resources.  Added new constraints requiring role and arcrole type declarations for custom extended link role values and and custom arc role values. |
| 10 February 2008 | Geoff Shuetrim | Changed the ID attributes on the generic link and generic arc elements as suggested by [**Mark Goodhand**](#person-mrg).  Simplified the wording of the constraints relating to roles and arcroles based on feedback from [**Mark Goodhand**](#person-mrg).  Added new constraints on the roles of resources in generic links. |
| 12 February 2008 | Geoff Shuetrim | Added definitions of custom extended links, custom arcs and custom resources. |
| 13 February 2008 | Geoff Shuetrim | Changed definitions of generic links and generic arcs to also include elements in the substitution groups for the concrete elements defined in the normative schema for this specification. This enables extension specifications to define new arcs, for example, in the substitution group for the `        <gen:arc>      ` element and to inherit all of the constraints imposed in this specification without needing to restate them.  Fixed the IDs used for the references to specific sections of the XBRL Specification [\[XBRL 2.1\]](#XBRL). |
| 18 March 2008 | Geoff Shuetrim | Fixed XML Schema validation problems for the example in Appendix B, as identified by [**Walter Hamscher**](#person-walter). |
| 20 March 2008 | Geoff Shuetrim | Fixed broken hyperlinks. |
| 01 April 2008 | Geoff Shuetrim | Relaxed the requirments for `        <link:usedOn>      ` element content for generic links and generic arcs to allow for generic links and generic arcs that are in the substitution group for the `        <gen:link>      ` and `        <gen:arc>      ` elements respectively. This correction was suggested by [**Cliff Binstock**](#person-cliff). |
| 02 April 2008 | Geoff Shuetrim | Added the custom audit link example that was provided by [**Walter Hamscher**](#person-walter). |
| 09 April 2008 | Geoff Shuetrim | Added material to Appendix B to explain the relationship between custom links, arcs and resources and the `        <xl:*>      ` elements defined in the schemas supporting the XBRL Specification [\[XBRL 2.1\]](#XBRL) as suggested by [**Ignacio Hernandez-Ros**](#person-ihr). This also entailed adding the section on custom locators and flagging that no locators other than the `        <link:loc>      ` element participate in DTS discovery. |
| 16 April 2008 | Geoff Shuetrim | Removed the paragraphs explaining the `        <xl:*>      ` elements in the XBRL 2.1 Specification given the lack of agreement in the specification WG about exactly what should be stated. Agreement was reached on the Base Specification WG mailing list that if additional explanation or clarification was required in regard to the `        <xl:*>      ` elements then that should be provided through an errata to the XBRL 2.1 Specification itself. This made the new section on custom locators redundant.  Error codes have been defined for all constraints imposed by this specification as suggested by [**Cliff Binstock**](#person-cliff). |
| 04 November 2008 | Geoff Shuetrim | Renamed the non-normative schema document. |
| 15 December 2008 | Geoff Shuetrim | Updated references to the latest errata-corrected version of the XBRL 2.1 specification. |

## Appendix G Errata corrections in this document

This appendix contains a list of the errata that have been incorporated into this document. This represents all those errata corrections that have been approved by the XBRL International Base Specification and Maintenance Working Group up to and including 22 June 2009. Hyperlinks to relevant e-mail threads may only be followed by those who have access to the relevant mailing lists. Access to internal XBRL mailing lists is restricted to members of XBRL International Inc.

No errata have been incorporated into this document.
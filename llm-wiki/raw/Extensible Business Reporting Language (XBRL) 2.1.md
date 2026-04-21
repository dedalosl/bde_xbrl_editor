---
title: "Extensible Business Reporting Language (XBRL) 2.1"
source: "https://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html"
author:
published: 2003-12-31
created: 2026-04-20
description:
tags:
  - "clippings"
---
Copyright © 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2011, 2013 XBRL International Inc., All Rights Reserved.

This version:

[<http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html>](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html)

Editors:

Phillip Engel, XBRL US (formerly of KPMG LLP) [<phillip.engel@xbrl.us>](mailto:phillip.engel@xbrl.us)

Walter Hamscher, US SEC (formerly of Standard Advantage) [<HamscherW@sec.gov>](mailto:HamscherW@sec.gov)

Geoffrey Shuetrim, Galexy Pty. (formerly of KPMG LLP) [<geoff@galexy.net>](mailto:geoff@galexy.net)

David vun Kannon, Deloitte (formerly of PricewaterhouseCoopers and previously KPMG LLP) [<dvunkannon@deloitte.com>](mailto:dvunkannon@deloitte.com)

Hugh Wallis, IBM (formerly of XBRL International Inc. and previously Hyperion Solutions Corporation) [<hugh.wallis@ca.ibm.com>](mailto:hugh.wallis@ca.ibm.com)

Contributors:

Herm Fischer, Mark V Systems (formerly of UBmatrix) [<fischer@markv.com>](mailto:fischer@markv.com)

Luther Hampton, IBM (fomerly of e-Numerate) [<luther.hampton@ibm.com>](mailto:luther.hampton@ibm.com)

Charles Hoffman, Formerly of UBmatrix [<CharlesHoffman@olywa.net>](mailto:CharlesHoffman@olywa.net)

Louis Matherne, FASB (formerly of AICPA) [<lmatherne@fasb.org>](mailto:lmatherne@fasb.org)

Campbell Pryde, XBRL US (formerly of Morgan Stanley and previously of KPMG LLP) [<campbell.pryde@xbrl.us>](mailto:campbell.pryde@xbrl.us)

Yufei Wang, KPMG [<yufeiwang1@kpmg.com>](mailto:yufeiwang1@kpmg.com)

Mark Goodhand, CoreFiling [<mrg@corefiling.com>](mailto:mrg@corefiling.com)

---

## Status

Circulation of this Recommendation is unrestricted. This document is normative. Recipients are invited to submit comments to [spec-feedback@xbrl.org](mailto:spec-feedback@xbrl.org), and to submit notification of any relevant patent rights of which they are aware and provide supporting documentation.

## Abstract

XBRL is the specification for the eXtensible Business Reporting Language. XBRL allows software vendors, programmers, intermediaries in the preparation and distribution process and end users who adopt it as a specification to enhance the creation, exchange, and comparison of business reporting information. Business reporting includes, but is not limited to, financial statements, financial information, non-financial information, general ledger transactions and regulatory filings, such as annual and quarterly reports.

This document defines XML elements and attributes that can be used to express information used in the creation, exchange, and comparison tasks of business reporting. XBRL consists of a core language of XML elements and attributes used in XBRL instances as well as a language used to define new elements and taxonomies of elements referred to in XBRL instances, and to express constraints among the contents of elements in those XBRL instances.

---

## 1 Introduction

XBRL is the specification for the eXtensible Business Reporting Language. XBRL allows software vendors, programmers and end users to enhance the creation, exchange, and comparison of business reporting information. Business reporting includes, but is not limited to, financial statements, financial information, non-financial information and regulatory filings such as annual and quarterly financial statements.

This document defines XML elements and attributes that can be used to express information used in the creation, exchange and comparison tasks of business reporting. XBRL consists of a core language of XML elements and attributes used in document instances. [Abstract Elements](#abstract-element) in this core language are replaced by [Concrete Elements](#concrete-element) in [XBRL Instances](#XBRL-instance). These abstract elements are defined in taxonomies. XBRL consists of a language used to define new elements and taxonomies of elements referred to in document instances and the relationships between taxonomy elements.

All parts of this document not explicitly identified as non-normative are normative. In the event of any conflict or apparent conflict between the English language text of this document and/or schema fragments included in the main body of this document and the normative schemas contained herein ([**Appendix A**](#A)), the more restrictive interpretation that is possible from the information provided by the English language text and that provided by the normative schemas (Appendix A) **SHALL** prevail. The schema fragments incorporated into the body of the text are non-normative and are generally indicated as such by means of shading such as that defined in [**Section 1.1**](#_1.1). It is important to note that the normative schemas (Appendix A) do not necessarily always provide the most restrictive interpretation, either because it is not possible to express certain limitations using the syntax of XML Schema [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) [\[XML Schema Datatypes\]](#XMLSCHEMA-DATATYPES) or because, as at the time of publication of this specification, some commonly available commercial implementations of XML Schema do not implement otherwise necessary features correctly or fully. For example, the schema specification of the [Abstract Element](#abstract-element) tuple (Appendix A) does not restrict its content model as much as the English language text in [**Section 4.9**](#_4.9). The text of section 4.9 **SHALL** prevail in this case. Another, converse, example is the order of the sub-elements of the `  <context>  ` element. In this case the schema (Appendix A) dictates a specific ordering of these sub-elements yet this is not explicitly articulated in the text of [**Section 4.7**](#_4.7). The schema (Appendix A) provides the more restrictive interpretation and thus it **SHALL** prevail over any alternative possible interpretation of the English language text in this case.

The schemas and other documents published separately and contemporaneously with the specification are non-normative and are provided for the convenience of users of this specification.

## 1.1 Documentation conventions

The following highlighting is used to present non-normative technical material in this document:

The following highlighting is used for non-normative commentary in this document:

Non-normative editorial comments are denoted by indentation and the prefix " **NOTE:**":

**NOTE**: This is a non-normative editorial comment.

*Italics* are used for rhetorical emphasis only and do not convey any special normative meaning.

## 1.2 Purpose

The XBRL specification is intended to benefit four categories of users: 1) business information preparers, 2) intermediaries in the preparation and distribution process, 3) users of this information and 4) the vendors who supply software and services to one or more of these three types of user. The overall intention is to balance the needs of these groups creating a standard that benefits to all four groups.

The needs of end users of business information have generally taken precedence over other needs when it has been necessary to make specification design decisions that might benefit one community at the expense of another.

A major goal of XBRL is to improve the business report product. It facilitates current practice; it does not change or set new accounting or other business domain standards. However, XBRL should facilitate changes in reporting over the long term.

XBRL provides users with a standard format in which to *prepare* reports that can subsequently be presented in a variety of ways. XBRL provides users with a standard format in which information can be *exchanged* between different software applications. XBRL permits the automated, efficient and reliable *extraction* of information by software applications. XBRL facilitates the automated *comparison* of financial and other business information, accounting policies, notes to financial statements between companies, and other items about which users may wish make comparisons that today are performed manually.

XBRL facilitates "drill down" to detailed information, authoritative literature, audit and accounting working papers. XBRL includes specifications for as much information about the reporting entity as may be relevant and useful to the process of financial and business reporting and the interpretation of the information.

XBRL supports international accounting and other standards as well as languages other than the various dialects of English.

XBRL is extensible by any adopter to increase its breadth of applicability, and its design encourages reuse via incremental extensions. For example, XBRL specifies the format of information that would reasonably be expected in an electronic format for securities filings by public entities. XBRL facilitates business reporting in general, and is not limited to financial and accounting reporting.

XBRL focuses on the genuine information needs of the user and adheres to the spirit of reporting standards that avoid the use of bold, italics, and other stylistic techniques that may distract from a true and fair presentation of results. Therefore, there is no functional requirement that XBRL documents support any particular text formatting conventions.

The purpose of [XBRL Instances](#XBRL-instance) is the transmission of a set of facts. There is no constraint on how much or how little they contain. A single fact can form the entire content of a valid XBRL instance, for example, when the information being conveyed is limited to what "Cost of Goods Sold" was last quarter or an XBRL instance can be a database dump, containing huge numbers of facts. It can also be anything in between. This provides a great deal of flexibility and is meant specifically to achieve the goals of allowing XBRL to be reused within other specifications and for application software needing to extract data from otherwise arbitrarily formatted documents. It is expected that, for most uses of XBRL, many XML XBRL instances will be created that consist almost exclusively of facts.

## 1.3 Relationship to other work

XBRL uses several World Wide Web Consortium (W3C) recommendations, XML 1.0 [\[XML\]](#XML), Namespaces in XML [\[XML Names\]](#XMLNAMES), and refers directly to XML Linking [\[XLINK\]](#XLINK) and others listed in [**Section 6**](#_6) References. It also relies extensively on the XML Schema [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) and [\[XML Schema Datatypes\]](#XMLSCHEMA-DATATYPES) recommendation.

Discussions have taken place with other bodies issuing XML specifications in the financial arena, including OAG (Open Applications Group), OMG (Object Management Group), FpML (Financial Products Markup Language), finXML (Financial XML), OFX/IFX (Open Financial Exchange) and ebXML (e-Business XML). The scope of XBRL does not include transaction protocols. It includes financial reporting and contemplates extensive detail in the representation and use of accounting conventions, which distinguishes it from these other efforts.

## 1.4 Terminology (non-normative except where otherwise noted)

The terminology used in XBRL frequently overlaps with terminology from other fields, and the following list is provided to reduce the possibility of ambiguity and confusion (see also the references in [**Section 6**](#_6) below). These definitions are non-normative except where marked otherwise by means of the word **(NORMATIVE)** appearing in the "Term" column.

| Term | Definition |
| --- | --- |
| Abstract Element | An element for which the attribute ` @abstract` in its XML schema declaration has the value " `true` " and which, therefore, cannot be used in an XML instance. |
| Alias Concept | The [Concept](#concept) at the "to" end of a definition arc with arc role `http://www.xbrl.org/2003/arcrole/essence-alias`. Alias and [Essence Concepts](#Essence-Concept) are definitionally equivalent in the sense that valid values for an alias concept are always valid values for essence concepts to which they are related by an essence-alias relationship. |
| Alias Item | An item in an instance whose element is an alias concept. |
| Arc | Arcs relate [Concepts](#concept) to each other by associating their locators. Arcs also associate concepts with resources by connecting the concept locators to the resources themselves. Arcs are also used to connect fact locators to footnote resources in footnote extended links. Arcs have a set of attributes that document the nature of the relationships expressed in extended links. Importantly all arcs have an ` @xlink:arcrole` attribute that determines the semantics of the relationship they describe. |
| C-Equal | Context-equal: Items or sets or sequences of items having the same item type in s-equal contexts. For a formal definition, see [**Section 4.10**](#_4.10) below. |
| Ancestor, Child, Descendant, Grandparent, Parent, Sibling, Uncle **(NORMATIVE)** | Relationships among elements in an XBRL instance: using the terminology of [\[XPath 1.0\]](#XPATH), for any element **E**, another element **F** is its: - ancestor if and only if **F** appears on the ancestor axis of **E** - child if and only if **F** appears on the child axis of **E** - descendant if and only if **F** appears on the descendant axis of **E** - grandparent if and only if **F** is the parent of the parent of **E** - parent if and only if **F** appears on the parent axis of **E** - sibling if and only if **F** appears on the child axis of the parent of **E** and is not **E** itself - uncle if and only if **F** is a sibling of the parent of **E** |
| Concept | Concepts are defined in two equivalent ways. In a syntactic sense, a concept is an XML Schema element definition, defining the element to be in the `item` element substitution group or in the `tuple` element substitution group. At a semantic level, a concept is a definition of a kind of fact that can be reported about the activities or nature of a business activity. |
| Concrete Element | An element for which the attribute ` @abstract` in its XML schema declaration has the value " `false` " and which, therefore, may appear in an XML instance. |
| Context | Contexts are elements that occur as children of the root element in XBRL instances. They document the entity, the period and the scenario that collectively give the appropriate context for understanding the values of items. |
| Custom Arc Element | An element derived from `xl:arc` that is *not* defined in this specification, Specifically, *not* one of: `link:presentationArc`, `link:calculationArc`, `link:labelArc`, `link:referenceArc`, or `link:definitionArc`. |
| Custom Extended Link Element | An element derived from `xl:link` that is *not* defined in this specification. Specifically, *not* one of: `link:presentationLink`, `link:calculationLink`, `link:labelLink`, `link:referenceLink`, or `link:definitionLink`. |
| Custom Resource Element | A element derived from `xl:resource` that is *not* defined in this specification, Specifically, *not* one of: one of `link:label`, `link:reference`, or `link:footnote`. |
| Discoverable Taxonomy Set (DTS) | A DTS is a collection of taxonomy schemas and linkbases. The bounds of a DTS are such that the DTS includes all taxonomy schemas and linkbases that can be discovered by following links or references in the taxonomy schemas and linkbases included in the DTS. At least one taxonomy schema in a DTS must import the *xbrl-instance-2003-12-31.xsd* schema. See [**Section 3**](#_3) for details on the discovery process. |
| Duplicate Items | Two items of the same concept in the same context under the same parent. For a formal definition see duplicate item in [**Section 4.10**](#_4.10). |
| Duplicate Tuples | Two occurrences of a tuple with all their descendants having the same content; more precisely: tuples that are p-equal, all of whose tuple children have a duplicate (except for being p-equal) in the other tuple, and all of whose item children have a duplicate (except for being p-equal) in the other tuple. For a formal definition see duplicate tuple in [**Section 4.10**](#_4.10). |
| Element | An XML element defined using XML Schema. |
| Entity | A business entity, the subject of XBRL items. Where the [\[XML\]](#XML) / [\[SGML\]](#SGML) concept of syntactic "entity" is meant, this will be pointed out. |
| Essence Concept | The [Concept](#concept) at the "from" end of a definition arc with arc role `http://www.xbrl.org/2003/arcrole/essence-alias`. Alias and essence concepts are definitionally equivalent in the sense that valid values for an alias concept are always valid values for essence concepts to which they are related by an essence-alias relationship. |
| Essence Item | An item in an instance whose element is an essence concept. |
| Extended Link | An extended link is an element identified as an extended link using the syntax defined in the XML Linking Language [\[XLINK\]](#XLINK). Extended links represent a set of relationships between information that they contain and information contained in third party documents. See [**Section 3.5.2.4**](#_3.5.2.4) for more details. |
| Fact | Facts can be simple, in which case their values must be expressed as simple content (except in the case of simple facts whose values are expressed as a ratio), and facts can be compound, in which case their value is made up from other simple and/or compound facts. Simple facts are expressed using items (and are referred to as items in this specification) and compound facts are expressed using tuples (and are referred to as tuples in this specification). |
| Instance Namespace | The namespace used for XBRL 2.1 instances, `http://www.xbrl.org/2003/instance` |
| Item | An item is an element in the substitution group for the XBRL item element. It contains the value of the simple fact and a reference to the context (and unit for numeric items) needed to correctly interpret that fact. When items occur as children of a tuple, they must also be interpreted in light of the other items and tuples that are children of the same tuple. There are numeric items and non-numeric items, with numeric items being required to document their measurement accuracy and units of measurement. |
| Least Common Ancestor | In an instance, the element that is an ancestor of two elements and has no child that also appears on the ancestor axis [\[XPath 1.0\]](#XPATH) of those same two elements. |
| Linkbase | A linkbase is a collection of XML Linking Language [\[XLINK\]](#XLINK) extended links that document the semantics of [Concepts](#concept) in a taxonomy. |
| Linkbase Namespace | The namespace of XBRL 2.1 linkbases, `http://www.xbrl.org/2003/linkbase` |
| Locator | Locators supply an XPointer [\[XPOINTER\]](#XPOINTER) reference to the taxonomy schema element definitions that uniquely identify each [Concept](#concept). They provide an anchor for extended link arcs. See [**Section 3.5.3.7**](#_3.5.3.7) for more details. |
| MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, MAY, OPTIONAL **(NORMATIVE)** | The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT, RECOMMENDED, MAY, and OPTIONAL, in this specification, are to be interpreted as described in [\[IETF RFC 2119\]](#RFC2119). |
| Non-Numeric Item | An item that is not a numeric item as defined below. Dates, in particular, are not numeric. |
| Numeric Item | An item whose simple content is derived by restriction from the XML Schema primitive types `decimal`, `float` or `double`, or complex content derived by restriction from the XBRL defined type `fractionItemType` (see [**Section 5.1.1.3**](#_5.1.1.3) for details on item types). |
| Period | An instant or duration of time. In business reporting, financial numbers and other facts are reported "as of" an instant or for a period of certain duration. Facts about instants and durations are both common. |
| P-Equal | Parent-equal: instance items or tuples having the same parent. For a formal definition, see [**Section 4.10**](#_4.10) below. |
| Resource | Resources are XML fragments, contained within extended links that provide additional information about [Concepts](#concept) or items. See [**Section 3.5.3.8**](#_3.5.3.8) for details. |
| Root of an XBRL Instance | The root of an XBRL instance is the `  <xbrl>  ` element. In principle, it is possible to embed an XBRL instance in *any* XML document. In this case, the `  <xbrl>  ` element is the container for the XBRL instance. |
| S-Equal | Structure-equal: XML nodes that are either equal in the XML value space, or whose XBRL-relevant sub-elements and attributes are s-equal. For a formal definition, see [**Section 4.10**](#_4.10) below. |
| Standard Arc Element | An element derived from `xl:arc` that is defined in this specification, Specifically, one of: `link:presentationArc`, `link:calculationArc`, `link:labelArc`, `link:referenceArc`, or `link:definitionArc`. |
| Standard Extended Link Element | An element derived from `xl:link` that is defined in this specification. Specifically, one of: `link:presentationLink`, `link:calculationLink`, `link:labelLink`, `link:referenceLink`, or `link:definitionLink`. |
| Standard Resource Element | A element derived from `xl:resource` that is defined in this specification, Specifically, one of: `link:label`, `link:reference`, or `link:footnote`. |
| Taxonomy | A taxonomy is an XML schema and the set of XBRL linkbases that it references using `  <linkbaseRef>  ` elements and the linkbases that are nested within it. |
| Taxonomy Schema | A taxonomy schema is an XML Schema [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES). A large part of many taxonomy schemas is given over to the definition of the syntax for the [Concepts](#concept) in that taxonomy. [**Section 3.1**](#_3.1), [**Section 5**](#_5) and [**Section 5.1**](#_5.1) address this in more detail. |
| Tuple | A tuple is an element in the substitution group for the XBRL tuple element. Tuples are used to bind together the parts of a compound fact. Those constituent parts are themselves, facts but they must be interpreted in light of each-other. For example, the name, age and compensation of a director of a company need to be grouped together to be correctly understood. |
| Unit | Units are XML fragments that occur as children of the root element in XBRL instances. They document the unit of measure for numeric items. Each `  <unit>  ` element is only capable of documenting a single unit of measurement. |
| U-Equal | Unit-equal. u-equal numeric items having the same units of measurement. For a formal definition, see [**Section 4.10**](#_4.10) below. |
| V-Equal | Value-equal: c-equal items having either the same non-numeric value, or numeric values that are equal within some tolerance defined by the lesser of their respective ` @precision`, implied ` @precision` or ` @decimals` attributes. For a formal definition see [**Section 4.10**](#_4.10) below. |
| XBRL Instance | XBRL instances are XML fragments with root element, `  <xbrl>  `. XBRL instances contain business report facts, with each fact corresponding to a [Concept](#concept) defined in their supporting DTS. XBRL instances also contain contexts and units that provide additional information needed to interpret the facts in the instance. |
| X-Equal | [\[XPath 1.0\]](#XPATH) -equal: The XPath "=" operator returns the value true. For a formal definition, see [**Section 4.10**](#_4.10) below. |

## 1.5 Levels of conformance

This specification describes two levels of conformance for XBRL aware processors. The first is required of all XBRL processors. Support for the other level of conformance will depend on the purpose of the processor.

Minimally conforming XBRL processors **MUST** completely and correctly implement all of the syntactic restrictions embodied in this specification.

Fully conforming XBRL processors **MUST** be minimally conforming and, in addition, they **MUST** completely and correctly implement all of the semantic restrictions relating to linkbases and XBRL instances.

All restrictions embodied in this specification apply to minimally conforming processors unless otherwise stated.

## 1.6 Namespace prefix conventions

This specification uses a number of namespace prefixes when describing elements and attributes. The namespace prefix convention used is as follows:

| Namespace prefix | Namespace name |
| --- | --- |
| link | http://www.xbrl.org/2003/linkbase |
| xbrli | http://www.xbrl.org/2003/instance |
| xl | http://www.xbrl.org/2003/XLink |
| xlink | http://www.w3.org/1999/xlink |
| xml | http://www.w3.org/XML/1998/namespace |
| xsi | http://www.w3.org/2001/XMLSchema-instance |
| xsd | http://www.w3.org/2001/XMLSchema |

Note that the `xml` prefix is reserved as defined in [\[XML Names\]](#XMLNAMES); specifically at [http://www.w3.org/TR/REC-xml-names/#nsc-NSDeclared](http://www.w3.org/TR/REC-xml-names/#nsc-NSDeclared).

Some elements and attributes defined in this specification are described without use of a namespace prefix or namespace. The normative namespaces for all elements and attributes defined in this spec are determined by the normative schemas contained herein ([**Appendix A**](#A)).

## 1.7 Extensions to this specification

It is understood that no single XML vocabulary can capture the entirety of business reporting. XBRL has therefore included extensibility as a design principle. Certain kinds of extension facilities are embodied in this specification, such as the basic ability to create taxonomies. In addition, it is possible to create new kinds of linkbases and new roles and arc roles for new and existing linkbases. It is also possible to create attributes that may be used on elements from the various XBRL namespaces. Other methods of extending the functionality of XBRL **MAY** be introduced in the future, by individual developers or with formal support from the XBRL consortium.

However, the design of this specification is such that all extension mechanisms **MUST** obey certain rules as follows:

- An extension **MUST NOT** add anything to the namespaces defined by this specification.
- An extension **MUST NOT** change the semantics of anything in this specification or anything in any of the namespaces defined in the schemas.
- An extension **MUST** use the elements and attributes of XBRL 2.1 and the other namespaces defined in this specification following the semantics defined herein and the syntactic constraints of XML Schema.

As an example, certain linkbases defined in this specification do not allow local resources. That constraint **MUST NOT** be changed by any extension mechanism. It is not permitted to create a "resources-allowed" link role whose semantics are to make local resources acceptable.

In summary, the only way to change the semantics of anything defined by this specification would be to change the text of this specification itself.

## 2 Changes from the previous published version

Changes from the previous, December 2001 version of [\[XBRL 2.1\]](#XBRL) (and the interim 2.0a "patch" release in November 2002) were driven by two factors. Several implementations of XML Schema required the removal of an ambiguous content model from the definition of contexts. This was done without changing the language recognised by the schema. Further implementation experience within the XBRL community, including the publication of the XBRL General Ledger taxonomy, motivated many other changes. A number of business requirements documented by the XBRL International Domain working group have been incorporated.

## 2.1 Changes in XBRL instances

The `group` element has been eliminated. It has been replaced with the `  <xbrl>  ` element, which acts as the root element of an [XBRL Instance](#XBRL-instance).

The set of [Taxonomy Schemas](#taxonomy-schema) and linkbases supporting an [XBRL Instance](#XBRL-instance) has been formally defined (as a [Discoverable Taxonomy Set](#DTS) (DTS)). XBRL instances now identify their supporting DTS using a new `  <schemaRef>  ` element, which points to supporting taxonomy schemas and using the existing `  <linkbaseRef>  ` element, which points to supporting linkbases. The XML Schema Instance ` @schemaLocation` attribute is no longer required in the DTS discovery process.

The `  <schemaRef>  ` elements must now appear first in an [XBRL Instance](#XBRL-instance). The `  <linkbaseRef>  ` elements must appear after the `  <schemaRef>  ` elements and before all other elements in an XBRL instance.

Guidance has been included on the entry of numerical quantities in [XBRL Instances](#XBRL-instance) for the common case of elements from accounting related taxonomies (elements using the optional " ` @balance` " attribute in their definition). The duration element has been eliminated from context [Periods](#period) so durations now have to be represented using `startDate` and `endDate`. There is also additional guidance on entering data to define a period of time.

The content of the [Unit](#unit) element has been simplified to facilitate more straightforward detection of equivalent units of measurement.

The ` @precision` attribute on `numericContext` has been eliminated in favour of more detailed documentation at the level of the [Numeric Items](#numeric-item). The ` @CWA` attribute on the `numericContext` element has been eliminated. The `  <unit>  ` element has been separated from the `numericContext` element to enable numeric and [Non-Numeric Items](#non-numeric-item) to use the same context structures. The `numericContext` element and the `nonNumericContext` element have been replaced with a `  <context>  ` element that documents only [Entity](#entity), [Period](#period) and scenario.

An additional mechanism has been introduced to enable [XBRL Instance](#XBRL-instance) preparers to make statements about the numerical accuracy of the facts reported. Specifically, a new ` @decimals` attribute has been allowed on items of numeric type to provide an alternative way to document accuracy in terms of the number of decimal places to which a numerical fact is accurate. Rules for handling ` @precision` and ` @decimals` attributes have been provided.

To specify that numbers are stated exactly in an [XBRL Instance](#XBRL-instance), two new types have been defined for use by the ` @decimals` and ` @precision` attributes. These types enable XBRL Instances to specify that numbers are represented to an infinite number of significant figures or number of decimal places.

The definition of a [Duplicate Item](#duplicate-items) has been changed to include reference to the content of any [Tuple](#tuple) structures that contain the items being compared.

## 2.2 Changes in XBRL taxonomies

Some of the [Arc](#arc) role values and role values previously *suggested* are now *normative* and additional arc role values and role values have been defined. Some of the previously suggested arc role values have been removed. A new mechanism to define custom arc role values and role values has been added. The essence-alias arc in definition [Extended Links](#extended-link) has superseded the element-dimension relationship in calculation extended links. The parent-child arc no longer exists in the calculation extended link and has been replaced by summation-item arc. The parent-child arc no longer exists in the definition extended link and has been replaced by the general-special arc and by the XML Schema approach to content modelling for [Tuples](#tuple). Because the parent-child arc in definition extended links has two possible replacements, this is one area where complete backward compatibility with 2.0 has not been achieved. Some manual intervention may be required when converting these relationships expressed in 2.0 taxonomies to 2.1. Some networks of relationships are no longer allowed to contain directed or undirected cycles.

[Tuples](#tuple) may now have a complex content model, but **MUST** only use a restricted set of XML Schema constructs to describe this content model. Tuple content model definitions **MUST NOT** permit descendant elements for the tuple that are not in the item substitution group or in the tuple substitution group. This implies that the declarations of the descendant elements for tuples **MUST** be references to globally declared elements [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES).

Calculations have been constrained to apply only within the scope of a [Tuple](#tuple) for items within a tuple.

The number of available item types has been expanded to include all of the appropriate built-in data types of XML Schema [\[XML Schema Datatypes\]](#XMLSCHEMA-DATATYPES).

A new type for items has been defined to allow the specification of facts that are reported as fractions (such as 22.5/77.5). The fraction type is not among the built-in data types of XML Schema [\[XML Schema Datatypes\]](#XMLSCHEMA-DATATYPES). Since fractions have two parts, denominator and numerator, it has complex content.

Derivation of new item and [Tuple](#tuple) types from those defined by XBRL itself has been limited so that item types **MUST** be defined by restriction from the set of item types provided by XBRL. This set contains item types that are derived by extension from all the appropriate built-in simple types of XML Schema and a special purpose type with complex content, the `fractionItemType`.

The suggested ` @xlink:role` attribute on extended link [Locators](#locator), that indicated the root element of a relationship hierarchy, has been eliminated.

Clarity has been provided around the possibility for linkbases to be contained in [Taxonomy Schemas](#taxonomy-schema).

A mandatory ` @periodType` attribute has been added to [Concept](#concept) definitions to constrain the type of [Period](#period) that can be attached to items based on concepts.

## 3 XBRL framework

XBRL defines a syntax in which a fact can be reported as the value of a well defined reporting [Concept](#concept) within a particular context. The syntax enables software to efficiently and reliably find, extract and interpret those facts. The XBRL framework splits business reporting information into two components: [XBRL Instances](#XBRL-instance) and taxonomies.

[XBRL Instances](#XBRL-instance) contain the facts being reported while the taxonomies define the [Concepts](#concept) being communicated by the facts. The combination of an XBRL instance and its supporting taxonomies, and additional linkbases constitute an XBRL business report.

## 3.1 Overview of XBRL taxonomies

A taxonomy is comprised of an XML Schema [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) and all of the linkbases contained in that schema or directly referenced by that schema. The XML schema is known as a [Taxonomy Schema](#taxonomy-schema).

In XBRL terminology, a [Concept](#concept) is a definition of a reporting term. Concepts manifest as XML Schema [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) element definitions. In the [Taxonomy Schema](#taxonomy-schema) a concept is given a concrete name and a type. The type defines the kind of data types allowed for facts measured according to the concept definition. For example, a "cash" concept would typically have a monetary type. This declares that when cash is reported, its value will be monetary. In contrast, a "accountingPoliciesNote" concept would typically have a string type so that, when the "accountingPoliciesNote" is reported in an [XBRL Instance](#XBRL-instance), its value would be interpreted as a string of characters. Additional constraints on how concepts can be used are documented by additional XBRL attributes on the XML Schema [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) element definitions that correspond to the concepts. See [**Section 5.1.1**](#_5.1.1) for details.

The linkbases in a taxonomy further document the meaning of the [Concepts](#concept) by expressing relationships between concepts (inter-concept relationships) and by relating concepts to their documentation. See [**Section 5.2**](#_5.2) for details.

A [Linkbase](#linkbase) is a collection of [extended links](#extended-link). There are five different kinds of extended links used in taxonomies to document [Concepts](#concept): definition, calculation, presentation, label and reference. The first three types of extended link express inter-concept relationships, and the last two express relationships between concept and their documentation.

The linkbases **MAY** be contained in a separate document from the [Taxonomy Schema](#taxonomy-schema), and they **MAY** be embedded in the taxonomy schema. When a linkbase is not embedded in a taxonomy schema, the taxonomy schema **MUST** contain a `  <linkbaseRef>  ` to point to the linkbase document if the linkbase is to be part of the taxonomy built around the taxonomy schema.

## 3.2 Overview of XBRL instances

While a taxonomy defines reporting [Concepts](#concept), it does not contain the actual values of facts based on the defined concepts. The fact values are contained in [XBRL Instances](#XBRL-instance) and are referred to as "facts". Besides the actual value of a fact, such as "cash is 500,000", the XBRL instance provides contextual information necessary for interpreting the fact values. For numeric facts, the XBRL instance also documents measurement accuracy and measurement [Units](#unit).

An [XBRL Instance](#XBRL-instance) can be supported by more than one taxonomy. Also, taxonomies can be interconnected, extending and modifying each other in various ways. Generally, it is necessary to consider multiple related taxonomies together when interpreting an XBRL instance. The set of related taxonomies is called a [Discoverable Taxonomy Set](#DTS) ([DTS](#DTS)). A DTS is a collection of [Taxonomy Schemas](#taxonomy-schema) and [Linkbases](#linkbase). The bounds of a DTS are determined by starting from some set of documents (instance, taxonomy schema, or linkbase) and following DTS discovery rules. Although an XBRL instance can be the starting point for DTS discovery, the XBRL instance itself is not part of the DTS. Taxonomy schemas and linkbases that are used as starting points for DTS discovery are part of the DTS that they discover.

[DTS](#DTS) rules of discovery:

[Taxonomy Schemas](#taxonomy-schema) in the [DTS](#DTS) are those:

1. referenced directly from an [XBRL Instance](#XBRL-instance) using the `  <schemaRef>  `, `  <roleRef>  `, `  <arcroleRef>  ` or `  <linkbaseRef>  ` element. The ` @xlink:href` attribute on the `  <schemaRef>  `, `  <roleRef>  `, `  <arcroleRef>  ` or `  <linkbaseRef>  ` element contains the URL of the taxonomy schema that is discovered. Every taxonomy schema that is referenced by the `  <schemaRef>  `, `roleRef, arcroleRef` or `  <linkbaseRef>  ` element **MUST** be discovered.
2. referenced from a discovered taxonomy schema via an XML Schema `import` or `include` element. Every taxonomy schema that is referenced by an `import` or `include` element in a discovered taxonomy schema **MUST** be discovered.
3. referenced from a discovered [Linkbase](#linkbase) document via a `  <loc>  ` element. Every taxonomy schema that is referenced by an ` @xlink:href` attribute on a `  <loc>  ` element in a discovered linkbase **MUST** be discovered.
4. referenced from a discovered linkbase document via a `  <roleRef>  ` element. Every taxonomy schema that is referenced by an ` @xlink:href` attribute on a `  <roleRef>  ` element in a discovered linkbase **MUST** be discovered.
5. referenced from a discovered linkbase document via an `  <arcroleRef>  ` element. Every taxonomy schema that is referenced by an ` @xlink:href` attribute on an `  <arcroleRef>  ` element in a discovered linkbase **MUST** be discovered.
6. referenced from a discovered taxonomy schema via a `  <linkbaseRef>  ` element. Every taxonomy schema that is referenced by an ` @xlink:href` attribute on a `  <linkbaseRef>  ` element in a discovered taxonomy schema **MUST** be discovered.

**NOTE:** since `<redefine>` is prohibited in [Taxonomy Schemas](#taxonomy-schema) it cannot play a role in [DTS](#DTS) discovery.

[Linkbase](#linkbase) documents in the [DTS](#DTS) are those:

1. referenced directly from an [XBRL Instance](#XBRL-instance) via the `  <linkbaseRef>  ` element. The ` @xlink:href` attribute contains the URL of the linkbase document being discovered. Every linkbase that is referenced by the `  <linkbaseRef>  ` element **MUST** be discovered.
2. referenced from a discovered taxonomy schema via the `  <linkbaseRef>  ` element. The ` @xlink:href` attribute contains the URL of the linkbase being discovered. Every linkbase that is referenced by the `  <linkbaseRef>  ` element **MUST** be discovered.
3. that are among the set of nodes identified by the XPath [\[XPath 1.0\]](#XPATH) path `"//xsd:schema/xsd:annotation/xsd:appinfo/*" ` in a discovered taxonomy schema (Throughout this specification, `schema`, `annotation` and `appinfo` are all elements defined in the XML Schema namespace).
4. referenced from a discovered linkbase document via a `  <loc>  ` element. Every linkbase that contains a resource that is referenced by an ` @xlink:href` attribute on a `  <loc>  ` element in a discovered linkbase **MUST** be discovered.

For example, the "Financial Reporting for Commercial and Industrial Companies, US GAAP DTS" consists of well-defined [Concepts](#concept) within the US Generally Accepted Accounting Principles (GAAP) when those principles are applied to Commercial and Industrial (C&I) companies. This [DTS](#DTS) contains an "expense" concept.

A hospital [XBRL Instance](#XBRL-instance) may use these [Concepts](#concept) from the US GAAP C&I [DTS](#DTS) as well as an additional concept "physician salaries" that is defined in a separate taxonomy. This taxonomy would include [Linkbases](#linkbase) that relate the "physician salaries" concept to the "expense" concept in the US GAAP C&I DTS. The hospital XBRL instance would have a `  <schemaRef>  ` element pointing to the hospital taxonomy. This XBRL instance would be the starting place for determining the DTS that supports the XBRL instance. The discovery starts by following the `  <schemaRef>  ` element to the hospital taxonomy. In the hospital taxonomy there would be a `  <linkbaseRef>  ` element pointing to its linkbases. One of the linkbases contains a `  <loc>  ` element pointing to the "expense" concept in one the US GAAP C&I taxonomies. The taxonomy that contains the "expense" concept would point to the other taxonomies in the US GAAP C&I DTS. Following this discovery process, all necessary taxonomies would be discovered and the result would be a DTS that includes the US GAAP C&I DTS and the hospital specific taxonomy.

As this example shows, [DTSs](#DTS) can also be used as "building blocks" to create larger, more sophisticated DTSs. Users **MAY** compose groups of existing DTSs into higher-level DTSs and **MAY** selectively add concepts and concept relationships via extension taxonomies.

While some consuming applications might be able to perform processing on an XBRL data file without referring to a [DTS](#DTS), normally, the interpretation and processing of any given XBRL fact is relative to the contents of a DTS.

For example, given an [XBRL Instance](#XBRL-instance), to correctly produce a list of facts with the entries in the list corresponding to an ordered set of [Concepts](#concept), it is necessary to find the label corresponding to each fact being listed. The labels are contained in label [Extended Links](#extended-link). The locations of the label extended links may be specified by `  <linkbaseRef>  ` elements in the [Taxonomy Schemas](#taxonomy-schema) that have been identified as supporting the facts being presented. The label extended link locations may also be specified by `  <linkbaseRef>  ` elements in the XBRL instance itself.

When processing an [XBRL Instance](#XBRL-instance), consuming applications **MUST** use all of the linkbases referenced directly or indirectly in this way, if they are relevant to the processing activities. All references to [Taxonomy Schemas](#taxonomy-schema) and linkbases **MUST** be resolved when determining the [DTS](#DTS) supporting an XBRL instance.

## 3.3 Data integrity and confidentiality

There are many applications that require business information to be transmitted securely, with a particular emphasis on data integrity (leading to the use of hash totals, etc.) and with confidentiality (leading to the use of cryptographic means of protection). XBRL deliberately provides neither of these mechanisms, since its focus is on transmission of actual content in an agreed-upon format. it is assumed that, like any other block of data, data integrity can be enhanced by adding redundant error correction bytes, by cryptographic hashing and signing with a private key, etc. These mechanisms are all outside the scope of XBRL.

An [XBRL Instance](#XBRL-instance) does not have to be aware of whether all or some of it has been manipulated to be signed, encrypted, canonicalised, compressed, etc. By the time XBRL processing has to take place, all of those manipulations will have been unwound, and the XBRL payload will be free of any evidence of those operations.

## 3.4 Validation

[XBRL Instances](#XBRL-instance), XBRL [Linkbases](#linkbase) and XBRL [Taxonomy Schemas](#taxonomy-schema) **MUST** comply with the syntax requirements imposed in this specification. Many of these syntax requirements are expressed using XML Schemas so a part of the validation process can be performed using XML Schema validation software. Some of these syntax requirements are not or cannot be expressed using XML Schemas and so, **MUST** be handled using other validation technologies.

Consuming applications **MAY** also check that the data in an [XBRL Instance](#XBRL-instance) is consistent with the semantics expressed in the [DTS](#DTS) supporting the instance. Semantic inconsistencies do not invalidate the XBRL instances in which they occur. However, this specification identifies the semantic inconsistencies that can be tested for by fully conformant XBRL processors.

## 3.5 XLink in XBRL

Links between XML fragments occur in many forms in XBRL. There are links between [XBRL Instances](#XBRL-instance) and their supporting [DTS](#DTS). There are links between XBRL instance facts and the footnotes that describe relationships between those facts. There are links between [Concept](#concept) syntax definitions and their semantics, defined in linkbases. The semantics themselves are expressed in the networks of links that constitute the linkbases. XBRL expresses all of these links using the syntax defined in the XLink specification [\[XLINK\]](#XLINK). XBRL uses both the simple links and the [Extended Links](#extended-link) defined in the [\[XLINK\]](#XLINK) specification.

The [\[XLINK\]](#XLINK) specification establishes the syntax and semantics for a set of attributes in the [\[XLINK\]](#XLINK) namespace, `http://www.w3.org/1999/xlink`. These attributes can then be used on elements defined in another namespace to document various kinds of links between XML fragments. Many of these attributes are used extensively in XBRL. Others have no semantics that are relevant to the links defined by XBRL. These other attributes are permitted by the XML Schema syntax constraints but they are not documented or given any specific semantics in this specification. Examples include the ` @xlink:show` and the ` @xlink:actuate` attributes.

This section documents the generic forms of the simple links and the [Extended Links](#extended-link) used in XBRL. Specific elements that use the simple link or extended link syntax are documented in detail in the relevant sections of this specification dealing with the syntax of XBRL instances or the syntax of XBRL taxonomies.

The syntax of the generic [\[XLINK\]](#XLINK) structures used by XBRL is constrained by two XML Schemas: the *xlink-2003-12-31.xsd (normative)* that defines the syntax for the [\[XLINK\]](#XLINK) attributes; and the *xl-2003-12-31.xsd (normative)* that defines the content models for the various kinds of link-related elements defined by this specification.

### 3.5.1 Simple links

A simple link is a link that points from one resource to another [\[XLINK\]](#XLINK) [http://www.w3.org/TR/xlink/#simple-links](http://www.w3.org/TR/xlink/#simple-links). Some examples of how XBRL uses simple links are:

The XML Schema constraints on the simple links used by XBRL are shown below.

<schema  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/XLink" elementFormDefault="qualified" attributeFormDefault="unqualified"><complexType name="simpleType"><documentation>

Type for the simple links defined in XBRL

</documentation><restriction base="anyType">

<attributeGroup ref="xlink:simpleType"/>

<attribute ref="xlink:href" use="required"/>

<attribute ref="xlink:arcrole" use="optional"/>

<attribute ref="xlink:role" use="optional"/>

<attribute ref="xlink:title" use="optional"/>

<attribute ref="xlink:show" use="optional"/>

<attribute ref="xlink:actuate" use="optional"/>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></complexType><documentation>

The abstract element at the head of the simple link substitution group.

</documentation></schema>

#### 3.5.1.1 The @xlink:type attribute on simple links

The ` @xlink:type` attribute **MUST** occur and **MUST** have the fixed content " `simple` ".

#### 3.5.1.2 The @xlink:href attribute on simple links

A simple link **MUST** have an ` @xlink:href` attribute. The ` @xlink:href` attribute **MUST** be a URI. The URI **MUST** point to an XML document or to an XML fragment within an XML document. If the URI is relative, it **MUST** be resolved to obtain an absolute URI as specified in XML Base specification [\[XML Base\]](#XMLBASE). For details on the allowable forms of XPointer [\[XPOINTER\]](#XPOINTER) syntax in the URI see [**Section 3.5.4**](#_3.5.4)

#### 3.5.1.3 The @xlink:role attribute on simple links (optional)

The optional ` @xlink:role` attribute **MUST** take URI values. If it is provided, the ` @xlink:role` attribute **MUST NOT** be empty.

#### 3.5.1.4 The @xlink:arcrole attribute on simple links (optional)

If it occurs, the ` @xlink:arcrole` attribute **MUST NOT** be an empty string.

#### 3.5.1.5 The @xml:base attribute on simple links (optional)

The ` @xml:base` attribute [\[XML Base\]](#XMLBASE) **MAY** appear on the simple links, participating in the resolution of relative URIs specified in their ` @xlink:href` attributes.

### 3.5.2 The <linkbase> element

The [\[XLINK\]](#XLINK) specification defines linkbases in the following way: "documents containing collections of inbound and third-party links are called link databases, or linkbases" [\[XLINK\]](#XLINK) ([http://www.w3.org/TR/2001/REC-xlink-20010627/#dt-linkbase](http://www.w3.org/TR/2001/REC-xlink-20010627/#dt-linkbase)). While the syntax for [Concepts](#concept) is defined in [Taxonomy Schemas](#taxonomy-schema), the semantics of those concepts are defined in XBRL [Linkbases](#linkbase). Linkbases are [Extended Links](#extended-link) or they are elements that contain extended links. Linkbases **MAY** also contain `  <documentation>  ` elements.

The `  <linkbase>  ` element is intended to be used as a linkbase container. The XML Schema constraints on the `  <linkbase>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><element name="linkbase"><documentation>

Definition of the linkbase element. Used to contain a set of zero or more extended link elements.

</documentation><complexType><choice minOccurs="0" maxOccurs="unbounded">

<element ref="link:documentation"/>

<element ref="link:roleRef"/>

<element ref="link:arcroleRef"/>

<element ref="xl:extended"/>

</choice>

<attribute name="id" type="ID" use="optional"/>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</complexType></element></schema>

Example 1: A skeletal linkbase

<linkbase  
xmlns:samp="http://www.xbrl.org/sample"  
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"  
xmlns:xbrli="http://www.xbrl.org/2003/instance"  
xmlns="http://www.xbrl.org/2003/linkbase"  
xmlns:xlink="http://www.w3.org/1999/xlink"  
xmlns:xl="http://www.xbrl.org/2003/XLink" xsi:schemaLocation="http://www.xbrl.org/sample samp001.xsd" xml:base="http://www.xbrl.org/sample"><calculationLink xlink:role="http://www.xbrl.org/2003/role/link" xlink:type="extended">

<!---->

</calculationLink></linkbase>

Meaning: Use of `  <linkbase>  ` as the root element, holding namespace prefix definitions and the ` @schemaLocation` attribute. The " `xml:`" prefix need not be declared. One extended link element, the `  <calculationLink>  `, is contained in the linkbase.

#### 3.5.2.1 The @id attribute on <linkbase> elements (optional)

The `  <linkbase>  ` element **MAY** have an ` @id` attribute. The value of the ` @id` attribute **MUST** conform to the [\[XML\]](#XML) rules for attributes with the ID type ([http://www.w3.org/TR/REC-xml#NT-TokenizedType](http://www.w3.org/TR/REC-xml#NT-TokenizedType)).

#### 3.5.2.2 The @xml:base attribute on <linkbase> elements (optional)

The ` @xml:base` attribute [\[XML Base\]](#XMLBASE) **MAY** appear on the `  <linkbase>  ` element, participating in the resolution of relative URIs in the contained extended links.

#### 3.5.2.3 <Documentation> elements in <linkbase> elements (optional)

All `  <linkbase>  ` elements **MAY** also contain `  <documentation>  ` elements.

The XML Schema constraints on the `  <documentation>  ` element are shown below.

<schema  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/XLink" elementFormDefault="qualified" attributeFormDefault="unqualified"><complexType name="documentationType"><documentation>

Element type to use for documentation of extended links and linkbases.

</documentation><extension base="string">

<anyAttribute namespace="##other" processContents="lax"/>

</extension></complexType><documentation>

Abstract element to use for documentation of extended links and linkbases.

</documentation></schema>

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><documentation>

Concrete element to use for documentation of extended links and linkbases.

</documentation></schema>

The `  <documentation>  ` element **MUST** have string content. The `  <documentation>  ` element **MAY** contain any attribute that is not defined in the XBRL [Linkbase Namespace](#linkbase-namespace), `http://www.xbrl.org/2003/linkbase`. For example, the `  <documentation>  ` element **MAY** use the `  @xml:lang  ` attribute to indicate the language used for the documentation.

#### 3.5.2.4 The <roleRef> element (optional)

The `  <roleRef>  ` element is used to resolve custom ` @xlink:role` values that are used in a [Linkbase](#linkbase) or [XBRL Instance](#XBRL-instance) (for `  <footnoteLink>  ` and `  <footnote>  `). The `  <roleRef>  ` element is a simple link, as defined in [**Section 3.5.1**](#_3.5.1). The `  <roleRef>  ` element points to the `  <roleType>  ` element in a [Taxonomy Schema](#taxonomy-schema) document that declares the ` @xlink:role` attribute value (see [**Section 5.1.3**](#_5.1.3)). The value, **V**, of the ` @xlink:role` attribute on a [Standard Resource Element](#standard-resource-element) or extended link element **MUST** be an absolute URI. If **V** does not correspond to a role defined by this specification, it is a *custom role*; in this case the ancestor `  <linkbase>  ` element of the resource or extended link element **MUST** have a child `  <roleRef>  ` element with **V** as the value of its ` @roleURI` attribute.

Note that `  <roleRef>  ` s are only required for roles that are used on [Standard Extended Links](#standard-extended-link-element) and [Standard Resources](#standard-resource-element). The standard extended links are those defined by this specification: `  <definitionLink>  `, `  <calculationLink>  `, `  <presentationLink>  `, `  <labelLink>  `, `  <referenceLink>  ` and `  <footnoteLink>  `. Likewise, the standard resources are `  <label>  `, `  <footnote>  `, and `  <reference>  `.

The XML Schema constraints on the `  <roleRef>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><element name="roleRef" substitutionGroup="xl:simple"><documentation>

Definition of the roleRef element - used to link to resolve xlink:role attribute values to the roleType element declaration.

</documentation><documentation>

This attribute contains the role name.

</documentation></element></schema>

##### 3.5.2.4.1 The @xlink:type attribute on <roleRef> elements

The ` @xlink:type` attribute **MUST** occur and **MUST** have the fixed content " `simple` ".

##### 3.5.2.4.2 The @xlink:href attribute on <roleRef> elements

A `  <roleRef>  ` element **MUST** have an ` @xlink:href` attribute. The ` @xlink:href` attribute **MUST** be a URI. The URI **MUST** point to a `  <roleType>  ` element in a [Taxonomy Schema](#taxonomy-schema) document. If the URI reference is relative, its absolute version **MUST** be determined as specified in [\[XML Base\]](#XMLBASE) before use. For details on the allowable forms of XPointer [\[XPOINTER\]](#XPOINTER) syntax in the URI see [**Section 3.5.4**](#_3.5.4). All files referenced by an ` @xlink:href` attribute **MUST** be discovered as part of the [DTS](#DTS), regardless of what [Linkbase](#linkbase) the `  <roleRef>  ` appears in.

##### 3.5.2.4.3 The @xlink:arcrole attribute on <roleRef> elements (optional)

The ` @xlink:arcrole` attribute **MAY** be used on the `  <roleRef>  ` element. No semantics are defined for the ` @xlink:arcrole` attribute when it occurs on the `  <roleRef>  ` element.

##### 3.5.2.4.4 The @xlink:role attribute on <roleRef> elements (optional)

The optional ` @xlink:role` attribute **MUST** take URI values. If it is provided, the ` @xlink:role` attribute **MUST NOT** be empty. No semantics are defined for the ` @xlink:role` attribute when it occurs on the `  <roleRef>  ` element.

##### 3.5.2.4.5 The @roleURI attribute

The ` @roleURI` attribute **MUST** occur on the `  <roleRef>  ` element. The ` @roleURI` attribute identifies the ` @xlink:role` attribute value that is defined by the XML resource that is pointed to by the `  <roleRef>  ` element. The value of this attribute **MUST** match the value of the ` @roleURI` attribute on the `  <roleType>  ` element that the `  <roleRef>  ` element is pointing to. Within a [Linkbase](#linkbase) or an [XBRL Instance](#XBRL-instance) there **MUST NOT** be more than one `roleRef ` element with the same ` @roleURI` attribute value.

#### 3.5.2.5 The <arcroleRef> element (optional)

The `  <arcroleRef>  ` element is used to resolve custom ` @xlink:arcrole` values that are used in a [Linkbase](#linkbase) or an [XBRL Instance](#XBRL-instance) (for `  <footnoteArc>  `). The `  <arcroleRef>  ` element is a simple link, as defined in [**Section 3.5.1**](#_3.5.1). The `  <arcroleRef>  ` element points to the `  <arcroleType>  ` element in a [Taxonomy Schema](#taxonomy-schema) document that declares the ` @xlink:arcrole` attribute value (see [**Section 5.1.4**](#_5.1.4)). The value, **V**, of the ` @xlink:arcrole` attribute on a [Standard Arc Element](#standard-arc-element) in a [Standard Extended Link Element](#standard-extended-link-element) **MUST** be an absolute URI. If **V** does not correspond to an arcrole defined by this specification, it is a *custom arcrole*; in this case the ancestor `  <linkbase>  ` element of the [Arc](#arc) element **MUST** have a child `  <arcroleRef>  ` element with **V** as the value of its ` @arcroleURI` attribute.

Note that `  <arcroleRef>  ` s are only required for arcroles that are used on [Standard Arcs](#standard-arc-element) appearing in standard extended links. The standard arcs are those defined by this specification: `  <definitionArc>  `, `  <calculationArc>  `, `  <presentationArc>  `, `  <labelArc>  `, `  <referenceArc>  ` and `  <footnoteArc>  `.

The XML Schema definition of the `  <arcroleRef>  ` element is shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><element name="arcroleRef" substitutionGroup="xl:simple"><documentation>

Definition of the roleRef element - used to link to resolve xlink:arcrole attribute values to the arcroleType element declaration.

</documentation><documentation>

This attribute contains the arc role name.

</documentation></element></schema>

##### 3.5.2.5.1 The @xlink:type attribute on <arcroleRef> elements

The ` @xlink:type` attribute **MUST** occur and **MUST** have the fixed content " `simple` ".

##### 3.5.2.5.2 The @xlink:href attribute on <arcroleRef> elements

An `  <arcroleRef>  ` element **MUST** have an ` @xlink:href` attribute. The ` @xlink:href` attribute **MUST** be a URI. The URI **MUST** point to an `  <arcroleType>  ` element in a [Taxonomy Schema](#taxonomy-schema) document. If the URI reference is relative, its absolute version **MUST** be determined as specified in [\[XML Base\]](#XMLBASE) before use. For details on the allowable forms of XPointer [\[XPOINTER\]](#XPOINTER) syntax in the URI see [**Section 3.5.4**](#_3.5.4). All files referenced by an ` @xlink:href` attribute **MUST** be discovered as part of the [DTS](#DTS), regardless of what [Linkbase](#linkbase) the `  <arcroleRef>  ` appears in.

##### 3.5.2.5.3 The @xlink:arcrole attribute on <arcroleRef> elements (optional)

The ` @xlink:arcrole` attribute **MAY** be used on the `  <arcroleRef>  ` element. No semantics are defined for the ` @xlink:arcrole` attribute when it occurs on the `  <arcroleRef>  ` element.

##### 3.5.2.5.4 The @xlink:role attribute on <arcroleRef> elements (optional)

The optional ` @xlink:role` attribute **MUST** take URI values. If it is provided, the ` @xlink:role` attribute **MUST NOT** be empty. No semantics are defined for the ` @xlink:role` attribute when it occurs on the `  <arcroleRef>  ` element.

##### 3.5.2.5.5 The @arcroleURI attribute

The ` @arcroleURI` attribute **MUST** occur on the `  <arcroleRef>  ` element. The ` @arcroleURI` attribute identifies the `xlink:arcrole ` attribute value that is defined by the XML resource that is pointed to by the `  <arcroleRef>  ` element. The value of this attribute **MUST** match the value of the ` @arcroleURI` attribute on the `  <arcroleType>  ` element that the `arcroleRef ` element is pointing to. Within a [Linkbase](#linkbase) or an [XBRL Instance](#XBRL-instance) there **MUST NOT** be more than one `  <arcroleRef>  ` element with the same ` @arcroleURI` attribute value.

### 3.5.3 Extended links

[Extended Links](#extended-link) are [\[XLINK\]](#XLINK) annotated XML fragments that document a set of relationships between resources. XBRL extended links document relationships between resources that are XML fragments.

The generic XML Schema constraints on the extended links used by XBRL are shown below.

<schema  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/XLink" elementFormDefault="qualified" attributeFormDefault="unqualified"><complexType name="extendedType"><documentation>

Generic extended link type

</documentation><restriction base="anyType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="xl:documentation"/>

<element ref="xl:locator"/>

<element ref="xl:arc"/>

<element ref="xl:resource"/>

</choice>

<attributeGroup ref="xlink:extendedType"/>

<attribute ref="xlink:role" use="required"/>

<attribute ref="xlink:title" use="optional"/>

<attribute name="id" type="ID" use="optional"/>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></complexType><documentation>

Abstract extended link element at head of extended link substitution group.

</documentation></schema>

XBRL extended links **MAY** contain five different types of child elements:

- `  <documentation>  ` elements;
- `title` elements (titles);
- `locator` elements ([Locators](#locator));
- `resource` elements (resources); and
- `arc` elements ([Arcs](#arc)).

The `  <documentation>  ` element is for XBRL documentation purposes only and has no [\[XLINK\]](#XLINK) -specific semantics. Titles, [Locators](#locator), resources and [Arcs](#arc) are identified by specific [\[XLINK\]](#XLINK) attributes. If the titles, [Locators](#locator), resources and arcs are not direct children of an extended element, then they have no [\[XLINK\]](#XLINK) specified meaning, and hence have no XBRL-specified meaning.

The attributes for XBRL extended links are described below.

#### 3.5.3.1 The @id attribute on extended links (optional)

[Extended Links](#extended-link) **MAY** have an ` @id` attribute. The value of the ` @id` attribute **MUST** conform to the [\[XML\]](#XML) rules for attributes with the ID type (see [http://www.w3.org/TR/REC-xml#NT-TokenizedType](http://www.w3.org/TR/REC-xml#NT-TokenizedType) for details). The ` @id` attribute identifies an extended link (see [**Section 4.8**](#_4.8)) so that it may be referenced directly by simple links.

#### 3.5.3.2 The @xlink:type attribute on extended links

The ` @xlink:type` attribute **MUST** occur on extended links and **MUST** have the fixed content " `extended` ".

#### 3.5.3.3 The @xlink:role attribute on extended links

The ` @xlink:role` attribute **MUST** occur on [Standard Extended Links](#standard-extended-link-element). The content of the ` @xlink:role` attribute is referred to as the extended link role value. The extended link role value **MUST** be used by applications to partition extended links into separate networks of relationships. See [**Section 5.2**](#_5.2) for details on how the semantics embodied in extended link arcs is contingent on extended link arc role values. One standard extended link role is defined by this specification:

`http://www.xbrl.org/2003/role/link`

Standard extended links may use this role without the need for a `  <roleType>  ` (see [**Section 5.1.3**](#_5.1.3)) and roleRef (see [**Section 3.5.2.4**](#_3.5.2.4))

#### 3.5.3.4 The @xml:base attribute on extended links (optional)

The ` @xml:base` attribute [\[XML Base\]](#XMLBASE) **MAY** appear on the extended links, participating in the resolution of relative URIs that they contain.

#### 3.5.3.5 Documentation elements in extended links (optional)

All XBRL extended links **MAY** contain `  <documentation>  ` elements.

The `  <documentation>  ` elements in extended links conform to the same syntax requirements that apply to `  <documentation>  ` elements in `Linkbase` elements. See [**Section 3.5.2.3**](#_3.5.2.3) for details.

#### 3.5.3.6 Titles in extended links (optional)

All XBRL [Extended Links](#extended-link) **MAY** contain titles. Titles may be used to document extended links, as an alternative to the more limited ` @xlink:title` attributes. They are particularly useful where information needs to be provided in multiple languages. Titles have no XBRL specified semantics. To use a title in an extended link, it is necessary to define a new element that is in the substitution group for the abstract `title` element.

The XML Schema constraints on the titles are shown below.

<schema  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/XLink" elementFormDefault="qualified" attributeFormDefault="unqualified"><complexType name="titleType"><documentation>

Type for the abstract title element - used as a title element template.

</documentation><restriction base="anyType">

<attributeGroup ref="xlink:titleType"/>

</restriction></complexType><documentation>

Generic title element for use in extended link documentation. Used on extended links, arcs, locators. See http://www.w3.org/TR/xlink/#title-element for details.

</documentation></schema>

##### 3.5.3.6.1 The @xlink:type attribute on titles

The ` @xlink:type` attribute **MUST** occur on all titles and **MUST** have the fixed content " `title` ".

#### 3.5.3.7 Locators

[Locators](#locator) are child elements of an [Extended Link](#extended-link) that point to resources external to the extended link itself. All XBRL extended links **MAY** contain locators.

The XML Schema constraints on generic [Locators](#locator) are shown below.

<schema  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/XLink" elementFormDefault="qualified" attributeFormDefault="unqualified"><complexType name="locatorType"><documentation>

Generic locator type.

</documentation><restriction base="anyType"><sequence>

<element ref="xl:title" minOccurs="0" maxOccurs="unbounded"/>

</sequence>

<attributeGroup ref="xlink:locatorType"/>

<attribute ref="xlink:href" use="required"/>

<attribute ref="xlink:label" use="required"/>

<attribute ref="xlink:role" use="optional"/>

<attribute ref="xlink:title" use="optional"/>

</restriction></complexType><documentation>

Abstract locator element to be used as head of locator substitution group for all extended link locators in XBRL.

</documentation></schema>

For consistency, the `  <loc>  ` element is the only [Locator](#locator) defined for use in XBRL [Extended Links](#extended-link). The `  <loc>  ` element is a concrete version of the generic locator. The XML Schema syntax constraints on the `  <loc>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><documentation>

Concrete locator element. The loc element is the XLink locator element for all extended links in XBRL.

</documentation></schema>

##### 3.5.3.7.1 The @xlink:type attribute on locators

The ` @xlink:type` attribute **MUST** occur on all [Locators](#locator) and **MUST** have the fixed content " `locator` ".

##### 3.5.3.7.2 The @xlink:href attribute on locators

A [Locator](#locator) **MUST** have an ` @xlink:href` attribute. The ` @xlink:href` attribute **MUST** be a URI. The URI **MUST** point to an XML document or to one or more XML fragments within an XML document. If the URI is relative, it **MUST** be resolved to obtain an absolute URI as specified in XML Base specification [\[XML Base\]](#XMLBASE). For details on the allowable forms of XPointer [\[XPOINTER\]](#XPOINTER) syntax in the URI see [**Section 3.5.4**](#_3.5.4). All files referenced by an ` @xlink:href` attribute **MUST** be discovered as part of the [DTS](#DTS), regardless of what [Linkbase](#linkbase) the locator appears in.

##### 3.5.3.7.3 The @xlink:label attribute on locators

The ` @xlink:label` attribute on a [Locator](#locator) identifies the locator so that [Arcs](#arc) in the same [Extended Link](#extended-link) can reference it. Multiple locators and resources in an extended link **MAY** have the same ` @xlink:label` attribute value. The ` @xlink:label` attribute value **MUST** be an NCName [\[XML\]](#XML) ([http://www.w3.org/TR/REC-xml-names/#NT-NCName)](http://www.w3.org/TR/REC-xml-names/#NT-NCName\)). This requirement means that ` @xlink:label` attributes **MUST** begin with a letter or an underscore.

##### 3.5.3.7.4 Titles on locators (optional)

[Locators](#locator) **MAY** contain titles. Title children of locators **MUST** conform to the same restrictions applying to title children of [Extended Links](#extended-link). See [**Section 3.5.3.6**](#_3.5.3.6) for details.

#### 3.5.3.8 Resources

Some XBRL [Extended Links](#extended-link) **MAY** contain resources. A resource is an XML fragment in an extended link that is related to other resources in the extended link and to resources outside of the extended link.

The XML Schema constraints on generic resources are shown below.

<schema  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/XLink" elementFormDefault="qualified" attributeFormDefault="unqualified"><complexType name="resourceType"><documentation>

Generic type for the resource type element

</documentation><restriction base="anyType">

<attributeGroup ref="xlink:resourceType"/>

<attribute ref="xlink:label" use="required"/>

<attribute ref="xlink:role" use="optional"/>

<attribute ref="xlink:title" use="optional"/>

<attribute name="id" type="ID" use="optional"/>

</restriction></complexType><documentation>

Abstract element to use as head of resource element substitution group.

</documentation></schema>

The content of generic resources is very loosely constrained. More specific constraints are applied by this specification for specific kinds of resources in specific kinds of extended links.

##### 3.5.3.8.1 The @xlink:type attribute on resources

The ` @xlink:type` attribute **MUST** occur on all resources and **MUST** have the fixed content " `resource` ".

##### 3.5.3.8.2 The @xlink:label attribute on resources

The ` @xlink:label` attribute on a resource identifies the resource so that [Arcs](#arc) in the same [Extended Link](#extended-link) can reference it. The ` @xlink:label` attribute on resources conforms to the same requirements applying to the ` @xlink:label` attribute on [Locators](#locator). See [**Section 3.5.3.7.3**](#_3.5.3.7.3) for details. Several resources in an extended link **MAY** have the same label.

##### 3.5.3.8.3 The @xlink:role attribute on resources (optional)

The optional ` @xlink:role` attribute on a resource is referred to as the resource role value.

Resources **MAY** contain an ` @xlink:role` attribute, which **SHOULD** distinguish between resources based on the nature of the information that they contain. Some of the resources defined in this specification have a set of standard resource role values defined for them`.` Custom reference roles can be defined using roleTypes (see [**Section 5.1.3**](#_5.1.3)).

##### 3.5.3.8.4 The @id attribute on resources (optional)

The ` @id` attribute **MAY** occur on all resources in XBRL [Extended Links](#extended-link). The value of the ` @id` attribute **MUST** conform to the [\[XML\]](#XML) rules for attributes with the ID type ([http://www.w3.org/TR/REC-xml#NT-TokenizedType).](http://www.w3.org/TR/REC-xml#NT-TokenizedType\).-) The ` @id` attribute identifies the resource so that it may be referenced by `locators` in other extended links for the purposes of [Arc](#arc) prohibition (see [**Section 3.5.3.9.5**](#_3.5.3.9.5)).

#### 3.5.3.9 Arcs

All XBRL [Extended Links](#extended-link) **MAY** contain `arcs`. [Arcs](#arc) document relationships between resources identified by [Locators](#locator) in extended links or occurring as resources in extended links.

The XML Schema constraints on generic [Arcs](#arc) are shown below.

<schema  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/XLink" elementFormDefault="qualified" attributeFormDefault="unqualified"><simpleType name="useEnum"><documentation>

Enumerated values for the use attribute on extended link arcs.

</documentation><restriction base="NMTOKEN">

<enumeration value="optional"/>

<enumeration value="prohibited"/>

</restriction></simpleType><complexType name="arcType"><documentation>

basic extended link arc type - extended where necessary for specific arcs Extends the generic arc type by adding use, priority and order attributes.

</documentation><restriction base="anyType"><sequence>

<element ref="xl:title" minOccurs="0" maxOccurs="unbounded"/>

</sequence>

<attributeGroup ref="xlink:arcType"/>

<attribute ref="xlink:from" use="required"/>

<attribute ref="xlink:to" use="required"/>

<attribute ref="xlink:arcrole" use="required"/>

<attribute ref="xlink:title" use="optional"/>

<attribute ref="xlink:show" use="optional"/>

<attribute ref="xlink:actuate" use="optional"/>

<attribute name="order" type="decimal" use="optional"/>

<attribute name="use" type="xl:useEnum" use="optional"/>

<attribute name="priority" type="integer" use="optional"/>

<anyAttribute namespace="##other" processContents="lax"/>

</restriction></complexType><documentation>

Abstract element to use as head of arc element substitution group.

</documentation></schema>

[Arcs](#arc) represent relationships between the XML fragments referenced by their [\[XLINK\]](#XLINK) attributes: ` @xlink:from` and ` @xlink:to`. The ` @xlink:from` and the ` @xlink:to` attributes represent each side of the arc. These two attributes contain the ` @xlink:label` attribute values of [Locators](#locator) and resources within the same [Extended Link](#extended-link) as the arc itself. For a locator, the referenced XML fragments comprise the set of XML elements identified by the `xlink:href ` attribute on the locator. For a resource, the referenced XML fragment is the resource element itself.

An [Arc](#arc) **MAY** reference multiple XML fragments on each side ("from" and "to") of the arc. This can occur if there are multiple [Locators](#locator) and/or resources in the [Extended Link](#extended-link) with the same ` @xlink:label` attribute value identified by the ` @xlink:from` or ` @xlink:to` attribute of the arc. Such arcs represent a set of one-to-one relationships between each of the XML fragments on their "from" side and each of the XML fragments on their "to" side.

Example 2: One-to-One arc relationships [\[XLINK\]](#XLINK)

This presentation link contains an [Arc](#arc) that relates one XBRL [Concept](#concept) to one other XBRL concept. The XML fragment on the "from" side is the conceptA element definition, found in the example.xsd [Taxonomy Schema](#taxonomy-schema). The XML fragment on the "to" side is the conceptB element definition, also found in the example.xsd taxonomy schema.

<presentationLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">

<loc xlink:type="locator" xlink:label="a" xlink:href="example.xsd#conceptA"/>

<loc xlink:type="locator" xlink:label="b" xlink:href="example.xsd#conceptB"/>

<presentationArc xlink:type="arc" xlink:from="a" xlink:to="b" xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child" order="1"/>

</presentationLink>

Example 3: One-to-Many arc relationships [\[XLINK\]](#XLINK)

This label link contains a single [Arc](#arc) that relates one XBRL [Concept](#concept) to two XBRL labels. This is accomplished by giving each of the label resources the same ` @xlink:label` attribute value, which, in turn, is the same as the ` @xlink:to` attribute value on the arc. The arc represents two relationships, one between `conceptA` and the standard label ("Concept A") and another between `conceptA` and the total label ("Total of Concept A").

<labelLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">

<loc xlink:type="locator" xlink:label="a" xlink:href="example.xsd#conceptA"/>

<label xlink:type="resource" xml:lang="en" xlink:label="lab\_a" xlink:role="http://www.xbrl.org/2003/role/label">Concept A</label>

<label xlink:type="resource" xml:lang="en" xlink:label="lab\_a" xlink:role="http://www.xbrl.org/2003/role/totalLabel">Total of Concept A</label>

<labelArc xlink:type="arc" xlink:from="a" xlink:to="lab\_a" xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label"/>

</labelLink>

This [Extended Link](#extended-link) could also express the same two relationships but be written with separate ` @xlink:label` attribute values for each label and two arcs.

<labelLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">

<loc xlink:type="locator" xlink:label="a" xlink:href="example.xsd#conceptA"/>

<label xlink:type="resource" xml:lang="en" xlink:label="lab\_a\_standard" xlink:role="http://www.xbrl.org/2003/role/label">Concept A</label>

<label xlink:type="resource" xml:lang="en" xlink:label="lab\_a\_total" xlink:role="http://www.xbrl.org/2003/role/totalLabel">Total of Concept A</label>

<labelArc xlink:type="arc" xlink:from="a" xlink:to="lab\_a\_standard" xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label"/>

<labelArc xlink:type="arc" xlink:from="a" xlink:to="lab\_a\_total" xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label"/>

</labelLink>

Semantically, these two extended links represent the same set of relationships between the concept and its labels.

Example 4: Many-to-Many arc relationships [\[XLINK\]](#XLINK)

This label link contains a single arc that relates two [Concepts](#concept) to two labels. This is accomplished by each of the [Locators](#locator) for the concepts having the same ` @xlink:label` attribute value, which in turn is the same as the ` @xlink:from` attribute value on the arc, and by each of the label resources having the same ` @xlink:label` attribute value, which in turn is the same as the ` @xlink:to` attribute value.

<labelLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">

<loc xlink:type="locator" xlink:label="ab" xlink:href="example.xsd#conceptA"/>

<loc xlink:type="locator" xlink:label="ab" xlink:href="example.xsd#conceptB"/>

<label xlink:type="resource" xml:lang="en" xlink:label="lab\_ab" xlink:role="http://www.xbrl.org/2003/role/label">Concept A or B</label>

<label xlink:type="resource" xml:lang="en" xlink:label="lab\_ab" xlink:role="http://www.xbrl.org/2003/role/totalLabel">Total of Concept A or B</label>

<labelArc xlink:type="arc" xlink:from="ab" xlink:to="lab\_ab" xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label"/>

</labelLink>

The arc represents 4 relationships as follows:

1. between conceptA and the label resource "Concept A or B"
2. between conceptA and the label resource "Total of Concept A or B"
3. between conceptB and the label resource "Concept A or B"
4. between conceptB and the label resource "Total of Concept A or B"

Like the one-to-many example, this [Extended Link](#extended-link) could be re-written as 4 one-to-one arcs, where each locator and each resource has a unique ` @xlink:label` attribute value. It could also be re-written as two one-to-two arcs where the label resources have the same ` @xlink:label` attribute value and the locators have unique ` @xlink:label` attribute values or *vice versa*.

There **MUST** not be any [\[XLINK\]](#XLINK) duplicate arcs within an [Extended Link](#extended-link). [\[XLINK\]](#XLINK) duplicate arcs are arcs that have the same pair of values for the ` @xlink:from` and ` @xlink:to` attributes within an extended link.

Example 5: Correct use of arcs according to [\[XLINK\]](#XLINK)

[\[XLINK\]](#XLINK) forbids duplicate [Arcs](#arc) within a single [Extended Link](#extended-link) and ignores `arcrole` in determining duplicates so the following example is invalid (see [**Section 5.2.6**](#_5.2.6) for details of `  <definitionLink>  ` extended links):

<definitionLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">

<loc xlink:type="locator" xlink:label="a" xlink:href="example.xsd#conceptA"/>

<loc xlink:type="locator" xlink:label="b" xlink:href="example.xsd#conceptB"/>

<definitionArc xlink:type="arc" xlink:from="a" xlink:to="b" xlink:arcrole="http://www.xbrl.org/2003/arcrole/general-special"/>

<definitionArc xlink:type="arc" xlink:from="a" xlink:to="b" xlink:arcrole="http://www.xbrl.org/2003/arcrole/requires-element"/>

</definitionLink>

instead, an alternative construction that is legal according to [\[XLINK\]](#XLINK), such as the following, **MUST** be used:

<definitionLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">

<loc xlink:type="locator" xlink:label="a" xlink:href="example.xsd#conceptA"/>

<loc xlink:type="locator" xlink:label="b" xlink:href="example.xsd#conceptB"/>

<definitionArc xlink:type="arc" xlink:from="a" xlink:to="b" xlink:arcrole="http://www.xbrl.org/2003/arcrole/general-special"/>

</definitionLink><definitionLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">

<loc xlink:type="locator" xlink:label="a" xlink:href="example.xsd#conceptA"/>

<loc xlink:type="locator" xlink:label="b" xlink:href="example.xsd#conceptB"/>

<definitionArc xlink:type="arc" xlink:from="a" xlink:to="b" xlink:arcrole="http://www.xbrl.org/2003/arcrole/requires-element"/>

</definitionLink>

##### 3.5.3.9.1 The @xlink:type attribute on arcs

The ` @xlink:type` attribute **MUST** occur on all [Arcs](#arc) and **MUST** have the fixed content " `arc` ".

##### 3.5.3.9.2 The @xlink:from attribute

The ` @xlink:from` attribute on an [Arc](#arc) **MUST** be equal to the value of an ` @xlink:label` attribute of at least one [Locator](#locator) or resource in the same [Extended Link](#extended-link) element as the arc element itself.

The ` @xlink:from` attribute value **MUST** be an NCName [\[XML\]](#XML) ([http://www.w3.org/TR/REC-xml-names/#NT-NCName)](http://www.w3.org/TR/REC-xml-names/#NT-NCName\)). This requirement means that ` @xlink:from` attributes **MUST** begin with a letter or an underscore.

##### 3.5.3.9.3 The @xlink:to attribute

The ` @xlink:to` attribute on an [Arc](#arc) **MUST** be equal to the value of an ` @xlink:label` attribute of at least one [Locator](#locator) or resource in the same [Extended Link](#extended-link) element as the arc element itself.

The ` @xlink:to` attribute value **MUST** be an NCName [\[XML\]](#XML) ([http://www.w3.org/TR/REC-xml-names/#NT-NCName)](http://www.w3.org/TR/REC-xml-names/#NT-NCName\)). This requirement means that ` @xlink:to` attributes **MUST** begin with a letter or an underscore.

##### 3.5.3.9.4 The @xlink:arcrole attribute

The ` @xlink:arcrole` attribute documents the specific kind of relationship being expressed by the [Arc](#arc). Its value is referred to as an arc role value. A set of standard arc role values are defined and given specific meaning in this specification for each arc element. These are documented in the sections describing the specific XBRL arc elements (`  <labelArc>  `, `  <referenceArc>  `, `  <calculationArc>  `, `  <definitionArc>  `, `  <presentationArc>  `, and `  <footnoteArc>  `) on which they are to be used.

Custom arc role values **MAY** be defined in [Taxonomy Schemas](#taxonomy-schema). The semantics for custom arc role values are defined using the `  <arcroleType>  ` element (see [**Section 5.1.4**](#_5.1.4)). `  <arcroleType>  ` s are discovered through `  <arcroleRef>  ` elements (see [**Section 3.5.2.5**](#_3.5.2.5)).

##### 3.5.3.9.5 The @order attribute (optional)

The optional ` @order` attribute **MUST** have a decimal value that that indicates the order in which applications **MUST** display siblings when hierarchical networks of relationships are being displayed. If missing, the ` @order` attribute value **MUST** default to "1". If multiple siblings in the hierarchy have the same ` @order` attribute value, the presentation order of those siblings is application dependent. The value of the ` @order` attribute is not restricted to integers, which is useful when there is a need to place a new sibling in between two previously defined siblings.

##### 3.5.3.9.6 Titles on arcs (optional)

[Arcs](#arc) **MAY** contain titles. Title children of arcs **MUST** conform to the same restrictions applying to title children of [Extended Links](#extended-link). See [**Section 3.5.3.6**](#_3.5.3.6) for details.

##### 3.5.3.9.7 Prohibiting and overriding relationships

A taxonomy author will generally not have write permissions on [Linkbases](#linkbase) created by other taxonomy authors. In situations where a taxonomy author needs to modify the relationships expressed in linkbases that they cannot alter directly, they may create new linkbases that contain [Arcs](#arc) that represent relationships that prohibit or override the specific relationships that are to be modified. Both overriding and prohibiting an existing relationship is achieved by constructing a new arc.

A prohibiting arc is an [Arc](#arc) that represents a prohibiting relationship or a set of prohibiting relationships. A prohibiting relationship is a relationship that negates another relationship. An overriding arc is an arc that represents an overriding relationship or a set of overriding relationships. An overriding relationship is a relationship that supersedes another relationship. Prohibition and overriding are relevant when determining the relationships in a network of relationships represented in a [DTS](#DTS) (see [**Section 3.5.3.9.7.3**](#_3.5.3.9.7.3)).

[Arcs](#arc) that represent prohibiting and overriding relationships are controlled by two attributes, ` @use` and ` @priority`, which are available on all arc elements defined in this specification.

###### 3.5.3.9.7.1 The @use attribute (optional)

The optional ` @use` attribute **MUST** take one of two possible values - `"optional"`, or `"prohibited"`.

`use="optional"` indicates that the [Arc](#arc) represents a relationship or set of relationships that **MAY** participate in a network of relationships represented by arcs in a [DTS](#DTS) (see [**Section 3.5.3.9.7.3**](#_3.5.3.9.7.3) for details on networks of relationships in a DTS). This is the default value that **MUST** be inferred for the ` @use` attribute if the ` @use` attribute is not specified.

`use="prohibited" ` indicates that this [Arc](#arc) represents a relationship or set of relationships that prohibit themselves and other equivalent relationships from participating in a network of relationships represented by arcs in a [DTS](#DTS) (see [**Section 3.5.3.9.7.4**](#_3.5.3.9.7.4) for details on relationship equivalency). Such relationships are referred to as prohibiting relationships.

###### 3.5.3.9.7.2 The @priority attribute (optional)

The content of the ` @priority` attribute **MUST** be an integer. The default value of the ` @priority` attribute is "0". The ` @priority` attribute is used when applying the rules of prohibition and overriding in a network of relationships. Each relationship has a priority equal to the value of the priority attribute on the [Arc](#arc) that represents the relationship.

###### 3.5.3.9.7.3 Networks of relationships in a DTS

The [Arcs](#arc) expressed in the [Extended Links](#extended-link) within a [DTS](#DTS) describe networks of relationships between XML fragments.

Individually, each [Arc](#arc) describes one or more relationships. However, within a [DTS](#DTS), only some of those relationships participate in the networks of relationships described by the DTS.

All relationships in the [DTS](#DTS) are candidates for inclusion in the networks of relationships described by the DTS. However, some relationships are excluded from the networks of relationships described by the DTS because they are prohibited or overridden by other relationships.

All [Arcs](#arc) in a [DTS](#DTS) are grouped into base sets of arcs. All arcs in a base set of arcs:

- have the same local name, namespace and ` @xlink:arcrole` attribute value on the `arc` element; and
- are contained in `extended link elements` that have the same local name, namespace, and ` @xlink:role` attribute value.

Each base set of [Arcs](#arc) in a [DTS](#DTS) represents the set of candidates for inclusion in a network of relationships. For each base set of arcs in a DTS, the rules of relationship prohibition and overriding determine the subset of relationships in that base set that participate in the corresponding network of relationships represented by arcs in the DTS.

###### 3.5.3.9.7.4 Equivalent relationships

Applying the rules of relationship prohibition and overriding requires a comparison of each relationship represented by [Arcs](#arc) in the base set to all other relationships represented by arcs in the base set.

Two relationships represented by [Arcs](#arc) in a given base set are equivalent if:

- in the post-schema-validation infoset [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) the following conditions hold:
	1. the [Arcs](#arc) have the same number of non-exempt attributes, and
		2. for each non-exempt attribute on the first [Arc](#arc) there is a corresponding [S-Equal](#s-equal) attribute on the second arc (see [**Section 4.10**](#_4.10) for the definition of S-Equal)
	For the purposes of the conditions above, the 'use' and 'priority' attributes are exempt, as are any attributes from the following namespaces:
	`http://www.w3.org/2000/xmlns/`
	`http://www.w3.org/1999/xlink`
	all other attributes are non-exempt,
	**NOTE**: This therefore applies after the consideration of any default and fixed values specified for attributes on the [Arc](#arc) declaration, according to the post-schema-validation infoset [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) specification
	and
- the XML fragments on the "from" sides of the relationships are identical as defined in [**Section 4.10**](#_4.10) (see [**Section 3.5.3.9**](#_3.5.3.9) for an explanation of the XML fragments identified by the ` @xlink:from` attribute on [Arcs](#arc)); and
- the XML fragments on the "to" sides of the relationships are identical as defined in [**Section 4.10**](#_4.10) (see [**Section 3.5.3.9**](#_3.5.3.9) for an explanation of the XML fragments identified by the ` @xlink:to` attribute on [Arcs](#arc)).

###### 3.5.3.9.7.5 Rules of prohibiting and overriding relationships

The rules of prohibiting and overriding relationships employ the ` @use` and ` @priority` attributes on [Arcs](#arc) and the notion of relationship equivalence to determine, for each relationship expressed by arcs in a base set, if that relationship is included in the network of relationships for that base set of arcs.

The rules of prohibition and overriding are applied to each set of equivalent relationships represented by [Arcs](#arc) in the base set as follows:

1. None of the prohibiting relationships in the set are ever included in the network of relationships represented by [Arcs](#arc) in the base set.
2. If only one relationship has the highest priority and that relationship is not prohibiting, then that relationship is an overriding relationship and is included in the network of relationships for the base set. All other equivalent relationships are not included in the network of relationships for the base set of [Arcs](#arc).
3. If there is more than one relationship with the highest priority and none of them are prohibiting, then one of those highest priority relationships **MUST** be included in the network of relationships for the base set of [Arcs](#arc). The relationship that is chosen for inclusion is an overriding relationship. All of the other equivalent relationships **MUST** be excluded from the network of relationships (these are overridden relationships) for the base set of arcs. The choice of which relationship is included in the network of relationships for the base set of arcs is application dependent.
4. If there are one or more relationships with the highest priority and at least one of those relationships is prohibiting, then none of the equivalent relationships are included in the network of relationships (these equivalent relationships, which are not prohibiting relationships, are prohibited relationships) for the base set of [Arcs](#arc).

Example 6: Prohibiting and overriding relationships

The following set of examples includes some unlikely but nevertheless possible situations and demonstrates how they are dealt with according to the rules of prohibiting and overriding relationships. These examples anticipate a series of extension taxonomies being created, possibly by different authors who do not have write access to the taxonomies that they are extending.

If the following two [Arcs](#arc) in a base set of arcs represent a set of equivalent relationships, then neither of those relationships is included in the network of relationships associated with that base set of arcs.

- Arc A with `use="optional"` and `priority="1"   ` represents relationship A
- Arc B with `use="prohibited"` and `priority="2"   ` represents relationship B

Arc B has the higher priority and represents a prohibiting relationship. Therefore relationship B excludes relationship A from the network of relationships associated with the base set of arcs. Relationship B is prohibiting and so, by definition, is excluded from the network of relationships associated with the base set of arcs (by application of rules i and iv).

If another arc is subsequently introduced into the base set of arcs as follows:

- Arc C with `use="prohibited"` and `priority="3"   ` represents relationship C

and relationship C is equivalent to the relationships A and B, then, since it has the highest priority, it is a prohibiting relationship. Therefore relationship C excludes relationship A from the network of relationships associated with the base set of arcs. Relationships B and C are prohibiting and so, by definition, are excluded from the network of relationships associated with the base set of arcs (by application of rules i and iv).

If another arc is subsequently introduced into the base set of arcs as follows:

- Arc D with `use="optional"` and `priority="4"   ` represents relationship D

and relationship D is equivalent to the relationships A, B and C, then, since it has the highest priority, it is an overriding relationship. Relationships A, B and C are therefore not included in the network of relationships associated with the base set of arcs. This relationship D thus effectively overrides the effect of the prohibiting relationships B and C and therefore is included in the network of relationships associated with the base set of arcs (by application of rule ii).

If another arc is subsequently introduced into the base set of arcs as follows:

- Arc E with `use="optional"` and `priority="4"   ` represents relationship E

and relationship E is equivalent to the relationships A, B, C and D, then, since it has the same priority as D, it is application dependent as to which of D and E is the overriding relationship. Relationships A, B and C are still not included in the network of relationships associated with the base set of arcs (by application of rule iii). Since the relationships are equivalent, the fact that it is application dependent as to which of D and E is the overriding relationship is unimportant because the choice of one over the other does not affect the semantics being expressed.

If another arc is subsequently introduced into the base set of arcs as follows:

- Arc F with `use="prohibited"` and `priority="4"   ` represents relationship F

and relationship F is equivalent to the relationships A, B, C, D and E, then, since it is one of the relationships with the highest priority, it is a prohibiting relationship and thus none of the equivalent relationships A, B, C, D, E or F are included in the network of relationships associated with the base set of arcs (by application of rule iv).

The process of dividing all discovered arcs in a [DTS](#DTS) into base sets and applying the rules of prohibition and overriding results in a set of networks of relationships, where each network contains relationships that:

- are represented by arcs that have the same local name, namespace and ` @xlink:arcrole` attribute value on the `arcType` element; and
- are represented by arcs that are contained in `extendedType` elements with the same local name, namespace, and ` @xlink:role` attribute value; and
- are not prohibited, prohibiting or overridden relationships.

### 3.5.4 Use of XPointer in URI fragment identifiers

To point to a particular XML element, URIs used in [\[XLINK\]](#XLINK) hrefs **MUST** end in a fragment identifier. According to the [\[XLINK\]](#XLINK) specification, XPointer [\[XPOINTER\]](#XPOINTER) syntax is allowed in the fragment identifier. The format of the fragment identifier **MUST** conform to the requirements set out for shorthand pointers ([http://www.w3.org/TR/xptr-framework/#shorthand](http://www.w3.org/TR/xptr-framework/#shorthand)) or to the requirements set out for a scheme-based pointer ([http://www.w3.org/TR/xptr-framework/#scheme](http://www.w3.org/TR/xptr-framework/#scheme)). The only scheme allowed for scheme-based pointers in XBRL links is the element scheme [\[ELEMENT-SCHEME\]](#ELEMENT-SCHEME).

Example 7: Example ` @xlink:href` values

| Example | Meaning |
| --- | --- |
| `#f1` | The fragment of the current document with an ` @id` attribute equal to "f1" |
| `us_bs_v21.xsd#currentAssets` | The element of the document us\_bs\_v21.xsd with an ` @id` attribute equal to "currentAssets" |
| `us_bs_v21.xsd#element(/1/14)` | The element of the document us\_bs\_v21.xsd that is the 14 child (in document order) of the root element. |
| `us_bs_v21.xsd#element(currentAssets)` | The element of the document us\_bs\_v21.xsd with an ` @id` attribute equal to "currentAssets" |

## 4 XBRL instances

An overview of [XBRL Instances](#XBRL-instance) is provided in [**Section 3.2**](#_3.2).

[XBRL Instances](#XBRL-instance) are XML fragments with root element, `  <xbrl>  `. XBRL instances contain facts, with each fact corresponding to a [Concept](#concept) defined in their supporting [DTS](#DTS). XBRL instances also contain `  <context>  ` and `  <unit>  ` elements that provide additional information needed to interpret the facts in the instance.

Facts can be simple, in which case their values are expressed as simple content (except in the case of simple facts whose values are expressed as a ratio), and facts can be compound, in which case their values are made up from other simple and/or compound facts. Simple facts are expressed using items (and are referred to as items in this specification) and compound facts are expressed using [Tuples](#tuple) (and are referred to as tuples in this specification).

Although the syntax for any given [Tuple](#tuple) or item can only be defined in a single [Taxonomy Schema](#taxonomy-schema), an [XBRL Instance](#XBRL-instance) **MAY** contain XBRL items and tuples from any number of taxonomy schemas.

[XBRL Instances](#XBRL-instance) identify the taxonomy schemas and XBRL [Linkbases](#linkbase) that make up the starting points for discovery of the [DTS](#DTS) that supports them. [**Section 3.2**](#_3.2) documents how the DTS supporting an XBRL instance is to be determined.

The [Taxonomy Schemas](#taxonomy-schema) and the [Linkbases](#linkbase) used as starting points in [DTS](#DTS) discovery are identified via the `  <schemaRef>  ` elements and `  <linkbaseRef>  ` elements in [XBRL Instances](#XBRL-instance) respectively. This enables XBRL instances to exert some control over the interpretation of the information that they report.

For example, the same set of elements defined in a [Taxonomy Schema](#taxonomy-schema) might have Spanish and Portuguese literature references defined in different [Linkbases](#linkbase) (that are not referenced directly from that schema). An instance might provide access to both or neither of these linkbases in order to specify which set of references the producer considers to be more appropriate.

An [XBRL Instance](#XBRL-instance) **MUST** comply with the rules specified herein. The syntax for XBRL instances is constrained using a set of XML Schemas. Example elements defined in the XBRL instance schema, *xbrl-instance-2003-12-31.xsd (normative)*, include `  <xbrl>  `, `  <item>  `, `  <context>  `, `  <unit>  `, and `  <tuple>  `. All XBRL instances **MUST** be valid XML documents as defined by XML Schema [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES).

The semantics of [XBRL Instances](#XBRL-instance) and their contents are specified only insofar as they impact the operation of software applications that use this specification.

## 4.1 The <xbrl> element

Expressing even a single fact in an XBRL instance requires multiple elements: at least one item element (see [**Section 4.1.1**](#_4.1.1)) and a `  <context>  ` element containing sub-elements (see [**Section 4.7**](#_4.7) below). Therefore, a container element is necessary to serve as the root element of an [XBRL Instance](#XBRL-instance). This container is the `  <xbrl>  ` element. If multiple "data islands" of XBRL mark-up are included in a larger document, the `  <xbrl>  ` element is the container for each.

The XML Schema constraints on the `  <xbrl>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><element name="xbrl"><documentation>

XBRL instance root element.

</documentation><complexType><sequence>

<element ref="link:schemaRef" minOccurs="1" maxOccurs="unbounded"/>

<element ref="link:linkbaseRef" minOccurs="0" maxOccurs="unbounded"/>

<element ref="link:roleRef" minOccurs="0" maxOccurs="unbounded"/>

<element ref="link:arcroleRef" minOccurs="0" maxOccurs="unbounded"/>

<choice minOccurs="0" maxOccurs="unbounded">

<element ref="xbrli:item"/>

<element ref="xbrli:tuple"/>

<element ref="xbrli:context"/>

<element ref="xbrli:unit"/>

<element ref="link:footnoteLink"/>

</choice></sequence>

<attribute name="id" type="ID" use="optional"/>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</complexType></element></schema>

Example 8: Use of xbrl as the root element

<xbrl  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns:ci="http://www.xbrl.org/us/gaap/ci/2003/usfr-ci-2003"  
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"  
xmlns:s="http://mycompany.com/xbrl/taxonomy"  
xmlns:xbrli="http://www.xbrl.org/2003/instance"  
xmlns:xlink="http://www.w3.org/1999/xlink"  
xmlns:xl="http://www.xbrl.org/2003/XLink"  
xmlns="http://www.xbrl.org/2003/instance" xsi:schemaLocation="http://www.xbrl.org/us/fr/ci/2003/usfr-ci-2003 http://www.xbrl.org/us/fr/ci/2000-07-31/usfr-ci-2003.xsd">

<link:schemaRef xlink:type="simple" xlink:href="http://www.xbrl.org/us/fr/ci/2000-07-31/usfr-ci-2003.xsd"/>

<ci:assets precision="3" unitRef="u1" contextRef="c1">727</ci:assets>

<ci:liabilities precision="3" unitRef="u1" contextRef="c1">635</ci:liabilities>

<context id="c1">

<!---->

</context><unit id="u1">

<!---->

</unit></xbrl>

Meaning: `  <xbrl>  ` holds namespace prefix definitions and the ` @schemaLocation` attribute.

### 4.1.1 The @id attribute on <xbrl> elements (optional)

The `  <xbrl>  ` element **MAY** have an ` @id` attribute. The value of the ` @id` attribute **MUST** conform to the [\[XML\]](#XML) rules for attributes with the ID type ([http://www.w3.org/TR/REC-xml#NT-TokenizedType](http://www.w3.org/TR/REC-xml#NT-TokenizedType)).

### 4.1.2 The @xml:base attribute on <xbrl> elements (optional)

The `  <xbrl>  ` element **MAY** have an ` @xml:base` attribute. The ` @xml:base` attribute `[XML Base]` **MAY** appear on the `  <xbrl>  ` element, participating in the resolution of relative URIs in the [XBRL Instance](#XBRL-instance).

## 4.2 The <schemaRef> element in XBRL Instances

Every [XBRL Instance](#XBRL-instance) **MUST** contain at least one `  <schemaRef>  ` element. The `  <schemaRef>  ` element is a simple link, as defined in [**Section 3.5.1**](#_3.5.1). The `  <schemaRef>  ` element **MUST** occur as a child element of an `  <xbrl>  ` element. All `  <schemaRef>  ` elements in an XBRL instance **MUST** occur before other children of the `  <xbrl>  ` element, in document order.

In an [XBRL Instance](#XBRL-instance), the `  <schemaRef>  ` element points to a [Taxonomy Schema](#taxonomy-schema) that becomes part of the [DTS](#DTS) supporting that XBRL instance.

**NOTE**: XBRL instance creators should be aware that, if there are inconsistencies between the information conveyed by a `schemaRef ` element and that conveyed by ` @schemaLocation` attributes elsewhere in the instance, processors may have difficulty processing the instance correctly.

The XML Schema definition of the `  <schemaRef>  ` element is shown below.

<schema  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/XLink" elementFormDefault="qualified" attributeFormDefault="unqualified"><complexType name="simpleType"><documentation>

Type for the simple links defined in XBRL

</documentation><restriction base="anyType">

<attributeGroup ref="xlink:simpleType"/>

<attribute ref="xlink:href" use="required"/>

<attribute ref="xlink:arcrole" use="optional"/>

<attribute ref="xlink:role" use="optional"/>

<attribute ref="xlink:title" use="optional"/>

<attribute ref="xlink:show" use="optional"/>

<attribute ref="xlink:actuate" use="optional"/>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></complexType></schema>

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><documentation>

Definition of the schemaRef element - used to link to XBRL taxonomy schemas from XBRL instances.

</documentation></schema>

### 4.2.1 The @xlink:type attribute on <schemaRef> elements

The ` @xlink:type` attribute **MUST** occur and **MUST** have the fixed content " `simple` ".

### 4.2.2 The @xlink:href attribute on <schemaRef> elements

A `  <schemaRef>  ` element **MUST** have an ` @xlink:href` attribute. The ` @xlink:href` attribute **MUST** be a URI. The URI **MUST** point to an XML Schema. If the URI reference is relative, its absolute version **MUST** be determined as specified in [\[XML Base\]](#XMLBASE) before use. For details on the allowable forms of XPointer [\[XPOINTER\]](#XPOINTER) syntax in the URI see [**Section 3.5.4**](#_3.5.4).

### 4.2.3 The @xlink:arcrole attribute on <schemaRef> elements (optional)

The ` @xlink:arcrole` attribute **MAY** be used on the `  <schemaRef>  ` element. It is given no semantics by this specification. The ` @xlink:arcrole` attribute value **MUST** be a URI value as defined by the [\[XLINK\]](#XLINK) specification.

### 4.2.4 The @xlink:role attribute on <schemaRef> elements (optional)

The ` @xlink:role` attribute **MAY** be used on the `  <schemaRef>  ` element. No semantics are defined for the ` @xlink:role` attribute when it occurs on the `  <schemaRef>  ` element. The ` @xlink:role` attribute value **MUST** be a URI value as defined by the [\[XLINK\]](#XLINK) specification.

### 4.2.5 The @xml:base attribute on <schemaRef> elements (optional)

The ` @xml:base` attribute `[XML Base]` **MAY** appear on `  <schemaRef>  ` elements, participating in the resolution of relative URIs specified in their ` @xlink:href` attributes.

## 4.3 The <linkbaseRef> element in XBRL instances

The [\[XLINK\]](#XLINK) specification provides for a standard way of finding [Linkbases](#linkbase) (see [http://www.w3.org/TR/xlink/#xlg](http://www.w3.org/TR/xlink/#xlg)). The `  <linkbaseRef>  ` element conforms to this standard by using a specific ` @xlink:arcrole` content value (see [**Section 4.3.3**](#_4.3.3)).

One or more `  <linkbaseRef>  ` elements **MAY** occur as children of the `  <xbrl>  ` element (They **MAY** also occur in [Taxonomy Schemas](#taxonomy-schema). See [**Section 5.1.2**](#_5.1.2) for details). If `  <linkbaseRef>  ` elements occur as children of `  <xbrl>  ` elements, they **MUST** follow the `  <schemaRef>  ` elements and precede all other elements, in document order.

In an [XBRL Instance](#XBRL-instance), the `  <linkbaseRef>  ` element identifies a [Linkbase](#linkbase) that becomes part of the [DTS](#DTS) supporting that XBRL instance.

The XML Schema constraints applying to the `  <linkbaseRef>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><element name="linkbaseRef" substitutionGroup="xl:simple"><documentation>

Definition of the linkbaseRef element - used to link to XBRL taxonomy extended links from taxonomy schema documents and from XBRL instances.

</documentation><restriction base="xl:simpleType"><documentation>

This attribute must have the value: http://www.w3.org/1999/xlink/properties/linkbase

</documentation>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></element></schema>

### 4.3.1 The @xlink:type attribute on <linkbaseRef> elements

The ` @xlink:type` attribute **MUST** occur and **MUST** have the fixed content " `simple` ".

### 4.3.2 The @xlink:href attribute on <linkbaseRef> elements

A `  <linkbaseRef>  ` element **MUST** have an ` @xlink:href` attribute. The ` @xlink:href` attribute **MUST** be a URI. The URI **MUST** point to a [Linkbase](#linkbase) (as defined in [**Section 3.5.2**](#_3.5.2)) that contains the appropriate [Extended Links](#extended-link), as determined by the value of the ` @xlink:role` attribute. If the URI reference is relative, its absolute version **MUST** be determined as specified in [\[XML Base\]](#XMLBASE) before use. For details on the allowable forms of XPointer [\[XPOINTER\]](#XPOINTER) syntax in the URI see [**Section 3.5.4**](#_3.5.4).

### 4.3.3 The @xlink:arcrole attribute on <linkbaseRef> elements

The ` @xlink:arcrole` attribute on the `  <linkbaseRef>  ` element **MUST** have the [\[XLINK\]](#XLINK) - specified fixed content:

`http://www.w3.org/1999/xlink/properties/linkbase`

### 4.3.4 The @xlink:role attribute on <linkbaseRef> elements (optional)

The optional ` @xlink:role` attribute constrains the kinds of [Extended Links](#extended-link) that are permitted within the [Linkbase](#linkbase) identified by the `  <linkbaseRef>  ` element. Table 2 sets out the standard ` @xlink:role` attribute values for the ` @xlink:role` attribute when it occurs on the `  <linkbaseRef>  ` element. Table 2 also documents which kinds of extended links:

- **MUST** be contained by the [Linkbase](#linkbase) connected to by a `  <linkbaseRef>  ` element with each of the standard ` @xlink:role` attribute values; and
- **MUST NOT** be contained by the [Linkbase](#linkbase) connected to by a `  <linkbaseRef>  ` element with each of the standard ` @xlink:role` attribute values.

If a `  <linkbaseRef>  ` element connects to a [Linkbase](#linkbase) containing an [Extended Link](#extended-link) that has not been defined in this specification, then a non-standard value of the ` @xlink:role` attribute **MAY** be used or the ` @xlink:role` attribute **MAY** be omitted.

Table 2: Roles in the linkbaseRef element

| Values of the `  <linkbaseRef>  ` ` @xlink:role` attribute | Element pointed to by ` @xlink:href` |
| --- | --- |
| `(unspecified)` | **MAY** contain any [Extended Link](#extended-link) elements |
| `http://www.xbrl.org/2003/role/calculationLinkbaseRef` | **MUST** contain only `  <calculationLink>  ` elements |
| `http://www.xbrl.org/2003/role/definitionLinkbaseRef` | **MUST** contain only `  <definitionLink>  ` elements |
| `http://www.xbrl.org/2003/role/labelLinkbaseRef` | **MUST** contain only `  <labelLink>  ` elements |
| `http://www.xbrl.org/2003/role/presentationLinkbaseRef` | **MUST** contain only `  <presentationLink>  ` elements |
| `http://www.xbrl.org/2003/role/referenceLinkbaseRef` | **MUST** contain only `  <referenceLink>  ` elements |

### 4.3.5 The @xml:base attribute on <linkbaseRef> elements (optional)

The ` @xml:base` attribute `[XML Base]` **MAY** appear on `  <linkbaseRef>  ` elements, participating in the resolution of relative URIs specified in their ` @xlink:href` attributes.

## 4.4 The <roleRef> element in XBRL instances (optional)

One or more `  <roleRef>  ` elements (defined in [**Section 3.5.2.4**](#_3.5.2.4)) **MAY** be used in [XBRL Instances](#XBRL-instance). If used, they **MUST** appear immediately after the `  <linkbaseRef>  ` elements in the XBRL instance, in document order. `  <roleRef>  ` elements are used in XBRL instances to reference the definitions of any custom ` @xlink:role` attribute values used in footnote links in the XBRL instance.

## 4.5 The <arcroleRef> element in XBRL instances (optional)

One or more `  <arcroleRef>  ` elements (defined in [**Section 3.5.2.5**](#_3.5.2.5)) **MAY** be used in [XBRL Instances](#XBRL-instance). If used, they **MUST** appear immediately after the `  <roleRef>  ` elements in the XBRL instance, in document order. `  <arcroleRef>  ` elements are used in XBRL instances to reference the definitions of any custom ` @xlink:arcrole` attribute values used in footnote links in the XBRL instance.

## 4.6 Items

As discussed in [**Section 3**](#_3) above, an [Item](#item) represents a single fact or business measurement. In the XML Schema for XBRL instances, item is defined as an [Abstract Element](#abstract-element). This means that it will never appear in its own right in an [XBRL Instance](#XBRL-instance). Therefore, all elements representing single facts or business measurements defined in an XBRL taxonomy document and reported in an XBRL instance **MUST** be either (a) members of the substitution group item; or, (b) members of a substitution group originally based on item. XBRL taxonomies include [Taxonomy Schemas](#taxonomy-schema) that contain such element definitions. `  <item>  ` elements might need to be referenced from elsewhere (such as from a footnote) therefore taxonomy authors **SHOULD NOT** prohibit the ` @id` attribute inherited from the base XBRL item type.

`  <item>  ` elements **MUST NOT** be descendants of other `  <item>  ` elements. Structural relationships necessary in an [XBRL Instance](#XBRL-instance) **MUST** be captured only using [Tuples](#tuple) (see [**Section 4.9**](#_4.9)). The intellectual structure - the relationship of financial [Concepts](#concept) to each other in a variety of senses - is captured by the link structure of taxonomy [Linkbases](#linkbase) rather than by nesting of facts in XBRL instances.

The XML Schema definition of the item element and the data types for elements in the item substitution group are given below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><attributeGroup name="factAttrs"><documentation>

Attributes for all items and tuples.

</documentation>

<attribute name="id" type="ID" use="optional"/>

<anyAttribute namespace="##other" processContents="lax"/>

</attributeGroup><attributeGroup name="tupleAttrs"><documentation>

Group of attributes for tuples.

</documentation>

<attributeGroup ref="xbrli:factAttrs"/>

</attributeGroup><attributeGroup name="itemAttrs"><documentation>

Attributes for all items.

</documentation>

<attributeGroup ref="xbrli:factAttrs"/>

<attribute name="contextRef" type="IDREF" use="required"/>

</attributeGroup><attributeGroup name="essentialNumericItemAttrs"><documentation>

Attributes for all numeric items (fractional and non-fractional).

</documentation>

<attributeGroup ref="xbrli:itemAttrs"/>

<attribute name="unitRef" type="IDREF" use="required"/>

</attributeGroup><attributeGroup name="numericItemAttrs"><documentation>

Group of attributes for non-fractional numeric items

</documentation>

<attributeGroup ref="xbrli:essentialNumericItemAttrs"/>

<attribute name="precision" type="xbrli:precisionType" use="optional"/>

<attribute name="decimals" type="xbrli:decimalsType" use="optional"/>

</attributeGroup><attributeGroup name="nonNumericItemAttrs"><documentation>

Group of attributes for non-numeric items

</documentation>

<attributeGroup ref="xbrli:itemAttrs"/>

</attributeGroup><documentation>

XBRL domain numeric item types - for use on concept element definitions The following 4 numeric types are all types that have been identified as having particular relevance to the domain space addressed by XBRL and are hence included in addition to the built-in types from XML Schema.

</documentation><extension base="xbrli:monetary">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="xbrli:shares">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="xbrli:pure">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension>

<element name="numerator" type="decimal"/>

<element name="denominator" type="xbrli:nonZeroDecimal"/>

<complexType name="fractionItemType" final="extension"><sequence>

<element ref="xbrli:numerator"/>

<element ref="xbrli:denominator"/>

</sequence>

<attributeGroup ref="xbrli:essentialNumericItemAttrs"/>

</complexType><extension base="string">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension>

<!---->

<documentation>

Abstract item element used as head of item substitution group

</documentation></schema>

Example 9: A numeric fact with three significant digits

<ci:capitalLeases contextRef="c1" unitRef="u1" precision="3">727432</ci:capitalLeases>

Meaning: The value of Capital Leases in the numeric context labelled c1 is 727000 accurate to 3 significant figures. Note that it will be necessary to consult the context (defined below) in order to determine other details concerning the value such as [Entity](#entity), [Period](#period), etc. and it will be necessary to consult the referenced `  <unit>  ` element to determine the relevant [Unit](#unit) information.

Example 10: A non-numeric item

<ci:concentrationsNote contextRef="c1"> Concentration of credit risk with regard to short term investments is not considered to be significant due to the Company's cash management policies. These policies restrict investments to low risk, highly liquid securities (that is, commercial paper, money market instruments, etc.), outline issuer credit requirements, and limit the amount that may be invested in any one issuer. </ci:concentrationsNote>

Meaning: The text of the Concentrations note in the context labelled c1.

The content of the abstract `  <item>  ` element is derived from `anyType`. Each member of the substitution group of `  <item>  ` must have a defined XBRL item type. This allows each substitution for `  <item>  ` in the instance to validate against its own data type. There is one defined XBRL item type derived from each of the appropriate built-in types of XML Schema, along with the `fractionItemType` type. The complete list is in [**Section 5.1.1.3**](#_5.1.1.3). An item **MUST NOT** have complex content unless its item type is derived by restriction from `fractionItemType`.

The ` @contextRef` attribute is an `IDREF` to the `  <context>  ` element (see [**Section 4.7**](#_4.7)) that holds additional relevant information about the fact represented. An item **MUST** contain a ` @contextRef` attribute that references a `  <context>  ` element in the same XBRL instance. Note that an [XBRL Instance](#XBRL-instance) is an occurrence of the `  <xbrl>  ` element, not the entire document. Items whose content is derived from an XML Schema built-in numeric type (`decimal`, `float` or double or a built-in type derived from one of them) or `fractionItemType` by restriction **MUST** use the ` @contextRef` attribute and the ` @unitRef` attribute; all others **MUST** use the ` @contextRef` attribute.

The ` @unitRef` attribute is an `IDREF` to the `  <unit>  ` element (see [**Section 4.8**](#_4.8)) that holds information about [Units](#unit) in which numeric facts have been measured. The ` @unitRef` attribute **MUST NOT** occur in [Non-Numeric Items](#non-numeric-item). The ` @unitRef` attribute **MUST** occur in [Numeric Items](#numeric-item), referencing a `  <unit>  ` element in the same XBRL instance.

Two optional attributes, ` @precision` and ` @decimals`, are available on [Numeric Items](#numeric-item) (except those with type `fractionItemType`) to enable the XBRL instance creator to make statements about the accuracy of the facts represented. They are discussed in the following sections.

### 4.6.1 The @contextRef attribute

All items **MUST** have a context. All [Tuples](#tuple) **MUST NOT** have a context. Items identify their contexts using the ` @contextRef` attribute. The ` @contextRef` attribute is used to identify the `  <context>  ` element that is associated with the item on which the ` @contextRef` attribute occurs.

The value of the ` @contextRef` attribute **MUST** be equal to the value of an ` @id` attribute on a `  <context>  ` element in the [XBRL Instance](#XBRL-instance) that contains the item on which the ` @contextRef` attribute occurs.

### 4.6.2 The @unitRef attribute

All [Numeric Items](#numeric-item) **MUST** have a statement of the [Units](#unit) of measurement. All [Tuples](#tuple) and all [Non-Numeric Items](#non-numeric-item) **MUST NOT** have a statement of the units of measurement. Numeric items identify their units using the ` @unitRef` attribute. The ` @unitRef` attribute is used to identify the `  <unit>  ` element that is associated with the item on which the ` @unitRef` attribute occurs.

The value of the ` @unitRef` attribute **MUST** be equal to the value of an ` @id` attribute on a `  <unit>  ` element in the [XBRL Instance](#XBRL-instance) that contains the [Numeric Item](#numeric-item) on which the ` @unitRef` attribute occurs.

### 4.6.3 Usage of @precision and @decimals attributes

A [Numeric Item](#numeric-item) **MUST** have either a ` @precision` attribute or a ` @decimals` attribute unless it is of the `fractionItemType` or of a type that is derived by restriction from `fractionItemType or has a nil value,` in which case, it **MUST NOT** have either a ` @precision` attribute or a ` @decimals` attribute.

A [Numeric Item](#numeric-item) **MUST NOT** have both a ` @precision` attribute and a ` @decimals` attribute.

A [Non-Numeric Item](#non-numeric-item) **MUST NOT** have either a ` @precision` or a ` @decimals` attribute.

When determining whether two [Numeric Items](#numeric-item) are [V-Equal](#v-equal) (a predicate that is used in the definition of various other equality type predicates) it is necessary to take into consideration the values of ` @precision` (or the precision inferred from the value of the ` @decimals` attribute) for the two numeric items. The formal definition of V-Equal for two numeric items is given in [**Section 4.10**](#_4.10).

### 4.6.4 The @precision attribute (optional)

The ` @precision` attribute **MUST** be a non-negative integer or the string " `INF` " that conveys the arithmetic precision of a measurement, and, therefore, the utility of that measurement to further calculations. Different software packages may claim different levels of accuracy for the numbers they produce. The ` @precision` attribute allows any producer to state the precision of the output in the same way. If a numeric fact has a ` @precision` attribute that has the value "n" then it is correct to "n" significant figures (see [**Section 4.6.1**](#_4.6.1) for the normative definition of 'correct to "n" significant figures'). An application **SHOULD** ignore (i.e. replace with zeroes) any digits after the first " *n* " decimal digits, counting from the left, starting at the first non-zero digit in the lexical representation of any number for which the value of precision is specified or inferred to be *n*.

The meaning of `precision="INF"` is that the lexical representation of the number is the exact value of the fact being represented.

**NOTE:** The definitions in this specification mean that ` @precision` and by inference, ` @decimals` indicate the range in which the actual value of the fact that gave rise to its expressed value in the [XBRL Instance](#XBRL-instance) lies.

Example 11: Precision and lexical representation

| Example | Meaning |
| --- | --- |
| `precision="9"` | Precision of nine digits. The first 9 digits, counting from the left, starting at the first non-zero digit in the lexical representation of the value of the numeric fact are known to be trustworthy for the purposes of computations to be performed using that numeric fact. |

| Precision | Example of lexical representation in the XBRL instance | Read as (after omitting or zeroing any spurious digits) | Known to be GE | Known to be LT |
| --- | --- | --- | --- | --- |
| INF | 476.334 | 476.334 | 476.334 | 476.33400000000…1 |
| 3 | 205 | 205e0 | 204.5 | 205.5 |
| 4 | 2002000 | 2002e3 | 2001500 | 2002500 |
| 4 | \-2002000 | \-2002e3 | \-2002500 | 2001500 |
| 2 | 2012 | 20e2 | 1950 | 2050 |
| 2 | 2000 | 20e2 | 1950 | 2050 |
| 1 | 99 | 9e1 | 85 | 95 |
| 0 | 1234 | 1234 | unknown | unknown |

The simple type `precisionType` has been provided to define the value space for the value of the ` @precision` attribute. Its definition is as follows:

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><simpleType name="precisionType"><documentation>

This type is used to specify the value of the precision attribute on numeric items. It consists of the union of nonNegativeInteger and "INF" (used to signify infinite precision or "exact value").

</documentation><restriction base="string">

<enumeration value="INF"/>

</restriction></simpleType></schema>

### 4.6.5 The @decimals attribute (optional)

The ` @decimals` attribute **MUST** be an integer or the value " `INF` " that specifies the number of decimal places to which the value of the fact represented may be considered accurate, possibly as a result of rounding or truncation. If a numeric fact has a ` @decimals` attribute with the value "n" then it is known to be correct to "n" decimal places. (See [**Section 4.6.7.2**](#_4.6.7.2) for the normative definition of 'correct to "n" decimal places').

The meaning of `decimals="INF"` is that the lexical representation of the number is the exact value of the fact being represented.

Example 12: Decimals and lexical representation

| Example | Meaning |
| --- | --- |
| `decimals="2"` | The value of the numeric fact is known to be correct to 2 decimal places. |
| `decimals="-2"` | The value of the numeric fact is known to be correct to -2 decimal places, i.e. all digits to the left of the hundreds digit are accurate. |

| Decimals | Example of lexical representation in the XBRL instance | Read as (after omitting or zeroing any spurious digits) | Known to be GE | Known to be LT |
| --- | --- | --- | --- | --- |
| INF | 436.749 | 436.749 | 436.749 | 436.74900000…1 |
| 2 | 10.00 | 10.00 | 9.995 | 10.005 |
| 2 | 10 | 10.00 | 9.995 | 10.005 |
| 2 | 10.000 | 10.00 | 9.995 | 10.005 |
| 2 | 10.009 | 10.00 | 9.995 | 10.005 |
| 0 | 10 | 10. | 9.5 | 10.5 |
| \-1 | 10 | 10. | 5 | 15 |
| \-1 | 11 | 10. | 5 | 15 |
| 3 | 205 | 205.000 | 204.9995 | 205.0005 |
| 4 | 2002000 | 2002000.0000 | 2001999.99995 | 2002000.00005 |
| \-2 | \-205 | \-200. | \-250 | \-150 |
| \-2 | 205 | 200. | 150 | 250 |
| \-2 | 2002000 | 2002000. | 2001950 | 2002050 |
| \-3 | 2002000 | 2002000. | 2001500 | 2002500 |
| \-4 | 2002000 | 2000000. | 1995000 | 2005000 |
| \-3 | 777000 | 777000 | 776500 | 777500 |

The simple type `decimalsType` defines the legal values for the ` @decimals` attribute. Its XML Schema definition is as follows:

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><simpleType name="decimalsType"><documentation>

This type is used to specify the value of the decimals attribute on numeric items. It consists of the union of integer and "INF" (used to signify that a number is expressed to an infinite number of decimal places or "exact value").

</documentation><restriction base="string">

<enumeration value="INF"/>

</restriction></simpleType></schema>

### 4.6.6 Inferring decimals

The following rules enable [XBRL Instance](#XBRL-instance) consumers to infer a value for the ` @decimals` attribute of a [Numeric Item](#numeric-item) when none is supplied.

For a [Numeric Item](#numeric-item) of type `fractionItemType` or type derived by restriction from `fractionItemType`, a consuming application **MUST** infer the precision to be equal to 'INF' if it is to be used in calculations.

If, on a [Numeric Item](#numeric-item), the ` @precision` attribute is present rather than the ` @decimals` attribute, then a consuming application **MUST** infer the decimals of that numeric fact if it is to be used in calculations or searches for duplicates in [XBRL Instances](#XBRL-instance).

If the value of the ` @precision` attribute of a [Numeric Item](#numeric-item) is equal to 0, nothing is known about the precision of the number, nothing can be inferred about decimals, and thus any consuming [V-Equals](#v-equal) comparison must be false, and any calculation link summation involving the item must be inconsistent.

If the value of the ` @precision` attribute is INF then the inferred decimals value is INF.

If the value of the ` @precision` attribute is not INF and greater than 0 then the decimals value is

- For an item of numeric value 0, the inferred decimals is deemed to be INF, treating data values of zero as a singularity of infinite decimals accuracy (regardless of non-zero value of ` @precision` attribute or item syntax, e.g., 0, or 000, or.00).
- Otherwise the inferred decimals is given by the following expression: precision - int(floor(log10(abs(number(item))))) - 1, where precision is the value of the ` @precision` attribute, int( ) a function returning an integer of its argument, floor( ) a function returning the largest integer less than or equal to its argument, log10( ) a function returning the logarithm base 10 of its argument, abs( ) a function returning the absolute value of its argument, number( ) a function providing a numeric conversion if its argument is not internally numeric (as may be needed for the math computations), and item is the item's value ([PSVI](http://www.w3.org/TR/xmlschema-1/#key-psvi) typed numeric node value if available, or otherwise inner text of numeric item node).

Example 13: Lexical representation, precision and decimals

| Lexical Representation | Value of the decimals attribute | Inferred value of the ` @precision` attribute |
| --- | --- | --- |
| 123 | 2 | 3+2=5 |
| 123.4567 | 2 | 3+2=5 |
| 123e5 | \-3 | 3+5+(-3)=5 |
| 123.45e5 | \-3 | 3+5+(-3)=5 |
| 0.1e-2 | 5 | 0+(-2)+5=3 |
| 0.001E-2 | 5 | (-2)+(-2)+5=1 |
| 0.001e-3 (this is a pathological case) | 4 | (-2)+(-3)+4=-1 which is less than 0 and hence 0 |

### 4.6.7 Definitions pertaining to accuracy

The following definitions are provided for clarity regarding accuracy-related features of this specification, i.e. ` @precision` and ` @decimals` attributes.

#### 4.6.7.1 "Correct to n Significant Figures", "Rounding" and "Truncation"

If the lexical representation of the value of a number is said to be correct to *n* significant figures it means that the first " *n* " decimal digits, counting from the left, starting at the first non-zero digit in the lexical representation of the number are known to be accurate for the purposes of computations to be performed using that number. (Note: in the following it is assumed that all zeros to the left of the decimal point and to the left of the first non-zero digit in the decimal representation have been removed first).

More precisely: in the decimal representation of a number, a significant figure is any one of the digits 1, 2, 3...9 that specify the magnitude of a number. Zero (0) is a significant figure except when it appears to the left of all non-zero digits or is used solely to fill the places of unknown or discarded digits (after truncation or rounding - see later). Thus, in the number "0.00263", there are three significant figures: 2, 6, and 3. The zeroes are not significant. In the number "3809" all four of the digits are significant. In the number "46300" the digits 4, 6, and 3 are known to be significant but it is not possible to conclude anything concerning the two zeroes as they are written. This ambiguity can be removed by writing the number in terms of powers of ten. If there are three significant figures the representation becomes 4.63 × 10 <sup>4</sup>; if there are four significant figures it becomes 4.630 × 10 <sup>4</sup>, etc.

It is often necessary to round significant figures following a calculation. This is known as **rounding** [\[IEEE\]](#IEEE) \[IEEE 4.3.1 Rounding-direction attributes to nearest, roundTiesToEven\]. To round a number to *n* significant figures, discard all digits to the right of the *n* th place. This step is known as **truncation**. Then, if the original number is equally near two truncated numbers, the one with an even *n* th digit is chosen. For example:

Example 14: Rounding

<table><tbody><tr><th>Original</th><th colspan="2">Rounded to <em>n</em> significant figures</th></tr><tr><td></td><td><p><em>n=2</em></p></td><td><p><em>n=3</em></p></td></tr><tr><td><p>3.5643</p></td><td><p>3.6</p></td><td><p>3.56</p></td></tr><tr><td><p>3.5673</p></td><td><p>3.6</p></td><td><p>3.57</p></td></tr><tr><td><p>0.49787</p></td><td><p>0.50</p></td><td><p>0.498</p></td></tr><tr><td><p>3.9999</p></td><td><p>4.0</p></td><td><p>4.00</p></td></tr><tr><td><p>9.999991</p></td><td><p>10</p></td><td><p>10.0</p></td></tr><tr><td><p>22.55</p></td><td><p>23</p></td><td><p>22.6†</p></td></tr><tr><td><p>22.65</p></td><td><p>23</p></td><td><p>22.6†</p></td></tr><tr><td><p>0.0019</p></td><td><p>0.0019</p></td><td><p>0.00190</p></td></tr><tr><td><p>0.00002</p></td><td><p>0.000020</p></td><td><p>0.0000200</p></td></tr><tr><td colspan="3"><p>† example of roundTiesToEven</p></td></tr></tbody></table>

The same procedure **MAY** be followed for any value of *n*, and we then say that a particular lexical representation of the value of a number is **correct to *n* significant figures**. It is possible that this technique has been used to create the lexical representation of a fact in an [XBRL Instance](#XBRL-instance) with a ` @precision` attribute of *n*.

#### 4.6.7.2 "Correct to n Decimal Places"

If the representation of a number is **correct to *n* decimal places** then

the number is rounded according to [\[IEEE\]](#IEEE) \[IEEE 4.3.1 Rounding-direction attributes to nearest, roundTiesToEven\].

Rounding, as described earlier, might have been used to make a number correct to exactly *n* decimal places for inclusion in an [XBRL Instance](#XBRL-instance) with a ` @decimals` attribute of *n*. The following table shows the representations of the number 123456.789012 correct to various numbers of decimal places, and examples of *roundTiesToEven*:

Example 15: Correct to *n* decimal places

<table><tbody><tr><td colspan="5">123456.789012 correct to <em>n</em> decimal places</td></tr><tr><td><p><em>n</em> =-3</p></td><td><p><em>n</em> =-2</p></td><td><p><em>n</em> =0</p></td><td><p><em>n</em> =3</p></td><td><p><em>n</em> =6</p></td></tr><tr><td><p>123000</p></td><td><p>123500</p></td><td><p>123457</p></td><td><p>123456.789</p></td><td><p>123456.789012</p></td></tr><tr><td colspan="5">123450 correct to <em>n</em> decimal places</td></tr><tr><td><p>123000</p></td><td><p>123400†</p></td><td><p>123450</p></td><td><p>123450.000</p></td><td><p>123450.000000</p></td></tr><tr><td colspan="5">123550 correct to <em>n</em> decimal places</td></tr><tr><td><p>124000</p></td><td><p>123600†</p></td><td><p>123550</p></td><td><p>123550.000</p></td><td><p>123550.000000</p></td></tr><tr><td colspan="5"><p>†- example of roundTiesToEven</p></td></tr></tbody></table>

## 4.7 The <context> element

The `  <context>  ` element contains information about the [Entity](#entity) being described, the reporting [Period](#period) and the reporting scenario, all of which are necessary for understanding a business fact captured as an XBRL item.

The `  <context>  ` element **MUST** conform to the following XML Schema constraints:

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><element name="context"><documentation>

Used for an island of context to which facts can be related.

</documentation><complexType><sequence>

<element name="entity" type="xbrli:contextEntityType"/>

<element name="period" type="xbrli:contextPeriodType"/>

<element name="scenario" type="xbrli:contextScenarioType" minOccurs="0"/>

</sequence>

<attribute name="id" type="ID" use="required"/>

</complexType></element></schema>

In the examples provided in the following sub-sections, the `xsi:schemaLocation` attribute does not contain URIs to resolve the ISO4217 and NASDAQ namespaces. In the case of NASDAQ the examples assume that the applications that produced and will consume this instance will be able to resolve this namespace reference without the help of the `xsi:schemaLocation`. The ISO4217 namespace does not refer to an XML Schema that can be used for validation of the [XBRL Instances](#XBRL-instance) shown in the examples. The ISO4217 and NASDAQ URIs do not reference actual resources of the ISO or NASDAQ.

### 4.7.1 The @id attribute

Every `  <context>  ` element **MUST** include the ` @id` attribute. The content of the ` @id` attribute **MUST** conform to the [\[XML\]](#XML) rules for attributes with the ID type ([http://www.w3.org/TR/REC-xml#NT-TokenizedType](http://www.w3.org/TR/REC-xml#NT-TokenizedType)). The ` @id` attribute identifies the context (see [**Section 4.7**](#_4.7)) so that it may be referenced by item elements.

Example 16: IDs

| Example | id="C2424" |  |
| --- | --- | --- |
| Counterexample | id="42" | Content of the ID type must not begin with a number. |

### 4.7.2 The <period> element

The [Period](#period) element contains the instant or interval of time for reference by an `  <item>  ` element. The sub-elements of period are used to construct one of the allowed choices for representing date intervals.

| Elements | Meaning |
| --- | --- |
| `startDate`, `endDate` | A period beginning and ending as specified. |
| `instant` | A point in time. |
| `forever` | An element to represent 'forever'. |

Each of the [Period](#period) sub-elements uses a standard XML Schema representation of a date.

The XML Schema constraints on the `  <period>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><simpleType name="dateUnion"><documentation>

The union of the date and dateTime simple types.

</documentation>

<union memberTypes="date dateTime"/>

</simpleType><complexType name="contextPeriodType"><documentation>

The type for the period element, used to describe the reporting date info.

</documentation><choice><sequence>

<element name="startDate" type="xbrli:dateUnion"/>

<element name="endDate" type="xbrli:dateUnion"/>

</sequence>

<element name="instant" type="xbrli:dateUnion"/>

<element name="forever">

<complexType/>

</element></choice></complexType></schema>

| Sub-element | XML Schema data type |
| --- | --- |
| `instant` | `date` or `dateTime` |
| `forever` | `empty` |
| `startDate` | `date` or `dateTime` |
| `endDate` | `date` or `dateTime` |

While the content of the `instant`, `startDate` and `endDate` elements are defined to use the data representation defined by ISO 8601 (as restricted by [\[XML Schema Datatypes\]](#XMLSCHEMA-DATATYPES)), XBRL adds further restrictions and constraints.

For an item element with `periodType="instant" (`See [**Section 5.1.1.1**](#_5.1.1.1)), the `  <period>  ` **MUST** contain an `instant` element.

For an item element with `periodType="duration"`, the [Period](#period) **MUST** contain `forever` or a valid sequence of `startDate` and `endDate`.

A `date`, with no `time` part, in the content of an `startDate` element is defined to be equivalent to specifying a `dateTime` of the same `date`, and `T00:00:00` (midnight at the start of the day).

A `date`, with no `time` part, in the `endDate` or `instant` element is defined to be equivalent to specifying a `dateTime` of the same `date` `plus` ` P1D` and with a time part of `T00:00:00.` This represents midnight at the end of the day. The reason for defining it thus, i.e. as midnight at the start of the next day, is that [\[XML Schema Datatypes\]](#XMLSCHEMA-DATATYPES) mandates this representation by prohibiting the value of 24 in the "hours" part of a time specification, which is ISO 8601 syntax.

If supplied, the `endDate` **MUST** specify or imply a point in time that is later than the specified or implied point in time of the corresponding `startDate`.

### 4.7.3 The <entity> element

The `  <entity>  ` element documents the [Entity](#entity) (business, government department, individual, etc.) that fact describes. The `  <entity>  ` element is required content of the `  <context>  ` element. The `  <entity>  ` element **MUST** contain an `  <identifier>  ` element and **MAY** contain a `  <segment>  ` element.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><complexType name="contextEntityType"><documentation>

The type for the entity element, used to describe the reporting entity. Note that the scheme attribute is required and cannot be empty.

</documentation><sequence><restriction base="anyURI">

<minLength value="1"/>

</restriction>

<element ref="xbrli:segment" minOccurs="0"/>

</sequence></complexType></schema>

#### 4.7.3.1 <identifier>

An `  <identifier>  ` element specifies a ` @scheme` for identifying business entities. The required ` @scheme` attribute contains the namespace URI of the identification ` @scheme`, providing a framework for referencing naming authorities. The element content **MUST** be a `token` that is a valid identifier within the namespace referenced by the ` @scheme` attribute. XBRL International is not a naming authority for business entities. XBRL makes no assumption about the ability of an application to resolve an identifier that may appear as element content in any particular scheme.

Example 17: Entity identifiers

| Example | Meaning |
| --- | --- |
| <identifier scheme="http://www.nasdaq.com">SAMP</identifier> | The company with NASDAQ ticker symbol SAMP. |
| <identifier scheme="http://www.dnb.com">121064880</identifier> | The company or subsidiary with D-U-N-S number 121064880. |
| <identifier scheme="http://www.cusip.org">41009876AB</identifier> | The [Entity](#entity) with CUSIP number 41009876AB (e.g. a mutual fund). |
| <identifier scheme="http://www.ietf.org/URI">www.w3c.org</identifier> | The non-profit organisation owning the URI www.w3c.org. |

#### 4.7.3.2 The <segment> element (optional)

The `  <segment>  ` element is an optional container for additional mark-up that the preparer of an [XBRL Instance](#XBRL-instance) **SHOULD** use to identify the business segment more completely in cases where the [Entity](#entity) identifier is insufficient. In general, the content of a `  <segment>  ` will be specific to the purpose of the XBRL instance. Elements contained by the `  <segment>  ` element MUST NOT be defined in the `http://www.xbrl.org/2003/instance` namespace. Also, they **MUST NOT** be in the substitution group for elements defined in the `http://www.xbrl.org/2003/instance` namespace. The `  <segment>  ` element **MUST NOT** be empty.

The XML Schema restrictions on the `  <segment>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><sequence>

<any namespace="##other" processContents="lax" minOccurs="1" maxOccurs="unbounded"/>

</sequence></schema>

Example 18: Using the segment element

<xbrl  
xmlns:ci="http://www.xbrl.org/us/gaap/ci/2003/usfr-ci-2003"  
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"  
xmlns:s="http://mycompany.com/xbrl/taxonomy"  
xmlns:xbrli="http://www.xbrl.org/2003/instance"  
xmlns:xlink="http://www.w3.org/1999/xlink"  
xmlns:my="http://www.someCompany.com/segment"  
xmlns:xl="http://www.xbrl.org/2003/XLink"  
xmlns="http://www.xbrl.org/2003/instance" xsi:schemaLocation="http://www.someCompany.com/segment http://www.someCompany.com/segment/segment-schema.xsd">

<!---->

<!---->

<context id="c1"><entity>

<!---->

<identifier scheme="http://www.dnb.com">121064880</identifier>

<!---->

<segment>

<my:stateProvince>MI</my:stateProvince>

</segment></entity><period>

<instant>2002-12-01</instant>

</period></context></xbrl>

<!---->

<schema  
xmlns="http://www.w3.org/2001/XMLSchema"  
xmlns:my="http://www.someCompany.com/segment" targetNamespace="http://www.someCompany.com/segment" elementFormDefault="qualified"><restriction base="token">

<enumeration value="MI"/>

<enumeration value="ON"/>

</restriction>

<element name="stateProvince" type="my:stateProvinceType"/>

</schema>

Meaning: The preparer has used a `<segment>` to indicate that the business facts relate to operations in the state of Michigan. The company's own XML Schema document defines the `stateProvince` element as including just Michigan and Ontario.

Creators of taxonomies should anticipate that [XBRL Instance](#XBRL-instance) creators will define elements to insert in the segment element to represent one or more dimensions of distinction such as:

- Organisational structure, such as a the corporate headquarters and individual subsidiaries of an [Entity](#entity);
- Regional decomposition, such as operations in Asia, Europe, and North America;
- Functional distinctions, such as results from continuing and discontinued operations;
- Product distinctions, such as operations relating to fishing, forestry and farming;
- Operational distinctions such as recurring vs. non-recurring revenues or new subscriptions vs. renewals.

It is up to the preparer of the document to provide the proper namespace support and `xsi:schemaLocation` hints necessary to ensure that an XML Schema validation process properly validates the `  <segment>  ` element.

### 4.7.4 The <scenario> element (optional)

Business facts can be reported as actual, budgeted, restated, pro forma, etc. For internal reporting purposes, there can be an even greater variety of additional metadata that preparers want to associate with items. The optional `  <scenario>  ` element allows additional valid mark-up (see note above regarding segment) to be included for this purpose.

Elements contained by the `  <scenario>  ` element **MUST NOT** be defined in the `http://www.xbrl.org/2003/instance` namespace. Also, they **MUST NOT** be in the substitution group for elements defined in the `http://www.xbrl.org/2003/instance` namespace. The `  <scenario>  ` element **MUST NOT** be empty.

The XML Schema restrictions on the `  <scenario>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><complexType name="contextScenarioType"><documentation>

Used for the scenario under which fact have been reported.

</documentation><sequence>

<any namespace="##other" processContents="lax" minOccurs="1" maxOccurs="unbounded"/>

</sequence></complexType></schema>

Example 19: Use of the scenario element

<xbrl  
xmlns:fid="http://www.someInsuranceCo.com/scenarios"  
xmlns:other="http://www.example.com"  
xmlns:ci="http://www.xbrl.org/us/gaap/ci/2003/usfr-ci-2003"  
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"  
xmlns:s="http://mycompany.com/xbrl/taxonomy"  
xmlns:xbrli="http://www.xbrl.org/2003/instance"  
xmlns:xlink="http://www.w3.org/1999/xlink"  
xmlns:xl="http://www.xbrl.org/2003/XLink"  
xmlns="http://www.xbrl.org/2003/instance" xsi:schemaLocation="http://www.someInsuranceCo.com/scenarios http://www.someInsuranceCo.com/scenarios/scenarios-schema.xsd">

<!---->

<!---->

<context id="c1"><entity>

<identifier scheme="http://www.example.com">someInsuranceCo</identifier>

</entity><scenario>

<other:bestEstimate/>

<fid:dwSlice>

<fid:residence>MA</fid:residence>

<fid:nonSmoker>true</fid:nonSmoker>

<fid:minAge>34</fid:minAge>

<fid:maxAge>49</fid:maxAge>

</fid:dwSlice></scenario></context></xbrl>

Meaning: The preparer has used a <scenario> to indicate that the reported values relate to a "best estimate" scenario for non-smokers residing in Massachusetts of the specified age group.

It is up to the preparer of the instance to provide the proper namespace support and `xsi:schemaLocation` hints necessary to ensure that the `  <scenario>  ` element is properly validated by an XML Schema validation process.

The scenario and segment sub-elements have exactly the same structure, but are used for two different purposes. Segment is used to specify some component of the business [Entity](#entity). Scenario is used to document the circumstances surrounding the measurement of a set of facts, and like the `  <segment>  ` element, its content will be application specific.

Creators of business reporting taxonomies should anticipate that [XBRL Instance](#XBRL-instance) creators will define elements to insert in the `  <scenario>  ` element to represent dimensions of distinction such as:

- Assuming certain valuations of assets or future revenue streams;
- Actual, adjusted, estimated, forecasted, or reported as of a certain date;
- Assuming a particular foreign currency exchange rate.

## 4.8 The <unit> element

The `  <unit>  ` element specifies the [Units](#unit) in which a [Numeric Item](#numeric-item) has been measured. The content of the `  <unit>  ` element **MUST** be either a simple unit of measure expressed with a single `  <measure>  ` element or a ratio of products of units of measure, with the ratio represented by the `  <divide>  ` element and the numerator and denominator products both represented by a sequence of `  <measure>  ` elements.

Some examples of simple [Units](#unit) of measure are EUR (Euros), meters, kilograms and FTE (Full Time Equivalents). Some examples of complex units of measures are Earnings per Share and Square Feet.

The XML Schema restrictions on the `  <unit>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><documentation>

XML Schema components contributing to the unit element

</documentation>

<element name="measure" type="QName"/>

<complexType name="measuresType"><documentation>

A collection of sibling measure elements

</documentation><sequence>

<element ref="xbrli:measure" minOccurs="1" maxOccurs="unbounded"/>

</sequence></complexType><element name="divide"><documentation>

Element used to represent division in units

</documentation><sequence>

<element name="unitNumerator" type="xbrli:measuresType"/>

<element name="unitDenominator" type="xbrli:measuresType"/>

</sequence></element><element name="unit"><documentation>

Element used to represent units information about numeric items

</documentation><complexType><choice>

<element ref="xbrli:measure" minOccurs="1" maxOccurs="unbounded"/>

<element ref="xbrli:divide"/>

</choice>

<attribute name="id" type="ID" use="required"/>

</complexType></element></schema>

### 4.8.1 The @id attribute

Every `  <unit>  ` element **MUST** include an ` @id` attribute. The value of the ` @id` attribute **MUST** conform to the [\[XML\]](#XML) rules for attributes with the ID type ([http://www.w3.org/TR/REC-xml#NT-TokenizedType](http://www.w3.org/TR/REC-xml#NT-TokenizedType)). The ` @id` attribute identifies the [Unit](#unit) (see [**Section 4.8**](#_4.8)) so that it may be referenced by `  <item>  ` elements.

### 4.8.2 The <measure> element

The `  <measure>  ` element is of type `xsd:QName`.

Some facts have restrictions on the content of the `  <unit>  ` element and the value of the `  <measure>  ` element that is a consequence of the type of [Concept](#concept) they represent. These restrictions are set out in the following table.

Table 3: Unit restrictions based on item types.

| Item type | implies `  <unit>  ` **MUST** contain |
| --- | --- |
| `monetaryItemType` or derived from `monetaryItemType` | A single `xbrli:measure` element whose `xsd:QName` content is constrained as follows:  The (local part) of the `xsd:QName` **MUST** be an ISO 4217 currency designation [\[ISO\]](#ISO) that was valid during the time designated by the [Period](#period) element of the item's context. The (namespace name) of the `xsd:QName` **MUST** be `http://www.xbrl.org/2003/iso4217` |
| `sharesItemType` or derived from `sharesItemType` | A single `xbrli:measure` element whose `xsd:QName` content is constrained as follows:  The (local part) of the `xsd:QName` **MUST** be `"shares"` and the (namespace name) of the `xsd:QName` **MUST** be `http://www.xbrl.org/2003/instance` |

To represent rates, percentages or ratios where the numerator and the denominator would be the same [Units](#unit), the fact **MUST** have a ` @unitRef` attribute identifying a `unit ` element with a single `  <measure>  ` element as its only child. The local part of the `  <measure>  ` **MUST** be `"pure"` and the namespace prefix **MUST** resolve to the namespace: `"http://www.xbrl.org/2003/instance"`. Rates, percentages and ratios **MUST** be reported using decimal or scientific notation rather than in percentages where the value has been multiplied by 100.

A complex [Unit](#unit) of measure can be expressed by showing the mathematical relationships between other units of measure using a sequence of sibling `  <measure>  ` elements (which imply a multiplication of those `  <measure>  ` elements) and a single `  <divide>  ` element (which implies division of a numerator by a denominator).

A `  <measure>  ` element with a namespace prefix that resolves to the `"http://www.xbrl.org/2003/instance"` namespace **MUST** have a local part of either `"pure"` or `"shares"`.

### 4.8.3 The <divide> element

The `  <divide>  ` element **MUST** contain a `  <unitNumerator>  ` element followed by a `  <unitDenominator>  ` element.

### 4.8.4 The <unitNumerator> and <unitDenominator> elements

The `  <unitNumerator>  ` element and the `  <unitDenominator>  ` element must both contain one or more `  <measure>  ` elements.

[Units](#unit) **MUST** be expressed in their simplest possible form. The `  <divide>  ` element **MUST** not contain any `  <measure>  ` elements in its `  <unitNumerator>  ` that are [S-Equal](#s-equal) to `  <measure>  ` elements in its `  <unitDenominator>  `.

Some examples of the `  <unit>  ` element are shown in the following example.

Example 20: Use of the unit element

<table><tbody><tr><th>Example</th><th>Meaning</th></tr><tr><td><unit id="u1"><p><measure<br>xmlns:ISO4217="http://www.xbrl.org/2003/iso4217">ISO4217:GBP</measure></p></unit></td><td><p>Currency, UK Pounds.</p></td></tr><tr><td><unit id="u2"><p><measure<br>xmlns:ISO4217="http://www.xbrl.org/2003/iso4217">ISO4217:gbp</measure></p></unit></td><td><p>Incorrect lower case currency designator.</p></td></tr><tr><td><unit id="u1"><p><measure>xbrli:pure</measure></p></unit></td><td><p>A pure number, such as % revenue change.</p></td></tr><tr><td><unit id="u3"><p><measure>myuom:feet</measure></p><p><measure>myuom:feet</measure></p></unit></td><td><p>Square feet - feet multiplied by feet.</p></td></tr><tr><td><unit id="u4"><p><measure>xbrli:shares</measure></p></unit></td><td><p>A number of shares.</p></td></tr><tr><td><unit id="u5"><p><measure>myuom:FTE</measure></p></unit></td><td><p>A head count (number of Full Time Equivalents).</p></td></tr><tr><td><divide><unitNumerator><p><measure>ISO4217:EUR</measure></p></unitNumerator><unitDenominator><p><measure>xbrli:shares</measure></p></unitDenominator></divide></td><td><p>Earnings per share (EPS) measured in Euros per share.</p></td></tr><tr><td><divide><unitNumerator><p><measure>ISO4217:EUR</measure></p></unitNumerator><unitDenominator><p><measure>ISO4217:EUR</measure></p></unitDenominator></divide></td><td><p>Illegal because the same measure occurs in both the <code>numerator</code> and the <code>denominator</code> of the <code> <divide> </code> element.</p></td></tr><tr><td colspan="2"><p>The <code>"ISO4217"</code> namespace prefix used in these examples must resolve to <code>"http://www.xbrl.org/2003/iso4217"</code>.</p><p>The <code>"xbrli"</code> namespace prefix used in these examples must resolve to <code>"http://www.xbrl.org/2003/instance".</code></p><p>The <code>"myuom"</code> namespace prefix is not defined by the XBRL specification, but it must resolve to a namespace that is in scope for the <code> <measure> </code> element. This namespace may be a URL that identifies a resource that describes the <a href="#unit">Units</a> of measure that are contained by the namespace. Although there are no XBRL semantics on how to interpret this information, it may provide assistance to creators of <a href="#XBRL-instance">XBRL Instances</a>. For example, if the <code>myuom</code> namespace prefix resolves to "http://www.mycomp.com/myuom" then this namespace could be a URL that contains an HTML document that lists the available units of measure.</p></td></tr></tbody></table>

Some complex [Units](#unit) of measure **MAY** be expressed as a simple unit of measure. For example, square feet may be expressed as a complex unit of measure showing a multiplication of two basic measures of feet as shown in the following example. It is at the discretion of the XBRL instance creator to use a `  <unit>  ` element that describes the unit of measure to the appropriate degree.

Example 21: Simple and complex unit of measure comparison

<table><tbody><tr><th>Simple Unit of Measure</th><th>Complex Unit of Measure</th></tr><tr><td><unit id="u1"><p><measure>myuom:sqrft</measure></p></unit></td><td><unit id="u4"><p><measure>myuom:feet</measure></p><p><measure>myuom:feet</measure></p></unit></td></tr><tr><td colspan="2"><p>Note: The namespace prefix <code>myuom</code> must resolve to a valid namespace. It should be understood that the measures in this example <code>"sqrft",</code> and <code>"feet"</code> are contained in this namespace.</p></td></tr></tbody></table>

## 4.9 Tuples

While most business facts can be independently understood, some facts are dependent on each other for proper understanding, especially if multiple occurrences of that fact are being reported. For example, in reporting the management of a company, each manager's name has to be properly associated with the manager's correct title. Such sets of facts (manager's title/manager's name) are called `tuples`.

[Tuples](#tuple) have complex content and **MAY** contain both items and other tuples. Like the `  <item>  ` element, the `  <tuple>  ` element is abstract. The following rules apply to tuples and consequently to their declarations in [Taxonomy Schemas](#taxonomy-schema):

- All [Tuples](#tuple) **MUST** be members of the substitution group that has `  <tuple>  ` as its head. Therefore, tuples **MUST** be declared globally, because only global elements can be in a substitution group.
- [Tuple](#tuple) declarations in [Taxonomy Schemas](#taxonomy-schema) **MUST NOT** include a ` @periodType` or ` @balance` attribute (see [**Section 5.1.1.1**](#_5.1.1.1) and [**Section 5.1.1.2**](#_5.1.1.2) respectively);
- [Tuples](#tuple) might need to be referenced from elsewhere (such as from a footnote). Therefore, all tuple declarations in [Taxonomy Schemas](#taxonomy-schema) **SHOULD** (but are not required to) include a declaration of an optional local attribute with name ` @id` of type xsd:`ID`. Authors of extension taxonomies **SHOULD NOT** prohibit the ` @id` attribute, if one exists, when restricting tuple datatypes.
	**NOTE:** If the taxonomy author fails to define or prohibits an ` @id` attribute for a [Tuple](#tuple) then that tuple will not be referenceable by shorthand xpointers.
- Attribute uses [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) (see specifically [http://www.w3.org/TR/xmlschema-1/#section-XML-Representation-of-Attribute-Use-Components](http://www.w3.org/TR/xmlschema-1/#section-XML-Representation-of-Attribute-Use-Components)) in [Tuple](#tuple) declarations **MUST NOT** reference attributes from any of the following namespaces: `http://www.xbrl.org/2003/instance`, `http://www.xbrl.org/2003/linkbase`, `http://www.xbrl.org/2003/XLink`, `http://www.w3.org/1999/xlink`..
- [Tuples](#tuple) **MUST NOT** have mixed content, or simple content. Therefore, all tuple definitions in [Taxonomy Schemas](#taxonomy-schema) **MUST NOT** permit mixed content or simple content.
- [Tuple](#tuple) declarations in [Taxonomy Schemas](#taxonomy-schema) **SHOULD NOT** specify local attributes, other than the 'id' attribute.
- Children of a [Tuple](#tuple) in an instance **MUST** be elements that are in a substitution group that has either `  <item>  ` or `  <tuple>  ` as its head.
- Considering the constraint on [Tuple](#tuple) content in instances (above), it is inappropriate for taxonomy authors to include non-concept elements in the content models of [Tuple](#tuple) declarations. Therefore, in the declaration of any tuple in a [Taxonomy Schema](#taxonomy-schema), declarations of child elements of that tuple **MUST** be references to global element declarations that are in a substitution group that has either `  <item>  ` or `  <tuple>  ` as its head.
	**NOTE:** From a schema perspective, this leaves open the possibility of illegal content in the instance via the use of wildcards (`<xsd:any>`); processors will signal such illegal content because of the preceding instance-level constraint.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><documentation>

Abstract tuple element used as head of tuple substitution group

</documentation></schema>

Example 22: Defining a tuple as a member of the substitutionGroup "tuple"

| An abbreviated example taxonomy schema: |
| --- |
| <schema   xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://mycompany.com/xbrl/taxonomy">  <element name="managementName" type="xbrli:tokenItemType" xbrli:periodType="instant" substitutionGroup="xbrli:item"/>  <element name="managementTitle" type="xbrli:tokenItemType" xbrli:periodType="instant" substitutionGroup="xbrli:item"/>  <element name="managementAge" type="xbrli:nonNegativeIntegerItemType" xbrli:periodType="instant" substitutionGroup="xbrli:item"/>  <restriction base="anyType"><sequence>  <element ref="s:managementName"/>  <element ref="s:managementTitle"/>  <element ref="s:managementAge" minOccurs="0"/>  </sequence>  <attribute name="id" type="ID" use="optional"/>  </restriction></schema> |

| An XBRL instance of the taxonomy (`  <context>  ` and `  <unit>  ` elements and `  <linkbaseRef>  ` elements not shown): |
| --- |
| <xbrl   xmlns="http://www.xbrl.org/2003/instance">  <!---->  <s:managementInformation>  <s:managementName contextRef="c1">Haywood Chenokitov</s:managementName>  <s:managementTitle contextRef="c1">President</s:managementTitle>  <s:managementAge precision="2" contextRef="n1" unitRef="u1">42</s:managementAge>  </s:managementInformation><s:managementInformation>  <s:managementName contextRef="c1">Miriam Minderbender</s:managementName>  <s:managementTitle contextRef="c1">CEO</s:managementTitle>  </s:managementInformation>  <!---->  <!---->  </xbrl> |

The `all`, `sequence` and `choice` elements **MAY** appear in [Tuples](#tuple). For example, consider information that is disclosed in tax filings regarding real estate and other properties:

Example 23: Elements describing business properties held and disposed

| Label | Element Name | Balance | Substitution Group |
| --- | --- | --- | --- |
| Property | `property` |  | tuple |
| Property description | `description` |  | item |
| Date property acquired | `dateAcquired` |  | item |
| Date property disposed of | `dateDisposedOf` |  | item |
| Property fair market value | `fairMarketValue` |  | item |

Although the description and date acquired are relevant for any property, the property either has a fair market value or has already been disposed of, but not both.

Example 24: Hierarchy in a tuple

| ![[image001.png]] | Example: [Tuples](#tuple) associate [Concepts](#concept) that cannot be understood independently and repeat within an [XBRL Instance](#XBRL-instance). Multiple occurrences of a tuple within an XBRL instance are distinguished by having different content and contexts. |
| --- | --- |

The content models for [Tuples](#tuple) can be defined using only XML Schema. Content models for tuples are not defined or modified by any of the XBRL [Linkbases](#linkbase).

## 4.10 Equality predicates relevant to detecting duplicate items and tuples

There are several different senses of "equal" that are relevant to detection of duplicates in [XBRL Instances](#XBRL-instance): Identical, Structure equal ([S-Equal](#s-equal)), Parent equal ([P-Equal](#p-equal)), Value equal ([V-Equal](#v-equal)), [\[XPath 1.0\]](#XPATH) -equal ([X-Equal](#x-equal)), Context equal ([C-Equal](#c-equal)) and Unit equal ([U-Equal](#u-equal)). These different equality predicates are polymorphic and formally defined in a recursive fashion. They are all symmetric predicates, i.e. the result of **X** (predicate) **Y** = the result of **Y** (predicate) **X**.

Table 4: Equality predicate definitions.

| Argument Types | Predicates | Definition |
| --- | --- | --- |
| `node` | identical | Exactly the same XML node. |
| `sequence` | [S-Equal](#s-equal), [V-Equal](#v-equal), [C-Equal](#c-equal), [U-Equal](#u-equal) | Every node in one sequence is { [S-Equal](#s-equal), [V-Equal](#v-equal), [C-Equal](#c-equal), [U-Equal](#u-equal) } to the node in the same position in the other sequence. |
| `set` | identical, [S-Equal](#s-equal), [V-Equal](#v-equal), [C-Equal](#c-equal), [U-Equal](#u-equal) | Set **X** is {identical, [S-Equal](#s-equal), [V-Equal](#v-equal), [C-Equal](#c-equal), [U-Equal](#u-equal) } to set **Y** if: every node in set **X** can be paired with a node in set **Y** to which it is {identical, [S-Equal](#s-equal), [V-Equal](#v-equal), [C-Equal](#c-equal), [U-Equal](#u-equal) } and the two sets have the same number of members.  **NOTE:** the definition of a set requires that it have distinct members. |
| `any XML object` | [X-Equal](#x-equal) | An XML object **A** is [X-Equal](#x-equal) to an XML object **B** if the [\[XPath 1.0\]](#XPATH) expression **A** = **B** returns the value `true` (see [http://www.w3.org/TR/xpath.html#booleans](http://www.w3.org/TR/xpath.html#booleans)). In the case of element and attribute values, those whose type are `xsd:decimal`, `xsd:float`, or `xsd:double`, or derived from one of these types **MUST** be treated as numbers for the purposes of interpretation of [http://www.w3.org/TR/xpath.html#booleans](http://www.w3.org/TR/xpath.html#booleans). If a value has type `xsd:boolean` (or a type derived from `xsd:boolean`), then it **MUST** be converted to an [\[XPath 1.0\]](#XPATH) Boolean with `'1'` and `'true'` being converted to `true` and `'0'` and `'false'` being converted to `false`. Values with any other XML Schema type are treated as [\[XPath 1.0\]](#XPATH) strings. |
| `text` | [S-Equal](#s-equal) | The two text strings are [X-Equal](#x-equal) |
| `attribute` | [S-Equal](#s-equal) | The two attributes have local names and namespaces that are [S-Equal](#s-equal) and have values that are [X-Equal](#x-equal) |
| `Element (except those   handled separately in this list)` | [S-Equal](#s-equal) | Not identical, and their element local names and namespaces are both [S-Equal](#s-equal), and the set of their attributes are [S-Equal](#s-equal), and the sequence of text and sub-element contents are [S-Equal](#s-equal). |
| `  <entity>  ` | [S-Equal](#s-equal) | `  <identifier>  ` elements are [S-Equal](#s-equal), and `  <segment>  ` elements are [S-Equal](#s-equal) (with any missing `segment` treated as [S-Equal](#s-equal) to an empty `  <segment>  ` element). |
| `startDate` | [S-Equal](#s-equal) | The implied date/time is equal, according to the rules set out in [**Section 4.7.2**](#_4.7.2) |
| `endDate` | [S-Equal](#s-equal) | The implied date/time is equal, according to the rules set out in [**Section 4.7.2**](#_4.7.2) |
| `instant` | [S-Equal](#s-equal) | The implied date/time is equal, according to the rules set out in [**Section 4.7.2**](#_4.7.2) |
| `  <period>  ` | [S-Equal](#s-equal) | One of the following conditions applies: 1. both elements have a child `forever` element, or 2. their child `instant` elements are [S-Equal](#s-equal), or 3. their child `startDate` elements are [S-Equal](#s-equal) and their child `endDate` elements are [S-Equal](#s-equal) |
| `  <unit>  ` | [S-Equal](#s-equal) | The child `  <divide>  ` or set of `  <measure>  ` elements are [S-Equal](#s-equal). |
| `  <divide>  ` | [S-Equal](#s-equal) | The `  <unitNumerator>  ` and `  <unitDenominator>  ` elements are both [S-Equal](#s-equal) |
| `  <unitNumerator>  ` | [S-Equal](#s-equal) | The sets of child `  <measure>  ` elements are [S-Equal](#s-equal) |
| `  <unitDenominator>  ` | [S-Equal](#s-equal) | The sets of child `  <measure>  ` elements are [S-Equal](#s-equal) |
| `  <measure>  ` | [S-Equal](#s-equal) | The namespace prefix in the content of the two `  <measure>  ` elements resolves to the same namespace and the local names in the content of the two `  <measure>  ` elements are [S-Equal](#s-equal). |
| `  <context>  ` | [S-Equal](#s-equal) | `  <period>  ` elements are [S-Equal](#s-equal), and `  <entity>  ` elements are [S-Equal](#s-equal), and `  <scenario>  ` elements are [S-Equal](#s-equal). |
| `  <item>  ` | [S-Equal](#s-equal) | they are [C-Equal](#c-equal), and they are [U-Equal](#u-equal), and ` @precision` attributes are [S-Equal](#s-equal), and ` @decimals` attributes are [S-Equal](#s-equal), and the text of their contents is [S-Equal](#s-equal) after converting any values of [Numeric Items](#numeric-item) to a decimal representation. |
| `  <tuple>  ` | [S-Equal](#s-equal) | The sets of (`  <item>  ` and `  <tuple>  `) children are [S-Equal](#s-equal). |
| `  <usedOn>  ` | [S-Equal](#s-equal) | The namespace prefix in the content of the two `  <usedOn>  ` elements resolves to the same namespace and the local names in the content of the two `  <usedOn>  ` elements are [S-Equal](#s-equal). |
| `item` | [P-Equal](#p-equal) | Nodes are children of the identical parent. |
| `  <tuple>  ` | [P-Equal](#p-equal) | Nodes are children of the identical parent. |
| `item` | [C-Equal](#c-equal) | their ` @contextRef` attributes identify `contexts` that are identical or [S-Equal](#s-equal) |
| Any pair of [Numeric Items](#numeric-item) | [U-Equal](#u-equal) | [Numeric Items](#numeric-item) **X** and **Y** are [U-Equal](#u-equal) if and only if all the following conditions apply: 1. the set of descendant `  <unitNumerator>  ` elements of **U <sub>X</sub>** is [S-Equal](#s-equal) to the set of descendant `  <unitNumerator>  ` elements of **U <sub>Y</sub>**, and 2. the set of descendant `  <unitDenominator>  ` elements of **U <sub>X</sub>** is [S-Equal](#s-equal) to the set of descendant `  <unitDenominator>  ` elements of **U <sub>Y</sub>**, and 3. the set of child `  <measure>  ` elements of of **U <sub>X</sub>** is [S-Equal](#s-equal) to the set of child `  <measure>  ` elements of **U <sub>Y</sub>**, where **U <sub>X</sub>** is the `  <unit>  ` element referenced by the ` @unitRef` attribute of **X** and **U <sub>Y</sub>** is the `  <unit>  ` element referenced by the ` @unitRef` attribute of **Y**  **NOTE:** if **U <sub>X</sub>** is identical to **U <sub>Y</sub>** then the above tests will always return the result true |
| Any pair of [Non-Numeric Items](#non-numeric-item) | [U-Equal](#u-equal) | true |
| One [Numeric Item](#numeric-item) and one [Non-Numeric Item](#non-numeric-item) | [U-Equal](#u-equal) | false |
| [Numeric Items](#numeric-item) not of `type fractionItemType` or a type derived from `   fractionItemType` by restriction | [V-Equal](#v-equal) | **A** and **B** are [V-Equal](#v-equal) if and only if all the following conditions apply: 1. **A** and **B** are [C-Equal](#c-equal) and [U-Equal](#u-equal) 2. the numeric values **A <sub>N</sub>** and **B <sub>N</sub>** are [X-Equal](#x-equal) where **A <sub>N</sub>** is obtained by rounding the content of **A** to **N** significant figures and **B <sub>N</sub>** is obtained by rounding the content of **B** to **N** significant figures where **N** is the lower of: 	1. the specified or inferred decimals for **A** and 		2. the specified or inferred decimals for **B** (If either [Numeric Item](#numeric-item) has a ` @precision` attribute value 0 then the v-equality is false.) |
| [Numeric Items](#numeric-item) of type `fractionItemType` or a type derived from `fractionItemType   ` by restriction | [V-Equal](#v-equal) | **A** and **B** are [V-Equal](#v-equal) if and only if all the following conditions apply: 1. **A** and **B** are [C-Equal](#c-equal) and [U-Equal](#u-equal) 2. **A <sub>N</sub>** is [X-Equal](#x-equal) to **B <sub>N</sub>** and **A <sub>D</sub>** is [X-Equal](#x-equal) to **B <sub>D</sub>** where: 	1. **A <sub>N</sub>** is the numerator and **A <sub>D</sub>** is the denominator of the normal form (defined below) of **A** and 		2. **B <sub>N</sub>** is the numerator and **B <sub>D</sub>** is the denominator of the normal form of **B.** For any item F of type `fractionItemType` or a type derived from `fractionItemType` by restriction, the normal form has numerator F **<sub>N</sub>** and denominator F **<sub>D</sub>** such that F **<sub>N</sub>** and F **<sub>D</sub>** are integers and have no integer common factor and there exists a number H such that multiplying F **<sub>N</sub>** by H gives the numerator of F and multiplying F **<sub>D</sub>** by H gives the denominator of F. |
| [Numeric Item](#numeric-item) `s, one of which is ` of `type fractionItemType ` or a type derived from `    fractionItemType  ` by restriction and the other of which is not | [V-Equal](#v-equal) | [V-Equal](#v-equal) is always false for such combinations of [Numeric Items](#numeric-item) |
| `Non-Numeric Item` | [V-Equal](#v-equal) | **A** and **B** are [V-Equal](#v-equal) if and only if all the following conditions apply 1. **A** and **B** are [C-Equal](#c-equal) 2. [\[XPath 1.0\]](#XPATH) **normalize-space(A <sub>C</sub>) = normalize-space(B <sub>C</sub>)** where **A <sub>C</sub>** is the content of **A** and **B <sub>C</sub>** is the content of **B.** |
| [`item`](#item) | duplicate | Item **X** and item **Y** are duplicates if and only if all the following conditions apply: 1. **X** is not identical to **Y**, and 2. the element local name of **X** is [S-Equal](#s-equal) to the element local name of **Y**, and 3. **X** and **Y** are defined in the same namespace, and 4. **X** is [P-Equal](#p-equal) to **Y**, and 5. **X** is [C-Equal](#c-equal) to **Y**, and 6. **X** is [U-Equal](#u-equal) to **Y**. |
| [`  <tuple>  `](#tuple) | duplicate | [Tuple](#tuple) **X** and [Tuple](#tuple) **Y** are duplicates if and only if all the following conditions apply: 1. **X** is not identical to **Y,** and 2. the element local name of **X** is [S-Equal](#s-equal) to the element local name of **Y**, and 3. **X** and **Y** are defined in the same namespace and 4. **X** is [P-Equal](#p-equal) to **Y**, and 5. every node **A** in the set of child [Tuples](#tuple) of **X** can be paired with one node **B** in the set of child [Tuples](#tuple) of **Y** such that **A** and **B** satisfy all the requirements for being [Duplicate Tuples](#duplicate-tuples) except for being [P-Equal](#p-equal), and 6. **X** has the same number of child [Tuples](#tuple) as **Y**, and 7. every node **A** in the set of child items of **X** can be paired with one node **B** in the set of child items of **Y** such that **A** is [V-Equal](#v-equal) to **B**, and **A** and **B** satisfy all the requirements for being [Duplicate Items](#duplicate-items) except for being [P-Equal](#p-equal), and 8. **X** has the same number of child items as **Y** |

The following extended example illustrates positive and negative examples of each of the above predicates.

Example 25: Duplicate items, tuples and contexts

| element | An XBRL instance containing two contexts that are s-equal and doubly nested tuples. Several of the elements are named in the left column. |
| --- | --- |
|  | `<xbrl xmlns="http://www.xbrl.org/2003/instance"` |
|  | `     xmlns:s="http://mycompany.com/xbrl/taxonomy"` |
|  | `     xmlns:xbrli="http://www.xbrl.org/2003/instance"` |
|  | `     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">` |
|  |  |
| `a analysis` | `<s:analysis>` |
| `b customer` | ` <s:customer>` |
| `b name` | `   <s:name contextRef="np3">Acme</s:name>` |
| `b gross` | `   <s:gross unitRef="u3" contextRef="np3"precision="4">3001</s:gross>` |
| `b returns` | `   <s:returns unitRef="u3" contextRef="np3"` |
|  | `              precision="3">100</s:returns>` |
|  | `   <s:net unitRef="u3"contextRef="np3" precision="4">2900</s:net>` |
|  | ` </s:customer>` |
| `c customer` | ` <s:customer>` |
| `c name` | `   <s:name contextRef="Xnnp3X">Acme</s:name>` |
| `c gross` | `   <s:gross unitRef="u3" contextRef="np3"precision="3">3000</s:gross>` |
|  | `   <s:returns unitRef="u3" contextRef="np3"` |
|  | `              precision="3">100</s:returns>` |
|  | `   <s:net unitRef="u3" contextRef="np3" precision="4">2900</s:net>` |
|  | ` </s:customer>` |
| `d customer` | ` <s:customer>` |
|  | `   <s:name contextRef="np3">Acme</s:name>` |
|  | `   <s:gross unitRef="u3" contextRef="np3"precision="4">3000</s:gross>` |
| `d returns` | `   <s:returns unitRef="u3" contextRef="np3"precision="3">500</s:returns>` |
|  | `   <s:net unitRef="u3"contextRef="np3" precision="4">2500</s:net>` |
|  | ` </s:customer>` |
|  | ` <s:customer>` |
| `e customer` | `   <s:name contextRef="np3">Bree</s:name>` |
| `f name` | `   <s:name contextRef="Xnnp3X">Bree</s:name>` |
| `g name` | `   <s:gross unitRef="u3" contextRef="np3"precision="4">3000</s:gross>` |
|  | `   <s:returns unitRef="u3" contextRef="np3"` |
|  | `              precision="3">200</s:returns>` |
|  | `   <s:net unitRef="u3"contextRef="np3" precision="4">2800</s:net>` |
|  | ` </s:customer>` |
|  | ` <s:totalGross unitRef="u3" contextRef="np3"` |
| `h totalGross` | `              precision="3">12000</s:totalGross>` |
|  | `</s:analysis>` |
|  |  |
|  |  |
|  | `<!-- One Redundant Context Xnnp3X = period,2003 -->` |
|  | `<context id="np3">` |
| `np3` | `  <entity>` |
|  | `   <identifier scheme="http://www.nasdaq.com">SAMP</identifier>` |
|  | `  </entity>` |
|  | `<period>` |
|  | ` <startDate>2003-01-01</startDate>` |
|  | `    <endDate>2003-12-31</endDate>` |
|  | `  </period>` |
|  | `</context>` |
|  | `<unit id="u3"><measure>ISO4217:USD</measure></unit>` |
| `u3` | `<context id="Xnnp3X">` |
| `Xnnp3X` | ` <entity>` |
|  | `   <identifier scheme="http://www.nasdaq.com">SAMP</identifier>` |
|  | ` </entity>` |
|  | `  <period>` |
|  | `   <startDate>2003-01-01</startDate>` |
|  | `   <endDate>2003-12-31</endDate>` |
|  | `  </period>` |
|  | `</context>` |
|  | `</xbrl>` |

Note that, notwithstanding the lack of a calculation linkbase in this example, the total of 12000 in "h totalGross" is the most precise value that can be derived from sum of the values of gross for the 4 customers (3001+3000+3000+3000=12001 but the most precise value can be correct to only 3 significant figures because c gross has `precision="3"` and is hence 12000)

Example 26: Predicates for detecting duplicates

| Node 1 | Node 2 | Type | Predicate | True | Reason |
| --- | --- | --- | --- | --- | --- |
| `np3` | `Xnnp3X` | `context` | Identical | no | different nodes |
| `np3` | `Xnnp3X` | `context` | [S-Equal](#s-equal) | yes | `  <entity>  ` and `  <period>  ` are [S-Equal](#s-equal) |
|  |  |  |  |  |  |
| `f name` | `g name` | `item` | [S-Equal](#s-equal) | yes | different context ids `np3` and `Xnnp3X` which are nevertheless [S-Equal](#s-equal) |
| `f name` | `g name` | `item` | [P-Equal](#p-equal) | yes | same parent element |
| `f name` | `g name` | `item` | [C-Equal](#c-equal) | yes | equal contexts `np3` and `Xnnp3X` |
| `f name` | `g name` | `item` | [V-Equal](#v-equal) | yes | equal content " `Bree` " |
| `f name` | `g name` | `item` | [Duplicates](#duplicate-items) | yes | [P-Equal](#p-equal) and [C-Equal](#c-equal) |
|  |  |  |  |  |  |
| `b name` | `c name` | `item` | [S-Equal](#s-equal) | yes | different context ids `np3` and `Xnnp3X` which are nevertheless [S-Equal](#s-equal) |
| `b name` | `c name` | `item` | [P-Equal](#p-equal) | no | they are in different customer [Tuples](#tuple) |
| `b name` | `c name` | `item` | [C-Equal](#c-equal) | yes | equal contexts `np3` and `Xnnp3X` |
| `b name` | `c name` | `item` | [V-Equal](#v-equal) | yes | they both have content "Acme" |
| `b name` | `c name` | `item` | [Duplicates](#duplicate-items) | no | not [P-Equal](#p-equal), so [V-Equal](#v-equal) doesn't matter |
|  |  |  |  |  |  |
| `b gross` | `c gross` | `item` | [S-Equal](#s-equal) | no |  |
| `b gross` | `c gross` | `item` | [P-Equal](#p-equal) | no | different parents |
| `b gross` | `c gross` | `item` | [C-Equal](#c-equal) | yes | they both have context np3 and [Unit](#unit) u3 |
| `b gross` | `c gross` | `item` | [V-Equal](#v-equal) | yes | "3001" with precision 3 equals "3000" |
| `b gross` | `c gross` | `item` | [Duplicates](#duplicate-items) | no | not [P-Equal](#p-equal), so [V-Equal](#v-equal) doesn't matter |
|  |  |  |  |  |  |
| `b customer` | `c customer` | `  <tuple>  ` | [S-Equal](#s-equal) | no | different context ids np3 and Xnnp3X |
| `b customer` | `c customer` | `  <tuple>  ` | [P-Equal](#p-equal) | yes | same parent " `a analysis` " |
| `b customer` | `c customer` | `  <tuple>  ` | [C-Equal](#c-equal) | n/a | [C-Equal](#c-equal) doesn't apply to [Tuples](#tuple) |
| `b customer` | `c customer` | `  <tuple>  ` | [V-Equal](#v-equal) | n/a | [V-Equal](#v-equal) doesn't apply to [Tuples](#tuple) |
| `b customer` | `c customer` | `  <tuple>  ` | [Duplicates](#duplicate-tuples) | yes | [P-Equal](#p-equal), and child items `name`, `gross`, `returns` and `net` are all [V-Equal](#v-equal) |
|  |  |  |  |  |  |
| `b returns` | `d returns` | `item` | [S-Equal](#s-equal) | no | different values |
| `b returns` | `d returns` | `item` | [P-Equal](#p-equal) | no | parents are `b customer` and `d customer` |
| `b returns` | `d returns` | `item` | [C-Equal](#c-equal) | yes | both have context `np3 and Unit u3` |
| `b returns` | `d returns` | `item` | [V-Equal](#v-equal) | no | b value is 100, d value is 500 |
| `b returns` | `d returns` | `item` | [Duplicates](#duplicate-items) | no | not [P-Equal](#p-equal), so [V-Equal](#v-equal) doesn't matter |
|  |  |  |  |  |  |
| `b customer` | `d customer` | `  <tuple>  ` | [S-Equal](#s-equal) | no | different values of `returns` and `net` |
| `b customer` | `d customer` | `  <tuple>  ` | [P-Equal](#p-equal) | yes | same parent " `a analysis` " |
| `b customer` | `d customer` | `  <tuple>  ` | [C-Equal](#c-equal) | n/a | [C-Equal](#c-equal) doesn't apply to [Tuples](#tuple) |
| `b customer` | `d customer` | `  <tuple>  ` | [V-Equal](#v-equal) | n/a | [V-Equal](#v-equal) doesn't apply to [Tuples](#tuple) |
| `b customer` | `d customer` | `  <tuple>  ` | [Duplicates](#duplicate-tuples) | no | [P-Equal](#p-equal), and child items `b name` and `b gross` are [V-Equal](#v-equal) to `d name` and `d gross`, and child items `b returns` and `b net` are not [V-Equal](#v-equal) to `b returns` and `b net`. |

The equality predicates in the definition of [Duplicate Items](#duplicate-items) are ones of *equal location*, not *equal content.* In addition, it should be noted that attributes other than ` @contextRef`, ` @unitRef`, ` @precision` and ` @decimals` **MUST** be ignored for the purposes of this comparison (a consequence of the definition of s-equality for items). For example, additional ` @id` attributes do not distinguish otherwise equal items. Whether items appear within a [Tuple](#tuple) or not also impacts on whether they are duplicates, because the definition of duplicate items also carries the proviso that they have the same parent (i.e. are [P-Equal](#p-equal)).

When determining whether two [Numeric Items](#numeric-item) are [V-Equal](#v-equal) (a predicate that is used in the definition of various other equality type predicates) it is necessary to take into consideration the values of ` @precision` for the two numeric items. If ` @precision` has not been specified for either of the two numeric items it is necessary to infer a value for it according to the rules in [**Section 4.6.6**](#_4.6.6).

The XBRL definition of [Duplicate Items](#duplicate-items) and [Tuples](#tuple) encompasses many, but not all, inconsistent and redundant data items in an [XBRL Instance](#XBRL-instance). Tuples that are not duplicates according to the XBRL definition might still have semantic inconsistencies. In the example above, customer elements "c" and "d" appear to contain data about the same customer, in the same context, but have inconsistent data; XBRL does not detect these as [Duplicate Tuples](#duplicate-tuples) even though to a human reader an element such as name indicates a "unique key" that is sufficient to determine that these two tuples are, in effect, [C-Equal](#c-equal) (same context, different content).

## 4.11 Footnotes

While [Tuples](#tuple) deal with certain regularly-structured associations between elements that might appear in an XBRL instance, many documents include irregularly structured associations between facts. For instance, several facts may all be linked to the sentence "Including the effects of the merger with Example.com." To express these irregular linkages, XBRL uses the `  <footnoteLink>  ` element to describe these irregularly structured associations between facts in an [XBRL Instance](#XBRL-instance).

### 4.11.1 The <footnoteLink> element

The `  <footnoteLink>  ` element is an extended link. Its generic syntax is documented in [**Section 3.5.3**](#_3.5.3). It contains [Locators](#locator), resources and arcs that describe irregular relationships between facts in an [XBRL Instance](#XBRL-instance).

The XML Schema constraints on the `  <footnoteLink>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><element name="footnoteLink" substitutionGroup="xl:extended"><documentation>

footnote extended link element definition

</documentation><restriction base="xl:extendedType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="link:documentation"/>

<element ref="link:loc"/>

<element ref="link:footnoteArc"/>

<element ref="link:footnote"/>

</choice>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></element></schema>

Example 27: A footnote in an XBRL instance

<xbrl  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns:ci="http://www.xbrl.org/us/gaap/ci/2003/usfr-ci-2003"  
xmlns:fr="http://www.xbrl-fr.org/xbrl/2003-02-29"  
xmlns:ISO4217="http://www.xbrl.org2003/2003/iso4217"  
xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"  
xmlns:s="http://mycompany.com/xbrl/taxonomy"  
xmlns:xbrli="http://www.xbrl.org/2003/instance"  
xmlns:xlink="http://www.w3.org/1999/xlink"  
xmlns:xl="http://www.xbrl.org/2003/XLink"  
xmlns="http://www.xbrl.org/2003/instance" xsi:schemaLocation="http://www.xbrl-fr.org/xbrl/2003-02-29 fr.xsd">

<link:schemaRef xlink:type="simple" xlink:href="fr.xsd"/>

<fr:propertyPlantEquipmentGross precision="4" unitRef="u1" contextRef="c1">1200</fr:propertyPlantEquipmentGross>

<fr:assetsTotal id="f1" precision="4" unitRef="u1" contextRef="c1">2600</fr:assetsTotal>

<fr:equityTotal id="f3" precision="4" unitRef="u1" contextRef="c1">1100</fr:equityTotal>

<fr:liabilitiesTotal id="f2" precision="4" unitRef="u1" contextRef="c1">2600</fr:liabilitiesTotal>

<link:footnoteLink xlink:type="extended" xlink:title="1" xlink:role="http://www.xbrl.org/2003/role/link">

<link:footnote xlink:type="resource" xlink:label="footnote1" xlink:role="http://www.xbrl.org/2003/role/footnote" xml:lang="en">Including the effects of the merger.</link:footnote>

<link:footnote xlink:type="resource" xlink:label="footnote1" xlink:role="http://www.xbrl.org/2003/role/footnote" xml:lang="fr">Y compris les effets de la fusion.</link:footnote>

<link:loc xlink:type="locator" xlink:label="fact1" xlink:href="#f1"/>

<link:loc xlink:type="locator" xlink:label="fact1" xlink:href="#f2"/>

<link:loc xlink:type="locator" xlink:label="fact1" xlink:href="#f3"/>

<link:footnoteArc xlink:type="arc" xlink:from="fact1" xlink:to="footnote1" xlink:title="view explanatory footnote" xlink:arcrole="http://www.xbrl.org/2003/arcrole/fact-footnote"/>

</link:footnoteLink><context id="c1"><entity>

<identifier scheme="http://www.un.org/">Example plc</identifier>

</entity><period>

<instant>2001-08-16</instant>

</period><scenario name="Actual values">

<fr:scenarioType>actual</fr:scenarioType>

</scenario></context><unit id="u1">

<measure>ISO4217:EUR</measure>

</unit></xbrl>

Meaning: The one `  <footnoteArc>  ` connects three facts to two footnotes. The two footnotes are in different languages. The ` @xlink:title` attribute has been used on the `  <footnoteArc>  ` element to document the nature of the resource being made accessible from the facts.

#### 4.11.1.1 Locators in <footnoteLink> elements

`  <footnoteLink>  ` elements **MUST NOT** contain [Locators](#locator) that are not `  <loc>  ` elements. `  <loc>  ` elements are documented in detail in [**Section 3.5.3.7**](#_3.5.3.7). The `  <loc>  ` element, when used in a `  <footnoteLink>  `, **MUST** only point to items or [Tuples](#tuple) in the same [XBRL Instance](#XBRL-instance) that contains the `  <loc>  ` element itself.

#### 4.11.1.2 The <footnote> element

The `  <footnote>  ` element is the only resource allowed in `  <footnoteLink>  ` elements. Generic resources are documented in detail in [**Section 3.5.3.8**](#_3.5.3.8). The content of `footnote` resources is restricted relative to generic resources. Specifically, `footnote` resources **MAY** have mixed content containing a simple string, or a fragment of XHTML or a mixture of both.

One standard role is defined for `  <footnote>  ` elements. Its value is:

`http://www.xbrl.org/2003/role/footnote`

The XML Schema constraints on the `  <footnote>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><element name="footnote" substitutionGroup="xl:resource"><documentation>

Definition of the reference resource element

</documentation><extension base="xl:resourceType"><sequence>

<any namespace="http://www.w3.org/1999/xhtml" processContents="skip" minOccurs="0" maxOccurs="unbounded"/>

</sequence>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</extension></element></schema>

##### 4.11.1.2.1 The @xml:lang attribute on <footnote> elements

All `footnote` resources **MUST** have an ` @xml:lang` attribute identifying the language used for the content of the footnote. The value of the ` @xml:lang` attribute **MUST** conform to [\[XML\]](#XML) rules. (See [http://www.w3.org/TR/2000/REC-xml-20001006#sec-lang-tag](http://www.w3.org/TR/2000/REC-xml-20001006#sec-lang-tag) for details).

#### 4.11.1.3 The <footnoteArc> element

The `  <footnoteArc>  ` element has the same syntax as generic [Extended Link](#extended-link) arcs. See [**Section 3.5.3.9**](#_3.5.3.9) for details.

The XML Schema constraints on the `  <footnoteArc>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><documentation>

Concrete arc for use in footnote extended links.

</documentation></schema>

##### 4.11.1.3.1 @xlink:arcrole attributes on <footnoteArc> elements

The value of the ` @xlink:arcrole` attribute **MUST** be a URI that indicates the meaning of the arc.

One standard arc role value has been defined for arc role values on `  <footnoteArc>  ` elements. Its value is:

`http://www.xbrl.org/2003/arcrole/fact-footnote`

This arc role value is for use on a `  <footnoteArc>  ` from item or tuple [Locators](#locator) to `footnote` resources and it indicates that the `  <footnote>  ` conveys human-readable information about the fact or facts.

##### 4.11.1.3.2 @xlink:title attribute on <footnoteArc> elements (optional)

The ` @xlink:title` attribute **MAY** be used to convey information about the relationship between facts and related footnotes to users navigating between those facts and footnotes. The content of the ` @xlink:title` attribute **MUST** be a string. The ` @xlink:title` attribute content **MAY** be made visible to users of [\[XLINK\]](#XLINK) -enabled applications.

If the ` @xlink:title` attribute is insufficient for this purpose (for example, if the information needs to be provided in several languages), then titles, as defined in [**Section 3.5.3.9.6**](#_3.5.3.9.6), **MAY** be used.

## 5 XBRL Taxonomies

[**Section 3.1**](#_3.1) provides an overview of XBRL taxonomies.

A taxonomy is defined as an XML Schema [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) and the set of directly referenced [Extended Links](#extended-link) (via the `  <linkbaseRef>  ` element; see [**Section 5.1.2**](#_5.1.2)) and any extended links that are nested within the XML Schema. The XML Schemas in taxonomies are referred to, in this specification, as " [Taxonomy Schemas](#taxonomy-schema) ".

## 5.1 Taxonomy schemas

A taxonomy **MUST** include a [Taxonomy Schema](#taxonomy-schema). A taxonomy schema **MUST** be a valid instance of an XML Schema.

If [Extended Links](#extended-link) are included in a taxonomy, the [Taxonomy Schema](#taxonomy-schema) **MUST** contain `  <linkbaseRef>  ` elements that point to their [Linkbases](#linkbase) (see [**Section 5.1.2**](#_5.1.2)) or the extended links **MUST** be nested in linkbases contained in the taxonomy schema itself.

The [XBRL Instance](#XBRL-instance) schema defines the [Abstract Elements](#abstract-element) `item` and `tuple.` As a consequence of this and of [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) (in particular [http://www.w3.org/TR/xmlschema-1/#src-resolve)](http://www.w3.org/TR/xmlschema-1/#src-resolve\)) it is necessary for [Taxonomy Schemas](#taxonomy-schema) to import the XBRL instance schema *xbrl-instance-2003-12-31.xsd* if they define [Concepts](#concept) (elements in the item or tuple substitution groups). However, taxonomy schemas do not need to import the XBRL instance schema (for example, if their only purpose is to define syntax for segments and scenarios in contexts).

[Taxonomy Schemas](#taxonomy-schema) **SHOULD** specify a target namespace. If a target namespace attribute is so specified, its value **MUST NOT** be empty.

It will be necessary to include namespace declarations for several other schemas when creating [Taxonomy Schemas](#taxonomy-schema), such as the namespace for XML Schema itself.

Example 28: A skeletal taxonomy schema showing linkbase references

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns:ci="http://www.mycompany.com/taxonomy/2003-10-19"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.mycompany.com/taxonomy/2003-10-19"><appinfo>

<link:linkbaseRef xlink:type="simple" xlink:href="linkbase\_presentation.xml" xlink:role="http://www.xbrl.org/2003/role/presentationLinkbaseRef" xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"/>

<link:linkbaseRef xlink:type="simple" xlink:href="linkbase\_calculation.xml" xlink:role="http://www.xbrl.org/2003/role/calculationLinkbaseRef" xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"/>

<link:linkbaseRef xlink:type="simple" xlink:href="linkbase\_definition.xml" xlink:role="http://www.xbrl.org/2003/role/definitionLinkbaseRef" xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"/>

<link:linkbaseRef xlink:type="simple" xlink:href="linkbase\_label.xml" xlink:role="http://www.xbrl.org/2003/role/labelLinkbaseRef" xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"/>

<link:linkbaseRef xlink:type="simple" xlink:href="linkbase\_reference.xml" xlink:role="http://www.xbrl.org/2003/role/referenceLinkbaseRef" xlink:arcrole="http://www.w3.org/1999/xlink/properties/linkbase"/>

</appinfo>

<import namespace="http://www.xbrl.org/2003/instance" schemaLocation="http://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd"/>

<!---->

</schema>

XBRL taxonomies **MAY** be constructed to refer to other taxonomies; this extensibility of taxonomies is a critical feature of XBRL. In order to realise the complete potential of the technology, taxonomies must be extensible to accommodate virtually any business entity's unique reporting requirements while maintaining significant comparability across entities.

XBRL [Taxonomy Schemas](#taxonomy-schema) **MAY** import other taxonomy schemas and reference additional XBRL [Linkbases](#linkbase) as appropriate to achieve this extensibility.

[Taxonomy Schemas](#taxonomy-schema) **MAY** also define custom role values and custom arc role values for use in [Linkbases](#linkbase). See [**Section 5.1.2**](#_5.1.2) and [**Section 5.1.4**](#_5.1.4) for details.

### 5.1.1 Concept definitions

[Concepts](#concept) are defined in [Taxonomy Schemas](#taxonomy-schema). Each concept defined in a taxonomy schema is uniquely identified by an element's syntax definition in the taxonomy schema. To correspond to a concept definition, an XML Schema element definition has to specify the element's name, a substitution group, and type. All element names **MUST** be unique within a given taxonomy schema. The element **MUST** be a member of the substitution group that has either the XBRL `  <item>  ` element or the XBRL `  <tuple>  ` element as its head. The element **MAY** also include any of the other XML Schema attributes that can be used on an element's syntax definition, including ` @abstract` and ` @nillable`.

An element defining the syntax for a [Concept](#concept) **SHOULD** also have an ` @id` attribute. Providing an ` @id` attribute simplifies the content of the ` @xlink:href` attribute on linkbase `  <loc>  ` elements (see [**Section 3.5.1.2**](#_3.5.1.2)). Note that some XML Schema validators require uniqueness of all ` @id` attribute values in a [Taxonomy Schema](#taxonomy-schema) and in all XML schemas that it imports or includes, directly or indirectly. To increase robustness to such interpretations of the XML Schema specification [\[XML Schema Datatypes\]](#XMLSCHEMA-DATATYPES), care **SHOULD** be taken to limit the extent to which ` @id` attributes values are likely to clash with ` @id` attribute values in related schemas. In the example below, this has been done by prefixing the element name with an additional string, " `ci_` ".

Example 29: Typical element definitions in a taxonomy schema

<schema  
xmlns="http://www.w3.org/2001/XMLSchema">

<!---->

<!---->

<element id="ci\_preferredDividends" name="preferredDividends" xbrli:periodType="duration" type="xbrli:monetaryItemType" substitutionGroup="xbrli:item" nillable="true"/>

<element id="ci\_stockBasedCompensationPolicy" name="stockBasedCompensationPolicy" xbrli:periodType="duration" type="xbrli:stringItemType" substitutionGroup="xbrli:item" nillable="true"/>

</schema>

Meaning: Two concepts have been defined, one associated with the `preferredDividends` element and the other associated with the `stockBasedCompensationPolicy` element. Both concepts can be represented by nil-value items in XBRL instances. The `preferredDividends` concept is required to appear in [XBRL Instances](#XBRL-instance) as a [Numeric Item](#numeric-item) with a duration [Period](#period) in its context and the `stockBasedCompensationPolicy` concept is to appear in XBRL instances as a [Non-Numeric Item](#non-numeric-item) with an instant period in its context.

XBRL also defines two attributes, ` @periodType` and ` @balance`, that **MAY** be used on the element syntax definitions.

#### 5.1.1.1 The @periodType attribute

Some elements are associated with concepts that are measurable at an instant in time while others measure change over a period of time.

The XML Schema constraints on the ` @periodType` attribute are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><attribute name="periodType"><documentation>

The periodType attribute (restricting the period for XBRL items)

</documentation><restriction base="token">

<enumeration value="instant"/>

<enumeration value="duration"/>

</restriction></attribute></schema>

The ` @periodType` attribute **MUST** be used on elements in the substitution group for the `  <item>  ` element. A value of `instant` for the periodType attribute indicates that the element, when used in an [XBRL Instance](#XBRL-instance), **MUST** always be associated with a context in which the [Period](#period) is an instant. A value of `duration` indicates that the element, when used in an XBRL instance, **MUST** always be associated with a context in which the period is a duration, expressed using the `startDate` and `endDate` elements or expressed using the `forever` element.

Example 30: Instant and duration concept definitions

<element id="a1" name="changeInRetainedEarnings" xbrli:periodType="duration" type="xbrli:monetaryItemType" substitutionGroup="xbrli:item"/>

<element id="a2" name="fixedAssets" xbrli:balance="debit" xbrli:periodType="instant" type="xbrli:monetaryItemType" substitutionGroup="xbrli:item"/>

#### 5.1.1.2 The @balance attribute (optional)

An optional ` @balance` attribute **MAY** be added to the definition of an element if its type is `monetaryItemType` or derived from `monetaryItemType`. The ` @balance` attribute **MUST NOT** be used on items that do not have type equal to the `monetaryItemType` or to a type that is derived from `monetaryItemType`.

If the idea of debit/credit balance is appropriate to the element, it **MAY** be indicated using this attribute.

The XML Schema constraints on the ` @balance` attribute are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><attribute name="balance"><documentation>

The balance attribute (imposes calculation relationship restrictions)

</documentation><restriction base="token">

<enumeration value="debit"/>

<enumeration value="credit"/>

</restriction></attribute></schema>

Example 31: Using the balance element to indicate normal debit and credit balances

<element id="netIncome" name="netIncome" xbrli:balance="credit" xbrli:periodType="duration" type="xbrli:monetaryItemType" substitutionGroup="xbrli:item"/>

<element id="fixedAssets" name="fixedAssets" xbrli:balance="debit" xbrli:periodType="instant" type="xbrli:monetaryItemType" substitutionGroup="xbrli:item"/>

The ` @balance` attribute is important to applications that consume numbers related to accounting [Concepts](#concept) such as asset, liability, equity, revenue and expense. The ` @balance` attribute (debit/credit) provides a definitive declaration of how values in [XBRL Instances](#XBRL-instance) are to be authored and interpreted when the debit/credit designation is provided.

Table 5: Correct signage in an XBRL instance

| Taxonomy element | Account balance | Sign of [XBRL Instance](#XBRL-instance) element value |
| --- | --- | --- |
| `balance="credit"` | Credit | Positive or zero |
| `balance="credit"` | Debit | Negative or zero |
| `balance="debit"` | Debit | Positive or zero |
| `balance="debit"` | Credit | Negative or zero |

The numeric representation of a debit or credit item will normally (that is, more often than not) be positive in an XBRL instance.

Example 32: A concept appearing with positive and negative values in an XBRL instance

<my:netIncome precision="3" unitRef="u1" contextRef="c1">500</my:netIncome>

<my:netIncome precision="3" unitRef="u1" contextRef="c2">-200</my:netIncome>

Meaning: A profit of 500 and a loss of 200 in different contexts.

In addition, the assignment of ` @balance` attributes constrains the legal weights in `  <calculationArc>  ` elements.

Table 6: Constraints among the balance attribute and calculation arc weights

| ` @balance` attribute of " `from` " item | ` @balance` attribute of " `to` " item | illegal values of the ` @weight` attribute on `  <calculationArc>  ` |
| --- | --- | --- |
| `debit` | `debit` | Negative (< 0) |
| `debit` | `credit` | Positive (> 0) |
| `credit` | `debit` | Positive (> 0) |
| `credit` | `credit` | Negative (< 0) |

#### 5.1.1.3 Item data types

All item types **MUST** be one of the types listed below or derived from one of them by restriction. This set of XBRL provided base types covers the appropriate subset of XML Schema built-in types (both primitive and derived) [\[XML Schema Datatypes\]](#XMLSCHEMA-DATATYPES) as well as 4 types that have been identified as having particular relevance to the domain space addressed by XBRL (`monetaryItemType`, `sharesItemType, pureItemType` and `fractionItemType`) and hence explicitly defined in the XBRL namespace. All these types have simple content except for `fractionItemType`. Therefore, an item type in a taxonomy can never have complex content unless it is derived by restriction from `fractionItemType`.

The [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) mechanism that enables the explicit assertion of the type of an element in an instance document ([http://www.w3.org/TR/xmlschema-1/index.html#xsi\_type](http://www.w3.org/TR/xmlschema-1/index.html#xsi_type)) **MUST NOT** be applied to any `  <item>  ` or `  <tuple>  ` in an [XBRL Instance](#XBRL-instance). The type of `items` and `tuples` **MUST** be specified in the appropriate [Taxonomy Schema](#taxonomy-schema) instead.

Table 7: Defined item types

<table><tbody><tr><th>XBRL Item Type</th><th>Base type</th><th>unitRef attribute</th></tr><tr><td><code>decimalItemType</code></td><td><code>decimal</code></td><td>yes</td></tr><tr><td><code>floatItemType</code></td><td><code>float</code></td><td>yes</td></tr><tr><td><code>doubleItemType</code></td><td><code>double</code></td><td>yes</td></tr><tr><td colspan="3">The following numeric types are all based on the XML Schema built-in types that are derived by restriction from <code>decimal</code>.</td></tr><tr><td><code>integerItemType</code></td><td><code>integer</code></td><td>yes</td></tr><tr><td><code>nonPositiveIntegerItemType</code></td><td><code>nonPositiveInteger</code></td><td>yes</td></tr><tr><td><code>negativeIntegerItemType</code></td><td><code>negativeInteger</code></td><td>yes</td></tr><tr><td><code>longItemType</code></td><td><code>long</code></td><td>yes</td></tr><tr><td><code>intItemType</code></td><td><code>int</code></td><td>yes</td></tr><tr><td><code>shortItemType</code></td><td><code>short</code></td><td>yes</td></tr><tr><td><code>byteItemType</code></td><td><code>byte</code></td><td>yes</td></tr><tr><td><code>nonNegativeIntegerItemType</code></td><td><code>nonNegativeInteger</code></td><td>yes</td></tr><tr><td><code>unsignedLongItemType</code></td><td><code>unsignedLong</code></td><td>yes</td></tr><tr><td><code>unsignedIntItemType</code></td><td><code>unsignedInt</code></td><td>yes</td></tr><tr><td><code>unsignedShortItemType</code></td><td><code>unsignedShort</code></td><td>yes</td></tr><tr><td><code>unsignedByteItemType</code></td><td><code>unsignedByte</code></td><td>yes</td></tr><tr><td><code>positiveIntegerItemType</code></td><td><code>positiveInteger</code></td><td>yes</td></tr><tr><td colspan="3">The following numeric types are all types that have been identified as having particular relevance to the domain space addressed by XBRL and are hence included in addition to the built-in types from XML Schema.</td></tr><tr><td><code>monetaryItemType
  </code></td><td><code>xbrli:monetary</code></td><td>yes</td></tr><tr><td><code>sharesItemType</code></td><td><code>xbrli:shares</code></td><td>yes</td></tr><tr><td><code>pureItemType</code></td><td><code>xbrli:pure</code></td><td>yes</td></tr><tr><td><code>fractionItemType</code></td><td><code>complex type with the
  numerator being a decimal and the denominator being a non-zero, decimal
  (xbrli:nonZeroDecimal)</code></td><td>yes</td></tr><tr><td colspan="3">The following non-numeric types are all based on XML Schema built-in types that are not derived from either <code>decimal</code> or <code>string</code>.</td></tr><tr><td><code>stringItemType</code></td><td><code>string</code></td><td>no</td></tr><tr><td><code>booleanItemType</code></td><td><code>Boolean</code></td><td>no</td></tr><tr><td><code>hexBinaryItemType</code></td><td><code>hexBinary</code></td><td>no</td></tr><tr><td><code>base64BinaryItemType</code></td><td><code>base64Binary</code></td><td>no</td></tr><tr><td><code>anyURIItemType</code></td><td><code>anyURI</code></td><td>no</td></tr><tr><td><code>QNameItemType</code></td><td><code>QName</code></td><td>no</td></tr><tr><td><code>durationItemType</code></td><td><code>duration</code></td><td>no</td></tr><tr><td><code>dateTimeItemType</code></td><td><code>xbrli:dateUnion</code> (union of <code>date</code> and <code>dateTime</code>)</td><td>no</td></tr><tr><td><code>timeItemType</code></td><td><code>time</code></td><td>no</td></tr><tr><td><code>dateItemType</code></td><td><code>date</code></td><td>no</td></tr><tr><td><code>gYearMonthItemType</code></td><td><code>gYearMonth</code></td><td>no</td></tr><tr><td><code>gYearItemType</code></td><td><code>gYear</code></td><td>no</td></tr><tr><td><code>gMonthDayItemType</code></td><td><code>gMonthDay</code></td><td>no</td></tr><tr><td><code>gDayItemType</code></td><td><code>gDay</code></td><td>no</td></tr><tr><td><code>gMonthItemType</code></td><td><code>gMonth</code></td><td>no</td></tr><tr><td colspan="3">The following non-numeric types are all based on the XML Schema built-in types that are derived by restriction (and/or list) from <code>string</code>.</td></tr><tr><td><code>normalizedStringItemType</code></td><td><code>normalizedString</code></td><td>no</td></tr><tr><td><code>tokenItemType</code></td><td><code>token</code></td><td>no</td></tr><tr><td><code>languageItemType</code></td><td><code>language</code></td><td>no</td></tr><tr><td><code>NameItemType</code></td><td><code>Name</code></td><td>no</td></tr><tr><td><code>NCNameItemType</code></td><td><code>NCName</code></td><td>no</td></tr></tbody></table>

Some of these types, especially some of those that XML Schema has defined for backward compatibility with Document Type Definitions ("DTDs"), may never be needed for any XBRL application, but all are provided by XBRL for completeness and compatibility with XML Schema.

Example 33: Deriving an enumerated item type

<schema  
xmlns="http://www.w3.org/2001/XMLSchema"  
xmlns:my="http://www.someCompany.com/taxonomy" targetNamespace="http://www.someCompany.com/taxonomy" elementFormDefault="qualified">

<import namespace="http://www.xbrl.org/2003/instance" schemaLocation="http://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd"/>

<restriction base="xbrli:tokenItemType">

<enumeration value="MI"/>

<enumeration value="ON"/>

</restriction>

<element name="stateProvince" id="my\_stateProvince" xbrli:periodType="instant" substitutionGroup="xbrli:item" type="my:stateProvinceItemType"/>

</schema>

Meaning: Deriving new item types by restriction from the XBRL provided item types is the only allowed method for XBRL [Taxonomy Schemas](#taxonomy-schema). Earlier, in Example 18, the `stateProvinceType` was defined and used to define a sub-element of `  <segment>  `. Here, instead we define an XBRL concept appearing in the company's own taxonomy; note that the previously defined simple type is not used.

##### 5.1.1.3.1 The monetary, shares and pure data types

The [XBRL Instance](#XBRL-instance) schema defines the `monetary` data type, which specialises the XML Schema `decimal` type. All numeric elements in XBRL Taxonomies that represent monetary values **MUST** use the `monetaryItemType` data type or one derived from it. The `shares` data type represents share-based values and the `pure` data type represents growth rates, percentages, and other measures where an implicit numerator and denominator are expressed in the same [Units](#unit). See [**Section 5.1.1.3**](#_5.1.1.3) for definitions of the item types that use these special data types.

The XML Schema definitions of these data types are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><documentation>

Define the simple types used as a base for for item types

</documentation><simpleType name="monetary"><documentation>

the monetary type serves as the datatype for those financial concepts in a taxonomy which denote units in a currency. Instance items with this type must have a unit of measure from the ISO 4217 namespace of currencies.

</documentation>

<restriction base="decimal"/>

</simpleType><simpleType name="shares"><documentation>

This datatype serves as the datatype for share based financial concepts.

</documentation>

<restriction base="decimal"/>

</simpleType><simpleType name="pure"><documentation>

This datatype serves as the type for dimensionless numbers such as percentage change, growth rates, and other ratios where the numerator and denominator have the same units.

</documentation>

<restriction base="decimal"/>

</simpleType></schema>

##### 5.1.1.3.2 The fractionItemType data type

The values of some facts that are to be reported may be known exactly but it may not be possible to represent them exactly using any of the built-in data types provided for in XML Schema. Examples are fractional values whose decimal representation contains recurring digits such as 1/3 (whose decimal representation is 0.333333…). To enable XBRL instances to report these exact values, a complex type, `fractionItemType`, is provided. All values of `fractionItemType` are exact. The ` @precision` and ` @decimals` attributes **MUST** not occur on items with the `fractionItemType`.

The XML Schema constraints on the `fractionItemType` are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified">

<element name="numerator" type="decimal"/>

<element name="denominator" type="xbrli:nonZeroDecimal"/>

<complexType name="fractionItemType" final="extension"><sequence>

<element ref="xbrli:numerator"/>

<element ref="xbrli:denominator"/>

</sequence>

<attributeGroup ref="xbrli:essentialNumericItemAttrs"/>

</complexType></schema>

Example 34: Representing fractions

| Fractional value | Representation |
| --- | --- |
| 1/3 | <myTaxonomy:oneThird id="oneThird" unitRef="u1" contextRef="numC1">  <numerator>1</numerator>  <denominator>3</denominator>  </myTaxonomy:oneThird> |

The `numerator` element **MUST** contain numeric values. The denominator element **MUST** contain a numeric value that is non-zero and finite.

### 5.1.2 The <linkbaseRef> element

The `  <linkbaseRef>  ` element **MAY** be placed among the set of nodes identified by the XPath [\[XPath 1.0\]](#XPATH) path `"//xsd:schema/xsd:annotation/xsd:appinfo/*"` in a [Taxonomy Schema](#taxonomy-schema). In a taxonomy schema, the `  <linkbaseRef>  ` element identifies a [Linkbase](#linkbase) that **MUST** always participate in a [DTS](#DTS) if that taxonomy schema participates in the DTS.

The syntax of the `  <linkbaseRef>  ` element in [Taxonomy Schemas](#taxonomy-schema) is identical to the syntax of the `  <linkbaseRef>  ` element in XBRL instances. For more details, see [**Section 4.2.5**](#_4.2.5).

### 5.1.3 Defining custom role types - the <roleType> element

The `  <roleType>  ` element contains a custom role type definition. The `  <roleType>  ` element describes the custom role type by defining the ` @roleURI` of the role type, declaring the elements that the role type may be used on, and providing a human-readable definition of the role type.

Role types define custom values for the ` @xlink:role` attribute on the [\[XLINK\]](#XLINK) [Extended Link](#extended-link) and resource elements. The `  <roleType>  ` element **MUST** be located among the set of nodes identified by the `[XPath 1.0]` path `"//xsd:schema/xsd:annotation/xsd:appinfo/*"`. The role values that are defined by this specification (as standard role attribute values) **MUST NOT** be redefined using the `  <roleType>  ` element.

There **MUST NOT** be more than one `  <roleType>  ` element with the same ` @roleURI` attribute value within a [Taxonomy Schema](#taxonomy-schema). Within a [DTS](#DTS), there **MAY** be more than one `  <roleType>  ` element with the same ` @roleURI` attribute value. However, all `  <roleType>  ` elements with the same ` @roleURI` attribute value **MUST** be [S-Equal](#s-equal).

The value of the ` @roleURI` attribute identifies the ` @xlink:role` attribute value that is being defined. The values of the `  <usedOn>  ` sub-elements identify which elements are allowed to use the custom role type. Since `  <roleType>  ` elements are pointed to via a `  <roleRef>  ` element in [Linkbases](#linkbase) that use the custom role type, the `  <roleType>  ` element **MAY** have an ` @id` attribute.

Example 35: Defining a custom role type

Example: The role type definition of a role: `"http://www.mycomp.com/role/endnote"` to indicate those footnotes in an [XBRL Instance](#XBRL-instance) that ought to be presented only at the end of a document.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.mycomp.com/mytaxonomy" elementFormDefault="qualified"><link:roleType roleURI="http://www.mycompany.com/role/endnote" id="endnote"><link:definition>

A footnote that should be displayed only at the end of a document

</link:definition><link:usedOn>

link:footnote

</link:usedOn></link:roleType></schema>

This `  <roleType>  ` element defines a role that could be used as follows:

<link:roleRef xlink:type="simple" xlink:href="mycomproles.xsd#endnote" roleURI="http://www.mycomp.com/role/endnote"/>

<!---->

<link:footnote xlink:role="http://www.mycomp.com/role/endnote" xlink:type="resource" xlink:label="endnote1"> Excluding the effects of the merger and contingent liabilities. </link:footnote>

``The ` @xlink:role` value is   resolved back to the `  <roleType>  ` element by finding the `  <roleRef>  ` element with a   ` @roleURI` attribute value that matches the ` @xlink:role` value. The ` @xlink:href`   attribute on the `  <roleRef>  ` element points directly (via the fragment   identifier) to the `  <roleType>  ` element with the ` @id` attribute equal to "endnote"   in the mycomproles.xsd Taxonomy Schema. The `  <roleType>  ` element has a matching   ` @roleURI` attribute value.``

The XML Schema constraints on the `  <roleType>  ` element and its sub-elements are set out below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><documentation>

The element to use for human-readable definition of custom roles and arc roles.

</documentation><documentation>

Definitionof the usedOn element - used to identify what elements may use a taxonomy defined role or arc role value.

</documentation><element name="roleType"><documentation>

The roleType element definition - used to define custom role values in XBRL extended links.

</documentation><complexType><sequence>

<element ref="link:definition" minOccurs="0"/>

<element ref="link:usedOn" maxOccurs="unbounded"/>

</sequence>

<attribute name="roleURI" type="xlink:nonEmptyURI" use="required"/>

<attribute name="id" type="ID"/>

</complexType></element></schema>

#### 5.1.3.1 The @roleURI attribute

The ` @roleURI` attribute **MUST** occur and **MUST** contain the role value being defined. When the custom role type is used, the ` @xlink:role` attribute value matches the value of the ` @roleURI`.

#### 5.1.3.2 The @id attribute on <roleType> elements (optional)

The `  <roleType>  ` element **MAY** have an ` @id` attribute. The value of the ` @id` attribute **MUST** conform to the [\[XML\]](#XML) rules for attributes with the ID type ([http://www.w3.org/TR/REC-xml#NT-TokenizedType](http://www.w3.org/TR/REC-xml#NT-TokenizedType)). Providing an ` @id` attribute simplifies the content of the ` @xlink:href` attribute on `  <roleRef>  ` elements.

#### 5.1.3.3 The <definition> element in <roleType> elements (optional)

The `  <roleType>  ` element **MAY** contain a `  <definition>  ` element. The content of a `  <definition>  ` element **MUST** be a string giving meaning to the role type.

#### 5.1.3.4 The <usedOn> element in <roleType> elements

The `  <roleType>  ` element **MAY** contain one or more `  <usedOn>  ` elements. The `  <usedOn>  ` element identifies which elements **MAY** use the role type being defined. Within a `  <roleType>  ` element there **MUST NOT** be [S-Equal](#s-equal) `  <usedOn>  ` elements. Standard extended link elements and [Standard Resource Elements](#standard-resource-element) that use the defined role type **MUST** be identified with a `  <usedOn>  ` element in the `  <roleType>  ` element. Note that [Custom Extended Link Elements](#custom-extended-link-element) and [Custom Resource Elements](#custom-resource-element) are not governed by this constraint.

### 5.1.4 Defining custom arc role types - the arcroleType element

The `  <arcroleType>  ` element contains a custom arc role definition. The `  <arcroleType>  ` element describes the custom arc role type by declaring the arc role value, declaring the elements that the arc role type may be used on, declaring the type of cycles that are allowed for a network of relationships using the arc role type, and providing a human-readable definition of the meaning of the arc role type.

The `  <arcroleType>  ` element **MUST** be among the set of nodes identified by the `[XPath 1.0]` path `"//xsd:schema/xsd:annotation/xsd:appinfo/*"`. The arc role values defined by this specification (as standard arc role values) **MUST NOT** be redefined using the `  <arcroleType>  ` element.

There **MUST NOT** be more than one `  <arcroleType>  ` element with the same ` @arcroleURI` attribute value within a [Taxonomy Schema](#taxonomy-schema). Within a [DTS](#DTS), there **MAY** be more than one `  <arcroleType>  ` element with the same ` @arcroleURI` attribute value. However, all `  <arcroleType>  ` elements with the same ` @arcroleURI` attribute value **MUST** be [S-Equal](#s-equal).

The value of the ` @arcroleURI` identifies the ` @xlink:arcrole` attribute value that is being defined. The values of the `  <usedOn>  ` sub-elements identify which arcs may use this arc role type. Because `  <arcroleType>  ` elements are pointed to via an `  <arcroleRef>  ` element in [Linkbases](#linkbase) that use the custom arc role value, the `  <arcroleType>  ` element **MAY** have an ` @id` attribute.

Example 36: Defining a custom arc role value

Example: The definition of an arc role value: `"http://www.mycomp.com/arcrole/average-item"` that connects items in the calculation linkbase

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.mycomp.com/mytaxonomy" elementFormDefault="qualified"><link:usedOn>

link:calculationArc

</link:usedOn></schema>

<link:arcroleRef xlink:type="simple" xlink:href="mycomparcroles.xsd#average-item" arcroleURI="http://www.mycomp.com/arcrole/average-item"/>

<!---->

<link:calculationArc xlink:arcrole="http://www.mycomp.com/arcrole/average-item" xlink:type="arc" xlink:from="salesAverage" xlink:to="salesDetail" link:weight="1"/>

``The ` @xlink:arcrole` value   is resolved back to the `  <arcroleType>  ` element by finding the `  <arcroleRef>  ` element   with an ` @arcroleURI` attribute value that matches the ` @xlink:arcrole` value. The   ` @xlink:href` attribute on the `  <arcroleRef>  ` element points directly (via the   fragment identifier) to the `  <arcroleType>  ` element with the ` @id` attribute equal   to "average-item" in the mycomparcroles.xsd Taxonomy Schema. The arcroleType   element has a matching ` @arcroleURI` attribute value.``

The XML Schema constraints on the `  <arcroleType>  ` element and its sub-elements are set out below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><documentation>

The element to use for human-readable definition of custom roles and arc roles.

</documentation><documentation>

Definition of the usedOn element - used to identify what elements may use a taxonomy defined role or arc role value.

</documentation><element name="arcroleType"><documentation>

The arcroleType element definition - used to define custom arc role values in XBRL extended links.

</documentation><complexType><sequence>

<element ref="link:definition" minOccurs="0"/>

<element ref="link:usedOn" maxOccurs="unbounded"/>

</sequence>

<attribute name="arcroleURI" type="xlink:nonEmptyURI" use="required"/>

<attribute name="id" type="ID"/>

<restriction base="NMTOKEN">

<enumeration value="any"/>

<enumeration value="undirected"/>

<enumeration value="none"/>

</restriction></complexType></element></schema>

#### 5.1.4.1 The @arcroleURI attribute

The ` @arcroleURI` attribute **MUST** occur and **MUST** contain the arc role value being defined. When the defined arc role type is used, the ` @xlink:arcrole` attribute value matches the value of the ` @arcroleURI`.

#### 5.1.4.2 The @id attribute on <arcroleType> elements (optional)

The `  <arcroleType>  ` element **MAY** have an ` @id` attribute. The value of the ` @id` attribute **MUST** conform to the [\[XML\]](#XML) rules for attributes with the ID type ([http://www.w3.org/TR/REC-xml#NT-TokenizedType](http://www.w3.org/TR/REC-xml#NT-TokenizedType)). Providing an ` @id` attribute simplifies the content of the ` @xlink:href` attribute on `  <arcroleRef>  ` elements.

#### 5.1.4.3 The @cyclesAllowed attribute

The `  <arcroleType>  ` element **MUST** have a ` @cyclesAllowed` attribute that identifies the type of cycles that are allowed in a network of relationships as defined in [**Section 3.5.3.9.7.3**](#_3.5.3.9.7.3). Fully conformant XBRL processors **MUST** detect and signal networks of relationships with custom arc role types that violate the cycle restrictions documented with this attribute for networks of relationships with custom arcroles appearing on standard arcs within standard [Extended Links](#extended-link). Note that networks involving [Custom Arc Elements](#custom-arc-element) are not governed by this constraint, nor are networks involving [Standard Arc Elements](#standard-arc-element) appearing in custom extended links.

Networks of relationships in XBRL, as defined in [**Section 3.5.3.9.7.3**](#_3.5.3.9.7.3), form directed graphs. Because of the way XPointer [\[XPOINTER\]](#XPOINTER) is used in XBRL, the vertices (nodes) in the graph will always correspond to XML elements (see [**Section 3.5.4**](#_3.5.4)). In the case of the relationships specified in [**Section 5.2**](#_5.2), the vertices will correspond to either [Concepts](#concept) or resources. Each relationship in the network corresponds to a directed edge in the graph -- that is, an ordered pair of vertices `(u,v)`.

A path is a sequence of vertices `<v<sub>0</sub>, v<sub>1</sub>, ... ,v<sub>n-1</sub>, v<sub>n</sub>>`.

A directed graph contains a directed cycle if there is a path from any node back to itself when edge directions are respected. That is, when there exists a sequence of vertices `<v<sub>0</sub>, v<sub>1</sub>, ... ,v<sub>n-1</sub>, v<sub>n</sub>>` such that `v<sub>0</sub> = v<sub>n</sub>`, and for each `v<sub>i</sub>`, with `0<=i<n`, there exists a directed edge `(v<sub>i</sub>, v<sub>i+1</sub>)`.

Example 37: Directed cycles

Directed cycles `<a,a>` and `<b,c,b>`.

![[image002.jpg]]

A directed graph contains an undirected cycle if there is a path from any node back to itself when edge directions are ignored. That is, when there exists a sequence of vertices `<v<sub>0</sub>, v<sub>1</sub>, ... ,v<sub>n-1</sub>, v<sub>n</sub>>` such that `v<sub>0</sub> = v<sub>n</sub>`, and for each `v<sub>i</sub>`, with `0<=i<n`, there exists a directed edge `(v<sub>i</sub>, v<sub>i+1</sub>)` or a directed edge `(v<sub>i+1</sub>, v<sub>i</sub>)` that is distinct from all edges previously used in the path.

Example 38: Undirected cycles

Undirected cycles `<d,f,e,d>` and `<g,h,i,j,g>`. Note the backwards traversal of edges `(d,e)`, `(i,h)`, and `(g,j)`.

![[image003.jpg]]

Note that any graph that contains a directed cycle necessarily contains an undirected cycle.

The ` @cyclesAllowed` attribute **MUST** have one of the following values:

| Value | Meaning |
| --- | --- |
| any | The graph **MAY** contain any number of directed cycles and any number of undirected cycles. |
| undirected | The graph **MAY** contain any number of undirected cycles, but **MUST NOT** contain any directed cycles. |
| none | The graph **MUST NOT** contain directed or undirected cycles. |

#### 5.1.4.4 The <definition> element on <arcroleType> elements (optional)

The `  <arcroleType>  ` element **MAY** contain a `  <definition>  ` element. The `  <definition>  ` element **MUST** contain a string giving human-readable meaning to the arc role type.

#### 5.1.4.5 The <usedOn> element on <arcroleType> elements

The `  <arcroleType>  ` element **MAY** contain one or more `  <usedOn>  ` elements. The `  <usedOn>  ` element identifies which elements **MAY** use the arc role type being defined. [Standard Arc Elements](#standard-arc-element) that use the defined arc role type **MUST** be identified with a `  <usedOn>  ` element in the `  <arcroleType>  ` element whenever they appear in standard extended links. Note that [Custom Arc Elements](#custom-arc-element) are not governed by this constraint, nor are standard arc elements that appear in custom extended links. Within an `  <arcroleType>  ` element there **MUST NOT** be [S-Equal](#s-equal) `  <usedOn>  ` elements.

### 5.1.5 Prohibit <redefine>

The [\[XML Schema Structures\]](#XMLSCHEMA-STRUCTURES) `<redefine>` construct **MUST NOT** appear in any [Taxonomy Schema](#taxonomy-schema). Use of `<redefine>` could cause ambiguity in respect of the target of links in [Linkbases](#linkbase) that reference [Locators](#locator) and so it is prohibited.

## 5.2 Taxonomy linkbases

The [Extended Links](#extended-link) in a taxonomy provide additional information about [Concepts](#concept) by expressing relationships between concepts (inter-concept relationships) or associating concepts with documentation about their meaning. The extended links in a taxonomy are grouped into [Linkbases](#linkbase), as defined in [**Section 3.5.1.5**](#_3.5.1.5). Taxonomies currently use five different types of extended link: definition, calculation, presentation, label and reference. The first three types of extended link express inter-concept relationships, while the last two express relationships between concepts and their documentation.

An example of an inter-concept relationship is a calculation [Linkbase](#linkbase) that expresses a relationship between "cash" and "current assets" where "cash" sums up to "current assets". An example of a relationship between a [Concept](#concept) and additional documentation is a label linkbase that expresses a relationship between the concept "cash" and a human-readable label in English, such as "Cash" and additional labels for cash in other languages. Also, the label linkbase may contain additional labels for different purposes, such as a label of "Opening Cash Balance", "Closing Cash Balance" and "Total Cash". Although the concept is always referred to as "cash" the labels provide multiple ways of tagging the concept for display purposes.

The linkbases **MAY** exist in a separate document from the [Taxonomy Schema](#taxonomy-schema), although they **MAY** alternatively be embedded in the taxonomy schema among the set of nodes identified by the XPath [\[XPath 1.0\]](#XPATH) path `"//xsd:schema/xsd:annotation/xsd:appinfo/*"`. When a linkbase in a taxonomy is not embedded in the taxonomy schema document, the taxonomy schema **MUST** contain a `  <linkbaseRef>  ` to point to the document containing the linkbase.

There are five kinds of [Extended Links](#extended-link) used in XBRL taxonomies.

- Relation links (calculation, definition, and presentation) manage the relations between taxonomy elements.
- Label links manage the text associated with taxonomy elements in various languages.
- Reference links manage the references to authoritative literature (either online or paper).

Each of these [Extended Links](#extended-link) **MUST** be held in an [\[XLINK\]](#XLINK) document container. The [\[XLINK\]](#XLINK) document container **MUST** be a `  <linkbase>  ` element located either:

1. among the set of nodes identified by the XPath [\[XPath 1.0\]](#XPATH) path `"//xsd:schema/xsd:annotation/xsd:appinfo/*"` in the [Taxonomy Schema](#taxonomy-schema); or
2. at the root element of a separate document.

In the presentation, calculation, and definition [Extended Links](#extended-link) in a [DTS](#DTS), [Arcs](#arc) organise XBRL [Concepts](#concept) into networks of relationships that associate each concept with other concepts. In label and reference extended links, arcs represent networks of relationships between concepts and their documentation (labels and references). See [**Section 3.5.3.9.7.3**](#_3.5.3.9.7.3) for details about networks of relationships.

Each network of inter-concept relationships in a [DTS](#DTS) **MAY** contain root [Concepts](#concept). A root concept is an XBRL concept that, for a given network of relationships, is not an XML fragment on the "to" side of any relationship in the network. It is possible for a concept to be a root concept in one network of relationships but not in another network of relationships. Note that this implies that any disconnected concept, i.e. one that is neither on the "to" side nor the "from" side of any relationship in any network, is a root concept.

The presentation, definition, and calculation [Extended Links](#extended-link) are not required in order to specify the formatting of a report derived from a collection of [XBRL Instances](#XBRL-instance). However, XBRL instance consuming applications are free to use the semantic information provided in a [DTS](#DTS) to format such reports as they deem appropriate.

Taxonomy authors may or may not find it useful to keep the networks of presentation, calculation and definition relationships in some kind of correspondence.

Inter-concept relationships and relationships between [Concepts](#concept) and resources that document them **MAY** be overridden or prohibited (see [**Section 3.5.3.9.7**](#_3.5.3.9.7) for details). As an example of prohibition, consider the situation of a third party desiring to create a new "sub-total" concept intervening between "children" concepts that already have summation-item arcs to the "total" concept (see [**Section 5.2.5.2**](#_5.2.5.2) for details about summation-item arcs and calculation relationships in [Extended Links](#extended-link)). The creator of the sub-total concept will add arcs from the sub-total Concept to the children concepts and from the total concept to the sub-total concept. There would then be two paths from the children concepts to the total concept, one using the new arcs through the sub-total concept, and the other using the original arcs direct from the summation concept. In the case of calculation links, this could result in the double counting of values. The creator of the sub-total concept **SHOULD** create prohibiting arcs to prevent this, effectively removing the arcs going directly from the total concept to the children concepts from the network of relationships in the calculation.

Example 39: Using relationship prohibition to insert a new sub-total into a calculation network

![[image004.png]]

One or more relationships in a network of relationships can form a cycle (that is, there may be a path in the network from an XML fragment back to that same XML fragment without involving any one relationship more than once). Depending on the semantics of the relationships in a network, different types of cycles may be semantically coherent, or they may represent a semantic inconsistency that processing applications **MAY** choose to detect.

Fully conformant XBRL processors **MUST** detect cycles that constitute semantic inconsistencies. Semantically inconsistent cycles are identified for each network that is given semantic meaning in this specification.

Example 40: Types of cycles

![[image005.png]]

To illustrate networks of relationships between [Concepts](#concept), consider the following concepts that might be defined in a taxonomy (note that the label would not be part of the element; labels are just shown to provide clarity):

Example 41: Elements of a financial reporting taxonomy

| Label | Element Name | Balance | Substitution Group |
| --- | --- | --- | --- |
| Income Statement | `incomeStatement` |  |  |
| … other taxonomy elements | `(various)` | (various) | (various) |
| Net Income Before Tax | `netIncomeBeforeTax` | credit | item |
| Taxes | `taxes` | debit | item |
| Net Income After Tax | `netIncomeAfterTax` | credit | item |
| Extraordinary Items | `extraordinaryItems` | debit | item |
| Net Income | `netIncome` | credit | item |
| Performance Measures | `performanceMeasures` |  | item |

Suppose that the mathematical relations that exist between the [Concepts](#concept) expressed as elements within the taxonomy as documented by some source are as follows:

1. `netIncomeAfterTax` = `netIncomeBeforeTax` - `taxes`
2. `netIncome` = `netIncomeAfterTax` - `extraordinaryItems`

The calculation [Linkbase](#linkbase) might then contain calculation extended links to facilitate computation of `netIncome, netIncomeBeforeTax, netIncomeAfterTax, `per the formulae above and expressed in a tree hierarchy in an application.

Example 42: Hierarchy in a calculation linkbase

| ![[image006.png]] | Example: Calculation hierarchy in which each item contributes to a summation.  Arcs are annotated with the numeric weight in parentheses. The weight indicates the ` @weight` attribute value of the calculation link expressing how the element contributes to the calculation/summation. |
| --- | --- |

The definition [Linkbase](#linkbase) might also contain definition extended links that relate [Concepts](#concept) to other concepts. In the case below, `performanceMeasures` is an element defined in the taxonomy and the types of performance measures are: `netIncome, netIncomeBeforeTax, `and `netIncomeAfterTax. `The ` @xlink:arcrole` of the link, an absolute URI such as `http://www.xbrl.org/2003/arcrole/general-special,` explains the type of definition relationship of the relation. See [**Section 3.5.3.9.4**](#_3.5.3.9.4) for details.

Example 43: Hierarchy of general-special arcs in a definition linkbase

| ![[image007.png]] | Example: Definition hierarchy in which various concepts are defined to be "Performance Measures."  Arcs are annotated with their "order" attribute used for presenting the hierarchy. |
| --- | --- |

Presentation links are used to arrange taxonomy elements into a hierarchy and specific ordering. In general, different uses will require different sets of presentation links. There is one set of users - taxonomy developers and domain experts working with a taxonomy - whose presentation needs remain relevant throughout the entire lifecycle of a taxonomy. In some sense this view is "context free" as opposed to the presentation of instance data that is "context dependent." When taxonomies are published they cannot contain all possible presentations but they **MAY** contain at least one "developer's eye" view, which is "context free" in the sense that it does not need to take [XBRL Instance](#XBRL-instance) contexts into account. The presentation [Linkbase](#linkbase) in this example could contain presentation links to organise [Concepts](#concept) to look like line items in a financial statement. Another presentation linkbase could contain links to organise a subset of these same concepts into a data collection form.

Example 44: Hierarchy in a presentation linkbase

| ![[image008.png]] | Example: Presentation hierarchy that mimics the order in which line items might appear on an income statement.  This view might be used in applications to present taxonomies to users of the application. The arcs are annotated with their "order" attribute. |
| --- | --- |

In these examples, the three [Linkbases](#linkbase) are trees, but they need not be strict trees at all. This is particularly true for the calculation linkbase. There are several ways to calculate movements in Equity, for example: one might net the issuing and retirement of common stock, net the issuing and retirement of preferred stock, and add those two - or one might add up all the issuance of stock whether common or preferred, and net it against the retirement of common and preferred. Although the calculations are hierarchical (that is, there are no loops), they do not form a tree.

### 5.2.1 The <linkbase> element

The `  <linkbase>  ` element is fully documented in [**Section 3.5.2**](#_3.5.2).

### 5.2.2 The <labelLink> element

The `  <labelLink>  ` element is an extended link. Its generic syntax is documented in [**Section 3.5.3**](#_3.5.3). It is intended to contain relationships between [Concepts](#concept) and textual documentation and labels for those concepts.

The XML Schema constraints on the `  <labelLink>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><element name="labelLink" substitutionGroup="xl:extended"><documentation>

label extended link element definition

</documentation><restriction base="xl:extendedType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="link:documentation"/>

<element ref="link:loc"/>

<element ref="link:labelArc"/>

<element ref="link:label"/>

</choice>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></element></schema>

#### 5.2.2.1 Locators in <labelLink> elements

`  <labelLink>  ` elements **MUST NOT** contain [Locators](#locator) that are not `  <loc>  ` elements. `  <loc>  ` elements are documented in detail in [**Section 3.5.3.7**](#_3.5.3.7). The `  <loc>  ` element, when used in a `  <labelLink>  `, **MUST** only point to [Concepts](#concept) in [Taxonomy Schemas](#taxonomy-schema) or to label resources as defined in 5.2.2.2.

#### 5.2.2.2 The <label> element

Although each taxonomy defines a single set of elements representing a set of business reporting [Concepts](#concept), the human-readable XBRL documentation for those concepts, including labels (strings used as human-readable names for each concept) and other explanatory documentation, is contained in a resource element in the label [Linkbase](#linkbase). The resource uses the ` @xml:lang` attribute to specify the language used (via the XML standard `lang` attribute) and an optional classification of the purpose of the documentation (via a `role` attribute).

This ability to provide documentation in a variety of different languages enables XBRL [Concepts](#concept) to be more easily reported in a multilingual environment.

Documentation of XBRL [Concepts](#concept) **MUST** be contained in `  <label>  ` elements in `  <labelLink>  ` extended links. The `  <label>  ` element is an [\[XLINK\]](#XLINK) resource. Its generic syntax is documented in [**Section 3.5.3.8**](#_3.5.3.8). The `  <label>  ` element **MUST** have the standard ` @xml:lang` attribute, and it **MUST** appear inside a `  <labelLink>  ` element. This content of the `  <label>  ` element is mixed, allowing a simple string, a fragment of XHTML or a combination of both.

XBRL processors are NOT **REQUIRED** to detect or display [Concept](#concept) documentation that appears anywhere other than in a `  <label>  ` element.

The XML Schema constraints on the `  <label>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><element name="label" substitutionGroup="xl:resource"><documentation>

Definition of the label resource element.

</documentation><extension base="xl:resourceType"><sequence>

<any namespace="http://www.w3.org/1999/xhtml" processContents="skip" minOccurs="0" maxOccurs="unbounded"/>

</sequence>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</extension></element></schema>

Example 45: Label resource examples

<label xlink:type="resource" xlink:role="http://www.xbrl.org/2003/role/label" xlink:label="ci\_currentAssets\_en" xml:lang="en">Current Assets</label>

<label  
xmlns:xhtml="http://www.w3.org/1999/xhtml" xlink:type="resource" xlink:role="http://www.xbrl.org/2003/role/label" xlink:label="ci\_netIncome\_en" xml:lang="en">

<xhtml:b>Net Income</xhtml:b>

(Loss)</label>

##### 5.2.2.2.1 The @xml:lang attribute on <label> elements

All `  <label>  ` resources **MUST** have an ` @xml:lang` attribute identifying the language used for the content of the label. The value of the ` @xml:lang` attribute **MUST** conform to [\[XML\]](#XML) rules. (See [http://www.w3.org/TR/2000/REC-xml-20001006#sec-lang-tag](http://www.w3.org/TR/2000/REC-xml-20001006#sec-lang-tag) for details).

##### 5.2.2.2.2 The @xlink:role attribute on <label> elements (optional)

Label resources **MAY** contain an ` @xlink:role` attribute, which **SHOULD** distinguish between `  <label>  ` resources by the nature of the XBRL [Concept](#concept) documentation that they provide. Table 8 specifies all standard ` @xlink:role` attribute values and their meanings for label resources.

Table 8: Standard label role attribute values.

| `  <label>  ` resource ` @xlink:role` attribute value | Meaning |
| --- | --- |
| `(Omitted role attribute)` | Standard label for a [Concept](#concept). |
| `http://www.xbrl.org/2003/role/label` | Standard label for a [Concept](#concept). |
| `http://www.xbrl.org/2003/role/terseLabel` | Short label for a [Concept](#concept), often omitting text that should be inferable when the concept is reported in the context of other related concepts. |
| `http://www.xbrl.org/2003/role/verboseLabel` | Extended label for a [Concept](#concept), making sure not to omit text that is required to enable the label to be understood on a stand alone basis. |
| `http://www.xbrl.org/2003/role/positiveLabel` `http://www.xbrl.org/2003/role/positiveTerseLabel` `http://www.xbrl.org/2003/role/positiveVerboseLabel` `http://www.xbrl.org/2003/role/negativeLabel` `http://www.xbrl.org/2003/role/negativeTerseLabel` `http://www.xbrl.org/2003/role/negativeVerboseLabel` `http://www.xbrl.org/2003/role/zeroLabel` `http://www.xbrl.org/2003/role/zeroTerseLabel` `http://www.xbrl.org/2003/role/zeroVerboseLabel` | Label for a [Concept](#concept), when the value being presented is positive (negative, zero). For example, the standard and standard positive labels might be "profit after tax" and the standard negative labels "loss after tax", the terse label and terse positive labels might both be "profit", while the negative terse label might be "loss". |
| `http://www.xbrl.org/2003/role/totalLabel` | The label for a [Concept](#concept) for use in presenting values associated with the concept when it is being reported as the total of a set of other values. |
| `http://www.xbrl.org/2003/role/periodStartLabel` `http://www.xbrl.org/2003/role/periodEndLabel` | The label for a [Concept](#concept) with `periodType="instant"` for use in presenting values associated with the concept when it is being reported as a start (end) of period value. |
| `http://www.xbrl.org/2003/role/documentation` | Documentation of a [Concept](#concept), providing an explanation of its meaning and its appropriate usage and any other documentation deemed necessary. |
| `http://www.xbrl.org/2003/role/definitionGuidance` | A precise definition of a [Concept](#concept), providing an explanation of its meaning and its appropriate usage. |
| `http://www.xbrl.org/2003/role/disclosureGuidance` | An explanation of the disclosure requirements relating to the [Concept](#concept). Indicates whether the disclosure is - mandatory (i.e. prescribed by authoritative literature); - recommended (i.e. encouraged by authoritative literature; - common practice (i.e. not prescribed by authoritative literature, but disclosure is common); - structural completeness (i.e., included to complete the structure of the taxonomy). |
| `http://www.xbrl.org/2003/role/presentationGuidance` | An explanation of the rules guiding presentation (placement and/or labelling) of this [Concept](#concept) in the context of other concepts in one or more specific types of business reports. For example, "Net Surplus should be disclosed on the face of the Profit and Loss statement". |
| `http://www.xbrl.org/2003/role/measurementGuidance` | An explanation of the method(s) required to be used when measuring values associated with this [Concept](#concept) in business reports. |
| `http://www.xbrl.org/2003/role/commentaryGuidance` | Any other general commentary on the [Concept](#concept) that assists in determining definition, disclosure, measurement, presentation or usage. |
| `http://www.xbrl.org/2003/role/exampleGuidance` | An example of the type of information intended to be captured by the [Concept](#concept). |

Example 46: Arc between a concept and one of its labels

<label xlink:type="resource" xlink:label="A" xlink:role="http://www.xbrl.org/2003/role/label" xml:lang="en">Current Assets</label>

<loc xlink:type="locator" xlink:href="us\_bs\_v2.xsd#currentAssets" xlink:label="B"/>

<labelArc xlink:type="arc" xlink:from="B" xlink:to="A" xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-label"/>

Meaning: The `  <label>  ` resource contains the text of the label and the arc element associates the concept with the label.

#### 5.2.2.3 The <labelArc> element

The `  <labelArc>  ` element is an [\[XLINK\]](#XLINK) arc. Its generic syntax is defined in [**Section 3.5.3.9**](#_3.5.3.9). In `  <labelLink>  ` elements, it connects [Concepts](#concept) with `  <label>  ` resources.

The XML Schema constraints on the `  <labelArc>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><documentation>

Concrete arc for use in label extended links.

</documentation></schema>

One standard arc role value is defined for `  <labelArc>  ` elements. Its value is:

`http://www.xbrl.org/2003/arcrole/concept-label`

This arc role value is for use on a `  <labelArc>  ` from a concept [Locator](#locator) (`  <loc>  ` element) to a `  <label>  ` element and it indicates that the label conveys human-readable information about the [Concept](#concept).

`  <labelArc>  ` elements cannot describe cyclic relationships between [Concepts](#concept) because they only relate concepts to `  <label>  ` resources, not other concepts. For this reason, no restrictions on cyclic `  <labelArc>  ` networks are prescribed.

The label elements that participate in a relationship described by a `  <labelArc>  ` element **MUST** be [\[XLINK\]](#XLINK) local resources except when the use attribute on the labelArc is "prohibited", in which case the `  <label>  ` elements **MAY** be [\[XLINK\]](#XLINK) local resources and/or [\[XLINK\]](#XLINK) remote resources.

### 5.2.3 The <referenceLink> element

The `  <referenceLink>  ` element is an extended link. Its generic syntax is documented in [**Section 3.5.3**](#_3.5.3). It is intended to contain relationships between [Concepts](#concept) and references to authoritative statements in the published business, financial and accounting literature that give meaning to the concepts.

The XML Schema constraints on the `  <referenceLink>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><element name="referenceLink" substitutionGroup="xl:extended"><documentation>

reference extended link element definition

</documentation><restriction base="xl:extendedType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="link:documentation"/>

<element ref="link:loc"/>

<element ref="link:referenceArc"/>

<element ref="link:reference"/>

</choice>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></element></schema>

Example 47: Sample values of ` @xlink:role` for several `  <referenceLink>  ` elements

- `http://www.my.org/role/balanceSheet`
- `http://www.my.org/role/incomeStatement`
- `http://www.my.org/role/statementOfComprehensiveIncome`
- `http://www.my.org/role/statementOfStockholdersEquity`
- `http://www.my.org/role/cashFlows`
Meaning: The taxonomy has given a "role" to each `referenceLink   extended ` link to partition the [Extended Links](#extended-link) in an accounting-related taxonomy based on which part of a financial statement they relate to.

#### 5.2.3.1 Locators in <referenceLink> elements

`  <referenceLink>  ` elements **MUST NOT** contain [Locators](#locator) that are not `  <loc>  ` elements. `  <loc>  ` elements are documented in detail in [**Section 3.5.3.7**](#_3.5.3.7). The `  <loc>  ` element, when used in a `  <referenceLink>  `, **MUST** only point to [Concepts](#concept) in [Taxonomy Schemas](#taxonomy-schema) or to reference resources as defined in [**Section 5.2.3.2**](#_5.2.3.2).

#### 5.2.3.2 The reference element

The `  <reference>  ` element enables XBRL taxonomies to ground the definitions of [Concepts](#concept) in authoritative statements in published business, financial and accounting literature. The `  <reference>  ` element **SHOULD** only provide information necessary to find the reference materials that are relevant to understanding appropriate usage of the concept being defined. They **MUST NOT** contain the content of those reference materials themselves. Where textual documentation is required to complete the definition of an XBRL context, this **MUST** be contained in XBRL `  <label>  ` elements as documented in [**Section 5.2.2.2**](#_5.2.2.2).

The `  <reference>  ` element is an [\[XLINK\]](#XLINK) resource. Its generic syntax is documented in [**Section 3.5.3.8**](#_3.5.3.8). The `  <reference>  ` element **MUST** appear inside a `  <referenceLink>  ` element.

The XML Schema constraints on the `  <reference>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><documentation>

Definition of the reference part element - for use in reference resources.

</documentation><element name="reference" substitutionGroup="xl:resource"><documentation>

Definition of the reference resource element.

</documentation><sequence>

<element ref="link:part" minOccurs="0" maxOccurs="unbounded"/>

</sequence></element></schema>

Reference elements are composed of parts. Since the division of references into parts varies in every jurisdiction, `part` is an abstract element defined in this specification. Taxonomies **MAY** define elements that substitute for `part`, allowing them to be included inside reference elements.

Example 48: Arc between a concept and supporting references

<linkbase  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns:ref="http://www.xbrl.org/2003/ref"  
xmlns="http://www.xbrl.org/2003/linkbase"><referenceLink xlink:type="extended" xlink:role="http://www.xbrl.org/2003/role/link">

<!---->

<loc xlink:type="locator" xlink:href="samp001.xsd#s\_customerName" xlink:label="s\_customerName"/>

<!---->

<referenceArc xlink:type="arc" xlink:from="s\_customerName" xlink:to="s\_customerName\_REF" xlink:arcrole="http://www.xbrl.org/2003/arcrole/concept-reference"/>

<!---->

<reference xlink:type="resource" xlink:label="s\_customerName\_REF" xlink:role="http://www.xbrl.org/2003/role/definitionRef">

<ref:name>Handbook of Business Reporting</ref:name>

<ref:pages>5</ref:pages>

</reference><reference xlink:type="resource" xlink:label="s\_customerName\_REF" xlink:role="http://www.xbrl.org/2003/role/measurementRef">

<ref:name>Handbook of Business Reporting</ref:name>

<ref:pages>45-50</ref:pages>

</reference></referenceLink></linkbase>

Meaning: The `  <reference>  ` elements contain two literature citations, with different ` @xlink:role` attributes to distinguish them. The arc relates the concept at to both references. The elements `name` and `pages` are defined as members of the `part` substitution group in the taxonomy referred to by the `ref:` namespace prefix, as shown below:

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns:ref="http://www.xbrl.org/2003/ref"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/ref" elementFormDefault="qualified">

<import namespace="http://www.xbrl.org/2003/linkbase" schemaLocation="xbrl-linkbase.xsd"/>

<element name="name" type="string" substitutionGroup="link:part"/>

<element name="number" type="string" substitutionGroup="link:part"/>

<element name="paragraph" type="string" substitutionGroup="link:part"/>

<element name="subparagraph" type="string" substitutionGroup="link:part"/>

<element name="clause" type="string" substitutionGroup="link:part"/>

<element name="pages" type="string" substitutionGroup="link:part"/>

</schema>

Example 49: Reference resource

<reference xlink:type="resource" xlink:label="ci\_propertyPlantAndEquipmentNet\_APB">

<ci:name>ABP</ci:name>

<ci:page>42</ci:page>

</reference>

##### 5.2.3.2.1 The @xlink:role attribute on reference elements (optional)

Reference elements **MAY** contain an optional ` @xlink:role` attribute, which **MUST** distinguish between reference elements by the nature of the XBRL [Concept](#concept) documentation that they make external reference to. Table 9 specifies the standard ` @xlink:role` attribute values and their meanings for reference resources. These parallel the standard ` @xlink:role` attribute values for `  <label>  ` resources.

Table 9: Reference role attribute values.

| `reference` resource ` @xlink:role` attribute value | Meaning |
| --- | --- |
| `(Omitted role   attribute)` | Standard reference for a [Concept](#concept) |
| `http://www.xbrl.org/2003/role/reference` | Standard reference for a [Concept](#concept) |
| `http://www.xbrl.org/2003/role/definitionRef` | Reference to documentation that details a precise definition of the [Concept](#concept). |
| `http://www.xbrl.org/2003/role/disclosureRef` `http://www.xbrl.org/2003/role/mandatoryDisclosureRef` `http://www.xbrl.org/2003/role/recommendedDisclosureRef` | Reference to documentation that details an explanation of the disclosure requirements relating to the [Concept](#concept). Specified categories include: - mandatory - recommended |
| `http://www.xbrl.org/2003/role/unspecifiedDisclosureRef` | Reference to documentation that details an explanation of the disclosure requirements relating to the [Concept](#concept). Unspecified categories include, but are not limited to: - common practice - structural completeness The latter categories do not reference documentation but are indicated in the link role to indicate why the [Concept](#concept) has been included in the taxonomy. |
| `http://www.xbrl.org/2003/role/presentationRef` | Reference to documentation which details an explanation of the presentation, placement or labelling of this [Concept](#concept) in the context of other [Concepts](#concept) in one or more specific types of business reports |
| `http://www.xbrl.org/2003/role/measurementRef` | Reference concerning the method(s) required to be used when measuring values associated with this [Concept](#concept) in business reports |
| `http://www.xbrl.org/2003/role/commentaryRef` | Any other general commentary on the [Concept](#concept) that assists in determining appropriate usage |
| `http://www.xbrl.org/2003/role/exampleRef` | Reference to documentation that illustrates by example the application of the [Concept](#concept) that assists in determining appropriate usage. |

#### 5.2.3.3 The <referenceArc> element

The `  <referenceArc>  ` element is an [\[XLINK\]](#XLINK) arc. Its generic syntax is defined in [**Section 3.5.3.9**](#_3.5.3.9). In `  <referenceLink>  ` elements, it connects [Concepts](#concept) with `reference` resources.

The XML Schema constraints on the `  <referenceArc>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><documentation>

Concrete arc for use in reference extended links.

</documentation></schema>

One standard arc role value is defined for `  <referenceArc>  ` elements. Its value is:

`http://www.xbrl.org/2003/arcrole/concept-reference`

This arc role value is for use on a `  <referenceArc>  ` from a concept [Locator](#locator) (`  <loc>  ` element) to a `reference` resource and it indicates that the reference is to materials documenting the meaning of the [Concept](#concept).

`  <referenceArc>  ` elements cannot describe cyclic relationships between [Concepts](#concept) because they represent relationships only between concepts and `reference` resources, not between concepts and other concepts. For this reason, no restrictions on cyclic `  <referenceArc>  ` networks are prescribed.

The reference elements that participate in a relationship described by a `  <referenceArc>  ` element **MUST** be [\[XLINK\]](#XLINK) local resources except when the use attribute on the referenceArc is "prohibited", in which case the reference elements **MAY** be [\[XLINK\]](#XLINK) local resources and/or [\[XLINK\]](#XLINK) remote resources.

### 5.2.4 The <presentationLink> element

The `  <presentationLink>  ` element is an [Extended Link](#extended-link). Its generic syntax is documented in [**Section 3.5.3**](#_3.5.3). It is intended to describe presentational relationships between [Concepts](#concept) in taxonomies. The `  <presentationLink>  ` element **MUST NOT** contain [\[XLINK\]](#XLINK) resources.

The XML Schema constraints on the `  <presentationLink>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><element name="presentationLink" substitutionGroup="xl:extended"><documentation>

presentation extended link element definition.

</documentation><restriction base="xl:extendedType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="link:documentation"/>

<element ref="link:loc"/>

<element ref="link:presentationArc"/>

</choice>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></element></schema>

#### 5.2.4.1 Locators in <presentationLink> elements

`  <presentationLink>  ` elements **MUST NOT** contain [Locators](#locator) that are not `  <loc>  ` elements. `  <loc>  ` elements are documented in detail in [**Section 3.5.3.7**](#_3.5.3.7). The `  <loc>  ` element, when used in a `  <presentationLink>  `, **MUST** only point to [Concepts](#concept) in [Taxonomy Schemas](#taxonomy-schema).

#### 5.2.4.2 The <presentationArc> element

The `  <presentationArc>  ` element is an [\[XLINK\]](#XLINK) arc. Its generic syntax is defined in [**Section 3.5.3.9**](#_3.5.3.9). The `  <presentationArc>  ` element defines how [Concepts](#concept) relate to one another for presentation.

The XML Schema constraints on the syntax for `  <presentationArc>  ` elements are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><complexType><documentation>

Extension of the extended link arc type for presentation arcs. Adds a preferredLabel attribute that documents the role attribute value of preferred labels (as they occur in label extended links).

</documentation><restriction base="anyURI">

<minLength value="1"/>

</restriction></complexType></schema>

Example 50: A presentation arc

<presentationArc xlink:type="arc" xlink:from="ci\_currentAssets" xlink:to="ci\_prepaidExpenses" xlink:arcrole="http://www.xbrl.org/2003/arcrole/parent-child" order="4"/>

Meaning: Current assets must be presented as the parent of prepaid expenses. The prepaid expense element appears after any children of current assets whose ` @order` is less than 4, and appears before any children of current assets whose ` @order` is more than 4.

A taxonomy **MAY** define [Abstract Elements](#abstract-element) (Table 1) and create presentation relationships to and/or from them, to allow taxonomy presentation applications to present groups of [Concepts](#concept), even when those [Concepts](#concept) are not related in any other way such as by calculation associations. Abstract elements **SHOULD** be in the substitution group for the abstract XBRL `  <item>  ` element (see [**Section 4.6**](#_4.6)).

Example 51: An abstract concept definition

<element name="balanceSheet" id="ci\_balanceSheet" type="xbrli:stringItemType" substitutionGroup="xbrli:item" abstract="true" xbrli:periodType="instant"/>

Meaning: The `balanceSheet` element exists in the taxonomy only to organise other elements; it **MUST NOT** appear in an [XBRL Instance](#XBRL-instance). It has the arbitrary `type` attribute of `xbrli:stringItemType` to satisfy the requirements of [**Section 4.6**](#_4.6) and the arbitrary ` @periodType` attribute `xbrli:periodType="instant"` to satisfy the requirements of [**Section 5.1.1.1**](#_5.1.1.1). These arbitrary attributes add no semantic information.

One standard arc role value is defined for `  <presentationArc>  ` elements. Its value is:

`http://www.xbrl.org/2003/arcrole/parent-child`

Such arcs are referred to as "parent-child" arcs. Parent-child arcs represent relationships between parent [Concepts](#concept) and child concepts and indicate that, in a hierarchical view of XBRL information, it is appropriate to show the child concept as a child of the parent concept. Parent-child arcs **MUST** represent relationships only between concepts (which, by definition, are in the `  <tuple>  ` or `  <item>  ` substitution groups).

Because a network of parent-child arcs represents a hierarchy of [Concepts](#concept), it makes no sense for such a network to document that a concept is its own descendant. For this reason, directed cycles are not allowed in networks of parent-child relationships. Fully conformant XBRL processors **MUST** detect and signal directed cycles in networks of parent-child relationships.

##### 5.2.4.2.1 The @preferredLabel attribute (optional)

The ` @preferredLabel` attribute is a URI that **MAY** be supplied on a parent-child arc to indicate the most appropriate kind of label to use when presenting the arc's child [Concept](#concept). If supplied, the value of the ` @preferredLabel` attribute **MUST** be equal to an ` @xlink:role` attribute value on a `  <label>  ` resource (in a `  <labelLink>  ` extended link) that is the target of a concept-label arc from the `  <presentationArc>  ` element's child concept.

XBRL processors **MAY** use the value of the ` @preferredLabel` attribute to choose between different labels that have been associated with the one [Concept](#concept). This can be particularly useful when a given concept is used in a variety of ways within a [DTS](#DTS). For example, cash can be used in the balance sheet and as the starting and ending balances in a cash flow statement. Each appearance of the concept in a set of presentation links **MAY** use this feature to indicate a different preferred label.

The ` @xlink:role` attribute value on the label [Extended Link](#extended-link) containing the preferred label and the ` @xlink:role` attribute value on the presentation extended link containing the `  <presentationArc>  ` element do not have to be equal.

### 5.2.5 The <calculationLink> element

The `  <calculationLink>  ` element is an [Extended Link](#extended-link). Its generic syntax is documented in [**Section 3.5.3**](#_3.5.3). It describes calculation relationships between [Concepts](#concept) in taxonomies. The `  <calculationLink>  ` element **MUST NOT** contain [\[XLINK\]](#XLINK) resources.

The XML Schema constraints on the `  <calculationLink>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><element name="calculationLink" substitutionGroup="xl:extended"><documentation>

calculation extended link element definition

</documentation><restriction base="xl:extendedType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="link:documentation"/>

<element ref="link:loc"/>

<element ref="link:calculationArc"/>

</choice>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></element></schema>

#### 5.2.5.1 Locators in <calculationLink> elements

`  <calculationLink>  ` elements **MUST NOT** contain [Locators](#locator) that are not `  <loc>  ` elements. `  <loc>  ` elements are documented in detail in [**Section 3.5.3.7**](#_3.5.3.7). The `  <loc>  ` element, when used in a `  <calculationLink>  `, **MUST** only point to [Concepts](#concept) in [Taxonomy Schemas](#taxonomy-schema).

#### 5.2.5.2 The <calculationArc> element

The `  <calculationArc>  ` element is an [\[XLINK\]](#XLINK) arc. Its generic syntax is defined in [**Section 3.5.3.9**](#_3.5.3.9). The `  <calculationArc>  ` element defines how [Concepts](#concept) relate to one another for calculation purposes.

The XML Schema constraints on the syntax for `  <calculationArc>  ` elements are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><complexType><documentation>

Extension of the extended link arc type for calculation arcs. Adds a weight attribute to track weights on contributions to summations.

</documentation><extension base="xl:arcType">

<attribute name="weight" type="decimal" use="required"/>

</extension></complexType></schema>

One standard arc role value is defined for `  <calculationArc>  ` elements. Its value is:

`http://www.xbrl.org/2003/arcrole/summation-item`

Such arcs are referred to as "summation-item" arcs. Summation-item arcs **MUST** represent relationships only between [Concepts](#concept) that are in the `  <item>  ` substitution group and whose type is numeric (see [**Section 5.1.1.3**](#_5.1.1.3)). They represent aggregation relationships between concepts and are referred to as "summation-item" relationships. Each of these relationships is between one concept, referred to as the summation concept, and another concept, referred to as the contributing concept.

A complete summation-item arc set for a given summation concept is defined in the context of the [DTS](#DTS) supporting an XBRL instance. It is the set of all summation-item arcs, defined in `  <calculationLink>  ` [Extended Links](#extended-link) with the same ` @xlink:role` attribute value that associate contributing concepts to the given summation concept. A summation item is an occurrence of a summation concept in an [XBRL Instance](#XBRL-instance).

For a given [Extended Link](#extended-link) role **R** and summation item **S**, another item **I** is a contributing item if all of the following conditions are satisfied:

1. **I** is an occurrence of a contributing concept for **S** in **R**.
2. **I** is [C-Equal](#c-equal) and [U-Equal](#u-equal) to **S**.
3. **I** is a descendant of the parent of **S** (i.e. **I** is a sibling of **S** or a descendant of one of the siblings of **S**).
4. **I** is not nil-valued (i.e. it does not have an xsi:nil attribute with value true).

A calculation represented by a "summation-item" relationship binds for a summation item **S** if and only if:

1. **S** has at least one contributing item.
2. **S** is not a [Duplicate Item](#duplicate-items) (as defined in [**Section 4.10**](#_4.10)), and
3. None of the contributing items are duplicates.
4. **S** is not nil-valued (i.e. it does not have an xsi:nil attribute with value true).

**NOTE**: Calculation checks work exclusively on the information that is explicitly provided in the instance; items and values that can be inferred through essence-alias relationships are not considered. Several items (all corresponding to the one [Concept](#concept)) can bind to a summation item if they are not duplicates because they are not [P-Equal](#p-equal). This is relevant in the context of calculation scoping through tuples (see [**Section 5.2.5.2.2**](#_5.2.5.2.2)) and means that detection of duplicates is not a sufficient test for double counting problems in [XBRL Instances](#XBRL-instance).

The total of a binding calculation is defined to be the sum of the rounded values of the contributing [Numeric Items](#numeric-item) in the binding, each multiplied by the value of the ` @weight` attribute on the item's associated `  <calculationArc>  `. This multiplication takes place after any necessary rounding is performed. The rounded value of a numeric item is the result of rounding the value of the numeric item to its decimals or inferred decimals (see [**Section 4.6.6**](#_4.6.6)). A binding calculation is defined to be consistent if the rounded value of the summation item is equal to the total rounded to the decimals or inferred decimals of the summation item. (If any item of the calculation has a precision attribute value 0 then the binding calculation is deemed to be inconsistent.)

An [XBRL Instance](#XBRL-instance) is consistent with the semantics of the calculation [Linkbases](#linkbase) in its supporting [DTS](#DTS) if all binding calculations for the XBRL instance are consistent.

Fully conformant XBRL processors **MUST** detect and signal inconsistencies, as defined above, between an [XBRL Instance](#XBRL-instance) and the summation-item arcs of calculation [Linkbases](#linkbase) in its supporting [DTS](#DTS).

Example 52: Calculations involving decimals and precision

Suppose that the [Numeric Item](#numeric-item) `a` is a summation for numeric items `b` and `c` (with ` @weight` `1.0`) and there exists a context with ` @id` ' `c1` ' and unit with ` @id` ' `u1` ' in the instance so that the summation binds. To perform the calculation, first round 984.8 to precision 3 to give 985 and then round 582.334973 to the inferred precision 4 to give 582.3 resulting in a total of 1567.3. The total is then equal to the summation item after rounding to precision 2 (the precision of the summation item `a`) at 1600, so that this calculation is consistent.

<a contextRef="c1" unitRef="u1" precision="2">1559</a>

<b contextRef="c1" unitRef="u1" precision="3">984.8</b>

<c contextRef="c1" unitRef="u1" decimals="1">582.334973</c>

This calculation is not consistent since the total at precision 2 is, again, 1600 but the summation item to precision 2 has value 1500.

<a contextRef="c1" unitRef="u1" precision="2">1527</a>

<b contextRef="c1" unitRef="u1" precision="3">984.8</b>

<c contextRef="c1" unitRef="u1" decimals="1">582.334973</c>

Example 53: Syntax of a `calculationArc`

<calculationArc xlink:type="arc" xlink:arcrole="http://www.xbrl.org/2003/arcrole/summation-item" xlink:from="currentAssets" xlink:to="prepaidExpenses" weight="1.0" order="1"/>

A [DTS](#DTS) might include a single [Concept](#concept) viewed from different perspectives or as having several different dimensions. In the example below, the cash concept can be broken down by branch location, by account type, and by availability.

Example 54: Cash, equivalent to cash as totalled by branch location and account type

Cash

- Cash by Branch Location
	- Cash in Domestic Branches
		- Cash in Foreign Branches
- Cash by Account Type
	- Cash in Interest Bearing Accounts
		- Cash in Non-interest Bearing Accounts
- Cash by Availability
	- Cash on Hand
		- Cash as Balances Due

Cash in domestic branches and cash in foreign branches adds to cash. Cash in interest bearing accounts and cash in non-interest bearing accounts also adds to cash. Cash on hand and cash as balances due also adds to cash. To ensure that the calculation relationships between all of these disaggregate cash [Concepts](#concept) and the cash concept itself do not cause double or triple counting, the three pairs of summation-item arcs **SHOULD** be grouped into [Extended Links](#extended-link) with different extended link role values.

Thus, the summation-item arcs from cash to cash in domestic branches and to cash in foreign branches could be defined in [Extended Links](#extended-link) with the extended link role value:

`http://www.mytaxonomy.com/calcLinks/cashByBranchLocation`

Likewise, the summation-item arcs from cash to cash in interest bearing accounts and cash in non-interest bearing accounts could be defined in [Extended Links](#extended-link) with the extended link role value:

`http://www.mytaxonomy.com/calcLinks/cashByAccountType`

Finally, the summation-item arcs from cash to cash on hand and cash as balances due could be defined in extended links with the extended link role value:

`http://www.mytaxonomy.com/calcLinks/cashByAvailability`

The different extended link role values avoid double or triple counting in this example by ensuring that the pairs of summation-item arcs are not all processed together.

##### 5.2.5.2.1 The @weight attribute

The ` @weight` attribute **MUST** appear on `  <calculationArc>  ` elements. The ` @weight` attribute **MUST** have a non-zero decimal value. For summation-item arcs, the ` @weight` attribute indicates the multiplier to be applied to an item value when accumulating numeric values from item elements to summation elements. A value of "1.0" means that 1.0 times the numeric value of the item is applied to the parent item. A weight of "-1.0" means that 1.0 times the numeric value is subtracted from the summation item.

##### 5.2.5.2.2 Calculation scoping

A summation-item `  <calculationArc>  ` applies when the taxonomy [Concepts](#concept) that are located by the " `from` " and " `to` " attributes of a `summation-item` calculation arc identify [C-Equal](#c-equal) and [U-Equal](#u-equal) items (i.e. they are within equivalent contexts and [Units](#unit) in an [XBRL Instance](#XBRL-instance)). However, calculations also take into account tuple structure in the XBRL instance. The " `from` " item **MUST** be a child of the [Least Common Ancestor](#least-common-ancestor) of both the "from" and "to" items for the calculation relationships to bind. A consequence of this scoping is that items inside [Duplicate Tuples](#duplicate-tuples) cannot participate together in calculations.

Example 55: XBRL instance fragment with nested tuples

There are three calculation arcs in the `  <calculationLink>  `:

from (summation) `net` to (item) `gross`, weight = 1.0

from (summation) `net` to (item) `returns`, weight = -1.0

from (summation) `totalGross` to (item) `gross`, weight = 1.0

The following is a fragment of an XBRL instance. Note that all [Numeric Items](#numeric-item) share a single context `c1`.

<analysis><customer>

<name contextRef="c1">Acme</name>

<gross precision="4" unitRef="u1" contextRef="c1">3000</gross>

<returns precision="3" unitRef="u1" contextRef="c1">100</returns>

<net precision="4" unitRef="u1" contextRef="c1">2900</net>

</customer><customer>

<name contextRef="c1">Bree</name>

<gross precision="4" unitRef="u1" contextRef="c1">2000</gross>

<returns precision="3" unitRef="u1" contextRef="c1">200</returns>

<net precision="4" unitRef="u1" contextRef="c1">1800</net>

</customer>

<totalGross precision="4" unitRef="u1" contextRef="c1">5000</totalGross>

</analysis>

| calculation item (" `to` ") path | calculation summation (" `from` ") path | Match? | Reason |
| --- | --- | --- | --- |
| `analysis/customer[1]/gross` | `analysis/customer[1]/net` | Yes | They are siblings. |
| `analysis/customer[2]/gross` | `analysis/customer[2]/net` | Yes | They are siblings. |
| `analysis/customer[1]/returns` | `analysis/customer[1]/net` | Yes | They are siblings. |
| `analysis/customer[2]/gross` | `analysis/customer[2]/net` | Yes | They are siblings. |
| `analysis/customer[1]/gross` | `analysis/customer[2]/net` | No | The "to" summation is not a sibling or uncle of the item. |
| `analysis/customer[2]/gross` | `analysis/customer[1]/net` | No | The "to" summation is not a sibling or uncle of the item. |
| `analysis/customer[1]/gross` | `analysis/totalGross` | Yes | `totalGross` is an uncle of the item under ancestor `analysis`. |
| `analysis/customer[2]/gross` | `analysis/totalGross` | Yes | `totalGross` is an uncle of the item under ancestor `analysis.` |

### 5.2.6 The <definitionLink> element

The `  <definitionLink>  ` element is an extended link. Its generic syntax is documented in [**Section 3.5.3**](#_3.5.3). It is intended to contain a variety of miscellaneous relationships between [Concepts](#concept) in taxonomies. The `  <definitionLink>  ` element **MUST NOT** contain [\[XLINK\]](#XLINK) resources.

The XML Schema constraints on the `  <definitionLink>  ` element are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><element name="definitionLink" substitutionGroup="xl:extended"><documentation>

definition extended link element definition

</documentation><restriction base="xl:extendedType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="link:documentation"/>

<element ref="link:loc"/>

<element ref="link:definitionArc"/>

</choice>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></element></schema>

#### 5.2.6.1 Locators in <definitionLink> elements

`  <definitionLink>  ` elements **MUST NOT** contain [Locators](#locator) that are not `  <loc>  ` elements. `  <loc>  ` elements are documented in detail in [**Section 3.5.3.7**](#_3.5.3.7). The `  <loc>  ` element, when used in a `  <definitionLink>  `, **MUST** only point to [Concepts](#concept) in [Taxonomy Schemas](#taxonomy-schema).

#### 5.2.6.2 The <definitionArc> element

The `  <definitionArc>  ` element is an [\[XLINK\]](#XLINK) arc. Its generic syntax is defined in [**Section 3.5.3.9**](#_3.5.3.9). The `  <definitionArc>  ` elements define various kinds of relationships between [Concepts](#concept).

The XML Schema constraints on the syntax for `  <definitionArc>  ` elements are shown below.

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><documentation>

Concrete arc for use in definition extended links.

</documentation></schema>

Four standard arc role values are defined for `  <definitionArc>  ` elements.

##### 5.2.6.2.1 "general-special" arcs

The first standard arc role value for `  <definitionArc>  ` elements is:

`http://www.xbrl.org/2003/arcrole/general-special`

Such arcs are referred to as " `general-special` " arcs. `  <definitionArc>  ` elements with this arc role value **MUST** represent relationships only between [Concepts](#concept) that are in the `  <item>  ` substitution group.

General-special arcs connect from a generalisation concept [Locator](#locator) to a specialisation concept locator. A generalisation item is an occurrence of a generalisation concept in an XBRL instance. A specialisation item is an occurrence of a specialisation concept in an [XBRL Instance](#XBRL-instance). A valid value for a specialisation item is a valid value of its generalisation item (if both items are [C-Equal](#c-equal) and [U-Equal](#u-equal)). However, a valid value for a generalisation item is not necessarily a valid value for its specialisation item, even if they are [C-Equal](#c-equal) and [U-Equal](#u-equal).

Only undirected cycles are allowed in networks of general-special arcs. Fully conformant XBRL processors **MUST** detect and signal directed cycles in networks of general-special arcs.

Example 56: A general-special arc

<definitionArc xlink:type="arc" xlink:from="postalCode" xlink:to="zipCode" xlink:arcrole="http://www.xbrl.org/2003/arcrole/general-special" order="1"/>

Meaning: `postalCode` is a generalisation of `zipCode`. The ` @order` attribute indicates that when this link is displayed to a user, it appears after links with order less than 1, and before links with order greater than 1.

##### 5.2.6.2.2 "essence-alias" arcs

The second standard arc role value for `  <definitionArc>  ` elements is:

`http://www.xbrl.org/2003/arcrole/essence-alias`

Such arcs are referred to as " `essence-alias` " arcs. `  <definitionArc>  ` elements with this arc role value **MUST** represent relationships only between [Concepts](#concept) that are in the `  <item>  ` substitution group.

This arc role value is for use on a `  <definitionArc>  ` from an [Essence Concept](#Essence-Concept) [Locator](#locator) to an [Alias Concept](#alias-concept) [Locator](#locator).

Only undirected cycles are allowed in networks of essence-alias arcs. Fully conformant XBRL processors **MUST** detect any directed cycles in networks of essence-alias arcs.

It is often the case that particular [Concepts](#concept) have been defined more than once in a single taxonomy or in a set of taxonomies. It is appropriate, in such cases, for taxonomy authors to have a single "canonical best element" or "essence" for one of the concepts and to associate it with the other "alias" concepts using the `essence-alias` definition arc to indicate to XBRL validating processors and other [XBRL Instance](#XBRL-instance) consuming applications that the items **MUST** be consistent as defined below.

An essence-alias arc denotes a relationship between two [Concepts](#concept), from the essence (basic, primary) concept, to the other alias (alternative name) concept.

For definitions of " [Alias Concept](#alias-concept) " " [Alias Item](#alias-item) " " [Essence Concept](#Essence-Concept) " and " [Essence Item](#essence-item) " refer to Table 1. For any set of essence-alias arcs that have the same essence concept the term "alias concept set" means the set of alias concepts associated with the set of arcs and the term "alias item set" means a corresponding set of items in an [S-Equal](#s-equal) or identical context in an [XBRL Instance](#XBRL-instance). The following conditions apply to definition arcs that are not prohibited (see [**Section 3.5.3.9.5**](#_3.5.3.9.5) for details on prohibited arcs) in any extension taxonomy having this arc role, to the alias concepts and essence concepts of such arcs, and to their corresponding alias items and essence items.

1. An [Alias Concept](#alias-concept) **MAY** be the [Essence Concept](#Essence-Concept) of any number of other alias concepts.
2. Both the [Alias Concept](#alias-concept) and [Essence Concept](#Essence-Concept) of an arc **MUST** have the same item type and the same value for the ` @periodType` attribute. Also, if the ` @balance` attribute is present on both the alias concept and essence concept of an arc, it **MUST** have the same value for both [Concepts](#concept). There is no similar requirement if the ` @balance` attribute is absent from either or both of the concepts
3. If an [Alias Item](#alias-item) and an [Essence Item](#essence-item) in an XBRL instance that are [C-Equal](#c-equal) and [P-Equal](#p-equal) are not [V-Equal](#v-equal) or are not [U-Equal](#u-equal) in those respective [S-Equal](#s-equal) contexts, then the two items are not consistent with the semantics of the definition links in the [DTS](#DTS) supporting the [XBRL Instance](#XBRL-instance). This requirement only applies if both items do not have nil values. Only fully conformant XBRL processors **MUST** detect such inconsistencies.
4. For any non-numeric [Essence Concept](#Essence-Concept) **E**, for which there is no corresponding [Essence Item](#essence-item) **EI** having parent **P** for an [XBRL Instance](#XBRL-instance) context **C**, an XBRL processor **MAY** infer the existence of such an item **EI** having a value that is [V-Equal](#v-equal) to the values of all of the (non nil valued) members of the alias item set **S** corresponding to all essence-alias arcs with **E** as their essence concept having parent **P** if **S** is not the empty set. If all (non nil valued) members of **S** are not [V-Equal](#v-equal), then the XBRL instance is not consistent with the definition link semantics expressed in its [DTS](#DTS) and fully conformant XBRL processors **MUST** detect and signal such inconsistencies. If an application applies this rule and any member **M** of **S** does not have a value supplied or has a nil value, but is an essence item in some set of essence-alias arcs, this rule **MUST** be applied recursively to infer the value of **M** before inferring the value of **E**.
	Example 57: Inference of values for non-numeric items with concepts connected by essence-alias arcs
	In an [XBRL Instance](#XBRL-instance) there is a context `c1`. The concepts D and E are string item types connected by an essence-alias `  <definitionArc>  `, with E being the [Essence Concept](#Essence-Concept) and D being the [Alias Concept](#alias-concept). E has the value "Bert" in context c1 while D has the value "Ernie" in context c1. These values are inconsistent with the `  <definitionArc>  ` semantics that have been expressed.
5. For any numeric [Essence Concept](#Essence-Concept) **E**, for which there is no corresponding [Essence Item](#essence-item) **EI** having parent **P** for an [XBRL Instance](#XBRL-instance) context **C**, an XBRL processor **MAY** infer the existence of such an item **EI** having a value that is [V-Equal](#v-equal) to the values of all of the members of the (non nil valued) alias item set **S** corresponding to all essence-alias arcs with **E** as their essence concept having parent **P** if **S** is not the empty set, at the greatest values of ` @precision` and ` @decimals` for which this is possible (see 4.6.3 above). If all (non nil valued) members of **S** are not [V-Equal](#v-equal), then the XBRL instance is not consistent with the definition link semantics expressed in its [DTS](#DTS) and fully conformant XBRL processors **MUST** detect such inconsistencies. If an application applies this rule and any member **M** of **S** does not have a value supplied or has a nil value, but is an essence item in some set of essence-alias arcs, this rule **MUST** be applied recursively to infer the value of **M** before inferring the value of **E**.

XBRL processors are not required to infer the values of [Alias Items](#alias-item) from the values of [Essence Items](#essence-item) and this specification provides no rules for so doing.

Example 58: Inference of values for numeric items with concepts connected by essence-alias arcs

**Case 1**

The concepts A, B and C are connected by essence-alias arcs, with A being the essence and B and C being aliases. In an [XBRL Instance](#XBRL-instance), B has the value 110 with precision=2 and C has the value 99 with precision=2. A, B and C are [C-Equal](#c-equal).

The values of B and C are inconsistent at their specified precision of 2. As a result, no inference can be made for A.

**Case 2**

The concepts A, B and C are connected by essence-alias arcs, with A being the essence and B and C being aliases. In an [XBRL Instance](#XBRL-instance), B has the value 110 with precision=1 and C has the value 99 with precision=1. A, B and C are [C-Equal](#c-equal).

Rounding B to precision=1 gives the result 100

Rounding C to precision=1 gives the result 100

Since these two values are the same, a value of 100 at precision=1 can be inferred for A.

##### 5.2.6.2.3 "similar-tuples" arcs

The third standard arc role value for `  <definitionArc>  ` elements is:

`http://www.xbrl.org/2003/arcrole/similar-tuples`

Such arcs are referred to as " `similar-tuples` " arcs. `  <definitionArc>  ` elements with this arc role value **MUST** represent relationships only between [Concepts](#concept) that are in the `  <tuple>  ` substitution group.

The `similar-tuples` arcs represent relationships between tuple [Concepts](#concept) that have equivalent definitions (as provided in the labels and references for those tuples) even when they have different XML content models.

For example, this kind of relationship would be appropriate to use between two different tuple [Concepts](#concept) that are both designed to describe mailing addresses.

The semantics of `similar-tuples` arcs are symmetric. It does not matter which tuple the arc goes from and which tuple the arc goes to.

Any cycles can be semantically sensible in networks of `  <definitionArc>  ` elements with the `http://www.xbrl.org/2003/arcrole/similar-tuples ` arc role value because the relationship between [Concepts](#concept) being described by these relationships is symmetric.

##### 5.2.6.2.4 "requires-element" arcs

The fourth standard arc role value for `  <definitionArc>  ` elements is:

`http://www.xbrl.org/2003/arcrole/requires-element`

Such arcs are referred to as " `requires-element` " arcs. `  <definitionArc>  ` elements with this arc role value **MUST** represent relationships only between [Concepts](#concept) (which, by definition, are in the `  <tuple>  ` or `  <item>  ` substitution groups).

If an instance of the [Concept](#concept) at the source of the arc occurs in an [XBRL Instance](#XBRL-instance) then an instance of the arc's target concept **MUST** also occur in the XBRL instance. No requirements are placed on c-equality or u-equality of these concept instances when testing this requirement. Likewise, this requirement does not impose requirements on relative locations of the concept instances in tuples. Fully conformant XBRL processors **MUST** detect and signal instances in which this relationship is violated.

For example, the data that is normally entered into a paper form could be represented electronically using XBRL instances. To represent the "required field" idea, the taxonomy author can create a `  <definitionArc>  ` with the `http://www.xbrl.org/2003/arcrole/requires-element` arc role value. This arc would link the [Concepts](#concept) representing the required fields and an element representing the concept of the form itself.

Cycles are allowed in networks of `requires-element` arcs.

## 6 References

ELEMENT-SCHEME

W3C (World Wide Web Consortium). "XPointer element() Scheme"  
Paul Grosso, Eve Maler, Jonathan Marsh, and Norman Walsh.  
(See [http://www.w3.org/TR/xptr-element/](http://www.w3.org/TR/xptr-element/))

IEEE

IEEE. "IEEE Standard for Floating Point Arithmetic, IEEE Std 754™-2008"  
(See [http://ieeexplore.ieee.org/xpl/mostRecentIssue.jsp?punumber=4610933](http://ieeexplore.ieee.org/xpl/mostRecentIssue.jsp?punumber=4610933))

IETF RFC 2119

IETF (Internet Engineering Task Force). "RFC 2119: Key words for use in RFCs to Indicate Requirement Levels"  
Scott Bradner.  
(See [http://www.ietf.org/rfc/rfc2119.txt](http://www.ietf.org/rfc/rfc2119.txt))

ISO

International Standards Organisation. " ISO 4217 Currency codes, ISO 639 Language codes, ISO 3166 Country codes, ISO 8601 international standard numeric date and time representations. "  
(See [http://www.iso.ch/](http://www.iso.ch/))

SGML

International Standards Organisation. "Information Processing - Text and office systems - Standard Generalized Markup Language (SGML)"  
(See [http://www.iso.ch/iso/en/CatalogueDetailPage.CatalogueDetail?CSNUMBER=16387](http://www.iso.ch/iso/en/CatalogueDetailPage.CatalogueDetail?CSNUMBER=16387))

XBRL 2.1

XBRL International Inc.. "Extensible Business Reporting Language (XBRL) 2.1 Includes Corrected Errata Up To 2012-01-25"  
Phillip Engel, Walter Hamscher, Geoff Shuetrim, David vun Kannon, and Hugh Wallis.  
(See [http://www.xbrl.org/specification/xbrl-recommendation-2003-12-31+corrected-errata-2012-01-25.htm](http://www.xbrl.org/specification/xbrl-recommendation-2003-12-31+corrected-errata-2012-01-25.htm))

XLINK

W3C (World Wide Web Consortium). "XML Linking Language (XLink) Version 1.0"  
Steve DeRose, Eve Maler, and David Orchard.  
(See [http://www.w3.org/TR/xlink/](http://www.w3.org/TR/xlink/))

XML

W3C (World Wide Web Consortium). "Extensible Markup Language (XML) 1.0 (Fifth Edition)"  
Tim Bray, Jean Paoli, C. M. Sperberg-McQueen, Eve Maler, and François Yergeau.  
(See [http://www.w3.org/TR/REC-xml/](http://www.w3.org/TR/REC-xml/))

XML Base

W3C (World Wide Web Consortium). "XML Base"  
Johnathan Marsh.  
(See [http://www.w3.org/TR/xmlbase/](http://www.w3.org/TR/xmlbase/))

XML Names

W3C (World Wide Web Consortium). "Namespaces in XML 1.0 (Third Edition)"  
(See [http://www.w3.org/TR/REC-xml-names/REC-xml-names-20091208](http://www.w3.org/TR/REC-xml-names/REC-xml-names-20091208))

XML Schema Datatypes

W3C (World Wide Web Consortium). "XML Schema Part 2: Datatypes Second Edition"  
Paul V. Biron, and Ashok Malhotra.  
(See [http://www.w3.org/TR/xmlschema-2/](http://www.w3.org/TR/xmlschema-2/))

XML Schema Structures

W3C (World Wide Web Consortium). "XML Schema Part 1: Structures Second Edition"  
Henry S. Thompson, David Beech, Murray Maloney, and Noah Mendelsohn.  
(See [http://www.w3.org/TR/xmlschema-1/REC-xmlschema-1-20041028/](http://www.w3.org/TR/xmlschema-1/REC-xmlschema-1-20041028/))

XPOINTER

W3C (World Wide Web Consortium). "XPointer Framework"  
Paul Grosso, Eve Maler, Jonathan Marsh, and Norman Walsh.  
(See [http://www.w3.org/TR/xptr-framework/](http://www.w3.org/TR/xptr-framework/))

XPath 1.0

W3C (World Wide Web Consortium). "XML Path Language (XPath) 1.0"  
James Clark, and Steve DeRose.  
(See [http://www.w3.org/TR/xpath/](http://www.w3.org/TR/xpath/))

## Appendix A Schemas

The following are the versions of the XML schemas provided as part of this specification. These are all normative. Non-normative versions (which should be identical to these except for appropriate comments indicating their non-normative status) are also provided as separate files for convenience of users of the specification.

**NOTE:** (non-normative) Following the schema maintenance policy of XBRL International, it is the intent (but is not guaranteed) that the location of non-normative versions of these schemas on the web will be as follows:

1. While any schema is the most current RECOMMENDED version and until it is superseded by any additional errata corrections a non-normative version will reside on the web in the directory [http://www.xbrl.org/2003/](http://www.xbrl.org/2003/)
2. A non-normative version of each schema as corrected by this update to the RECOMMENDATION will be archived in perpetuity on the web in the directory [http://www.xbrl.org/2003/2006-12-18/](http://www.xbrl.org/2003/2006-12-18/)

In order to allow validation of linkbase documents, the XBRL linkbase namespace (`http://www.xbrl.org/2003/linkbase)` **MUST** be used with the schema that implements the [\[XLINK\]](#XLINK) specification. This schema defines the namespace `http://www.w3.org/1999/xlink` is not an official document of the W3C. It is the intention of XBRL International to integrate with the official schemas for [\[XLINK\]](#XLINK) should they become available.

## A.1 xbrl-instance-2003-12-31.xsd (normative)

<!---->

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/instance" elementFormDefault="qualified"><documentation>

Taxonomy schema for XBRL. This schema defines syntax relating to XBRL instances.

</documentation>

<import namespace="http://www.xbrl.org/2003/linkbase" schemaLocation="xbrl-linkbase-2003-12-31.xsd"/>

<documentation>

Define the attributes to be used on XBRL concept definitions

</documentation><attribute name="periodType"><documentation>

The periodType attribute (restricting the period for XBRL items)

</documentation><restriction base="token">

<enumeration value="instant"/>

<enumeration value="duration"/>

</restriction></attribute><attribute name="balance"><documentation>

The balance attribute (imposes calculation relationship restrictions)

</documentation><restriction base="token">

<enumeration value="debit"/>

<enumeration value="credit"/>

</restriction></attribute><documentation>

Define the simple types used as a base for for item types

</documentation><simpleType name="monetary"><documentation>

the monetary type serves as the datatype for those financial concepts in a taxonomy which denote units in a currency. Instance items with this type must have a unit of measure from the ISO 4217 namespace of currencies.

</documentation>

<restriction base="decimal"/>

</simpleType><simpleType name="shares"><documentation>

This datatype serves as the datatype for share based financial concepts.

</documentation>

<restriction base="decimal"/>

</simpleType><simpleType name="pure"><documentation>

This datatype serves as the type for dimensionless numbers such as percentage change, growth rates, and other ratios where the numerator and denominator have the same units.

</documentation>

<restriction base="decimal"/>

</simpleType><simpleType name="nonZeroDecimal"><documentation>

As the name implies this is a decimal value that can not take the value 0 - it is used as the type for the denominator of a fractionItemType.

</documentation><union><restriction base="decimal">

<minExclusive value="0"/>

</restriction><restriction base="decimal">

<maxExclusive value="0"/>

</restriction></union></simpleType><simpleType name="precisionType"><documentation>

This type is used to specify the value of the precision attribute on numeric items. It consists of the union of nonNegativeInteger and "INF" (used to signify infinite precision or "exact value").

</documentation><restriction base="string">

<enumeration value="INF"/>

</restriction></simpleType><simpleType name="decimalsType"><documentation>

This type is used to specify the value of the decimals attribute on numeric items. It consists of the union of integer and "INF" (used to signify that a number is expressed to an infinite number of decimal places or "exact value").

</documentation><restriction base="string">

<enumeration value="INF"/>

</restriction></simpleType><attributeGroup name="factAttrs"><documentation>

Attributes for all items and tuples.

</documentation>

<attribute name="id" type="ID" use="optional"/>

<anyAttribute namespace="##other" processContents="lax"/>

</attributeGroup><attributeGroup name="tupleAttrs"><documentation>

Group of attributes for tuples.

</documentation>

<attributeGroup ref="xbrli:factAttrs"/>

</attributeGroup><attributeGroup name="itemAttrs"><documentation>

Attributes for all items.

</documentation>

<attributeGroup ref="xbrli:factAttrs"/>

<attribute name="contextRef" type="IDREF" use="required"/>

</attributeGroup><attributeGroup name="essentialNumericItemAttrs"><documentation>

Attributes for all numeric items (fractional and non-fractional).

</documentation>

<attributeGroup ref="xbrli:itemAttrs"/>

<attribute name="unitRef" type="IDREF" use="required"/>

</attributeGroup><attributeGroup name="numericItemAttrs"><documentation>

Group of attributes for non-fractional numeric items

</documentation>

<attributeGroup ref="xbrli:essentialNumericItemAttrs"/>

<attribute name="precision" type="xbrli:precisionType" use="optional"/>

<attribute name="decimals" type="xbrli:decimalsType" use="optional"/>

</attributeGroup><attributeGroup name="nonNumericItemAttrs"><documentation>

Group of attributes for non-numeric items

</documentation>

<attributeGroup ref="xbrli:itemAttrs"/>

</attributeGroup><documentation>

General numeric item types - for use on concept element definitions The following 3 numeric types are all based on the built-in data types of XML Schema.

</documentation><extension base="decimal">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="float">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="double">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><documentation>

XBRL domain numeric item types - for use on concept element definitions The following 4 numeric types are all types that have been identified as having particular relevance to the domain space addressed by XBRL and are hence included in addition to the built-in types from XML Schema.

</documentation><extension base="xbrli:monetary">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="xbrli:shares">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="xbrli:pure">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension>

<element name="numerator" type="decimal"/>

<element name="denominator" type="xbrli:nonZeroDecimal"/>

<complexType name="fractionItemType" final="extension"><sequence>

<element ref="xbrli:numerator"/>

<element ref="xbrli:denominator"/>

</sequence>

<attributeGroup ref="xbrli:essentialNumericItemAttrs"/>

</complexType><documentation>

The following 13 numeric types are all based on the XML Schema built-in types that are derived by restriction from decimal.

</documentation><extension base="integer">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="nonPositiveInteger">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="negativeInteger">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="long">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="int">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="short">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="byte">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="nonNegativeInteger">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="unsignedLong">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="unsignedInt">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="unsignedShort">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="unsignedByte">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><extension base="positiveInteger">

<attributeGroup ref="xbrli:numericItemAttrs"/>

</extension><documentation>

The following 17 non-numeric types are all based on the primitive built-in data types of XML Schema.

</documentation><extension base="string">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="boolean">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="hexBinary">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="base64Binary">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="anyURI">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="QName">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="duration">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="xbrli:dateUnion">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="time">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="date">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="gYearMonth">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="gYear">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="gMonthDay">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="gDay">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="gMonth">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><documentation>

The following 5 non-numeric types are all based on the XML Schema built-in types that are derived by restriction and/or list from string.

</documentation><extension base="normalizedString">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="token">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="language">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="Name">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><extension base="NCName">

<attributeGroup ref="xbrli:nonNumericItemAttrs"/>

</extension><documentation>

XML Schema components contributing to the context element

</documentation><sequence>

<any namespace="##other" processContents="lax" minOccurs="1" maxOccurs="unbounded"/>

</sequence><complexType name="contextEntityType"><documentation>

The type for the entity element, used to describe the reporting entity. Note that the scheme attribute is required and cannot be empty.

</documentation><sequence><restriction base="anyURI">

<minLength value="1"/>

</restriction>

<element ref="xbrli:segment" minOccurs="0"/>

</sequence></complexType><simpleType name="dateUnion"><documentation>

The union of the date and dateTime simple types.

</documentation>

<union memberTypes="date dateTime"/>

</simpleType><complexType name="contextPeriodType"><documentation>

The type for the period element, used to describe the reporting date info.

</documentation><choice><sequence>

<element name="startDate" type="xbrli:dateUnion"/>

<element name="endDate" type="xbrli:dateUnion"/>

</sequence>

<element name="instant" type="xbrli:dateUnion"/>

<element name="forever">

<complexType/>

</element></choice></complexType><complexType name="contextScenarioType"><documentation>

Used for the scenario under which fact have been reported.

</documentation><sequence>

<any namespace="##other" processContents="lax" minOccurs="1" maxOccurs="unbounded"/>

</sequence></complexType><element name="context"><documentation>

Used for an island of context to which facts can be related.

</documentation><complexType><sequence>

<element name="entity" type="xbrli:contextEntityType"/>

<element name="period" type="xbrli:contextPeriodType"/>

<element name="scenario" type="xbrli:contextScenarioType" minOccurs="0"/>

</sequence>

<attribute name="id" type="ID" use="required"/>

</complexType></element><documentation>

XML Schema components contributing to the unit element

</documentation>

<element name="measure" type="QName"/>

<complexType name="measuresType"><documentation>

A collection of sibling measure elements

</documentation><sequence>

<element ref="xbrli:measure" minOccurs="1" maxOccurs="unbounded"/>

</sequence></complexType><element name="divide"><documentation>

Element used to represent division in units

</documentation><sequence>

<element name="unitNumerator" type="xbrli:measuresType"/>

<element name="unitDenominator" type="xbrli:measuresType"/>

</sequence></element><element name="unit"><documentation>

Element used to represent units information about numeric items

</documentation><complexType><choice>

<element ref="xbrli:measure" minOccurs="1" maxOccurs="unbounded"/>

<element ref="xbrli:divide"/>

</choice>

<attribute name="id" type="ID" use="required"/>

</complexType></element><documentation>

Elements to use for facts in instances

</documentation><documentation>

Abstract item element used as head of item substitution group

</documentation><documentation>

Abstract tuple element used as head of tuple substitution group

</documentation><element name="xbrl"><documentation>

XBRL instance root element.

</documentation><complexType><sequence>

<element ref="link:schemaRef" minOccurs="1" maxOccurs="unbounded"/>

<element ref="link:linkbaseRef" minOccurs="0" maxOccurs="unbounded"/>

<element ref="link:roleRef" minOccurs="0" maxOccurs="unbounded"/>

<element ref="link:arcroleRef" minOccurs="0" maxOccurs="unbounded"/>

<choice minOccurs="0" maxOccurs="unbounded">

<element ref="xbrli:item"/>

<element ref="xbrli:tuple"/>

<element ref="xbrli:context"/>

<element ref="xbrli:unit"/>

<element ref="link:footnoteLink"/>

</choice></sequence>

<attribute name="id" type="ID" use="optional"/>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</complexType></element></schema>

## A.2 xbrl-linkbase-2003-12-31.xsd (normative)

<!---->

<schema  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/linkbase" elementFormDefault="qualified"><documentation>

XBRL simple and extended link schema constructs

</documentation>

<import namespace="http://www.xbrl.org/2003/XLink" schemaLocation="xl-2003-12-31.xsd"/>

<import namespace="http://www.w3.org/1999/xlink" schemaLocation="xlink-2003-12-31.xsd"/>

<documentation>

Concrete element to use for documentation of extended links and linkbases.

</documentation><documentation>

Concrete locator element. The loc element is the XLink locator element for all extended links in XBRL.

</documentation><documentation>

Concrete arc for use in label extended links.

</documentation><documentation>

Concrete arc for use in reference extended links.

</documentation><documentation>

Concrete arc for use in definition extended links.

</documentation><complexType><documentation>

Extension of the extended link arc type for presentation arcs. Adds a preferredLabel attribute that documents the role attribute value of preferred labels (as they occur in label extended links).

</documentation><restriction base="anyURI">

<minLength value="1"/>

</restriction></complexType><complexType><documentation>

Extension of the extended link arc type for calculation arcs. Adds a weight attribute to track weights on contributions to summations.

</documentation><extension base="xl:arcType">

<attribute name="weight" type="decimal" use="required"/>

</extension></complexType><documentation>

Concrete arc for use in footnote extended links.

</documentation><element name="label" substitutionGroup="xl:resource"><documentation>

Definition of the label resource element.

</documentation><extension base="xl:resourceType"><sequence>

<any namespace="http://www.w3.org/1999/xhtml" processContents="skip" minOccurs="0" maxOccurs="unbounded"/>

</sequence>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</extension></element><documentation>

Definition of the reference part element - for use in reference resources.

</documentation><element name="reference" substitutionGroup="xl:resource"><documentation>

Definition of the reference resource element.

</documentation><sequence>

<element ref="link:part" minOccurs="0" maxOccurs="unbounded"/>

</sequence></element><element name="footnote" substitutionGroup="xl:resource"><documentation>

Definition of the reference resource element

</documentation><extension base="xl:resourceType"><sequence>

<any namespace="http://www.w3.org/1999/xhtml" processContents="skip" minOccurs="0" maxOccurs="unbounded"/>

</sequence>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</extension></element><element name="presentationLink" substitutionGroup="xl:extended"><documentation>

presentation extended link element definition.

</documentation><restriction base="xl:extendedType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="link:documentation"/>

<element ref="link:loc"/>

<element ref="link:presentationArc"/>

</choice>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></element><element name="definitionLink" substitutionGroup="xl:extended"><documentation>

definition extended link element definition

</documentation><restriction base="xl:extendedType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="link:documentation"/>

<element ref="link:loc"/>

<element ref="link:definitionArc"/>

</choice>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></element><element name="calculationLink" substitutionGroup="xl:extended"><documentation>

calculation extended link element definition

</documentation><restriction base="xl:extendedType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="link:documentation"/>

<element ref="link:loc"/>

<element ref="link:calculationArc"/>

</choice>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></element><element name="labelLink" substitutionGroup="xl:extended"><documentation>

label extended link element definition

</documentation><restriction base="xl:extendedType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="link:documentation"/>

<element ref="link:loc"/>

<element ref="link:labelArc"/>

<element ref="link:label"/>

</choice>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></element><element name="referenceLink" substitutionGroup="xl:extended"><documentation>

reference extended link element definition

</documentation><restriction base="xl:extendedType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="link:documentation"/>

<element ref="link:loc"/>

<element ref="link:referenceArc"/>

<element ref="link:reference"/>

</choice>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></element><element name="footnoteLink" substitutionGroup="xl:extended"><documentation>

footnote extended link element definition

</documentation><restriction base="xl:extendedType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="link:documentation"/>

<element ref="link:loc"/>

<element ref="link:footnoteArc"/>

<element ref="link:footnote"/>

</choice>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></element><element name="linkbase"><documentation>

Definition of the linkbase element. Used to contain a set of zero or more extended link elements.

</documentation><complexType><choice minOccurs="0" maxOccurs="unbounded">

<element ref="link:documentation"/>

<element ref="link:roleRef"/>

<element ref="link:arcroleRef"/>

<element ref="xl:extended"/>

</choice>

<attribute name="id" type="ID" use="optional"/>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</complexType></element><element name="linkbaseRef" substitutionGroup="xl:simple"><documentation>

Definition of the linkbaseRef element - used to link to XBRL taxonomy extended links from taxonomy schema documents and from XBRL instances.

</documentation><restriction base="xl:simpleType"><documentation>

This attribute must have the value: http://www.w3.org/1999/xlink/properties/linkbase

</documentation>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></element><documentation>

Definition of the schemaRef element - used to link to XBRL taxonomy schemas from XBRL instances.

</documentation><element name="roleRef" substitutionGroup="xl:simple"><documentation>

Definition of the roleRef element - used to link to resolve xlink:role attribute values to the roleType element declaration.

</documentation><documentation>

This attribute contains the role name.

</documentation></element><element name="arcroleRef" substitutionGroup="xl:simple"><documentation>

Definition of the roleRef element - used to link to resolve xlink:arcrole attribute values to the arcroleType element declaration.

</documentation><documentation>

This attribute contains the arc role name.

</documentation></element><documentation>

The element to use for human-readable definition of custom roles and arc roles.

</documentation><documentation>

Definition of the usedOn element - used to identify what elements may use a taxonomy defined role or arc role value.

</documentation><element name="roleType"><documentation>

The roleType element definition - used to define custom role values in XBRL extended links.

</documentation><complexType><sequence>

<element ref="link:definition" minOccurs="0"/>

<element ref="link:usedOn" maxOccurs="unbounded"/>

</sequence>

<attribute name="roleURI" type="xl:nonEmptyURI" use="required"/>

<attribute name="id" type="ID"/>

</complexType></element><element name="arcroleType"><documentation>

The arcroleType element definition - used to define custom arc role values in XBRL extended links.

</documentation><complexType><sequence>

<element ref="link:definition" minOccurs="0"/>

<element ref="link:usedOn" maxOccurs="unbounded"/>

</sequence>

<attribute name="arcroleURI" type="xl:nonEmptyURI" use="required"/>

<attribute name="id" type="ID"/>

<restriction base="NMTOKEN">

<enumeration value="any"/>

<enumeration value="undirected"/>

<enumeration value="none"/>

</restriction></complexType></element></schema>

## A.3 xlink-2003-12-31.xsd (normative)

<!---->

<schema  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.w3.org/1999/xlink" elementFormDefault="qualified" attributeFormDefault="qualified"><documentation>

XLink attribute specification

</documentation><simpleType><documentation>

Enumeration of values for the type attribute

</documentation><restriction base="string">

<enumeration value="simple"/>

<enumeration value="extended"/>

<enumeration value="locator"/>

<enumeration value="arc"/>

<enumeration value="resource"/>

<enumeration value="title"/>

</restriction></simpleType><simpleType><documentation>

A URI with a minimum length of 1 character.

</documentation><restriction base="anyURI">

<minLength value="1"/>

</restriction></simpleType><simpleType><documentation>

A URI with a minimum length of 1 character.

</documentation><restriction base="anyURI">

<minLength value="1"/>

</restriction></simpleType>

<attribute name="title" type="string"/>

<simpleType><documentation>

Enumeration of values for the show attribute

</documentation><restriction base="string">

<enumeration value="new"/>

<enumeration value="replace"/>

<enumeration value="embed"/>

<enumeration value="other"/>

<enumeration value="none"/>

</restriction></simpleType><simpleType><documentation>

Enumeration of values for the actuate attribute

</documentation><restriction base="string">

<enumeration value="onLoad"/>

<enumeration value="onRequest"/>

<enumeration value="other"/>

<enumeration value="none"/>

</restriction></simpleType>

<attribute name="label" type="NCName"/>

<attribute name="from" type="NCName"/>

<attribute name="to" type="NCName"/>

<attribute name="href" type="anyURI"/>

</schema>

## A.4 xl-2003-12-31.xsd (normative)

<!---->

<schema  
xmlns="http://www.w3.org/2001/XMLSchema" targetNamespace="http://www.xbrl.org/2003/XLink" elementFormDefault="qualified" attributeFormDefault="unqualified">

<import namespace="http://www.w3.org/1999/xlink" schemaLocation="xlink-2003-12-31.xsd"/>

<simpleType name="nonEmptyURI"><documentation>

A URI type with a minimum length of 1 character. Used on role and arcrole and href elements.

</documentation><restriction base="anyURI">

<minLength value="1"/>

</restriction></simpleType><complexType name="documentationType"><documentation>

Element type to use for documentation of extended links and linkbases.

</documentation><extension base="string">

<anyAttribute namespace="##other" processContents="lax"/>

</extension></complexType><documentation>

Abstract element to use for documentation of extended links and linkbases.

</documentation><documentation>

XBRL simple and extended link schema constructs

</documentation><complexType name="titleType"><documentation>

Type for the abstract title element - used as a title element template.

</documentation><restriction base="anyType">

<attribute ref="xlink:type" use="required" fixed="title"/>

</restriction></complexType><documentation>

Generic title element for use in extended link documentation. Used on extended links, arcs, locators. See http://www.w3.org/TR/xlink/#title-element for details.

</documentation><complexType name="locatorType"><documentation>

Generic locator type.

</documentation><restriction base="anyType"><sequence>

<element ref="xl:title" minOccurs="0" maxOccurs="unbounded"/>

</sequence>

<attribute ref="xlink:type" use="required" fixed="locator"/>

<attribute ref="xlink:href" use="required"/>

<attribute ref="xlink:label" use="required"/>

<attribute ref="xlink:role" use="optional"/>

<attribute ref="xlink:title" use="optional"/>

</restriction></complexType><documentation>

Abstract locator element to be used as head of locator substitution group for all extended link locators in XBRL.

</documentation><simpleType name="useEnum"><documentation>

Enumerated values for the use attribute on extended link arcs.

</documentation><restriction base="NMTOKEN">

<enumeration value="optional"/>

<enumeration value="prohibited"/>

</restriction></simpleType><complexType name="arcType"><documentation>

basic extended link arc type - extended where necessary for specific arcs Extends the generic arc type by adding use, priority and order attributes.

</documentation><restriction base="anyType"><sequence>

<element ref="xl:title" minOccurs="0" maxOccurs="unbounded"/>

</sequence>

<attribute ref="xlink:type" use="required" fixed="arc"/>

<attribute ref="xlink:from" use="required"/>

<attribute ref="xlink:to" use="required"/>

<attribute ref="xlink:arcrole" use="required"/>

<attribute ref="xlink:title" use="optional"/>

<attribute ref="xlink:show" use="optional"/>

<attribute ref="xlink:actuate" use="optional"/>

<attribute name="order" type="decimal" use="optional"/>

<attribute name="use" type="xl:useEnum" use="optional"/>

<attribute name="priority" type="integer" use="optional"/>

<anyAttribute namespace="##other" processContents="lax"/>

</restriction></complexType><documentation>

Abstract element to use as head of arc element substitution group.

</documentation><complexType name="resourceType"><documentation>

Generic type for the resource type element

</documentation><restriction base="anyType">

<attribute ref="xlink:type" use="required" fixed="resource"/>

<attribute ref="xlink:label" use="required"/>

<attribute ref="xlink:role" use="optional"/>

<attribute ref="xlink:title" use="optional"/>

<attribute name="id" type="ID" use="optional"/>

</restriction></complexType><documentation>

Abstract element to use as head of resource element substitution group.

</documentation><complexType name="extendedType"><documentation>

Generic extended link type

</documentation><restriction base="anyType"><choice minOccurs="0" maxOccurs="unbounded">

<element ref="xl:title"/>

<element ref="xl:documentation"/>

<element ref="xl:locator"/>

<element ref="xl:arc"/>

<element ref="xl:resource"/>

</choice>

<attribute ref="xlink:type" use="required" fixed="extended"/>

<attribute ref="xlink:role" use="required"/>

<attribute ref="xlink:title" use="optional"/>

<attribute name="id" type="ID" use="optional"/>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></complexType><documentation>

Abstract extended link element at head of extended link substitution group.

</documentation><complexType name="simpleType"><documentation>

Type for the simple links defined in XBRL

</documentation><restriction base="anyType">

<attribute ref="xlink:type" use="required" fixed="simple"/>

<attribute ref="xlink:href" use="required"/>

<attribute ref="xlink:arcrole" use="optional"/>

<attribute ref="xlink:role" use="optional"/>

<attribute ref="xlink:title" use="optional"/>

<attribute ref="xlink:show" use="optional"/>

<attribute ref="xlink:actuate" use="optional"/>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</restriction></complexType><documentation>

The abstract element at the head of the simple link substitution group.

</documentation></schema>

## Appendix B Document history and acknowledgments (non-normative)

This specification could not have been written without the contribution of many people. The participants in the XBRL Specification Working Group, public commentators, and personal advisors have all played a significant role. At the time of the first publication of this specification as a Recommendation, the XBRL International Specification Group was chaired by Masatomo Goto, Fujitsu Laboratories of USA, and its vice chair was Hugh Wallis of Hyperion Solutions Corporation. The XBRL International Domain Working Group also produced and refined many issue drafts and final requirements documents that defined the scope and guided the priorities of this version of the specification. The XBRL International Domain working group was chaired by Mark Schnitzer of Morgan Stanley and vice chaired by John Turner of KPMG. In alphabetical order and in addition to those individuals already credited as editors, Peter Calvert of ICAEW, Eric E. Cohen of PricewaterhouseCoopers, Don Dwiggins, Justin Foley of DecisionSoft, Charles Hoffman of UBmatrix, Josef MacDonald of Ernst & Young, Manabu Mizutani of PCS, David Prather of IASCF, Campbell Pryde of KPMG, Noboyuki Sambuichi of Hitachi, Paul Warren of Decisionsoft (subsequently CoreFiling) and Eiichi Watanabe of TSR, all contributed to the authoring and refinement of requirements and reviewing of the specification. In addition to the above Mark Goodhand of Decisionsoft (subsequently CoreFiling) contributed to the authoring and refinement of subsequent errata corrections.

| Date | Author | Details |
| --- | --- | --- |
| 20 February 2013 | Mark Goodhand | Reformatting of specification in S4S format. This edition incorporates no new errata; constraints and semantics are unchanged from the previous edition. The HTML version is now normative. |
| 31 October 2011 | Herm Fischer | Editorial to correction 074 typo. Erratum correction 075: Revision of IEEE Floating Point standard reference. Change to [**Section 4.6.7.1**](#_4.6.7.1) and [**Section 4.6.7.2**](#_4.6.7.2) from non-standandard terms and conflicting descriptions ( [**Section 4.6.7.1**](#_4.6.7.1) was round ties to larger magnitude, [**Section 4.6.7.2**](#_4.6.7.2) was round ties to lesser magnitude), to round ties to even (referencing the IEEE standard term and recommendation). |
| 29 April 2011 | Hugh Wallis | Editorial to publish as Proposed Edited Recommendation (erratum correction 074) |
| 07 March 2011 | Herm Fischer | Incorporated changes to change from inferring Decimals to inferring Precision – erratum correction 074 |
| 23 June 2008 | Hugh Wallis | Added errata corrections 069-073 and reflected approval by the SWG. |
| 04 March 2008 | Hugh Wallis | Removed text that had been deleted pursuant to erratum correction 006 but which had incorrectly (due to an editing error) been reinstated ( [**Section 5.2.5.2**](#_5.2.5.2)). |
| 10 January 2007 | Hugh Wallis | Added errata corrections 060-068 and reflected approval for publication by the XBRL International Standards Board. |
| 21 January 2006 | Hugh Wallis | Added erratum correction 059. Updated e-mail addresses and affiliations of editors and contributors. |
| 07 November 2005 | Hugh Wallis | Updated document to reflect approval for publication by the International Steering Committee of XBRL International. |
| 01 November 2005 | Hugh Wallis | Added errata corrections 048-058. |
| 25 April 2005 | Hugh Wallis | Updated document to reflect approval for publication by the International Steering Committee of XBRL International. |
| 30 March 2005 | Hugh Wallis | Updated document to reflect Specification Working Group approval of errata correction 013 and 047. Incorporated publication date (2005-04-25) in document title, name and text regarding the location on the web of non-normative versions of the schemas ([**Appendix A**](#A)). |
| 24 March 2005 | Hugh Wallis | Updated document to reflect Specification Working Group approval of errata corrections 044-046. Incorporated errata corrections 013 and 047. Added recognition of contribution from Mark Goodhand of Decisionsoft. |
| 10 March 2005 | Hugh Wallis | Updated document to reflect Specification Working Group approval of errata corrections 034-043. Incorporated errata correction 044-046. |
| 03 March 2005 | Hugh Wallis | Incorporated errata corrections 034-043 |
| 08 October 2004 | Hugh Wallis | Updated document to reflect Specification Working Group approval of all errata corrections preparatory to publication. |
| 01 October 2004 | Hugh Wallis | Incorporated final edits for erratum 027 and correction for erratum 033. |
| 30 September 2004 | Hugh Wallis | Incorporated further changes to errata 027 and 031 corrections as well as correction for erratum 032. |
| 08 September 2004 | Hugh Wallis | Incorporated additional minor wording modifications to erratum correction 027. Reflected Working Group approval of errata corrections 026 and 028-030. |
| 19 August 2004 | Hugh Wallis | Incorporated errata corrections 028-030. |
| 12 August 2004 | Hugh Wallis | Incorporated errata corrections 026-027. |
| 27 July 2004 | Hugh Wallis | updated e-mail address and affiliation for editor Wallis. Reflected Specification Working Group approval of errata corrections 018-022 and 024-025. |
| 14 July 2004 | Hugh Wallis | incorporated correction of errata 018-022 and 024-025 pending Specification Working Group approval, erratum 023 indicating approval already given. |
| 30 April 2004 | Hugh Wallis | Updated list of errata to indicate approvals by the Specification Working Group. Updated status section to indicate approval by the ISC for publication. Added non-normative note to [**Appendix A**](#A) regarding the schema maintenance policy for schema updates and their location on the web. |
| 23 April 2004 | Hugh Wallis | Incorporated correction of errata 009-017 (excluding 013 which is still in preparation as of this date). |
| 26 February 2004 | Hugh Wallis | Updated correction of erratum 004 to include `anyAttribute` in the declaration of additional elements. Incorporated corrections for errata 006, 007 and 008. |
| 12 February 2004 | Hugh Wallis | Incorporated corrections for errata 004 and 005. Updated corrections for erratum 001. |
| 22 January 2004 | Hugh Wallis | Incorporated corrections for errata 001, 002 and 003. Changed descriptive text on page 1 to reflect the status of the document as incorporating errata corrections. Added [**Appendix D**](#D) to provide summary documentation of errata corrections. |

Changes prior to 2003-12-31 were reflected in the original RECOMMENDATION of that date. All changes subsequent to that date are errata corrections or editorial.

| Date | Author | Details |
| --- | --- | --- |
| 28 December 2003 | Hugh Wallis | Corrected schema definition of arcroleType to include the ` @id` attribute as described in [**Section 5.1.4**](#_5.1.4). Changed the document status, title, headers and footers etc. to reflect the status of RECOMMENDATION. |
| 17 December 2003 | Hugh Wallis | Enhanced Example 6 to include examples of each rule relating to relationship prohibition and overriding. |
| 17 December 2003 | Phillip Engel | Added [**Section 1.6**](#_1.6) to document namespace prefix conventions used in the text. Various typographical and formatting corrections and improvements throughout. Further tidying up of language around the notion that arcs represent relationships for greater consistency. Edited "new arc roles" to read "custom arc roles" and "new role" to read "custom role" throughout, for consistency of terminology. Added section header for some non-numeric item types in table 7. |
| 15 December 2003 | Hugh Wallis | Editorial corrections to definitions in [**Section 1.4**](#_1.4) – added defintion of "ancestor". Replaced occurrences of "instance document" and "XBRL document" with the more precise "XBRL instance" throughout, where appropriate. Deleted "sets" from [**Section 3.5.3.9.7.4**](#_3.5.3.9.7.4) when referring to XML fragments since it had previously been erroneously introduced as an editorial change. Corrected " **MAY** " to " **MUST** " in the second sentence of [**Section 4.2**](#_4.2) (`  <schemaRef>  ` element). Replaced line drawings with graphics in Examples 24, 40, 41, 42. Updated text in subsections of [**Section 5.2**](#_5.2) to clarify the notion that arcs represent relationships. Corrected broken hyperlinks and outdated references in [**Section 1.3**](#_1.3) and [**Section 6**](#_6). Removed references to schemas that are no longer part of the specification from [**Appendix A**](#A). Deleted [**Appendix D**](#D) (Approval Process). Various minor grammatical and typographical corrections throughout the document. |
| 10 December 2003 | Hugh Wallis | Corrected section formatting in [**Section 3.5.3.7.3**](#_3.5.3.7.3). Corrected Example 51 to add `xbrli:periodType` attribute. Removed sentence from [**Section 3.5.3.9**](#_3.5.3.9) that appeared to contradict the limitations on number of XML fragments that can be pointed to by ` @xlink:href` s resulting from the restrictions on allowable xpointer syntax detailed in [**Section 3.5.4**](#_3.5.4). Changed document dates to 2003-12-11. |
| 09 December 2003 | Hugh Wallis | Replaced remaining occurrences of "network(s) of arcs" with "network(s) of relationships". Removed the redundant item type uriItemType and changed schema dates to 2003-12-31. Changed schema dates from 2003-10-22 to 2003-12-31. Editorial changes to use the word "represent" instead of "define" when referring to how arcs are used to "represent" relationships. Reworded [**Section 3.5.3.9**](#_3.5.3.9) to refer to locators in the singular rather than the plural. Reworded Example 5 (Correct use of arcs) to allow for the possibility of various alternative legal constructions. Removed unnecessary prohibition on relationships being equivalent to themselves in [**Section 3.5.3.9.7.4**](#_3.5.3.9.7.4) and further clarified the language elsewhere in this section. Added the standard role for `  <footnote>  ` elements: `"http://www.xbrl.org/2003/role/footnote"`. Added "identical" to the definition of set-wise equality in [**Section 4.10**](#_4.10) to support the language in [**Section 3.5.3.9.7.4**](#_3.5.3.9.7.4). Renamed [**Section 4**](#_4) to "XBRL Instances" and inserted the missing section heading 4.1 "The `  <xbrl>  ` element." Much of the above pursuant to comments from Paul Warren and Don Dwiggins. |
| 09 December 2003 | Geoffrey Shuetrim | Modified sections on extended link arcs and taxonomy linkbases to revise treatment of networks of relationships and relationship prohibition and overriding. Replaced arc equivalence definition with relationship equivalence definition. Moved the documentation of relationship prohibition and overrides back to the section on extended link arcs and out of the section on taxonomy linkbases so that it also relates to footnoteLinks and any other kinds of linkbases that get developed as XBRL modules. |
| 07 December 2003 | Phillip Engel | Modified [**Section 3.5.2.4**](#_3.5.2.4), [**Section 3.5.2.4.5**](#_3.5.2.4.5), [**Section 3.5.2.5**](#_3.5.2.5), [**Section 3.5.2.5.5**](#_3.5.2.5.5), [**Section 5.1.3**](#_5.1.3) and [**Section 5.1.4**](#_5.1.4) to clarify issues around custom role attribute definitions on simple links and the scope of `  <roleRef>  ` and `  <arcroleRef>  ` elements. Modified [**Section 3.5.3.9**](#_3.5.3.9), [**Section 3.5.3.9.5**](#_3.5.3.9.5), Section 3.5.3.9.5.1 (relocated to [**Section 5.2**](#_5.2)), Section 3.5.3.9.5.2 (renumbered Section 3.5.3.9.5.1 and part relocated to [**Section 5.2**](#_5.2)), Section 3.5.3.5.9.3 (renumbered to Section 3.5.3.5.9.2), [**Section 5.2**](#_5.2) to clarify language relating to arc prohibition and traversal (removing confusing or ambiguous references to the XLink notion of traversal) including a more rigorous definition of equivalence of arcs. Added examples of one-to-one, one-to-many and many-to-many arc relationships. Corrected example of the correct use of arcs with respect to the prohibition on duplicate arcs ( [**Section 3.5.3.9**](#_3.5.3.9)). Clarified the behaviour of prohibiting arcs within networks. |
| 05 December 2003 | Hugh Wallis | Separated out the text relating to allowable forms of xpointer syntax from [**Section 3.5.1.2**](#_3.5.1.2) into a new [**Section 3.5.4**](#_3.5.4) and referenced it from [**Section 3.5.1.2**](#_3.5.1.2), [**Section 3.5.2.4.2**](#_3.5.2.4.2), [**Section 3.5.2.5.2**](#_3.5.2.5.2), [**Section 3.5.3.7.2**](#_3.5.3.7.2), [**Section 4.2.2**](#_4.2.2) and [**Section 4.3.2**](#_4.3.2). Provided more formal definitions of duplicate tuples and duplicate items. Added definitions of u-equals for sets and sequences. Clarified that equality predicates are symmetric. Updated restrictions on the ` @balance` attribute at the ends of essence-alias arcs so that they are only relevant if present on both ends of the arc. Corrected a left-over reference to "any of these two arc roles" in respect of essence-alias arcs. |
| 04 December 2003 | Hugh Wallis | Clarified the definition of u-equal ( [**Section 4.10**](#_4.10)) to ensure that the order of the measures in the `  <unit>  ` element is not relevant. |
| 03 December 2003 | Geoffrey Shuetrim | Clarified [**Section 3.5.1.2**](#_3.5.1.2) as to allowable forms of xpointer syntax and updated examples. Added reference to XPointer element() Scheme specification in [**Section 6**](#_6). |
| 02 December 2003 | Hugh Wallis | Added clarifying text to Example 1 relating to simple links connecting only on resource at each end. Corrected the description of the `  <unit>  ` element in [**Section 4.8**](#_4.8). Corrected formatting in "Table 4. Equality predicate definitions". Removed the redundant (and incorrect) arcrole from the `  <schemaRef>  ` element in Example 5. Corrected example 31 (missing " `contextRef=` "). Applied additional restrictions on alias and essence concepts to ensure consistency between them ( [**Section 5.2.6.2**](#_5.2.6.2)). Reworded the definitions of the various definitionArc arcs and added sub-headings to [**Section 5.2.6.2**](#_5.2.6.2) for easier locations of the various definitions. |
| 17 November 2003 | Hugh Wallis | Corrected error in [**Section 4.11.1.3.1**](#_4.11.1.3.1) in fact-footnote arcrole syntax. |
| 13 November 2003 | Hugh Wallis | Updated definition of taxonomy schema in [**Section 1.4**](#_1.4) and moved it in the table to its correct alphabetical position. Inserted clarifying forward references to [**Section 5.1.3**](#_5.1.3) and [**Section 5.1.4**](#_5.1.4) in [**Section 3.5.2.4**](#_3.5.2.4). and [**Section 3.5.2.5**](#_3.5.2.5). Corrected example 3 to use `requires-element` instead of `requires-target`. Clarified `use="prohibited"` in Section 3.5.3.9.5.2. Added non-normative note re consistency between `  <schemaRef>  ` and ` @schemaLocation` in [**Section 4.2**](#_4.2). Clarified text in [**Section 4.8.2**](#_4.8.2) re the `pure` type. Clarified the definition of u-equal in [**Section 4.10**](#_4.10) where non-numeric items are involved. Changed titles of [**Section 5.1.3**](#_5.1.3) and [**Section 5.1.4**](#_5.1.4) to better indicate their purpose. Clarified wording relating to cycles in [**Section 5.1.4.3**](#_5.1.4.3). Corrected typos in Example 49. Updated definition and rules relating to `essence-alias` definition arc to properly handle scoping in tuples. Minor typographical edits. Removed restriction on duplicate roleType and arcroleType definitions within a taxonomy schema. |
| 26 October 2003 | Hugh Wallis | Corrected typos in examples 24 and 25 identified by Charles Hoffman and Yufei Wang |
| 20 October 2003 | Hugh Wallis | Amended the definition of tuple to have type="anyType" in order to accommodate validators that could not accept a more restrictive definition. Made changes to [**Section 4.9**](#_4.9) in order to define the restrictions on tuple in text rather than in XML schema and amended examples accordingly. Amended xbrl-instance definition of the tuple element and removed the defintion of tupleType which is no longer needed. Corrected the definition of the reference element in the xbrl-linkbase schema to add mixed="true" so that it can be validly derived from xl:resource (an amendment that was missed in the 2003-10-14 edits). Changed all dates from 2003-10-15 to 2003-10-22 except in this history section. |
| 16 October 2003 | Hugh Wallis | Corrected the schema fragment in [**Section 4.9**](#_4.9) (Tuples) to conform to the schema definition of tupleType. |
| 15 October 2003 | Geoffrey Shuetrim | Relaxed the XML Schema constraints on the attributes of the `  <documentation>  ` element to bring the XML Schema constraints into line with the wording of the specification, as suggested by Paul Warren. |
| 15 October 2003 | Hugh Wallis | Changed all dates from 2003-09-30 to 2003-10-15 except in this history section. Updated status section to reflect Candidate Recommendation 2 status. Updated Approval Process Appendix (D). Added clarification text regarding precision as it relates to calculations, from Justin Foley, and updated acknowledgements accordingly. Made minor formatting changes to various tables to address pagination and text wrapping issues. |
| 14 October 2003 | Geoffrey Shuetrim | Removed the reference parts schema from the specification. Added mixed="true" to the complexContent element in the tupleType content model to cover the mixed content in footnote and label resources. Corrected typographic errors flagged by Bill Palmer and Paul Warren. |
| 03 October 2003 | Geoffrey Shuetrim | Corrected formatting errors and an error in the standard arc role for footnotes as identified by Charlie Hoffman. |
| 03 October 2003 | Geoffrey Shuetrim | Corrected errors in examples that omitted precision information and ` @unitRef` information, as identified by Bill Palmer. |
| 02 October 2003 | Geoffrey Shuetrim | Tightened XML Schema constraints around the ` @xml:lang` and ` @xml:base` attributes to require attributes used where they are appropriate to have the correct namespace. Corrected errors in precision examples identified by Justin Foley. Inserted the tuple text changes provided by Paul Warren to reflect requirement that were previously only made explicit in XML Schema. Removed the obsolete reference to standard role types. |
| 27 September 2003 | Geoffrey Shuetrim | Modified text to allow roleRef and `  <arcroleRef>  ` elements inside the `  <xbrl>  ` element. Modified the DTS discovery algorithm accordingly. Incorporated text on finding two definitions for the same custom role or arcrole, as supplied by Phillip Engel. Modified the definitions of numeric item v-equality to include a requirement of u-equality. Modified the definition of item duplicates to include a requirement of u-equality for numeric items. Added explanatory text to the preferredLabel attribute documentation, noting that there is no requirement for the label extended link and presentation extended link to have the same ` @xlink:role` attribute value. |
| 25 September 2003 | Geoffrey Shuetrim | Added sections explaining the usage of the ` @unitRef` and ` @contextRef` attributes. Added ISO 8601 to the references to related literature section. |
| 24 September 2003 | Geoffrey Shuetrim | Removed the dependence on the xml.xsd schema from the XBRL specification by eliminating the XML Schema validation of the xml namespace attributes used by XBRL (base and lang). Standardised the wording of section headings. Added ` @xml:base` sections for all of the specific simple link elements documented in the specification. Made editorial changes to the sections introduced by Phillip Engel on 2003-09-18. Fixed the error in the treatment of items with "shares" units, as noted by Paul Warren. Added Don Bruey’s example for appropriate usages of the xlink:href attribute. |
| 22 September 2003 | Hugh Wallis | Updated specification wording to reflect status as a candidate recommendation. Reworded the details relating to the interpretation of endDate and instant values where no time component has been provided. Added a reference from the section on monetary, pure and shares items types back to the section that formally defines the constraints relating to usage of these item types. |
| 21 September 2003 | Geoffrey Shuetrim | Corrected an error in example 4 indicating that the `  <schemaRef>  ` element was defined in the xbrl-instance namespace instead of the xbrl-linkbase namespace. Corrected an error in the XML Schema for `  <schemaRef>  ` elements that used the wrong namespace prefix for simpleType. Incorporated the suggested rewording of the algorithm for inference of precision from decimals provided by Hugh Wallis to handle a specific boundary case. |
| 19 September 2003 | Geoffrey Shuetrim | Updated the schemas and schema fragments to 2003-09-30. Corrected an error in the target namespace for the `  <schemaRef>  ` element in the specification examples as per the suggestion from Paul Warren. |
| 18 September 2003 | Phillip Engel | Modified the handling of custom roles and arc roles to handle the separation of the identifying URI’s from the URL’s that locate the definitions of the custom roles and arc roles. Extended the DTS discovery algorithm to include discovery via roleRef and `  <arcroleRef>  ` elements. |
| 17 September 2003 | Geoffrey Shuetrim | Stated explicitly that documents used as a starting point for DTS discovery are also part of the DTS. Corrected the title for the section on the ` @id` attribute for linkbase elements. Ruled out traversal of any arc twice in the definition of cycles. Clarified the role of abstract elements in networks of concepts. |
| 10 September 2003 | Geoffrey Shuetrim | Removed the requirement that the xbrl-instance-2003-09-30.xsd schema be part of a DTS. Made editorial changes to the drafting of the specification to eliminate redundant wording and to clarify terminology for alias-essence relationships. Inserted the XHTML label example provided by Don Bruey. Changed references to XLink so that they use the reference to the relevant bibliographic entry. Modified the specified ` @xlink:role` attribute on extended links to make them mandatory and to require them not to be empty. Eliminated the inferred ` @xlink:role` attribute value in the event that the attribute is missing or empty. Amended the definition of calculation binding to items in XBRL instances to leverage the definition of item duplicates and to ensure that the rules for calculation binding did not obstruct the binding of calculation arcs through tuple structures. Removed the requirement to use XML Schema to describe relationships between elements within tuples to facilitate binding in calculation relationships. |
| 05 September 2003 | Geoffrey Shuetrim | Refined the definition of a network of arcs in a DTS to also take into account arcs that have been over-ridden rather than explicitly prohibited. |
| 04 September 2003 | Geoffrey Shuetrim | Changed references to the XLink standard to references to the XLink specification as suggested by Don Bruey. Modified the introduction to taxonomy linkbases to clarify the role of linkbases in providing semantics for XBRL defined reporting concepts. Corrected the section heading error for locators in `  <definitionLink>  ` elements noted by Campbell Pryde. Eliminated a redundant statement that xlink:arcrole attributes must be absolute URIs. Changed the value in example 5 to more clearly demonstrate the impact of the ` @precision` attribute. Clarified the explanation of decimals=-2 in example 8 by replacing the use of the ambiguous word, "prior". Removed the reference to the now illegal empty `  <scenario>  ` element in example 22. |
| 02 September 2003 | Geoffrey Shuetrim | Reworded the specification relating to the handling of `  <measure>  ` elements for pure numbers to clarify the required namespace and to clarify the treatment of percentage values. Added "placement" to the documentation of the `http://www.xbrl.org/2003/role/presentationRef` and eliminated the redundant `http://www.xbrl.org/2003/role/placementRef` reference role as recommended by Josef Macdonald. This change brings the reference treatment into line with the label treatment. |
| 28 August 2003 | Geoffrey Shuetrim | Removed the requirement that c-equal items not be s-equal and removed the requirement that u-equal items not be s-equal, as recommend by Frank Lippold. |
| 21 August 2003 | Geoffrey Shuetrim | Removed the detail on tuple content model restrictions in the section on changes in XBRL instances. Corrected the title for the section on `  <documentation>  ` elements in linkbases. Eliminated the xbrl-role-2003-07-31.xsd schema from the specification. Removed the obsolete reference to the non-numeric contexts in the explanatory text for example 6. Removed the requirement that the requires-element relationship only bind when the related items are c-equal. |
| 21 August 2003 | Geoffrey Shuetrim | Removed the any element from the set of allowed elements in tuple content model definitions. Added the attribute element to the set of allowed elements in tuple content model definitions. Added a requirement that tuple content models cannot include abstract elements. |
| 18 August 2003 | Geoffrey Shuetrim | Added discovery of linkbases from other linkbase locators to the DTS discovery algorithm to cover situations where traversals to resources in linkbases are being prohibited in other linkbases. |
| 14 August 2003 | Geoffrey Shuetrim | Corrected a section cross reference to the "Taxonomy Linkbases" section. |
| 13 August 2003 | Geoffrey Shuetrim | Flagged the changes to the content of the `  <unit>  ` element in the section on changes in XBRL instances. |
| 13 August 2003 | Geoffrey Shuetrim | Added http:// to the beginning of the scheme URIs in example 13. |
| 12 August 2003 | Geoffrey Shuetrim | Added a value to the `  <identifier>  ` element in example 15. |
| 08 August 2003 | Geoffrey Shuetrim | Changed the content model for the `  <documentation>  ` element from complexContent to simpleContent on advice from Takuki Kamiya. Responded to editorial comments from Charlie Hoffman. Updated the section on changes to the specification to reflect the modifications to the content model for the `  <unit>  ` element. |
| 06 August 2003 | Geoffrey Shuetrim | Added documentation of the ` @xml:base` attribute on simple links and extended links. Fixed references to the numerator and denominator elements in the units element, changing them to references to the unitNumerator and unitDenominator that distinguish them from the elements used in fractionItemType items. Rewrote the treatment of unit equality definitions in the section on equality predicates to cover `  <unitNumerator>  ` and `  <unitDenominator>  ` elements and the `  <divide>  ` element and the `  <measure>  ` element. |
| 05 August 2003 | Geoffrey Shuetrim | Removed the reference to inference of decimal places accuracy for numeric items in the section on inference of precision from decimals. Replaced reference to numerator and denominator elements in the `  <divide>  ` element with `  <unitNumerator>  ` and `  <unitDenominator>  ` elements. Clarified the definition of s-equality for unit elements. Corrected the omission of ` @xml:base` attributes on simple and extended links. Imposed fixed values for ` @xlink:type` attributes. Changed the DTS requirement relating to the XBRL-instance schema to use a normative **MUST** rather than a must. Clarified example 36 regarding the references supporting the concepts in the general-special relationships. |
| 31 July 2003 | Geoffrey Shuetrim | Made the usedOn attribute a QName and eliminated the enumeration restriction on it. Changed the schema dates to 2003-07-31 from 2003-07-28. Corrected the definition of arc equivalence to cover prohibition of arcs to resources. Introduced the requirement that a DTS must include a taxonomy schema that imports the XBRL-instance schema. Prohibited values of zero for the ` @weight` attribute on `  <calculationArc>  ` elements. Eliminated the XHTML content in simple links. |
| 30 July 2003 | Geoffrey Shuetrim | Introduced the section on XLink and XBRL. Reorganised the sections on extended links, linkbases and simple links to refer to the new section on XLink and XBRL. Reorganised the section on taxonomy extended links to bring together all materials for each type of extended link into the one sub-section. Reorganised the section on XBRL instances to bring together the various sections dealing with syntax in taxonomy schemas. Clarified the definition of arc equivalence to make the definition no longer contingent on extraneous attribute values. Added the requirement that the ` @balance` attribute only be used on items with a monetaryItemType or a type derived therefrom. Clarified the interpretation of tupleTypes being final with respect to extension. Changed the font to Verdana from Times New Roman. Modified restrictions on parent-child arcs to allow undirected cycles. Updated the xbrl-role.xsd schema to reflect the new syntax. Updated the schema appendix to reflect current syntax. |
| 29 July 2003 | Geoffrey Shuetrim | Removed the items types: NOTATIONitemType, NMTOKENItemType, NMTOKENItemType, NMTOKENSItemType, IDItemType, IDREFItemType, IDREFSItemType, ENTITYItemType and ENTITIESItemType. Changed the content model for the `  <xbrl>  ` element to require a `  <schemaRef>  ` element and to require that the `  <schemaRef>  ` elements occur first, followed by linkbaseRef elements, followed by the other possible children in any order. Also introduced the requirement that at least one `  <schemaRef>  ` element occurs as a child of the `  <xbrl>  ` element. Changed the name of the numerator and denominator child elements of the `  <divide>  ` element to be called `  <unitNumerator>  ` and `  <unitDenominator>  ` to avoid a naming clash with the fractionItemType children. Added the documentation element to be used for documentation on `  <linkbase>  ` elements and extended link elements. Added ID attributes to the linkbase and extended link elements. Changed the DTS discovery model to ensure linkbases contained in discovered schemas are also discovered. Clarified the treatment of linkbases that are nested within taxonomy schemas. Modified the definition of taxonomy schemas to allow XML Schemas that do not import the XBRL instance schema. |
| 28 July 2003 | Geoffrey Shuetrim | Modified the schemas to tighten the XML Schema constraints on extended links and their content. Clarified the definition of arc equivalence to cover arcs from concepts to resources instead of just concepts to other concepts. Modified the calculationLink XML Schema content model to allow flexible ordering of children. |
| 23 July 2003 | Geoffrey Shuetrim | Changed the instantaneous attribute to be called the ` @periodType` attribute. Added the `  <schemaRef>  ` element. Rearranged the standard arc role value sections, merging them with the descriptions of each of the specific arc elements. Separated the `  <unit>  ` element from the `  <context>  ` element. Changed the numericContext and nonNumericContext to a single `  <context>  ` element and modified the attributes on items to reference unit and `  <context>  ` elements using ` @contextRef` and unitRef attributes. |
| 22 July 2003 | Geoffrey Shuetrim | References to MIME type have been removed from the specification. Moved the section on the linkbase related schemas to the appendix listing the text of the various schema documents supporting this specification. Modified the syntax for the unit element to eliminate the `multiply` element. Added the section on levels of conformance of XBRL processors. |
| 20 July 2003 | Geoffrey Shuetrim | Removed profile attributes. Removed the references to deprecated syntax, eliminating the syntax instead. Removed the aloc, absoluteContext and relativeContext elements from the `  <calculationLink>  ` element, removing the capacity for expressing cross-context calculations using the calculationLink. Removed the references to an ability to associate concepts to remote labels Removed the CWA attribute. Changed all rules expressed in terms of processing errors or fatal errors into rules expressed in terms of **MUST** and **MUST NOT** style requirements. |
| 09 June 2003 | Hugh Wallis | Numerous editorial changes, clarifications etc. Incorporated changes pursuant to the resolution of comments 025 (no change needed), 030 (no change required), 032, 034, 036, 037, 045, 055 |
| 16 May 2003 | Hugh Wallis | Incorporated changes pursuant to the resolution of comments 003, 004, 005, 006, 007, 008, 009, 010, 011, 013, 014, 015, 018, 019, 020, 021, 022, 026, 028 |
| 29 April 2003 | Hugh Wallis | Formatting, table headings (bolding and repeating on new pages), prevent table cells splitting across pages where appropriate, font, pagination, hyperlinking and typographical changes. |
| 23 April 2003 | Walter Hamscher | Edits to incorporate name of release as the name of specification, updated status to Public Working Draft. Updated list of editors, contributors and Acknowledgements. Corrected numerous typographical and style errors caught by Charles Hoffman, Campbell Pryde and Hugh Wallis. |
| 21 April 2003 | Hugh Wallis | Finalised changes required to present to Domain Working Group as a candidate for submition to the ISC for approval as Public Working Draft. Incorporated minor corrections from Charles Hoffman. Added detailed text to define v-equal for numeric items of different types in a complete and unambiguous way. Various minor formatting and grammatical updates. |
| 20 April 2003 | Walter Hamscher | Changed the relative context specifiers to use the XML Schema duration type; provided tables detailing the matching rules for absolute contexts; removed proposed absolute and relative context filters; provided an example of an absolute context in use. Consolidated all roles and arc roles as fragments under the http://www.xbrl.org/2003/role namespace URI. Added footnote linkbase material in several places per suggestion of Phillip Engel. |
| 17 April 2003 | Walter Hamscher | Edited arc role material to incorporate distinction between directed and undirected arcs, adding attributes to the arc role definition material, along with changes to schema. Removed composition linkbase material, and rewrote the tuple related material, moving composition linkbase functionality relating to extensions into the definition linkbase, and defining the legal schema constructs appearing in restrictions of the tuple type. Clarified text relating to equality testing in the presence of the ` @precision` attribute. Added note clarifying that items may only refer to a context ID that is within the scope of the enclosing `  <xbrl>  ` element. Added note clarifying that the general-special arc role has the same semantic intent as 2.0’s definition parent-child arc. |
| 14 April 2003 | Walter Hamscher | Updated material on arc roles and equality definitions. Updated schemas accordingly. Made the symmetry of arc roles more explicit and made explicit the requirement that arcs be symmetric. Added standard "zero" label roles. Added table captions and table of tables. Generalised c-equal to not require identical element names so as to use it in alias-essence definitions. Removed unused references. Changed the `absoluteContext` and `relativeContext` types to `anyURI` so as to allow for remote context definitions. |
| 08 April 2003 | Walter Hamscher | Typo, schema, and reference fixes in preparation for internal release. |
| 06 April 2003 | Walter Hamscher | Fixed example text based on suggestions of Rene van Egmond and Don Dwiggins of UBmatrix. Section Section 5.3 on derived types changed to mandate the derivation of item types by restriction from a provided item type. Corrected miscellaneous typos in examples and schemas detected by Charles Hoffman. Added more to Example 8. Began converting to use of upper case modals. Weakened directions for use of the ` @balance` attribute from " **MUST** " to " **MAY** " at direction of DWG. Incorporated comments from David vun Kannon and Geoff Shuetrim, adding the "/positive" label role, defining "linkbase namespace" and "instance namespace", clarifying the role of XBRL validation, moving MIME type node to the end, possibly to be removed; changed the profile description to use a set of Boolean attributes while removing the nopointers profile, adding the `pure` type and item type, created the ISO4217 namespace and schema, rearranged description of ` @order` attribute, made fixes to the absolute and relative context examples. Removed `conceptMatch` attribute and generalised the arcRole definition mechanism to cover any arc role with concomitant changes to the schema. Replaced occurrences of must, shall and may with **MUST** and **MAY**. Added notes regarding the impact of combining schemas with different name spaces on phenomena such as arc overrides and arc role definitions. Rewrote sections relating to equivalence and duplications to provide precise definitions of various notions of equality. Changed the `relativecontext` and `absoluteContext` to normal elements instead of resources, and restricted the use of the `relativeContext` and `absoluteContext` attributes only within the `  <calculationLink>  ` element. Added a calculation linkbase example using relative contexts. Updated the label and reference linkbase role tables to reflect most recent changes from Josef MacDonald. Updated schemas. |
| 30 March 2003 | Walter Hamscher | Added clarifications and other edits from Hugh Wallis, Eric E. Cohen, and others. Revised the four introductory linkbase examples using material provided by Charles Hoffman. Incorporated `  <arcroleType>  ` material from Phillip Engel and propagated arcrole syntax changes throughout. Distinguished between XBRL validation and optional calculation linkbase validation. Changed `baseProfile` to `profile` as list of tokens and propagated changes throughout. Revised schemas. Fixed typos, replaced "instance document" and variations with "XBRL instance" throughout. Added example captions. Changed the `use="required"` statement to apply only to the `part-whole` arc role. Expanded the examples of duplicates and equivalence. Removed sections 6 and 7 (semantics) since this material is now integrated into [**Section 4**](#_4) and [**Section 5**](#_5). |
| 23 March 2003 | Walter Hamscher | Added acknowledgement of Domain working group members. Defined the `numericItemAttrs` attribute group, `rootType` complex type that disallows nested `group` elements, disallowed nested `  <segment>  ` elements, and otherwise brought consistency to other Schema changes throughout the text. Cleaned up text relating to allowed item types. Defined equality for numeric items in the face of differing values of ` @precision` and ` @decimals`. Clarified that equality of items is *not* affected by adding "ID" attributes. Removed the optional `  <unit>  ` sub-element in `nonNumericContext` and multiple `  <segment>  ` sub-elements in the entity type. Moved the bulk of the tuple definition material to the linkbase section as a placeholder. Changed arcroles to remove `linkprops` path element. Added text about arc cycles. Shortened the footnote example. Used the newly DWG approved debit/credit material. Specified the two legal locations for `  <linkbase>  ` elements. Added the `  <linkbase>  ` element syntax. Provided an example of remote label content and moved this material to the label resource section. Tentatively restricted the `  <linkbaseRef>  ` element to empty content. Included schema fragments for every defined element. Removed linkprops component from all defined role and arcrole values. Tentatively added three `negative` label roles pending DWG approval. Added a tentative table of `reference` resource roles. Added mention of XML Base in three places and note regarding absolute URI usage in two. Incorporated material from Geoff Shuetrim into the composition linkbase, which includes the tuple arc, sequence resource, and choice resource. Removed element-dimension from the calculation linkbase and incorporated text into the definition linkbase for the alias-essence relationship. |
| 11 March 2003 | Walter Hamscher | Began revisions to `relativeContext` and `absoluteContext` and miscellaneous fixes to schema material. |
| 11 March 2003 | Geoffrey Shuetrim | Added a section proposing a variant on the calculation link processing model that is sensitive to calculation link role attribute values. Introduced a number of smaller edits and queries regarding the approach in relation to tuples and other areas of significant change since the previous draft. |
| 10 March 2003 | Walter Hamscher | Added relative contexts to the calculation linkbase and the relativeContext element and all its paraphernalia. Tentatively added absolute contexts. Redefined equivalence so as to ignore non-XBRL attributes and rely only on tuple elements. Added example of tuple scoping for calculation arcs. Removed the stock-flow and flow-stock arcroles. Added additional explanatory text to the abstract. Separated the explanation of linkbases from taxonomies and schemas. Added table of primitive and derived types and item types. Tightened up language around the `href` attribute of `  <linkbaseRef>  `. More formatting tweaks particularly to non-normative examples. |
| 07 March 2003 | Walter Hamscher | Changed the `baseProfile` attribute to a URI. Added "0.0" as a legal value for the ` @weight` attribute on `  <calculationArc>  `. Added additional material regarding schemaLocation. Added list of legal item types. |
| 06 March 2003 | Walter Hamscher | Changed `stockFlow` to `instantaneous` to generalise. Added example of Spanish and Portuguese labels to reinforce the point that schemas and linkbases can be mixed and matched by any given schema. Defined "identical" "equivalent" and in some cases, "matching," and used these to rewrite context processing and duplicate items. Defined "inconsistency" of ` @decimals` and ` @precision` attributes. Changed `xbrlPrecision` to `precisionType`, etc. Added the `baseProfile` attribute and noted inline where it impacts the scope of XBRL syntax recognised. Moved the ` @order` attribute to appear on all arc elements. Yet more formatting changes, small fixes to examples and schema fragments but these still need to be finalised with published schemas. |
| 18 February 2003 | Walter Hamscher | Responded to comments from Hugh Wallis and Geoff Shuetrim, in most cases by editing the text as requested, and noted areas requiring further resolution. Tried to increase the consistency of formatting, in particular to indicate all normative material as unshaded even when appearing inside a table. |
| 08 February 2003 | Hugh Wallis | Numerous editorial changes and comments added. Changed, deleted and added sections about precision and decimals. Added definitions section. Added a fractionItemType data type. |
| 27 January 2003 | Walter Hamscher | Added normative text relating to arcroles. Removed the reference-actual and actual-reference arcroles to conform with Linkbase clarity issues. Revised the section on arcrole to conform to linkbase clarity requirements insofar as they are currently defined. Described the definitionArc as a "specialisation / generalisation" arc. When used to define a tuple, the relationship is actually a part-whole relationship, as noted when defining the constraint that children of a tuple definition must not appear in XBRL instances except when wrapped by the parent. Added placeholders for numeric precision and decimal sections. Removed anySimpleType from the schema. Changed references to 2.1 to Tulip. Reformatted entire document based on more recent XBRL International documents. Changed example uses of `<group>` to `<xbrl>`. |
| 22 January 2003 | David vun Kannon | Added material clarifying the syntax and semantics of tuples. |
| 19 January 2003 | Geoffrey Shuetrim | Added material relating to linkbase clarity, and all new roles for `  <label>  ` resources. |
| 05 September 2002 | David vun Kannon | Released as internal working draft of 2.1 specification. Included `stockFlow` and ` @balance` attributes and XML Schema primitive data types. |
| 12 June 2002 | David vun Kannon | Began 2.1 changes. Eliminated reference to the group element. Added xbrl root element. Changed definition of duplicate items to allow duplicates in separate tuples. Added prohibition of duplicate tuples. |
| 09 January 2002 | David vun Kannon | Corrected the discussion of the datatype of item to refer to anySimpleType. |
| 13 December 2001 | David vun Kannon | Added additional explanatory text relating to concept equivalency. Eliminated references to "draft" status. |
| 21 November 2001 | Walter Hamscher | Added additional explanatory text relating to links and linkbases and their intended uses, reformatted examples and callouts for readability, applied "code" and "code block" styles as appropriate, corrected minor typos. |
| 15 November 2001 | Louis Matherne | Edited for consistency and readability. Added "example" and "suggested" label to several illustrations for clarity. In the example at [**Section 4.4**](#_4.4), changed the link pointing to a file on the web site. Change the page footer to XBRL Specification v2, 2001-11-14. Added text at "Status of This Document". |
| 15 November 2001 | David vun Kannon | Added wording on MIME types, priority deadlock in overriding arcs. |
| 16 October 2001 | Yufei Wang | \[vun Kannon/Wang\] Edited for consistency and readability. Modified examples to make namespaces consistent. Incorporated commentary from discussion groups and added explanatory material. |
| 24 August 2001 | Luther Hampton | Edited for consistency and readability. Modified examples to make namespaces consistent. Incorporated commentary from discussion groups and added explanatory material. |
| 21 June 2001 | David vun Kannon | First draft of enhanced version. Modified examples to reflect use of substitution groups and other features of XML Schema. Modified taxonomy section to reflect use of XML Linking structures. |
| 31 July 2000 | David vun Kannon | Final review. Added namespace prefix to many examples. |
| 20 July 2000 | David vun Kannon | changed sense={add, subtract, none} to numeric weight. |
| 27 June 2000 | David vun Kannon | Corrected schemaLocation attribute examples and explanation. Corrected typos and namespace references. |
| 12 April 2000 | Charles Hoffman | Made corrections to reference to public discussion group, changed xfrml-public to xbrl-public. Changed the links pointing to this document on the web site from 00-04-04 version to 00-04-06 version. Removed a link in [**Section 1.2**](#_1.2) of this document to a document (March 3rd, 2000 version of SPEC) in the private eGroups vault. Updated PDF version and HTML versions for all of these changes. |
| 06 April 2000 | Walter Hamscher | Made corrections to the SAMP and IMA examples. Remaining text did not change. |
| 02 April 2000 | Walter Hamscher | In the taxonomy, eliminated "total" from element names or changed them to "gross" as appropriate. In the taxonomy, changed "cash flow" to "cash flows". In the taxonomy, changed "intangible assets" in long term assets to "intangibles". Added additional examples of the period attribute. Deleted the \[Instance Rationale\] note, since the design rationale discussion covers all the necessary points. Removed the \[Style Everywhere\] note, since we have a current compromise which allows the group element to contain elements other than items. Added section discussing the meaning of "period" and why a specific date and duration is a good idea. Added section discussing prior period balances and how that interacts with taxonomies. Added note on alternate breakdowns. Added cautionary note about applications assuming duration. Fixed all the capitalization problems in the examples to agree with 00-04-04 release of the files. |
| 29 March 2000 | Walter Hamscher | Miscellaneous typo corrections. Continuing repairs to text that concerns the fact that markup is forbidden inside items. Changed all "CamelCase" names to "camelCase". Added an additional paragraph explaining the "sense" attribute. Checked for references to "footnote" that should have been references to Notes. Added the \[Long Names\] note. |
| 28 March 2000 | Walter Hamscher | Added the "pure" datatype, deleted the \[unit examples\] issue. Reverted to original explanation of the item tag disallowing embedded markup. Changed wording of the paragraph contrasting namespaces with the schemaLocation attribute. Added \[Instance Includes\] suggestion raised by David vun Kannon. Added explanation of parsing implications of decimalPattern. Got rid of the \[Time Duration\] issue and changed to an explanation that we are differing from XML Schema convention. Miscellaneous typo corrections. |
| 24 March 2000 | Walter Hamscher | Changed text references to "taxonomy attribute" to schemaLocation. Fixed typo in example of Section 3.12. Fixed the period definition with a better reference for ISO 8601 than the incomplete summary given in the W3C material. Miscellaneous typo corrections. |
| 23 March 2000 | Walter Hamscher | Added change log. Changed "taxonomy" to schemaLocation. Repaired broken definition of period attribute, raised new timeDuration issue. Included new "unique elements" issue. Raised issue of deleting "links". Added XML Schema: Primer reference. Changed text of the Unit Examples text, fixing the Moody's example and removing the PURE example. Added issue regarding label processing. Got rid of the Parents Required issue, left the discussion. Added historical notes regarding the fundamental decisions agreed to at the Chicago meeting. Changed scalefactor to scaleFactor. Changed taxonomy to schemaLocation. Added distinction between financial presentation and accounting, in the context of order independence. Similar distinction with respect to negative balances. Added discussion of the unique naming issue. Fixed the non-negative-integer datatype of order. Added taxonomy extensions issue, from Eric Cohen. Miscellaneous typo corrections. |
| 19 March 2000 | Walter Hamscher | First released version. |

## Appendix C Intellectual property status (non-normative)

This document and translations of it may be copied and furnished to others, and derivative works that comment on or otherwise explain it or assist in its implementation may be prepared, copied, published and distributed, in whole or in part, without restriction of any kind, provided that the above copyright notice and this paragraph are included on all such copies and derivative works. However, this document itself may not be modified in any way, such as by removing the copyright notice or references to XBRL International or XBRL organizations, except as required to translate it into languages other than English. Members of XBRL International agree to grant certain licenses under the XBRL International Intellectual Property Policy ([www.xbrl.org/legal](http://www.xbrl.org/legal)).

This document and the information contained herein is provided on an "AS IS" basis and XBRL INTERNATIONAL DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTY THAT THE USE OF THE INFORMATION HEREIN WILL NOT INFRINGE ANY RIGHTS OR ANY IMPLIED WARRANTIES OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.

The attention of users of this document is directed to the possibility that compliance with or adoption of XBRL International specifications may require use of an invention covered by patent rights. XBRL International shall not be responsible for identifying patents for which a license may be required by any XBRL International specification, or for conducting legal inquiries into the legal validity or scope of those patents that are brought to its attention. XBRL International specifications are prospective and advisory only. Prospective users are responsible for protecting themselves against liability for infringement of patents. XBRL International takes no position regarding the validity or scope of any intellectual property or other rights that might be claimed to pertain to the implementation or use of the technology described in this document or the extent to which any license under such rights might or might not be available; neither does it represent that it has made any effort to identify any such rights. Members of XBRL International agree to grant certain licenses under the XBRL International Intellectual Property Policy ([www.xbrl.org/legal](http://www.xbrl.org/legal)).

## Appendix D Errata Corrections incorporated in this document

This appendix contains a list of the errata that have been incorporated into this document. This represents all those errata corrections that have been approved by the XBRL International Specification Working Group (SWG) up to and including 20 February 2013. Hyperlinks to relevant e-mail threads may only be followed by those who have access to the relevant mailing lists. Access to internal XBRL mailing lists is restricted to members of XBRL International Inc.

| Number | Date | Sections | Details |
| --- | --- | --- | --- |
| 1. | 15 January 2004 | [**Section 5.2.2.1**](#_5.2.2.1)   [**Section 5.2.2.3**](#_5.2.2.3)   [**Section 5.2.3.1**](#_5.2.3.1)   [**Section 5.2.3.3**](#_5.2.3.3) | `  <loc>  ` elements in `  <labelLink>  ` and `  <referenceLink>  ` elements should be permitted to point to label and reference resources to facilitate prohibition  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4499](http://groups.yahoo.com/group/XBRL-SpecV2/message/4499)  (further corrections approved 2004-02-05) |
| 2. | 22 January 2004 | [**Section 5.2.4.2**](#_5.2.4.2) | Example 49 is in error and contains misleading reasoning for the presence of various attributes  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4478](http://groups.yahoo.com/group/XBRL-SpecV2/message/4478) |
| 3. | 22 January 2004 | [**Section 4.10**](#_4.10) | Typographical error. The definition of [S-Equal](#s-equal) for `  <context>  ` incorrectly requires `  <entity>  ` sub elements to be [X-Equal](#x-equal). This should read [S-Equal](#s-equal).  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4479](http://groups.yahoo.com/group/XBRL-SpecV2/message/4479) |
| 4. | 05 February 2004 | [**Section 4.3**](#_4.3)   [**Section 4.11.1**](#_4.11.1)   [**Section 5.2.2**](#_5.2.2)   [**Section 5.2.3**](#_5.2.3)   [**Section 5.2.4**](#_5.2.4)   [**Section 5.2.5**](#_5.2.5)   [**Section 5.2.6**](#_5.2.6)   [**A.2**](#A.2) | `anyAttribute` required in definition of `  <linkbaseRef>  `  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4537](http://groups.yahoo.com/group/XBRL-SpecV2/message/4537)  Updated to include `anyAttribute` in definitions of `  <presentationLink>  `, `  <definitionLink>  `, `  <calculationLink>  `, `  <labelLink>  `, `  <referenceLink>  `, `  <footnoteLink>  `  (updated 2004-02-26)  (further confirmed 2004-03-04) |
| 5. | 05 February 2004 | [**Section 4.2**](#_4.2)   [**Section 4.3**](#_4.3)   [**A.1**](#A.1)   [**A.2**](#A.2) | Various occurrences of incorrect terminology that should read " [XBRL Instance](#XBRL-instance) " persisted in the final draft  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4489](http://groups.yahoo.com/group/XBRL-SpecV2/message/4489) |
| 6. | 19 February 2004 | [**Section 5.2.5.2**](#_5.2.5.2) | Remove prohibition on cycles in networks of summation-item arcs  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4570](http://groups.yahoo.com/group/XBRL-SpecV2/message/4570) |
| 7. | 19 February 2004 | [**Section 5.1.4.3**](#_5.1.4.3) | Remove the word "direct" from the definition of `cyclesAllowed="none"`  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4570](http://groups.yahoo.com/group/XBRL-SpecV2/message/4570) |
| 8. | 26 February 2004 | [**Section 5.1.4**](#_5.1.4) | Typographical error - changed "are role" to "arc role" |
| 9. | 29 April 2004 | [**Section 4.1**](#_4.1) | Correct missing namespace reference in example 8.  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4674](http://groups.yahoo.com/group/XBRL-SpecV2/message/4674) |
| 10. | 29 April 2004 | [**Section 5.2**](#_5.2) | Clarification of the definition of "root concept"  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4642](http://groups.yahoo.com/group/XBRL-SpecV2/message/4642) |
| 11. | 29 April 2004 | [**Section 5.1.3**](#_5.1.3)   [**Section 5.1.4**](#_5.1.4) | Correct typographical errors in Examples 35 and 36  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4640](http://groups.yahoo.com/group/XBRL-SpecV2/message/4640) |
| 12. | 29 April 2004 | [**Section 3.5.3.9.4**](#_3.5.3.9.4) | Correct `  <roleType>  ` to read `  <arcroleType>  `  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4640](http://groups.yahoo.com/group/XBRL-SpecV2/message/4640) |
| 13. | 24 March 2005 | [**Section 4.6.4**](#_4.6.4)   [**Section 4.6.7.1**](#_4.6.7.1)   [**Section 5.2.5.2**](#_5.2.5.2) | Clarification of text regarding binding of calculation relationships  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4614](http://groups.yahoo.com/group/XBRL-SpecV2/message/4614) and subsequent discussion threads |
| 14. | 29 April 2004 | [**Section 5.1.1.3**](#_5.1.1.3)   [**Appendix A**](#A) | Removal of vestigial references to floats in description of `fractionItemType` and removal of redundant `nonZeroNonInfiniteFloat` type from the instance schema  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4762](http://groups.yahoo.com/group/XBRL-SpecV2/message/4762) |
| 15. | 29 April 2004 | [**Section 3.5.1.4**](#_3.5.1.4) | Removal of redundant sentence (already covered in section 4.3.3)  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4774](http://groups.yahoo.com/group/XBRL-SpecV2/message/4774) |
| 16. | 29 April 2004 | [**Section 4.3.2**](#_4.3.2) | Correct section reference  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4775](http://groups.yahoo.com/group/XBRL-SpecV2/message/4775) |
| 17. | 29 April 2004 | [**Section 4.10**](#_4.10) | Removal of references to duplicate contexts and correction of typographical error in example instance (identifier section)  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4819](http://groups.yahoo.com/group/XBRL-SpecV2/message/4819) |
| 18. | 22 July 2004 | [**Section 4.7.2**](#_4.7.2) | Removal of outdated reference to "duration" in section |
| 19. | 22 July 2004 | [**Section 4.11.1**](#_4.11.1)   [**Section 5.2.1**](#_5.2.1)   [**Section 5.2.2**](#_5.2.2)   [**Section 5.2.3**](#_5.2.3)   [**Section 5.2.4**](#_5.2.4)   [**Section 5.2.5**](#_5.2.5)   [**Section 5.2.6**](#_5.2.6) | Correction of erroneous section references  See [http://groups.yahoo.com/group/XBRL-SpecV2/message/4769](http://groups.yahoo.com/group/XBRL-SpecV2/message/4769) |
| 20. | 22 July 2004 | [**Section 4.10**](#_4.10) | Insert missing word "than" |
| 21. | 22 July 2004 | [**Section 5.1.1**](#_5.1.1) | Clarify that chains of substitution groups are permitted by correcting ambiguous wording.  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4860](http://groups.yahoo.com/group/XBRL-SpecV2/message/4860) |
| 22. | 22 July 2004 | [**Section 3.5.3.3**](#_3.5.3.3)   [**Section 3.5.3.8.3**](#_3.5.3.8.3)   [**Section 4.2.3**](#_4.2.3)   [**Section 4.2.4**](#_4.2.4) | Clarify that ` @xlink:role` and ` @xlink:arcrole` attributes are to contain URIs as required by the [\[XLINK\]](#XLINK) specification [http://www.w3.org/TR/2001/REC-xlink-20010627/#link-semantics](http://www.w3.org/TR/2001/REC-xlink-20010627/#link-semantics)  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4825](http://groups.yahoo.com/group/XBRL-SpecV2/message/4825) |
| 23. | 10 June 2004 | [**Section 4.9**](#_4.9) | Remove restriction on [Abstract Elements](#abstract-element) appearing in the content model for tuples |
| 24. | 22 July 2004 | [**Section 5.2.2.3**](#_5.2.2.3)   [**Section 5.2.3.3**](#_5.2.3.3) | Correct typos in erratum 001 – replacing "prohibit" by "prohibited" |
| 25. | 22 July 2004 | [**Section 5.1.3**](#_5.1.3) | Correct the omission of the restriction of multiple definition of custom `  <roleType>  ` elements in the same [Taxonomy Schema](#taxonomy-schema) (consistent with the restriction on custom `  <arcroleType>  ` elements)  [http://groups.yahoo.com/group/XBRL-SpecV2/message/4850](http://groups.yahoo.com/group/XBRL-SpecV2/message/4850) |
| 26. | 29 July 2004 | [**Section 5.2.6.2.1**](#_5.2.6.2.1) | Typo ([S-Equal](#s-equal) for [U-Equal](#u-equal)) |
| 27. | 07 October 2004 | [**Section 4.9**](#_4.9) | Clarification of requirements relating to ID attribute on tuples |
| 28. | 02 September 2004 | [**Section 4.9**](#_4.9) | Various clarifications and easing of restrictions relating to tuples |
| 29. | 12 August 2004 | [**Section 5.1.1**](#_5.1.1) | Remove redundant sentence fragment |
| 30. | 02 September 2004 | [**Section 3.2**](#_3.2)   [**Section 5.1.5**](#_5.1.5) | Prohibit the use of `<redefine>` in [Taxonomy Schemas](#taxonomy-schema) |
| 31. | 07 October 2004 | [**Section 4.6**](#_4.6) | Prevent the prohibition of the xsd:id attribute on items in extension taxonomies |
| 32. | 07 October 2004 | [**Section 5.2.5.2**](#_5.2.5.2) | Limit summation-item relationships to [Numeric Items](#numeric-item) |
| 33. | 07 October 2004 | [**Section 5.2.3.2**](#_5.2.3.2) | Correct errors in Example 46 |
| 34. | 03 March 2005 | [**Section 4.6**](#_4.6)   [**Section 5.1.1.3.2**](#_5.1.1.3.2)   [**Appendix A**](#A) | Make `numerator` and `denominator` global elements to permit derivation from `fractionItemType` by restriction |
| 35. | 03 March 2005 | [**Appendix A**](#A) | Correct omission of `anyAttribute` from declaration of `positiveIntegerItemType`, `normalizedStringItemType`, `tokenItemType`, `languageItemType`, `NameItemType`, `NCNameItemType` |
| 36. | 03 March 2005 | [**Section 5.2.5.2.2**](#_5.2.5.2.2) | Correct column headings |
| 37. | 03 March 2005 | [**Section 4.10**](#_4.10) | Correct errors in example that indicated items are not [S-Equal](#s-equal) when in fact they are |
| 38. | 03 March 2005 | [**Section 5.1**](#_5.1) | Recommend that a target namespace be specified on [Taxonomy Schemas](#taxonomy-schema) and prohibit specification of an empty target namespace |
| 39. | 03 March 2005 | [**Section 3.5.2.4.4**](#_3.5.2.4.4) | Correct typographical error (`role` for `arcrole`) |
| 40. | 03 March 2005 | [**Section 3.5.2.5.4**](#_3.5.2.5.4) | Correct typographical error (`role` for `arcrole`) |
| 41. | 03 March 2005 | [**Section 4.10**](#_4.10) | `  <usedOn>  ` needs its own definition of " [S-Equal](#s-equal) " since it cannot delegate the semantics to "x‑equal" |
| 42. | 03 March 2005 | [**Section 5.1**](#_5.1) | Clarify the need to import xbrl‑instance‑2003‑12‑31 as being a consequence of http://www.w3.org/TR/xmlschema-1/#src-resolve |
| 43. | 03 March 2005 | [**Section 4.9**](#_4.9) | The case for ` @id` on `tuples` was overstated in the associated non-normative note. Clarification. |
| 44. | 17 March 2005 | [**Section 4.9**](#_4.9) | Clarify wording regarding tuple content models. |
| 45. | 17 March 2005 | [**Section 5.1.1.3.1**](#_5.1.1.3.1) | Correct erroneous section reference |
| 46. | 17 March 2005 | [**Section 4.11.1.2**](#_4.11.1.2) | Clarification of wording relating to mixed content in footnote resources |
| 47. | 24 March 2005 | [**Section 4.9**](#_4.9) | Update example 22 pursuant to erratum correction 027 |
| 48. | 27 October 2005 | [**Section 1.6**](#_1.6)   [**Section 3.2**](#_3.2)   [**Section 5.1.2**](#_5.1.2)   [**Section 5.1.3**](#_5.1.3)   [**Section 5.1.4**](#_5.1.4)   [**Section 5.2**](#_5.2) | Correct inconsistent references to `schema/annotation/appinfo/   ` (includes adding entry for use of `xsd:` namespace prefix) |
| 49. | 27 October 2005 | [**Section 5.2.6.2.2**](#_5.2.6.2.2) | Correct definition of "alias item set" to include items in identical contexts, not just [S-Equal](#s-equal) contexts. (A context is not [S-Equal](#s-equal) to itself). |
| 50. | 27 October 2005 | [**Section 4.1**](#_4.1)   [**Section 4.7.3.2**](#_4.7.3.2)   [**Section 4.7.4**](#_4.7.4)   [**Section 4.9**](#_4.9)   [**Section 4.11.1**](#_4.11.1)   [**Section 5.1**](#_5.1)   [**Section 5.1.1**](#_5.1.1)   [**Section 5.1.1.1**](#_5.1.1.1)   [**Section 5.1.1.2**](#_5.1.1.2)   [**Section 5.1.1.3**](#_5.1.1.3)   [**Section 5.2.3.2**](#_5.2.3.2) | Correct errors in (non-normative) examples |
| 51. | 27 October 2005 | [**Section 5.2.5**](#_5.2.5)   [**Section 5.2.5.2**](#_5.2.5.2) | Decouple semantics of the calculation linkbase from that of the `summation-item` arc. |
| 52. | 27 October 2005 | [**Section 5.1.4.3**](#_5.1.4.3) | Undirected cycles definition does not cover all possible cases.  Note that the addition of two examples for this erratum also resulted in the renumbering of all examples from 37 onwards. |
| 53. | 27 October 2005 | [**Section 1.4**](#_1.4) | Mark section 1.4 (Terminology) as non-normative (except where noted otherwise) since formal definitions are provided elsewhere |
| 54. | 27 October 2005 | [**Section 4.9**](#_4.9) | Remove ambiguous and redundant constraint on anonymous type declarations in descendants of tuples. |
| 55. | 27 October 2005 | [**Section 4.9**](#_4.9) | Insert **SHOULD NOT** restriction for local attributes on tuples for consistency with items – enforced by schema for items but not for tuples - [http://groups.yahoo.com/group/XBRL-SpecV2/message/8110](http://groups.yahoo.com/group/XBRL-SpecV2/message/8110) |
| 56. | 27 October 2005 | [**Section 5.2.3.2**](#_5.2.3.2)   [**Appendix A**](#A) | Reference parts should have been based on `anySimpleType` rather than `string - ` [http://groups.yahoo.com/group/XBRL-SpecV2/message/7104](http://groups.yahoo.com/group/XBRL-SpecV2/message/7104) |
| 57. | 27 October 2005 | [**Section 4.10**](#_4.10) | Resolve discrepancy between XML Schema types \[SCHEMA‑1\] and \[XPATH\] types in definition of [X-Equal](#x-equal) |
| 58. | 27 October 2005 | [**Appendix A**](#A)   [**Section 4.6**](#_4.6) | Schema changes to permit attributes from other namespaces to appear on elements in XBRL instances in derived types |
| 59. | 18 December 2006 | [**Section 4.6.4**](#_4.6.4)   [**Section 4.6.7.1**](#_4.6.7.1)   [**Section 4.6.7.2**](#_4.6.7.2) | Clarify wording relating to the definition of decimals and precision, correct some non-normative examples and add additional non-normative clarifying examples. |
| 60. | 18 December 2006 | [**Section 1.7**](#_1.7) | Clarify situation regarding any extensions to this specification not being able to modify anything in this specification |
| 61. | 01 December 2005 | [**Section 3.2**](#_3.2) | Correct omission of `  <linkbaseRef>  ` from certain parts of the [DTS](#DTS) discovery rules |
| 62. | 08 December 2005 | [**Section 4.8.2**](#_4.8.2) | Correct redundant and incorrect definitions and use of `xsd:QName` |
| 63. | 18 December 2006 | [**Section 5.1.1.3**](#_5.1.1.3) | `dateTimeItemType` is derived from `xbrli:dateUnion` – correct wrong information in table 7 |
| 64. | 18 December 2006 | [**Section 4.9**](#_4.9) | Correct example 22 |
| 65. | 18 December 2006 | [**Section 1.4**](#_1.4)   [**Section 3.5.2.4**](#_3.5.2.4)   [**Section 3.5.3.3**](#_3.5.3.3)   [**Section 3.5.3.5**](#_3.5.3.5)   [**Section 3.5.3.8.3**](#_3.5.3.8.3)   [**Section 3.5.3.9.4**](#_3.5.3.9.4)   [**Section 5.1.3**](#_5.1.3)   [**Section 5.1.3.4**](#_5.1.3.4)   [**Section 5.1.4**](#_5.1.4)   [**Section 5.1.4.3**](#_5.1.4.3)   [**Section 5.1.4.5**](#_5.1.4.5) | Clarification of the behaviour of `arcRoleRef`, `  <roleRef>  `, `  <roleType>  `, and `arcRoleType` relative to custom elements such as links, arcs, and resources |
| 66. | 18 December 2006 | [**Section 3.5.2.4**](#_3.5.2.4)   [**Section 3.5.2.4.2**](#_3.5.2.4.2)   [**Section 3.5.2.5**](#_3.5.2.5)   [**Section 3.5.2.5.2**](#_3.5.2.5.2)   [**Section 3.5.3.7.2**](#_3.5.3.7.2) | Clarification of [DTS](#DTS) Discovery in custom linkbases. |
| 67. | 18 December 2006 | [**A.4**](#A.4)   [**A.3**](#A.3)   [**A.2**](#A.2) | Replace XLink schemas with minimal implementation of the W3C namespace schema and necessary changes in dependent schemas to enhance compatibility with other standards employing XLink |
| 68. | 18 December 2006 | [**Section 3.5.2.4**](#_3.5.2.4)   [**Section 3.5.2.5**](#_3.5.2.5)   [**Section 3.5.3.3**](#_3.5.3.3)   [**Section 3.5.3.8.3**](#_3.5.3.8.3)   [**Section 3.5.3.9.4**](#_3.5.3.9.4)   [**Section 5.1.3**](#_5.1.3)   [**Section 5.1.3.4**](#_5.1.3.4)   [**Section 5.1.4**](#_5.1.4) | Remove redundant constraints on arcroles |
| 69. | 23 June 2008 | [**Section 3.5.3.5**](#_3.5.3.5) | Correct hyperlink cross reference |
| 70. | 23 June 2008 | [**Section 5.1.4**](#_5.1.4) | Minor editorial correction to example |
| 71. | 23 June 2008 | [**Section 4.3.3**](#_4.3.3) | Clarification to eliminate possible misinterpretation |
| 72. | 23 June 2008 | [**Section 3.5.3.9.7.4**](#_3.5.3.9.7.4) | Clarification to make explicit that ` @xmlns` attributes are not significant when establishing equivalence of relationships |
| 73. | 23 June 2008 | [**Section 4.10**](#_4.10) | Clarification that a set contains unique members (relevant for equality predicate definitions) |
| 74. | 07 March 2011 | [**Section 4.6.6**](#_4.6.6)   [**Section 4.10**](#_4.10)   [**Section 5.2.5.2**](#_5.2.5.2) | Changed from inferring precision to inferring decimals |
| 75. | 31 October 2011 | [**Section 4.6.7.1**](#_4.6.7.1)   [**Section 4.6.7.2**](#_4.6.7.2) | Changed rounding descriptions to IEEE standard recommendation |
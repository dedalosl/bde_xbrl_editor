---
title: "Generic Labels 1.0"
source: "https://www.xbrl.org/specification/genericlabels/rec-2011-10-24/genericlabels-rec-2011-10-24.html"
author: Phillip Engel, Herm Fischer, Victor Morilla, Jim Richards, Geoff Shuetrim
published: 2011-10-24
created: 2026-04-20
description: >
  Extension to XBRL 2.1 specifying flexible label syntax via generic labels that can
  be associated with any XML element, not limited to XBRL concepts.
tags:
  - "specification"
  - "XBRL"
  - "labels"
  - "generic"
---

# Generic Labels 1.0

## Abstract

This specification extends XBRL 2.1 by defining syntax for labels more flexible than
traditional label link labels. While XBRL label links only label XBRL concepts, generic
labels can associate labels with any XML element.

## Background

XBRL label link labels are limited to concept labeling. They cannot label custom role
declarations, XLink resources from extension specifications, or other non-concept XML
structures. Generic labels overcome this limitation.

## Key Element: `label:label`

A generic label is declared by a `label:label` element — an XLink resource.

- When contained within an XBRL extended link, provides documentation for elements linked
  by element-label relationships
- All generic label resources must have `@xml:lang` identifying the label language
- Language values must conform to XML language identification rules

## Element-Label Relationships

An arcrole relationship between an XML element and a generic label:

- Arcrole value: `http://xbrl.org/arcrole/2008/element-label`
- Starting resource: XML element
- Ending resource: generic label
- Must be expressed by generic arcs (`gen:arc`)
- Undirected cycles are allowed (enables sharing of label resources)

## Standard Resource Role Declarations

- `http://www.xbrl.org/2008/role/label`
- `http://www.xbrl.org/2008/role/verboseLabel`
- `http://www.xbrl.org/2008/role/terseLabel`
- `http://www.xbrl.org/2008/role/documentation`

## Key Namespace

- `label`: `http://xbrl.org/2008/label`
- `xbrlle`: `http://xbrl.org/2008/label/error`

## Dependencies

- XBRL 2.1
- XBRL Generic Links 1.0

## Relationship to Other Specifications

Generic labels use generic links/arcs, making them compatible with:

- [[XBRL Generic Links 1.0]] — Foundation for custom linking
- [[Table Linkbase 1.0]] — Uses generic labels for table/header labeling
- [[XBRL Formula Overview 1.0]] — Uses labels for assertion/formula documentation

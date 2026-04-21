---
title: "Generic References 1.0"
source: "https://www.xbrl.org/specification/genericreferences/rec-2009-06-22/genericreferences-rec-2009-06-22+corrected-errata-2011-03-21.html"
author: Phillip Engel, Herm Fischer, Victor Morilla, Jim Richards, Geoff Shuetrim
published: 2009-06-22
created: 2026-04-20
description: >
  Extension to XBRL 2.1 specifying flexible reference syntax via generic references
  that can be associated with any XML element, not limited to XBRL concepts.
tags:
  - "specification"
  - "XBRL"
  - "references"
  - "generic"
---

# Generic References 1.0

## Abstract

This specification extends XBRL 2.1 by defining syntax for references more flexible
than traditional reference link references. While XBRL reference links only reference
authoritative documentation for concepts, generic references can associate references
with any XML element.

## Background

XBRL reference link references are limited to concept documentation. They cannot reference
custom role declarations, XLink resources from extension specifications, or other
non-concept XML structures. Generic references overcome this limitation.

## Key Element: `reference:reference`

A generic reference is declared by a `reference:reference` element — an XLink resource.

- When contained within an XBRL extended link, identifies documentation for elements
  linked by element-reference relationships
- Contains `link:part` elements for referencing specific parts of documents

## Element-Reference Relationships

An arcrole relationship between an XML element and a generic reference:

- Arcrole value: `http://xbrl.org/arcrole/2008/element-reference`
- Starting resource: XML element
- Ending resource: generic reference
- Must be expressed by generic arcs (`gen:arc`)
- Undirected cycles are allowed (enables sharing of reference resources)

## Standard Resource Role Declarations

- `http://www.xbrl.org/2008/role/reference`

## Key Namespace

- `reference`: `http://xbrl.org/2008/reference`
- `xbrlre`: `http://xbrl.org/2008/reference/error`

## Dependencies

- XBRL 2.1
- XBRL Generic Links 1.0

## Relationship to Other Specifications

Generic references use generic links/arcs, making them compatible with:

- [[XBRL Generic Links 1.0]] — Foundation for custom linking
- [[Generic labels 1.0]] — Complementary label specification
- [[Table Linkbase 1.0]] — Uses generic references for table documentation
- [[XBRL Formula Overview 1.0]] — Uses references for formula documentation

---
title: "XBRL Generic Links 1.0"
source: "https://www.xbrl.org/specification/gnl/rec-2009-06-22/gnl-rec-2009-06-22.html"
author: Mark Goodhand, Ignacio Hernández-Ros, Geoff Shuetrim
published: 2009-06-22
created: 2026-04-20
description: >
  Extension to XBRL 2.1 defining generic extended links and arcs for establishing
  relationships between arbitrary XML elements, not limited to XBRL concepts.
tags:
  - "specification"
  - "XBRL"
  - "linking"
  - "XLink"
---

# XBRL Generic Links 1.0

## Abstract

XBRL taxonomies use XLink to declare relationships supplementing XML Schema information.
XBRL 2.1 defines standard links for concepts (label, reference, calculation, presentation).
This specification extends those capabilities by defining `gen:link` and `gen:arc`
elements capable of establishing relationships between arbitrary XML elements.

## Purpose

Many XBRL extensions need to use XLink power to associate information with, and express
relationships between, XML elements that are not XBRL concepts. This specification defines
concrete linking components and guidance for custom linking constructs.

## Key Elements

### Generic Links (`gen:link`)

An XBRL extended link in the substitution group of `gen:link`. Can be used in any XBRL
linkbase subject to `@xlink:role` restrictions.

- `@xlink:role` must be an absolute URI
- If not the standard link role, the parent `linkbase` must have a `roleRef` declaring it
- The `roleType` must contain a `usedOn` referencing `gen:link`

### Generic Arcs (`gen:arc`)

An XBRL arc in the substitution group of `gen:arc`. Typically appears inside generic links
but may appear elsewhere.

- `@xlink:arcrole` must be an absolute URI
- The parent `linkbase` must have an `arcroleRef` declaring the arcrole
- The `arcroleType` must contain a `usedOn` referencing `gen:arc`
- Cycle constraints from `arcroleType` must be enforced

### Locators in Generic Links

Generic links may contain `link:loc` elements. However, DTS discovery is only defined for
`link:loc` elements — locators using other elements will not trigger DTS discovery.

## Custom Linking Component Guidance

### Custom Extended Links

Only define when tight control over content model is desired. Should be in the substitution
group for `xl:extended`.

### Custom Arcs

Useful when relationships require additional attributes beyond XLink namespace. Must be
in the substitution group for `gen:arc` to be usable within generic links.

### Custom Resources

Common for complex content models, possibly with mixed content. Must be in the substitution
group for `xl:resource`.

## Key Namespace

- `gen`: `http://xbrl.org/2008/generic`
- `xbrlgene`: `http://xbrl.org/2008/generic/error`

## Dependencies

- XBRL 2.1
- XLink

## Relationship to Other Extensions

This specification underpins several other generic extensions:

- [[Generic labels 1.0]] — Generic labels using generic links/arcs
- [[Generic references 1.0]] — Generic references using generic links/arcs
- [[Table Linkbase 1.0]] — Uses generic links for table definitions
- [[XBRL Formula Overview 1.0]] — Uses generic links for formula linkbases

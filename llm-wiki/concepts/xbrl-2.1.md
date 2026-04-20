---
title: "XBRL 2.1"
source: "https://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html"
author: Phillip Engel, Walter Hamscher, Geoffrey Shuetrim, David vun Kannon, Hugh Wallis
published: 2003-12-31
created: 2026-04-20
description: >
  The eXtensible Business Reporting Language 2.1 specification, defining XML elements and
  attributes for business reporting information creation, exchange, and comparison.
tags:
  - "specification"
  - "XBRL"
  - "core"
---

# XBRL 2.1

## Abstract

XBRL is the eXtensible Business Reporting Language. It allows software vendors, programmers,
intermediaries, and end users to enhance the creation, exchange, and comparison of business
reporting information. Business reporting includes financial statements, financial information,
non-financial information, general ledger transactions, and regulatory filings.

## Purpose

The XBRL specification is intended to benefit four categories of users:

1. Business information preparers
2. Intermediaries in the preparation and distribution process
3. Users of this information
4. Vendors who supply software and services to the above groups

Key goals:

- Improve the business report product
- Facilitate current practice without changing accounting standards
- Provide a standard format for preparing, exchanging, extracting, and comparing reports
- Support "drill down" to detailed information
- Support international accounting standards and languages other than English
- Be extensible via incremental extensions

## Framework

XBRL splits business reporting information into two components:

- **XBRL Instances**: contain the facts being reported
- **Taxonomies**: define the concepts being communicated by the facts

The combination of an XBRL instance and its supporting taxonomies and linkbases constitutes
an XBRL business report.

### Discoverable Taxonomy Set (DTS)

A DTS is a collection of taxonomy schemas and linkbases discovered by following links or
references in the taxonomy schemas and linkbases. Discovery rules include:

- Schemas referenced directly from an XBRL Instance via `schemaRef`, `roleRef`, `arcroleRef`, or `linkbaseRef`
- Schemas referenced via XML Schema `import` or `include`
- Schemas referenced by `loc` elements in discovered linkbases
- Linkbases referenced directly from instances via `linkbaseRef`
- Linkbases embedded in discovered taxonomy schemas

### Namespace Prefix Conventions

| Prefix | Namespace |
|---|---|
| `link` | `http://www.xbrl.org/2003/linkbase` |
| `xbrli` | `http://www.xbrl.org/2003/instance` |
| `xl` | `http://www.xbrl.org/2003/XLink` |
| `xlink` | `http://www.w3.org/1999/xlink` |
| `xml` | `http://www.w3.org/XML/1998/namespace` |
| `xsi` | `http://www.w3.org/2001/XMLSchema-instance` |
| `xsd` | `http://www.w3.org/2001/XMLSchema` |

## Key Terminology

- **Concept**: An XML Schema element definition for the `item` or `tuple` substitution group;
  semantically, a definition of a kind of fact.
- **Fact**: Simple facts (items) or compound facts (tuples).
- **Item**: An element in the substitution group for the XBRL item element containing a
  simple fact value with context and unit references.
- **Tuple**: An element in the substitution group for the XBRL tuple element binding
  together parts of a compound fact.
- **Context**: Documents entity, period, and scenario for interpreting item values.
- **Unit**: Documents the unit of measurement for numeric items.
- **Linkbase**: A collection of XLink extended links documenting concept semantics.
- **Extended Link**: Represents relationships between information in extended links and
  third-party documents.
- **Abstract Element**: An element with `@abstract="true"` in its schema declaration,
  cannot be used directly in XML instances.
- **Concrete Element**: An element with `@abstract="false"`, may appear in XML instances.

## Linkbase Types

Five kinds of extended links document concepts:

1. **Definition**: Inter-concept relationships including essence-alias, general-special
2. **Calculation**: Arithmetic summation relationships (summation-item arcs)
3. **Presentation**: Hierarchical organization for display
4. **Label**: Human-readable documentation for concepts
5. **Reference**: Links to authoritative literature

## Conformance Levels

- **Minimally conforming**: Fully implements all syntactic restrictions
- **Fully conforming**: Minimally conforming plus all semantic restrictions relating to
  linkbases and XBRL instances

## Key Changes from XBRL 2.0

- `group` element replaced with `xbrl` root element
- DTS formally defined with discovery rules
- `schemaRef` elements must appear first in instances
- Period duration replaced with `startDate`/`endDate`
- `unit` element separated from context
- `@decimals` attribute added for numeric accuracy documentation
- `@precision` attribute eliminated from context
- `summation-item` arc replaced `parent-child` in calculation extended links
- `general-special` arc replaced `parent-child` in definition extended links
- Cycles prohibited in certain relationship networks

## Relationship to Other Specifications

XBRL 2.1 is the base specification that other XBRL extensions build upon:

- [[XBRL Formula Overview 1.0]] — validation and derived data generation
- [[Table Linkbase 1.0]] — table structure for fact presentation/entry
- [[Table Linkbase Overview 1.0]] — high-level introduction to table linkbase
- [[XBRL Generic Links 1.0]] — custom linking components
- [[Generic labels 1.0]] — flexible label syntax
- [[Generic references 1.0]] — flexible reference syntax

See [[BDE XBRL Editor Overview]] for how this project uses these specifications.

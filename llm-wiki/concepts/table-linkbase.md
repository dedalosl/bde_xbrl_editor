---
title: "Table Linkbase 1.0"
source: "https://www.xbrl.org/Specification/table-linkbase/REC-2014-03-18+errata-2024-12-17/table-linkbase-REC-2014-03-18+corrected-errata-2024-12-17.html"
author: Herm Fischer, Victor Morilla, Jon Siddle
published: 2014-03-18
created: 2026-04-20
description: >
  Normative specification for the Table Linkbase — semantics and syntax constraints for
  XBRL table structures in a Cartesian coordinate system.
tags:
  - "specification"
  - "XBRL"
  - "table"
  - "linkbase"
  - "normative"
---

# Table Linkbase 1.0

## Abstract

This document specifies semantics and syntax constraints for tables. Tables reference
subsets of facts and fact-related information defined by a DTS, and specify their
representation in a Cartesian coordinate system.

## Uses

1. **Data entry** — Entering new facts or editing existing facts in an instance document
2. **Data presentation** — Rendering instance data

## Three Models

### Structural Model

Describes a collection of tables defined in a single linkbase, independent of how they
were defined. Tables are grouped into table sets. The shape of each table is described
in terms of hierarchical breakdowns of fact space.

### Definition Model

A direct representation of the contents of a table linkbase. Syntax-independent,
retaining the same semantics as the table linkbase.

### Layout Model

A direct representation of the structure and values expressed in the final rendered output.
Essentially the structural model with all breakdowns projected onto x, y, or z axis,
populated with values from a fact source.

## Tables

A table represents a breakdown of XBRL fact space for defining a reference view of XBRL data.

- Consists of one or more independent **breakdowns** of fact space
- Each breakdown constrains facts and describes their arrangement in the layout table
- The **domain** of a table is the restricted fact space defined by all constraints
- The **shape** is the arrangement of constraints into breakdown trees

A **closed table** consists only of closed breakdowns.
An **open table** includes at least one open breakdown.

## Table Sets

A table set is a set of one or more tables that share a common definition, parameterised
by table parameters. A single table definition produces a sequence of tables via evaluation
of global parameters in an ordered Cartesian product.

## Breakdowns

A breakdown defines a logically distinct breakdown of fact space by sets of constraints.

- Modeled as an ordered tree of **structural nodes**
- Each node contributes zero or more constraints
- Different constraint sets for the same node must not have the same tag
- All constraint sets for the same node must constrain exactly the same aspects

### Closed vs Open Breakdowns

- **Closed breakdown** — Sequence of constraint sets determined independently of instance facts
- **Open breakdown** — Sequence changes dynamically with facts in the instance

### Roll-up Nodes

A roll-up node is a closed structural node that represents an aggregation of its siblings.
It contributes no additional constraints but reserves a row/column in the rendered table.

## Structural Nodes

Two groups:

- **Closed structural nodes** — Constraints fully determined by definition and DTS
- **Open structural nodes** — Do not fully define aspect value constraints; expand during
  layout based on instance data

## Definition Nodes

Types of definition nodes:

- **Rule nodes** — Express constraints via aspect rules; may be abstract, non-abstract, or merged
- **Concept relationship nodes** — Cover the concept aspect using DTS networks
- **Dimension relationship nodes** — Cover explicit dimension aspects using DRS
- **Aspect nodes** — Open definition nodes; specify aspect with optional filters

## Key Namespace

- `table`: `http://xbrl.org/2014/table`
- `xbrlte`: `http://xbrl.org/2014/table/error`
- `tablemodel`: `http://xbrl.org/2014/table/model`

## BDE Usage Note

BDE uses the PWD (Public Working Draft) version of the Table Linkbase specification,
not the final REC 1.0 version. See [[Table Linkbase Overview 1.0]] for a high-level
introduction.

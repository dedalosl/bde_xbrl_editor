---
title: "Table Linkbase Overview 1.0"
source: "https://www.xbrl.org/wgn/table-linkbase-overview/wgn-2014-03-18/table-linkbase-overview-wgn-2014-03-18.html"
author: Jon Siddle, Herm Fischer, Victor Morilla
published: 2014-03-18
created: 2026-04-20
description: >
  High-level introduction to Table Linkbase — defines table structure for presentation
  and entry of XBRL instance data with multi-axis breakdowns.
tags:
  - "specification"
  - "XBRL"
  - "table"
  - "overview"
---

# Table Linkbase Overview 1.0

## Abstract

The Table Linkbase specification provides a way to define the structure of tables for
presentation and/or entry of XBRL instance data. Facts in XBRL exist in a highly dimensional
space; the table linkbase specifies a projection of these facts onto a table.

## Background

Presentation linkbases (XBRL 2.1) establish relationships between items for presentation
purposes. XBRL Dimensions introduced flexibility but exposed limitations in expressing
presentations of multidimensional models. The Table Linkbase overcomes these limitations
by enabling multi-axis tables.

## Processing Model

Three models and processes transform each into the next:

1. **Definition Model** → (Resolution) → **Structural Model**
2. **Structural Model** → (Layout) → **Layout Model**

### Resolution

Transforms a definition model into a structural model. The DTS may be required (e.g.,
for concept tree traversal). Does not fully resolve instance-dependent definitions.

### Layout

Transforms a structural model into a layout model. Projects breakdowns onto x, y, or z
axis, creates table headers from labels, and populates cells with values from a fact
source (usually an instance).

## Structural Model

Consists of tables within table sets.

- Axes are trees defining constraints on facts
- **Closed nodes** specify constraints for a single column
- **Open nodes** expand during layout to multiple columns based on instance data
- **Roll-up nodes** contain aggregate values (default dimension members)

### Axes

Each axis consists of a series of trees. Each tree defines a logically separate breakdown
of fact space. Breakdowns are projected onto the axis by taking the cross-product of
constraint sets.

### Cells

A cell at the intersection of a row, column, and z-axis point can only be associated
with facts satisfying all three sets of constraints.

### Roll-up

Roll-up columns/rows display aggregate values against the default value for a dimension.
For example, a Geography dimension with default "World" would have roll-up columns
containing totals across all reported regions.

## Layout Model

Contains headers and data appearing in rendered output.

- Each axis header is arranged into header rows/columns of header cells
- Each header cell has a **span** (columns/rows occupied), optional **label**, and a
  **merge** flag
- A **roll-up cell** is semantically part of the cell above it
- Data is specified as a three-dimensional matrix

### Layout Process Steps

1. Expand open nodes
2. Project breakdown trees onto axes (cross-product of constraint sets)
3. Construct table axis headers
4. Populate table cells with matching facts

## Example: Simple Table

A simple table might display concepts in a tree on the y-axis (rows) while the x-axis
breaks down by Product and Geography dimensions. Widget A could be further broken down
by Geography with a roll-up column for all regions.

## Example: Table Sets

A single table definition can resolve to multiple tables with different shapes using
table parameters. A common case is different Extended Link Roles (ELRs) producing
different concept hierarchies on the y-axis while sharing the same x-axis definition.

## Data Entry Support

Table linkbases can be used not only for presenting existing data but also for describing
the shape of forms into which facts may be entered to create new instances. Open tables
with open nodes enable dynamic data entry where rows/columns are created at runtime.

## Relationship to Presentation Linkbase

The Table Linkbase supplements, not replaces, the presentation linkbase. It provides a
standard way to define views that overcome the presentation linkbase's limitations with
multidimensional models.

## See Also

- [[Table Linkbase 1.0]] — Normative specification
- [[XBRL 2.1]] — Base specification
- [[BDE XBRL Editor Overview]] — How the project uses table linkbases

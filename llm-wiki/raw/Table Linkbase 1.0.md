---
title: "Table Linkbase 1.0"
source: "https://www.xbrl.org/Specification/table-linkbase/REC-2014-03-18+errata-2024-12-17/table-linkbase-REC-2014-03-18+corrected-errata-2024-12-17.html"
author:
published: 2014-03-18
created: 2026-04-20
description:
tags:
  - "clippings"
---
Copyright © 2011, 2012, 2013, 2014, 2015, 2018, 2024 XBRL International Inc., All Rights Reserved.

This version:

[<http://www.xbrl.org/Specification/table-linkbase/REC-2014-03-18+errata-2024-12-17/table-linkbase-REC-2014-03-18+corrected-errata-2024-12-17.html>](http://www.xbrl.org/Specification/table-linkbase/REC-2014-03-18+errata-2024-12-17/table-linkbase-REC-2014-03-18+corrected-errata-2024-12-17.html)

Editors:

Herm Fischer, Mark V Systems [<fischer@markv.com>](mailto:fischer@markv.com)

Victor Morilla, Banco de España [<victor.morilla@bde.es>](mailto:victor.morilla@bde.es)

Jon Siddle, CoreFiling [<js@corefiling.com>](mailto:js@corefiling.com)

Contributors:

Geoff Shuetrim, Galexy Pty. [<geoff@galexy.com>](mailto:geoff@galexy.com)

Masatomo Goto, Fujitsu Ltd. [<mg@jp.fujitsu.com>](mailto:mg@jp.fujitsu.com)

Roland Hommes, RHOCON [<roland@rhocon.nl>](mailto:roland@rhocon.nl)

Takahide Muramoto, Fujitsu [<taka.muramoto@jp.fujitsu.com>](mailto:taka.muramoto@jp.fujitsu.com)

David North, CoreFiling [<dtn@corefiling.com>](mailto:dtn@corefiling.com)

Bartosz Ochocki, BRAG [<bartosz.ochocki@br-ag.eu>](mailto:bartosz.ochocki@br-ag.eu)

Shogo Ohyama, Fujitsu Ltd. [<ohyama.shogo@jp.fujitsu.com>](mailto:ohyama.shogo@jp.fujitsu.com)

Joshua Roache, CoreFiling [<jr@corefiling.com>](mailto:jr@corefiling.com)

Hugh Wallis, Standard Dimensions [<hugh@standarddimensions.com>](mailto:hugh@standarddimensions.com)

Paul Warren, XBRL International (formerly CoreFiling) [<pdw@xbrl.org>](mailto:pdw@xbrl.org)

---

## Status

Circulation of this Recommendation is unrestricted. This document is normative. Recipients are invited to submit comments to [rendering-feedback@xbrl.org](mailto:rendering-feedback@xbrl.org), and to submit notification of any relevant patent rights of which they are aware and provide supporting documentation.

## Abstract

This document specifies semantics and syntax constraints for tables. Tables reference subsets of the facts and fact related information defined by a DTS, and specify representation of those facts in a Cartesian coordinate system.

---

## 1 Introduction

This document specifies semantics and syntax constraints for tables. Tables reference subsets of the facts and fact related information defined by a DTS, and specify representation of those facts in a Cartesian coordinate system. A table defines a virtual space which represents an arrangement of facts. Applications may display facts from an existing instance according to this arrangement, or allow entry of new facts according to this arrangement.

All tables defined by this specification can be used for rendering existing instances, and some may be used for the addition or modification of facts to form new instances. This specification does not constrain the details of how these facts are presented or entered.

This specification defines the semantics of the table linkbase. It also describes a syntax that is used to represent these semantics.

Tables use hierarchies to specify the arrangement of XBRL facts. These hierarchies are one of the basic building blocks of the specification, but also constitute by themselves a vehicle to communicate the meaning of those reporting concepts in a similar fashion to that of the presentation linkbase, but enhanced to cover multidimensional information and more complex models.

This specification defines the semantics of tables (and the syntax to define them). It does **NOT** define how tables should be rendered or formatted. References to specific formatting decisions are provided for explanation purposes only, and tools are free to produce any rendering that honours the logical structure of the table(s).

## 1.1 Relationship to other work

This specification depends upon the XBRL Specification [\[XBRL 2.1\]](#XBRL), the XBRL Dimensions Specification [\[DIMENSIONS\]](#DIMENSIONS) and the XBRL Formula Specification [\[FORMULA\]](#FORMULA).

## 1.2 Namespaces and namespace prefixes

Namespace prefixes [\[XML NAMES\]](#XMLNAMES) will be used for elements and attributes in the form `ns:name` where `ns` is the namespace prefix and `name` is the local name. Throughout this specification, the mappings from namespace prefixes to actual namespaces are consistent with [**Table 1**](#table-namespaces).

The prefix column in [**Table 1**](#table-namespaces) is non normative. The namespace URI column is normative.

Table 1: Namespaces and namespace prefixes

| Prefix | Namespace URI |
| --- | --- |
| `table` | `http://xbrl.org/2014/table` |
| `xbrlte` | `http://xbrl.org/2014/table/error` |
| `tablemodel` | `http://xbrl.org/2014/table/model` |
| `eg` | `http://example.com/` |
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
| `gpl` | `http://xbrl.org/2013/preferred-label` |
| `variable` | `http://xbrl.org/2008/variable` |
| `formula` | `http://xbrl.org/2008/formula` |
| `tuple` | `http://xbrl.org/2010/formula/tuple` |
| `df` | `http://xbrl.org/2008/filter/dimension` |

## 1.3 Document conventions (non-normative)

[Documentation conventions](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#sec-document-conventions) follow those set out in the XBRL Variables Specification [\[VARIABLES\]](#VARIABLES).

## 1.4 XPath usage

XPath usage is identical to that in the XBRL Variables Specification [\[VARIABLES\]](#VARIABLES), except that the [context item](http://www.w3.org/TR/xpath20/#dt-context-item) is undefined unless otherwise stated.

Such XPath expressions allowed by this specification are evaluated with no context item to avoid the use of arbitrary XPath expressions which rely heavily on the XML of the instance.

## 2 Uses

This specification defines two significant categories of use:

Data entry is the use of this specification for the purpose of entering new facts or editing existing facts in a (possibly new) instance document.

Data presentation is the use this specification for the purpose of rendering instance data.

Uses that fall outside these definitions are also acceptable.

## 3 Fact source

A fact source is a container for [XBRL facts](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_4.6).

For example, a fact source may be an existing [XBRL instance](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_4) or may consist of new facts created (possibly on-demand) from information entered by the user.

The fact source consists of facts that are to be considered for inclusion in the table. The facts actually included in a table are those facts in the fact source that are in the [domain of the table](#term-domain-of-table).

A [fact source](#term-fact-source) need not have a serialisation. It **MAY** exist only in memory, or be dynamically created on demand. A [fact source](#term-fact-source) **MAY** be modifiable.

## 4 Models

Three models are defined by this specification:

## 5 Structural model

The structural model describes a collection of one or more [tables](#term-table) defined in a single linkbase, in a way that is independent of the way they were defined.

Tables are grouped into [table sets](#term-table-set).

The [shape](#term-shape-of-table) of each table is described in terms of hierarchical [breakdowns](#term-breakdown) of fact space.

[**Figure 1**](#figure-xbrl-structural-model) shows the classes that participate in the structural model.

Figure 1: Structural model

![[structural-model.png]]

## 5.1 Tables

A table represents a breakdown of XBRL fact space for the purpose of defining a reference view of XBRL data.

A table consists of one or more independent [breakdowns](#term-breakdown) of the fact space. Together, these constrain the facts to be included in the table and describe their arrangement in the [layout table](#term-layout-table).

The set of participating aspects for a table is the union of the [participating aspects](#term-participating-aspect) of each of the table's breakdowns.

The domain of a table is the restricted fact space defined by the combination of [constraints](#term-constraint) from all of the table's breakdowns, along with any additional global constraints specified using table filters.

The domain of a table determines which facts are eligible for inclusion in the table.

The shape of the table is the particular arrangement of [constraints](#term-constraint) into the [breakdown](#term-breakdown) trees for the table.

Tables may have a fixed shape, independent of the facts in the [fact source](#term-fact-source). Alternatively, regions of a table may have shapes that vary depending on the facts in the fact source.

A closed table is defined as a table that consists only of [closed breakdowns](#term-closed-breakdown).

An open table is defined as a table whose constituent breakdowns include at least one [open breakdown](#term-open-breakdown).

Each axis consists of a sequence of slices, where a single slice represents a position along that axis. A [slice](#term-slice) along the x-axis is a column. A [slice](#term-slice) along the y-axis is a row.

Any axis without any breakdowns has a single [slice](#term-slice) (e.g. a row or column) along that axis, which contributes no constraints. For example, a table with a single breakdown on the x-axis and no breakdowns on the y-axis will have one row, and a table with a single breakdown on the y-axis and no breakdowns on the x-axis will have one column.

## 5.2 Table sets

A table set is a set of one or more [tables](#term-table) that share a common definition, parameterised by [table parameters](#term-table-parameter).

A single table definition is parameterised by its [table parameters](#term-table-parameter) and produces a single [table set](#term-table-set) that contains a sequence of tables.

A table set corresponds to an ordered Cartesian product of the sequences obtained by evaluating the global parameters associated with the table definition's parameters.

Each item in the ordered Cartesian product represents a set of bindings which bind each table parameter to a single value from the sequence obtained by evaluating the corresponding global parameter. Each of these sets of bindings corresponds to a table.

The ordering of this Cartesian product is derived from the order of the table-parameter relationships and the order of the global parameter evaluated sequences. The Cartesian product is ordered first according to the order of the first sequence then by each of the subsequent sequences in turn.

A table definition model resolves to a sequence of tables in a single table set in the structural model. The tables in a table set vary according to the values assigned to the [table parameters](#term-table-parameter).

## 5.3 Table parameters

A table parameter is a named parameter which binds to an item of the sequence obtained by evaluating a global parameter.

A table parameter is specified by a [parameter](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#term-parameter) declaration that is linked to a table through a [table-parameter relationship](#term-table-parameter-relationship).

For a given table in the structural model, each table parameter binds to an item in the sequence resulting from the evaluation of the global parameter. The value of the table parameter is assigned to a named variable. These variables may be referenced anywhere that the table linkbase syntax allows an XPath expression.

Table parameters allow multiple related tables to be produced from a single table definition, forming a [table set](#term-table-set).

### 5.3.1 Table-parameter relationships

A table-parameter relationship is a [relationship](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9.7.3) which:

- has an extended link name of `  <gen:link>  `
- has an arc name of `  <table:tableParameterArc>  `
- has an [arcrole value](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9) equal to [`http://xbrl.org/arcrole/2014/table-parameter`](#table-parameter)

A [table-parameter-relationship](#term-table-parameter-relationship) **MUST** have a [table:table](#xml-table) resource on its "from" side.

Error code xbrlte:tableParameterSourceError **MUST** be reported if the processing software encounters a table-parameter relationship that does not have a [`  <table:table>  `](#xml-table) resource on its "from" side.

A [table-parameter-relationship](#term-table-parameter-relationship) **MUST** have a parameter declaration on its "to" side.

Error code xbrlte:tableParameterTargetError **MUST** be reported if the processing software encounters a table-parameter relationship that does not have a parameter declaration on its "to" side.

The ` @name` attribute on a table-parameter relationship defines the QName of a variable bound to the value of the [table parameter](#term-table-parameter) for the current table. Within the scope of a single table in a [table set](#term-table-set), XPath variable references with this QName evaluate to the value of the [table parameter](#term-table-parameter) for that table.

If this QName is the same as the QName given in the parameter declaration, XPath variable references with this QName are references to the variable containing the individual parameter value, which overrides the parameter reference.

The value of the ` @name` attribute on a table-parameter relationship **MUST** be unique within the scope of a single table.

Error code xbrlte:tableParameterNameClash **MUST** be reported if the processing software encounters a table-parameter relationship with a value for the ` @name` attribute which is the same as the value of the ` @name` attribute on any other table-parameter relationship for the same table.

## 5.4 Breakdowns

A breakdown defines a logically distinct breakdown of the fact space by sets of [constraints](#term-constraint).

A breakdown is modelled as an ordered tree of [structural nodes](#term-structural-node). Each of these nodes contributes zero or more constraints to the breakdown.

These constraints are grouped into one or more constraint sets, which may each be associated with a tag. There may be at most one constraint set without a tag for a given node. Each type of node in this specification defines the constraint set(s) it contributes.

A node which does not explicitly define any constraint sets is deemed to have a single empty constraint set.

Different constraint sets for the same node **MUST NOT** have the same tag.

Error code xbrlte:duplicateTag **MUST** be reported if the processing software encounters a tag which is used on more than one constraint set for the same node.

All constraint sets for the same node **MUST** consist of constraints for exactly the same aspects.

Error code xbrlte:constraintSetAspectMismatch **MUST** be reported by the processing software for each aspect `A` and each constraint set `S` such that `S` does not constrain `A`, but there exists another distinct set `T` for the same node which does constrain `A`.

Each node may have a number of tag selectors which specify the tags to be selected when determining the combined constraints for a cell as described in [**Section 7.6**](#sec-cell-constraints).

Each leaf node corresponds to a row (or column) in the table and each path through the breakdown tree from root to leaf determines the constraints to be [satisfied](#term-satisfy) by facts in the corresponding row (or column). [**Figure 2**](#structural-model-example-table) illustrates a simple table, in which sales figures (*y* -axis) are broken down by two dimensions: `Product` and `Geography` (*x* -axis). [**Figure 3**](#structural-model-example) shows (part of) the corresponding structural model (the constraints associated with each node are not shown).

Figure 2: Structural model example table

![[structural-model-example-table.png]]

Figure 3: Structural model example

![[structural-model-example.png]]

### 5.4.1 Breakdown labels

A breakdown may have associated labels. Each of these labels applies to the breakdown as a whole.

### 5.4.2 Uniform depth

All leaf nodes in a breakdown are at the same level in the tree. A path from the root node to any leaf node will therefore have the same length.

A tree that has this property is referred to as a uniform depth tree. The process of [height-balancing](#term-height-balancing) ensures that every breakdown consists of a [uniform depth tree](#term-uniform-depth) of nodes.

For example, in [**Figure 3**](#structural-model-example) an additional roll-up node is needed as a child of `widgetB`. This additional node explicitly indicates that the facts in the corresponding column are not further broken down at the next level.

### 5.4.3 Constraints

A constraint is a restriction on the facts eligible for inclusion in a table cell, in terms of their aspect values.

A fact satisfies a constraint if the aspect value specified by the constraint is [equal](#term-aspect-value-equal) to the value of the same aspect for the fact.

Facts must [satisfy](#term-satisfy) all of the combined constraints of the intersecting rows and columns to be rendered or entered in a cell according to the rules laid out in [**Section 7.6**](#sec-cell-constraints).

Each constraint may be tagged to indicate that it only applies in combination with the corresponding [tag selector](#term-tag-selector).

Closed nodes have constraints which restrict an aspect to exactly one aspect value. For example, a closed node may restrict the "Geography" dimension to a single country. There are constructs in the definition model that allow many closed nodes to be defined using a single definition node. For example, it is possible to define a tree of closed nodes, each restricting the "concept" aspect to a different concept, by reference to a presentation network.

Open nodes have constraints which identify a single aspect to be constrained, but the aspect values are not known until layout is performed, and these may be dependent on the facts present.

The aspect values associated with [closed definition nodes](#term-closed-definition-node) can be determined during the [resolution](#term-resolution) process.

The aspect values associated with [open definition nodes](#term-open-definition-node) cannot be determined until [expansion](#term-expansion) occurs as part of the [layout](#term-layout-process) process.

### 5.4.4 QName equality

Two QNames are QName equal if and only if their namespace URIs are equal and their local parts are equal.

### 5.4.5 Aspect value equality

Two aspect values are aspect value equal if they are values for the same aspect and are also equal according to the rules specified for that aspect.

Two aspect values for the concept aspect are equal if the QNames of the concepts they identify are [equal](#term-qname-equal).

Two aspect values for the period aspect are equal if the period values are equal [as defined in XBRL 2.1](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_4.10).

Two aspect values for the unit aspect are equal if the unit values are equal [as defined in XBRL 2.1](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_4.10).

Two aspect values for the entity identifier aspect are equal if the entity identifier values are equal [as defined in XBRL 2.1](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_4.10).

Two aspect values for the same explicit dimension aspect are equal if the the QNames of the members they identify are [equal](#term-qname-equal).

Two aspect values for the same typed dimension aspect are equal if they have [corresponding typed dimension values](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#sec-default-typed-dimension-aspect-tests). Note that custom typed-dimension aspect tests are not used by this specification.

Two aspect values for the non-XDT segment aspect are equal if the `xfi:nodes-correspond` XPath function would deem them to be. The aspect value for the non-XDT segment aspect is the (potentially empty) ordered sequence of child elements of the segment element which do not report values for XBRL dimensions. The analogous equivalence and definition hold for the non-XDT scenario aspect.

### 5.4.6 Participating aspects

An aspect which is identified by a structural node is a participating aspect.

The participating aspects of a breakdown are the [participating aspects](#term-participating-aspect) of the structural nodes in the breakdown.

The aspects participating in a breakdown can always be determined during the [resolution](#term-resolution) process, which does not require an instance.

### 5.4.7 Restrictions on aspect constraints

The [aspect model](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#term-aspect-model) of the table is the [dimensional aspect model](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#term-dimensional-aspect-model) .

A table **MUST NOT** contain more than one breakdown that addresses the same aspect.

Error code xbrlte:aspectClashBetweenBreakdowns **MUST** be reported if the processing software encounters two or more breakdowns in a table that address the same aspect.

Each leaf node in a breakdown **MUST** have an associated aspect value per constraint set for all aspects in that breakdown. For a given aspect, the leaf node itself or one of its ancestors may explicitly define a value for that aspect. Where neither the leaf node itself nor any ancestor explicitly specifies an aspect value for some aspect participating elsewhere in the same breakdown, the following rules apply:

- For explicit and typed dimensional aspects, the absence of a reported value for that dimension is inferred. For explicit dimensions with a default, this is equivalent to constraining to that default.
- For non-dimensional aspects, the absence of such a constraint is an error.

For example, the two nodes in [**Figure 3**](#structural-model-example) with `rollup` = `true` constrain the `Geography` dimension to its default value.

Error code xbrlte:missingAspectValue **MUST** be reported if the processing software encounters a leaf node in a breakdown which does not specify or inherit a value for any non-dimensional aspect which participates elsewhere in that breakdown.

### 5.4.8 Combining breakdowns

Breakdowns are combined by taking the Cartesian product of the individual lists of constraints.

For a single breakdown in isolation, the leaf nodes of the breakdown tree each correspond to a single [slice](#term-slice) (e.g. a row or column) in the layout table. Branch nodes correspond to headers in the layout table that span the headers corresponding to the descendant nodes.

Every breakdown is associated with one of the [axes](#term-axis) defined by the layout model. Several breakdowns may be projected onto a single axis in the layout table, as described in [**Section 9.3.2**](#sec-layout-projection). Interactive tools **MAY** provide a mechanism to allow the user to pivot the table by moving breakdowns between axes and re-ordering breakdowns on the same axis.

### 5.4.9 Closed breakdowns

A closed breakdown is defined as a [breakdown](#term-breakdown) whose sequence of [constraint sets](#term-constraint-set) can be determined independently of the facts to be included.

A closed breakdown cannot directly depend on an instance. However, a closed breakdown may depend on parameters. An application can always provide values for these parameters to satisfy this dependency. The expression for the default value for such a parameter may refer to the content of the instance document, and an application can evaluate this expression against the fact source if it is an instance document.

### 5.4.10 Open breakdowns

An open breakdown is defined as a [breakdown](#term-breakdown) whose sequence of [constraint sets](#term-constraint-set) changes dynamically with the facts included and thus cannot be completely determined without knowledge of those facts.

An example of an open breakdown is one that breaks down facts by period. For [presentation of existing data](#term-data-presentation), this requires a slice (e.g. row or column) for each period against which a fact is reported. For [data entry](#term-data-entry), it requires the ability to dynamically create and populate new slices as the user enters data.

A tool that supports data entry into [open tables](#term-open-table) **SHOULD** provide a method for the user to create new rows or columns in dynamic regions of the table and to specify the necessary aspect values.

## 5.5 Structural nodes

A structural node is a node in a breakdown tree. Each node contributes zero or more [constraints](#term-constraint) to the breakdown.

A structural node may contribute no constraints, in which case it exists solely to group together its children (possibly contributing a header to the table axes; see [**Section 5.5.4**](#sec-structural-node-labels)).

Structural nodes can be classified into two groups: [open structural nodes](#term-open-structural-node) and [closed structural nodes](#term-closed-structural-node).

### 5.5.1 Closed structural nodes

A closed structural node is a structural node with constraints fully determined by its definition and the DTS.

A [closed structural node](#term-closed-structural-node) does not depend on the facts in the instance to determine its constraints.

A closed structural node has been fully resolved during resolution, and is not further expanded during layout.

A breakdown that consists only of closed structural nodes is, by definition, a [closed breakdown](#term-closed-breakdown).

[Closed structural nodes](#term-closed-structural-node) can be [roll-up nodes](#term-roll-up-node).

### 5.5.2 Open structural nodes

An open structural node is a structural node that does not fully define aspect value constraints and does not necessarily have a one-to-one relationship with layout nodes produced during [resolution](#term-resolution).

An [open structural node](#term-open-structural-node) has exactly one [participating aspect](#term-participating-aspect).

During resolution, an open structural node is [expanded](#term-expansion) to a number of layout nodes.

The ordering of layout nodes produced during this expansion is implementation-defined.

An open structural node semantically represents a set of values for a given aspect. For example, an open structural node may represent "all periods used in the fact source". For data presentation, the contexts are required in order to enumerate the periods which will ultimately determine the number of slices (e.g. rows or columns). For data entry, the open node acts as a placeholder for the periods period entered into the application. The application **MAY** expand this placeholder according to the values already entered and **MAY** display a placeholder directly, possibly using it to accept new data.

A breakdown that contains at least one open structural node is, by definition, an [open breakdown](#term-open-breakdown).

### 5.5.3 Roll-up nodes

A roll-up node is a closed structural node which represents an aggregation of its siblings.

A roll-up node contributes no additional constraints to a breakdown. It is always the first or last child of its parent, but is not otherwise different from its non-roll-up equivalent.

A processor **MAY** choose to merge the header cell corresponding to a roll-up node with its parent when rendering the table.

### 5.5.4 Structural node labels

A closed structural node may be associated with one or more labels, as described in [**Section 6.10**](#sec-labels), for the purpose of labelling the header cells it contributes to the layout table. Every header cell corresponding to a given structural node shares the same labels. Open structural nodes do not have labels. The labelling of header cells is described in [**Section 7.4**](#sec-header-cell-labels).

For any node which has no labels, processors are free to choose labels corresponding to that node's constraints. For a node with a single concept or explicit dimensional member that has not been inferred according to [**Section 5.4.7**](#sec-aspect-constraints), processors **SHOULD** use one or more labels associated with the concept in the DTS. Processors **SHOULD NOT** add labels for any constraints inferred according to [**Section 5.4.7**](#sec-aspect-constraints).

Any labels which are not explicitly attached to a definition node, which are attached to a structural node by a processor **MUST** be indicated as coming from the processor. In the layout model serialisation, the "processor" value for the @source attribute is used.

It is desirable to allow the application to use existing labels corresponding to the node's constraints where possible. Where an appropriate label already exists in the DTS, an explicit label is **NOT RECOMMENDED**.

## 5.6 Path labels

The path label of a given resource role for a leaf node in a breakdown is the sequence of node labels of that same resource role associated with the nodes in the path from the root of the breakdown to the leaf.

## 5.7 Slice labels

The slice label of a given resource role for a [slice](#term-slice) (e.g. a row or column) is the sequence formed from the concatenation of the path labels of that same resource role for the slice.

The path labels for a slice are the path labels of the leaf node which aligns with the slice, in each of the breakdowns on the axis.

The order of the concatenation is the order defined by the breakdowns by the table linkbase.

If an application allows breakdowns to be reordered within an axis or pivoted between axes, it **MUST** use the original order and axis when determining slice labels.

## 5.8 Cell labels

The cell label of a given resource role for a cell is a map from each axis to the slice label of that same resource role for the slice which aligns with the cell on that axis.

## 5.9 Unspecified aspects

The concept aspect **MUST** [participate](#term-participating-aspect) in the table.

Error code xbrlte:tableMissingConceptAspect **MUST** be reported if the processing software encounters a table in which the concept aspect does not participate.

The absence of any other aspect has no effect on the structural model. See also [**Section 9.3.1**](#sec-processing-layout-underspecified).

## 6 Definition model

The definition model is a direct representation of the contents of a table linkbase. The syntax of the linkbase provides a direct description of the definition model.

A table linkbase **MUST** consist of one or more valid [generic links](http://www.xbrl.org/Specification/gnl/REC-2009-06-22/gnl-REC-2009-06-22.html#term-generic-link). Violations of this requirement **MUST** be detected by validation against the Generic Links Specification [\[GENERIC LINKS\]](#GENERIC) and the XBRL Specification [\[XBRL 2.1\]](#XBRL).

[**Figure 4**](#figure-xbrl-definition-model) illustrates the definition model.

Figure 4: Definition model

![[definition-model.png]]

## 6.1 Tables

A table is defined by a [`  <table:table>  `](#xml-table) resource with at least one [table-breakdown relationship](#term-table-breakdown-relationship). A [`  <table:table>  `](#xml-table) without any such relationships has no meaning within the scope of this specification.

The [`  <table:table>  `](#xml-table) element is related to [breakdown definitions](#term-breakdown-definition) which define the shape of the table. It can also be related to filters which restrict the [domain of the table](#term-domain-of-table).

The ` @parentChildOrder` attribute on a table declaration defines the default placement of [roll-up nodes](#term-roll-up-node) contributed by all [closed definition nodes](#term-closed-definition-node) in the table for which it is not overridden, as described in [**Section 6.5.3.1**](#sec-parent-child-ordering).

A single table definition potentially defines multiple tables in the structural model. All tables in the structural model resulting from a single definition are grouped into a [table set](#term-table-set).

### 6.1.1 Table labels

Tables **MAY** be associated with [generic labels](http://www.xbrl.org/Specification/genericLabels/REC-2009-06-22/genericLabels-REC-2009-06-22.html#term-generic-label) and [generic references](http://www.xbrl.org/Specification/genericReferences/REC-2009-06-22/genericReferences-REC-2009-06-22.html#term-generic-reference), as described in [**Section 6.10**](#sec-labels). These labels apply to every table in a [table set](#term-table-set).

## 6.2 Table filters

Tables may be associated with [filters](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#sec-filters) through [table-filter relationships](#term-table-filter-relationship).

The context item for XPath expressions of table filters is each candidate fact being considered to meet the conditions that would make it an accepted member of the domain of the table.

### 6.2.1 Table-filter relationships

A table-filter relationship is a [relationship](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9.7.3) which:

- has an extended link name of `  <gen:link>  `
- has an arc name of `  <table:tableFilterArc>  `
- has an [arcrole value](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9) equal to [`http://xbrl.org/arcrole/2014/table-filter`](#table-filter)

A [table-filter-relationship](#term-table-filter-relationship) **MUST** have a [table:table](#xml-table) resource on its "from" side.

Error code xbrlte:tableFilterSourceError **MUST** be reported if the processing software encounters a table-filter relationship that does not have a [`  <table:table>  `](#xml-table) resource on its "from" side.

A [table-filter-relationship](#term-table-filter-relationship) **MUST** have a filter on its "to" side.

Error code xbrlte:tableFilterTargetError **MUST** be reported if the processing software encounters a table-filter relationship that does not have a filter on its "to" side.

The ` @complement` attribute on a table-filter relationship indicates whether the filter's effect is inverted. The default value is ` @complement` = `false`. A table-filter where the ` @complement` attribute has a value of `true` uses the [filter complement](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#term-filter-complement) rather than the filter itself.

## 6.3 Axes

The axes of a table are defined by [breakdown definitions](#term-breakdown-definition).

## 6.4 Breakdowns

Breakdown definitions define [breakdowns](#term-breakdown) using trees of [definition nodes](#term-definition-node). Breakdown definitions may also have generic labels. These label the breakdown as a whole.

A [breakdown definition](#term-breakdown-definition) is represented by a [`  <table:breakdown>  `](#xml-breakdown) resource.

The [`  <table:breakdown>  `](#xml-breakdown) resource is related to trees of definition nodes which define the shape of the breakdown.

The ` @parentChildOrder` attribute on a breakdown defines the default placement of [roll-up nodes](#term-roll-up-node) contributed by all [closed definition nodes](#term-closed-definition-node) in the breakdown (as described in [**Section 6.5.3.1**](#sec-parent-child-ordering)) and overrides the value inherited from the table.

### 6.4.1 Table-breakdown relationships

A table-breakdown relationship is a [relationship](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9.7.3) which:

- has an extended link name of `  <gen:link>  `
- has an arc name of `  <table:tableBreakdownArc>  `
- has an [arcrole value](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9) equal to [`http://xbrl.org/arcrole/2014/table-breakdown`](#table-breakdown)

A [table-breakdown-relationship](#term-table-breakdown-relationship) **MUST** have a [table:table](#xml-table) resource on its "from" side.

Error code xbrlte:tableBreakdownSourceError **MUST** be reported if the processing software encounters a table-breakdown relationship that does not have a [`  <table:table>  `](#xml-table) resource on its "from" side.

A [table-breakdown-relationship](#term-table-breakdown-relationship) **MUST** have a [`  <table:breakdown>  `](#xml-breakdown) resource on its "to" side.

Error code xbrlte:tableBreakdownTargetError **MUST** be reported if the processing software encounters a table-breakdown relationship that does not have a [`  <table:breakdown>  `](#xml-breakdown) resource on its "to" side.

The ordering of [breakdowns](#term-breakdown) is the order of the table-breakdown relationships, as defined by their [order attributes](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9). Where no order attribute is specified on a relationship, or if two relationships have identical order attributes, the relative ordering is implementation-defined. However, it **MUST** be deterministic. Ordering of breakdowns is only significant for relationships that have the same value for their ` @axis` attribute.

### 6.4.2 Breakdown labels

Breakdowns **MAY** be associated with [generic labels](http://www.xbrl.org/Specification/genericLabels/REC-2009-06-22/genericLabels-REC-2009-06-22.html#term-generic-label) and [generic references](http://www.xbrl.org/Specification/genericReferences/REC-2009-06-22/genericReferences-REC-2009-06-22.html#term-generic-reference), as described in [**Section 6.10**](#sec-labels). These labels provide an overall description of content of the breakdown.

## 6.5 Definition nodes

A definition node is a definition of zero or more [structural nodes](#term-structural-node) in the structural model.

Definition nodes are represented by elements in the substitution group for the abstract [`  <table:definitionNode>  `](#xml-abstract-definition-node) element. The following types of [definition node](#term-definition-node) are defined by this specification:

- [Rule nodes](#term-rule-node)
- [Concept relationship nodes](#term-concept-relationship-node)
- [Dimension relationship nodes](#term-dimension-relationship-node)
- [Aspect nodes](#term-aspect-node)

This section specifies syntax and semantics common to all types of definition node.

Definition nodes contribute nodes to the structural model through the [resolution process](#term-resolution) (described in [**Section 9.2**](#sec-processing-resolution)). The specific contribution to the structural model depends on the type of definition node, and is described in the corresponding section for a given type of definition node.

Definition nodes and the structural nodes they contribute are classified as either "closed" or "open".

Definition nodes can include a [tag selector](#term-tag-selector) using the ` @tagSelector` attribute. Specific types of definition node define override the value of this attribute (for example concept relationship nodes). Except where this value is overriden, all structural nodes defined by a single definition node share this tag selector value.

### 6.5.1 Extension

Definition nodes **MAY** be extended using qualified attributes in other namespaces. Any such attributes **MUST NOT** affect the meaning of anything defined by this specification.

### 6.5.2 Labelling

The following types of definition node **MUST NOT** have labels:

- Merged rule nodes
- Relationship nodes
- Aspect nodes

Error code xbrlte:invalidUseOfLabel **MUST** be reported if the processing software encounters a definition node of any of the above types which has one or more labels.

### 6.5.3 Closed definition node

A closed definition node is a definition node which resolves to one or more [closed structural nodes](#term-closed-structural-node) .

The figure below provides a model of the closed definition nodes.

Figure 5: Closed definition node model

![[closed-definition-node-model.png]]

[Closed definition nodes](#term-closed-definition-node) define trees of [structural nodes](#term-closed-structural-node).

There are three types of [closed definition nodes](#term-closed-definition-node) defined by this specification:

Those which resolve to a single [structural node](#term-closed-structural-node), or two structural nodes where one is a [roll-up node](#term-roll-up-node) and is a child of the other. This type of definition node may have children. Given such a definition node `D` which resolves to structural node `S` (where `S` is either the single contributed node, or the parent node if two nodes are contributed), any of the top-level structural nodes contributed by children of `D` are children of `S`.

Those which resolve to a tree of [structural nodes](#term-closed-structural-node) and may depend on the DTS. For example, a single closed definition node may resolve to a tree of structural nodes representing a concept tree. This type of definition node cannot have children.

Those which exist to group other closed definition nodes and contain common properties to be contributed to their children.

A [closed definition node](#term-closed-definition-node) which does not contribute common properties to its children **MUST** contribute at least one structural node to the table.

Error code xbrlte:closedDefinitionNodeZeroCardinality **MUST** be reported if the processing software encounters a closed definition node which does not contribute common properties to its children and does not contribute at least one structural node to the table.

A [closed definition node](#term-closed-definition-node) is instance-independent, and can therefore be used to define a table which can be used for both [data entry](#term-data-entry) and [data presentation](#term-data-presentation).

#### 6.5.3.1 Parent-child ordering

Wherever a definition node contributes a [roll-up node](#term-roll-up-node), the position of the roll-up node relative to its siblings is determined by the effective value of the ` @parentChildOrder` attribute on the contributing definition node, which can take either of two values:

- `parent-first`: the roll-up node **MUST** be laid out as the first child of its parent node. This is the default value.
- `children-first`: the roll-up node **MUST** be laid out as the last child of its parent node.

The ` @parentChildOrder` attribute may be specified on a [`  <table:table>  `](#xml-table) element, a [`  <table:breakdown>  `](#xml-breakdown) element, or any element in the [`  <table:closedDefinitionNode>  `](#xml-abstract-closed-definition-node) substitution group.

The effective value of the ` @parentChildOrder` attribute on a [closed definition node](#term-closed-definition-node) is inherited by all [children](#term-children) of that node that do not explicitly specify a different value. [Closed definition nodes](#term-closed-definition-node) at the root of a [breakdown definition](#term-breakdown-definition) inherit the effective value of the ` @parentChildOrder` attribute of the [`  <table:breakdown>  `](#xml-breakdown) element (which may in turn have inherited it from the [`  <table:table>  `](#xml-table) element) as the default value of their ` @parentChildOrder` attribute.

### 6.5.4 Open definition node

An open definition node is a definition node which resolves to an [open structural node](#term-open-structural-node).

A table with one or more [open definition nodes](#term-open-definition-node) defines an [open table](#term-open-table).

[Aspect nodes](#term-aspect-node) are examples of open definition nodes.

### 6.5.5 Breakdown-tree relationships

A breakdown-tree relationship is a [relationship](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9.7.3) which:

- has an extended link name of `  <gen:link>  `
- has an arc name of `  <table:breakdownTreeArc>  `
- has an [arcrole value](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9) equal to [`http://xbrl.org/arcrole/2014/breakdown-tree`](#breakdown-tree)

A [breakdown-tree-relationship](#term-breakdown-tree-relationship) **MUST** have a [table:breakdown](#xml-breakdown) resource on its "from" side.

Error code xbrlte:breakdownTreeSourceError **MUST** be reported if the processing software encounters a breakdown-tree relationship that does not have a [`  <table:breakdown>  `](#xml-breakdown) resource on its "from" side.

A [breakdown-tree-relationship](#term-breakdown-tree-relationship) **MUST** have a definition node on its "to" side.

Error code xbrlte:breakdownTreeTargetError **MUST** be reported if the processing software encounters a breakdown-tree relationship that does not have a definition node on its "to" side.

A breakdown may be on the "from" side of more than one [breakdown-tree relationship](#term-breakdown-tree-relationship). The ordering of the individual breakdown trees is the order of the breakdown-tree relationships, as defined by their [order attributes](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9). Where no order attribute is specified on a relationship, or if two relationships have identical order attributes, the relative ordering is implementation-defined. However, it **MUST** be deterministic.

### 6.5.6 Definition-node-subtree relationships

A definition-node-subtree relationship is a [relationship](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9.7.3) which:

- has an extended link name of `  <gen:link>  `
- has an arc name of `  <table:definitionNodeSubtreeArc>  `
- has an [arcrole value](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9) equal to [`http://xbrl.org/arcrole/2014/definition-node-subtree`](#definition-node-subtree)

A [definition-node-subtree-relationship](#term-definition-node-subtree-relationship) **MUST** have a resource derived from the [table:definitionNode](#xml-abstract-definition-node) type on its "from" side.

Error code xbrlte:definitionNodeSubtreeSourceError **MUST** be reported if the processing software encounters a definition-node-subtree relationship that does not have a resource derived from the [table:definitionNode](#xml-abstract-definition-node) type on its "from" side.

A [definition-node-subtree-relationship](#term-definition-node-subtree-relationship) **MUST** have a resource derived from the [table:definitionNode](#xml-abstract-definition-node) type on its "to" side.

Error code xbrlte:definitionNodeSubtreeTargetError **MUST** be reported if the processing software encounters a definition-node-subtree relationship that does not have a resource derived from the [table:definitionNode](#xml-abstract-definition-node) type on its "to" side.

The base set of a [definition-node-subtree relationship](#term-definition-node-subtree-relationship) **MAY** have undirected cycles but **MUST NOT** have directed cycles.

The children (singular: child) of a definition node `P` are the targets of [definition-node-subtree relationships](#term-definition-node-subtree-relationship) whose source is the [definition node](#term-definition-node) `P`.

The ordering of the [children](#term-children) is the order of the [definition-node-subtree relationships](#term-definition-node-subtree-relationship), as defined by their [order attributes](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9).

The following types of definition node **MUST NOT** have subtrees:

- [Concept relationship nodes](#term-concept-relationship-node)
- [Dimension relationship nodes](#term-dimension-relationship-node)

Error code xbrlte:prohibitedDefinitionNodeSubtreeSourceError **MUST** be reported if the processing software encounters a definition-node-subtree relationship that has a prohibited [definition node](#term-definition-node) at its "from" end.

## 6.6 Rule node

This section specifies semantics and syntax constraints for rule nodes.

The figure below provides a model of the rule node.

Figure 6: Rule node model

![[rule-node-model.png]]

A rule node is a closed definition node that defines a structural node whose aspect constraints are defined by [aspect rules](http://www.xbrl.org/Specification/formula/REC-2009-06-22/formula-REC-2009-06-22.html#sec-aspect-rules). It may define an additional roll-up node which has no aspect constraints.

For example, a rule node may specify that a given [slice](#term-slice) (e.g. a row or column) should be constrained to facts reported against a certain period, or dimension member.

A rule node may be [abstract](#term-abstract), in which case it exists to group [its children](#term-children) and contribute a parent structural node with a common set of constraints.

Alternatively, it may be non-abstract. In which case it also represents an aggregation of [its children](#term-children), and contributes a [roll-up node](#term-roll-up-node) with no constraints to the structural model.

For example, a non-abstract rule node whose [children](#term-children) constrain facts to different members of an explicit dimension will typically have as its own constraint the default member of that dimension. In this case, the constraints specified by the [children](#term-children) take precedence over that of the parent. The roll-up node has no constraint, and so the constraint specified by the parent applies.

A rule node may be [merged](#term-merged) in which case it contributes no structural nodes, but instead contributes its constraints to its children.

### 6.6.1 Rule node aspect rules

A rule node defines zero or more rule sets; sets of [aspect rules](http://www.xbrl.org/Specification/formula/REC-2009-06-22/formula-REC-2009-06-22.html#sec-aspect-rules). Each rule set **MAY** specify a tag. At most one of these rule sets may omit the tag.

Each [rule set](#term-rule-set) contributes a [constraint set](#term-constraint-set) to the corresponding structural node during resolution. If there are no [rule sets](#term-rule-set) in the rule node, a single untagged empty constraint set is contributed.

The constraints of each [constraint set](#term-constraint-set) are defined by the formula [aspect rules](http://www.xbrl.org/Specification/formula/REC-2009-06-22/formula-REC-2009-06-22.html#sec-aspect-rules).

The [Formula specification](http://www.xbrl.org/Specification/formula/REC-2009-06-22/formula-REC-2009-06-22.html) defines [aspect rules](http://www.xbrl.org/Specification/formula/REC-2009-06-22/formula-REC-2009-06-22.html#term-aspect-rule) which specify [output aspects](http://www.xbrl.org/Specification/formula/REC-2009-06-22/formula-REC-2009-06-22.html#term-output-aspect).

This specification reuses this construct, but alters its interpretation in the following ways:

- The aspect values defined as the output aspects (required aspect values) by the Formula specification become the aspect values of the rule node's constraints.
- There is no source aspect value.
- The context item when evaluating any XPath expression is undefined.

Error code xbrlte:incompleteAspectRule **MUST** be reported if the processing software encounters an [aspect rule](http://www.xbrl.org/Specification/formula/REC-2009-06-22/formula-REC-2009-06-22.html#term-aspect-rule) that does not specify an aspect value.

Error code xbrlte:unrecognisedAspectRule **MUST** be reported if the processing software encounters an [aspect rule](http://www.xbrl.org/Specification/formula/REC-2009-06-22/formula-REC-2009-06-22.html#term-aspect-rule) for an aspect which is not part of the dimensional aspect model.

Within the scope of a single [constraint set](#term-constraint-set), there **MUST NOT** be more than one [aspect rule](http://www.xbrl.org/Specification/formula/REC-2009-06-22/formula-REC-2009-06-22.html#term-aspect-rule) for the same [aspect](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#term-aspect).

Error code xbrlte:multipleValuesForAspect **MUST** be reported if the processing software encounters a constraint set which has more than one rule for the same aspect.

Aspect values that use a QName to identify an item declaration (e.g. a concept or dimension member) in the taxonomy **MUST** refer to an existing [domain member declaration](http://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html#term-domain-member-declaration) (as defined by the XBRL Dimensions 1.0 specification [\[DIMENSIONS\]](#DIMENSIONS): an item declaration that is neither a [dimension declaration](http://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html#term-dimension-declaration) nor a [hypercube declaration](http://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html#term-hypercube-declaration)). This requirement does not affect other aspect values, such as units, that involve QNames.

Error code xbrlte:invalidQNameAspectValue **MUST** be reported if the processing software encounters an aspect rule whose value does not refer to an existing domain member declaration.

### 6.6.2 Merged rule nodes

A [merged](#term-merged) rule node indicates additional properties which apply to all of its children. A merged rule node contributes no structural nodes directly, but instead contributes its constraints and its tag selectors to its children (which in turn will contribute structural nodes).

A merged rule node **MUST NOT** have any tagged rule sets. It contributes all of its constraints to every constraint set produced by its children.

Error code xbrlte:mergedRuleNodeWithTaggedRuleSet **MUST** be reported if the processing software encounters a merged rule node with a tagged rule set.

A [merged](#term-merged) rule node **MUST NOT** have any labels, as specified in [**Section 6.5.2**](#sec-definition-node-labelling).

A [merged](#term-merged) rule node **MUST** be abstract. Note that by virtue of the fact that all abstract nodes must have children, so must merged rule nodes.

Error code xbrlte:nonAbstractMergedRuleNode **MUST** be reported if the processing software encounters a non-abstract merged rule node.

### 6.6.3 Rule node syntax

A [rule node](#term-rule-node) is represented by a [`  <table:ruleNode>  `](#xml-rule-node) element with an optional subtree of [children](#term-children).

The ` @abstract` attribute on a [`  <table:ruleNode>  `](#xml-rule-node) element determines whether the node is [abstract](#term-abstract) or not. This has implications for how it [resolves](#term-resolution) (see [**Section 6.6.4**](#sec-rule-node-resolution)). The default value is ` @abstract` = `false`.

An abstract rule node is a [rule node](#term-rule-node) that is represented by a [`  <table:ruleNode>  `](#xml-rule-node) element with ` @abstract` = `true`.

The ` @merge` attribute on a [`  <table:ruleNode>  `](#xml-rule-node) element determines whether the node is [merged](#term-merged) or not. This has implications for how it [resolves](#term-resolution) (see [**Section 6.6.4**](#sec-rule-node-resolution)). The default value is ` @merge` = `false`.

A merged rule node is a [rule node](#term-rule-node) that is represented by a [`  <table:ruleNode>  `](#xml-rule-node) element with ` @merge` = `true`.

A [`  <table:ruleNode>  `](#xml-rule-node) element **MAY** have one or more elements from the `  <formula:aspectRule>  ` substitution group as children of itself, or as children of [`  <table:ruleSet>  `](#xml-rule-set) elements which are children of itself. These are used to specify aspects and aspect constraints for the node.

Each [`  <table:ruleSet>  `](#xml-rule-set) element represents a rule set with the tag specified by the ` @tag` attribute. The children of the [`  <table:ruleSet>  `](#xml-rule-set) element specify constraints in the corresponding constraint set with the same tag value.

The rules which are direct children of the ruleNode form the untagged rule set. These rules specify the constraints in the untagged constraint set.

If there is at least one tagged rule set, and no aspectRule children of the ruleNode, there is no untagged rule set.

If there are no tagged rule sets, and no aspectRule children of the ruleNode, the untagged rule set is empty.

The following `  <formula:aspectRule>  ` features are NOT processed: ` @source` (all rules) and ` @augment` (unit rule).

A [`  <table:ruleNode>  `](#xml-rule-node) **MAY** have `  <formula:aspectRule>  ` elements that have an [XPath expression](http://www.w3.org/TR/xpath20/). The context item when evaluating any XPath expression in such an aspect rule is undefined. XPath expressions **MAY** refer to variables as described in [**Section 6.9**](#sec-variable-references). XPath expressions **SHOULD** be evaluated when constructing the table, but are not expected to be re-evaluated as data is entered (if used for data entry).

Example 1: Rule nodes

| Rule nodes | Explanation |
| --- | --- |
| <table:ruleNode xlink:type="resource" xlink:label="parent" abstract="true"/>     <formula:member>  <formula:qname>eg:Europe</formula:qname>  </formula:member>   <formula:member>  <formula:qname>eg:World</formula:qname>  </formula:member>    <table:definitionNodeSubtreeArc xlink:type="arc" xlink:arcrole="http://xbrl.org/arcrole/2014/definition-node-subtree" xlink:from="parent" xlink:to="child1" order="1"/>  <table:definitionNodeSubtreeArc xlink:type="arc" xlink:arcrole="http://xbrl.org/arcrole/2014/definition-node-subtree" xlink:from="parent" xlink:to="child2" order="2"/> | Defines two columns of a table. The parent rule node is abstract and thus contributes no columns itself. The two child nodes each define a single columns and constrain the value of the `eg:Geography` dimension to `eg:Europe` and `eg:World`, respectively. |
| <formula:member>  <formula:qname>eg:World</formula:qname>  </formula:member>   <formula:member>  <formula:qname>eg:Europe</formula:qname>  </formula:member>    <table:definitionNodeSubtreeArc xlink:type="arc" xlink:arcrole="http://xbrl.org/arcrole/2014/definition-node-subtree" xlink:from="parent" xlink:to="child"/> | Defines two columns with identical constraints to the previous example. The second column is a roll-up contributed by the (non-abstract) parent rule node. The parent node constrains the value of the `eg:Geography` dimension to be `eg:World`, which becomes the effective constraint on the roll-up column. Meanwhile, the single child node that defines the first column specifies a different value, `eg:Europe`, for the `eg:Geography` dimension, which takes precedence over the constraint inherited from the parent node. |
| <table:ruleNode xlink:type="resource" xlink:label="parent" parentChildOrder="children-first"><formula:period>  <formula:instant value="xs:date('2002-01-01')"/>  </formula:period><formula:period>  <formula:instant value="xs:date('2002-12-31')"/>  </formula:period><formula:period>  <formula:duration start="xs:date('2002-01-01')" end="xs:date('2002-12-31')"/>  </formula:period></table:ruleNode> | Defines a column with three alternative constraints for the period aspect. |

### 6.6.4 Rule node resolution

Each non-merged [rule node](#term-rule-node) [resolves](#term-resolution) to either one or two [structural nodes](#term-structural-node), as shown in [**Figure 7**](#figure-abstract-rule-node-resolution) and [**Figure 8**](#figure-non-abstract-rule-node-resolution), respectively.

Merged rule nodes do not resolve directly to any structural nodes, but instead contribute their constraints to their children.

A rule node, `D`, always contributes a single structural node, `S`, as a child of the structural node to which the parent of `D` resolves.

All children of `D` resolve to children of `S`.

The [constraints](#term-constraint) attached to the [structural node](#term-structural-node) `S` are those defined by the [aspect rules](http://www.xbrl.org/Specification/formula/REC-2009-06-22/formula-REC-2009-06-22.html#sec-aspect-rules) attached to [rule node](#term-rule-node) `D`.

If `D` is an [abstract rule node](#term-abstract), it resolves to the single [structural node](#term-closed-structural-node), `S`, as shown in [**Figure 7**](#figure-abstract-rule-node-resolution).

An [abstract rule node](#term-abstract) **MUST** have at least one [child](#term-children).

Error code xbrlte:abstractRuleNodeNoChildren **MUST** be reported if the processing software encounters an abstract rule node with no children.

If `D` is a non- [abstract rule node](#term-abstract) with at least one child, it additionally contributes a single [roll-up node](#term-roll-up-node), `R`, as a child of `S`, as shown in [**Figure 8**](#figure-non-abstract-rule-node-resolution).

Placement of the [roll-up node](#term-roll-up-node) is determined by the effective value of the [rule node](#term-rule-node) 's ` @parentChildOrder` attribute, as described in [**Section 6.5.3.1**](#sec-parent-child-ordering). [**Figure 8**](#figure-non-abstract-rule-node-resolution) shows the children-first case.

Figure 7: Resolution of an abstract rule node

![[rule-node-abstract-example.png]]

Figure 8: Resolution of a non-abstract rule node

![[rule-node-non-abstract-example.png]]

The roll-up node contributes no [constraints](#term-constraint), so the constraints of its ancestors apply.

### 6.6.5 Rule node labels

Rule nodes **MAY** be associated with [generic labels](http://www.xbrl.org/Specification/genericLabels/REC-2009-06-22/genericLabels-REC-2009-06-22.html#term-generic-label) and [generic references](http://www.xbrl.org/Specification/genericReferences/REC-2009-06-22/genericReferences-REC-2009-06-22.html#term-generic-reference), as described in [**Section 6.10**](#sec-labels).

During resolution, these labels are associated with the sole resulting structural node (if there is only one) or the parent structural node (if there are two).

A processor **MAY** add labels to the structural nodes contributed during resolution as described in [**Section 5.5.4**](#sec-structural-node-labels).

## 6.7 Relationship nodes

This section specifies the semantics and syntax for relationship nodes. Relationship nodes provide an implementation of closed definition nodes that resolve into a tree of structural nodes, defined by networks of concepts or explicit dimension members in a DTS.

[**Figure 9**](#figure-relationship-node-model) below provides a model of relationship nodes.

Figure 9: Relationship node model

![[relationship-node-model.png]]

A relationship node is a closed definition node expressed in terms of networks of relationships between concepts. Here the term concept has the general meaning defined by the XBRL 2.1 specification [\[XBRL 2.1\]](#XBRL), not to be confused with the aspect of the same name.

A [relationship node](#term-relationship-node) defines a tree walk of all or part of one or more networks of concepts.

The [tree walk](#term-tree-walk) defined by a [relationship node](#term-relationship-node) unambiguously identifies part of a network.

A relationship node resolves to an ordered tree of structural nodes representing its [tree walk](#term-tree-walk). Each structural node has a single untagged constraint set that constrains the relevant aspect (the concept aspect in the case of a concept relationship node or an explicit dimension aspect in the case of a dimension relationship node) to a single value. The order of sibling nodes is given by the [order of the relationships](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_Ref47265752) by which the concepts or dimension members associated with the nodes were discovered. The ordering between a parent node and its children is defined by the relationship node itself, and is determined by the effective value of the ` @parentChildOrder` attribute, as described in [**Section 6.5.3.1**](#sec-parent-child-ordering).

### 6.7.1 Relationship node syntax

Each concrete type of relationship node defines its own syntax and its own rules for traversing a tree of relationships. This specification defines two types of relationship node: the concept relationship node ( [**Section 6.7.4**](#sec-concept-relationship-node)) and the dimension relationship node ( [**Section 6.7.5**](#sec-dimension-relationship-node)).

A relationship source identifies a starting concept for the [tree walk](#term-tree-walk).

All relationship nodes **MUST** identify at least one [relationship source](#term-relationship-source), either by providing syntax for the source to be explicitly specified by the table linkbase author or by defining a default [relationship source](#term-relationship-source) in case it is not specified. Where more than one [relationship source](#term-relationship-source) is specified, the order in which they are specified is significant and is reflected in the resulting tree of structural nodes. If a [relationship source](#term-relationship-source) is duplicated then the same tree walk is performed once for each duplicate source.

Every relationship node **MUST** specify the basic parameters of its [tree walk](#term-tree-walk), consisting of values for the `formulaAxis` and `generations` properties.

The `formulaAxis` property is an enumeration whose allowed values **MUST** be a subset of the following set: `descendant`, `descendant-or-self`, `child`, `child-or-self`, `sibling`, `sibling-or-self`, `sibling-or-descendant`, `sibling-or-descendant-or-self`. These values have the same meanings as the corresponding values of the [axis](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#term-axis) property of concept relation filters [\[CONCEPT RELATION FILTERS\]](#CONCEPTRELATIONFILTERS) (with the addition of `sibling-or-descendant-or-self` value, which behaves like `sibling-or-descendant` but includes the relationship source and its descendants). The token suffix `-or-self` specifies that the relationship sources are to be included. If the `-or-self` suffix is not present, the top level rendered concepts are the children, parent or siblings of the relationship sources.

Note that the value of the `formulaAxis` property only affects which concepts are included in the [tree walk](#term-tree-walk). It has no effect on the shape of the resulting tree of structural nodes. For example, the siblings of a relationship source are always treated as siblings, even if they are discovered by walking the network from the relationship source.

The `generations` property is a non-negative integer (`xs:nonNegativeInteger`) that limits the [tree walk](#term-tree-walk) to the given number of generations, in the same way as for concept relation filters [\[CONCEPT RELATION FILTERS\]](#CONCEPTRELATIONFILTERS). A value of `generations` = `0` results in an unlimited [tree walk](#term-tree-walk). The relationship sources are not included when calculating the depth of the [tree walk](#term-tree-walk), e.g. a value of `generations` = `1` with `formulaAxis` = `descendant` is equivalent to specifying `formulaAxis` = `child`.

If the value of `formulaAxis` is `child`, `child-or-self`, `sibling` or `sibling-or-self` then the value of `generations` **MUST** be either `0` or `1`.

Error code xbrlte:relationshipNodeTooManyGenerations **MUST** be reported if the processing software encounters a value of `formulaAxis` that implies a single generation tree walk in combination with a value of generations greater than 1.

### 6.7.2 Relationship node expressions

Relationship nodes offer an alternative way to express some properties; using [XPath expressions](http://www.w3.org/TR/xpath20/). The result of evaluating such an XPath expression **MUST** be [castable](http://www.w3.org/TR/xpath20/#id-castable) to the data type of the equivalent non-expression element.

Error code xbrlte:expressionNotCastableToRequiredType **MUST** be raised if an XPath expression is encountered that is not castable to the required type.

XPath expressions used to specify the properties of a relationship node have no context item. They may, however, reference [table parameters](#term-table-parameter) and global parameters defined in the DTS.

### 6.7.3 Relationship node labels

Relationship nodes **MUST NOT** have any labels, as specified in [**Section 6.5.2**](#sec-definition-node-labelling). During resolution, a processor **SHOULD** add labels as described in [**Section 7.4**](#sec-header-cell-labels).

### 6.7.4 Concept relationship node

A concept relationship node is a [relationship node](#term-relationship-node) which describes a tree of values for the concept aspect in terms of a tree walk of a network of concept-concept relationships.

Concept relationship nodes discover concepts by performing a tree walk of an XBRL 2.1 [network](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9.7.3). The tree walk is uniquely identified by the network and one or more [relationship sources](#term-relationship-source). A concept relationship node **MUST** identify a single network. In most cases, the combination of link role and arcrole is sufficient to unambiguously identify the network, but it may be necessary to specify additional information such as the arc name or the name of the extended link.

Error code xbrlte:ambiguousConceptNetwork **MUST** be reported if the processing software encounters a concept relationship node that provides insufficient information to unambiguously identify a single network.

It is not an error for a concept relationship node to specify properties for which there are no matching relationships in the DTS. In this case no relationships are found but the relationship sources themselves are still processed.

The [participating aspect](#term-participating-aspect) of a [concept relationship node](#term-concept-relationship-node) is the concept aspect.

As described in [**Section 6.5.6**](#sec-definition-node-subtree-relationships) concept relationship nodes cannot have subtrees.

#### 6.7.4.1 Concept relationship node syntax

The syntax of concept relationship nodes is defined by the normative schema supplied with this specification.

A concept relationship node **MAY** include any number of `  <table:relationshipSource>  ` or `  <table:relationshipSourceExpression>  ` elements, each containing, respectively, a QName (`xs:QName`) or an XPath expression that evaluates to a QName identifying a single [relationship source](#term-relationship-source) for the [tree walk](#term-tree-walk). If a relationship source is specified, it **MUST** be either:

- the QName of a [concept](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#concept) that exists in the DTS, or
- the special value `xfi:root`.

Error code xbrlte:invalidConceptRelationshipSource **MUST** be reported if the processing software encounters a relationship source that is neither the QName of a concept that exists in the DTS nor the special value `xfi:root`.

The special value `xfi:root` represents a virtual concept that has as its children the root concepts of the specified network. When resolving a concept relationship node with a relationship source of `  <xfi:root>  `, a table linkbase processor **MUST** order the root concepts of the network according to their QNames, as described in [**Section 6.7.4.3**](#sec-network-root-ordering)

If no [relationship source](#term-relationship-source) is specified, the special value `xfi:root` is assumed.

The `  <table:arcrole>  ` or `  <table:arcroleExpression>  ` element is, respectively, a non-empty URI (`xl:nonEmptyURI`) or an expression that evaluates to a non-empty URI. In either case this URI identifies the arcrole of the network(s).

The `  <table:linkrole>  ` or `  <table:linkroleExpression>  ` element is, respectively, a non-empty URI (`xl:nonEmptyURI`) or an expression that evaluates to a non-empty URI. In either case, this URI identifies the link role of the network(s). If no link role is specified, the [standard link role](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.3) is used.

The `  <table:linkname>  ` or `  <table:linknameExpression>  ` element is, respectively, a QName (`xs:QName`) or an XPath expression that evaluates to a QName. It identifies the name of the extended link element defining the network(s).

The `  <table:arcname>  ` or `  <table:arcnameExpression>  ` element is, respectively, a QName (`xs:QName`) or an XPath expression that evaluates to a QName. It identifies the name of the arcs comprising the network(s).

The `  <table:linkname>  ` and `  <table:arcname>  ` elements (and the corresponding expression-based equivalents) are optional and need only be included if necessary to uniquely identify the network.

If no relationships are found in the specified network, only the relationship sources are included in the resulting tree.

If the resulting tree is empty (for example, because the relationship sources themselves are excluded by the choice of `formulaAxis`) then this is an error, as described in [**Section 6.5.3**](#sec-closed-definition-node).

The `  <table:formulaAxis>  ` or `  <table:formulaAxisExpression>  ` element, if present, specifies the value of the `formulaAxis` property, as defined in [**Section 6.7.1**](#sec-relationship-node-syntax). If neither element is present, the value `descendant-or-self` is assumed.

The behaviour of concept relationship nodes with each combination of relationship source and `  <table:formulaAxis>  ` is described in [**Table 2**](#table-concept-relationship-node-behaviour) below.

Table 2: Concept relationship node behaviour

<table><colgroup><col width="20%"> <col width="15%"> <col width="65%"></colgroup><thead><tr><th><code>formulaAxis</code></th><th><code>relationshipSource</code></th><th>Behaviour</th></tr></thead><tbody><tr><td rowspan="2">when the suffix <code>-or-self</code> is present</td><td><code>xfi:root</code></td><td>The root relationships are equivalent to a virtual root source concept that has the root concepts of the network as children.</td></tr><tr><td>present</td><td>The top level rendered relationship is a virtual relationship that has as its child the named relationship source. If the current binding is to a source object, any <code> @name</code> variable does not have a bound relationship object (it is an empty sequence for the source objects).</td></tr><tr><td rowspan="2">when the suffix <code>-or-self</code> is not present</td><td><code>xfi:root</code></td><td>The root relationships are the relationships whose source is a root concept of the network, causing the children of these root concepts to be the top level of rendered concepts.</td></tr><tr><td>present</td><td>The top level rendered relationships are the relationships that have as their parents the named relationship source, causing the children of the relationship source to be the top level of rendered relationships.</td></tr></tbody></table>

The `  <table:generations>  ` or `  <table:generationsExpression>  ` element is, respectively, a non-negative integer or a non-negative integer expression that, if present, specifies the value of the `generations` property, which limits the tree walk to the given number of generations, as described in [**Section 6.7.1**](#sec-relationship-node-syntax). If neither element is present, a value of `0` is assumed.

#### 6.7.4.2 Concept relationship node resolution

Each concept in the [tree walk](#term-tree-walk) resolves to at least one structural node, which both constrains the value of the [concept aspect](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#term-concept-aspect) to that concept and acts as parent to structural nodes for each of that concept's child concepts. Child structural nodes are ordered by the ` @order` attribute of the relationship linking the child concept to its parent concept.

For concepts that are non- [abstract](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#table-terms-definitions) and that are not leaves of the tree walk, an additional child [roll-up node](#term-roll-up-node) is added to reserve a position on the axis for facts reported against the concept. No [roll-up node](#term-roll-up-node) is added for abstract concepts or for concepts that have no child concepts.

Abstract concepts without any non-abstract descendants **SHOULD** be skipped. The resulting tree of structural nodes **SHOULD NOT** contain any leaf nodes with abstract concepts.

#### 6.7.4.3 Ordering of network roots

Because the roots of a network have no incoming relationships (other than the virtual relationships linking them to the `  <xfi:root>  ` virtual concept), their relative ordering is undefined in [\[XBRL 2.1\]](#XBRL).

A concept relationship node may include the root concepts of a network either because a relationship source of `  <xfi:root>  ` was specified, or because one of the network roots was explicitly specified as a relationship source, along with a value of `sibling`, `sibling-or-self`, `sibling-or-descendant` or `sibling-or-descendant-or-self` for the `formulaAxis` property.

When resolving a concept relationship node that includes the root concepts of a network, a table linkbase processor **MUST** order them according to their QNames. QNames are ordered first by namespace then by local name, each using Unicode Codepoint Collation as used by [\[XPATH AND XQUERY FUNCTIONS\]](#XFUNCTIONS).

#### 6.7.4.4 Tag selection

If a [preferred label attribute](#term-preferred-label-attribute) is present on a relationship, this is used to determine the tag selector value as described below. A preferred label attribute is either a ` @preferredLabel` attribute appearing on a `  <link:presentationArc>  ` element, or the ` @gpl:preferredLabel` appearing on any arc.

Error code xbrlte:ambiguousPreferredLabel **MUST** be reported if the processing software encounters a `  <link:presentationArc>  ` during the tree walk which has both the ` @preferredLabel` and ` @gpl:preferredLabel` attributes.

- If the [preferred label attribute](#term-preferred-label-attribute) value is `http://www.xbrl.org/2003/role/periodStartLabel` the tag selector value is table.periodStart.
- If the [preferred label attribute](#term-preferred-label-attribute) value is `http://www.xbrl.org/2003/role/periodEndLabel` the tag selector value is table.periodEnd.
- Otherwise, the tag selector value of the concept relationship node itself is used.

Tag selectors **MUST** only be added for non-abstract concepts. That is:

- for non-abstract concepts at the leaves of the tree walk, the tag selectors are added to the corresponding structural node
- for non-abstract concepts elsewhere in the tree walk, the tag selectors are added to the roll-up nodes produced for these concepts

### 6.7.5 Dimension relationship node

A dimension relationship node is a [relationship node](#term-relationship-node) which describes a tree of explicit dimension members in terms of a tree walk of a [dimensional relationship set](http://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html#term-dimensional-relationship-set) (DRS).

The tree walk of a dimension relationship node is uniquely identified by one or more [relationship sources](#term-relationship-source) and the link role of the outgoing domain-member relationships. Dimension relationship nodes traverse the DRS by following [consecutive relationships](http://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html#term-consecutive-relationships) as defined by the XBRL Dimensions 1.0 Specification [\[DIMENSIONS\]](#DIMENSIONS).

The participating aspect of a [dimension relationship node](#term-dimension-relationship-node) is a single explicit dimension aspect, referred to as the participating dimension.

As described in [**Section 6.5.6**](#sec-definition-node-subtree-relationships) dimension relationship nodes cannot have subtrees.

#### 6.7.5.1 Dimension relationship node syntax

The syntax of dimension relationship nodes is defined by the normative schema supplied with this specification.

The [participating dimension](#term-participating-dimension) of a dimension relationship node is specified by a `  <table:dimension>  ` element which contains a QName (`xs:QName`). The QName **MUST** identify an existing [dimension declaration](http://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html#term-dimension-declaration) in the DTS and the dimension **MUST** be an [explicit dimension](http://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html#term-explicit-dimension).

Error code xbrlte:invalidExplicitDimensionQName **MUST** be reported if the processing software encounters a dimension relationship node that does not refer to an existing dimension declaration or that refers to a dimension declaration that is not an explicit dimension.

A dimension relationship node **MAY** include any number of `  <table:relationshipSource>  ` or `  <table:relationshipSourceExpression>  ` elements, each containing, respectively, a QName (`xs:QName`) or an XPath expression that evaluates to a QName identifying a single [relationship source](#term-relationship-source) for the [tree walk](#term-tree-walk). If a relationship source is specified, it **MUST** identify an existing [domain member declaration](http://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html#term-domain-member-declaration).

Error code xbrlte:invalidDimensionRelationshipSource **MUST** be reported if the processing software encounters a relationship source that does not refer to an existing domain member declaration.

If no [relationship source](#term-relationship-source) is specified, the root members of the [domain](http://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html#term-dimension-domain) of the [participating dimension](#term-participating-dimension) are used as the relationship sources. Specifically, the [relationship sources](#term-relationship-source) are the targets of dimension-domain relationships with the specified link role whose source is the [participating dimension](#term-participating-dimension). Note that the dimension-domain relationships may specify a target role that differs from the specified link role, so that the behaviour is potentially different from the case where the same relationship sources were specified explicitly. See [**Example 2**](#example-dimension-relationship-nodes) for example behaviour.

The `  <table:formulaAxis>  ` or `  <table:formulaAxisExpression>  ` element, if present, specifies the value of the `formulaAxis` property, as defined in [**Section 6.7.1**](#sec-relationship-node-syntax). For dimension relationship nodes, valid values correspond to those for explicit dimension filters [\[DIMENSION FILTERS\]](#DIMENSIONFILTERS): `descendant`, `descendant-or-self`, `child` or `child-or-self`. If neither element is present, the value `descendant-or-self` is assumed.

The behaviour of dimension relationship nodes with each combination of relationship source and `  <table:formulaAxis>  ` is described in [**Table 3**](#table-dimension-relationship-node-behaviour) below.

Table 3: Dimension relationship node behaviour

<table><colgroup><col width="20%"> <col width="15%"> <col width="65%"></colgroup><thead><tr><th><code>formulaAxis</code></th><th><code>relationshipSource</code></th><th>Behaviour</th></tr></thead><tbody><tr><td rowspan="2">when the suffix <code>-or-self</code> is present</td><td>omitted</td><td>The root relationships are the dimension-domain relationships that have the <a href="#term-participating-dimension">participating dimension</a> as the source.</td></tr><tr><td>present</td><td>The top level rendered relationship is a virtual relationship that has as its child the named relationship source. If the current binding is to a source object, any <code> @name</code> variable does not have a bound relationship object (it is an empty sequence for the source objects).</td></tr><tr><td rowspan="2">when the suffix <code>-or-self</code> is not present</td><td>omitted</td><td>The root relationships are the relationships whose source is the target of a dimension-domain relationship which in turn has the <a href="#term-participating-dimension">participating dimension</a> as its source, causing the children of these root members to be the top level of rendered members.</td></tr><tr><td>present</td><td>The top level rendered relationships are the relationships that have as their parents the named relationship source, causing the children of the relationship source to be the top level of rendered relationships.</td></tr></tbody></table>

The `  <table:generations>  ` or `  <table:generationsExpression>  ` element is, respectively, a non-negative integer or a non-negative integer expression (`xs:nonNegativeInteger`) that, if present, specifies the value of the `generations` property, which limits the tree walk to the given number of generations, as described in [**Section 6.7.1**](#sec-relationship-node-syntax). If neither element is present, a value of `0` is assumed.

The `  <table:linkrole>  ` or `  <table:linkroleExpression>  ` element is, respectively, a non-empty URI or an expression (`xl:nonEmptyURI`) that, if present, constrains the network in which the node should begin traversing the DRS. If no linkrole is specified then the [standard link role](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.3) is assumed.

If no relationships are found in the specified network then no error is raised and the resulting tree comprises only the relationship sources. However, if the relationship sources themselves are excluded by the value of the `  <table:formulaAxis>  ` element then the resolved tree is empty, which is an error, as described in [**Section 6.5.3**](#sec-closed-definition-node).

Example 2: Dimension relationship nodes

| Dimension relationship nodes | Explanation |
| --- | --- |
| <table:dimensionRelationshipNode xlink:type="resource" xlink:label="members">  <table:relationshipSource>eg:World</table:relationshipSource>  <table:dimension>eg:Geography</table:dimension>  <table:formulaAxis>descendant-or-self</table:formulaAxis>  </table:dimensionRelationshipNode> | Defines a tree of domain members for the explicit dimension `eg:Geography` with the `eg:World` member as the root. |
| <table:dimensionRelationshipNode xlink:type="resource" xlink:label="members">  <table:dimension>eg:Geography</table:dimension>  <table:formulaAxis>descendant-or-self</table:formulaAxis>  </table:dimensionRelationshipNode> | Defines a tree of domain members for the explicit dimension `eg:Geography` with the root(s) of the dimension's domain as the root.  Assuming that `eg:World` is the root of the domain of `eg:Geography`, the resulting tree is equivalent to the previous example. |
| <table:dimensionRelationshipNode xlink:type="resource" xlink:label="members">  <table:dimension>eg:Geography</table:dimension>  <table:formulaAxis>child</table:formulaAxis>  </table:dimensionRelationshipNode> | Defines a tree of domain members for the explicit dimension `eg:Geography` with a single level consisting of the children of the root(s) of the dimension's domain. |

#### 6.7.5.2 Dimension relationship node resolution

In general, each domain member in the [tree walk](#term-tree-walk) resolves to at least one structural node. This node both constrains the value of the relevant [dimension aspect](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#term-dimension-aspect) to that member and acts as parent to structural nodes for each of that member's child members.

The Dimensions Specification [\[DIMENSIONS\]](#DIMENSIONS) allows certain members of the domain of an explicit dimension to be marked as unusable. Such members exist solely for the purpose of organising the domain into a hierarchy and are not expected to be used as actual values for the dimension. Processors **SHOULD** honour the usability of a domain member as defined by the incoming relationship. For usable members that are not leaves of the tree walk, an additional child [roll-up node](#term-roll-up-node) is added to reserve a position on the axis for facts reported with that dimension value. No [roll-up node](#term-roll-up-node) is added for unusable members or for members that are leaves of the [tree walk](#term-tree-walk).

Unusable members without any usable descendants **SHOULD** be skipped. The resulting tree of structural nodes **SHOULD NOT** contain any leaf nodes with unusable members.

Relationship sources that are specified explicitly are always treated as usable, as there are no incoming relationships from which to determine the usability. If the relationship source is omitted then the usability of the domain roots is determined from the incoming `dimension-domain` relationships.

## 6.8 Aspect node

An aspect node is an open definition node which directly specifies a single [participating aspect](#term-participating-aspect), and optionally a restriction on the facts used during expansion to determine the included values for that aspect.

The figure below provides a model of the aspect node.

Figure 10: Aspect node model

![[filter-node-model.png]]

### 6.8.1 Aspect node aspect constraints

An aspect node has exactly one [participating aspect](#term-participating-aspect), which is specified directly.

An aspect node contributes exactly one untagged constraint set.

Dimensional aspect specifications have an optional ` @includeUnreportedValue` property (which defaults to false) which specifies whether the expansion should include a "no value" placeholder when facts exist which have no value for that aspect.

### 6.8.2 Expansion

During the [expansion](#term-expansion) phase of the layout process, an aspect node expands to one layout node for each distinct value of its participating aspect present in its set of [contributing facts](#term-contributing-facts), plus a single layout node representing the absence of a reported value for the participating aspect if ` @includeUnreportedValue` is `true` and the [contributing facts](#term-contributing-facts) include at least one fact where no value is reported for the participating aspect.

An aspect node can be associated with Formula filters to constrain the [contributing facts](#term-contributing-facts) used for this expansion.

The contributing facts for the aspect node are the facts in the fact source for the table, filtered according to the formula filters associated with the aspect node.

Note that the filters constrain the facts used to determine the aspect values which should be included during expansion, but they do not contribute any constraints to the table.

Example 3: Effect of filtering non-participating aspects

If the facts present in the fact source are as follows:

| Concept Aspect | Period Aspect | Fact Value |
| --- | --- | --- |
| Profit | 2011 | 100 |
| Assets | 2012 | 100 |
| Profit | 2013 | 100 |
| Assets | 2013 | 200 |

Given the following definition of aspect node and associated filter:

<table:aspectNode xlink:type="resource" xlink:label="periodNode" id="periodNode">

<table:periodAspect/>

</table:aspectNode><cf:concept>

<cf:qname>eg:profit</cf:qname>

</cf:concept>

<table:aspectNodeFilterArc xlink:from="periodNode" xlink:to="conceptFilter" xlink:type="arc" xlink:arcrole="http://xbrl.org/arcrole/2014/aspect-node-filter"/>

The resulting table would look like this (assuming a suitable definition of the y-axis with concept as a participating aspect):

|  | 2013 | 2011 |
| --- | --- | --- |
| **Profit** | 100 | 100 |
| **Assets** | 100 | (unreported) |

The filter restricts the contributing facts to those with "profit" as the value for the concept aspect. The period aspect node then expands to a node for each value of the period aspect. There is no fact reported against the "profit" concept for the "2012" period, so only 2011 and 2013 are included. The constraints on the nodes on the x-axis only constrain the period aspect, so the values for the "assets" concept still appear in the final table.

This allows the y-axis to provide constraints for the concept aspect without causing an [xbrlte:aspectClashBetweenBreakdowns](#error-aspect-clash-between-breakdowns).

### 6.8.3 Aspect node labels

Aspect nodes **MUST NOT** have any labels, as specified in [**Section 6.5.2**](#sec-definition-node-labelling). During expansion, a processor **SHOULD** add labels to the layout nodes as described in [**Section 7.4**](#sec-header-cell-labels).

### 6.8.4 Aspect node syntax

An aspect node is represented by a [`  <table:aspectNode>  `](#xml-aspect-node) element with exactly one child element in the `  <table:aspectSpec>  ` substitution group and optionally one or more `  <variable:filter>  ` resources related by [aspect-node-filter relationships](#term-aspect-node-filter-relationship).

The child element in the `  <table:aspectSpec>  ` substitution group specifies the [participating aspect](#term-participating-aspect) of the aspect node.

The `  <table:conceptAspect>  `, `  <table:entityIdentifierAspect>  `, `  <table:periodAspect>  `, `  <table:unitAspect>  ` elements specify the concept, entityIdentifier, period and unit aspects respectively.

The `  <table:dimensionAspect>  ` element specifies a dimensional aspect by the dimension's QName. This **MUST** be the QName of a dimension that exists in the DTS. It has an optional ` @includeUnreportedValue` attribute (which defaults to false) which specifies the includeUnreportedValue property of the aspect node.

Error code xbrlte:invalidDimensionQNameOnAspectNode **MUST** be reported if the processing software encounters a dimensionAspect element that specifies a QName which is not the QName of a dimension that exists in the DTS.

The context item for any XPath expression associated with an aspect node filter is the fact from the fact source being considered for inclusion as a [contributing fact](#term-contributing-facts) for the aspect node.

Filters **MUST** be evaluated when rendering an existing instance. An application supporting data entry **MUST** ensure that the facts entered into cells satisfy the associated filters but **MAY** defer this check until the instance is serialised.

The filters associated with a given cell are:

- the table filters for its table
- the filters attached to aspect nodes which expanded (see [**Section 6.8.2**](#sec-aspect-node-expansion)) into layout nodes which contribute constraints to the cell (see [**Section 7.6**](#sec-cell-constraints))

#### 6.8.4.1 Aspect-node-filter relationships

An aspect-node-filter relationship is a [relationship](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9.7.3) which:

- has an extended link name of `  <gen:link>  `
- has an arc name of `  <table:aspectNodeFilterArc>  `
- has an [arcrole value](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html#_3.5.3.9) equal to [`http://xbrl.org/arcrole/2014/aspect-node-filter`](#aspect-node-filter)

A [aspect-node-filter-relationship](#term-aspect-node-filter-relationship) **MUST** have a [table:aspectNode](#xml-aspect-node) resource on its "from" side.

Error code xbrlte:aspectNodeFilterSourceError **MUST** be reported if the processing software encounters an aspect-node-filter relationship that does not have a [`  <table:aspectNode>  `](#xml-aspect-node) resource on its "from" side.

A [aspect-node-filter-relationship](#term-aspect-node-filter-relationship) **MUST** have a filter on its "to" side.

Error code xbrlte:aspectNodeFilterTargetError **MUST** be reported if the processing software encounters an aspect-node-filter relationship that does not have a filter on its "to" side.

A complemented aspect-node-filter relationship is an aspect-node-filter relationship that is expressed by a relationship with a ` @complement` attribute that has a value of `true`.

An [aspect node](#term-aspect-node) with a [complemented aspect-node-filter](#term-complemented-aspect-node-filter-relationship) relationship to a filter uses the [filter complement](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#term-filter-complement) in its implied XPath expression.

## 6.9 Variable references

XPath expressions in definition nodes may refer to in-scope variables. These consist of the following types of variable:

- Global [parameters](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html#term-parameter) defined anywhere in the DTS.
- Variables bound to the values of [table parameters](#term-table-parameter).

## 6.10 Labels

Elements in the definition model **MAY** be associated with [generic labels](http://www.xbrl.org/Specification/genericLabels/REC-2009-06-22/genericLabels-REC-2009-06-22.html#term-generic-label) or [generic references](http://www.xbrl.org/Specification/genericReferences/REC-2009-06-22/genericReferences-REC-2009-06-22.html#term-generic-reference) for the purpose of labelling the corresponding parts of the rendered table.

Labels are associated with elements by [XLink arcs](http://www.w3.org/TR/xlink/#xlink-arcs) which link the element to:

- a [generic label](http://www.xbrl.org/Specification/genericLabels/REC-2009-06-22/genericLabels-REC-2009-06-22.html#term-generic-label), using the [`http://xbrl.org/arcrole/2008/element-label`](http://www.xbrl.org/Specification/genericLabels/REC-2009-06-22/genericLabels-REC-2009-06-22.html#element-label) arcrole
- a [generic reference](http://www.xbrl.org/Specification/genericReferences/REC-2009-06-22/genericReferences-REC-2009-06-22.html#term-generic-reference), using the [`http://xbrl.org/arcrole/2008/element-reference`](http://www.xbrl.org/Specification/genericReferences/REC-2009-06-22/genericReferences-REC-2009-06-22.html#element-reference) arcrole

An element **MAY** be associated with any number of generic labels and generic references. When more than one label or reference is associated with an element, their order is given by their effective relationships' XLink ` @order` attribute. The relative order of labels **MUST** be preserved in the [structural](#term-structural-model) and [layout](#term-layout-model) models.

## 7 Layout model

The layout model directly represents the layout and content of each table in a [layout](#term-layout-result), where the content of a table includes both data, derived from XBRL facts, and header information documenting the meaning of that data.

The process of producing a [layout](#term-layout-result) from a [structural model](#term-structural-model) is described in [**Section 9.3**](#sec-processing-layout).

## 7.1 Layout tables

A layout table represents an arrangement of selected XBRL facts following a matrix layout in a Cartesian space with *x*, *y* and *z* [axes](#term-axis).

## 7.2 Axes

An axis defines an ordered mapping of XBRL fact space onto a line.

This specification describes three axes: *x*, *y*, and *z*. The following conventions for interpreting the different axes **SHOULD** be followed by rendering software where the output format allows it.

- The *x* -axis **SHOULD** be interpreted as a horizontal arrangement of columns in a table. Columns **MAY** be laid out from left to right, or right to left, according to the language conventions.
- The *y* -axis **SHOULD** be interpreted as a vertical progression of rows in a table. Rows **SHOULD** be laid out from top to bottom.
- The *z* -axis **MAY** be interpreted as multiple two-dimensional tables and **MAY** be laid out on a two-dimensional display by presenting each table in series or by supplying controls for the user to select the data to be presented.

Each position along an [axis](#term-axis), corresponding to a [slice](#term-slice) (e.g. a row or column) in the table, is associated with a set of [constraints](#term-constraint) on the fact space. An [axis](#term-axis) may be composed of multiple independent [breakdowns](#term-breakdown) of the fact space. These are combined by [projecting](#term-projection) them onto the [axis](#term-axis), as described in [**Section 9.3.2**](#sec-layout-projection).

Each one of the possible combinations of constraints along a table's axes, corresponding to a single [cell](#term-cell) in a table, is referred to as a coordinate.

## 7.5 Cells

Cells are located at the intersections of rows and columns and act as containers for XBRL facts.

Each cell contains the facts (if any) that [satisfy](#term-satisfy) all of the constraints associated with the particular row and column at whose intersection they are located, as well as any global constraints associated with the table.

A cell may contain zero or more facts. If more than one fact is associated with a cell then the behaviour is implementation-defined. A tool **MAY** choose to display all or a subset of the values. Alternatively, a tool **MAY** display a visual indication that the cell contains multiple values.

In tools that support [data entry](#term-data-entry), a cell may be editable, to allow a user to enter new facts or to edit existing facts. This specification places no restrictions on how tools present this editing functionality to users.

## 7.6 Cell constraints

The constraints which apply to a given cell are determined as follows:

- The set of constraint-contributing nodes is the set of nodes which align with the cell.
- The [tag selector](#term-tag-selector) set for the cell is the union of the [tag selectors](#term-tag-selector) for each of these nodes.
- Exactly one constraint set from each of these nodes is chosen.
	- For a given node, if a single constraint set is present which is [tagged](#term-tagged-constraint) with any of the [tag selectors](#term-tag-selector) , it is chosen.
		- For a given node, if multiple constraint sets are present which are [tagged](#term-tagged-constraint) with any of the [tag selectors](#term-tag-selector), it is an error.  
		Error code xbrlte:tagSelectorClash **MUST** be reported if the processing software encounters a cell that has aligned nodes with more than one tag selector which match constraint sets of an aligned node for that cell.
		- For a given node with an untagged constraint set, if no constraint sets are present which are [tagged](#term-tagged-constraint) with any of the [tag selectors](#term-tag-selector), the untagged constraint set is chosen.
		- For a given node without an untagged constraint set, if no constraint sets are present which are [tagged](#term-tagged-constraint) with any of the [tag selectors](#term-tag-selector), it is an error.  
		Error code xbrlte:noMatchingConstraintSet **MUST** be reported if the processing software encounters a cell that has an aligned nodes with no matching constraint set.
- Where different aspect values for the same aspect are present in this set, only the aspect value from the node closest to the leaf is used.

The constraints according to the above rules are the combined constraints for the cell. A fact should be included in the cell if and only if all of these combined constraints are [satisfied](#term-satisfy).

## 8 Serialisation

This specification defines a canonical XML serialisation of the layout model. The syntax is defined by the normative schema supplied with this specification (see [**A.2**](#sec-tablemodel-xsd)).

For most of the XML elements in the schema, ordering is significant and corresponds to the order in which the corresponding cells in the table are laid out, as outlined below.

The layout model serialisation is used by the conformance suite to compare layouts produced by tools implementing this specification to those expected from a conformant processor.

## 8.1 Table sets

Each [table set](#term-table-set) is represented by a [`  <tablemodel:tableSet>  `](#xml-rendering-table-set) element, as a child of the root [`  <tablemodel:tableModel>  `](#xml-table-model) element. A serialised layout model may contain any number of table sets.

A [table set](#term-table-set) may be optionally associated with a list of labels, which apply to all the tables in the set (these are the labels attached to the original table in the definition model). These are represented by zero or more [`  <tablemodel:label>  `](#xml-rendering-table-label) elements. The order of the labels is given by the relationships linking them to the original table in the definition model.

Each table set must have at least one child [`  <tablemodel:table>  `](#xml-rendering-table) element.

## 8.2 Tables

A [table](#term-table) is represented by a [`  <tablemodel:table>  `](#xml-rendering-table) element.

A [`  <tablemodel:table>  `](#xml-rendering-table) element must have as its children:

- exactly one [`  <tablemodel:cells>  `](#xml-rendering-table-cells) element describing the contents of the table cells
- one or more [`  <tablemodel:headers>  `](#xml-rendering-table-headers) elements describing the headers for each axis of the table.

## 8.3 Axis headers

The headers for an axis are declared by a [`  <tablemodel:headers>  `](#xml-rendering-table-headers) element.

The required attribute ` @axis` indicates which of the three defined axes a [`  <tablemodel:headers>  `](#xml-rendering-table-headers) element is associated with. Valid values of this attribute are `x`, `y` and `z`. Only one [`  <tablemodel:headers>  `](#xml-rendering-table-headers) element may be associated with each axis for a given table.

Individual headers for an axis are represented by [`  <tablemodel:header>  `](#xml-rendering-table-header) elements, one header for each one for each row (or column) of header cells for a single axis. These are nested inside a [`  <tablemodel:group>  `](#xml-rendering-table-group) element which contains the header elements based on the breakdown they were contributed by. These group and header elements are ordered starting from the outside of the table (i.e. farthest from the data cells) and working inwards. Each [`  <tablemodel:group>  `](#xml-rendering-table-group) element contains a sequence of zero or more [`  <tablemodel:label>  `](#xml-rendering-header-cell-label) elements corresponding to the labels for the breakdown that group is representing, followed by a sequence of zero or more [`  <tablemodel:header>  `](#xml-rendering-table-header) elements.

A [`  <tablemodel:header>  `](#xml-rendering-table-header) element contains a sequence of [`  <tablemodel:cell>  `](#xml-rendering-cell) elements. Each [`  <tablemodel:cell>  `](#xml-rendering-cell) element contains a sequence of [`  <tablemodel:label>  `](#xml-rendering-header-cell-label) elements and a sequence of [`  <tablemodel:constraint>  `](#xml-rendering-header-cell-constraint) elements.

Each [`  <tablemodel:constraint>  `](#xml-rendering-header-cell-constraint) element describes a constraint as an aspect-value pair.

Each [`  <tablemodel:label>  `](#xml-rendering-header-cell-label) element describes the label associated with a single header cell. These are ordered according to the natural direction of ordering in the rendered table.

The ` @source` attribute on the label element indicates where the label originated. If the label was not associated explicitly with a definition node, this attribute **MUST** be provided with a value other than "explicit".

Spanning of multiple rows or columns in the table is indicated in the document by an optional ` @span` attribute on the [`  <tablemodel:cell>  `](#xml-rendering-cell) element. The value of this attribute is a positive integer giving the number of table columns spanned by the header cell. If the attribute is not specified then a span of 1 is assumed. The total number of columns spanned by all the labels on each header row for a given axis should be the same.

Roll-up nodes are indicated by an optional ` @rollup` attribute with a value of `true`.

## 8.4 Table cells

Each cell is represented by a single [`  <tablemodel:cell>  `](#xml-rendering-table-cell) element.

The [`  <tablemodel:cell>  `](#xml-rendering-table-cell) elements are arranged into nested [`  <tablemodel:cells>  `](#xml-rendering-table-cells) elements.

Each [`  <tablemodel:cells>  `](#xml-rendering-table-cells) represents a dimensional slice of the data. The number of dimensions involved in the slice depends on the level of nesting.

A series of [`  <tablemodel:cell>  `](#xml-rendering-table-cell) elements is contained in a [`  <tablemodel:cells>  `](#xml-rendering-table-cells) element, which represents a one dimensional sequence of cells along a single axis, indicated by the ` @axis` attribute on the containing [`  <tablemodel:cells>  `](#xml-rendering-table-cells) element. The position of each cell along the indicated axis is determined by its position within the containing [`  <tablemodel:cells>  `](#xml-rendering-table-cells) element.

The most nested [`  <tablemodel:cells>  `](#xml-rendering-table-cells) elements may each be contained in another [`  <tablemodel:cells>  `](#xml-rendering-table-cells) element, which represents a two dimensional slice of cells along another axis. These in turn may be nested inside a single [`  <tablemodel:cells>  `](#xml-rendering-table-cells) element, representing a three dimensional slice (of which there is only one).

In this way, each level of nesting addresses a more specific part of the data. The position of a child element `C` within a [`  <tablemodel:cells>  `](#xml-rendering-table-cells) element `P` with an ` @axis` attribute value of `A` determines the position along axis `A` of all cells which are descendants of `C` (or `C` itself).

A [`  <tablemodel:cells>  `](#xml-rendering-table-cells) element contains either a sequence of [`  <tablemodel:cell>  `](#xml-rendering-table-cell) elements, or a sequence of nested [`  <tablemodel:cells>  `](#xml-rendering-table-cells) elements. Each [`  <tablemodel:cells>  `](#xml-rendering-table-cells) element must specify (using the required ` @axis` attribute) the axis along which its contained slices or cells are arranged.

The value of the ` @axis` attribute on a [`  <tablemodel:cells>  `](#xml-rendering-table-cells) element must be one of the three axes defined by this specification: `x`, `y` and `z`. All sibling elements must have the same value for the ` @axis` attribute. Elements must never have the same value of the ` @axis` attribute as one of their ancestors.

The content of a [`  <tablemodel:cell>  `](#xml-rendering-table-cell) element describes the content of a single data cell. It consists of a sequence of zero or more [`  <tablemodel:fact>  `](#xml-rendering-table-fact) elements. Each of these contains the URI of a fact which is in the cell. The URI will consist of an instance document location with an [XPointer](http://www.w3.org/TR/xptr-framework/) to the fact within the document.

A `  <tablemodel:cells>  ` element may only be empty if it is the outermost (and only) element for the enclosing table. This indicates that the table contains no cells. Otherwise, it MUST contain either a child `  <tablemodel:cells>  ` element or a non-empty sequence of `  <tablemodel:cell>  ` elements. Note also that the nesting of `  <tablemodel:cells>  ` elements is restricted to defining the axes in a fixed order (z, y, x).

## 9 Processing model

## 9.1 Compilation

Compilation is the process of parsing the table linkbase and producing a [definition model](#term-definition-model).

## 9.2 Resolution

Resolution is the process of building a structural model from the definition model.

The resolution process has the DTS available, but not a fact source (for example, an instance), so that it produces a structural model that is useful both for data entry and data presentation.

### 9.2.1 Table set resolution

A single table definition can define multiple tables in a table set in the structural model, according to the values its parameters can take, as described in [**Section 5.3**](#sec-table-parameters).

Implementations **MAY** provide a series of values for each parameter to produce multiple tables (the table set), or they **MAY** provide a single value for each parameter to produce a single table (this may be seen as "selecting" a table from the table set).

Given a single value for each parameter, a single table in the structural model is produced by resolving the table definition. Resolution of a table definition to a table set for a series of values for its parameters is equivalent to sequentially resolving against a single set of parameter values, for each set of parameter values in the series.

### 9.2.2 Table resolution

The general process of resolving a table definition to a table structure is described here. The individual descriptions of definition node types describe how they contribute to the structural model.

Each breakdown in the definition model is resolved to a breakdown in the structural model by following the resolution rules for each node in the breakdown definition.

The resulting tree of structural nodes is based on the tree of definition nodes. Each node in the definition model resolves to one structural node, a tree of structural nodes or a list of structural nodes.

### 9.2.3 Definition node resolution

For a definition node `D` that resolves into a single structural node `S` or a structural node `S` with a child [roll-up node](#term-roll-up-node) ` R`:

- The parent of `S` is the structural node to which the parent of `D` resolves.
- The children of `S` are the roll-up `R` and the resolved children of `D`.

For a definition node `D` that resolves to a tree of structural nodes, with structural node `S` being the root of this tree:

- The parent of `S` is the structural node to which the parent of `D` resolves. If `D` has no parent, `S` has no parent.
- The non-root structural nodes in the result are arranged as described in the specification of the definition node.

For a definition node `D` that exists to group other definition nodes and contribute common properties to its children:

- The parent of the resolved children `S<sub>1</sub>..S<sub>n</sub>` is the structural node to which the parent of `D` resolves. If `D` has no parent `S<sub>1</sub>..S<sub>n</sub>` have no parent.

Despite representing a number of aspect values, and ultimately a number of columns or rows in the rendered output, open definition nodes resolve to one open structural node since they depend on a fact source (typically an instance). The resulting open structural node represents a part of the table which is dynamic.

### 9.2.4 Height balancing

[Height-balancing](#term-height-balancing) is performed so that there is an unambiguous correspondence between nodes on the same level of the breakdown (and an unambiguous alignment of header cells in the final rendering).

This is particularly important when [projecting](#term-projection) multiple breakdowns onto an axis.

Height-balancing adds a single [roll-up node](#term-roll-up-node) at each level under any leaf nodes up to the required depth.

## 9.3 Layout

The layout process takes the [structural model](#term-structural-model) and a [fact source](#term-fact-source) and produces a [layout](#term-layout-result).

The facts of a table are from the [fact source](#term-fact-source) which **MAY** be an XBRL instance ([data presentation](#term-data-presentation)), or **MAY** be virtual allowing new facts created from information entered into a tool by a user to produce a new or edited output XBRL instance ([data entry](#term-data-entry)). In the latter case, the table provides a description of the facts that may be entered.

The layout process **MAY** be interactive. Examples of interactive layout include allowing the user of a tool to move breakdowns between axes or select the language in which axis headers and text-valued facts are displayed.

A layout is a result of the [layout process](#term-layout-process).

### 9.3.1 Under-specified tables

#### 9.3.1.1 Dimensional aspects

The non-participation of a dimensional aspect implicitly constrains the facts in the table to those which do have no aspect value for that aspect or have the default aspect value for that aspect.

For explicit dimensions with a default, this will have the effect of only including facts for the default member.

For explicit dimensions without a default, and for typed dimensions, this will have the effect of only including facts not reported against that dimension.

#### 9.3.1.2 Non-dimensional aspects

The non-participation of non-dimensional aspects leaves the cells in the table to be unconstrained with respect to those aspects.

The handling of this case is implementation defined, and is described in [**Section 9.3.1.3**](#sec-multiple-values)

#### 9.3.1.3 Multiple values in a cell

Multiple facts may match the constraints for a single [cell](#term-cell). In this case, the behaviour is implementation defined. Applications **MAY** choose to handle this in one of the following ways:

- by displaying the most appropriate fact or facts. For example, locale may be used to select the fact with the most appropriate language or unit.
- by displaying a single fact, where the values are consistent,
- by producing separate instances of the table for each value of an unconstrained aspect. For example, if period is unspecified, it may be desirable to produce a rendered table for each period present in the instance.
- by providing user interface controls for the user to select which facts are displayed. For example, the user may be presented with a choice of entity identifiers present in the instance, and shown a table containing only the facts relating to the selected entity.

### 9.3.2 Projection of multiple breakdowns onto an axis

Multiple breakdowns may be associated with a single table [axis](#term-axis). Breakdowns on an [axis](#term-axis) are ordered according to the ` @order` attributes of the [table-breakdown relationships](#term-table-breakdown-relationship) linking their definitions to that of the table.

Projection is the process of combining two or more independent [breakdowns](#term-breakdown) into a single [effective breakdown](#term-effective-breakdown) for display on a single [axis](#term-axis).

Any additional constraints inferred under [**Section 5.4.7**](#sec-aspect-constraints) are added to the relevant individual breakdown before [projection](#term-projection).

The [effective breakdown](#term-effective-breakdown) for a single breakdown is the breakdown itself.

The effective breakdown for a pair of breakdowns is the tree formed by attaching an identical copy of the second breakdown to each leaf of the first breakdown, such that the root nodes of the second breakdown become the children of the leaves of the first breakdown, as illustrated in [**Figure 11**](#example-cartesian-product).

The [effective breakdown](#term-effective-breakdown) for an ordered set of `n` individual [breakdowns](#term-breakdown) is the effective breakdown for the following pair of breakdowns:

1. the effective breakdown for the first `n-1` individual breakdowns
2. the last individual breakdown

The effective breakdown for an axis is the result of [projecting](#term-projection) all of the individual [breakdowns](#term-breakdown) associated with that [axis](#term-axis).

Figure 11: Projection of two breakdowns onto an axis

![[cartesian-product.png]]

The [projection](#term-projection) in [**Figure 12**](#example-cartesian-product-2) involves a more complex breakdown, that includes two roll-ups (`B` requires padding with an additional [roll-up node](#term-roll-up-node) to bring the first breakdown tree to a [uniform depth](#term-uniform-depth) (see [**Section 5.4**](#sec-structural-breakdowns)), thus ensuring that the individual breakdowns line up correctly in the [effective breakdown](#term-effective-breakdown).

Figure 12: Projection involving a more complicated breakdown

![[cartesian-product-2.png]]

### 9.3.4 Elimination

Elimination is the process of eliminating [unpopulated slices](#term-unpopulated) (e.g. rows and columns) to produce a more compact table.

An unpopulated slice is a [slice](#term-slice) of a table is one whose constraints match no facts when populating the table.

When laying out a table for [data presentation](#term-data-presentation):

- Processors **MUST** be able to produce a complete table in which no slices have been eliminated.
- Processors **MAY** eliminate some or all unpopulated slices.

The conformance suite for this specification expects output tables to have no slices eliminated.

Processors **MUST NOT** perform [elimination](#term-elimination) when laying out a table for [data entry](#term-data-entry).

### 9.3.5 Expansion

Expansion is the process of expanding an open structural node during the layout process.

This expansion depends on the [fact source](#term-fact-source).

Aspects that participate in expansion are referred to as expansion aspects.

An open structural node contributes one layout node for each value of each [expansion aspect](#term-expansion-aspect) it defines. Every open definition node defines the [expansion aspects](#term-expansion-aspect) of its corresponding structural node.

- See [**Section 6.8.2**](#sec-aspect-node-expansion) for a description of expansion for aspect nodes (the only open nodes defined by this specification).

### 9.3.6 Layout for data presentation

Given a set of facts from the fact source, the layout process **MUST** constrain these facts to those which satisfy all table filters (if any) associated with the table.

These facts **MUST** be arranged in the table according to the constraints associated with its slices (e.g. the columns, rows and positions along the z-axis).

### 9.3.7 Layout for data entry

[Closed tables](#term-closed-table) have a fixed [shape](#term-shape-of-table) in that they do not depend on facts in a fact source, so the initial layout process for data entry is the same as for data presentation of an empty fact source when performing no elimination.

[Open tables](#term-open-table) have a [shape](#term-shape-of-table) that depends on the fact source. For data entry, the facts in the fact source can change (and it will often be empty initially).

Processing software that supports data entry **MUST** allow the user to dynamically add aspect values for any expansion aspects. These aspect values **MUST** be validated against the constraints defined by the open definition nodes.

For example, if an open definition node defines period as an expansion aspect, but defines no constraint, the user should be able to create new columns for any period. If an open definition node defines a typed dimension as a expansion aspect, constraining values to a be numeric, the user should be able to create new columns for that dimension and the user should either be prevented from entering non-numeric values or any non-numeric value entered should cause a validation error after entry.

## Appendix A Normative schemas

The following is the XML schema provided as part of this specification. This is normative. Non-normative versions (which should be identical to these except for appropriate comments indicating their non-normative status) are also provided as separate files for convenience of users of the specification.

NOTE: (non-normative) Following the schema maintenance policy of XBRL International, it is the intent (but is not guaranteed) that the location of non-normative versions of these schemas on the web will be as follows:

1. While any schema is the most current RECOMMENDED version and until it is superseded by any additional errata corrections a non-normative version will reside on the web in the directory `http://www.xbrl.org/2014/`.
2. A non-normative version of each schema as corrected by any update to the RECOMMENDATION will be archived in perpetuity on the web in a directory that will contain a unique identification indicating the date of the update.

## A.1 Table linkbase schema (table.xsd)

<schema  
xmlns="http://www.w3.org/2001/XMLSchema"  
xmlns:link="http://www.xbrl.org/2003/linkbase"  
xmlns:variable="http://xbrl.org/2008/variable"  
xmlns:xl="http://www.xbrl.org/2003/XLink" elementFormDefault="qualified" targetNamespace="http://xbrl.org/2014/table"><appinfo><link:arcroleType arcroleURI="http://xbrl.org/arcrole/2014/table-breakdown" cyclesAllowed="undirected" id="table-breakdown"><link:definition>

breakdown used on the axes of a table

</link:definition><link:usedOn>

table:tableBreakdownArc

</link:usedOn></link:arcroleType><link:arcroleType arcroleURI="http://xbrl.org/arcrole/2014/breakdown-tree" cyclesAllowed="undirected" id="breakdown-tree"><link:definition>

root node of a breakdown tree

</link:definition><link:usedOn>

table:breakdownTreeArc

</link:usedOn></link:arcroleType><link:arcroleType arcroleURI="http://xbrl.org/arcrole/2014/table-filter" cyclesAllowed="undirected" id="table-filter"><link:definition>

filter applied to table

</link:definition><link:usedOn>

table:tableFilterArc

</link:usedOn></link:arcroleType><link:arcroleType arcroleURI="http://xbrl.org/arcrole/2014/table-parameter" cyclesAllowed="undirected" id="table-parameter"><link:definition>

parameter of a table

</link:definition><link:usedOn>

table:tableParameterArc

</link:usedOn></link:arcroleType></appinfo>

<import namespace="http://www.xbrl.org/2003/XLink" schemaLocation="http://www.xbrl.org/2003/xl-2003-12-31.xsd"/>

<import namespace="http://xbrl.org/2008/variable" schemaLocation="http://www.xbrl.org/2008/variable.xsd"/>

<import namespace="http://xbrl.org/2008/formula" schemaLocation="http://www.xbrl.org/2008/formula.xsd"/>

<import namespace="http://xbrl.org/2008/generic" schemaLocation="http://www.xbrl.org/2008/generic-link.xsd"/>

<extension base="xl:resourceType">

<attribute default="parent-first" name="parentChildOrder" type="table:parentChildOrder.type" use="optional"/>

<!---->

<anyAttribute namespace="##other" processContents="lax"/>

</extension><extension base="xl:resourceType">

<attribute name="parentChildOrder" type="table:parentChildOrder.type" use="optional"/>

<!---->

<anyAttribute namespace="##other" processContents="lax"/>

</extension><attributeGroup name="definitionNode.attrs"><documentation>

Attributes for definition nodes.

</documentation>

<attribute name="tagSelector" type="NCName" use="optional"/>

<!---->

<anyAttribute namespace="##other" processContents="lax"/>

</attributeGroup><extension base="xl:resourceType">

<attributeGroup ref="table:definitionNode.attrs"/>

</extension><restriction base="token">

<enumeration value="parent-first"/>

<enumeration value="children-first"/>

</restriction><extension base="table:definitionNode.type">

<attribute name="parentChildOrder" type="table:parentChildOrder.type" use="optional"/>

</extension><restriction base="anyType">

<!---->

<anyAttribute namespace="##other" processContents="lax"/>

</restriction>

<element abstract="true" id="xml-abstract-aspect-spec" name="aspectSpec" type="anyType"/>

<element id="xml-concept-aspect-spec" name="conceptAspect" substitutionGroup="table:aspectSpec" type="table:simpleAspectSpec.type"/>

<element id="xml-unit-aspect-spec" name="unitAspect" substitutionGroup="table:aspectSpec" type="table:simpleAspectSpec.type"/>

<element id="xml-entity-identifier-aspect-spec" name="entityIdentifierAspect" substitutionGroup="table:aspectSpec" type="table:simpleAspectSpec.type"/>

<element id="xml-period-aspect-spec" name="periodAspect" substitutionGroup="table:aspectSpec" type="table:simpleAspectSpec.type"/>

<extension base="QName">

<attribute default="false" name="includeUnreportedValue" type="boolean" use="optional"/>

<!---->

<anyAttribute namespace="##other" processContents="lax"/>

</extension>

<element id="xml-dimension-aspect-spec" name="dimensionAspect" substitutionGroup="table:aspectSpec" type="table:dimensionAspectSpec.type"/>

<element id="xml-table" name="table" substitutionGroup="xl:resource" type="table:table.type"/>

<element id="xml-breakdown" name="breakdown" substitutionGroup="xl:resource" type="table:breakdown.type"/>

<element abstract="true" id="xml-abstract-definition-node" name="definitionNode" substitutionGroup="xl:resource" type="table:definitionNode.type"/>

<element abstract="true" id="xml-abstract-closed-definition-node" name="closedDefinitionNode" substitutionGroup="table:definitionNode" type="table:closedDefinitionNode.type"/>

<restriction base="token">

<enumeration value="x"/>

<enumeration value="y"/>

<enumeration value="z"/>

</restriction><extension base="gen:genericArcType">

<attribute name="axis" type="table:axis.type" use="required"/>

</extension><complexContent>

<extension base="gen:genericArcType"/>

</complexContent><extension base="gen:genericArcType">

<attribute name="complement" type="boolean" use="required"/>

</extension><extension base="gen:genericArcType">

<attribute name="name" type="variable:QName" use="required"/>

</extension><link:arcroleType arcroleURI="http://xbrl.org/arcrole/2014/definition-node-subtree" cyclesAllowed="undirected" id="definition-node-subtree"><link:definition>

arc between a parent and child definition node.

</link:definition><link:usedOn>

table:definitionNodeSubtreeArc

</link:usedOn></link:arcroleType><complexContent>

<extension base="gen:genericArcType"/>

</complexContent><complexType name="ruleSet.type"><sequence maxOccurs="unbounded" minOccurs="0">

<element ref="formula:abstract.aspect"/>

</sequence>

<attribute name="tag" type="NCName" use="required"/>

</complexType><extension base="table:closedDefinitionNode.type"><choice>

<element ref="formula:abstract.aspect"/>

<element name="ruleSet" type="table:ruleSet.type" id="xml-rule-set"/>

</choice>

<attribute default="false" name="abstract" type="boolean"/>

<attribute default="false" name="merge" type="boolean"/>

</extension>

<element id="xml-rule-node" name="ruleNode" substitutionGroup="table:closedDefinitionNode" type="table:ruleNode.type"/>

<complexContent>

<extension base="table:closedDefinitionNode.type"></extension>

</complexContent><restriction base="token">

<enumeration value="descendant"/>

<enumeration value="descendant-or-self"/>

<enumeration value="child"/>

<enumeration value="child-or-self"/>

<enumeration value="sibling"/>

<enumeration value="sibling-or-self"/>

<enumeration value="sibling-or-descendant"/>

<enumeration value="sibling-or-descendant-or-self"/>

</restriction><sequence><choice maxOccurs="unbounded" minOccurs="0">

<element maxOccurs="unbounded" minOccurs="0" name="relationshipSource" type="QName"/>

<element maxOccurs="unbounded" minOccurs="0" name="relationshipSourceExpression" type="variable:expression"/>

</choice><choice maxOccurs="1" minOccurs="0">

<element name="linkrole" type="xl:nonEmptyURI"/>

<element name="linkroleExpression" type="variable:expression"/>

</choice><choice maxOccurs="1" minOccurs="1">

<element name="arcrole" type="xl:nonEmptyURI"/>

<element name="arcroleExpression" type="variable:expression"/>

</choice><choice maxOccurs="1" minOccurs="0">

<element name="formulaAxis" type="table:conceptRelationshipFormulaAxis.type"/>

<element name="formulaAxisExpression" type="variable:expression"/>

</choice><choice maxOccurs="1" minOccurs="0">

<element name="generations" type="nonNegativeInteger"/>

<element name="generationsExpression" type="variable:expression"/>

</choice><choice maxOccurs="1" minOccurs="0">

<element name="linkname" type="QName"/>

<element name="linknameExpression" type="variable:expression"/>

</choice><choice maxOccurs="1" minOccurs="0">

<element name="arcname" type="QName"/>

<element name="arcnameExpression" type="variable:expression"/>

</choice></sequence><restriction base="token">

<enumeration value="descendant"/>

<enumeration value="descendant-or-self"/>

<enumeration value="child"/>

<enumeration value="child-or-self"/>

</restriction><sequence><choice maxOccurs="unbounded" minOccurs="0">

<element maxOccurs="unbounded" minOccurs="0" name="relationshipSource" type="QName"/>

<element maxOccurs="unbounded" minOccurs="0" name="relationshipSourceExpression" type="variable:expression"/>

</choice><choice maxOccurs="1" minOccurs="0">

<element name="linkrole" type="xl:nonEmptyURI"/>

<element name="linkroleExpression" type="variable:expression"/>

</choice>

<element maxOccurs="1" minOccurs="1" name="dimension" type="QName"/>

<choice maxOccurs="1" minOccurs="0">

<element name="formulaAxis" type="table:dimensionRelationshipFormulaAxis.type"/>

<element name="formulaAxisExpression" type="variable:expression"/>

</choice><choice maxOccurs="1" minOccurs="0">

<element name="generations" type="nonNegativeInteger"/>

<element name="generationsExpression" type="variable:expression"/>

</choice></sequence>

<element id="xml-concept-relationship-node" name="conceptRelationshipNode" substitutionGroup="table:closedDefinitionNode" type="table:conceptRelationshipNode.type"/>

<element id="xml-dimension-relationship-node" name="dimensionRelationshipNode" substitutionGroup="table:closedDefinitionNode" type="table:dimensionRelationshipNode.type"/>

<link:arcroleType arcroleURI="http://xbrl.org/arcrole/2014/aspect-node-filter" cyclesAllowed="undirected" id="aspect-node-filter"><link:definition>

filter applied to aspect node

</link:definition><link:usedOn>

table:aspectNodeFilterArc

</link:usedOn></link:arcroleType><sequence>

<element ref="table:aspectSpec"/>

</sequence>

<element id="xml-aspect-node" name="aspectNode" substitutionGroup="table:definitionNode" type="table:aspectNode.type"/>

<extension base="gen:genericArcType">

<attribute default="false" name="complement" type="boolean" use="optional"/>

</extension></schema>

## A.2 Layout model schema (tablemodel.xsd)

<schema  
xmlns="http://www.w3.org/2001/XMLSchema"  
xmlns:model="http://xbrl.org/2014/table/model" targetNamespace="http://xbrl.org/2014/table/model" elementFormDefault="qualified">

<import namespace="http://xbrl.org/2014/table" schemaLocation="table.xsd"/>

<element id="xml-table-model" name="tableModel"><documentation>

This is the top level element representing a table model containing zero or more table sets, each derived from a single table definition in the table linkbase.

</documentation><complexType><sequence>

<element id="xml-rendering-table-set" name="tableSet" type="model:tableSet.type" minOccurs="0" maxOccurs="unbounded"/>

</sequence>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</complexType></element><sequence>

<element id="xml-rendering-table-label" name="label" type="model:label.type" minOccurs="0" maxOccurs="unbounded"/>

<element id="xml-rendering-table" name="table" type="model:table.type" minOccurs="1" maxOccurs="unbounded"/>

</sequence><complexType name="table.type"><documentation>

This type represents a table. A table has fixed axes as described by the table headers.

</documentation><sequence>

<element id="xml-rendering-table-headers" name="headers" type="model:headers.type" minOccurs="1" maxOccurs="unbounded"/>

<element id="xml-rendering-table-cells" name="cells" type="model:cells.type" minOccurs="1" maxOccurs="1"/>

</sequence>

<anyAttribute namespace="http://www.w3.org/XML/1998/namespace" processContents="lax"/>

</complexType><complexType name="headers.type"><documentation>

This type represents the headers for a single axis (x, y or z) of a table.

</documentation><sequence>

<element id="xml-rendering-table-group" name="group" type="model:group.type" minOccurs="0" maxOccurs="unbounded"/>

</sequence>

<attributeGroup ref="model:commonAttributes.group"/>

</complexType><documentation>

This type represents groups levels in a set of headers for a single axis, for labelling purposes.

</documentation><complexType name="header.type"><documentation>

This type represents a single level in a set of headers for a single axis. It contains a series of header labels.

</documentation><sequence>

<element id="xml-rendering-cell" name="cell" type="model:headerCell.type" minOccurs="1" maxOccurs="unbounded"/>

</sequence></complexType><extension base="string">

<attribute name="source" type="model:labelSource.type" use="optional" default="explicit"/>

</extension><complexType name="constraint.type"><sequence>

<element id="xml-rendering-constraint-aspect" name="aspect" type="model:aspect.type" minOccurs="1" maxOccurs="1"/>

<element id="xml-rendering-constraint-value" name="value" type="model:value.type" minOccurs="1" maxOccurs="1"/>

</sequence>

<attribute name="tag" type="NCName" use="optional"/>

</complexType><restriction base="token">

<enumeration value="explicit"/>

<enumeration value="processor"/>

</restriction><restriction base="token">

<enumeration value="concept"/>

<enumeration value="entity-identifier"/>

<enumeration value="period"/>

<enumeration value="unit"/>

<!---->

<enumeration value="segment"/>

<enumeration value="scenario"/>

</restriction><sequence>

<any namespace="##other" processContents="lax" minOccurs="0" maxOccurs="unbounded"/>

</sequence><complexType name="cells.type"><choice minOccurs="0" maxOccurs="unbounded">

<element name="cells" type="model:cells.type"/>

<element id="xml-rendering-table-cell" name="cell" type="model:cell.type"/>

</choice>

<attributeGroup ref="model:commonAttributes.group"/>

</complexType><complexType name="cell.type"><sequence>

<element id="xml-rendering-table-fact" name="fact" type="anyURI" minOccurs="0" maxOccurs="unbounded"/>

</sequence>

<attribute name="abstract" type="boolean" use="optional" default="false"/>

</complexType><attributeGroup name="commonAttributes.group">

<attribute name="axis" type="table:axis.type" use="required"/>

</attributeGroup></schema>

## Appendix B References

CONCEPT RELATION FILTERS

XBRL International Inc..  
["XBRL Concept Relation Filters 1.0"](http://www.xbrl.org/Specification/conceptRelationFilters/REC-2011-10-24/conceptRelationFilters-REC-2011-10-24.html)  
Phillip Engel, Herm Fischer, Victor Morilla, Jim Richards, Geoff Shuetrim, David vun Kannon, and Hugh Wallis.

DIMENSION FILTERS

XBRL International Inc..  
["XBRL Dimension Filters 1.0"](http://www.xbrl.org/Specification/dimensionFilters/REC-2009-06-22/dimensionFilters-REC-2009-06-22+corrected-errata-2011-03-10.html)  
Phillip Engel, Herm Fischer, Victor Morilla, Jim Richards, Geoff Shuetrim, David vun Kannon, and Hugh Wallis.

DIMENSIONS

XBRL International Inc..  
["XBRL Dimensions 1.0"](http://www.xbrl.org/specification/dimensions/rec-2012-01-25/dimensions-rec-2006-09-18+corrected-errata-2012-01-25-clean.html)  
Ignacio Hernández-Ros, and Hugh Wallis.

FORMULA

XBRL International Inc..  
["XBRL Formula 1.0"](http://www.xbrl.org/Specification/formula/REC-2009-06-22/formula-REC-2009-06-22.html)  
Phillip Engel, Herm Fischer, Victor Morilla, Jim Richards, Geoff Shuetrim, David vun Kannon, and Hugh Wallis.

GENERIC LABELS

XBRL International Inc..  
["XBRL Generic Labels 1.0"](http://www.xbrl.org/Specification/genericLabels/REC-2009-06-22/genericLabels-REC-2009-06-22.html)  
Phillip Engel, Herm Fischer, Victor Morilla, Jim Richards, Geoff Shuetrim, David vun Kannon, and Hugh Wallis.

GENERIC LINKS

XBRL International Inc..  
["XBRL Generic Links 1.0"](http://www.xbrl.org/Specification/gnl/REC-2009-06-22/gnl-REC-2009-06-22.html)  
Mark Goodhand, Ignacio Hernández-Ros, and Geoff Shuetrim.

GENERIC REFERENCES

XBRL International Inc..  
["XBRL Generic References 1.0 (Public Working Draft)"](http://www.xbrl.org/Specification/genericReferences/REC-2009-06-22/genericReferences-REC-2009-06-22.html)  
Phillip Engel, Herm Fischer, Victor Morilla, Jim Richards, Geoff Shuetrim, David vun Kannon, and Hugh Wallis.

VARIABLES

XBRL International Inc..  
["XBRL Variables 1.0"](http://www.xbrl.org/Specification/variables/REC-2009-06-22/variables-REC-2009-06-22.html)  
Phillip Engel, Herm Fischer, Victor Morilla, Jim Richards, Geoff Shuetrim, David vun Kannon, and Hugh Wallis.

XBRL 2.1

XBRL International Inc..  
["Extensible Business Reporting Language (XBRL) 2.1 Includes Corrected Errata Up To 2013-02-20"](http://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31+corrected-errata-2013-02-20.html)  
Phillip Engel, Walter Hamscher, Geoff Shuetrim, David vun Kannon, and Hugh Wallis.

XLINK

W3C (World Wide Web Consortium).  
["XML Linking Language (XLink) Version 1.0"](http://www.w3.org/TR/xlink/)  
Steve DeRose, Eve Maler, and David Orchard.

XML NAMES

W3C (World Wide Web Consortium).  
["Namespaces in XML 1.0 (Second Edition)"](http://www.w3.org/TR/REC-xml-names/)  
Tim Bray, Dave Hollander, Andrew Layman, and Richard Tobin.

XPATH 2.0

W3C (World Wide Web Consortium).  
["XML Path Language (XPath) 2.0"](http://www.w3.org/TR/xpath20/)  
Anders Berglund, Scott Boag, Don Chamberlin, Mary F. Fernández, Michael Kay, Jonathan Robie, and Jérôme Siméon.

XPATH AND XQUERY FUNCTIONS

W3C (World Wide Web Consortium).  
["XQuery 1.0 and XPath 2.0 Functions and Operators"](http://www.w3.org/TR/xpath-functions/)  
Ashok Malhotra, Jim Melton, and Norman Walsh.

XPOINTER

W3C (World Wide Web Consortium).  
["XPointer Framework"](http://www.w3.org/TR/xptr-framework/)  
Paul Grosso, Eve Maler, Jonathan Marsh, and Norman Walsh.

## Appendix C Intellectual property status (non-normative)

This document and translations of it may be copied and furnished to others, and derivative works that comment on or otherwise explain it or assist in its implementation may be prepared, copied, published and distributed, in whole or in part, without restriction of any kind, provided that the above copyright notice and this paragraph are included on all such copies and derivative works. However, this document itself may not be modified in any way, such as by removing the copyright notice or references to XBRL International or XBRL organizations, except as required to translate it into languages other than English. Members of XBRL International agree to grant certain licenses under the XBRL International Intellectual Property Policy ([www.xbrl.org/legal](http://www.xbrl.org/legal)).

This document and the information contained herein is provided on an "AS IS" basis and XBRL INTERNATIONAL DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTY THAT THE USE OF THE INFORMATION HEREIN WILL NOT INFRINGE ANY RIGHTS OR ANY IMPLIED WARRANTIES OF MERCHANTABILITY OR FITNESS FOR A PARTICULAR PURPOSE.

The attention of users of this document is directed to the possibility that compliance with or adoption of XBRL International specifications may require use of an invention covered by patent rights. XBRL International shall not be responsible for identifying patents for which a license may be required by any XBRL International specification, or for conducting legal inquiries into the legal validity or scope of those patents that are brought to its attention. XBRL International specifications are prospective and advisory only. Prospective users are responsible for protecting themselves against liability for infringement of patents. XBRL International takes no position regarding the validity or scope of any intellectual property or other rights that might be claimed to pertain to the implementation or use of the technology described in this document or the extent to which any license under such rights might or might not be available; neither does it represent that it has made any effort to identify any such rights. Members of XBRL International agree to grant certain licenses under the XBRL International Intellectual Property Policy ([www.xbrl.org/legal](http://www.xbrl.org/legal)).

## Appendix D Acknowledgements (non-normative)

This document could not have been written without the contributions of many people.

## Appendix E Document history (non-normative)

| Date | Author | Details |
| --- | --- | --- |
| 01 October 2011 | Herm Fischer | Initial draft |
| 09 October 2011 | Victor Morilla | Added comments on issues that require further disucssion |
| 11 October 2011 | Hugh Wallis | Identified unresolved issues and commented them for publication and feedback solicitation |
| 28 October 2011 | Herm Fischer | Working group updates: position of coordinate in axes |
| 03 November 2011 | Herm Fischer | Working group updates: replace predefinedAxis model with subtrees of ruleAxes and compositions of ruleAxes with relationshipAxes. Replace axis-member notion with that of axis subtree composition. |
| 05 December 2011 | Herm Fischer | Update class diagram, provide schema definitions. |
| 19 December 2011 | Herm Fischer | Editorial updates suggested by [**Roland Hommes**](#p-rh) in WG e-mail of 2011-12-08. |
| 23 April 2012 | Herm Fischer | Editorial updates suggested by [**Takahide Muramoto**](#p-tm) in WG e-mail of 2012-04-11. Includes new error code axisValueClash, clarification to syntax. parentChildOrder has an example where the parents are first at an outer level of nesting and children are first in more detail breakdowns nested within. |
| 08 May 2012 | Herm Fischer | Clarified use of coordinate (orders among axes dispositions taken together) and ordinate (ordering along a single axis disposition).  Added Message can be used to label headers in table |
| 28 May 2012 | Herm Fischer | Added parentChildOrder attribute to table, made attribute optional in schema, added that it is inheritable, and added an error code of there is no value specified or inheritable on a predefinedAxis element. |
| 30 May 2012 | Herm Fischer | Added parentChildOrder table default parent-first, per F2F WG agreement.  Added explanation of axis headers, per F2F WG agreement.  Moved rendering attributes to CSS specification, per F2F WG agreement, added class attributes to relationships. |
| 10 July 2012 | Herm Fischer | Added axis-selection-message arcrole arelationship. |
| 11 July 2012 | Herm Fischer | Per WG decision 2012-07-04, merged separate specs into this spec: rule axis, composition axis, relationship axis, tuple axis, selection axis, and filter axis. |
| 21 July 2012 | Herm Fischer | Editorial updates suggested by [**Roland Hommes**](#p-rh): (a) removed error code error-missing-parent-child-order-attribute as WG agreed to a parentChildOrder inherited from of table element which has a default; (b) removed references to standard labels, as they can only apply in message constructs (due to need to handle role selection when appropriate to relationship axes); (c) clarified that language selection for axis headers applies to label and messages; (d) clarified ordering of a single ordinate's multiple axis headers (using ` @order` across arcroles) |
| 01 August 2012 | Herm Fischer | Editorial updates suggested by WG e-mails from [**Shogo Ohyama**](#p-so): (a) Filter axes wording in paragraph 1 of [**Section 6.8.1**](#sec-aspect-node-aspect-constraints). (b) Filter axes with XPath expressions dependent on other ordinate values by variable names, in [**Section 6.8.4**](#sec-aspect-node-syntax). |
| 26 October 2012 | Jon Siddle | Re-organise content to fit the new three-model approach. |
| 08 November 2012 | Jon Siddle | Rename (eg axis -> breakdown) according to WG discussion and editorial changes. |
| 09 November 2012 | Jon Siddle | Add more details on the structural model. |
| 12 November 2012 | Jon Siddle | Improvements to wording and formatting. Clarify some definitions. |
| 13 November 2012 | Jon Siddle | Define top level use cases, reorder model descriptions and fix schema validation issues. |
| 19 November 2012 | Jon Siddle | Clarify various descriptions (particularly in relation to open and closed tables and ordering). Updated figures. Some rewording and formatting improvements. |
| 21 November 2012 | Jon Siddle | Clarify restrictions on defined axes and tables in a table linkbase. Use new terms more consistently. Update naming for consistency. |
| 26 November 2012 | Jon Siddle | Shuffling of content and rewording, especially in the definition model section.  Remove remaining uses of "ordinate".  Added missing description. Some formatting improvements. |
| 28 November 2012 | Jon Siddle | Expand and clarify a number of descriptions. Some grammar, broken reference and schema validity fixes.  Define missing terms. Describe participating aspects and change uses of "covering" to "participating" where appropriate. |
| 29 November 2012 | Jon Siddle | Improve subsection headings.  Clarify and expand on descriptions for shape of the table, table cells, coveredAspect, etc. |
| 06 December 2012 | Jon Siddle | Further wording and formatting improvements.  Update rendering model, incorporating some of the suggestions made in the comments. Add a preliminary definition for cells. |
| 11 December 2012 | Jon Siddle | Move definitions of models. Other minor changes to clarify terminology. Reorganise and expand rendering sections. |
| 17 December 2012 | Jon Siddle | Clarification of xfi function usage. Move sections to be consistent with similar specifications, make example non-normative. |
| 20 December 2012 | Jon Siddle | Define abstract / non-abstract nodes and remove explicit roll-up nodes in the definition model, in accordance with WG resolution. Rewrite closed definition node description since previous assertions no longer hold.  Describe elimination, and tidy up some no longer relevant descriptions and an error code.  Improvements to abstract / non-abstract description.  Minor fixes (prefixes, example name, broken reference). |
| 21 December 2012 | Jon Siddle | Rendering model and rendering process updates.  Improve description of ordering and Cartesian product of breakdown constraint sets. |
| 07 January 2013 | Jon Siddle | Minor fixes (missing ID, orphaned comment, etc.). |
| 08 January 2013 | Jon Siddle | Rename @disposition to @axis in the infoset schema for consistency with the table linkbase schema. |
| 08 February 2013 | Joshua Roache | Change valid values for dimension relationship node formula axis elements to reflect those accepted by formula for dimension filters. |
| 19 February 2013 | Jon Siddle | Remove composition node (redundant), selection node (no use-cases for v1.0) and tuple nodes (agreed that v1.0 doesn't need special treatment of tuples). |
| 20 March 2013 | Victor Morilla | Removed some comments about issues already addressed in the spec. Added some additional comments |
| 20 March 2013 | Jon Siddle | Add a definition of effective constraints (specified or inherited) on a node, and define behaviour for leaf nodes not specifying all participating aspects, as agreed at the Oxford F2F |
| 26 March 2013 | Jon Siddle | Add a description of behaviour for unspecified aspects for a table, as agreed at the Oxford F2F.  Add a description of height-balancing for structural breakdowns to ensure they "line up" correctly (and unambiguously) when projected onto an axis. |
| 27 March 2013 | Jon Siddle | Clarify that only one breakdown per table is necessary. |
| 28 March 2013 | Jon Siddle | Some fixes and improvements around issues identified by Victor's recent comments.  Removed some stale comments which no longer apply.  Incorporated some of Roland's feedback.  Updated / added comments according to agreements from Oxford F2F. |
| 10 March 2013 | Jon Siddle | Redrafting of sections relating to labels and header cells, as agreed at the Oxford F2F. |
| 14 March 2013 | Jon Siddle | Redrafting around Dublin F2F discussions. |
| 25 April 2013 | Jon Siddle | Drafting aspectNode replacement for filterNode as per Dublin discussion. |
| 29 April 2013 | Jon Siddle | Added example of filter behaviour for non-participating aspects (in relation to aspectNodes). |
| 07 May 2013 | Jon Siddle | Fix a couple of errors noted in feedback to the group. |
| 28 May 2013 | Joshua Roache | Define error codes for constraints on the starting and ending resources of arcs. |
| 30 May 2013 | Jon Siddle | Update to reflect that definition-node-subtree can be used for open nodes too. |
| 05 June 2013 | Jon Siddle | Update to ensure that QNames refer to existing concepts. |
| 12 June 2013 | Jon Siddle | Specify that open node expansion order is implementation-dependent, as agreed. |
| 24 June 2013 | Joshua Roache | No longer iterate over multiple link roles on relationship nodes.  No link role specified now means the default link role. |
| 03 July 2013 | Jon Siddle | Add @merge attribute to indicate a merged rule node which only adds constraints and doesn't contribute a structural node. Also added errors for merged rule nodes. |
| 09 July 2013 | Jon Siddle | Remove section for unused structural infoset. Changed wording of "infoset" for remaining uses, since our usage was not consistent with existing usage. Both as agreed at the London F2F. |
| 10 July 2013 | Jon Siddle | Add missing error code. |
| 10 July 2013 | Joshua Roache | @complement attribute on aspect-node-filter relationships now has a default value of 'false'. |
| 12 July 2013 | Jon Siddle | Generalise structural nodes to have (possibly tagged) constraint sets, not a single set of constraints. This is the proposed solution for making start/end period line-up possible. |
| 12 July 2013 | Joshua Roache | Add error code for subtrees linked to definition nodes that cannot have subtrees |
| 15 July 2013 | Jon Siddle | Improvements to specification of ruleSets/constraintSets/tags.  Aspect model is now always dimensional. |
| 23 July 2013 | Jon Siddle | Define parentChildOrder more consistently, and make the inheritance clear. |
| 19 August 2013 | Jon Siddle | Define table-filter relationships in terms of 2.1 relationships, not arcs.  Define table-parameter relationships in terms of 2.1 relationships, not arcs.  Define table-breakdown relationships in terms of 2.1 relationships, not arcs.  Define breakdown-tree relationships in terms of 2.1 relationships, not arcs.  Define definition-node-subtree relationships in terms of 2.1 relationships, not arcs.  Define aspect-node-filter relationships in terms of 2.1 relationships, not arcs.  Use "reported" instead of "thrown" for errors, as this more accurately reflects the requirement. |
| 20 August 2013 | Jon Siddle | Add some missing errors.  Minor editorial changes.  Clarify that inferred constraints should not be labelled.  Remove unused table source section. Fact source covers this now.  Describe layout header groups, and how they get their labels. |
| 27 August 2013 | Jon Siddle | Shuffle table set and table parameter sections and clarify wording.  Add definitions for path, slice and cell labels. |
| 28 August 2013 | Jon Siddle | Minor clarification to slice label description. |
| 29 August 2013 | Jon Siddle | Remove error code as agreed on call. |
| 17 September 2013 | Jon Siddle | Add specification of equality for aspect values.  Remove section on relationship binding since there hasn't been a way to use these bindings for some time.  Remove out of date comments.  Update wording from filter node to aspect node in one place that was missed. |
| 19 September 2013 | David North | Add requirement that processors must be able to disable elimination of empty slices for data presentation, and note that the conformance suite requires this.  Clarify wording for duplicateTag and constraintSetAspectMismatch errors. |
| 01 October 2013 | Jon Siddle | Clarification of introductory paragraph.  Remove some repetition from the introduction and reword to focus on what this specification is, not what it isn't.  Minor clarification to XPath usage.  Clarify that the two defined uses aren't exclusive.  Minor grammatical improvements.  Remove repetition of table set definition where it was incomplete, less clear and less relevant.  Tidy up wording of domain of the table.  Use "included" instead of "presented or entered into". Be more precise about table domain, facts being constrained, etc. Remove unused "belonging to a table" as discussed.  Move fact source up to the top since it's referenced almost immediately, and its definition stands alone.  Improved flow of concept relationship node section. Reference 2.1 concepts not domain-members. |
| 23 October 2013 | Jon Siddle | Minor wording tweaks  Partitioning is really expansion, and what we were calling expansion is just node resolution.  Make description of projection more precise. Remove reference to Cartesian product of constraint sets, as we're producing trees not sequences and this only confuses things that are well-defined elsewhere.  Remove addressed comments.  Remove remaining mentions of "belonging" to a table.  Clarify wording of non-participating aspects. |
| 23 October 2013 | Joshua Roache | Remove error code as agreed with the working group.  Clarify that the aspect model of the table is the dimensional aspect model.  Rename aspect clash and conflicting aspect rule error codes to make their meanings clearer. |
| 24 October 2013 | Jon Siddle | Clarify wording of non-participating aspects.  Minor improvements to wording around processes. |
| 28 October 2013 | Jon Siddle | Address use of "group" where it is potentially confusing. |
| 28 October 2013 | Joshua Roache | Add new error code for incomplete aspect rules.  Describe serialisation of breakdown labels. |
| 30 October 2013 | Jon Siddle | Open nodes can have children, so remove conflicting statement.  Remove unnecessary nested section for specific definition node types.  Remove unnecessary nesting in resolution description.  Correct minor typos. |
| 31 October 2013 | Joshua Roache | Update introduction to make it clearer that the specification does not define a rendering for tables. |
| 01 November 2013 | Joshua Roache | Allow breakdowns with no aspects as authors may want to be able to label an axis that has no constraints. |
| 04 November 2013 | Jon Siddle | Reword QName ordering to reference Unicode Codepoint Collation already used by XPath. |
| 05 November 2013 | David North | Updated table set serialization to remove out of date material and add description of table set label serialization. |
| 27 November 2013 | Joshua Roache | The structural model diagram now shows that a structural breakdown can have multiple root structural nodes.  Remove attributes from the definition model diagram that are no longer part of the schema. |
| 16 December 2013 | David North | Fixed link in aspect value equality for typed dimensions to point to the correct section of the variables specification. This avoids implying that custom typed-dimension aspect tests are not applicable within this specification.  Remove outdated wording in the variable references section - nodes can no longer define variables. Also delete requirement to raise an error for cyclic dependencies between variables. Since Table Linkbase can no longer define variables, cycles can only occur between global parameters, and this is validated by the Variables specification upon which this specification depends.  Remove wording about how relationships linking labels and references to Table Linkbase constructs may be in any extended link role. This is already made clear by the XLink specification and does not need re-stating here.  Added missing description of the XPointer mechanism used to reference facts from cells in the layout model serialisation.  Added missing definition and equality for OCC (non-XDT segment/scenario) aspect values.  Added missing error code for unrecognised aspect rules.  Make explicit which filters are associated with a given cell in a table.  Added error code for when the result of an XPath expression on a relationship node cannot be cast to the required type.  Generalise error code for merged rule nodes with labels to cover other types of definition node which must not have labels.  Removed the ability to specify the participating dimension of a dimension relationship node using an XPath expression. By referencing parameters, this capability could have violated the requirement for the participating aspects of a breakdown to be determinable during resolution in the absence of an instance. The ability to define aspects of a breakdown dynamically may be revisited in a future version of this specification. |
| 16 December 2013 | Joshua Roache | Add tag selector attributes to the definition model diagrams.  Add merge attribute to rule node in the definition model diagrams.  Clarify behaviour of relationship node resolution when encountering abstract concepts/unusable members at the leaf level of the tree walk.  Update outdated explanation of closed definition nodes and zero cardinality to allow for merged rule nodes.  Update outdated explanation of definition node resolution to allow for merged rule nodes.  Clarify that tag selectors on a merge rule node should be merged into its children.  Clarify that tag selectors should only be added at the leaves of the concept relationship tree walk. |
| 17 December 2013 | Jon Siddle | Add change annotations from CR.  Minor improvements to wording. |
| 20 January 2014 | David North | Removed change annotations for changes from CR to PR.  Fixed typographical error in the definition of cell label.  Minor correction to wording relating to tag selectors for relationship nodes  Reverted previous hyperlink change to imply custom typed dimension equalities are in scope for this specification. These are not implementable within Table Linkbase owing to their dependence on facts, and hence should not have been allowed in the PR of this specification. Added clarifying note about this. |
| 31 January 2014 | David North | Fixed some editorial errors in the description of the layout model serialization.  Fixed broken hyperlinks and typographical error 'label' which should have read 'cell'.  Removed out-of-date reference to now-removed @label attribute. |

## Appendix F Errata corrections in this document

This appendix contains a list of the errata corrections that have been incorporated into this document. This represents all those errata corrections that have been approved by the XBRL International Rendering Working Group up to and including 17 December 2024.

| Number | Date | Sections | Details |
| --- | --- | --- | --- |
| 1. | 10 June 2015 | [**Section 8.4**](#sec-layout-serialisation-cells) | Improvements to layout model serialisation designed to make it easier for vendors to run the conformance suite. |
| 2. | 25 November 2015 | [**Section 6.7.4.4**](#sec-concept-relationship-tag-selection)   [**Section 5.5.4**](#sec-structural-node-labels) | Clarification of the term "preferredLabel attribute" to include both standard and generic preferred label attributes. Fixed erroneous references to "label" (singular) in [**Section 5.5.4**](#sec-structural-node-labels). |
| 3. | 20 March 2018 | [**Section 6.7.4.4**](#sec-concept-relationship-tag-selection) | Added error code for use of both standard and generic preferred label attributes (bug 559). |
| 4. | 27 March 2024 | [**Section 6.7.5**](#sec-dimension-relationship-node) | Address wording issue with description of dimension relationship node tree walk (#22). |
| 5. | 11 July 2024 | [**Section 9.3.2**](#sec-layout-projection) | Clarify that inferred aspect constraints are added to breakdowns prior to projection (#20). |
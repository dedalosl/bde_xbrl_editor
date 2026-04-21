---
title: "XBRL Formula Overview 1.0"
source: "https://www.xbrl.org/wgn/xbrl-formula-overview/pwd-2011-12-21/xbrl-formula-overview-wgn-pwd-2011-12-21.html"
author: Herm Fischer
published: 2011-12-21
created: 2026-04-20
description: >
  Overview of XBRL Formula specification — validation based on instance facts and
  generation of derived output facts using assertions, variables, filters, and rules.
tags:
  - "specification"
  - "XBRL"
  - "formula"
  - "validation"
---

# XBRL Formula Overview 1.0

## Abstract

XBRL Formula specifies validations based on XBRL instance facts and generation of derived
data as output XBRL instance facts.

## Goals

XBRL Formula provides validation capabilities not available in XBRL 2.1 base specification
validation or dimensional validation, designed to be:

- Closely attuned to XBRL semantics
- Intuitive in XBRL terms
- Suitable for business users
- Extensible and maintainable
- Formally documentable for audit functions

It also supports output instance documents representing derived data such as transformations,
ratio determination, and data mining.

## Four Processing Models

1. **Value Assertions** — Boolean expressions checked against input instance facts (success or failure)
2. **Existence Assertions** — Count existence of data located by filter expressions
3. **Formula** — Produce output XBRL instance facts with context, unit, concept, and value
4. **Consistency Assertions** — Compare formula output facts with matching input facts within tolerance

## Formula Linkbase Components

- **Assertions** — Boolean expressions (value, existence, or consistency)
- **Formula** — Rules specifying output facts and their aspects
- **Variables** — Fact variables (bind to input facts) and general variables (intermediate results)
- **Filters** — Specify aspects that constrain which facts bind to variables
- **Messages** — Text and structured parameters for assertion/formula results
- **Preconditions** — Determine if bound variables can activate assertions or formulas
- **Parameters** — Internal expressions or externally set values
- **Custom Functions** — XPath 2.0 implementations for organized expressions

## Variable Sets

A variable set is a value assertion, existence assertion, or formula, with its associated
variables. It is an evaluatable processing declaration that, when applied by filters to
input facts, results in assertion attempts and formula processing.

## Filters

Filter types include:

- **Concept name filters** — Match facts by concept QName
- **Dimension filters** — Match facts by dimensional aspects
- **Period filters** — Including `instantDuration` for matching instant to duration boundaries
- **Unit filters** — Match facts by unit
- **Entity filters** — Match facts by entity identifier
- **Parent/ancestor filters** — Match facts by structural position

## Processing

Processing follows this model:

1. Parameters are identified and evaluated
2. Assertions/formulas are identified for processing
3. Fact variables are bound to input facts according to filters
4. Implicit filtering narrows scope by matching uncovered aspects
5. Expressions are evaluated; results are produced

## Implementation Notes

The project uses `elementpath` library with custom `xfi:` function registration for formula
evaluation. See [[XBRL 2.1]] for the base specification.

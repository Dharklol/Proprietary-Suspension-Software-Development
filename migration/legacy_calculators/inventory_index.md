# Legacy Calculator Inventory Index

**Status:** Active Phase 0 documentation  
**Implementation gate:** Physics implementation does not begin until the structural inventory is reviewed and the unresolved source/definition questions are assigned.

## Purpose

This directory inventories the team's existing calculation assets before any formulas are migrated into software. Inventory is deliberately separate from acceptance. A formula can be fully inventoried and still be rejected, rewritten, or retained only as a benchmark.

The inventory records:

- source identity and cryptographic hash;
- workbook and sheet structure;
- meaningful cell ranges and formula population;
- input, output, lookup, sweep, chart, and telemetry blocks;
- cross-sheet and external-process dependencies;
- explicit notes and assumptions already present in the source;
- suspected duplicates and conflicting definitions;
- preliminary migration disposition;
- questions that must be resolved during the five-layer audit.

## Current sources

| Inventory ID | Source | Status | Detailed record |
|---|---|---|---|
| `MIG-SC26-0001` | Suspension Calculations 2026 | Structural inventory complete; semantic audit open | `suspension_calculations_2026/workbook_inventory.md` |
| `MIG-LLTD-0001` | LLTD Calculator | Structural inventory complete; semantic audit open | `lltd_calculator/workbook_inventory.md` |

## Inventory status vocabulary

- **Observed:** directly present in the workbook.
- **Inferred:** interpretation based on labels, formulas, and surrounding context; requires review.
- **Conflict:** two or more values, units, definitions, or methods cannot all be canonical without a resolution rule.
- **Unknown:** purpose or provenance cannot be established from the workbook alone.
- **Blocked:** dependent migration work must not proceed until the issue is resolved.
- **Preliminary disposition:** migration recommendation only; not an engineering approval.

## Required next documentation

1. Cell/block-level disposition register for each sheet.
2. Canonical-quantity mapping for every retained input and output.
3. Equation cards with literature sources and validity envelopes.
4. Parameter provenance records for WUFR-26/WUFR-27 values.
5. Benchmark definitions for calculations retained as hand checks.
6. Retired-item records for abandoned or unidentified content.

## Source preservation

The original workbooks remain immutable source artifacts in Drive. Git records their hashes, inventory, decisions, and later benchmark extracts. The software must never use workbook cell addresses as its runtime API.

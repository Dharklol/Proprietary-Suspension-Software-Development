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
| `MIG-STR-0001` | Tie-rod optimizer and steering motion study | Transition specification active; source recovery open | `steering_tie_rod_optimizer/transition_specification.md` |

`MIG-STR-0001` is the first proposed calculator implementation after its documentation and benchmark gate is satisfied. Priority does not waive any Phase 0 review requirement.

## Phase 0 migration control documents

| Document | Purpose |
|---|---|
| [`block_disposition_register.md`](block_disposition_register.md) | Stable block IDs, source ranges, preliminary dispositions, and next gates for every meaningful workbook block |
| [`canonical_quantity_mapping.md`](canonical_quantity_mapping.md) | Candidate canonical quantity IDs, units, prohibited aliases, and unresolved definition questions |
| [`equation_card_and_benchmark_backlog.md`](equation_card_and_benchmark_backlog.md) | Proposed equation/model IDs, literature work, benchmark plans, and documentation sequence |
| [`../../docs/governance/evidence_role_and_redundancy_policy.md`](../../docs/governance/evidence_role_and_redundancy_policy.md) | Rules for duplicate observations, independent evidence, active-value resolution, filtering, and circular-validation prevention |
| [`../../data_catalog/external_source_recovery_register.md`](../../data_catalog/external_source_recovery_register.md) | Missing external artifacts, recovery metadata, evidence roles, and priorities |
| [`../../docs/governance/implementation_authorization_matrix.md`](../../docs/governance/implementation_authorization_matrix.md) | Explicit authorization states and gates separating documentation, benchmark reproduction, prototype work, and production use |

## Inventory status vocabulary

- **Observed:** directly present in the workbook.
- **Team-described:** described by the team but not yet recovered from the original artifact.
- **Inferred:** interpretation based on labels, formulas, and surrounding context; requires review.
- **Conflict:** two or more values, units, definitions, or methods cannot all be canonical without a resolution rule.
- **Unknown:** purpose or provenance cannot be established from the workbook alone.
- **Blocked:** dependent migration work must not proceed until the issue is resolved.
- **Preliminary disposition:** migration recommendation only; not an engineering approval.

## Six documentation workstreams following structural inventory

1. **Stable block identity:** assign a durable migration ID to every meaningful source block.
2. **Canonical quantity mapping:** map every retained input/output to an explicit quantity candidate rather than a cell or local alias.
3. **Evidence and redundancy control:** classify duplicate, derived, conflicting, calibration, identification, validation, and historical records.
4. **External source recovery:** locate and hash referenced CAD, MATLAB, Box, logger, test, and workbook artifacts.
5. **Equation and benchmark planning:** create equation cards, applicability notes, and verification cases before physics implementation.
6. **Implementation authorization:** explicitly authorize only bounded items whose documentation and verification gates are complete.

These workstreams are now established in the linked control documents. Their existence does not imply that the underlying physics has passed review.

## Required next documentation

1. Review and freeze the first accepted subset of canonical quantity definitions.
2. Link every block ID to exact input/output quantity IDs.
3. Convert legacy values into parameter-observation records with provenance, uncertainty, and applicability.
4. Populate equation-level literature citations and derivations.
5. Recover Priority A external sources and freeze benchmark extracts.
6. Complete five-layer review packets for the first steering and fundamental-model candidates.
7. Create retired records for abandoned, explicitly wrong, empty, or unidentified content.

## Source preservation

The original workbooks and external design artifacts remain immutable source evidence. Git records their hashes, inventory, decisions, and later benchmark extracts. The software must never use workbook cell addresses or copied polynomial coefficients as its runtime API.

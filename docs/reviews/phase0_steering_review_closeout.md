# Phase 0 Steering Review Closeout

**Status:** Review decisions proposed for merge  
**Review scope:** `P0-STR-004`, `P0-STR-005`, `P0-PAR-001`, `P0-STR-007`, `P0-STR-008`, and `P0-STR-009`  
**Excluded:** installed-state completion under `P0-STR-006` and physical correlation under `P0-STR-011`

## Purpose

This packet records whether the steering tasks that had reached `review_ready` satisfy their stated Phase 0 exit criteria. It does not close unresolved installed-state, source-hash, sensor-calibration, compliance-attribution, or Level F acceptance work.

Historical packets remain useful source records, but their old status lines and provisional interpretations are superseded by the versioned configuration, benchmark result, registry records, and this review decision where they conflict.

## Decision summary

| Task | Decision | Basis |
|---|---|---|
| `P0-STR-004` | Complete | `GEO-STEER-BASIC-001` and the Level A/B/C analytical/synthetic expectations were frozen before implementation; `BENCH-STEER-0002` through `0008` are automated and passing. |
| `P0-STR-005` | Complete | `EQ-STEER-0001` through `0007` have equation sources, applicability, numerical behavior, failure semantics, and benchmark links; the bounded implementation exercises the packet. |
| `P0-PAR-001` | Complete | Recovered steering values are represented as inactive, rejected, provisional, active-for-nominal, historical, or installed observations with units, provenance, uncertainty, and applicability. |
| `P0-STR-007` | Complete | Assembly, rack, tie-rod, upright, drawing, BOM, and conflicting-identity hierarchy is mapped; the extraction path is defined. Remaining native-reference checks stay in `RISK-STEER-0001` and installed-state work. |
| `P0-STR-008` | Complete | The nominal baseline, coordinate adapters, FDR point identity, 0.5-in rack revision, static alignment state, exact CAD mirror rule, rack-center mapping, and Level E relationship are reconciled. Remaining physical work has moved to `P0-STR-006` and `P0-STR-011`. |
| `P0-STR-009` | Complete | `AUTH-STEER-0001` was reviewed and merged before implementation; the prototype stayed inside the permitted scope and passed the mandatory benchmark suite. |

## `P0-STR-004` — Steering benchmark geometry

### Exit criterion

`GEO-STEER-BASIC-001` and Level A/B/C expected results are reviewed and frozen before mechanism code begins.

### Evidence

- PR #4 merged the analytical and synthetic benchmark packet before mechanism implementation.
- `benchmarks/steering/preimplementation_freeze_packet.md` explicitly freezes fixture geometry, expected values, tolerances, branch behavior, singularity behavior, and failure semantics.
- PR #9 carried the same fixture into the bounded authorization.
- PR #10 implemented `BENCH-STEER-0002` through `0008` and the tests continue to pass in CI.

### Decision

Complete. Subsequent WUFR-specific Level E/F work does not reopen the synthetic Level A/B/C fixture unless a mechanism-equation change requires re-correlation.

## `P0-STR-005` — Rigid steering function and equation packet

### Exit criterion

`EQ-STEER-0001` through `0007` have reviewed sources, equations, validity limits, numerical behavior, failure states, and benchmark links.

### Evidence

- `docs/models/steering/rigid_steering_function_specification.md` defines the full function inventory and the rigid model boundary.
- Equation cards cover Ackermann reference, tie-rod closure, spatial position solution, transmission staging, ratio definitions, turning-radius constructions, and Ackermann error.
- The specification distinguishes upright rotation from projected road-wheel heading and total heading from incremental steer.
- Bracket preservation, branch continuity, singularity handling, no-extrapolation behavior, structured unavailable outputs, and explicit failures are specified and tested.
- The implementation and Level E work demonstrated that the packet is executable without replacing the mechanism with historical polynomial fits.

### Decision

Complete for the bounded rigid evaluator. Compliance, loads, tire objectives, suspension motion, tolerance propagation, and optimization remain separate model layers and require separate authorization.

## `P0-PAR-001` — Steering parameter-observation seed

### Exit criterion

Recovered WUFR steering dimensions and settings are stored as non-authoritative observations with provenance, units, frame, uncertainty, and applicability before active-value selection.

### Evidence

The registry now distinguishes:

- inactive design-spec observations such as wheelbase and C-factor;
- rejected observations such as the reported `3.12:1` ratio;
- active nominal-design values such as the corrected one-sided `+/-1.00 in` study domain;
- frozen nominal hardpoints and static alignment in `WUFR26_DESIGN_NOMINAL_V0`;
- historical compliance observations;
- the current approximate whole-system `4 deg` free-play observation;
- supplier/component observations that are prohibited from double counting against whole-system measurements.

### Supersession note

The original observation seed's `1.00 in total travel -> +/-0.50 in` interpretation is obsolete. The team clarified that the nominal CAD study permits approximately `1.00 in` to either side of center. `PAR-STEER-0003` and `WUFR26_DESIGN_NOMINAL_V0` are the current authority for that nominal design-source domain. Installed stops remain unmeasured.

### Decision

Complete. This task closes the observation-governance seed, not every active-value or installed-state selection.

## `P0-STR-007` — Steering drawing and BOM authority

### Exit criterion

WUFR-26 steering assembly, rack, tie-rod, and front-upright drawing/BOM hierarchy is mapped; conflicting part identities are recorded; and the active-geometry extraction path is defined.

### Evidence

- `data_catalog/wufr26_steering_drawing_bom_manifest.md` maps the top-level steering assemblies and the current rack, tie-rod, and upright families.
- Manufacturing-feature, component-identity, and mechanism-geometry authority are separated.
- The `SU-60502-AA` versus `ST-60502-AA` mismatch and historical/copied assembly risks are retained rather than erased.
- The required native export path is defined for configurations, component references, axes, joints, stops, installed lengths, adjustment limits, and setup.
- Later reconciliation established the nominal design geometry without claiming that the drawing/BOM manifest alone proves the installed state.

### Decision

Complete. Native active-reference confirmation and immutable source hashing remain open controls under `RISK-STEER-0001`, `P0-STR-002`, and `P0-STR-006`; they do not negate that the hierarchy and extraction path have been defined.

## `P0-STR-008` — WUFR-26 steering baseline reconciliation

### Exit criterion

The real-geometry baseline, specification observations, rejected steering ratio, rack-center/travel interpretation, coordinate adapters, front-left FDR identity, static-toe reference state, geometry-study assembly relationship, and remaining SolidWorks correlation requirements are reviewed.

### Evidence

- OptimumK upright points and FDR steering-specific tie-rod points are merged under a documented source-authority rule.
- The FDR point pair is confirmed as front-left in the SolidWorks vehicle frame.
- The 0.5-in rearward rack revision is separated from coordinate conversion.
- CAD rack center maps exactly to canonical `[-0.079298, 0, 0.162865] m`.
- The team confirms the nominal CAD right side is an exact reflection of the left.
- Static toe and camber follow the setup sheet and are embedded in the nominal reference orientation.
- The wheel-plane projection and descriptive Level E comparison are frozen.
- FDR endpoint values provide an additional design-review cross-check.
- Existing physical free-play, historical compliance, force calculations, and available sensors are linked without being inserted into the rigid model.

### Supersession note

Older reconciliation text that treats `1.00 in` as total rack travel, treats the right side as merely unconfirmed for nominal CAD, or says projected road-wheel heading remains unavailable is historical. The current versioned configuration and Level E contract supersede those statements for nominal design-source use. Installed-state claims remain open.

### Decision

Complete. Remaining stops, staged transmission data, setup uncertainty, source hashes, and physical response belong to `P0-STR-006` and `P0-STR-011`.

## `P0-STR-009` — Bounded rigid steering prototype authorization

### Exit criterion

`AUTH-STEER-0001` is reviewed and merged with permitted functions, numerical behavior, configurations, benchmark requirements, provenance, prohibited scope, and promotion gates explicitly recorded.

### Evidence

- PR #9 merged the human- and machine-readable authorization before mechanism implementation.
- PR #10 implemented the bounded prototype under that authorization.
- The implementation uses explicit geometry provenance, bracket-preserving scalar solving, branch and singularity diagnostics, structured unavailable outputs, and the mandatory benchmark suite.
- Later wheel-plane projection and Level E comparison remained bounded to nominal design-source comparison.
- No optimizer, production release authority, compliance model, or as-built claim has been introduced.

### Decision

Complete. `AUTH-STEER-0001` remains active for the bounded evaluator. Any inverse-design optimizer, production design authority, or higher-fidelity physical model requires a separate authorization.

## Tasks intentionally left open

- `P0-STR-001`: canonical steering definitions need final project-level freeze and review of the remaining full-transmission/path definitions.
- `P0-STR-002`: priority source recovery and immutable project hashes remain incomplete.
- `P0-STR-003`: requirement-role classification remains to be reconciled with the WUFR-27 design workflow.
- `P0-STR-006`: installed stops, transmission, setup uncertainty, staged compliance/backlash attribution, hashes, and Level F tolerance remain open.
- `P0-STR-011`: sensor calibration, physical sweeps, repeatability, staged attribution, uncertainty, and acceptance-rule work remain open.

## Re-correlation rule

The completed tasks reopen only if a change alters one of their frozen contracts—for example:

- an equation or sign convention changes;
- the synthetic fixture or expected results change;
- the nominal steering geometry or coordinate adapter changes;
- the authorization scope expands;
- a source-identity correction invalidates the recorded hierarchy.

New installed-state measurements do not automatically reopen the rigid benchmark/equation/authorization tasks; they advance the separate Level F layer.

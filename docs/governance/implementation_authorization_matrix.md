# Physics Implementation Authorization Matrix

**Status:** Active project control document  
**Default rule:** No legacy or proposed physics block is authorized for production implementation unless this matrix explicitly says so.

## 1. Authorization states

| State | Meaning |
|---|---|
| `not_authorized` | Documentation, definitions, evidence, or verification planning is incomplete. Production physics code must not begin. |
| `documentation_candidate` | The item is being documented and may receive equation/model cards, but implementation remains prohibited. |
| `benchmark_implementation_only` | A minimal implementation may reproduce a legacy or published result solely for regression/verification. It must not feed production analyses. |
| `prototype_authorized` | A bounded reference implementation may be developed behind an experimental interface after the stated gates pass. |
| `production_authorized` | The model is approved for stated design decisions and validity range. |
| `retired` | The item is preserved only for lineage or regression and cannot be used as active physics. |

Authorization is separate from disposition and maturity. A model can be physically defensible but not yet authorized because required parameter evidence or tests are missing.

## 2. Mandatory authorization packet

Before an item can move to `prototype_authorized`, it requires:

1. stable migration, quantity, equation, model, assumption, risk, and benchmark IDs as applicable;
2. reviewed definitions, frames, signs, units, and reference points;
3. complete source and derivation record;
4. explicit assumptions and validity envelope;
5. parameter authority and uncertainty path;
6. numerical method and failure behavior;
7. dimensional and limiting-case benchmarks;
8. independent or cross-tool verification plan;
9. result schema and provenance requirements;
10. reviewer approval recorded in the change history.

`production_authorized` additionally requires the maturity and physical/cross-tool evidence appropriate to the decision risk.

## 3. Current authorization matrix

| Item | Scope | Current state | Earliest allowable work | Blocking documentation/evidence | Intended first use |
|---|---|---|---|---|---|
| `MOD-STEER-0001` | Bounded rigid nominal-height steering evaluator | `prototype_authorized` under `AUTH-STEER-0001` | Maintain geometry schema, rigid closure, branch-controlled position solve, wheel-plane projection, diagnostics, and frozen tests | Installed transmission/stops and Level F evidence still block installed/as-built claims; higher-fidelity physics remains separate | Authoritative steering analyzer and verification backbone |
| `MOD-STEER-0002` | Role-driven nominal-height steering inverse-design orchestrator | `prototype_authorized` only after `AUTH-STEER-0002` review and merge | Role resolver and parametric geometry generator first; deterministic constrained search only after generator benchmarks pass | Must compose `MOD-STEER-0001`; target-recovery, infeasibility, repeatability, method, and candidate-report benchmarks remain open | Experimental geometry generation and constrained inverse design |
| `MOD-VEH-0001` | Explicit source-preserving vehicle/per-wheel operating-state exchange provider; no vehicle physics equations | `prototype_authorized` as a non-physics provider after `AUTH-VEH-0001` / PR #29 review and merge | Validate explicit states, missing-data boundaries, canonical sign conversion, wheel identity, and tire-interface readiness | Upstream load/camber/pressure/Fy authority remains separate; generated or production vehicle-state claims require their own reviewed models/evidence | Shared boundary for tire, steering, LLTD/QSS, telemetry, and later effort providers |
| `MOD-SUSP-0001` | Rigid ideal-joint double-wishbone position kinematics with front unresolved-steering reference and rear chassis toe-link closure | `prototype_authorized` only after `AUTH-SUSP-0001` / PR #39 review and merge | Implement `EQ-SUSP-0001` through `0004` behind the frozen geometry contract and pass `BENCH-SUSP-0001` through `0003` | Wheel-center/wheel-plane construction, whole-vehicle rear origin, actuation linkage, loads/compliance, installed correlation, and production authority remain separate gates | Native suspension kinematics and canonical zero-steer upright-pose provider for steering |
| `MIG-STR-0001` | Steering geometry and tie-rod inverse-design workflow | `prototype_authorized` within `AUTH-STEER-0002` after merge | Requirement roles, candidate generator, target provider, constrained search, candidate set, and diagnostics within the authorized sequence | Hardware-feasible and production ranking still require packaging, articulation, manufacturing, robustness, and later physical evidence | First complete steering calculator replacement vertical slice |
| `EQ-STEER-0001` through `0007` | Ackermann reference, rigid closure/position, transmission staging, ratios, radius, and error | `prototype_authorized` only within `AUTH-STEER-0001`; the optimizer calls these through `MOD-STEER-0001` | Implement and maintain the exact documented functions and frozen tests | WUFR-specific derived outputs return unavailable when prerequisites are absent | Fundamental analyzer functions; no duplicate optimizer equations |
| `EQ-SUSP-0001` through `0004` | Rigid A-arm rotation, upright closure, zero-steer reference transport, and rear chassis toe-link twist closure | `prototype_authorized` only within `AUTH-SUSP-0001` after PR #39 merge | Implement exactly the frozen equations, branch rules, residuals, and structured failures | Wheel-center semantics, actuation kinematics, physical joint limits, whole-vehicle placement, and installed validation remain excluded | Fundamental rigid suspension position solver |
| `EQ-STEER-0010` through `0015` | Tire effort/compliance/tire-informed optimization | `not_authorized` | Literature/model planning and provider-interface design only | Canonical tire, load, compliance, and steering-force models | Later steering fidelity layers |
| `MIG-SC26-LT-001` / `EQ-MASS-0001` | Static mass distribution | `documentation_candidate` | Equation card and hand benchmark | Resolve mass/weight naming, CG source, vehicle configuration | Fundamental benchmark and future core calculation |
| `MIG-SC26-LT-002` / `EQ-LOAD-0090` | Legacy fixed-coefficient transfer method | `benchmark_implementation_only` after benchmark card approval | Exact reproduction test only | Freeze source cells, inputs, outputs, and intentional limitations | Regression and migration comparison |
| `EQ-LOAD-0001` through `0006` | Canonical longitudinal/lateral transfer and wheel loads | `not_authorized` | Derivations, quantity mapping, benchmark planning | Separate total/geometric/elastic/unsprung/aero terms; resolve parameters | Future fundamental core model |
| `MIG-SC26-LT-003` / `EQ-AERO-0001` | Fixed/simple aero load | `not_authorized` | Documentation only | Coefficient signs, references, map state, force application | Future low-fidelity aero adapter |
| `MIG-LLTD-RIG-*` / `MOD-ROLL-0001` | Rigid linear elastic roll baseline | `documentation_candidate` | Equation cards and independent hand cases | Freeze motion ratio, tire stiffness, ARB and elastic-LLTD definitions | Named restricted benchmark model |
| `MIG-LLTD-COMP-001` / `EQ-CHASSIS-0090` | Independent series chassis placeholder | `retired` except regression | Exact legacy reproduction only | None for active use; replacement required | Intentional-disagreement regression |
| `EQ-CHASSIS-0001` / `MOD-CHASSIS-0001` | Coupled front-chassis-rear torsional model | `not_authorized` | Derivation and benchmark planning | Plane definitions, installed stiffness evidence, compatibility equations | Future first-mode compliance model |
| `MIG-SC26-PITCH-001` / `EQ-PITCH-0001` | Linear static pitch baseline | `documentation_candidate` | Independent derivation and limiting tests | Reconcile geometry, sign, tire stiffness, motion ratio | Restricted educational benchmark |
| `MIG-SC26-PITCH-002` / `EQ-PITCH-0002` | Load-transfer pitch addition | `not_authorized` | Documentation only | Complete derivation and parameter authority | Future reduced pitch model input |
| `MIG-SC26-ALIGN-*` / `EQ-ALIGN-*` | Alignment measurement conversion | `not_authorized` | Procedure and synthetic benchmark design | Fixture geometry, corrected trigonometry, calibration, uncertainty | Future setup/calibration tool |
| `MIG-SC26-TIRE-001` / `EQ-TIRE-0001` | Historical cornering-stiffness fit | `documentation_candidate` | Source recovery and fit-reproduction benchmark | Tire dataset/script, units, conditions, residuals, fit envelope | Historical benchmark only unless applicability is proven |
| Future canonical tire model | Tire force/moment API | `not_authorized` | Interface and evidence planning | Current tire data, signs, interpolation, combined slip, uncertainty | Core quasi-static and transient analyses |
| `MIG-SC26-FD-001/003` / `EQ-FORCE-0001` | Analytical longitudinal force-distribution boundaries | `documentation_candidate` | Equation card and hand benchmark | Clarify requested versus achieved force and assumptions | Benchmark/design education |
| `MIG-SC26-FD-002` / `MOD-BRAKE-0001` | Aero/tire/actuator constrained distribution | `not_authorized` | Scenario and model planning | Canonical tire, load, brakes, aero, combined slip | Future braking/acceleration workflow |
| `MIG-SC26-US-002` | Explicitly rejected understeer block | `retired` | Reproduction only if needed to explain prior results | Preserve rejection rationale | No active use |
| `MIG-SC26-US-001/003/004/005/006/007/008` | Handling and understeer variants | `not_authorized` | Separate definition and equation cards | Split metrics; recover tire fits and model assumptions | Future handling/understeer budget |
| `MIG-SC26-SF-*` | Steering-force contributions | `not_authorized` | Free-body and sign documentation | Trusted tire/load states and steering geometry | Future effort and component-load model |
| `MIG-SC26-SCF-*` | Column, gear, bearing loads | `not_authorized` | Structural benchmark planning | Trusted upstream rack force; re-derived FBDs and supports | Future component structural loads |
| `MIG-LLTD-RAW-*` / `MOD-DATA-0001` | Raw-data lineage and selection masks | `documentation_candidate` | Data schema and immutable-lineage planning | Recover raw file, channel metadata, reason codes | Physical-data backbone |
| `MIG-LLTD-DER-*` / `EQ-MEAS-*` | Wheel travel, body plane, twist, LLTD proxies | `not_authorized` | Measurement-model and calibration documentation | Sensor poses/calibration, kinematic maps, identifiability, uncertainty | Future parameter identification and validation |
| `MIG-LLTD-SUM-*` / `EQ-ID-*` | Regression and correlation reports | `not_authorized` | Statistical/report schema planning | Dataset roles, holdout, weighting, confidence, residuals | Future validation report |
| `MIG-SC26-ARB-001`, `MIG-SC26-NF-001`, `MIG-SC26-UNK-001` | Missing/unknown source pointers | `not_authorized` | Source search only | Recover artifact or formally deprecate | None until identified |
| `MIG-SC26-BEAM-001` | Empty sheet | `retired` | None | None | No replacement dependency |

## 4. Steering transition gates

### 4.1 Authoritative analyzer gate

The following remain accepted under `AUTH-STEER-0001`:

- rigid nominal-height scope;
- body, rack, steering-axis, joint, angle, side, and reference-state definitions;
- exact equation/function packet `EQ-STEER-0001` through `0007`;
- `GEO-STEER-BASIC-001` analytical/synthetic expectations;
- branch, singularity, infeasibility, provenance, and failure semantics;
- frozen WUFR-26/27 nominal geometry and descriptive Level E comparison.

`MOD-STEER-0001` remains the only steering-kinematics evaluator. Optimizer code may not duplicate or replace its mechanism or derived-metric functions.

### 4.2 First inverse-design gate

`AUTH-STEER-0002` permits a phased prototype after review and merge:

1. role resolver and parametric geometry generator;
2. zero-offset reconstruction of `WUFR27_STEERING_BASELINE_V0` through the public analyzer contract;
3. frozen synthetic and historical target-recovery fixtures;
4. deterministic constrained search with explicit scaling, initialization, tolerances, failure behavior, and repeatability;
5. hard infeasibility separated from objective values;
6. multiple feasible or nondominated candidates with transparent ranking and complete analyzer diagnostics.

The first optimizer fixes steering axes, upright poses, suspension hardpoints, wheel centers, static alignment, and rack-axis direction. Exact left/right reflection is enforced. Rack location, inner-joint half-spacing, and upright-local outer-pickup coordinates are role-selectable variables; outer-pickup depth is tightly bounded.

### 4.3 Higher-fidelity gates that remain open

The following do not block generic nominal optimizer development, but they do block the named higher-use claims:

- installed stops, transmission, and Level F sweeps for installed/as-built WUFR claims;
- reviewed articulation, thread engagement, clearance, stop, and manufacturing evidence for hardware-feasible ranking;
- a reviewed suspension-pose provider for bump-steer or travel-state optimization;
- `MOD-VEH-0001` provides the explicit vehicle-state exchange boundary, but reviewed generated/production wheel-load, camber, pressure, and force-demand authority remains required for production-relevant tire-informed targets;
- reviewed load and steering-effort models for effort optimization;
- reviewed tolerance and uncertainty models for robustness claims;
- later focused authorization for WUFR-28 production geometry selection.

Ideal Ackermann remains a reference or selectable target, not a universal performance objective. No open gate may be silently replaced by a spreadsheet value, polynomial fit, symmetry assumption outside its named configuration, or CAD-only agreement.

## 5. Suspension transition gate

After PR #39 merge, `AUTH-SUSP-0001` permits only the first rigid position-kinematics prototype:

1. rotate each A-arm outboard joint about its fixed fore-to-aft inboard hinge axis;
2. use lower-arm rotation `q_L` as the first internal independent coordinate;
3. solve upper-arm rotation from invariant upright joint separation on the nominal-continuation branch;
4. generate a shortest-rotation zero-extra-twist upright reference transform;
5. keep front steering twist unresolved and pass that reference to `MOD-STEER-0001`;
6. close rear upright twist only where the frozen link role is `chassis_locating_toe_link`;
7. pass the analytical synthetic, WUFR front OptimumK, and synthetic rear-toe benchmarks before implementation is considered complete.

`q_L` is not yet a public wheel-travel quantity. Wheel center/wheel plane, actuation linkage, roll center, anti-geometry, forces, compliance, joint limits, packaging, and whole-vehicle rear placement remain separate authorization problems.

## 6. Literature and method control

Physics equations remain tied to the existing equation records and their vehicle-dynamics sources. Optimizer-specific numerical methods must record the algorithm source, package and version where applicable, variable and constraint scaling, initialization, stopping criteria, deterministic seed behavior, and benchmark comparison. Learned or reinforcement-learning methods remain research candidates until a deterministic baseline and fair comparison burden exist.

## 7. Change-control rule

Any authorization-state change requires a focused pull request that lists:

- affected stable IDs;
- completed gate evidence;
- unresolved restrictions;
- benchmark results;
- reviewer decision;
- permitted use and prohibited use;
- whether re-correlation is required for downstream results.

Silence, age, prior competition use, or plausible output never upgrades authorization.

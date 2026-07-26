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
| `MOD-VEH-0002` | Explicit planar wheel-velocity and signed tire-slip kinematics from externally supplied `u`, `v`, and `r` | `prototype_authorized` under `AUTH-VEH-0002`; implementation merged in PR #33 | Maintain exact wheel-center velocity, velocity-heading, slip, and required-heading functions with source/frame diagnostics | Prediction of body motion, equilibrium, tire force, wheel loads, and production motion authority remain separate | Kinematic consumer of future QSS/telemetry/multibody body-motion states |
| `MOD-VEH-0003` | Whole-vehicle body/road point transport, wrench assembly, virtual-work generalized-force mapping, rigid four-contact classification, and reviewed WUFR design-intent frame adapter | `prototype_authorized` under `AUTH-VEH-0003`; implementation in PR #46 | Maintain `EQ-VEH-0004` through `0007`, exact frame/origin/application-point contracts, `BENCH-VEH-0003` through `0004`, and source-separated WUFR adapter provenance | Spring/ARB/tire/aero/brake/gravity force laws, exact same-session driver z-CG, total/sprung mass force authority, per-corner unsprung allocation, equilibrium, linkage loads, alternate contact modes, installed evidence, and production authority remain separate | Mechanics foundation for later spring/ARB providers, prescribed-force QSS, and ideal linkage statics |
| `MOD-SUSP-0001` | Rigid ideal-joint double-wishbone position kinematics with front unresolved-steering reference and rear chassis toe-link closure | `prototype_authorized` under `AUTH-SUSP-0001`; implementation merged in PR #40 | Maintain `EQ-SUSP-0001` through `0004`, branch/failure diagnostics, and `BENCH-SUSP-0001` through `0003` | Wheel reference/state adapters, whole-vehicle rear origin, actuation linkage, loads/compliance, installed correlation, and production authority remain separate gates | Native suspension kinematics and canonical zero-steer upright-pose provider for steering |
| `MOD-SUSP-0002` | WUFR source-bounded wheel-center/wheel-plane reference, rigid upright transport, body-frame wheel-center vertical-state inversion, and historical source-steering removal | `prototype_authorized` only after `AUTH-SUSP-0002` review and merge | Implement `EQ-SUSP-0005` through `0008` by composing `MOD-SUSP-0001`; pass `BENCH-SUSP-0004` through `0006` | Nonzero OptimumK wheel-offset semantics, generic contact/tire geometry, whole-vehicle source-origin placement, actuation linkage, installed metrology, and production authority remain separate | Physical wheel-state provider for suspension/steering integration and source correlation |
| `MOD-SUSP-0003` | WUFR source-bounded rigid push/pull-rod, one-axis rocker, ideal coilover-displacement, and signed local actuation-derivative kinematics | `prototype_authorized` under `AUTH-SUSP-0003`; implementation in PR #44 | Maintain `EQ-SUSP-0009` through `0012`, branch/failure diagnostics, and `BENCH-SUSP-0007` through `0008` | Spring/damper force laws, wheel rate/damping, ARB coupling, loads/compliance, installed stroke/stops, packaging, correlation, and production authority remain separate | Ideal actuation-state provider for later suspension R&D |
| `MIG-STR-0001` | Steering geometry and tie-rod inverse-design workflow | `prototype_authorized` within `AUTH-STEER-0002` after merge | Requirement roles, candidate generator, target provider, constrained search, candidate set, and diagnostics within the authorized sequence | Hardware-feasible and production ranking still require packaging, articulation, manufacturing, robustness, and later physical evidence | First complete steering calculator replacement vertical slice |
| `EQ-STEER-0001` through `0007` | Ackermann reference, rigid closure/position, transmission staging, ratios, radius, and error | `prototype_authorized` only within `AUTH-STEER-0001`; the optimizer calls these through `MOD-STEER-0001` | Implement and maintain the exact documented functions and frozen tests | WUFR-specific derived outputs return unavailable when prerequisites are absent | Fundamental analyzer functions; no duplicate optimizer equations |
| `EQ-VEH-0001` through `0003` | Planar wheel-center velocity, signed tire slip/required heading, and velocity-center diagnostics | `prototype_authorized` only within `AUTH-VEH-0002`; implementation merged in PR #33 | Maintain explicit externally supplied body-motion and wheel-center-geometry contracts | No prediction of `u`, `v`, `r`, equilibrium, load transfer, tire force, or suspension motion | Shared planar kinematic adapter for downstream motion-aware consumers |
| `EQ-VEH-0004` through `0007` | Body-fixed point transport, point-force wrench translation, virtual-work generalized force, and rigid flat-road contact admissibility | `prototype_authorized` within `AUTH-VEH-0003`; implementation in PR #46 | Maintain exact frame/origin/application-point contracts, analytical/numerical generalized-force agreement, rigid-contact classifications, and structured failures | No constitutive force law, equilibrium solve, negative-load clipping, tire vertical compliance, alternate contact mode, linkage forces, stress, or installed authority | Common force-coordinate interface for later QSS and structural load paths |
| `EQ-SUSP-0001` through `0004` | Rigid A-arm rotation, upright closure, zero-steer reference transport, and rear chassis toe-link twist closure | `prototype_authorized` within `AUTH-SUSP-0001`; implementation merged in PR #40 | Maintain the exact equations, branch rules, residuals, and structured failures | Wheel reference/state semantics, actuation kinematics, physical joint limits, whole-vehicle placement, and installed validation remain excluded | Fundamental rigid suspension position solver |
| `EQ-SUSP-0005` through `0008` | Source-bounded nominal wheel reference, rigid transport, physical vertical-state inversion, and 3D OptimumK source-steering removal | `prototype_authorized` only within `AUTH-SUSP-0002` after review/merge | Implement only behind the frozen source/zero-offset boundary and compose `MOD-SUSP-0001` | Nonzero source offsets, generic contact patch/tire model, front steering solve, whole-vehicle source placement, actuation and installed validation remain excluded | Wheel/upright state adapter and external-source correlation |
| `EQ-SUSP-0009` through `0012` | Arm-fixed actuation-pickup transport, one-axis rocker closure, ideal coilover displacement, and signed local damper-over-wheel displacement derivative | `prototype_authorized` only within `AUTH-SUSP-0003` | Compose `MOD-SUSP-0001`/`MOD-SUSP-0002`, retain source attachment roles and nominal branch, and preserve structured closure/derivative failures | No constitutive force law, wheel/ride rate, damping, ARB, load transfer, compliance, installed limits, packaging, or optimization authority | Fundamental rigid actuation kinematics and downstream geometry-state interface |
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

## 5. Whole-vehicle force-coordinate transition gate

`AUTH-VEH-0003`, after PR #45 review and merge, authorizes only the bounded common mechanics foundation. PR #46 implements that foundation without expanding its physics scope:

1. preserve one explicit right-handed whole-vehicle body frame and explicit compatible road/inertial frame descriptions;
2. transport body-fixed application/contact-reference points with `EQ-VEH-0004` and reject missing source-origin transforms;
3. translate and sum forces/free couples about named reference points with `EQ-VEH-0005`;
4. map applied actions into signed generalized forces with `EQ-VEH-0006` and declared coordinate order, units, Jacobian method, steps, and convergence diagnostics;
5. classify only the flat-road, vertically rigid, all-four-active contact mode with `EQ-VEH-0007`;
6. report any negative normal reaction as wheel lift/contact-mode invalidity, retain the negative value, and never clip it;
7. retain WUFR-27 inheritance of WUFR-26 suspension geometry without treating wheelbase alone as a common front/rear/CG origin transform;
8. permit the separately reviewed PR #46 WUFR design-intent adapter because it freezes explicit CAD axle/track references, the named driver/no-fuel planar scale state, the separately sourced `0.290 m` driver-equivalent-ballast tilt value, the no-driver/no-fuel planar scale state, source/configuration identity, and authority boundaries;
9. keep the primary driver/no-fuel 3D reference explicitly source-separated rather than same-session metrology, and leave the no-driver/no-fuel `z_CG` unavailable;
10. retain the reported `10 kg` front-axle and `10 kg` rear-axle unsprung masses only as future mass-model evidence, with no per-corner split or force-generation authority inferred;
11. retain ideal two-force-member linkage statics as a downstream fidelity decision only, with no linkage-force or stress output in `MOD-VEH-0003`;
12. maintain `BENCH-VEH-0003` and `BENCH-VEH-0004` as implementation gates.

Spring/damper/ARB/tire/aero/brake/gravity constitutive forces, total/sprung mass force authority, per-corner unsprung allocation, four-corner wheel-load generation, heave/roll/pitch equilibrium, alternate contact modes, tire vertical compliance, linkage/member/bearing reactions, stress/FEA, compliance, installed limits, and production optimization remain separate authorization problems.

The measured static corner-weight diagonal split is not reproduced by `MOD-VEH-0003`: rigid-body vertical force/roll/pitch equilibrium alone does not uniquely close four vertical reactions. Spring/preload/ARB/ride-height compatibility remains a later force/equilibrium gate.

## 6. Suspension transition gate

`AUTH-SUSP-0001` permits the implemented rigid position-kinematics prototype:

1. rotate each A-arm outboard joint about its fixed fore-to-aft inboard hinge axis;
2. use lower-arm rotation `q_L` as the first internal independent coordinate;
3. solve upper-arm rotation from invariant upright joint separation on the nominal-continuation branch;
4. generate a shortest-rotation zero-extra-twist upright reference transform;
5. keep front steering twist unresolved and pass that reference to `MOD-STEER-0001`;
6. close rear upright twist only where the frozen link role is `chassis_locating_toe_link`;
7. maintain the analytical synthetic, WUFR front OptimumK, and synthetic rear-toe benchmarks merged in PR #40.

`AUTH-SUSP-0002`, after review and merge, permits only the next wheel-reference/state-adapter prototype:

1. reconstruct the frozen zero-offset WUFR nominal wheel center from source half-track, tire radius, side, and static camber;
2. reuse the reviewed static toe/camber wheel-plane convention rather than create a second alignment sign system;
3. transport wheel center and wheel-plane basis rigidly with the `MOD-SUSP-0001` upright transform, preserving unresolved front steering;
4. expose body-frame wheel-center vertical displacement as the first physical suspension-state coordinate and invert it to `q_L` with a bounded nominal-branch solve;
5. remove historical OptimumK front source steering for validation using three-dimensional upright tie-point twist rather than the scalar `Steer Angle` channel;
6. pass `BENCH-SUSP-0004` through `BENCH-SUSP-0006` before implementation is considered complete.

`AUTH-SUSP-0003`, after PR #43 review and merge, permits only the bounded rigid actuation prototype:

1. transport the front push/pull attachment with the solved upper A-arm and the rear attachment with the solved lower A-arm;
2. solve one-axis rocker rotation from invariant push/pull-rod length on the continuation branch connected to nominal `theta_R=0`;
3. rotate the rocker rod and coilover points with the same transform and report closure residual, candidate-root, and failure diagnostics;
4. report ideal coilover eye-to-eye displacement as current length minus nominal length, positive in extension;
5. expose only the signed local `rho_dw=d(delta_L_d)/d(delta_z_wc_body)` in the `MOD-SUSP-0002` physical wheel coordinate, with a conditioned reciprocal when available;
6. preserve historical OptimumK `Motion Ratio Heave` as comparison-only evidence and pass `BENCH-SUSP-0007` through `BENCH-SUSP-0008` before implementation merge.

Nonzero OptimumK wheel-offset semantics, generic tire/contact geometry beyond `AUTH-VEH-0003`, roll center/anti geometry, spring/damper forces, wheel rate/damping, anti-roll-bar coupling, load transfer/equilibrium, compliance, physical joint limits, packaging, installed/as-built validation, and production optimization remain separate authorization problems.

## 7. Literature and method control

Physics equations remain tied to the existing equation records and their vehicle-dynamics sources. Optimizer-specific numerical methods must record the algorithm source, package and version where applicable, variable and constraint scaling, initialization, stopping criteria, deterministic seed behavior, and benchmark comparison. Learned or reinforcement-learning methods remain research candidates until a deterministic baseline and fair comparison burden exist.

## 8. Change-control rule

Any authorization-state change requires a focused pull request that lists:

- affected stable IDs;
- completed gate evidence;
- unresolved restrictions;
- benchmark results;
- reviewer decision;
- permitted use and prohibited use;
- whether re-correlation is required for downstream results.

Silence, age, prior competition use, or plausible output never upgrades authorization.

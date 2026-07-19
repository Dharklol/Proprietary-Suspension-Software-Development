# Equation-Card and Benchmark Backlog

**Status:** Initial Phase 0 planning  
**Authority:** Proposed IDs and review sequence; equations are not accepted by appearing in this backlog

## 1. Equation-card minimum content

Every equation card must contain:

- stable equation ID and title;
- output quantity IDs;
- input quantity IDs;
- equation in canonical symbols and units;
- derivation or source with edition, chapter/section, and page;
- coordinate frame, reference point, sign, and force-direction convention;
- assumptions and neglected effects;
- validity envelope;
- parameter authority requirements;
- numerical evaluation or solver method;
- derivative/Jacobian requirements where applicable;
- failure and extrapolation behavior;
- migration block IDs;
- benchmark IDs;
- dependent and replacement model IDs;
- five-layer review status;
- maturity and implementation authorization.

## 2. Benchmark-card minimum content

Every benchmark must contain:

- stable benchmark ID;
- target equation/model/migration IDs;
- verification level A through F;
- exact inputs and initial state;
- expected output and tolerance;
- source or independent derivation;
- units, frames, and sign conventions;
- interpretation of failure;
- whether the result verifies algebra, implementation, model form, or physical correlation;
- software/environment revision;
- frozen evidence hashes where applicable.

## 3. Priority 1 — steering inverse-design vertical slice

| Proposed equation/model ID | Scope | Primary migration blocks | Initial benchmark plan | Gate before implementation |
|---|---|---|---|---|
| `EQ-STEER-0001` | Ideal low-speed Ackermann relation using wheelbase and steering-axis track | `MIG-SC26-ACK-001`, `MIG-STR-0001` | `BENCH-STEER-0002`: analytical inside/outside angle pairs at selected radii | Freeze track and angle definitions |
| `EQ-STEER-0002` | Rigid tie-rod length/constraint closure at the reference configuration | `MIG-STR-0001` | `BENCH-STEER-0003`: exact link-length closure and zero-input toe | Recover joint-center geometry and tie-rod definition |
| `EQ-STEER-0003` | Steering-linkage position solution over rack displacement | `MIG-STR-0001`, `MIG-SC26-SR-001/003` | `BENCH-STEER-0004`: left/right mirror, branch continuity, singularity detection | Select reviewed planar or spatial mechanism fidelity |
| `EQ-STEER-0004` | Steering-wheel/pinion/rack transmission relation | `MIG-STR-0001` | `BENCH-STEER-0005`: unit and ratio-chain identity tests | Recover `C-factor` and transmission definitions |
| `EQ-STEER-0005` | Local and secant steering-ratio functions | `MIG-SC26-SR-002/004`, `MIG-STR-0001` | `BENCH-STEER-0006`: derivative versus finite difference and direct-map comparison | Freeze input/output ratio definitions |
| `EQ-STEER-0006` | Kinematic turning-radius calculation | `MIG-SC26-ACK-001`, `MIG-STR-0001` | `BENCH-STEER-0007`: ideal Ackermann radius reconstruction | Define radius reference point and tire-path convention |
| `EQ-STEER-0007` | Ackermann error metric over a steering sweep | `MIG-SC26-ACK-003`, `MIG-STR-0001` | `BENCH-STEER-0008`: zero error for ideal reference and explicit error sign | Freeze metric definition; percentage remains secondary/report-only |
| `MOD-STEER-0001` | Rigid steering-linkage inverse-design workflow | `MIG-STR-0001` | Existing `BENCH-STEER-0001` CAD comparison plus `BENCH-STEER-0002` through `0008` | Complete source recovery, requirement-role classification, output schema, and failure reporting |

Later steering equation cards, not authorized in the first release:

- `EQ-STEER-0010`: steering-axis moment from tire forces and moments;
- `EQ-STEER-0011`: rack force from left/right tie-rod force paths;
- `EQ-STEER-0012`: steering-column torsional compliance;
- `EQ-STEER-0013`: backlash/friction/hysteresis model;
- `EQ-STEER-0014`: tire-informed inner/outer target generation;
- `EQ-STEER-0015`: robust geometry objective under tolerances and compliance.

## 4. Priority 2 — mass, load transfer, and wheel-load assembly

| Proposed equation ID | Scope | Migration blocks | Benchmark plan | Key restriction |
|---|---|---|---|---|
| `EQ-MASS-0001` | Static axle/corner load from total mass and CG | `MIG-SC26-LT-001`, `MIG-SC26-VAR-001` | `BENCH-MASS-0001`: force and moment closure; symmetric limit | Static level-road rigid-body equilibrium |
| `EQ-LOAD-0001` | Total longitudinal load transfer | `MIG-SC26-LT-002/004`, `MIG-SC26-FD-001` | `BENCH-LOAD-0001`: zero-CG-height and zero-acceleration limits | Separate total transfer from suspension pitch response |
| `EQ-LOAD-0002` | Total lateral load transfer required by equilibrium | `MIG-SC26-LT-002/004` | `BENCH-LOAD-0002`: symmetric-track and zero-CG-height limits | Does not determine front/rear distribution by itself |
| `EQ-LOAD-0003` | Geometric lateral load-transfer contribution | `MIG-SC26-LT-004` | `BENCH-LOAD-0003`: roll-reference height to zero-road-plane limit | Requires reviewed force-path definition |
| `EQ-LOAD-0004` | Elastic lateral load-transfer contribution | `MIG-SC26-LT-004`, `MIG-LLTD-RIG-*` | `BENCH-LOAD-0004`: stiffness-distribution limiting cases | Distinguish elastic from total LLTD |
| `EQ-LOAD-0005` | Unsprung lateral load-transfer contribution | Missing/implicit legacy content | `BENCH-LOAD-0005`: zero-unsprung-mass limit | Requires unsprung mass and force-path data |
| `EQ-AERO-0001` | Aero force and moment from coefficients/map | `MIG-SC26-LT-003` | `BENCH-AERO-0001`: zero-speed and coefficient-sign tests | First version may be fixed-map but must expose applicability |
| `EQ-LOAD-0006` | Four-corner normal-force assembly | `MIG-SC26-LT-004`, force-distribution sheets | `BENCH-LOAD-0006`: sum/moment closure and no-negative-load detection | Must report wheel lift and invalid states |

The fixed magic-number/fudge-factor block receives a legacy reproduction equation ID only if needed for regression:

- `EQ-LOAD-0090`: retired fixed-coefficient front transfer distribution;
- `BENCH-LOAD-0090`: reproduce workbook output exactly;
- disposition: benchmark-only/retired, never canonical physics.

## 5. Priority 3 — rigid elastic roll and chassis compliance

| Proposed equation/model ID | Scope | Migration blocks | Benchmark plan | Gate |
|---|---|---|---|---|
| `EQ-ROLL-0001` | Installed wheel rate from spring rate and explicit motion ratio | `MIG-LLTD-RIG-001` | `BENCH-ROLL-0001`: unit and inverse-ratio tests | Freeze motion-ratio convention |
| `EQ-ROLL-0002` | Axle spring roll stiffness from left/right wheel rates and geometry | `MIG-LLTD-RIG-002` | `BENCH-ROLL-0002`: equal-rate analytical case and track-scaling test | Define wheel displacement/roll kinematics |
| `EQ-ROLL-0003` | Tire vertical-compliance contribution to axle roll stiffness | `MIG-LLTD-RIG-002` | `BENCH-ROLL-0003`: rigid-tire and zero-tire-stiffness limits | Linear vertical tire assumption |
| `EQ-ROLL-0004` | Rigid-chassis total elastic roll stiffness and front elastic LLTD | `MIG-LLTD-RIG-003` | `BENCH-ROLL-0004`: front/rear stiffness fractions and infinite stiffness limits | Name outputs as elastic quantities |
| `EQ-ROLL-0005` | Small-angle roll gradient | `MIG-LLTD-RIG-003` | `BENCH-ROLL-0005`: zero roll-arm and stiffness-scaling limits | Uses stated sprung mass and roll arm |
| `EQ-CHASSIS-0001` | Coupled front-chassis-rear torsional equilibrium and compatibility | `MIG-LLTD-COMP-001` | `BENCH-CHASSIS-0001`: infinite chassis stiffness recovers rigid case; zero/low stiffness behavior | Replace independent-series placeholder |
| `MOD-ROLL-0001` | Named rigid linear elastic roll baseline | `MIG-LLTD-RIG-*` | Equation benchmarks above plus independent hand case | Restricted baseline, not total transient LLTD model |
| `MOD-CHASSIS-0001` | First-mode coupled chassis-compliance roll model | `MIG-LLTD-COMP-*` | `BENCH-CHASSIS-0001/0002` plus optional FEA/test comparison | Plane definitions and installed stiffness evidence |

Retired placeholder:

- `EQ-CHASSIS-0090`: independent axle/chassis series-softening formula;
- `BENCH-CHASSIS-0090`: exact workbook reproduction;
- purpose: preserve lineage and prove intentional disagreement with replacement.

## 6. Priority 4 — pitch, alignment, tire fits, and force distribution

| Proposed equation ID | Scope | Migration blocks | Benchmark plan | Status |
|---|---|---|---|---|
| `EQ-PITCH-0001` | Linear static pitch from front/rear vertical compliance | `MIG-SC26-PITCH-001` | `BENCH-PITCH-0001`: symmetric compliance and zero-moment limits | Restricted benchmark candidate |
| `EQ-PITCH-0002` | Pitch including longitudinal load-transfer force redistribution | `MIG-SC26-PITCH-002` | `BENCH-PITCH-0002`: independent derivation and dimensional check | Rewrite required |
| `EQ-ALIGN-0001` | String/bar measurement to per-wheel toe | `MIG-SC26-ALIGN-001/002` | `BENCH-ALIGN-0001`: synthetic fixture geometry with known toe | Correct legacy trigonometry and define fixture |
| `EQ-ALIGN-0002` | Tie-rod adjustment turns to toe change | `MIG-SC26-ALIGN-003` | `BENCH-ALIGN-0002`: measured adjustment fixture | Requires thread pitch and steering geometry |
| `EQ-TIRE-0001` | Historical cornering-stiffness fit versus normal load | `MIG-SC26-TIRE-001` | `BENCH-TIRE-0001`: reproduce source fit and residuals after recovery | Benchmark only until source recovered |
| `EQ-FORCE-0001` | Analytical longitudinal force-distribution boundary | `MIG-SC26-FD-001/003` | `BENCH-FORCE-0001`: textbook/hand derivation | Does not represent full optimum without tire/actuator model |
| `MOD-BRAKE-0001` | Four-corner tire/actuator constrained force-distribution workflow | `MIG-SC26-FD-*` | Future equilibrium and lock-order benchmarks | Later implementation after tire/load model |

## 7. Priority 5 — telemetry measurement and identification equations

These cards document the measurement chain before model calibration.

| Proposed equation/model ID | Scope | Migration blocks | Benchmark plan | Main circularity control |
|---|---|---|---|---|
| `EQ-MEAS-0001` | Damper-pot electrical/physical calibration | `MIG-LLTD-IN-002`, `MIG-LLTD-DER-001` | `BENCH-MEAS-0001`: calibration-fixture residual and repeatability | Independent calibration data |
| `EQ-MEAS-0002` | Suspension sensor to wheel-travel kinematic map | `MIG-LLTD-DER-001/004` | `BENCH-MEAS-0002`: CAD/fixture comparison through travel | Do not use constant ratio outside validated range |
| `EQ-MEAS-0003` | Four-corner ride-height plane fit for heave/pitch/roll | `MIG-LLTD-DER-002/003` | `BENCH-MEAS-0003`: synthetic plane and sensor-noise tests | Residual is not automatically chassis twist |
| `EQ-MEAS-0004` | Front/rear body-plane difference research channel | `MIG-LLTD-DER-003` | `BENCH-MEAS-0004`: structural/road-plane synthetic cases | Keep research label until identifiable |
| `EQ-ID-0001` | Linear gradient regression with uncertainty and residual diagnostics | `MIG-LLTD-SUM-002` | `BENCH-ID-0001`: synthetic slope/intercept/noise and outlier cases | Holdout and weighting declared |
| `EQ-ID-0002` | Model-assisted roll-moment/LLTD proxy | `MIG-LLTD-DER-005` | `BENCH-ID-0002`: dependency tracing and sensitivity to assumed stiffness | Cannot validate the same stiffness independently |
| `MOD-DATA-0001` | Immutable raw-to-normalized-to-derived lineage | `MIG-LLTD-RAW-*` | `BENCH-DATA-0001`: hash/lineage and non-destructive annotation tests | Raw data never overwritten |

## 8. Priority 6 — handling and steering-force decomposition

These remain documentation and research until tire, load, steering geometry, and compliance interfaces are reviewed.

Proposed cards:

- `EQ-HAND-0001`: linear bicycle road-wheel steering gradient;
- `EQ-HAND-0002`: steering-wheel gradient including steering ratio/compliance;
- `EQ-HAND-0003`: yaw-rate gain;
- `EQ-HAND-0004`: neutral steer point/static margin;
- `EQ-HAND-0005`: local nonlinear sensitivity budget;
- `EQ-HAND-0006`: interaction residual for non-additive budget terms;
- `EQ-SFORCE-0001`: tire longitudinal-force steering-axis moment;
- `EQ-SFORCE-0002`: tire lateral-force steering-axis moment;
- `EQ-SFORCE-0003`: normal-force steering-axis moment;
- `EQ-SFORCE-0004`: aligning-moment contribution;
- `EQ-SFORCE-0005`: parked scrub/breakaway model;
- `EQ-COLUMN-0001`: rack-to-column torque relation;
- `EQ-COLUMN-0002`: miter-gear force model;
- `EQ-COLUMN-0003`: shaft-bearing reaction model.

Each understeer/handling quantity receives its own output definition. The old `Understeer Gradient` sheet must never become one monolithic equation card.

## 9. Literature concordance targets

Equation-level review should use at least:

- Guiggiani for wheel/tire kinematics, steering geometry, relative tire slips, vehicle equilibrium, suspension first-order analysis, and handling definitions;
- Pacejka for tire inputs, force/moment signs, load sensitivity, combined slip, and transient applicability;
- Gillespie for practical steering linkage, steering-system effects, load transfer, roll, pitch, and classical analytical decompositions;
- Milliken for race-car tire use, handling diagrams, setup sensitivity, and practical steering/force-distribution context;
- Deakin or equivalent chassis-stiffness literature for coupled roll-plane compatibility;
- exact team CAD/test sources for car-specific geometry and parameters.

No equation is accepted solely because it appears in one textbook or one external tool.

## 10. Documentation sequence for each card

1. Map legacy block inputs/outputs to candidate quantities.
2. Resolve definitions and conventions.
3. Recover source artifacts and parameter provenance.
4. Draft derivation and literature concordance.
5. Define analytical and limiting-case benchmarks.
6. Define independent/cross-tool/physical evidence plan.
7. Complete five-layer review.
8. Assign disposition and maturity.
9. Obtain implementation authorization.
10. Only then create production physics code.

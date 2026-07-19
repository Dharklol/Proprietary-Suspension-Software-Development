# Physics Implementation Authorization Matrix

**Status:** Active Phase 0 control document  
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
| `MIG-STR-0001` / `MOD-STEER-0001` | Rigid steering linkage inverse design | `documentation_candidate` | Equation cards, source recovery, benchmark extraction, UI/result schema design | Recover legacy optimizer/CAD sources; freeze C-factor, geometry, input/output, constraints, and benchmark curves | First calculator transition candidate |
| `EQ-STEER-0001` | Ideal low-speed Ackermann reference | `documentation_candidate` | Derivation and benchmark card | Freeze steering-axis track, wheelbase, angle and radius definitions | Benchmark/reference only |
| `EQ-STEER-0002` through `0007` | Link closure, sweep, ratio, radius, Ackermann error | `not_authorized` | Documentation and analytical fixtures | Complete geometry fidelity and convention review | Future steering prototype |
| `EQ-STEER-0010` through `0015` | Tire effort/compliance/tire-informed optimization | `not_authorized` | Literature/model planning only | Canonical tire, load, compliance, and steering-force models | Later steering fidelity layers |
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
| `MIG-LLTD-RAW-*` / `MOD-DATA-0001` | Raw-data lineage and selection masks | `documentation_candidate` | Data schema and immutable-lineage planning | Recover raw file, channel metadata, reason codes | Phase 5 data backbone |
| `MIG-LLTD-DER-*` / `EQ-MEAS-*` | Wheel travel, body plane, twist, LLTD proxies | `not_authorized` | Measurement-model and calibration documentation | Sensor poses/calibration, kinematic maps, identifiability, uncertainty | Future parameter identification and validation |
| `MIG-LLTD-SUM-*` / `EQ-ID-*` | Regression and correlation reports | `not_authorized` | Statistical/report schema planning | Dataset roles, holdout, weighting, confidence, residuals | Future validation report |
| `MIG-SC26-ARB-001`, `MIG-SC26-NF-001`, `MIG-SC26-UNK-001` | Missing/unknown source pointers | `not_authorized` | Source search only | Recover artifact or formally deprecate | None until identified |
| `MIG-SC26-BEAM-001` | Empty sheet | `retired` | None | None | No replacement dependency |

## 4. Steering first-transition gate

The steering inverse-design workflow may move to `prototype_authorized` only after all of the following are checked:

- legacy optimizer recovered or formally unavailable after documented search;
- CAD motion-study geometry and exports recovered and hashed;
- body, rack, steering-axis, wheel, and joint frames frozen;
- C-factor replaced by an explicit transmission quantity;
- steering-wheel, shaft, pinion, rack, left-wheel, and right-wheel quantities defined;
- tie-rod joint-center definition, adjustment range, and hardware limits documented;
- each input classified as fixed, design variable, discrete option, hard condition, acceptable band, target, or derived result;
- ideal Ackermann retained as reference/boundary, not universal performance objective;
- first-release rigid kinematic scope accepted;
- analytical, mirror, closure, monotonicity, singularity, turning-radius, ratio, and CAD-comparison benchmarks frozen;
- result provenance, solver diagnostics, failure states, and export schema reviewed.

Tire-informed, steering-effort, compliance, tolerance, and transient objectives remain required architectural extensions but do not block the bounded rigid first prototype as long as the interface and quantity meanings already accommodate them.

## 5. Change-control rule

Any authorization-state change requires a focused pull request that lists:

- affected stable IDs;
- completed gate evidence;
- unresolved restrictions;
- benchmark results;
- reviewer decision;
- permitted use and prohibited use;
- whether re-correlation is required for downstream results.

Silence, age, prior competition use, or plausible output never upgrades authorization.

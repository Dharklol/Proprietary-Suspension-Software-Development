# Phase 2 scope closure and transient entry v0.1.0

Program position: [G2–G4 in the master timeline](vehicle_dynamics_master_program_v0.1.0.md).
Owner direction: close scope and prioritize analytical transient development;
do not make a fully functional operational application a prerequisite.

## Scope disposition

This is an initial repository-backed coverage map. “Implemented ingredients”
does not mean that a complete, validated named calculation exists. Resolve each
row to a bounded implementation, a verified existing capability, or an explicit
defer with a successor milestone. Do not silently remove an original Phase 2 item.

| Original item | Existing capability / boundary | Disposition and next action |
|---|---|---|
| Static loads | Native gravity/static equilibrium and bounded reaction recovery | Reuse current reference cases; keep mass/setup assumptions visible |
| Longitudinal load transfer | Force-coordinate machinery exists; no general braking/acceleration service | Separate analytical reference slice; not required for first quarter-car |
| Lateral load transfer | Coupled steady-cornering reactions exist within development scope | Define total/geometric/elastic/unsprung comparison metrics separately; do not insert legacy LLTD shortcuts |
| Aero loads | No integrated aero-force provider | Retain as a separate Phase 2 calculation backlog item with explicit coefficients/application points |
| Wheel rates | Spring force/energy and actuation Jacobians exist | G3 priority: define complete local wheel-coordinate tangent, including geometric/preload terms where applicable |
| Roll stiffness | Coupled ARB mechanics and body equilibrium exist | G3/next vertical slice: define tangent matrix and heave/roll boundary conditions; distinguish component and effective axle/body quantities |
| Ride frequencies | No general named modal calculation | G3 priority: verified mass/stiffness eigenproblem and explicit modal definitions |
| Elastic LLTD | Relevant spring/ARB ingredients exist | Define a bounded diagnostic separately from total maneuver load-transfer distribution |
| Brake balance | No integrated brake/longitudinal tire calculation | Separate analytical reference slice; defer combined-slip vehicle prediction |
| Ackermann/steering ratio | Rigid steering evaluator and derived metrics exist | Reuse; distinguish descriptive geometry metrics from a handling objective |
| Steering torque/effort | Prescribed-load compliance/structural screens exist | Remains incomplete: source-backed tire moments and a consistent transmission/load path are required |
| Linear bicycle/understeer metrics | Manufactured low-force checks exist | General named reference calculation and precise metric conventions remain to be closed; useful entry for G5b |

G2 exit is a reviewed disposition for every row plus a fixed immediate batch.
It is not an assertion that all rows are implemented. Preserve incomplete rows
as tracked work after scope closure. Completing all unrelated Phase 2 calculations
is not a dependency of G4; completing its specific input and verification
contracts is.

## Immediate batch

| Work item | Concrete output | Verification / completion criterion |
|---|---|---|
| P2-T1: stiffness definitions | Wheel-coordinate force/tangent definitions, signs, held coordinates, local operating-point identity | Independent constant-ratio and changing-ratio/preloaded cases; compare force and energy derivatives without duplicating spring laws |
| P2-T2: modal reference | Explicit mass/stiffness inputs and mode/frequency reporting | Hand-solvable one/two-DOF systems, units, eigenpair residuals and stability/domain checks |
| TR-T1: transient parameter contract | Sprung/unsprung mass, suspension/vertical-tire stiffness, damper law, equilibrium reference, load/travel limits and road history | No silent values; separate manufactured, design-derived and measured inputs |
| TR-T2: quarter-car packet | Governing equations, state/output definitions, energy accounting, integrator/failure policy and independent cases | Meet documentation-before-implementation gate; record missing source parameters explicitly |
| TR-T3: bounded implementation | Deterministic free-response, smooth-bump and sinusoidal runs and exports | Analytical/independent linear references, dissipation and time-step convergence; no acceptance based solely on a solver finishing |

The first modal/stiffness fixtures can be manufactured and independent of the
native vehicle solver. Mapping native spring/ARB tangents into a reduced vehicle
model is a separately checked adapter. This prevents the full nonlinear native
composition from becoming the only reference for a reduced model built from it.

## Inputs and current blockers

No hardware measurements are needed for manufactured verification. Native ride
parameterization needs explicit vertical tire stiffness, mass allocation and
damper data/assumptions. The lateral R25B table supplies none of those vertical
properties. A linear manufactured damper is not a KW V5 calibration; gas force,
friction and asymmetric damping are separate extensions with separate evidence.

Pitch/yaw extensions need explicit relevant inertias. Total mass and CG location
alone do not supply those inertias. Start synthetic references while design/CAD
or manufacturer inputs are assembled; do not present assumed values as measured.

## Cross-check package and timeline discipline

Retain a small versioned reference configuration plus analytical expected values,
plots and machine-readable outputs for each new calculation. This is a developer
and engineering comparison package, not an operational product-release project.

Each work item above updates the master timeline checkpoint with: result,
independent checks, parameter/source status and next dependency. Broader UI,
telemetry collection and lap simulation remain outside this immediate batch.

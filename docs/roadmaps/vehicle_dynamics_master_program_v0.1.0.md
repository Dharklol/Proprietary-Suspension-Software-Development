# Vehicle-dynamics master program v0.1.0

## Direction and end goal

Owner direction, 2026-10-31: a fully functional operational release is not the
immediate priority. Close the original Phase 2 scope, develop reduced transient
models and deeper analytical calculations, and retain an overarching timeline
through individual development steps. Physical correlation waits for hardware;
analytical development does not. A reference calculation/report package is useful
for cross-checking and does not require a polished UI or full application release.

The end goal remains a source-traceable vehicle-dynamics engineering platform:
explicit configurations and geometry, verified fundamental calculations, coupled
loads and handling, standardized transient scenarios, comparisons/optimization,
and eventual calibration and physical validation. Scenario/lap simulation comes
after the reduced transient layer; QSS3 and learned methods are later capabilities.
External simulators are optional adapters, not mandatory hidden dependencies.

This is the program-level navigation and status record. Existing authorizations
and model-specific applicability limits remain in force. It does not authorize
new physical equations, select installed parameters, or promote development
evidence into validated vehicle predictions.

## Original phases and current position

These are the original program phases; later subsystem documents use their own
workstream numbering. Progress is uneven across phases, so no single completion
percentage is assigned.

| Phase | Goal | Current disposition |
|---|---|---|
| 0 | Physics/calculator audit and migration | Assurance process and selected subsystem audits established; broader migration remains open |
| 1 | Canonical schema and dependencies | Strong subsystem/source/result contracts; complete application/database not yet delivered |
| 2 | Verified fundamental calculation library | Substantial mechanics implemented; scope closure and missing reference calculations are current work; operational product release deferred |
| 3 | Geometry and load paths | Rigid kinematics, ideal linkage statics and bounded static exchange exist; maneuver-to-component loading and higher fidelity remain incomplete |
| 4 | Nonlinear four-corner equilibrium | Static and uncorrelated pure-lateral steady-cornering development paths exist; general acceleration/braking/aero/contact modes remain incomplete |
| 5 | Telemetry and calibration | Measurement scaffolding exists; data collection/correlation deferred until suitable hardware/data |
| 6 | Reduced transient models | Next physics program, beginning with explicit stiffness/mass/damping contracts and a manufactured quarter-car |
| 7 | Standardized scenarios and lap simulation | Scenario definitions can be prepared early; integrated/lap execution follows verified transient/subsystem capability; QSS3 later |
| 8 | Advanced optimization and learned methods | Bounded steering optimization exists; general vehicle optimization/learned methods remain later work |

## Milestone timeline

The order below is a dependency plan, not a calendar commitment. Each milestone
needs its stated exit evidence. Scope closure means every original item has an
explicit disposition; it does not mean every item is implemented or released.

| ID | Milestone | State | Exit evidence / next dependency |
|---|---|---|---|
| G0 | Assurance, subsystem mechanics and steady-state integration | Implemented in bounded scopes | Preserve current provider boundaries and verification |
| G1 | Analytical audit/envelope and first controlled comparison | Implemented; PR 121 ready/unmerged at this snapshot | Source-bound cases, retained failures and repeatable evidence; not design-ranking authority |
| G2 | Original Phase 2 coverage and scope closure | Current | Every item in the scope checklist has an implementation/evidence/defer disposition and a named successor |
| G3 | Transient prerequisite calculations and contracts | Next | Explicit local stiffness/mass/damping/tire-vertical inputs, independently checked modes/frequencies and source labels |
| G4 | Manufactured 2-DOF quarter-car transient | Next after its prerequisites | Independent analytical references, energy checks, time-step convergence, visible domain/contact failure |
| G5a | Half-car heave/pitch and axle road-delay response | After G4 | Explicit pitch inertia and front/rear parameters; modal and symmetry/decoupling checks |
| G5b | Reduced lateral sideslip/yaw transient | Parallel branch after its own prerequisite review | Explicit yaw inertia and tire-force/stiffness inputs; step-steer and steady-state limiting checks |
| G6 | Four-corner body/unsprung transient and compatible load propagation | Later | Reviewed roll/pitch/inertia/ARB/damper composition and complete case-specific wrenches |
| G7 | Standardized maneuver comparisons and expanded engineering workbench | Incremental alongside verified models | Reusable case schedules and comparable run/result identities; UI consumes the same engine |
| G8 | Integrated scenario/lap capability, including later QSS3 | After subsystem/transient readiness | Reviewed aero/brake/powertrain/tire coverage and numerical orchestration |
| G9 | Physical correlation and broader design/optimization promotion | Hardware/data gated; overlaps later software work | Separately classified identification/validation data and applicability evidence |

G2 is a bounded classification pass, not a reason to postpone all G3/G4 work.
Close the ride/stiffness prerequisites first; independently scoped brake/aero
reference calculations can proceed separately. G5b need not wait for completion
of every vertical-dynamics extension. Aligning-moment/steering-effort work also
remains a separate useful branch when its source inputs are established.

## Immediate execution

1. Finish G2 using the [Phase 2 checklist](phase2_scope_and_transient_entry_v0.1.0.md).
   Reuse existing functions where possible; distinguish a missing report/adapter
   from missing physics. Explicitly defer unrelated breadth instead of letting
   it silently become a prerequisite for the first transient experiment.
2. At G3, define wheel-coordinate tangent stiffness, mass allocation, vertical
   tire stiffness and damper parameter contracts. State the operating point and
   which coordinates are held fixed. Do not substitute a component spring rate
   for a complete wheel-coordinate tangent or infer tire vertical stiffness
   from the existing pure-lateral tire table.
3. Prepare the G4 documentation/authorization packet and independent verification
   cases before implementing its new force laws/integrator. Begin with explicit
   manufactured parameters; a WUFR-labelled parameter set is a separate mapping.
4. Implement and verify G4, then publish deterministic traces and parameter
   comparisons through the existing report/viewer contracts. Keep existing
   steady-state results as reference fixtures; no full operational release is
   required for this cross-checking role.

## Scope of the first transient experiment

Proposed G4: two vertical coordinates (sprung and unsprung displacement) and their
velocities about a declared static equilibrium, with suspension spring/damper,
vertical tire stiffness and an explicit road displacement history. Start with
linear, time-invariant, passive components and a positive static normal-load
reference. Keep tire compliance explicit. No hidden manufacturer damper curve,
inerter, roll/pitch, lateral/yaw coupling or installed setup is introduced.

Outputs: time histories of body/wheel motion, body acceleration, suspension
travel, damper force, tire deflection and dynamic normal-load variation; modal
frequencies and damping information where definitions permit. Label increments
versus absolute forces and avoid adding static weight twice. Loss of positive
normal load or violation of declared travel/constitutive bounds ends the supported
linear-contact result; do not clip forces or silently continue through wheel lift.

Verification must precede numerical acceptance criteria: zero-input equilibrium,
undamped free-vibration modes, passive energy dissipation, independently obtained
linear-system time/frequency responses, smooth-bump and sinusoidal forcing,
time-step refinement and clear rejection of nonphysical inputs. Keep manufactured
tests independent of the production integrator. An ideal road step is not a
finite wheel-acceleration peak reference.

Reference inspected: Guiggiani, *The Science of Vehicle Dynamics*, third edition
(2022), chapter 10, sections 10.1–10.3 and 10.6, especially printed pp. 440–443
and 459–460. These motivate the reduced ride hierarchy, equilibrium-relative
coordinates and the importance of tire compliance for Formula cars. They do not
provide WUFR parameter authority. The source PDF is catalogued externally; no
licensed source material is copied into the repository.

## UI and release policy

Keep the current offline viewer and reproducible reference reports useful. Add
only UI that reduces effort in the active experiments: explicit parameter/case
editing, run status and comparable plots. A polished application, broad database
management and full operational release are deferred. The equation/parameter
contracts remain in the engine and source records, never duplicated in UI code.

## Progress-update rule

Every development PR that changes program capability or priority updates the
current milestone row and appends one checkpoint below. Include milestone ID,
delivered behavior, verification, remaining limitation and next dependency.
Routine fixes may cite an unchanged milestone without inventing a new phase.
Do not mark a phase complete from PR count, a converged result or a UI screenshot.
Status transitions require evidence; preserve historical failures and decisions.

| Date | Milestone | Checkpoint | Next dependency |
|---|---|---|---|
| 2026-10-31 | G1 | PR 121 has 51 accepted comparison cells, one retained guarded recovery, 54 focused tests and 12 successful workflows; ready/unmerged | Do not equate this bounded workflow with full Phase 2 or vehicle validation |
| 2026-10-31 | G2–G4 | Owner prioritizes Phase 2 scope closure and reduced transients; this checklist/timeline fixes the next sequence, without authorizing new physics | G2 disposition confirmation, then G3 contracts and G4 model/verification packet |

## Checkpoint — manufactured ride verification, 2026-10-31

G2 scope disposition remains tracked in the Phase 2 scope document. The first G3
local stiffness/modal slice and G4 manufactured quarter-car verification are now
implemented; this does not close native parameter integration or Phase 2 breadth.

Delivered: signed compression-map stiffness including loaded geometric stiffness;
undamped mass-normalized modes; fixed-step RK4 sprung/unsprung response with
same-stage energy quadratures and explicit sampled contact/travel failures.
Nine analytical/contract tests pass. Harmonic step-halving error ratios are 15.96
and 15.97 (predeclared acceptance 12–20); manufactured bump energy balance closes
to 8.53e-14 J at dt=0.005 s. These are manufactured verification results, not
vehicle accuracy estimates.

Next dependency: recover the documented vertical tire/damper parameter sources,
bind explicit represented masses and local geometry derivatives, then run native
parameter sensitivity cases. Half-car heave/pitch follows that adapter. No physical
car measurements or operational UI release are required for this analytical work.
See [verification specification](../models/vehicle/reduced_ride_verification_spec_v0.1.0.md)
and [machine-readable results](../reports/reduced_ride_verification_v0.1.0/summary.json).

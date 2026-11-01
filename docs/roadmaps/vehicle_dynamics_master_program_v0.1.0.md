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

## Checkpoint — exploratory parameter binding, 2026-10-31

G3 now includes nominal native geometry compression-gradient/curvature recovery
with step checks and independent spring-energy tangents. G4 now includes 36
exploratory tire/damping sensitivity cases with time-step checks. All pass.
The repo-referenced LLTD workbook tire inputs were recovered (180/190 kN/m
front/rear); they remain legacy scenarios without operating-condition authority.
Individual corner scales and the reviewed 5 kg unsprung split replace arbitrary
total-mass quartering. Damping remains an explicit scenario proxy, pending KW
curve and setting recovery. Nominal local stiffness is not equilibrium-based
vehicle modal authority. See [study results](../reports/ride_parameter_study_v0.1.0/README.md).

Next: recover KW velocity-force curves/settings and tire operating conditions;
then equilibrium-based local derivatives and coupled half-car mass/inertia.
Physical correlation remains deferred; analytical verification continues.

KW source follow-up: recovered vendor Box file 1791709004896 links piggyback
3980599103 to standard S2FS01 and provides force envelopes at 0.25 m/s. Remaining
damping work is curve digitization and explicit click-setting scenarios, rather
than a missing damper-family identity. No one-speed F/v calibration is introduced.

## Checkpoint — manufactured half-car, 2026-10-31

G5a has its first implemented verification slice: coupled sprung heave/pitch and
front/rear unsprung vertical dynamics, independent roads, energy quadratures and
sampled contact/travel guards. Six new tests pass, including exact symmetric
heave/pitch modes, asymmetric force/moment/energy identities and bump refinement.
The previous nine stiffness/quarter-car tests remain passing. This is not native
half-car readiness or completion of G5a. See [half-car results](../reports/half_car_verification_v0.1.0/README.md).

G3/G4 source dependency: KW text recovery succeeded but both advertised Box raw
PDF download tools were unavailable (`Tool ... not found`). Plot digitization
remains blocked on renderable source access; no fake samples or inferred KW
linear coefficient were introduced. Native equilibrium linearization and pitch
inertia remain ahead. Continue analytical verification independently of physical
car correlation. No UI/operational-release dependency is introduced.

## Checkpoint — inertia source audit and equilibrium local tangents, 2026-10-31

Existing static mass/CG/geometry/spring/ARB providers support solving a source-
bounded equilibrium without pitch inertia. Local spring tangents are now sampled
at the solved wheel coordinates rather than nominal CAD coordinates; derivative
and energy checks remain unchanged. Results and pass/failure status are recorded
in the equilibrium-local-stiffness report when the reproducible run completes.
This is not a complete coupled body stiffness matrix or tire-compliant equilibrium.

No usable native sprung pitch inertia was identified in the bounded repository/
Box audit. Engine inertia, shaft section inertia and an acceleration filter's
pitch time constant are explicitly rejected as substitutes. The telemetry route
is deferred: static calculations do not need it, and IMU-only response would not
uniquely identify inertia with unknown inputs/damping. The next native half-car
input is a configuration-matched sprung-CG pitch inertia source or a separately
specified identification experiment. See `data_catalog/pitch_inertia_source_audit_v0.toml`.

Run completion: equilibrium-local study passes, with force/moment closure
5.16e-8 N / 4.57e-8 N*m and all four derivative/energy checks passing. Solved-state
local spring tangents are 24.990/24.994 N/mm front and 32.575/32.560 N/mm rear.
[Evidence](../reports/equilibrium_local_stiffness_v0.1.0/README.md) retains full
results. Native pitch dynamics remain gated on sprung-CG pitch inertia; there is
no telemetry requirement for the completed equilibrium calculation.

## Checkpoint — no-driver/no-fuel provisional inertia, 2026-11-01

Owner clarified no fuel/no driver and accepted electrical mass as a point at the
car CG. Read-only WUFR-26 COM/BOM and subsystem drawings support a provisional
partition. CAD-origin tensor ordering and mixed production/CAD bases were bypassed
by reconstructing from component CAD masses, CGs and labelled centroidal Lyy.
The source snapshot includes the fuel exclusion and manual shock aggregate once.
This supersedes the earlier narrow finding that no useful COM inertia source
could be identified; usable component data exists, with frame/completeness limits.

G5a now includes three reproducible inertia-only sensitivity cases, Jy=67.771,
69.932,72.089 kg*m². Other dynamic inputs are fixed, including the middle-case
body mass; all refinement/energy checks pass. In the illustrative bump, peak pitch
acceleration changes about 2.5%, peak heave acceleration <0.2%. These are scenario
results, not native vehicle predictions or rigorous bounds.

The earlier static state is driver/no-fuel; it is not a compatible equilibrium
for this no-driver mass study. Native promotion still needs mass-inventory
reconciliation, tensor-frame verification, distributed electrical inertia review
and moving-link effective mass reduction. Analytical work can use the labelled
range without treating physical correlation or telemetry as a prerequisite.
See [inertia study](../reports/no_driver_pitch_study_v0.1.0/README.md) and
[specification](../models/vehicle/no_driver_pitch_sensitivity_spec_v0.1.0.md).

## Checkpoint — stack landed and consistent CAD mass budget, 2026-11-01

PRs 121–127 are merged and verified by GitHub readback; all head workflows passed
before landing, with no outstanding review threads. See the
[closeout record](../reviews/analytical_transient_stack_closeout_2026_11_01.md).
Owner confirmed COM export axes match software. The axis-convention gap is closed
for development; no new KW source is expected, and damping remains scenario data.

Three no-driver/no-fuel coupled allocation cases now use their own matching body
mass/Jy/CG and complementary front/rear axle masses, replacing illustrative axle
mass placeholders. Every case preserves the 203.731 kg CAD mass inventory and
source first moments before explicit axle-station projection. Refinement, energy
and represented-model static load identities pass. Unlike the earlier inertia-only
study, coupled allocation changes peak heave acceleration about 5.8% in the chosen
bump, identifying moving-link mass reduction as a worthwhile next analytical task.
[Study evidence](../reports/no_driver_mass_consistency_v0.1.0/README.md).

No-driver 449.149 lb CAD versus 477 lb scale inventory remains unresolved; do not
combine this CAD mass scenario with the driver/no-fuel equilibrium or infer a
missing-mass position. Analytical development continues without physical release
or broader UI work. Native prediction remains source/calibration gated.

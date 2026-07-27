# Post-rigid-contact R&D program v0.1.0

## Decision

PR #67 closes the first WUFR design-intent rigid-road compatibility slice. The project now has enough reviewed geometry, conservative suspension-force providers, gravity allocation, and provider-neutral quasi-static mechanics to finish a first uncorrelated static vehicle composition, but WUFR-27-specific prediction is increasingly limited by installed/as-built evidence that cannot exist until the car is assembled.

The program therefore separates **reusable physics that can be verified now** from **WUFR-27 correlation work that must wait for hardware**.

The ordered architecture is:

1. finish one bounded WUFR static-equilibrium integration slice;
2. build reusable suspension linkage/load-path statics;
3. promote the existing TTC branch work into a reusable steady-state tire model;
4. prepare the WUFR-27 physical correlation/data contract before the car exists;
5. resume integrated maneuver QSS only after the static model has physical correlation evidence.

The implementation order may overlap where subsystem boundaries are independent, but no later layer may invent missing upstream authority inside a downstream model.

---

## Program A — WUFR static-equilibrium closeout

### Goal

Compose the already-reviewed providers:

- `MOD-SUSP-0004` spring generalized force;
- `MOD-SUSP-0005` Z-bar generalized force;
- `MOD-VEH-0005` sprung/unsprung gravity;
- `MOD-VEH-0006` rigid-circle flat-road compatibility;
- `MOD-VEH-0004` provider-neutral quasi-static equilibrium kernel.

### Output boundary

The first result is an **uncorrelated design-intent integration result**, not an as-built corner-weight prediction. It may report solver state, wheel coordinates, spring/ARB states, equilibrium residuals, and recovered rigid-road reactions only under a separate authorization that preserves all current assumption labels.

No static result is independent validation against the historical scale state when the same scale state contributes to the mass/CG source chain.

### Resume/promotion evidence

Physical correlation later requires, at minimum, the actual vehicle configuration, corner scales, body ride-height references, damper/shock-pot states, installed spring/perch references, ARB adjustment and zero-preload state, alignment, tire pressure, and loaded tire radius.

---

## Program B — suspension linkage and load-path statics

### Why this is the next reusable mechanics vertical slice

The suspension kinematics stack already supplies reviewed point geometry and rigid transforms. A separate statics layer can therefore answer a different question without pretending to know the final WUFR tire load case:

`prescribed external wrench + reviewed geometry -> ideal linkage forces/reactions`

The first model is intentionally an ideal statics baseline. Borg (2009), *An Approach to Using Finite Element Models to Predict Suspension Member Loads in a Formula SAE Vehicle*, Chapter 3 Section 3.3.1, derives the familiar six-member space-truss formulation by building member unit vectors and stacking three force plus three moment equilibrium equations. The same work also shows why this model must remain bounded: the truss FE model reproduced the hand calculation, while beam-member fidelity introduced meaningful bending/load redistribution, and steering articulation materially changed member loads in cornering cases. Those results are treated as model-boundary evidence, not WUFR load authority.

Guiggiani (2022), Section 3.10.7, independently motivates suspension internal equilibrium as the problem of determining how road/tire loads are transmitted through suspension linkages and elastic elements.

### B1 — provider-neutral single-rigid-body axial-link kernel

First authorization: `MOD-SUSP-0006`.

Scope:

- one rigid body;
- prescribed external force and couple about an explicit reference point;
- exactly six ideal pin-ended two-force links for the first determinate solve;
- each link force constrained to its current geometric axis;
- signed axial force with positive tension;
- exact 3D force and moment equilibrium;
- scaled rank/conditioning diagnostics;
- no least-squares or minimum-norm repair of singular/over/under-determined systems.

This is the canonical replacement for a hand-built 6x6 member-force matrix. It is **not** yet a WUFR corner-load calculator.

### B2 — general equilibrium graph / WUFR topology audit

Before mapping `MOD-SUSP-0006` directly onto WUFR, review the actual load-path topology. The current source package explicitly places the front push/pull attachment on the upper A-arm and the rear attachment on the lower A-arm rather than universally on the upright. That means a naive six-link-to-upright model would silently move an application point and is prohibited.

The next statics slice must therefore decide, from source geometry and hardware architecture, which bodies/joints are represented as:

- rigid bodies;
- ideal axial links;
- massless pin nodes;
- prescribed reactions;
- or deferred beam/compliance members.

A multi-body or joint-equilibrium graph may then reuse the same force/moment assembly primitives without changing `MOD-SUSP-0006` semantics.

### B3 — actuation/reaction propagation

After the topology is reviewed, propagate load through the actual actuation chain to recover quantities such as push/pull-rod axial force, rocker bearing reaction, coilover axial force, ARB-link/blade reactions, tie-rod load, and chassis pickup reactions where the ideal model is statically determinate.

Spring and ARB constitutive providers remain authoritative for their own elastic forces; the statics layer must not duplicate their force laws.

### B4 — structural load-case exchange

Create a source-preserving load-case packet for downstream CAD/FEA consumers containing:

- geometry/configuration identity;
- body/link/joint identities;
- application points and frames;
- external wrench provenance;
- signed axial/reaction forces;
- equilibrium residuals and conditioning;
- explicit exclusions and model fidelity.

This packet is the intended bridge toward replacing the useful parts of OptimumK Forces without making FEA boundary conditions depend on spreadsheet conventions.

### B5 — higher-fidelity structural mechanics later

Beam bending, welded wishbone load sharing, bearing stiffness, joint friction/backlash, compliance, buckling, fatigue, weld stress, and production structural release remain separate models. An ideal axial-load result may seed those analyses but may not be labelled final member stress or factor of safety.

---

## Program C — reusable steady-state tire model

Promote the existing steering-specific R25B branch exporter into a shared tire package.

Initial target:

`Fy = f(alpha, Fz, inclination, pressure)`

Then add:

`Mz = f(alpha, Fz, inclination, pressure)`

Use the already reviewed Hoosier 43105 R25B source chain while preserving the intended 43104 R20 identity separately. The first shared model should remain source bounded, avoid hidden extrapolation, and report its operating envelope explicitly.

Combined slip, longitudinal force, temperature, wear, relaxation, and transient effects are later additions only when demanded by a reviewed downstream model.

---

## Program D — WUFR-27 physical correlation contract

Build the data schema and test procedure before the vehicle exists so that measured states replace assumptions rather than forcing architectural changes after assembly.

Minimum static/configuration packet:

- car revision and assembly configuration;
- driver/ballast/fuel state;
- tire identity, pressure, and temperature condition;
- four corner weights and total mass;
- defined front/rear body ride-height points;
- installed damper lengths or calibrated shock-pot positions;
- spring free/installed lengths and perch positions;
- ARB blade/link setting and verified zero-preload state;
- per-wheel camber and toe;
- loaded tire radius;
- per-corner unsprung mass when practical.

Steering correlation packet:

`steering/shaft angle -> rack displacement -> left/right wheel heading`

with reversal/deadband tests and, later, loaded compliance tests.

Suspension correlation packet should include selected known bump/rebound states sufficient to compare wheel-center/upright motion and actuation displacement against the rigid kinematic model.

---

## Program E — integrated maneuver QSS after correlation

Only after Program A has static physical correlation should the project add maneuver-specific equilibrium inputs such as lateral/longitudinal tire forces, aero, brake/powertrain forces, loaded-radius/tire vertical compliance, and alternate contact modes.

The target is a synchronized steady-state operating state, not a lap simulator. LLTD, load transfer, body roll/pitch, wheel loads, required tire slips, and steering regime should emerge as model outputs rather than being inserted as governing shortcuts.

---

## Architecture rules carried across all programs

1. **Source ownership stays local.** Geometry, tire response, springs, ARB, mass/gravity, steering, and structural statics keep separate authority records.
2. **Frames and application points are explicit.** Every force/couple is attached to a named point/frame/origin before equilibrium assembly.
3. **No hidden repair.** Singular statics, negative contact reaction, unavailable tire state, failed kinematic branch, or missing installed evidence returns an explicit failure rather than clipping or fitting.
4. **Low-fidelity models remain useful when labelled.** An ideal axial-link result is acceptable for screening and load-path understanding, but it does not become beam stress or as-built validation through wording.
5. **Physical correlation updates parameters, not architecture.** The pre-build software should already expose the places where measured WUFR-27 values will enter.
6. **Lap simulation remains downstream orchestration.** It should consume reviewed subsystem providers rather than become the place where missing subsystem physics is invented.

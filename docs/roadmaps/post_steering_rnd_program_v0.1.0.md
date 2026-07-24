# Post-steering R&D program v0.1.0

## Decision

The steering R&D vertical slice is feature-complete for its present purpose after PR #32 and PR #33. Further steering-only physics is intentionally paused until upstream suspension, vehicle-state, tire-response, or physical-correlation evidence changes the design question.

This is an architecture closeout, not a production steering release. Installed-system correlation, real hardware constraints, rack-load/effort authority, tolerance/robustness, and physical release remain separately data-gated.

## Why steering stops here

The steering stack can now consume:

- a provider-supplied zero-steer upright pose;
- explicit per-wheel normal load, inclination, pressure, and force demand;
- source-preserving tire response branches;
- explicit body motion `(u, v, r)`;
- state weights and authority/provenance;
- existing mechanism and design-variable definitions.

It can then produce state-dependent steering targets and evaluate candidate mechanisms through the same reviewed rigid steering analyzer. What it cannot honestly produce by itself is the missing upstream WUFR suspension motion, wheel-load distribution, tire-force demand, or body-motion state. Adding those equations inside steering would collapse subsystem boundaries and create unreviewed vehicle physics.

## Next vertical slices

### 1. Authoritative suspension kinematics evaluator

Build `MOD-SUSP-0001` as the next primary R&D model.

The first release should map reviewed hardpoints and explicit chassis/wheel-travel inputs to wheel-center and upright state, including at minimum:

- heave and independent bump/rebound;
- roll and pitch inputs where the kinematic contract requires them;
- wheel-center translation;
- upright orientation;
- camber/inclination;
- toe/heading response where appropriate for suspension-only validation;
- caster/KPI and steering-axis state;
- track and wheelbase change;
- spring/damper/rocker or direct-actuation motion where available.

The first external benchmark should reproduce selected OptimumK kinematic channels from the current WUFR source set. The steering-facing output must be the zero-steer upright rigid transform required by `SuspensionPoseSet`; a source state that already contains tie-rod-induced steering may be validation evidence but may not be fed directly into steering closure.

### 2. Quasi-static vehicle load-state generator

After suspension kinematics is credible, build a shared vehicle-state producer rather than a lap simulator.

Inputs should include reviewed mass properties, tracks/wheelbase, CG location, spring/ARB/roll-stiffness information, aero inputs where applicable, speed, and requested longitudinal/lateral acceleration. Outputs should populate the existing vehicle operating-state contract with four explicit wheel loads and synchronized suspension state.

The first objective is a trustworthy operating envelope, not transient lap prediction.

### 3. Reusable steady-state tire model

Promote the tire work from steering-specific target support into a shared vehicle-dynamics model.

Initial priority:

`Fy = f(alpha, Fz, inclination, pressure)`

Then add aligning moment `Mz` because it is needed for yaw response and later steering effort. Longitudinal/combined-slip and thermal/transient effects should be added only when a downstream model actually requires them.

The Hoosier 43105 R25B TTC source remains the project-authorized engineering proxy for the intended 43104 R20, with both identities preserved. The historical automatic `2/3` surface scale remains outside the intrinsic tire-data path unless separately justified.

### 4. Steady-state vehicle trim / QSS

Once suspension, load state, and tire response are available, solve representative steady-state vehicle conditions for force and yaw equilibrium.

The useful output is a synchronized state containing quantities such as:

- `u`, `v`, and `r`;
- four wheel loads;
- suspension/upright poses;
- camber/inclination;
- tire force demands and required slips;
- steering target and resulting mechanism response.

This is the point at which WUFR-specific pro/parallel/anti-Ackermann preferences can be evaluated meaningfully across the operating envelope.

### 5. Lap simulation later

Do not make lap simulation the place where subsystem physics is first invented.

A useful future lap simulator should orchestrate already-reviewed tire, suspension, steering, aero, powertrain, brake, and mass-property models. Building it after the subsystem solvers reduces hidden assumptions and makes each lap-time result traceable to independently testable models.

## Physical testing path

Physical steering work remains important but is not the next software dependency. Preserve the planned measurement chain for later testing:

`steering/shaft angle -> rack displacement -> left/right wheel heading`

with reversal tests for deadband/hysteresis and loaded tests for compliance. These data should identify installed corrections without replacing the rigid design model.

## Visualization/tooling policy

### Implement reliable graphing now

Plotting is part of verification, not presentation polish. Add a reusable visualization/report layer that consumes machine-readable outputs and fails visibly when required data are absent.

Priority plots include:

- rack/input versus left/right/inside/outside wheel heading;
- target versus actual response and residuals;
- Ackermann/reference split and state-dependent regime;
- tire `Fy` versus slip angle at explicit operating points;
- constraint margins and infeasible-state diagnostics;
- candidate objective decomposition and local sensitivity;
- operating-state coverage and out-of-domain warnings.

Generated plots should carry units, source/state identifiers, and deterministic filenames. Blank plots or manual screenshots should not be model evidence.

### Add a lightweight 3D viewer with suspension kinematics

A 3D viewer becomes high-value as soon as `MOD-SUSP-0001` exists because it can expose coordinate-frame, sign, branch, and hardpoint mistakes that are difficult to see in scalar plots.

Useful first features:

- hardpoints and links;
- rack and tie rods;
- steering axes;
- upright and wheel planes;
- wheel centers/contact references;
- animation through rack travel, bump/rebound, heave, and roll;
- visual highlighting of failed/singular states.

### Defer a polished full GUI

Do not couple the core physics to a large desktop UI while upstream contracts are still changing. Keep numerical packages headless and dependency-light. Put visualization in a separate optional package or application layer. Once suspension kinematics and quasi-static state interfaces stabilize, a local browser-based engineering workbench can become the main team-facing UI without forcing UI dependencies into the physics packages.

## Resume-steering triggers

Return to major steering R&D when one of the following becomes available:

1. reviewed WUFR zero-steer suspension pose data;
2. representative synchronized Fz/camber/pressure/Fy operating states;
3. reviewed source-derived R25B force branches at required states;
4. reviewed QSS/telemetry `(u,v,r)` states;
5. physical rack-to-wheel/backlash/compliance correlation;
6. a real hardware constraint or steering-effort requirement that changes candidate feasibility.

Until then, steering should remain a stable consumer of upstream models rather than a place to invent them.

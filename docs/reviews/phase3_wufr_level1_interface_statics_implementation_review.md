# Phase 3 WUFR Level-1 interface statics implementation review

## Outcome

`MOD-SUSP-0007` is implemented under `AUTH-SUSP-0012` as a source-bounded Level-1 interface solver. The implementation preserves the three-body topology authorized after the WUFR27 carryover decision:

- outboard carrier/upright rigid body;
- upper A-arm rigid body;
- lower A-arm rigid body;
- upper/lower spherical outboard joints;
- upper/lower equivalent net revolute inboard supports;
- one signed lateral axial link;
- one signed arm-mounted push/pull axial link.

The solver does not generate an actual WUFR maneuver load case. It consumes one complete prescribed external wrench on the outboard-carrier boundary.

## Mechanics implemented

The physical equilibrium system is exactly `18 x 18`:

- UCA equivalent hinge: 5 reaction scalars;
- LCA equivalent hinge: 5;
- upper spherical force on carrier: 3;
- lower spherical force on carrier: 3;
- tie/toe axial force: 1;
- push/pull axial force: 1.

The front actuation column acts only on the UCA at its reviewed current arm attachment. The rear actuation column acts only on the LCA. No load application point is moved to the carrier/upright to recover a six-link shortcut.

Each equivalent revolute support admits arbitrary net force and two reaction-moment components perpendicular to the exact fore/aft A-arm hinge axis. The reconstructed hinge moment is explicitly checked to have zero component along the hinge axis.

## Source-preserving current-state adapter

`wufr_interface_adapter.py` consumes the existing suspension and actuation state objects rather than duplicating kinematics.

It constructs:

- exact inboard hinge axes from the frozen fore/aft hardpoints;
- current upper/lower carrier joint centers from the suspension state;
- current arm-mounted actuation point and current rocker rod point from `MOD-SUSP-0003` state;
- rear current toe-link body point from the reviewed rear upright/toe transform.

Front steering remains an explicit ownership boundary. The adapter refuses to substitute nominal suspension toe points for a front tie-rod state; it requires current tie-rod endpoints carrying `MOD-STEER-0001`/steering-closure provenance.

## Numerical implementation

The implementation follows the conservative direct-solve policy already established by `MOD-SUSP-0006`:

- physical SI force/moment assembly first;
- per-body moment-row scaling using a geometry-derived characteristic length;
- deterministic partial-pivot direct elimination;
- explicit infinity-norm condition-number evaluation;
- rejection above `cond_inf = 1e10`;
- relative pivot rejection below `1e-12`;
- independent reconstruction of physical force/moment equilibrium on all three bodies;
- no pseudoinverse, least squares, minimum-norm, regularization, stiffness-weighted load sharing, sign clipping, or geometry repair.

Compression remains a valid negative axial result.

## Verification

`BENCH-SUSP-0021` freezes a nontrivial full-rank analytical 18x18 fixture. Its signed target solution includes both hinge resultant components, spherical interface forces, lateral-link axial force, and arm-mounted actuation force. The benchmark also freezes the three body scaling lengths and scaled condition number.

`BENCH-SUSP-0022` is enforced by the current-state adapter tests. It verifies physical application-point ownership and the front steering handoff.

`BENCH-SUSP-0023` checks rigid translation, wrench-reference translation, hinge-axis sign invariance, source/ownership failures, degenerate geometry, singular/ill-conditioned systems, incomplete external wrenches, and no approximate repair.

The frozen implementation record is `benchmarks/suspension/wufr_interface_statics_result_v0.1.0.toml`.

## Important fidelity boundary

The following are still deliberately **not** outputs of this implementation:

- unique fore/aft UCA/LCA chassis rod-end or tab loads;
- welded A-arm tube internal loads or stress;
- rocker pivot reaction;
- physical spring/ARB/damper forces on the rocker;
- internal upright/hub/bearing/caliper/halfshaft reactions;
- tire/contact/maneuver load generation;
- structural FEA release or production factors of safety.

The next structural layer should propagate the solved push/pull force through the rocker. That requires physical force vectors for the spring and ARB interfaces. The spring path is already close to that form, but the current Z-bar implementation primarily owns deformation/generalized force mechanics. A separate review must establish the physical ARB linkage force vector and its rocker application point before rocker pivot reaction is solved.

Separately, actual WUFR Level-1 loads require a complete external carrier-wrench source. This implementation must not be mistaken for that load-case authorization.

# WUFR linkage/load-path topology source audit

## Purpose

This audit is the B2 gate in `docs/roadmaps/post_rigid_contact_program_v0.1.0.md`. It asks a narrower question than “calculate suspension loads”:

> What physical bodies, joints, and load interfaces are actually present in the WUFR corner/inboard suspension, and what can be idealized without moving a load application point or inventing load sharing?

The answer matters because `MOD-SUSP-0006` is intentionally a **one rigid body + exactly six ideal two-force links** kernel. That model is useful as a provider-neutral benchmark, but it is not automatically the WUFR topology.

`AUTH-SUSP-0011` records the outcome of this audit as an implementation hold. No WUFR member force is authorized here.

## 1. Source hierarchy reviewed

### 1.1 Frozen repository geometry/kinematics

The existing suspension geometry contract is the strongest current authority for hardpoint meaning and attachment ownership. It explicitly identifies four inboard control-arm pickups, two upright control-arm joints, front tie-rod vs rear toe-link roles, and the actuation pickup/rocker points. Most importantly, it freezes **front actuation on the upper A-arm** and **rear actuation on the lower A-arm**.

`AUTH-SUSP-0003` already enforces the same ownership in the actuation solver: moving the front pickup with the upright/lower arm or the rear pickup with the upright/upper arm is prohibited.

### 1.2 WUFR26 physical corner assemblies

Box contains current WUFR26 assembly drawings:

- `SU-A0701-AA FRONT CORNERS.pdf`, Box file `2120119871272`, SHA-1 `a1aedb29a997535435af7b613499448715cac926`;
- `SU-A0702-AA REAR CORNERS.pdf`, Box file `2142858842201`, SHA-1 `ebf896e9924541c63e364ca352c9aee860f089f9`.

The front BOM contains separate upper/lower fore/aft steel tubes, upper/lower bearing housings, pullrod, pullrod tabs/connector, four HAB-4TG high-misalignment spherical bearings across the two corners, and twelve 0.25-28 rod ends across the two corners.

The rear BOM contains the analogous upper/lower steel A-arm parts, pushrod/tab/connector, carbon toe-link tube, four HAB-4TG spherical bearings across the two corners, and sixteen rod ends across the two corners.

These records establish that the real corner is not a six-line abstract truss with six members all meeting the upright. The A-arms are physical welded assemblies and actuation hardware belongs to those assemblies.

The aggregate BOM counts alone are **not** promoted to endpoint-by-endpoint joint authority. That mapping still needs assembly-callout/mate review or explicit team confirmation.

### 1.3 WUFR26 linkages, upright/hub, and inboard design reviews

The WUFR26 Linkages FDR identifies the A-arms as steel-tube assemblies, the tie/toe links as carbon components, and the bearing housings as the A-arm/upright interface. It also documents historical OptimumK-based member-force sizing.

The WUFR26 Upright/Hub FDR is especially important for load-path ownership. The upright is the attachment body for suspension links, bearings/hub, and brake caliper; the hub carries wheel/brake-rotor torque and rear driveshaft torque. That review also records that prior load calculations omitted brake-caliper bolt forces and tire moments, which materially undermines legacy tie/toe-link loads.

The WUFR26 In-Board Suspension FDR establishes the physical rocker/coilover/ARB package. Existing repository models already own its detailed kinematics, spring mechanics, and Z-bar mechanics; the new structural statics layer should consume those outputs rather than recreate them.

### 1.4 Historical load matrices are negative evidence, not authority

The Drive document `Load Case List with Load Matrices` contains the instruction:

> `TREAT ALL NEGATIVE VALUES AS 0N`

That rule is incompatible with the project’s signed axial-force convention, where positive is tension and negative is compression. The same historical load lineage also predates the corrected brake-caliper/tire-moment treatment documented by the upright review.

Accordingly, the load-matrix document is retained only as lineage/comparison evidence. It is **not** a governing input to future WUFR structural statics.

## 2. What is source-supported now

The following topology facts are sufficiently supported to freeze as constraints on the next model:

1. **Upper and lower A-arms remain separate physical bodies/assemblies.** Each has forward/aft chassis hardpoints and one upright joint in the frozen geometry.
2. **Front actuation loads the upper A-arm.** The pullrod load cannot be translated to the upright merely to obtain a six-link matrix.
3. **Rear actuation loads the lower A-arm.** The same prohibition applies at the rear.
4. **Front tie rod and rear toe link are distinct axial-link candidates with different kinematic ownership.** Front steering closure remains owned by `MOD-STEER-0001`; the rear toe link is a chassis locating link.
5. **The rocker is a separate load-path body.** Push/pull rod, coilover, ARB, and chassis pivot reactions meet there.
6. **The upright/hub/brake interface must preserve torque path.** A braking or drive case cannot be reduced to an arbitrary wheel-center force without an explicit wrench contract.
7. **Signed force is mandatory.** Compression is not clipped to zero.

## 3. Why the simple six-link WUFR adapter is blocked

A classic six-member FSAE hand calculation treats six members as pin-ended two-force links meeting a rigid upright. Borg’s thesis demonstrates why that can reproduce a truss model exactly when the real model is forced to share those assumptions, and also why moving an actual arm-mounted pullrod back onto the upright changes the load path.

WUFR has the exact topology conflict that matters here: the front and rear actuation pickups are attached to control arms rather than directly to the upright. The welded arm therefore receives an additional off-upright load. Calling its two tubes independent two-force links would discard the load path we are trying to calculate.

`MOD-SUSP-0006` remains valid as a generic determinate kernel, but **not as a current-WUFR corner adapter**.

## 4. Candidate first WUFR architecture

The strongest low-fidelity architecture I see is a **multi-rigid-body equilibrium graph**, not an enlarged version of the six-link matrix.

Candidate bodies/elements:

```text
road/tire/wheel/hub/brake external wrench
                 |
          [upright/corner]
           /      |      \
    spherical  spherical  tie/toe axial link
        /          \
     [UCA]        [LCA]
       |             |
  chassis hinge  chassis hinge
       |
  front pullrod     rear pushrod
       \             /
          axial actuation rod
                 |
             [rocker]
          /       |       \
      chassis   coilover   ARB
       pivot    provider   provider
```

For a first interface-level solve, each A-arm’s two inboard hardpoints could potentially be reduced to an **equivalent revolute support about the already-frozen arm hinge axis**. That is attractive because it is consistent with `MOD-SUSP-0001` kinematics and prevents the welded wishbone from being falsely represented as two independent truss bars.

That reduction is **not authorized yet**. The current hardware/joint review must first establish that the ideal revolute support is a defensible first-order static abstraction.

### 4.1 Important output boundary

Even after accepting an equivalent revolute support, rigid-body statics would provide the **net hinge reaction/wrench**, not unique loads in each forward/aft chassis rod end/tab or each welded A-arm tube.

The forward/aft split contains information about joint stiffness, tube/arm stiffness, fit, and load sharing. It generally cannot be recovered uniquely by force/moment equilibrium alone.

That gives us a natural fidelity ladder:

```text
Level 1: interface resultants
        upright joint force, equivalent A-arm hinge reaction,
        tie/toe force, push/pull force, rocker/pivot reactions

Level 2: discrete joint/tab loads
        forward vs aft chassis joint forces, bearing/tab loads
        -> needs an additional reviewed load-sharing/joint model

Level 3: welded member internal loads/stress
        tube axial + shear + bending, weld/bearing stress, buckling
        -> beam/FE structural model and stiffness authority
```

This separation is important. The first useful statics PR does not need to pretend it is already a structural FEA replacement.

## 5. WUFR27 authority check

The current `WUFR-27 Linkages & Loads PDR` is still a work-in-progress document. It explicitly lists redoing/confirming linkage load calculations as a goal and notes unresolved WUFR26 lessons, but it does not yet freeze the WUFR27 body/joint topology.

Box has a WUFR27 suspension folder scaffold with front/rear corner, ARB, rocker, and shock folders. At audit time the WUFR27 front-corner `PARTS` folder contained only an `FEA FILES` subfolder, while the front-corner assembly file existed as an early scaffold. That is not sufficient evidence that the WUFR26 hardware topology is unchanged.

Therefore the existing `WUFR27_SUSPENSION_BASELINE_V0` remains valid for the already-reviewed **kinematic hardpoint baseline**, but this audit does not promote that to a hardware/load-path carryover statement.

## 6. Exact source/topology questions remaining

The remaining questions are now narrow enough to answer deliberately.

### A. WUFR27 carryover vs redesign

For each of these, confirm “WUFR26 topology retained” or identify the change:

- front UCA/LCA;
- rear UCA/LCA;
- front pullrod and its arm attachment;
- rear pushrod and its arm attachment;
- front tie rod;
- rear toe link;
- front/rear rocker and pivot support;
- front/rear ARB connection to rocker;
- upright/hub/bearing interfaces;
- brake caliper/rotor interface;
- rear CV/halfshaft/hub torque path.

### B. Endpoint joint table

For every connection above, freeze:

- body A / body B;
- exact hardpoint or bolt-axis definition;
- hardware type: spherical bearing, rod end, clevis/bolt, bearing pair, etc.;
- first-model idealization: spherical, revolute, axial two-force, prescribed force, or deferred structural interface;
- whether the connection can carry force only, force plus moments, or a constrained-axis moment reaction.

### C. Required output fidelity

The next implementation depends strongly on what the team actually wants from “linkage statics”:

- **interface loads only** are compatible with the proposed rigid-body graph;
- **individual chassis-tab/rod-end loads** require an additional rule for the forward/aft split;
- **A-arm tube/weld loads** should go directly to a beam/FE layer rather than be invented from rigid statics.

### D. Brake and drive load path

For braking, freeze whether the upstream load packet will provide:

- a complete external wrench on the chosen corner body; or
- separate wheel-bearing/hub and caliper reactions that the statics graph must assemble.

For rear drive, freeze the equivalent contract for the halfshaft/CV/hub torque path.

## 7. Recommended next gate

Once the questions in Section 6 are answered, the next authorization should define a WUFR multi-body equilibrium graph with:

- explicit body list;
- joint types and reaction unknowns;
- known vs solved forces at the spring/ARB/actuation interfaces;
- matrix/rank/conditioning rules;
- synthetic analytical benchmark(s);
- one WUFR geometry-only benchmark that proves load application points were not moved;
- structured failure for under/over-constrained or source-incomplete topology.

Only after that authorization should current-car interface reactions be calculated.

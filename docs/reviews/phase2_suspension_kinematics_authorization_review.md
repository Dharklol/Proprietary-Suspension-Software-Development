# Phase 2 suspension kinematics authorization review

**Status:** review-ready in PR #39  
**Authorization:** `AUTH-SUSP-0001`  
**Model:** `MOD-SUSP-0001`

## Review question

Is there now enough source, equation, numerical-method, failure-contract, and benchmark definition to allow a bounded rigid double-wishbone kinematics implementation without inventing wheel geometry, steering behavior, loads, or whole-vehicle origin semantics?

## Decision

**Recommended: authorize the bounded prototype after this PR is reviewed and merged.**

PR38 froze the WUFR-26/27 nominal hardpoints and roles. This slice freezes the mechanism equations and verification burden before solver code begins.

## What is authorized

1. Exact rigid rotation of each A-arm outboard joint about the line through its fore/aft chassis pivots (`EQ-SUSP-0001`).
2. A one-dimensional upper-arm closure solve preserving rigid upper/lower upright joint-center separation (`EQ-SUSP-0002`).
3. A deterministic shortest-rotation, zero-extra-twist upright reference transform (`EQ-SUSP-0003`).
4. Rear-only chassis toe-link closure for the remaining upright twist (`EQ-SUSP-0004`).
5. A first internal independent coordinate `q_L`, defined only as signed lower-arm rotation about the fore-to-aft lower-arm hinge axis.
6. Front output compatible with the existing unresolved-steering pose contract; front tie-rod steering remains in `MOD-STEER-0001`.

## Why arm rotation is the first coordinate

The geometry contract does not yet contain a reviewed wheel-center construction. Choosing wheel-center vertical travel as the solver coordinate would therefore make an unreviewed point authoritative.

Using `q_L` avoids that problem. The lower arm has a geometrically exact hinge axis from already frozen chassis hardpoints, and the outboard joint follows a rigid circle with no numerical solve. The upper-arm closure is then a single scalar root.

This is an internal mechanism coordinate, not a user-facing suspension-state definition. A later adapter may expose wheel travel, heave, roll, pitch, or independent corner displacement once the associated reference points are reviewed.

## Front upright twist boundary

The wishbones determine the current lower/upper ball-joint centers and thus the steering-axis line. They do not, by themselves, select front upright twist about that line because the steering linkage closes that degree of freedom.

The minimum-twist transform is therefore defined only as a deterministic zero-steer reference. It must not be interpreted as the physical wheel heading. The resulting front pose is passed to `MOD-STEER-0001`, which solves the actual tie-rod-induced steering rotation.

This preserves the already merged rule:

`upright_reference_pose_excludes_tie_rod_steering_rotation`.

## Rear distinction

The frozen OptimumK source explicitly gives the rear link a chassis-locating role. After the wishbones locate the kingpin axis, the rear toe-link length can therefore close the remaining twist about that axis. The rear equation rejects a front steering-tie-rod role.

## Numerical policy

Both scalar closures use a bracket-preserving method and stay on the branch connected to the nominal assembly. The following are explicitly prohibited:

- unconstrained Newton as the default;
- selecting another root after branch loss;
- hidden clipping or extrapolation;
- assigning a plausible pose after no closure exists.

Singularity/conditioning is reported separately from closure residual.

## Benchmark review

### BENCH-SUSP-0001

The synthetic parallel-arm fixture has a closed-form solution `q_U=q_L` and exact sine/cosine joint positions. This supplies the independent analytical check.

### BENCH-SUSP-0002

The WUFR front comparison uses the already frozen `WUFR-26 8.21 Heaves 1inch.xlsx` source, SHA-256 `db071b7e696149ec82213e9ed05aa557349d18d19debe7925e7e01058534e4b8`.

For the pure-heave result, multiple chassis points show that OptimumK translates chassis `z` coordinates by the `Motion [Heave]` amount while the wheel/upright remains road referenced. The benchmark therefore subtracts `[0,0,h]` in the OptimumK result frame before applying the reviewed source-to-canonical orientation transform.

This is intentionally a source-specific pure-heave adapter. It is not evidence that the same rule applies to roll, pitch, or another exporter.

The fixture contains 11 right-front states over ±25.4 mm. Static hardpoints from PR38 are rounded to 0.001 mm while the result workbook has higher numerical precision; private preauthorization checks found sub-micrometre-to-about-0.7-micrometre disagreement when the planned rigid equations are evaluated against the two source precisions. A 2 micrometre point tolerance is therefore conservative without pretending that the sources are identical-byte representations.

Tie-rod/toe/steer channels are excluded because the exported front upright state already contains tie-rod-constrained steering.

### BENCH-SUSP-0003

The synthetic rear fixture isolates the rear toe-link twist equation and requires exact recovery of a known +10 deg branch root. This avoids using the still-unreviewed rear whole-vehicle origin relationship.

## Open source issue: rear origin

The same OptimumK heave export places rear result coordinates approximately one `Reference Distance = 1562.4 mm` behind the front result origin. That is strong evidence about the result-export placement, but PR38's static suspension source uses separate axle-local reference origins.

This PR records the observation but does not promote it. A future whole-vehicle geometry/viewer adapter should review the exact origin semantics before applying the translation.

## Explicit exclusions

This authorization does not cover:

- wheel-center or contact-patch construction;
- motion ratio, pushrod/pullrod, rocker, spring, damper, or ARB kinematics;
- roll-center or anti-geometry outputs;
- suspension forces or structural loads;
- compliance, backlash, bearing/joint limits, or packaging;
- body heave/roll/pitch equilibrium;
- tire or aero models;
- installed/as-built claims.

## User input currently required

None for the first rigid mechanism implementation.

The first likely future data request is a reviewed wheel-center/wheel-plane construction or source if we want the suspension module—not an external downstream adapter—to become authoritative for wheel-center travel and wheel-plane state. The rear origin relationship will also need explicit review before a complete front-to-rear 3D vehicle scene is considered authoritative.

## Next action after merge

Implement `AUTH-SUSP-0001` in a separate PR, run `BENCH-SUSP-0001` through `0003`, emit provider-compatible front zero-steer poses, and keep every excluded output unavailable with a reason rather than inferred.

# WUFR road-contact assumption failure audit

## Purpose

This audit records the first implementation probe of `AUTH-VEH-0006` / `ASM-VEH-0004` and prevents a failed source interpretation from being converted into a working-looking compatibility model by weakening verification.

## What the merged authorization required

`ASM-VEH-0004` proposed that the nominal WUFR-26 OptimumK `Contact Patch` output could be treated, for a first rigid-road prototype, as a fixed point attached to the upright/wheel assembly. `BENCH-VEH-0008` made that assumption falsifiable: selected historical front-left pure-heave rows had to be reconstructed by the already verified minimum-twist upright transport plus the independently reconstructed 3D source steering twist, with no use of the OptimumK scalar `Steer Angle`.

The required maximum point disagreement was `5e-6 m`.

## PR #64 implementation probe

PR #64 implemented exactly that composition rather than adding a duplicate suspension or steering equation. Its focused test used:

- `MOD-SUSP-0002` / `EQ-SUSP-0003` minimum-twist upright transport;
- `EQ-SUSP-0008` reconstructed historical 3D source twist;
- the nominal front-left source contact observation `[0, 0.61598556, 0] m`;
- the selected historical rows already frozen in `WUFR26_ROAD_CONTACT_REFERENCE_V0`.

The source-consistency check failed with a maximum Euclidean point disagreement of

`0.0008458158026623031 m` (`0.845816 mm`).

That is about `169.16x` the required `0.005 mm` tolerance. This is not a finite-difference or equilibrium-convergence issue.

## Why the failure is meaningful

The frozen OptimumK result itself gives a second semantic clue. In the selected pure-heave rows, the exported `Contact Patch Z` remains on the source road plane. After applying the already reviewed body re-reference, the listed body-frame contact z is exactly the opposite of the imposed body heave:

- `heave=-25.4 mm -> contact z=+25.4 mm`;
- `heave=-5.08 mm -> contact z=+5.08 mm`;
- `heave=0 -> contact z=0`;
- `heave=+5.08 mm -> contact z=-5.08 mm`;
- `heave=+25.4 mm -> contact z=-25.4 mm`.

That behavior is consistent with OptimumK reporting a **road-contact solution/output**, not with the channel proving that one material point remains rigidly attached to the upright throughout motion.

The source therefore supports the nominal contact-output observation, but it does **not** support `ASM-VEH-0004` as a source-validated arbitrary-state contact map.

## What did not fail

The implementation probe also showed that the surrounding architecture is viable:

- the physical wheel-coordinate inversion can be composed corner-by-corner;
- the front centered-rack steering closure can be composed after the unresolved suspension pose;
- scalar road-gap roots can be solved without track-width or crossweight shortcuts;
- a body-to-wheel Jacobian and work-conjugate point-force projections can be differentiated numerically.

Those numerical successes do not rescue the contact assumption. They are implementation evidence only and PR #64 remains unmerged.

## Authority correction

`AUTH-VEH-0007` suspends the implementation permission granted by `AUTH-VEH-0006` for the current contact assumption. `MOD-VEH-0006` is blocked until a replacement contact model/source assumption is reviewed.

The following remain explicitly prohibited as substitutes:

- body-roll-times-track or half-track wheel travel;
- direct left/right wheel-travel difference as a whole-vehicle closure;
- scalar spring/ARB motion ratio;
- hard-coded `c_i=1` or `Q_u=-49.05 N` away from independently verified limiting states;
- hidden crossweight/load-transfer repair;
- using OptimumK scalar `Steer Angle` as the front rotation;
- simply relabeling the failed rigid attached-point interpretation as a tire model.

## Realistic replacement paths

Two defensible paths are currently visible, but neither is authorized by this audit.

### 1. Explicit low-fidelity rigid circular tire reference

Use the already reviewed physical wheel center and wheel-plane orientation together with a reviewed nominal tire radius to define an ideal zero-width circular tire/road tangency point geometrically. This would be a new, explicit low-fidelity tire/contact assumption. It must state its limitations: no loaded radius, finite tread width, carcass deflection, footprint migration, or vertical stiffness.

This path is attractive for the first static R&D equilibrium because it is deterministic, work-conjugate, and does not pretend the OptimumK `Contact Patch` channel is a material point. It still requires a new authorization and independent geometric/limiting-case benchmarks.

### 2. Physical/empirical contact or loaded-radius authority

Measure or otherwise source a loaded-radius/contact model and use it as the road compatibility provider. This is higher-value for as-built correlation but requires more evidence and likely delays the first whole-car static equilibrium result.

## Next gate

Do not restart `MOD-VEH-0006` implementation yet. First review which contact fidelity is actually needed for the next design decision, freeze the replacement model/assumption and verification plan, and only then reopen implementation.

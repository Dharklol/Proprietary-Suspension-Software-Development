# Phase 2 whole-vehicle force-coordinate implementation review

## Review status

**Review-ready implementation for PR #46.**

This review covers the implementation of `MOD-VEH-0003` under the authorization merged in PR #45. It does not expand that authorization.

## Implemented scope

PR #46 adds:

- `src/pssd_vehicle/force_coordinates.py`;
- exact yaw-pitch-roll body-fixed point transport (`EQ-VEH-0004`);
- explicit point-force/free-couple wrench translation and summation (`EQ-VEH-0005`);
- signed generalized-force mapping through `Q=J_r^T F + J_omega^T M` (`EQ-VEH-0006`);
- an analytical local yaw-pitch-roll Jacobian and an independent centered `h` versus `h/2` numerical verification path using SO(3) rotation-log increments;
- flat-road, vertically rigid, all-four-active contact classification (`EQ-VEH-0007`);
- explicit wheel-lift failure with the negative supplied normal reaction retained rather than clipped;
- a reviewed WUFR-26/27 design-intent whole-vehicle frame adapter;
- `BENCH-VEH-0003` and `BENCH-VEH-0004` tests, runner, and frozen result record.

No spring, damper, ARB, tire, aero, brake, gravity, or inertia force law is introduced. No heave/roll/pitch equilibrium, wheel-load solve, linkage-force solve, stress calculation, contact-mode switch, or installed-limit calculation is reachable through this interface.

## WUFR source review

### CAD identity

The adapter records the live Box identities reviewed for this PR:

- `SU-00001-AA 2026 SUSPENSION GEOMETRY.SLDPRT`, Box `1943897977651`, version `2546941960247`, SHA-1 `2cfb771f296961be0857161f7b57a6c178180d7a`;
- `FSA SUSPENSION.SLDASM`, Box `1966637303418`, version `2547286736404`, SHA-1 `cfb95b650db19ca0624eaf82f272690aa70625df`.

The reviewer-supplied SolidWorks metadata exports distinguish suppression separately from visibility. Suppressed entries are excluded from the active vehicle configuration; hidden but unsuppressed construction is not discarded merely because it is hidden. The active FSA assembly shows the top-level rear ARB suppressed. This is source/configuration evidence only and does not authorize an ARB force model.

The geometry export establishes a common right-handed CAD frame and reviewed nominal references:

```text
+x forward, +y vehicle left, +z upward
front axle center = [ 0.000000, 0, 0.228600] m
rear axle center  = [-1.562400, 0, 0.228600] m
front track       = 1.231972 m
rear track        = 1.206572 m
```

The export run's transformed `model_x_m/model_y_m/model_z_m` sketch-point fields were found unreliable. The frozen adapter therefore uses raw 3D-sketch and SolidWorks reference-point coordinates only. Exact reviewed export hashes are retained in the adapter record.

### CG source separation

The reviewer supplied two distinct scale states, confirmed in pounds.

Driver / no fuel:

```text
LF=178, RF=175, LR=163, RR=159
x_CG_source = -0.7453226666666667 m
y_CG_source = +0.006312743703703716 m
```

The `0.290 m` CG-height value was clarified by the reviewer to come from a separate tilt test with ballast used to simulate a driver. The scale session and tilt-test session are not proven to be the same physical setup. Therefore the combined driver/no-fuel 3D CG point is explicitly labeled **source-separated design-intent analysis authority**, not same-session metrology or installed/as-built authority.

No driver / no fuel:

```text
LF=113, RF=104, LR=126, RR=134
x_CG_source = -0.8516226415094339 m
y_CG_source = +0.0015043731656184725 m
```

No no-driver-state vertical CG coordinate has been supplied. The `0.290 m` driver-equivalent tilt value is not reused or relabeled for this state.

The reviewer also supplied measured unsprung mass of `10 kg` for the front axle and `10 kg` for the rear axle (`20 kg` total). That measurement is retained only for later mass/QSS authorization and is not consumed by this mechanics layer.

## Contact-reference review

The first contact model remains exactly the PR #45 model: flat road, vertically rigid tires, all four contacts active.

For the WUFR design-intent adapter, the nominal road datum is source `z=0`. The four contact **reference points** are the frozen axle/track stations projected to this plane. They are model points for evaluating the rigid contact gap; they are not physical tire footprint centroids, loaded-radius measurements, contact-patch geometry, or installed ride-height metrology.

The classifier does not generate normal loads. It accepts an externally supplied normal reaction only to test admissibility. A negative reaction returns `wheel_lift` and preserves the negative corner value.

## Static corner-weight interpretation

PR #46 deliberately does not attempt to reproduce the four measured scale readings from CG location.

For four vertical road reactions, rigid-body vertical-force, roll-moment, and pitch-moment equilibrium provide three independent equations. The diagonal load split remains statically indeterminate until spring/preload/ride-height/ARB/compliance compatibility or a measured imposed corner-load condition is introduced.

The no-driver state illustrates this directly: it is almost laterally centered yet has roughly `51.78%` LF+RR crossweight. Building a hidden crossweight rule into `MOD-VEH-0003` would therefore be physically and architecturally wrong.

## Numerical review

`BENCH-VEH-0003` uses synthetic geometry independent of WUFR data. It checks:

- identity and elemental rigid rotations;
- exact cross-product wrench moment arms;
- reference-point translation consistency;
- analytical generalized forces against the centered numerical Jacobian path;
- structured frame and Jacobian failures.

The analytical angular-variation Jacobian does not assume Euler-coordinate increments equal inertial rotation-vector increments. The finite-difference path obtains the angular increment from `R_plus R_minus^T` and checks convergence at `h` and `h/2`.

`BENCH-VEH-0004` checks:

- contact-gap sign;
- valid four-contact classification;
- negative-reaction wheel lift without clipping;
- unsupported contact fidelity;
- WUFR design-intent axle/track/contact placement;
- continued rejection of an incomplete wheelbase-only adapter;
- absence of linkage-force outputs.

The frozen benchmark record is `benchmarks/vehicle/vehicle_force_coordinate_result_v0.1.0.toml`.

## Authority decision

The implementation is suitable as the common mechanics layer for later separately authorized suspension-force, QSS, and ideal linkage-statics work.

It is **not** authority for:

- spring/damper/ARB/tire forces;
- total or corner wheel loads generated from mass/CG;
- heave/roll/pitch equilibrium;
- tire radial compliance or alternate contact modes;
- linkage/member/bearing reactions;
- stress, fatigue, buckling, FEA release, or compliance;
- installed/as-built geometry, setup, stops, ride height, or production performance.

## Next gate after review

The next vehicle-dynamics dependency should remain separate from `MOD-VEH-0003`: authorize the first suspension elastic force element and its exact generalized-force/energy mapping before any quasi-static equilibrium solver is allowed to consume it. Coupled ARB behavior remains a separate subsequent authorization.

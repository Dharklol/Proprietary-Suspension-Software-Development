# Whole-vehicle force-coordinate implementation v0.1.0

## Scope

This document records the first implementation of `MOD-VEH-0003` under `AUTH-VEH-0003`.
The implementation is intentionally limited to:

- rigid body-fixed point transport using `R_IB = R_z(psi) R_y(theta) R_x(phi)`;
- point-force/free-couple wrench translation and summation about explicit reference points;
- signed generalized-force mapping for `q=[z_s, phi, theta]` through virtual work;
- a centered numerical Jacobian verification path with an `h` versus `h/2` convergence check;
- flat-road, vertically rigid, all-four-active contact classification;
- one explicit WUFR-26/27 design-intent whole-vehicle frame adapter.

No constitutive force law, body equilibrium, wheel-load generation, linkage-force solve, stress,
installed limit, or optimization is added.

## Implementation package

`src/pssd_vehicle/force_coordinates.py`

The public contracts are immutable dataclasses with explicit frame/origin/source fields. Frame or
origin mismatch is a structured failure rather than a hidden coordinate conversion.

### Point transport — `EQ-VEH-0004`

For a body-fixed point `r_B`,

```text
r_I = r_O + [0,0,z_s] + R_z(psi) R_y(theta) R_x(phi) r_B
```

The implementation refuses points not explicitly declared `body_fixed` and does not mirror or
translate suspension-local coordinates implicitly.

### Wrench assembly — `EQ-VEH-0005`

For a force/couple applied at `P` and reported about `O`,

```text
F_O = F
M_O = M_P + (r_P-r_O) cross F
```

All contributions must already share one frame and origin before summation.

### Generalized force — `EQ-VEH-0006`

The exact local point Jacobian for `q=[z_s,phi,theta]` is evaluated analytically. The compatible
inertial angular-variation columns are:

```text
delta omega / delta z_s = 0
delta omega / delta phi = R_z(psi) R_y(theta) e_x
delta omega / delta theta = R_z(psi) e_y
```

and

```text
Q = J_r^T F + J_omega^T M.
```

A second path evaluates centered pose differences. Translational columns use direct centered point
positions; rotational columns use the logarithm of `R_plus R_minus^T` so the angular variation is
expressed in the inertial frame. The requested step is halved once and the two generalized-force
vectors must converge within the declared scaled tolerance.

No absolute value or scalar motion-ratio substitution is used.

### Rigid four-contact classification — `EQ-VEH-0007`

The classifier accepts only `flat_rigid_four_contact` in this slice. For each corner,

```text
g_i = n_road dot (r_contact_i-r_road)
```

and an externally supplied normal reaction may be checked. The classifier never calculates a
reaction from mass, CG, spring rates, or load-transfer equations. A negative supplied reaction is
retained in the result and returns `wheel_lift`; it is never clipped or redistributed.

## WUFR whole-vehicle adapter

`data_catalog/wufr26_whole_vehicle_frame_v0.toml` freezes the explicit adapter used by this model.

The native suspension CAD source is the WUFR-26 geometry part in the active `Default`
configuration. The reviewed unsuppressed source references establish:

```text
front axle center = [ 0.000000, 0, 0.228600] m
rear axle center  = [-1.562400, 0, 0.228600] m
front track       = 1.231972 m
rear track        = 1.206572 m
```

The source frame is already right-handed `+x` forward, `+y` vehicle left, `+z` upward.

The first body origin is a named **no-driver design-intent CG reference**, not an installed/as-built
claim. Its planar coordinates are calculated from the reviewer-supplied no-driver/no-fuel scale
readings and the frozen CAD contact stations:

```text
LF=113 lb, RF=104 lb, LR=126 lb, RR=134 lb
x_CG_source = -0.8516226415094339 m
y_CG_source = +0.0015043731656184725 m
```

Its vertical coordinate `z=0.290 m` comes from the separate no-driver CG-height entry in the 2026
FSAE Design IC spec sheet. The two sources are not asserted to represent the same physical mass or
setup state. The combined 3D point is therefore explicitly design-intent analysis authority only.

The reviewer also supplied a distinct **driver/no-fuel** scale state:

```text
LF=178 lb, RF=175 lb, LR=163 lb, RR=159 lb
x_CG_source = -0.7453226666666667 m
y_CG_source = +0.006312743703703716 m
```

No driver-state `z_CG` is authorized in this PR. The no-driver `0.290 m` value must not be reused
for that state.

### Road and contact references

For the authorized first vertically rigid contact model, the nominal road datum is frozen as source
`z=0`. Four **contact reference points** are defined at the frozen axle station and wheel-center
track station projected to that plane. These are deterministic model references used to close the
rigid contact gap. They are not tire footprint centroids and are not installed tire-contact
metrology.

The adapter loader consumes only the frozen source record. It does not regenerate the CG from
unrelated values or use wheelbase alone to create a rear/front transform.

## Source-state filtering

The SolidWorks export preserves suppression separately from visibility. The source audit treats:

- suppressed geometry/components as excluded from the active physical configuration;
- unsuppressed hidden geometry as eligible design/reference geometry;
- visibility alone as insufficient to decide whether an item exists.

The current FSA assembly shows the top-level rear ARB suppressed. This is recorded only as source
context; this PR does not implement any ARB physics.

The exporter model-space columns for sketch points were found unreliable in this run. The adapter
therefore uses only raw 3D-sketch coordinates and SolidWorks reference-point coordinates, not the
exported `model_x_m/model_y_m/model_z_m` sketch columns.

## Verification

`BENCH-VEH-0003` verifies exact synthetic point transport, wrench translation, reference-point
behavior, and analytical-versus-centered generalized force.

`BENCH-VEH-0004` verifies contact-gap sign, valid four-contact classification, explicit wheel lift,
WUFR frame/axle/track placement, and the absence of installed authority.

The frozen result is `benchmarks/vehicle/vehicle_force_coordinate_result_v0.1.0.toml` and is
regenerated by `scripts/run_vehicle_force_coordinate_benchmarks.py`.

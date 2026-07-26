# Whole-vehicle force-coordinate function specification

## Status

Reviewed implementation specification for `MOD-VEH-0003` under `AUTH-VEH-0003`; PR #46 implements this bounded interface after PR #45 authorization.

No implementation may add constitutive force laws, equilibrium solving, linkage loads, or installed authority under this specification.

## 1. Responsibilities

The implementation provides four bounded mechanics primitives:

1. transport an explicitly body-fixed point into a declared road/inertial frame;
2. translate and assemble force/couple wrenches about a named reference point;
3. map applied actions into signed generalized forces through virtual work;
4. classify the initial flat-road rigid four-contact state.

It must also preserve source/configuration identity and return structured failures for missing frames, origins, contact authority, unsupported fidelity, and numerical-Jacobian problems.

## 2. Canonical frames and coordinates

### 2.1 Body frame

The whole-vehicle body frame is right-handed:

- `+x`: forward;
- `+y`: vehicle left;
- `+z`: upward.

Every point must record:

- frame identifier;
- origin identifier;
- position in meters;
- source/configuration authority;
- whether it is body-fixed, road-fixed, or externally supplied.

A source-local suspension point is not automatically a whole-vehicle body-frame point.

### 2.2 Road/inertial frame

The first road frame contains:

- road-plane reference point `r_road`;
- unit road normal `n_road`;
- body-origin position `r_O`;
- body orientation relative to the road frame.

The first bounded model supports a flat plane only. A road plane or contact snapshot may be expressed in another explicitly named compatible frame only when both the plane and every point declare that same frame/origin; this does not create a hidden transform.

### 2.3 Body pose

Use the yaw-pitch-roll rotation

```text
R_IB = R_z(psi) R_y(theta) R_x(phi)
```

and point transport

```text
r_I = r_O + R_IB r_B.
```

The first future QSS coordinate order is frozen as

```text
q = [z_s, phi, theta]
```

with:

- `z_s`: body-origin upward translation, meters;
- `phi`: positive roll about body `+x`, radians;
- `theta`: positive pitch about the intermediate/body lateral axis according to the declared yaw-pitch-roll convention, radians.

`MOD-VEH-0003` evaluates mechanics at an explicitly supplied `q`; it does not solve `q`.

## 3. Data contracts

### 3.1 Point reference

A point record contains at minimum:

```text
point_id
frame_id
origin_id
position_m = [x, y, z]
attachment/body role
source_id
configuration_id
authority
```

### 3.2 Applied wrench

An applied action contains:

```text
wrench_id
frame_id
origin_id
application_point_id
force_N = [Fx, Fy, Fz]
free_couple_Nm = [Mx, My, Mz]
source/model authority
```

A force may not omit its application point. A pure free couple may use a declared reference point for reporting, but its physical value is reference-independent.

### 3.3 Resultant wrench

The result includes:

```text
reference_point_id
resultant_force_N
resultant_moment_Nm
per_contribution translated moments
force-balance-ready diagnostics
source/model provenance
```

### 3.4 Generalized-force result

The result includes:

```text
coordinate_order
coordinate_units
Q
J_r
J_omega
jacobian_method
requested and actual steps
virtual_work_residual
conditioning/status
```

For `q=[z_s,phi,theta]`, the expected units are `[N,N*m,N*m]`.

### 3.5 Contact result

Per corner, report:

```text
corner identity
contact_reference_point
road-normal gap g_i
normal reaction lambda_i, when externally supplied
active-contact flag
status
failure code
```

Aggregate status must distinguish:

- `four_contact_admissible`;
- `open_gap`;
- `penetration`;
- `wheel_lift`;
- `contact_mode_invalid`;
- `unsupported_contact_model`;
- `missing_authority`.

## 4. Equations

### 4.1 Point transport — `EQ-VEH-0004`

```text
r_I = r_O + R_z(psi) R_y(theta) R_x(phi) r_B
```

No hidden translation, mirroring, or source-origin inference is allowed.

### 4.2 Wrench translation — `EQ-VEH-0005`

For a point force `F` and free couple `M_P` applied at `P`, reported about `O`:

```text
F_O = F
M_O = M_P + (r_P-r_O) cross F
```

Multiple actions are summed only after every contribution is expressed in one compatible frame and about the same reference point.

### 4.3 Generalized force — `EQ-VEH-0006`

```text
delta_W = F dot delta_r_P + M dot delta_omega
Q = J_r^T F + J_omega^T M
```

where:

```text
J_r = partial r_P / partial q
J_omega maps delta_q to the compatible infinitesimal angular variation.
```

The implementation must not assume `J_omega` is the identity for finite yaw-pitch-roll angles. PR #46 uses the exact local yaw-pitch-roll angular-variation mapping for the analytical path and independently verifies it with centered pose differences and an SO(3) rotation-log increment.

### 4.4 Rigid contact — `EQ-VEH-0007`

```text
g_i = n_road dot (r_contact_i-r_road)
lambda_i = n_road dot F_contact_i
```

The initial active contact mode requires:

```text
g_i = 0
lambda_i >= 0
```

for all four corners.

## 5. Numerical Jacobian policy

Analytical Jacobians are preferred where simple. A centered finite difference is allowed when:

- the coordinate step is declared per coordinate;
- both perturbed states stay on the same upstream suspension/actuation branch when an upstream state is involved;
- the point map succeeds at both neighbors;
- at least two step sizes demonstrate convergence;
- the synthetic virtual-work benchmark passes;
- the actual step and convergence diagnostic are returned.

PR #46 implements the point/pose numerical check without an upstream bounded suspension state. The requested step is evaluated at `h` and `h/2`; the finer result is returned only after the generalized-force difference satisfies the declared scaled convergence tolerance.

One-sided differences are not needed in this first unconstrained coordinate primitive. Later bounded suspension/contact states require their own reviewed rule.

No derivative may:

- cross an unavailable kinematic state;
- silently use a different rocker/upright branch;
- clip a coordinate;
- use an absolute value to hide sign;
- silently convert a scalar motion ratio into a multidimensional Jacobian.

## 6. WUFR adapter boundary

The implementation may consume WUFR-26/27 geometry only through an explicit reviewed adapter. The design-intent adapter for PR #46 is `data_catalog/wufr26_whole_vehicle_frame_v0.toml`.

Allowed now:

- preserve WUFR-27 inheritance of WUFR-26 suspension geometry;
- preserve front/rear/left/right identity;
- use the reviewed unsuppressed SolidWorks CAD references to freeze the common source axes, front/rear axle centers, front/rear tracks, and nominal `z=0` road datum;
- transform those explicitly frozen source positions to a named body/CG reference using the adapter's stored transform;
- use the specifically reviewed driver/no-fuel corner-scale state to establish the primary named planar CG reference;
- retain the separately sourced `0.290 m` tilt-test CG height as a distinct driver-equivalent provenance contribution because the test used ballast to simulate a driver;
- combine those two driver-related sources only as an explicitly source-separated driver/no-fuel **design-intent** body reference, not same-session metrology;
- retain the no-driver/no-fuel planar CG as a separate state with `z_CG` unavailable;
- retain the reported `10 kg` front-axle and `10 kg` rear-axle unsprung masses as future mass-model evidence only; they are not consumed by this model;
- define deterministic rigid-contact **reference points** at the frozen axle/track stations projected to the nominal road plane;
- return `missing_transform_authority` for any source/configuration that lacks equivalent explicit placement authority.

Not allowed:

- place front and rear source-local origins using wheelbase alone;
- derive a generic CG transform from arbitrary corner weights or a legacy spreadsheet without a reviewed named measurement state and geometry basis;
- relabel the `0.290 m` driver-equivalent tilt-test value as a no-driver CG height;
- treat the composite driver/no-fuel design reference as same-session or installed metrology;
- use the reported unsprung masses to generate gravity/inertia/wheel loads under this authorization;
- construct a physical tire footprint centroid, loaded radius, or compliance model from tire diameter/width;
- treat the projected rigid-contact references as physical contact-patch metrology;
- call the CAD geometry, scale-derived adapter, or contact references installed/as-built.

The SolidWorks metadata export distinguishes suppression from visibility. Suppressed components/features are excluded from the active configuration; hidden but unsuppressed reference/optimization geometry may remain valid design evidence. PR #46 does not use the exporter run's unreliable transformed `model_x_m/model_y_m/model_z_m` sketch-point columns.

## 7. Contact policy

The initial flat-road rigid-contact model is a classification layer, not a force solver.

It may check externally supplied normal reactions. It may not calculate them from total mass, CG, corner weights, or load-transfer equations.

A negative normal reaction must produce a failed four-contact state. The failure result retains the negative value and corner identity for diagnosis. It must not:

- replace it with zero;
- redistribute the deficit;
- remove the corner and continue;
- declare convergence.

The measured static corner weights are not a target for this contact classifier. Four vertical reactions are not uniquely determined by rigid-body force/roll/pitch equilibrium alone; diagonal load split requires later elastic/preload/compatibility authority.

Later contact-mode enumeration or complementarity requires separate authorization.

## 8. Linkage-force downstream contract

`ASM-SUSP-0001` freezes the intended first linkage fidelity, but `MOD-VEH-0003` exposes no linkage-force function.

A later solver may consume the resultant external wrenches and explicit application points from this layer. That later authorization must define:

- rigid bodies included;
- every two-force member and centerline;
- joint roles;
- pushrod ownership on the A-arm;
- spring/ARB force source;
- brake torque reaction path;
- unsprung inertia treatment;
- matrix rank and conditioning;
- residual acceptance;
- FEA/stress boundary.

## 9. Failure codes

The implementation provides or preserves structured codes including:

```text
nonfinite_input
invalid_frame
invalid_origin
frame_mismatch
missing_transform_authority
invalid_rotation
invalid_reference_point
invalid_road_normal
unsupported_contact_model
open_contact_gap
penetrating_contact_reference
negative_normal_reaction
contact_mode_invalid
jacobian_unavailable
jacobian_not_converged
missing_authority
unsupported_force_law
unsupported_equilibrium_request
unsupported_linkage_force_request
```

An unavailable future force law/equilibrium/linkage operation is not silently approximated by this module; those scopes remain absent from the public implementation interface.

## 10. Benchmark requirements

### `BENCH-VEH-0003`

- exact point rotations/translations;
- exact wrench moment arms and summation;
- reference-point translation consistency;
- analytical versus centered finite-difference generalized force;
- frame/origin and Jacobian failure behavior.

### `BENCH-VEH-0004`

- contact-gap sign;
- valid four-contact classification;
- explicit negative-reaction wheel lift with the negative value preserved;
- unsupported contact fidelity;
- WUFR-27 suspension-geometry inheritance;
- successful use of the separately reviewed WUFR design-intent placement adapter;
- continued rejection of a wheelbase-only/incomplete transform fixture;
- no linkage-force outputs.

## 11. Result authority

Every output is labeled with one of these practical roles:

- synthetic benchmark result;
- source-local suspension geometry/state;
- explicit design-intent whole-vehicle placement;
- installed/as-built measurement;
- unavailable.

PR #46 implements only synthetic mechanics and explicit design-intent WUFR placement. It does not create an installed/as-built result, force-law result, wheel-load prediction, equilibrium solution, or linkage-load result.

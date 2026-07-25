# MOD-SUSP-0002 wheel-reference and physical-state adapter specification

**Status:** preimplementation specification for `AUTH-SUSP-0002`  
**Upstream:** `MOD-SUSP-0001`  
**Geometry baseline:** `WUFR27_SUSPENSION_BASELINE_V0`  
**First scope:** source-bounded wheel reference, rigid transport, physical vertical-state inversion, and historical source-steering removal

## 1. Architectural purpose

`MOD-SUSP-0001` now solves the rigid double-wishbone mechanism and returns an upright reference transform, but intentionally does not define a wheel-center point or a user-facing physical wheel-travel coordinate. `MOD-SUSP-0002` fills only that boundary.

The front chain becomes:

```text
reviewed WUFR source wheel setup
    -> EQ-SUSP-0005 nominal wheel reference
MOD-SUSP-0001 q_L state
    -> EQ-SUSP-0003 minimum-twist unresolved-steering upright transform
    -> EQ-SUSP-0006 rigid wheel-reference transport
    -> optional SuspensionPoseSet / wheel-state outputs
    -> MOD-STEER-0001 front tie-rod steering closure
```

The rear chain becomes:

```text
reviewed WUFR source wheel setup
    -> EQ-SUSP-0005 nominal wheel reference
MOD-SUSP-0001 q_L state + EQ-SUSP-0004 rear toe-link closure
    -> EQ-SUSP-0006 rigid rear wheel-reference transport
```

A separate physical-coordinate adapter provides:

```text
requested body-frame delta_z_wc
    -> EQ-SUSP-0007 bounded inverse
    -> q_L
    -> MOD-SUSP-0001
    -> EQ-SUSP-0006 wheel/upright state.
```

No front steering equation is duplicated in this model.

## 2. Frames and alignment conventions

All calculations use the project canonical frame:

- `+x`: forward;
- `+y`: vehicle left;
- `+z`: upward;
- right-handed.

Side sign is

```text
s = +1 left
s = -1 right.
```

The static wheel-plane convention is reused from `src/pssd_steering/projection.py`:

- side-local positive toe means toe-out;
- side-local positive camber means the wheel top leans outward;
- road-plane heading at the centered state is `s * toe_out`.

Reusing the existing convention is an explicit architecture choice: suspension must not create a second toe/camber sign system that later needs reconciliation with steering.

## 3. EQ-SUSP-0005 — source-bounded nominal wheel reference

### 3.1 Source scope

The frozen WUFR-26 OptimumK setup uses zero longitudinal, lateral, and vertical wheel offsets at both axles. This first source adapter supports that exact case only.

Let

```text
R = D_tire / 2
h_t = source half-track
gamma = source static camber.
```

For the frozen zero-offset setup,

```text
x_wc,0 = 0
y_wc,0 = s [h_t + R sin(gamma)]
z_wc,0 = R cos(gamma).
```

This construction is not inferred from generic vehicle geometry. It is frozen because it exactly reconstructs the nominal wheel centers exported by the source OptimumK result.

The Box text representation gives half-track to 0.001 mm, while the result evidence exposes higher precision. The benchmark retains `615.98556 mm` front and `603.28556 mm` rear rather than silently rounding them to the display values `615.986` and `603.286 mm`.

### 3.2 Wheel plane

The nominal wheel-plane basis is constructed from source static toe/camber with the existing reviewed algorithm.

For side sign `s`, toe-out angle `tau`, and camber `gamma`:

```text
heading = s*tau
f_0 = [cos(heading), sin(heading), 0]
```

and the outward horizontal direction is

```text
o_0 = [-s sin(heading), s cos(heading), 0].
```

The wheel-plane outward normal is

```text
n_0 = cos(gamma) o_0 - sin(gamma) z_hat.
```

The implementation should call or share the reviewed static-alignment primitive rather than maintain a numerically separate copy if package dependencies can remain clean.

### 3.3 Explicit boundary

The following are not implied by this equation:

- nonzero OptimumK wheel-offset interpretation;
- tire loaded radius;
- tire deflection;
- a unique three-dimensional contact-patch point;
- force application location.

## 4. EQ-SUSP-0006 — rigid transport with the upright

Given an upstream rigid transform

```text
T(p) = R_u p + t_u,
```

transport the nominal wheel center as

```text
p_wc = T(p_wc,0)
```

and wheel-plane basis directions as

```text
n = R_u n_0
f = R_u f_0.
```

For a front corner, `R_u,t_u` are the `EQ-SUSP-0003` minimum-twist unresolved-steering transform. The tie rod has **not** yet rotated the upright. This is exactly the state expected by the existing `SuspensionPoseSet`/steering composition boundary.

For a rear corner, the final `MOD-SUSP-0001` transform may include the `EQ-SUSP-0004` rear chassis toe-link twist because the rear toe link is part of suspension location rather than a driver steering input.

The body-frame wheel-center displacement vector is simply

```text
Delta p_wc = p_wc - p_wc,0.
```

The first public physical scalar coordinate is its z component.

## 5. EQ-SUSP-0007 — physical vertical-state inversion

Define

```text
Delta z_wc,body(q_L) = z_wc(q_L) - z_wc(0).
```

Positive values mean the wheel center moved upward relative to the body/suspension frame.

For a requested physical state `z_req`, solve

```text
F(q_L) = Delta z_wc,body(q_L) - z_req = 0.
```

Each evaluation of `F` composes:

1. `MOD-SUSP-0001` at candidate `q_L`;
2. `EQ-SUSP-0006` wheel-reference transport;
3. extraction of current body-frame wheel-center z.

### 5.1 Branch and domain rule

The inverse remains on the suspension assembly branch connected to `q_L=0`. The implementation must use an explicit reviewed q_L interval and a bracket-preserving scalar method.

The state adapter must distinguish:

- requested displacement outside the reachable domain;
- no root bracket;
- multiple brackets / nonmonotonic ambiguity;
- upstream suspension branch loss;
- numerical nonconvergence.

It must not clip the request, extrapolate the mapping, or select an alternate assembly root merely because one exists.

### 5.2 Why the OptimumK result displacement channel is not the input

The frozen pure-heave workbook expresses wheel/chassis coordinates in a road-fixed/result convention. PR39 established that chassis points translate by the prescribed heave while upright/wheel coordinates are road-fixed in that export. Consequently the result channel `Wheel Center Displacement Z` is not automatically the body-relative wheel-center state used here.

For cross-tool validation, the source result must first be transformed into the reviewed body frame; only then is `Delta z_wc,body` formed.

## 6. EQ-SUSP-0008 — removal of source front steering

The historical front OptimumK pure-heave result contains tie-rod-constrained steering. The source provides enough 3D point geometry to remove that steering exactly for validation.

At a current state, let:

- `p_L`, `p_U`: current lower/upper upright joint centers;
- `p_T,src`: current source result upright tie point;
- `p_T,ref`: nominal upright tie point transported by the `EQ-SUSP-0003` minimum-twist reference;
- `k = normalize(p_U-p_L)`.

Define radius vectors

```text
a = p_T,ref - p_L
b = p_T,src - p_L
```

and project them perpendicular to `k`:

```text
a_perp = a - k(k dot a)
b_perp = b - k(k dot b).
```

The signed source upright twist is

```text
psi = atan2(
    k dot (a_perp cross b_perp),
    a_perp dot b_perp
).
```

For an upright-attached source point `p_src`, the unresolved-steering point is

```text
p_unresolved = p_L + R(k,-psi)(p_src-p_L).
```

For a direction vector, apply only `R(k,-psi)`.

### 6.1 Why the scalar OptimumK `Steer Angle` is excluded

The frozen workbook's scalar `Steer Angle` does not equal the actual 3D rotation about the current steering axis that maps the minimum-twist upright reference to the tie-rod-constrained source upright.

At `-25.4 mm` front heave, for example:

```text
source scalar Steer Angle     about -0.1534 deg
3D tie-point-derived twist    about -0.24354 deg.
```

Using the scalar channel to unsteer a 3D pose would therefore leave a systematic rotational error. The implementation must derive `psi` from 3D geometry and may report the scalar channel only as a descriptive comparison.

## 7. First result contract

A successful wheel-reference state should retain at least:

- configuration/source IDs and authority;
- axle and side;
- requested physical state, if inversion was used;
- solved `q_L` and upstream `MOD-SUSP-0001` state reference;
- nominal and current wheel-center coordinates;
- nominal/current wheel-plane normal and forward reference;
- `Delta z_wc,body`;
- front unresolved-steering rule or rear toe-link-closed role;
- inversion bracket, iterations, residual, and branch diagnostics;
- failure code/message when unavailable.

A historical source-steering-removal result additionally retains:

- source workbook identity/version;
- reconstructed `psi`;
- tie-point lever-arm conditioning;
- source-steered and unresolved-steering comparison roles;
- explicit statement that scalar `Steer Angle` was not used as the rotation input.

## 8. Frozen verification plan

### BENCH-SUSP-0004 — nominal wheel reference

Use `WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml` to verify all four source nominal wheel centers and front/rear wheel-plane bases.

The source-backed expected nominal wheel centers are:

```text
front left  [0, +0.6068611862194348, 0.2322308203127064] m
front right [0, -0.6068611862194348, 0.2322308203127064] m
rear left   [0, +0.5992294462199110, 0.2323746028312969] m
rear right  [0, -0.5992294462199110, 0.2323746028312969] m.
```

### BENCH-SUSP-0005 — source-steering removal

Use the existing 11-state front pure-heave fixture. For every state:

1. reconstruct `psi` from tie-point geometry;
2. unsteer the source wheel center;
3. compare it to the nominal wheel center transported only by the minimum-twist unresolved-steering transform.

The two should agree within the frozen tolerance. Representative scalar `Steer Angle` values must also be shown to differ from `psi`, preventing future accidental use of the wrong channel.

### BENCH-SUSP-0006 — physical state inversion

First use an analytical/synthetic monotonic fixture. Then use selected WUFR front states from the frozen pure-heave evidence, forming the requested physical coordinate from body-referenced wheel-center z. The inversion must recover the known source-derived q_L values on the nominal branch.

Failure cases include out-of-domain request, no bracket, ambiguous/multiple brackets, and upstream kinematic failure.

## 9. Source-origin and contact boundaries intentionally left open

The team has confirmed the WUFR wheelbase is `1.5624 m`. That is now a reviewed vehicle scalar. It does not prove which front/rear OptimumK local origin should be translated, by which sign, to form one authoritative whole-vehicle geometry scene. That adapter remains separate.

Likewise, this model does not need a generic tire contact-patch construction. A future tire/road model should define unloaded/loaded radius, deflection, road normal, and force application consistently with the tire model rather than baking those assumptions into rigid suspension kinematics.

## 10. Implementation boundary

`AUTH-SUSP-0002` authorizes only the equations and source adapters above. Motion ratio, pushrod/pullrod, rocker, damper, spring, ARB, roll-center/anti geometry, load transfer, tire force, compliance, and installed correlation remain separate follow-on work.
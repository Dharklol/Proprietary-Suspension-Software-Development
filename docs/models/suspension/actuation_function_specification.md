# MOD-SUSP-0003 rigid suspension actuation specification

**Status:** preimplementation specification for `AUTH-SUSP-0003`  
**Upstream:** `MOD-SUSP-0001`, `MOD-SUSP-0002`  
**Geometry baseline:** `WUFR27_SUSPENSION_BASELINE_V0`  
**First scope:** arm attachment transport -> push/pull-rod closure -> rocker pose -> ideal coilover displacement -> explicit local damper/wheel derivative

## 1. Architecture

The model is a downstream actuation layer. It does not modify the existing suspension closure.

```text
requested delta_z_wc_body
    -> MOD-SUSP-0002
    -> q_L + MOD-SUSP-0001 solved arm state
    -> EQ-SUSP-0009 arm-fixed push/pull attachment
    -> EQ-SUSP-0010 rocker closure
    -> EQ-SUSP-0011 coilover length/displacement
    -> EQ-SUSP-0012 local signed derivative
```

Front steering remains outside this chain. The actuation pickup belongs to the suspension arm and is independent of tie-rod steering rotation.

## 2. Frames and source roles

Project canonical frame remains `+x forward, +y vehicle left, +z upward`.

The frozen source role is asymmetric by axle:

- front: push/pull attachment is fixed to the **upper A-arm**;
- rear: push/pull attachment is fixed to the **lower A-arm**.

That role is data, not an inferred nearest-link association.

## 3. EQ-SUSP-0009 — arm-fixed actuation point

Let the owning A-arm hinge axis be represented by point `a` and unit direction `k`. Let `p_PP,0` be the nominal push/pull attachment.

```text
p_PP(q) = a + R(k,q_owner) (p_PP,0-a)
```

where

```text
q_owner = q_U   front
q_owner = q_L   rear.
```

The implementation should reuse the reviewed `EQ-SUSP-0001` rotation primitive. It must not move this point using the upright transform or wheel-center displacement directly.

## 4. EQ-SUSP-0010 — rocker closure

The nominal rocker is defined by:

- pivot `p_R`;
- axis point `p_A`;
- axis `k_R = normalize(p_A-p_R)`;
- rod pickup `p_Rod,0`;
- coilover pickup `p_Coil,0`.

At rocker angle `theta_R`:

```text
p_Rod(theta_R)  = p_R + R(k_R,theta_R)(p_Rod,0-p_R)
p_Coil(theta_R) = p_R + R(k_R,theta_R)(p_Coil,0-p_R).
```

Freeze the nominal push/pull length as

```text
L_PP = ||p_Rod,0-p_PP,0||.
```

Then solve

```text
g(theta_R) = ||p_Rod(theta_R)-p_PP(q)||^2 - L_PP^2 = 0.
```

### Branch rule

`theta_R=0` is the nominal source branch. Subsequent states must remain on the continuous branch connected to zero.

A second mathematical root is not permission to jump assembly mode. If continuation does not uniquely identify the correct root, return an ambiguity failure.

Required diagnostics include:

- solved `theta_R`;
- bracket/search interval or equivalent geometric branch descriptor;
- rod-length residual;
- rocker-axis conditioning;
- upstream state identity;
- explicit failure code.

## 5. EQ-SUSP-0011 — ideal coilover displacement

With fixed chassis eye `p_D,ch` and current rocker eye `p_Coil`:

```text
L_d = ||p_Coil-p_D,ch||
L_d0 = ||p_Coil,0-p_D,ch||
delta_L_d = L_d-L_d0.
```

Sign convention:

- `delta_L_d > 0`: extension;
- `delta_L_d < 0`: compression.

This is an **ideal joint-center length**. It is not shaft position, available stroke, bump-stop engagement, gas volume, or force.

The frozen OptimumK `CoilOver Displacement` channel uses the same extension-positive scalar sign in the reviewed heave result and provides a direct source benchmark.

## 6. EQ-SUSP-0012 — explicit local actuation derivative

The project will not expose a naked scalar named only `motion_ratio`.

Define

```text
rho_dw = d(delta_L_d) / d(delta_z_wc_body)
```

where:

- numerator: ideal coilover length change, extension positive;
- denominator: body-frame wheel-center vertical displacement from `MOD-SUSP-0002`, upward positive.

The reciprocal

```text
rho_wd = 1/rho_dw
```

may be returned only when `rho_dw` is safely away from zero. Sign must be retained.

### Numerical evaluation

An analytic derivative is acceptable if the implementation remains transparent. Otherwise use a centered finite difference in the **physical wheel coordinate**:

```text
rho_dw(z) ~= [delta_L_d(z+h)-delta_L_d(z-h)]/(2h).
```

Requirements:

1. both neighbor states remain on the same suspension and rocker branches;
2. the actual `h` is retained in diagnostics;
3. no sample crosses an infeasible state;
4. at a reviewed boundary, a branch-preserving one-sided difference may be used and must be labeled as such;
5. an ill-conditioned derivative is unavailable, not replaced with zero/infinity.

## 7. Why OptimumK `Motion Ratio Heave` is not the canonical ratio

The historical result provides `Motion Ratio Heave` near `1.22` front and `1.00` rear. The historical inboard-suspension calculator also contains front `MR=1.22`, rear `MR=1`, and defines an installation ratio as its reciprocal.

Those are useful provenance and cross-check evidence, but the OptimumK heave input is a historical chassis/result motion coordinate. The project physical state is the body-relative wheel-center coordinate from `MOD-SUSP-0002`.

Therefore:

```text
OptimumK Motion Ratio Heave != definition of rho_dw.
```

The source channel may be reported alongside native results only with its original name/coordinate role.

## 8. Result contract

A successful actuation state should retain at least:

- source/configuration/axle/side IDs;
- upstream suspension and wheel-state identity;
- owning arm and current arm attachment point;
- nominal/current rocker rod and coilover pickup points;
- `theta_R`;
- nominal/current push/pull length and closure residual;
- nominal/current coilover length;
- `delta_L_d`;
- requested/current `delta_z_wc_body` when applicable;
- `rho_dw`, optional `rho_wd`, method and differentiation step;
- branch and feasibility diagnostics;
- explicit statement that installed stroke/stops were not evaluated.

## 9. Frozen verification plan

### BENCH-SUSP-0007 — analytical synthetic actuation

Use a simple planar one-axis rocker fixture with closed-form states to test:

- arm-attached point transport;
- nominal and nonzero rocker closure;
- exact rod-length preservation;
- coilover length/displacement;
- signed local derivative;
- unreachable closure;
- ambiguous second-root behavior;
- degenerate axis and reciprocal-conditioning failures.

### BENCH-SUSP-0008 — WUFR OptimumK cross-tool

Use `WUFR26_OPTIMUMK_ACTUATION_V0` and the existing pure-heave source evidence.

Across all eleven states from `-25.4` to `+25.4 mm` source heave, compare front and rear:

- ideal coilover length;
- ideal coilover displacement;
- rod-length closure;
- nominal-continuation rocker branch.

The frozen source precision is millimetric in the provider text representation, so the implementation acceptance tolerance is intentionally finite (`0.10 mm`) rather than pretending the exported display precision is micrometric.

The source `Motion Ratio Heave` values are retained to test terminology separation, not as target values for `rho_dw`.

## 10. Explicitly deferred

`AUTH-SUSP-0003` does not authorize:

- spring or damper forces;
- wheel rate / spring installation stiffness;
- damping rate/ratio;
- ARB kinematics, preload, or stiffness;
- force/virtual-work mapping;
- loads or member stress;
- compliance/friction/backlash;
- bump/droop stops, damper stroke, articulation, packaging, or clearance;
- installed/as-built authority;
- geometry optimization.

Those require later, separately sourced model packets.

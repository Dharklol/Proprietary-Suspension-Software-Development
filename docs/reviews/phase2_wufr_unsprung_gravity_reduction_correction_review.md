# Phase 2 WUFR compatible unsprung-gravity reduction correction review

## Review status

**Review-ready correction and implementation reauthorization.**

This review corrects only the reduced body equilibrium authorized by `AUTH-VEH-0009`. It does not change the WUFR mass allocation, rigid-circle contact model, suspension constitutive laws, ARB settings, solver, or result authority boundary.

## Why the correction is required

The draft `MOD-VEH-0007` implementation solved the authorized `EQ-VEH-0016` residual

```text
R_old = Q_sprung_gravity + J_wb^T Q_susp.
```

Tightening the road-root numerical tolerances allowed this residual to approach zero at the retained probe state:

```text
q_b = [-0.0026807702741682574,
       -0.00008013635009263544,
       +0.0026941883103072345]

R_old = [+3.632870630099205e-5 N,
         +8.863720509788564e-6 N*m,
         -8.93393380341223e-6 N*m]
```

However, the independently required physical road-frame closure remained

```text
F_res = [0, 0, -1.3778569402013403] N
M_res = [+0.007362280416703726,
         +0.5962048927027155,
          0] N*m,
```

far above the frozen `1e-6 N` and `1e-6 N*m` gates. The failure therefore is not a Newton tolerance, line-search, or road-root issue.

`EQ-VEH-0016` omitted the compatible reduced generalized force of the four `MOD-VEH-0005` unsprung gravity point loads. Those masses are not road-fixed. Their physical wheel-center points depend on body pose directly and through the eliminated road-compatible wheel coordinates. Consequently, their reduced generalized force is not zero.

## Correct chain rule

For corner `i`, let the physical wheel-center point be

```text
r_wc,i = r_wc,i(q_b, z_i)
```

and let `F_u,i=[0,0,-m_u,i g]` be the existing source-owned unsprung gravity point force.

At fixed physical wheel coordinate, `MOD-VEH-0003` supplies the exact local body-point Jacobian. The direct body contribution is

```text
Q_u,b,direct = sum_i J_r,wc_i^T F_u,i.
```

`MOD-VEH-0006` already supplies the wheel-coordinate projection

```text
Q_u,z,i = F_u,i dot partial(r_wc,i)/partial(z_i)
```

and the compatible wheel map `J_wb=partial(z_w)/partial(q_b)`. Therefore

```text
Q_u,red = Q_u,b,direct + J_wb^T Q_u,z.
```

The independent potential statement is

```text
Q_u,red = -d/dq_b [sum_i m_u,i g z_wc,i^road(q_b,z_w(q_b))].
```

At a representative bounded state near the failed continuation, the assembled term was approximately

```text
Q_u,b,direct = [-196.20000000000002,
                  +1.2404650178835475,
                  -7.036582971000492]

J_wb^T Q_u,z = [+194.8230908218273,
                  -1.2327608446851848,
                  +7.632491939166649]

Q_u,red = [-1.376909178172724,
            +0.007704173198362696,
            +0.5959089681661567].
```

A direct centered finite difference of total compatible unsprung gravitational potential gave the same term to sub-micro-unit agreement in this probe. The large direct and mapped contributions nearly cancel, which is precisely why neither may be silently omitted or replaced by total unsprung weight.

## Corrected body equilibrium

`EQ-VEH-0019` supersedes `EQ-VEH-0016`:

```text
R_b = Q_sprung_gravity
    + Q_u,red
    + J_wb^T Q_susp
    = 0.
```

The solver remains the existing `MOD-VEH-0004` bounded deterministic damped-Newton method. No alternate root finder, least-squares repair, fitted restart, or balancing wrench is introduced.

The wheel-coordinate contact recovery remains unchanged:

```text
lambda_i = -(Q_susp,i + Q_u,z,i) / c_i.
```

With the corrected body residual, the reduced-coordinate solve and the independent physical wrench closure describe the same gravity system.

## Verification decision

`BENCH-VEH-0014` is added before another integrated solve is accepted. It must:

1. verify the analytical direct term at nominal and bounded nonzero states;
2. verify the algebraic chain exactly;
3. compare the complete term against two-step finite differences of total compatible unsprung gravitational potential;
4. retain the failed old-equation probe as negative evidence;
5. fail closed for missing source, point, frame, order, or Jacobian data.

`BENCH-VEH-0012` then reruns the complete corrected equilibrium from both declared initial states and retains the original nonnegative-contact, energy-gradient, and `1e-6` physical closure requirements.

## Authority boundary

This correction provides mechanics consistency only. The result remains:

- driver/no-fuel design intent;
- centered rack;
- flat ideal rigid-circle road contact;
- prototype unsprung allocation;
- uncorrelated and not installed/as-built;
- not setup-selection, maneuver-QSS, carrier-wrench, structural-load-case, stress, fatigue, or production authority.

No new external source data are required for this correction because every term is composed from already reviewed physical points, masses, transforms, and generalized-force providers.

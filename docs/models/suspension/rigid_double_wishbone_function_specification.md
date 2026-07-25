# MOD-SUSP-0001 rigid double-wishbone kinematics function specification

**Status:** preimplementation specification for `AUTH-SUSP-0001`  
**Model:** `MOD-SUSP-0001`  
**Geometry baseline:** `WUFR27_SUSPENSION_BASELINE_V0`  
**First implementation scope:** rigid, ideal-joint position kinematics only

## 1. Purpose and architectural boundary

The first native suspension evaluator supplies source-grounded rigid suspension states to downstream vehicle and steering models. It must not become a second steering solver or a hidden load-transfer model.

The intended front chain is:

```text
reviewed suspension hardpoints
    -> MOD-SUSP-0001 wishbone position solve
    -> zero-steer upright reference transform
    -> SuspensionPoseSet
    -> MOD-STEER-0001 tie-rod steering closure
```

The intended rear chain is:

```text
reviewed suspension hardpoints
    -> wishbone position solve
    -> zero-twist upright reference
    -> rear chassis toe-link twist closure
    -> complete rear upright reference pose
```

This preserves the steering contract `upright_reference_pose_excludes_tie_rod_steering_rotation` and the PR38 distinction between the front steering tie rod and the rear chassis-locating toe link.

Guiggiani's vehicle model treats each independently suspended wheel hub as connected to the body by a one-degree-of-freedom linkage while steering is a separate wheel-angle input. Gillespie and Borg provide the corresponding independent/SLA suspension geometry context. The exact axis-angle implementation below is a project numerical formulation of rigid-link geometry, not a copied proprietary solver.

## 2. Frames, signs, and source state

All calculations use the canonical project orientation:

- `+x`: forward;
- `+y`: vehicle left;
- `+z`: upward;
- right-handed.

PR38 keeps front and rear OptimumK suspension-reference origins separate. No rear-to-front translation is applied in this specification.

For each A-arm, the hinge-axis direction is defined **fore inboard -> aft inboard**. The signed arm coordinate `q_A` follows the right-hand rule about that axis. `q_A` is an internal mathematical coordinate; it is not yet declared equivalent to wheel jounce, rebound, heave, roll, or damper travel.

The first public solver is parameterized by the lower-arm rotation `q_L`. A later state adapter may map a reviewed wheel/body displacement coordinate into this internal coordinate without changing the mechanism equations.

## 3. EQ-SUSP-0001 — exact rigid A-arm rotation

For an arm `A` with fore inboard point `a_A,F`, aft inboard point `a_A,A`, and nominal outboard joint center `p_A,0`, define

```text
e_A = (a_A,A - a_A,F) / ||a_A,A - a_A,F||.
```

For signed rotation `q_A`,

```text
p_A(q_A) = a_A,F + R(e_A,q_A) (p_A,0 - a_A,F)
```

where Rodrigues rotation is

```text
R(e,q)v = v cos(q)
         + (e x v) sin(q)
         + e (e dot v) [1-cos(q)].
```

This construction preserves distance from the outboard joint to both collinear inboard hinge points by rigid rotation; both physical arm-leg residuals are still reported as diagnostics.

A zero-length/degenerate hinge axis is an invalid geometry definition.

## 4. EQ-SUSP-0002 — upright joint-separation closure

The nominal rigid upright separation is

```text
L_K = ||p_U,0 - p_L,0||.
```

Given requested `q_L`, compute `p_L(q_L)` directly. Solve only `q_U` from

```text
f(q_U;q_L)
  = 0.5 [ ||p_U(q_U)-p_L(q_L)||^2 - L_K^2 ]
  = 0.
```

The exact derivative, useful for diagnostics or a safeguarded method, is

```text
df/dq_U
  = (p_U-p_L) dot { e_U x [p_U-a_U,F] }.
```

### Branch rule

The reviewed nominal assembly is

```text
q_L = q_U = 0.
```

Requested states must be evaluated on the geometric root branch continuously connected to that assembly. Branch continuity is part of feasibility. If the branch cannot be bracketed or becomes ambiguous, the state fails; the solver must not jump to another mathematical assembly mode.

### Numerical rule

The implementation must use a bracket-preserving scalar method such as bisection or a reviewed Brent-Dekker routine. Unconstrained Newton is not the default, and an alternate root must never be selected merely because it converges.

The solver reports the unsquared physical residual

```text
r_K = ||p_U-p_L|| - L_K.
```

## 5. EQ-SUSP-0003 — zero-steer upright reference transport

Once the wishbones locate `p_L` and `p_U`, define nominal and current kingpin/steering-axis directions

```text
k_0 = normalize(p_U,0-p_L,0)
k   = normalize(p_U-p_L).
```

The wishbones locate this line but, for the front suspension, do not determine physical twist about it because the steering tie rod closes that degree of freedom.

To create a deterministic provider reference, select the **shortest rotation** `R_align` that maps `k_0` onto `k` and adds no extra twist about `k`.

For nonparallel, non-antiparallel axes:

```text
c = k_0 dot k
s = ||k_0 x k||
n = (k_0 x k)/s
phi = atan2(s,c)
R_align = R(n,phi).
```

For same-direction parallel axes, `R_align=I`. Antiparallel axes are ambiguous and return a structured failure.

Anchor the rigid transform at the lower upright joint:

```text
p_ref = p_L + R_align (p_0-p_L,0).
```

All upright-local points and direction bases must use the same transform.

### Meaning of the minimum-twist rule

This is a **reference/gauge convention**, not a prediction that an unconstrained front upright physically takes the minimum-twist orientation. Its purpose is to provide a smooth deterministic zero-steer pose to the steering layer. `MOD-STEER-0001` subsequently applies the physical steering-axis rotation required by its reviewed tie-rod closure.

## 6. EQ-SUSP-0004 — rear chassis toe-link twist closure

PR38 records the rear source link as `chassis_locating_toe_link`; therefore it can locate the remaining rear upright twist.

Let `p_t,ref` be the rear toe-link outboard point after the zero-twist reference transport. Rotate it about the current kingpin axis through `p_L`:

```text
p_t(psi) = p_L + R(k,psi)(p_t,ref-p_L).
```

The nominal toe-link length is

```text
L_t = ||p_t,0-p_t,in||.
```

Solve

```text
g(psi)
  = 0.5 [ ||p_t(psi)-p_t,in||^2 - L_t^2 ]
  = 0
```

with derivative

```text
dg/dpsi
  = (p_t-p_t,in) dot [ k x (p_t-p_L) ].
```

The final rear upright rotation is

```text
R_rear = R(k,psi) R_align.
```

The admissible branch is continuous from `psi=0` at nominal. The front `steering_tie_rod` role is explicitly rejected by this rear closure function.

## 7. First result contract

A successful corner state should retain at least:

- corner identity and source/configuration IDs;
- requested `q_L`;
- solved `q_U`;
- solved lower and upper upright joint centers;
- kingpin/steering-axis line;
- rigid arm-leg and upright-separation physical residuals;
- zero-steer reference rigid transform;
- rear `psi` and toe-link residual when applicable;
- branch identity / continuation status;
- convergence iterations and bracket;
- singularity/conditioning diagnostic;
- feasibility and structured failure reason.

Front results may be adapted into the existing provider-neutral `SuspensionPoseSet` only with the unresolved-steering rule preserved.

Wheel center, wheel plane, contact patch, roll center, motion ratio, spring/damper travel, and ARB state are outside the first result contract.

## 8. Frozen verification plan

### BENCH-SUSP-0001 — analytical parallel arms

`GEO-SUSP-BASIC-001` uses two parallel `+x` hinge axes and equal 0.4 m arm radii. The exact solution is

```text
q_U = q_L
p_L = [0, 0.4 cos q, 0.4 sin q]
p_U = [0, 0.4 cos q, 0.2 + 0.4 sin q].
```

This verifies the basic geometry independently of OptimumK.

### BENCH-SUSP-0002 — WUFR front OptimumK pure heave

The source is `WUFR-26 8.21 Heaves 1inch.xlsx`, SHA-256 `db071b7e696149ec82213e9ed05aa557349d18d19debe7925e7e01058534e4b8`, OptimumK Result v2.3.0.

Direct inspection of this pure-heave result shows chassis hardpoint `z` coordinates translated by exactly the `Motion [Heave]` value while wheel/upright coordinates remain road-fixed. For this benchmark only, result points are therefore re-referenced into the source body-fixed suspension frame as

```text
p_body,optk = p_export,optk - [0,0,h]
```

before the already reviewed orientation/unit conversion

```text
p_body,can = 0.001 [x_optk,-y_optk,z_optk].
```

The adapter is intentionally **not** generalized to roll, pitch, or arbitrary OptimumK result exports.

The frozen 11-state right-front fixture supplies source-derived `q_L` as the independent input and comparison-only `q_U`, lower-joint, and upper-joint expectations. PR38 static hardpoints are rounded to 0.001 mm from the Box text representation while the result workbook exposes higher precision; a 2 micrometre point tolerance covers that source precision mismatch.

Front tie-rod, toe, steer-angle, and wheel-plane result channels are excluded because the OptimumK result already contains tie-rod-constrained steering.

### BENCH-SUSP-0003 — synthetic rear toe closure

A synthetic rear geometry gives the reference toe-outboard point a -10 deg azimuthal offset about a fixed vertical kingpin axis. A +10 deg solved twist must restore `[0.1,0,0.1] m` and the 0.3 m rigid toe-link length.

## 9. Source-origin issue intentionally left open

The OptimumK heave result places the nominal rear upright about `1562.4 mm` longitudinally behind the front result origin, matching the source setup's `Reference Distance` magnitude. PR38 deliberately kept static front/rear suspension sources in their local origins because the full origin semantics had not been reviewed.

This observation is retained as evidence only. The first suspension solver can operate per-corner without resolving it. A later whole-vehicle geometry/viewer adapter must explicitly review the origin relationship before translating rear states.

## 10. References

- Guiggiani, M., *The Science of Vehicle Dynamics*, 3rd ed., Springer, 2023: rigid-body vehicle model, independent suspension as a one-degree-of-freedom wheel-hub linkage, and suspension-geometry context.
- Gillespie, T. D., *Fundamentals of Vehicle Dynamics*, SAE: independent/SLA suspension geometry and roll-center background.
- Borg, L. T., *An Approach to Using Finite Element Models to Predict Suspension Member Loads in a Formula SAE Vehicle*, Virginia Tech, 2009: SLA suspension architecture, steering/articulation context, and Formula SAE suspension modeling.
- Project source: `WUFR-26 FINAL 8.21.2025.xlsx` frozen in PR38.
- External kinematics evidence: `WUFR-26 8.21 Heaves 1inch.xlsx` frozen in BENCH-SUSP-0002.

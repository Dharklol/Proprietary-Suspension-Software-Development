# Rigid Steering Evaluator — Function and Equation Specification

**Status:** Proposed preimplementation specification  
**Model:** `MOD-STEER-0001`  
**Equation IDs:** `EQ-STEER-0001` through `EQ-STEER-0007`  
**Migration:** `MIG-STR-0001`  
**Implementation authority:** Documentation only; no physics code is authorized by this document alone

## 1. Purpose

This document defines the calculation functions required for the first rigid, nominal-height steering evaluator. It records what each function computes, where its governing relationship comes from, why the relationship is appropriate, its assumptions and validity limits, and how it must fail.

The first evaluator is deliberately a mechanism calculation rather than a user-interface feature. It must answer the following questions reproducibly:

- where the rack inner joints are for a requested rack displacement;
- which left and right upright rotations satisfy rigid tie-rod closure;
- what total and incremental road-wheel headings result;
- which wheel is inside and outside for each turn direction;
- what the ideal low-speed Ackermann reference is;
- what turning radius and steering gains follow from the solved geometry;
- whether the mechanism remains on the intended branch and away from a singularity.

No polynomial, CAD motion-study export, tire model, or optimizer substitutes for this mechanism evaluator.

## 2. Model boundary

### Included in the first evaluator

- rigid rack, tie rods, uprights, and joints;
- one named nominal ride-height/reference configuration;
- three-dimensional steering-axis lines;
- exact rigid rotation of upright-fixed points about those axes;
- direct solution over rack displacement;
- total toe-inclusive wheel heading and incremental steer;
- exact low-speed Ackermann reference;
- turning radius to named reference paths;
- local gains, secant ratios, branch status, closure residual, and singularity diagnostics.

### Excluded

- suspension bump, rebound, roll, pitch, and heave motion;
- elastic compliance, backlash, friction, hysteresis, and joint clearance;
- steering effort, tire forces, aligning moments, trail, scrub, and rack loads;
- tolerance propagation and manufacturing variation;
- collision or packaging verification performed without a reviewed geometry adapter;
- transient vehicle response;
- tire-informed target generation and inverse-design optimization.

These exclusions are later model layers, not permission to hide them in effective constants.

## 3. Required frames and state

Internal calculations use the reviewed project body and road frames. Until the project-wide convention is frozen, every benchmark and implementation must state its frame explicitly.

The proposed body frame is:

- `+x` forward;
- `+y` vehicle left;
- `+z` upward;
- positive rotation by the right-hand rule.

A steering evaluation requires:

- a road-plane unit normal `n`;
- left and right steering-axis points `a_j` and unit directions `k_j`;
- left and right outer tie-rod points at the reference state `p_out,j,0`;
- left and right rack inner-joint points at rack center `p_in,j,0`;
- rack-axis unit direction `e_r`;
- tie-rod joint-center lengths `L_j`;
- wheel-frame forward vectors at the reference state;
- static left and right toe or an equivalent reviewed reference upright pose;
- mechanical road-wheel-angle bounds and rack-travel bounds;
- the intended mechanism branch at rack center.

Here `j` is `L` or `R`. Left/right remain canonical. Inside/outside are assigned only after turn direction is known.

## 4. Function inventory

| Proposed function | Governing ID | Purpose |
|---|---|---|
| `translate_rack_joint` | `EQ-STEER-0003` | Move each rack inner joint along the directed rack axis. |
| `rotate_point_about_axis` | `EQ-STEER-0003` | Rotate an upright-fixed point about its actual steering axis. |
| `tie_rod_closure_residual` | `EQ-STEER-0002` | Evaluate rigid link-length closure and a physical length residual. |
| `solve_road_wheel_state` | `EQ-STEER-0003` | Solve the intended left/right mechanism branches at one rack position. |
| `extract_road_wheel_heading` | `EQ-STEER-0003` | Convert the solved upright orientation into road-wheel yaw in the road plane. |
| `classify_inside_outside` | `EQ-STEER-0007` | Map left/right results to maneuver-dependent inside/outside aliases. |
| `ackermann_outside_reference` | `EQ-STEER-0001` | Calculate the exact no-slip low-speed outside-wheel reference. |
| `ackermann_error` | `EQ-STEER-0007` | Compare actual outside incremental steer with the declared reference. |
| `kinematic_turn_radius` | `EQ-STEER-0006` | Calculate named path radii under the no-slip kinematic construction. |
| `local_steering_gain` | `EQ-STEER-0005` | Calculate a local derivative with explicit numerator and denominator. |
| `secant_steering_ratio` | `EQ-STEER-0005` | Calculate a finite-interval ratio with explicit endpoints. |
| `evaluate_transmission_chain` | `EQ-STEER-0004` | Keep steering wheel, shaft, pinion, rack, and road-wheel relations separate. |
| `evaluate_steering_sweep` | `MOD-STEER-0001` | Evaluate an ordered input sweep with continuation, diagnostics, and lineage. |
| `interpolate_legacy_map` | Migration support only | Compare imported CAD tables inside their reviewed domain without replacing the mechanism. |

## 5. Exact rigid-body geometry

### 5.1 Rack inner-joint translation

For a rigid translating rack,

```text
p_in,j(s) = p_in,j,0 + s e_r
```

where `s` is signed rack displacement from rack center and `e_r` is a unit vector.

**Source and validity:** This is the definition of translation of a point fixed to a rigid rack. It is exact for a rack whose centerline motion is constrained to one line. A variable rack path, housing deflection, or compliance requires another model rather than a correction to this equation.

### 5.2 Upright point rotation about the steering axis

For a point fixed to the upright,

```text
r0 = p_out,j,0 - a_j
p_out,j(delta_j) = a_j + R(k_j, delta_j) r0
```

with the axis-angle rotation

```text
R(k, delta) r =
    r cos(delta)
  + (k cross r) sin(delta)
  + k (k dot r) [1 - cos(delta)]
```

**Source and validity:** This is the standard Rodrigues/axis-angle representation of a proper rigid rotation. It is selected because it preserves lengths and angles exactly, works with caster and steering-axis inclination, and does not pretend that upright rotation is always a yaw about the body `z` axis. Gillespie Chapter 8 emphasizes that road-wheel steer occurs about a generally nonvertical steering axis and that this geometry controls both kinematics and later force/moment behavior.

The formula is exact for a rigid upright rotating about a fixed axis in the named reference configuration. Suspension motion or compliance changes the axis or upright pose and belongs to a later model layer.

### 5.3 Rigid tie-rod closure

The physical length residual is

```text
e_L,j(delta_j, s) = norm[p_out,j(delta_j) - p_in,j(s)] - L_j
```

The algebraic closure function may use the squared form

```text
F_j(delta_j, s) =
    0.5 * ( norm[p_out,j(delta_j) - p_in,j(s)]^2 - L_j^2 )
```

and closure requires

```text
F_j = 0
```

**Source and validity:** This is the holonomic distance constraint for a rigid two-force link with ideal joint centers. It follows directly from Euclidean geometry and is higher equation authority than a fitted steering polynomial. It is valid only when `L_j` is the joint-center distance and the joints provide the required articulation without contacting their limits.

The solver may use `F_j`, but reports `e_L,j` in metres because it has immediate physical meaning.

### 5.4 Reference tie-rod length

At the reviewed reference configuration,

```text
L_j = norm[p_out,j(delta_j,0) - p_in,j(0)]
```

when tie-rod length is a derived output. If a physical catalog assembly is selected first, its accepted joint-center length becomes an input and the reference toe/geometry must satisfy closure.

The software must not independently accept both an arbitrary tie-rod length and arbitrary reference joint coordinates without reporting inconsistency.

## 6. Position solution and branch control

At each rack displacement, solve one scalar closure equation per side:

```text
find delta_j such that F_j(delta_j, s) = 0
```

### 6.1 Required numerical behavior

1. The rack-center solution and branch identity are supplied by the reference configuration.
2. The sweep proceeds outward from rack center in both directions.
3. Each new solution uses the preceding accepted solution for continuation.
4. Root brackets remain inside mechanical road-wheel-angle limits.
5. A bracket-preserving scalar root algorithm is used. A safeguarded Brent–Dekker-family method is the preferred first implementation because it combines bisection reliability with faster interpolation while retaining a sign-changing bracket.
6. An unconstrained Newton iteration is not the default because it can jump to another assembly branch or cross a singular configuration.
7. If multiple roots exist inside the mechanical bounds, branch continuity and declared assembly orientation determine the valid root. If those rules do not identify one root unambiguously, evaluation fails rather than selecting a visually convenient result.
8. A missing bracket, loss of closure, joint-limit violation, or branch ambiguity is an engineering failure state, not `NaN` silently passed downstream.

**Numerical source:** The Brent root-finding family is a standard bracketed scalar-root method originating with R. P. Brent, *Algorithms for Minimization Without Derivatives* (1973). It is a numerical choice, not part of the physical model; an independently verified bracket-preserving implementation may be substituted without changing the equation card.

### 6.2 Singularity diagnostic

Let

```text
q_j = p_out,j - p_in,j
p'_out,j = k_j cross (p_out,j - a_j)
```

Then

```text
partial F_j / partial delta_j = q_j dot p'_out,j
partial F_j / partial s       = -q_j dot e_r
```

and, where the denominator is nonzero,

```text
d delta_j / d s =
    - (partial F_j / partial s) / (partial F_j / partial delta_j)
```

A steering-linkage position singularity is approached as `partial F_j / partial delta_j` approaches zero on the active branch. The evaluator must report the raw derivative, a documented normalized margin, and the applicable threshold. It must not step through a branch fold merely because a numerical root still exists elsewhere.

## 7. Road-wheel heading

Rotation about the steering axis is not automatically equal to road-wheel yaw. The wheel-frame forward vector is rotated with the upright and projected into the road plane:

```text
f = R(k_j, delta_j) f_j,0
f_p = f - (f dot n) n
f_hat = f_p / norm(f_p)
```

With reviewed road-plane basis vectors `e_x` and `e_y`,

```text
delta_total,j = atan2(f_hat dot e_y, f_hat dot e_x)
```

The result is continuously unwrapped over the sweep.

Two distinct outputs are required:

```text
static_toe_j = delta_total,j(s = 0)

delta_incremental,j(s) =
    unwrap[delta_total,j(s) - static_toe_j]
```

**Why this definition is required:** The recovered WUFR curves retain approximately one degree of static toe at rack center. Guiggiani Section 3.4 treats static toe and steering-dependent dynamic toe as separate effects. Differentiation removes the constant toe term, but Ackermann comparisons and setup reporting do not. A forced-zero curve therefore cannot replace total wheel heading.

The projection fails if the wheel forward vector becomes parallel to the road normal. That state is outside normal steering operation and must return an invalid-orientation failure.

## 8. Inside/outside classification

Left/right results are stored. For an ordinary front-steered vehicle:

- positive vehicle turn/yaw direction identifies a left turn;
- the left front wheel is inside for a left turn;
- the right front wheel is inside for a right turn.

The exact mapping must be implemented from the declared turn convention, not inferred from whichever angle has larger magnitude. Using magnitude to identify the inside wheel can hide anti-Ackermann behavior or a sign error.

## 9. Exact low-speed Ackermann reference

For positive inside and outside **incremental** steer magnitudes, wheelbase `l`, steering-axis ground-intersection track `t`, and rear-axle-center turn radius `R`, exact no-slip geometry gives

```text
tan(delta_i) = l / (R - t/2)
tan(delta_o) = l / (R + t/2)
```

and therefore

```text
1/tan(delta_o) - 1/tan(delta_i) = t/l
```

For a selected inside angle,

```text
delta_o,ref = atan2(
    l,
    l/tan(delta_i) + t
)
```

using a quadrant-aware `atan2` implementation.

**Sources:** Guiggiani, 2022, Section 3.4.1, equations 3.67–3.68, pages 88–89; Gillespie, 1992, Chapter 8, equations 8-1 and 8-2.

**Why it is valid:** This is the exact planar no-slip construction for rigid wheels at low speed. It is an excellent analytical benchmark and a possible low-speed target.

**Why it is not the universal objective:** Guiggiani Sections 3.4.2–3.4.3 explains that static and dynamic toe alter tire slips and lateral-force directions, and that parallel or anti-Ackermann behavior may be appropriate at race-car operating conditions. The eventual optimization objective must therefore be generated from WUFR tire, load, effort, compliance, and operating-envelope models. Minimum turning capability and low-speed behavior remain constraints or weighted requirements.

## 10. Ackermann error

The default dimensional error is

```text
E_A = actual outside incremental steer
      - Ackermann outside reference
```

The independent variable, turn direction, track definition, toe treatment, and domain must accompany every curve.

A positive error means the outside wheel steers more than the exact reference for the same inside angle. Percentage or normalized coefficients are separate report quantities and cannot replace the dimensional error.

Toe-inclusive target curves may be constructed by adding the reviewed static setup to an incremental target, but the operation must be explicit.

## 11. Turning radius

For exact no-slip incremental angles,

```text
R_rear_axle_center = l/tan(delta_i) + t/2
                   = l/tan(delta_o) - t/2
```

Agreement between the two expressions is an internal consistency check, not an assumption that an arbitrary linkage is perfect Ackermann.

For non-Ackermann actual angles, the two front wheel planes do not generally identify one common instantaneous center. The evaluator must either:

- report separate inside-derived and outside-derived radii and their mismatch; or
- calculate a separately named best-fit/equivalent curvature quantity.

It must not average the two radii and label the result simply `turning radius`.

Radius to the rear axle center, CG, tire paths, or outside vehicle envelope are separate functions. The first analytical packet freezes only the rear-axle-center construction.

## 12. Steering transmission, gains, and ratios

The mechanism relation is separated into stages:

```text
steering-wheel angle -> shaft angle -> pinion angle
pinion angle -> rack displacement
rack displacement -> left/right road-wheel heading
```

For a constant rack relation,

```text
s = C_rp * theta_p
```

where `C_rp` is rack displacement per pinion angle in `m/rad`. A variable-ratio rack uses a reviewed function `s(theta_p)` and its derivative.

The local road-wheel gain is

```text
g_j = d delta_j / d theta_input
```

The conventional local steering ratio is

```text
R_j = d theta_steering_wheel / d delta_j
    = 1 / g_j
```

only when the numerator input is confirmed to be steering-wheel angle and the gain is nonzero.

The chain rule is explicit:

```text
d delta_j / d theta_sw =
    (d delta_j / d s)
    (d s / d theta_p)
    (d theta_p / d theta_sw)
```

A secant ratio over endpoints `a` and `b` is

```text
R_secant =
    [theta_sw(b) - theta_sw(a)]
    / [delta_output(b) - delta_output(a)]
```

with the selected output named. Gillespie Chapter 8 notes that steering-wheel-to-road-wheel ratio normally varies with steering angle; one scalar ratio is therefore a summary, not the mechanism definition.

Local analytical or implicit derivatives must be checked against centered finite differences away from boundaries and singularities. Automatic differentiation may later provide another implementation route, but it does not replace the analytical definition or benchmark.

## 13. Sweep result and failure schema

Every evaluated point reports:

- requested input quantity and value;
- rack displacement;
- left/right upright rotation;
- left/right total wheel heading;
- left/right incremental steer;
- inside/outside aliases and turn direction;
- physical tie-rod length residuals;
- root bracket and iteration status;
- branch identifier;
- joint articulation status where available;
- local derivative and singularity margin;
- Ackermann reference/error where defined;
- named turning-radius outputs;
- model, geometry, parameter, solver, and source revisions.

Required failure codes include at least:

- `input_outside_domain`;
- `no_closure_root`;
- `multiple_branch_ambiguity`;
- `branch_discontinuity`;
- `singularity_margin_violated`;
- `joint_limit_violated`;
- `invalid_wheel_projection`;
- `ratio_undefined`;
- `turning_radius_undefined`;
- `extrapolation_prohibited`.

An optimizer later receives the same structured failures and may classify a candidate as infeasible. It must never replace a failed mechanism evaluation with a penalty value that looks like valid physics.

## 14. Imported map interpolation

A CAD or historical table is comparison evidence. When an imported table requires interpolation, the default candidate is a shape-preserving piecewise cubic Hermite interpolation, following the monotonicity-preserving approach of Fritsch and Carlson (1980), or a reviewed linear interpolation for sparse data.

Reasons:

- it preserves the sampled table as authority;
- it avoids global polynomial oscillation;
- it provides local derivatives without extrapolating a quartic fit;
- it allows explicit failure outside the source domain.

The interpolant is never used as the native geometry model and never validates the source data from which it was constructed.

## 15. Car-specific adaptation rule

The equations above are general rigid-mechanism fundamentals. WUFR-specific behavior enters only through reviewed parameters and requirements:

- steering-axis and joint coordinates;
- rack axis, width, placement, and travel;
- pinion/rack transmission;
- static alignment;
- rod-end articulation and hardware limits;
- steering stops and packaging;
- wheelbase and steering-axis track;
- later tire, force, effort, compliance, tolerance, and maneuver targets.

Changing the car must change the parameter/configuration records, not the governing rigid-body equations. Changing the fidelity—such as allowing suspension travel or compliance—requires a new model layer and benchmark burden.

## 16. Preimplementation exit gate

Mechanism code may begin only after review accepts:

1. this function specification;
2. equation records `EQ-STEER-0001` through `EQ-STEER-0007`;
3. `GEO-STEER-BASIC-001` and its expected analytical results;
4. result/failure fields and branch-control behavior;
5. the distinction between total heading, static toe, and incremental steer;
6. the exact Ackermann reference as a benchmark rather than universal optimum;
7. explicit deferral of unresolved WUFR-26 Level E signal and datum choices.

WUFR-26 CAD reproduction may remain partially open while a bounded evaluator prototype is developed against the frozen synthetic and analytical cases. It must close before WUFR-26 design conclusions receive cross-tool maturity credit.
# Rigid Steering Prototype Implementation v0.1.0

**Authorization:** `AUTH-STEER-0001`  
**Model:** `MOD-STEER-0001`  
**Scope:** Bounded rigid evaluator only; no optimizer or production/as-built authority

## Implemented function families

| Function | Equation basis | Implementation | Validity boundary |
|---|---|---|---|
| Rack-joint translation | `EQ-STEER-0003`; Euclidean vector addition | `translate_rack_joint` | Declared rigid frame, rack axis, and SI displacement |
| Upright-joint rotation | `EQ-STEER-0003`; Rodrigues axis-angle rotation | `rotate_point_about_axis` | Fixed nonzero steering axis and rigid upright |
| Tie-rod closure | `EQ-STEER-0002`; joint-center distance constraint | `closure_squared_residual` and `closure_length_residual` | Rigid link and spherical-joint centers |
| Position solution | `EQ-STEER-0003`; scalar root of closure | Deterministic bracket scan plus bisection | Intended branch has a sign-changing bracket inside declared mechanical bounds |
| Branch identity | Closure-Jacobian sign at reviewed reference state | Reference derivative sign retained at every accepted root | Reference state must be nonsingular; no alternate-root fallback |
| Local mechanism gain | `EQ-STEER-0005`; implicit differentiation | `-g_s/g_theta` using analytical partial derivatives | Away from singular closure Jacobian |
| Wheel heading | `EQ-STEER-0003`; rotated wheel-forward vector projected to road plane | `wheel_heading` | Numerical wheel-forward basis must exist |
| Ackermann reference/error | `EQ-STEER-0001` and `0007` | Exact `atan2` form and outside-minus-reference error | Low-speed no-slip reference; incremental angles |
| Turning radii | `EQ-STEER-0006` | Separate inside- and outside-derived rear-axle-center radii | Named wheelbase/track and nonzero wheel angles |
| Transmission/ratio | `EQ-STEER-0004` and `0005` | Explicit staged chain and reciprocal only for nonzero named gain | Signal identities and transmission factors supplied |

## Numerical method

The prototype uses only the Python 3.11 standard library. The position solver:

1. samples the declared mechanical angle interval to locate sign-changing closure brackets;
2. solves each bracket with deterministic bisection;
3. evaluates the analytical closure derivative at each root;
4. retains only roots whose derivative sign matches the reviewed reference branch;
5. rejects ambiguity, branch changes, domain violations, singularity, and nonconvergence;
6. reports squared residual and physical length residual separately.

Unconstrained Newton/secant solving, clipping, extrapolation, and alternate-root substitution are absent.

Default numerical controls are:

```text
angle interval tolerance       1e-13 rad
squared closure tolerance      1e-14 m^2
maximum bisection iterations   120
mechanical interval samples    1601
singularity warning ratio      0.25 of reference |dg/dtheta|
singularity failure ratio      1e-6 of reference |dg/dtheta|
```

## Automated benchmark coverage

`tests/test_rigid_steering_benchmarks.py` implements:

- `BENCH-STEER-0002`: four exact Ackermann angle/radius pairs and cotangent identity;
- `BENCH-STEER-0003`: reference closure, tie-rod length, and branch signatures;
- `BENCH-STEER-0004`: five-state sweep, mirror symmetry, monotonicity, sweep-direction independence, branch-limit warnings, and deliberate domain failures;
- `BENCH-STEER-0005`: staged transmission identity and `m/rad` to `mm/rev` conversion;
- `BENCH-STEER-0006`: analytical local gain, centered finite difference, chained road-wheel gain, and conventional ratio;
- `BENCH-STEER-0007`: exact radius agreement and preservation of non-Ackermann radius mismatch;
- `BENCH-STEER-0008`: Ackermann error sign, static-toe removal invariance, and side-based inside/outside assignment.

Additional tests reject a zero steering-axis direction and verify that the WUFR-26 nominal configuration returns only closure/upright-rotation outputs while wheel heading remains explicitly unavailable.

## WUFR-26 nominal output boundary

`WUFR26_DESIGN_NOMINAL_V0` is evaluated as a design-source mechanism. The implementation may report front-left and mirror-derived front-right upright rotation, closure, branch, and singularity diagnostics. It does not report authoritative road-wheel heading, steering-wheel ratio, Ackermann error, or turning radius because the numerical wheel-plane, exact toe convention, and transmission prerequisites remain unavailable.

## Developer execution

```text
python -m unittest discover -s tests -v
python scripts/run_steering_benchmarks.py
```

The benchmark script prints machine-readable synthetic results and a non-authoritative WUFR-26 nominal incremental-rotation sweep.

# Phase 2 quasi-static equilibrium implementation review

## Review target

PR #60 implements the generic `MOD-VEH-0004` slice authorized by merged `AUTH-VEH-0004` / PR #59.

This review is for the **generic numerical/mechanics kernel only**. It is not a request to authorize WUFR corner loads.

## Implemented boundary

The implementation accepts explicit providers for:

- road-compatible wheel coordinates and `J_wb`;
- conservative suspension generalized wheel force and stored energy;
- body external generalized force and optional potential energy.

It solves:

```text
R_b = Q_body_ext + J_wb^T Q_susp_w = 0
```

with caller-declared coordinate/residual scales and bounds.

Road-normal reactions are recovered only from:

```text
Q_susp_i + Q_wheel_ext_i + c_i lambda_i = 0
```

with explicit wheel external generalized forces and contact coefficients.

## Numerical implementation

The first implementation is dependency-free and uses:

- scaled centered finite-difference residual tangent;
- one-sided tangent only at declared bounds;
- partial-pivot Gaussian elimination;
- reciprocal pivot-ratio singular/conditioning rejection;
- damped residual-reducing line search;
- no coordinate clipping;
- explicit iteration/residual/tangent/provenance diagnostics.

Independent two-step total-potential finite differences verify the conservative generalized-force sign convention.

## Dedicated benchmark evidence

The dedicated motion-aware CI run on PR #60 passed the implementation tests and generated both benchmark reports.

### BENCH-VEH-0005

Analytical synthetic target:

```text
q_b = [-0.024525 m, 0, 0]
Q_susp = -245.25 N/corner
lambda = +294.30 N/corner
sum(lambda) = 1177.20 N
```

Observed first passing run:

```text
body q error                  2.4529e-14
wheel coordinate error       2.4529e-14 m
spring-force error           2.4528e-10 N
reaction error               2.4528e-10 N
reaction-sum error           9.8112e-10 N
scaled equilibrium residual  9.8112e-13
energy-gradient disagreement 3.4153e-09
reciprocal pivot ratio       0.4444444444
iterations                   1
```

### BENCH-VEH-0006

The implementation also demonstrated:

- repeatability from two declared initial guesses (`3.5891e-14` max coordinate difference);
- singular/rank-deficient fixture -> `singular_or_ill_conditioned_tangent`;
- unreachable bounded equilibrium -> `line_search_failure` without clipping;
- omitted wheel external generalized force -> `missing_wheel_external_force_authority`;
- negative road reaction retained at `-10 N` -> `negative_normal_reaction`;
- no hidden WUFR mass default.

## Source/authority review

The implementation obeys the PR #58/#59 boundary:

- there is no WUFR gravity constructor;
- there is no 5 kg/corner WUFR default;
- historical 10 kg/corner is not used;
- 207 kg LLTD sprung mass is not used;
- 220+100 kg calculation inputs are not used;
- no crossweight/load-transfer equation is present;
- no scalar spring wheel rate or scalar ARB roll stiffness is present.

The synthetic `5 kg/corner` value exists only inside BENCH-VEH-0005 test/report fixtures and is clearly marked `synthetic_only` in the frozen result record.

## Remaining blocker

A WUFR driver/no-fuel road-reaction adapter still needs a reviewed physical gravity decomposition.

The current reviewer-measured unsprung evidence is only:

```text
front axle unsprung mass = 10 kg
rear axle unsprung mass  = 10 kg
```

A later authorization must either supply measured/reviewed per-corner values and force application locations, explicitly approve a named prototype left/right allocation assumption, or provide an independently reviewed sprung-body mass/CG model.

Until then, PR #60 should be merged only as a generic/synthetic equilibrium kernel.

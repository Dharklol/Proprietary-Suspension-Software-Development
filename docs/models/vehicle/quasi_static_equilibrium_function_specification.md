# Provider-neutral quasi-static equilibrium function specification

## 1. Purpose

`MOD-VEH-0004` is the first bounded equilibrium layer allowed to compose the reviewed whole-vehicle coordinate foundation with conservative suspension-force providers.

The implementation must remain **provider-neutral**. It may solve explicit synthetic fixtures and later consume reviewed WUFR spring/ARB providers, but it must not contain WUFR mass defaults or produce a WUFR road-reaction result until a separate mass/gravity authorization closes the unresolved sprung/unsprung allocation.

The proposed implementation package is:

```text
src/pssd_vehicle/quasi_static.py
```

The first implementation is quasi-static only. No damping, transient inertia, tire constitutive force, aero, brake, powertrain, chassis compliance, or contact-mode switching belongs in this module.

## 2. Coordinate contract

### 2.1 Reduced body coordinates

The kernel accepts an arbitrary small reduced coordinate vector, with the first project use expected to follow the existing `MOD-VEH-0003` convention:

```text
q_b = [z_s_m, phi_rad, theta_rad]
```

The kernel itself must not infer coordinate meaning from vector position. The caller supplies:

- `coordinate_order`;
- `coordinate_units`;
- initial guess;
- per-coordinate numerical scale;
- optional lower/upper bounds.

All dimensions must agree exactly.

### 2.2 Physical wheel coordinates

The compatibility provider returns:

```text
z_w(q_b)
```

and

```text
J_wb = partial(z_w)/partial(q_b)
```

with explicit wheel-coordinate order and units. The intended physical WUFR coordinate is the already reviewed `MOD-SUSP-0002` quantity `delta_z_wc_body_m`, positive upward relative to the body.

The generic kernel does not know how `z_w` was generated. It only verifies the declared contract and rejects incompatible/nonfinite outputs.

A missing compatibility map may **not** be replaced with:

- `phi * track/2`;
- direct body-roll-to-wheel-travel assumptions;
- wheelbase/track load-transfer equations;
- OptimumK `Motion Ratio Heave`;
- scalar spring/ARB installation ratios.

## 3. Provider contracts

### 3.1 Compatibility provider

Conceptual callable:

```text
compatibility(q_b) -> CompatibilityState
```

Required successful output:

- `wheel_coordinates`;
- `wheel_coordinate_order`;
- `wheel_coordinate_units`;
- `J_wb` with shape `(n_wheel, n_body)`;
- source/configuration/provenance string(s).

Optional output:

- provider-specific diagnostics;
- Jacobian verification metadata.

Failure from the provider must propagate as a structured upstream-provider failure; the kernel may not retry with a different physical model.

### 3.2 Suspension provider

Conceptual callable:

```text
suspension(wheel_coordinates) -> SuspensionState
```

Required successful output:

- `generalized_wheel_force`, ordered exactly like the compatibility wheel coordinates;
- `stored_energy_J` for the conservative force set represented by that provider;
- coordinate order/units;
- provenance.

The sign convention is the standard generalized-force convention:

```text
Q_susp_w = -partial(U_susp)/partial(z_w)
```

`MOD-SUSP-0004` and `MOD-SUSP-0005` already use energy/virtual-work conventions compatible with this architecture, but later WUFR composition must still test order/sign compatibility explicitly.

The kernel must not independently recompute spring rate, wheel rate, ARB stiffness, or motion ratio.

### 3.3 Body external generalized-force provider

Conceptual callable:

```text
body_external(q_b) -> BodyExternalState
```

Required output:

- `generalized_force` in the exact reduced body-coordinate order;
- provenance.

For conservative synthetic verification it may additionally provide potential energy so the total-potential gradient can be checked.

The future static WUFR gravity provider belongs behind a separate authorization. `MOD-VEH-0004` must not derive gravity from corner weights or mass spreadsheets itself.

### 3.4 Wheel external generalized forces

For post-solve road-reaction recovery the caller supplies, per physical wheel coordinate:

```text
Q_wheel_ext
```

Examples in future physical use can include unsprung gravity when separately authorized. Synthetic benchmark masses are allowed only when clearly fixture-local.

A physical road-reaction result requiring unsprung gravity must fail when that input is absent rather than assuming zero.

### 3.5 Contact coefficient

For each active corner the caller supplies the signed coefficient `c_i` mapping a positive scalar road-normal reaction `lambda_i` into the corresponding wheel generalized force:

```text
Q_contact_i = c_i * lambda_i
```

For the simplest vertical physical wheel coordinate aligned with the upward road normal, `c_i=+1`, but the implementation must not hard-code that value as a universal convention.

`c_i` must be finite and nonzero.

## 4. Governing equations

### 4.1 Reduced body equilibrium

With compatibility already enforced by the wheel-coordinate map, the reduced residual is:

```text
R_b(q_b) = Q_body_ext(q_b) + J_wb(q_b)^T Q_susp_w(z_w(q_b))
```

The equilibrium state satisfies:

```text
R_b = 0
```

Road reactions do not appear directly in this reduced residual because the supplied active-contact compatibility has eliminated the constrained wheel degrees of freedom. For an ideal active contact, the road constraint force performs no virtual work in allowed reduced variations.

Wheel-only external generalized forces that are fixed to the road-side constrained coordinates are likewise not mapped into `R_b`; they enter reaction recovery. This prevents double counting unsprung gravity in a reduced sprung-body solve.

### 4.2 Road-reaction recovery

After body equilibrium converges, each active wheel coordinate must satisfy:

```text
Q_susp_i + Q_wheel_ext_i + c_i * lambda_i = 0
```

so:

```text
lambda_i = -(Q_susp_i + Q_wheel_ext_i) / c_i
```

A negative `lambda_i` invalidates the first all-four-active contact mode. The implementation returns the negative value diagnostically and reports wheel lift/contact-mode invalidity. It must not clip or redistribute.

### 4.3 Conservative energy verification

When both suspension and body external providers expose consistent potential energies, define:

```text
Pi(q_b) = U_susp(z_w(q_b)) + V_body_ext(q_b)
```

The independent finite-difference check is:

```text
R_b approximately -partial(Pi)/partial(q_b)
```

at declared two-step perturbations. This is a verification path, not the primary numerical residual definition.

## 5. Numerical solver

### 5.1 Required configuration

Suggested immutable configuration fields:

```text
residual_absolute_tolerance
residual_relative_tolerance
max_iterations
coordinate_scales
lower_bounds
upper_bounds
finite_difference_relative_step
finite_difference_min_step
minimum_step_scale
line_search_reduction
line_search_max_trials
pivot_tolerance
condition_warning_threshold
```

No default may silently encode a WUFR physical parameter.

### 5.2 Tangent

The first implementation may use a finite-difference residual tangent:

```text
K_ij = partial(R_i)/partial(q_j)
```

Perturbations are scaled by the declared coordinate scale and must remain inside caller-supplied bounds. Prefer centered differences; one-sided differences are allowed only at a declared bound and must be reported.

The solver records the actual perturbation per coordinate.

### 5.3 Linear solve

The implementation should avoid adding a heavy dependency for this small bounded kernel. A deterministic pivoted Gaussian-elimination solve is sufficient for the first 1-3 coordinate prototypes if it reports:

- pivot magnitudes;
- singular/ill-conditioned failure;
- a simple reciprocal-pivot or equivalent conditioning diagnostic.

A later larger solver may replace the linear algebra behind the same contract.

### 5.4 Newton step and line search

For tangent `K` and residual `R`:

```text
K * delta_q = -R
```

A damped step is accepted only if it remains within the declared bounds and reduces the scaled residual norm. The implementation may reduce the step by a declared line-search factor for a bounded number of trials.

If no acceptable step exists, return structured nonconvergence; do not clip a coordinate to a bound and pretend convergence.

### 5.5 Convergence

Report both raw and scaled residuals. A state is converged only when the configured residual criterion is met and all providers return successful finite states.

The result must retain:

- final coordinates;
- final wheel coordinates;
- final residual;
- raw/scaled residual norms;
- iterations;
- tangent method/steps;
- conditioning diagnostic;
- line-search information;
- provider provenance;
- contact reactions/admissibility when reaction recovery was requested.

## 6. Structured status and failures

Suggested status:

```text
success
failure
```

Suggested failure codes:

```text
nonfinite_input
coordinate_contract_mismatch
compatibility_provider_failure
suspension_provider_failure
body_external_provider_failure
missing_wheel_external_force_authority
missing_contact_coefficient
singular_or_ill_conditioned_tangent
coordinate_bound_exceeded
line_search_failure
nonconvergence
negative_normal_reaction
contact_mode_invalid
energy_gradient_disagreement
missing_mass_force_authority
```

Provider-native failure details should be preserved in a message/provenance field where possible.

## 7. Synthetic verification fixtures

### 7.1 BENCH-VEH-0005 symmetric analytical case

Use fixture-local values only:

```text
sprung mass = 100 kg
g = 9.81 m/s^2
four suspension k = 10000 N/m
four wheel-side synthetic masses = 5 kg each
```

At the symmetric branch:

```text
z_i = -z_s
Q_susp_i = -k z_i
Q_body,z = -100*9.81 N
```

The exact state is:

```text
z_s = -0.024525 m
phi = 0
theta = 0
z_i = +0.024525 m
Q_susp_i = -245.25 N
Q_wheel_ext_i = -49.05 N
lambda_i = +294.30 N
sum(lambda) = 1177.20 N
```

These numbers have **no WUFR authority**.

### 7.2 BENCH-VEH-0006 failure cases

At minimum verify:

- deterministic asymmetric synthetic convergence;
- singular tangent;
- coordinate-bound/nonconvergence behavior;
- negative contact reaction retained and flagged;
- contact coefficient zero/missing;
- nonfinite input;
- coordinate order/unit mismatch;
- upstream provider failure;
- missing WUFR mass-force authority path.

## 8. WUFR boundary

The implementation must contain no implicit WUFR mass record.

The current project evidence provides:

- driver/no-fuel scale state `178/175/163/159 lb`;
- a source-separated driver-equivalent `z_CG=0.290 m` design reference;
- measured unsprung totals `10 kg` front axle and `10 kg` rear axle.

It does **not** yet provide a reviewed per-corner unsprung split/application convention or an independent sprung-body mass/CG force model.

Therefore the first WUFR road-reaction adapter remains blocked. A future authorization must explicitly state whether any per-corner mass allocation is measured or assumed and how its gravity force is applied.

## 9. Explicit exclusions

This authorization/implementation does not include:

- maneuver tire-force solution;
- tire load sensitivity or combined slip;
- aero map/application points;
- braking or powertrain load paths;
- damper force;
- transient inertia;
- unsprung lateral/longitudinal load transfer;
- chassis compliance;
- alternate road/contact modes;
- suspension linkage force/stress;
- physical stops/ride-height limits;
- installed/as-built validation;
- optimization or production release.

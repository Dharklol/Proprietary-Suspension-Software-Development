# Coupled Anti-Roll-Bar Function Specification

**Model:** `MOD-SUSP-0005`  
**Authorization:** `AUTH-SUSP-0005`  
**Status:** preimplementation review contract

## Purpose

Provide one conservative, source-bounded anti-roll-bar element that is explicitly coupled across the left and right suspension states. The provider is intended to compose with the existing suspension/actuation providers and later quasi-static equilibrium. It is not a scalar wheel-rate calculator.

## Governing decomposition

The model is deliberately split into three operations:

1. **Bilateral mechanism mapping — `EQ-SUSP-0016`**

   `s_ARB = s_mech(q_left, q_right; geometry) - s_ref`

   `J_s = partial(s_ARB) / partial(q)`

   `s_ARB` may be scalar or vector. Its dimension and units are frozen by the source-specific mechanism/constitutive packet. For the WUFR Z-bar this prevents the implementation from prematurely deciding that blade angle, tip displacement, rocker angle, or wheel displacement is the elastic coordinate before the CAD/topology is reconstructed.

2. **Conservative constitutive law — `EQ-SUSP-0017`**

   `a_ARB = gradient_s(U_ARB)`

   `K_ARB = partial(a_ARB) / partial(s)`

   Linear reference form:

   `U_ARB = 0.5 * s^T * K_ARB * s`

   `a_ARB = K_ARB * s`

   A WUFR constitutive evaluation is unavailable until traceable stiffness or force-deflection/torque-angle evidence exists.

3. **Virtual-work mapping — `EQ-SUSP-0018`**

   `Q_ARB = -J_s^T * a_ARB`

   All left/right signs are retained. No absolute motion ratio, scalar `k*MR^2`, or independent-corner spring surrogate is permitted as governing physics.

## Required data contracts

### Bilateral mechanism state

The implementation shall require:

- axle and configuration identity;
- successful left and right upstream suspension/actuation states;
- explicit ARB mechanism geometry/topology and attachment roles;
- explicit branch/reference identity;
- signed elastic coordinate/vector;
- signed deformation Jacobian and declared generalized-coordinate order/units;
- zero-preload/preload provenance;
- source and assumption IDs.

A raw list of CAD sketch points is not sufficient mechanism topology.

### Constitutive packet

The implementation shall require:

- coordinate dimension and units matching the mechanism state;
- conservative `U(s)` or an equivalent reviewed action law with an unambiguous energy integral;
- local tangent stiffness/matrix;
- validity/domain bounds;
- source identity and authority level.

For WUFR-27, the first package intentionally has no constitutive stiffness authority. Geometry-only state may be evaluated if the mechanism is reconstructed, but WUFR energy/action/generalized force must return `missing_stiffness_authority` until the source gap is closed.

## WUFR-27 source boundary

`ASM-SUSP-0003` freezes only:

- reviewer-directed carryover of the 2025 Z-bar/blade design basis into WUFR-27;
- current populated WUFR-26 ARB/suspension geometry as carryover design-intent evidence until a populated WUFR-27 revision exists;
- zero intentional ARB preload at the named nominal setup;
- explicit refusal to invent stiffness.

The current WUFR-27 A0303 and A0305 assembly files are byte-identical and therefore do not independently establish populated front/rear geometry. The active WUFR-26 FSA assembly has the front ARB active and the rear top-level ARB suppressed; that state is preserved as configuration evidence only.

## Common-mode and differential behavior

`BENCH-SUSP-0011` uses the synthetic differential coordinate

`s = z_L - z_R - s0`.

For zero preload and symmetric geometry:

- equal `z_L=z_R` gives `s=0` and zero ARB energy/action;
- equal-and-opposite input produces nonzero `s` and equal/opposite generalized reactions.

These are limiting-case benchmarks. The WUFR source implementation may not force exact common-mode cancellation by symmetry if the recovered mechanism geometry is asymmetric.

## Explicit no-bar mode

A configuration may explicitly state `arb_enabled=false`. In that case the provider returns zero energy/action/generalized force and a `no_bar`/disabled status with configuration provenance. This is distinct from a present ARB with missing or zero stiffness.

## Failure behavior

The implementation shall expose, at minimum:

- `missing_bilateral_geometry_authority`;
- `mechanism_closure_failure`;
- `branch_ambiguity`;
- `missing_zero_preload_reference`;
- `missing_stiffness_authority`;
- `constitutive_domain_exceeded`;
- `jacobian_unavailable`;
- `source_configuration_mismatch`.

Failures are not repaired with clipping, hidden reference offsets, symmetry, historical rate literals, or scalar wheel-rate substitutions.

## Verification requirements

Before implementation merge:

- analytical synthetic common/differential cases must pass;
- generalized force must agree with independent finite differences of stored energy at two step sizes;
- source/configuration/provenance failure tests must pass;
- the WUFR package must prove that unsupported numeric stiffness values remain unavailable;
- source-specific mechanism reconstruction must document point/link roles rather than rely on exported sketch row order.

## Out of scope

Damper force, spring-force duplication, tire force, body equilibrium/load transfer, contact switching, linkage/member/bearing loads, blade stress/fatigue, bearing friction/backlash, compliance beyond the authorized ARB constitutive coordinate, packaging/clearance, installed travel/stops, installed/as-built validation, and production optimization.
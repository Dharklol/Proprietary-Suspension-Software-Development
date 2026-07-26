# Coupled Anti-Roll-Bar Function Specification

**Model:** `MOD-SUSP-0005`  
**Authorization:** `AUTH-SUSP-0005`  
**Status:** preimplementation review contract

## Purpose

Provide one conservative, source-bounded anti-roll-bar element that is explicitly coupled across the left and right suspension states. The provider is intended to compose with the existing suspension/actuation providers and later quasi-static equilibrium. It is not a scalar wheel-rate calculator.

For the first WUFR-27 prototype, the governing constitutive source is a reviewer-selected **reduced effective axle roll stiffness**, not a reconstructed blade stiffness. The reduced model must therefore be kept distinct from a future detailed Z-bar/blade model.

## Governing decomposition

The model is split into three operations:

1. **Bilateral/reduced mechanism mapping — `EQ-SUSP-0016`**

   `s_ARB = s_mech(q_left, q_right; geometry) - s_ref`

   `J_s = partial(s_ARB) / partial(q)`

   `s_ARB` may be scalar or vector. Its dimension and units are frozen by the source-specific mechanism/constitutive packet. A detailed WUFR Z-bar reconstruction may later use blade/link coordinates, but the first WUFR reduced law uses a signed effective axle differential/roll angle `phi_ARB` in radians relative to the explicit zero-preload reference.

2. **Conservative constitutive law — `EQ-SUSP-0017`**

   `a_ARB = gradient_s(U_ARB)`

   `K_ARB = partial(a_ARB) / partial(s)`

   Generic linear reference form:

   `U_ARB = 0.5 * s^T * K_ARB * s`

   `a_ARB = K_ARB * s`

   WUFR reduced scalar form:

   `K_phi_rad = K_phi_deg * 180/pi`

   `U_ARB = 0.5 * K_phi_rad * phi_ARB^2`

   `M_ARB = K_phi_rad * phi_ARB`

   Reviewer-selected source values are:

   - front: `K_phi_deg = 2560 N*m/deg`, `K_phi_rad = 146677.19555349075 N*m/rad`;
   - rear: `K_phi_deg = 2270 N*m/deg`, `K_phi_rad = 130061.41949469688 N*m/rad`.

   These are **effective axle ARB roll-stiffness values**. The provider must not multiply or divide them by another blade/link/motion-ratio factor. A future detailed blade/system constitutive model replaces this reduced law rather than being added to it.

3. **Virtual-work mapping — `EQ-SUSP-0018`**

   `Q_ARB = -J_s^T * a_ARB`

   For the reduced scalar law:

   `Q_ARB = -J_phi^T * M_ARB`

   All signs are retained. No absolute motion ratio, scalar `k*MR^2`, or independent-corner spring surrogate is permitted as governing physics.

## Required data contracts

### Bilateral/reduced state

The implementation shall require:

- axle and configuration identity;
- a successful reviewed left/right state or an explicitly reviewed signed effective axle ARB deformation coordinate;
- explicit branch/reference identity for any mechanism reconstruction;
- signed elastic coordinate/vector;
- signed deformation Jacobian and declared generalized-coordinate order/units;
- zero-preload/preload provenance;
- source and assumption IDs.

A raw list of CAD sketch points is not sufficient mechanism topology.

### Constitutive packet

The implementation shall require:

- coordinate dimension and units matching the state;
- conservative `U(s)` or an equivalent reviewed action law with an unambiguous energy integral;
- local tangent stiffness/matrix;
- validity/domain bounds where applicable;
- source identity and authority level.

For WUFR-27, `ASM-SUSP-0003` authorizes the reduced effective axle law above. It does **not** authorize a blade torsional stiffness or a recovered component force-deflection curve.

## WUFR-27 source boundary

`ASM-SUSP-0003` freezes:

- reviewer-directed carryover of the 2025 Z-bar/blade design basis into WUFR-27;
- current populated WUFR-26 ARB/suspension geometry as carryover design-intent evidence until a populated WUFR-27 revision exists;
- zero intentional ARB preload at the named nominal setup;
- reviewer selection of `K_phif_neutral=2560` and `K_phir_neutral=2270` from `Weight_transfer_sensitivity.m` as the governing reduced effective axle ARB values;
- the script's displayed `N*m/deg` unit context and its front-line `%change and figure out` warning;
- the reviewer statement that available Instron data comes somewhat close but the MATLAB/simulation values were more consistent for stiffer settings.

The MATLAB script uses the two K values mainly through their ratio, so the script itself does not independently validate their absolute scale. Absolute-value authority comes from the explicit reviewer/team design-intent decision. Instron remains qualitative corroboration until its exact data and comparison method are frozen.

The current WUFR-27 A0303 and A0305 assembly files are byte-identical and therefore do not independently establish populated front/rear geometry. The active WUFR-26 FSA assembly has the front ARB active and the rear top-level ARB suppressed; that state is preserved as configuration evidence only.

## Common-mode and differential behavior

`BENCH-SUSP-0011` uses a synthetic differential coordinate

`s = z_L - z_R - s0`.

For zero preload and symmetric geometry:

- equal `z_L=z_R` gives `s=0` and zero ARB energy/action;
- equal-and-opposite input produces nonzero `s` and equal/opposite generalized reactions.

These are limiting-case benchmarks. They do not force a particular detailed WUFR Z-bar topology.

`BENCH-SUSP-0012` additionally verifies the reduced WUFR angular law. At exactly `phi_ARB = 1 deg`, the action magnitude must equal the source stiffness number in N*m: `2560 N*m` front and `2270 N*m` rear. Stored energy is evaluated using the radian-coordinate SI law.

## Explicit no-bar mode

A configuration may explicitly state `arb_enabled=false`. In that case the provider returns zero energy/action/generalized force and a `no_bar`/disabled status with configuration provenance. This is distinct from a present ARB with missing stiffness.

Front/rear enablement is not silently inferred from one WUFR-26 assembly suppression state.

## Failure behavior

The implementation shall expose, at minimum:

- `missing_bilateral_geometry_authority` when a detailed mechanism map is requested without sufficient geometry/topology;
- `mechanism_closure_failure`;
- `branch_ambiguity`;
- `missing_zero_preload_reference`;
- `missing_stiffness_authority` for configurations without a reviewed law;
- `constitutive_domain_exceeded`;
- `jacobian_unavailable`;
- `source_configuration_mismatch`.

Failures are not repaired with clipping, hidden reference offsets, symmetry, unreviewed historical literals, scalar wheel-rate substitutions, or a second stiffness reduction applied to the WUFR 2560/2270 reduced law.

## Verification requirements

Before implementation merge:

- analytical synthetic common/differential cases must pass;
- generalized force must agree with independent finite differences of stored energy at two step sizes;
- source/configuration/provenance failure tests must pass;
- the WUFR package must reproduce the 2560/2270 values, exact N*m/deg-to-N*m/rad conversion, and one-degree action/energy hand cases;
- tests must prove the WUFR K values are treated as reduced effective axle stiffness with no additional motion-ratio reduction;
- source-specific detailed mechanism reconstruction, when eventually added, must document point/link roles rather than rely on exported sketch row order.

## Out of scope

Damper force, spring-force duplication, tire force, body equilibrium/load transfer, contact switching, linkage/member/bearing loads, blade stress/fatigue, quantitative Instron correlation, bearing friction/backlash, compliance beyond the authorized ARB constitutive coordinate, packaging/clearance, installed travel/stops, installed/as-built validation, and production optimization.

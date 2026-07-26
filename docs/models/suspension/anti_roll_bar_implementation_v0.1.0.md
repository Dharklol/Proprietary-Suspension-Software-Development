# Anti-Roll-Bar Implementation v0.1.0

**Model:** `MOD-SUSP-0005`  
**Authorization:** `AUTH-SUSP-0005` / merged PR #49  
**Implementation PR:** #50  
**Package:** `src/pssd_suspension/anti_roll_bar.py`

## Scope

This implementation supplies the first conservative coupled anti-roll-bar elastic provider. It keeps the elastic coordinate source-defined and evaluates

`a_ARB = dU_ARB/ds`

`Q_ARB = -J_s^T a_ARB`, where `J_s = ds/dq`.

The implementation is deliberately narrower than a full Z-bar mechanism model. It does not infer WUFR bar deformation from body roll, wheel travel, track, or CAD sketch ordering. A consumer must provide an explicitly reviewed elastic coordinate and, when generalized force is requested, its signed Jacobian.

## Source-defined scalar coordinate

`AntiRollBarDefinition` stores:

- the scalar conservative stiffness `da/ds`;
- elastic-coordinate unit;
- conjugate-action unit;
- source/configuration/assumption identity;
- optional deformation domain;
- whether the definition is already a reduced axle-level quantity.

This supports both authorized benchmark and WUFR cases without pretending they use the same physical coordinate:

- `BENCH-SUSP-0011`: `s=z_L-z_R-s0` [m], action [N], stiffness [N/m];
- WUFR reduced law: signed `phi_ARB` [rad], action [N*m], stiffness [N*m/rad].

The provider verifies that definition and reference coordinate units/configuration identities match. It does not perform implicit unit conversion between source-defined coordinate classes.

## EQ-SUSP-0016 — elastic coordinate/reference

`anti_roll_bar_coordinate()` evaluates

`s = s_current - s_zero`

with optional signed `ds/dq`, generalized-coordinate order, and units.

The zero-energy coordinate is an explicit `AntiRollBarReference`; it is not reconstructed by subtracting a nominal residual. This preserves the zero-preload boundary from `ASM-SUSP-0003`.

`symmetric_differential_coordinate()` implements only the frozen synthetic benchmark map

`s = z_L - z_R - s0`, `J=[+1,-1]`.

It is not a WUFR geometry adapter.

## EQ-SUSP-0017 — conservative law

The v0.1.0 provider implements the authorized linear conservative scalar law:

`a = k s`

`U = 0.5 k s^2`

`k_t = k`.

The action can be negative when the signed deformation is negative. Energy remains nonnegative. Optional source-defined deformation bounds return `constitutive_domain_exceeded`; no clipping or extrapolation is performed.

## EQ-SUSP-0018 — generalized force

`generalized_anti_roll_bar_force()` implements

`Q = -J_s^T a`.

The Jacobian sign is retained. No absolute motion ratio is used.

For the synthetic differential benchmark, `J=[+1,-1]`, `k=10000 N/m`, and `s=0.020 m` produce

- action `200 N`;
- energy `2 J`;
- `Q=[-200,+200] N`.

A centered energy finite difference at two step sizes independently verifies the signed generalized-force mapping.

## Explicit no-bar mode

`evaluate_anti_roll_bar(..., enabled=False)` returns `status=no_bar` with zero deformation energy/action/generalized force and preserved configuration/source identity. This is distinct from an enabled ARB with missing stiffness, which returns `missing_stiffness_authority`.

Front/rear enablement is not inferred from the WUFR-26 FSA assembly suppression state.

## WUFR-27 reduced source adapter

`load_wufr27_anti_roll_bar_package()` reads `data_catalog/wufr27_anti_roll_bar_package_v0.toml` and freezes the reviewer-selected source values:

- front `2560 N*m/deg`;
- rear `2270 N*m/deg`.

The loader recomputes the SI conversion rather than accepting a second independent rate:

`K_Nm_per_rad = K_Nm_per_deg * 180/pi`.

Resulting values are:

- front `146677.19555349075 N*m/rad`;
- rear `130061.41949469688 N*m/rad`.

The loader also verifies that the selected source values still match the frozen MATLAB literals and that the stored SI values match the explicit conversion.

For signed source-supplied `phi_ARB` in radians:

`U = 0.5 K_phi phi_ARB^2`

`M = K_phi phi_ARB`

`Q = -J_phi^T M`.

At exactly one degree:

- front action `2560 N*m`, energy `22.340214425527417 J`;
- rear action `2270 N*m`, energy `19.80948701013564 J`.

The definitions carry `reduced_axle_level=true`. No blade/link/Z-bar motion-ratio reduction is applied after loading these values.

## Source and authority boundary

The implementation preserves the PR #49 decision:

- the MATLAB values are reviewer-selected design-intent reduced effective axle ARB stiffness;
- the MATLAB file's front `%change and figure out` warning remains source provenance;
- the MATLAB calculation mainly exercises the rates through their ratio, so the absolute-value authority comes from the reviewer's explicit team selection;
- reported Instron agreement remains qualitative corroboration only;
- 2025 SolidWorks Simulation files remain future detailed blade-law recovery evidence;
- spec-sheet 556/458 N*m/deg suspension roll rates are not substituted for the ARB law.

No result from this provider is a blade torsional-stiffness measurement or installed/as-built validation.

## Failure behavior

The public contract exposes structured failures including:

- `missing_bilateral_geometry_authority` for future source-specific mechanism adapters;
- `mechanism_closure_failure` / `branch_ambiguity` reserved for such adapters;
- `missing_zero_preload_reference`;
- `missing_stiffness_authority`;
- `constitutive_domain_exceeded`;
- `jacobian_unavailable`;
- `source_configuration_mismatch`;
- `invalid_energy_law`.

The v0.1.0 reduced WUFR path does not invoke a detailed mechanism closure, so it does not manufacture geometry failures simply to fill those future branches.

## Verification

`BENCH-SUSP-0011` exercises:

- exact common-mode cancellation;
- equal/opposite differential generalized reactions;
- explicit shifted reference;
- no-bar behavior;
- missing-stiffness/domain failures;
- centered energy-gradient checks at two step sizes.

`BENCH-SUSP-0012` exercises:

- exact WUFR source values;
- exact degree-to-radian rate conversion;
- one-degree action and energy hand cases;
- `reduced_axle_level=true`;
- zero-energy reference;
- signed generalized force for `q=phi_ARB`;
- source/Instron/installed boundaries.

The frozen result record is `benchmarks/suspension/suspension_anti_roll_bar_result_v0.1.0.toml`, tied back to executable provider behavior by `tests/test_suspension_anti_roll_bar_result_record.py`.

## Explicitly not implemented

No WUFR body-roll-to-bar-angle mapping, detailed Z-bar/link/blade closure, blade stress/strain, linkage/member/bearing load, damper force, tire force, vehicle equilibrium/load transfer, contact-mode switching, friction/backlash/hysteresis, installed travel/limits, installed/as-built correlation, or production optimization is added in PR #50.

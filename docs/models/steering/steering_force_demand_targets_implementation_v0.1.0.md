# Force-demand tire-slip steering target implementation v0.1.0

**Task:** `P1-STR-006J`  
**Benchmark:** `BENCH-STEER-0021`  
**Steering evaluator:** `MOD-STEER-0001`  
**Optimizer/orchestrator:** `MOD-STEER-0002`  
**Vehicle-state boundary:** `MOD-VEH-0001`

## Purpose

PR #30 replaces the PR #28 *peak-slip-utilization proxy* with the software boundary required for the next physically meaningful question:

`explicit wheel operating point + explicit lateral-force demand -> required slip angle`.

It does not yet claim that current WUFR wheel force demands are known. The implementation separates the inversion/steering composition from the later vehicle-state/QSS producer so the source of `Fy` remains visible.

## Tire force-response contract

`src/pssd_tire/force_demand.py` introduces a source-preserving table for one monotonic pre-peak branch at one exact tire operating point.

Each branch contains ordered samples:

`(|alpha|_i, |Fy|_i)`

with strictly increasing slip and force magnitudes.

The first contract permits only:

- exact operating-point lookup by `Fz`, inclination, and pressure;
- bounded piecewise-linear inversion between adjacent **supplied response samples**;
- explicit branch/source authority and provenance.

It rejects:

- force demand below/above the supplied branch range;
- operating-point interpolation or extrapolation;
- nonmonotonic pre-peak branches;
- negative/nonfinite force or slip magnitudes.

This interpolation is an exchange-table operation, not a new tire-force equation. No Magic Formula, spline fit, polynomial surrogate, or vehicle equilibrium is implemented.

## Magnitude convention

The inversion contract deliberately uses lateral-force and slip-angle **magnitudes**. The source-specific exporter is responsible for selecting the physically intended branch and recording source force/slip signs in provenance.

This avoids a hidden SAE/ISO sign conversion inside steering and is sufficient for the differential quantity required here:

`Delta_alpha = |alpha_out|required - |alpha_in|required`.

## Steering correction

For a nonzero steering sample, the adapter:

1. preserves the sampling target's inside-wheel incremental heading magnitude;
2. computes exact zero-slip Ackermann outside heading through the existing `exact_ackermann_outside_reference` implementation;
3. inverts the explicit inside/outside `|Fy|` demands through the supplied tire branches;
4. computes `Delta_alpha = alpha_out - alpha_in`;
5. sets:

`delta_out,target = delta_out,Ackermann + Delta_alpha`.

No steering mechanism equation is duplicated. Candidate geometry is still evaluated exclusively through `MOD-STEER-0001`.

The centered rack sample is an explicit no-turn sentinel with zero supplied force demands and is copied from the sampling target without querying a directional tire branch.

## Ackermann-regime classification

`SteeringDifferentialRegime` reports:

- `pro_ackermann`: inside heading magnitude > outside;
- `parallel`: equal within explicit tolerance;
- `anti_ackermann`: outside heading magnitude > inside.

The regime is evaluated after the tire correction. It is never specified as an objective in advance.

A positive outside-minus-inside required-slip differential always moves the target **toward anti-Ackermann**, but it crosses into anti only when it exceeds the geometric Ackermann inside/outside gap at that steering angle.

## PR #28 diagnostic

PR #28 used the R25B source-derived peak-slip pair:

- inside `9.6 deg`;
- outside `10.9 deg`;
- differential `+1.3 deg`.

At the WUFR endpoint:

- preserved inside heading: `32.18468832 deg`;
- exact Ackermann outside heading: approximately `22.8686960462 deg`;
- geometric Ackermann gap: approximately `9.315992274 deg`;
- corrected outside heading: approximately `24.1686960462 deg`;
- corrected gap: approximately `8.015992274 deg`;
- final regime: `pro_ackermann`.

So the PR #28 endpoint being pro does **not** mean the tire correction pointed pro. The correction was anti-direction, but much smaller than the large geometric split at full steer.

At the `+15 deg` steering-input sample, the geometric split is small enough that the PR #28 utilization-scaled correction crosses slightly anti: outside approximately `3.7104805346 deg` versus inside `3.6966375 deg`.

## Synthetic mixed-regime benchmark

`SYNTHETIC_FORCE_DEMAND_BRANCHES_V0.toml` contains hand-authored monotonic branches solely for software verification. It intentionally produces a substantial positive outside-minus-inside required-slip differential.

Because the Ackermann gap grows strongly with steer angle, the same synthetic trend produces anti-Ackermann at modest steering and returns to pro-Ackermann at large steering. This verifies that the implementation does not confuse a tire slip trend with a globally fixed steering regime.

The synthetic branch values have no R25B/R20 physical authority.

## Vehicle-state composition

`MOD-VEH-0001` already carries the exact fields required by the future source path:

- `Fz`;
- inclination/camber;
- pressure;
- lateral-force demand;
- wheel identity;
- state authority and weight.

The current PR #29 Suspension Calculations fixture remains evidence-only because it supplies wheel loads but not reviewed camber, pressure, or `Fy` demand. PR #30 does not fill those gaps.

## Source path to physical use

The team R25B package contains raw TTC Round 6 cornering data, processed cornering MAT data, and fitted `.tir` models. A later source-specific offline exporter should sample reviewed pre-peak `Fy(alpha)` branches at representative operating points and store only the source-preserving branch table required by this runtime.

See `steering_force_demand_tire_source_audit.md` for the exact source inventory and restrictions.

## Failure behavior

A target sample receives no valid force-demand correction when:

- the operating point has no explicit response branch;
- requested force lies outside the branch;
- branch samples are nonmonotonic or invalid;
- schedule length does not match rack sampling;
- the centered sample has nonzero demands;
- the correction would create a negative outside heading magnitude.

These failures are explicit; no extrapolation, clipping, branch substitution, or objective penalty hides them.

## Excluded scope

This implementation does not include:

- WUFR force-demand generation;
- load transfer, LLTD, aero, yaw equilibrium or QSS;
- suspension kinematics/camber generation;
- actual R25B pre-peak force curves in the committed synthetic fixture;
- combined slip or transient tire behavior;
- automatic track-surface scaling;
- production steering geometry ranking.

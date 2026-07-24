# Phase 1 steering force-demand tire target review

**PR:** #30  
**Task:** `P1-STR-006J`  
**Benchmark:** `BENCH-STEER-0021`  
**Review state:** implementation in progress; final CI/source freeze pending

## Review question

Does PR #30 establish a bounded, source-neutral `Fy demand -> required tire slip -> steering differential` path that can reveal pro/parallel/anti-Ackermann behavior from explicit operating states without inventing tire curves, vehicle equilibrium, or a preferred Ackermann regime?

## Decision requested

Approval of this PR means the following software boundary is acceptable:

1. a reviewed external source supplies monotonic pre-peak `|Fy|` versus `|alpha|` samples at an exact tire operating point;
2. the runtime may invert between those supplied samples without extrapolation;
3. explicit inside/outside force demands may be converted to required slip magnitudes;
4. their differential may be applied to the existing exact Ackermann outside-wheel reference while the base inside-wheel trajectory remains explicit;
5. pro/parallel/anti-Ackermann is reported from the resulting wheel pair rather than prescribed.

Approval does **not** authorize current synthetic force branches or incomplete PR #29 workbook states as WUFR design truth.

## Why the PR #28 endpoint is pro

The R25B reference pair frozen by PR #28 has peak slip magnitudes:

- inside: `9.6 deg`;
- outside: `10.9 deg`;
- outside-minus-inside: `+1.3 deg`.

This is an anti-Ackermann-direction correction because it increases the outside-wheel target relative to exact Ackermann.

At full positive steer, however:

- inside target = `32.18468832 deg`;
- exact Ackermann outside reference = approximately `22.8686960462 deg`;
- geometric inside/outside split = approximately `9.315992274 deg`;
- after the full `+1.3 deg` correction, outside = approximately `24.1686960462 deg`;
- corrected split = approximately `8.015992274 deg`.

The correction points anti, but is nowhere near large enough to overcome the endpoint geometric Ackermann split. The endpoint therefore remains pro-Ackermann.

More interestingly, PR #28 already becomes slightly **anti-Ackermann near center**. At the `+15 deg` input sample its utilization-scaled correction produces outside approximately `3.7104805346 deg` versus inside `3.6966375 deg`.

This review therefore rejects the framing that the R25B must be represented by one global `pro` or `anti` label. The steering regime is a state-dependent result.

## Tire force-demand contract

`pssd_tire.force_demand` stores explicit monotonic pre-peak branch samples and performs only bounded inversion between neighboring supplied samples.

The first version intentionally does **not** interpolate operating points. A caller requesting a branch at an unlisted `Fz`, inclination, or pressure receives an error rather than a guessed response.

The branch values are magnitudes. A source-specific exporter must preserve the original sign convention and identify the selected physical branch in provenance.

## Synthetic verification boundary

`SYNTHETIC_FORCE_DEMAND_BRANCHES_V0` is intentionally artificial. It exercises:

- exact and interpolated force-demand inversion;
- out-of-range rejection;
- exact operating-point matching;
- mixed anti/pro regime behavior;
- target-set composition with the existing operating-state objective path;
- complete `MOD-STEER-0001` evaluation of a reference candidate.

It is not a Hoosier tire fit and may not be used for vehicle design.

## R25B source audit

The team source package contains the required higher-fidelity information path:

- raw Round 6 cornering runs 21/22;
- processed Cornering Trojan MAT data;
- fitted Hoosier 43105 R25B `.tir` files;
- MATLAB comparison and Magic Formula integration scripts;
- Tire Selection Notes summaries.

The current repository summary has cornering stiffness, camber thrust, peak force, and peak slip but not enough intermediate `Fy(alpha)` samples to reconstruct a unique nonlinear pre-peak branch. PR #30 therefore refuses to manufacture one from summary values.

A reviewed offline branch exporter from the `.tir`/TTC source is the required next source step.

## Vehicle-state gate

The shared `MOD-VEH-0001` record can carry the necessary per-wheel fields, but the current Suspension Calculations fixture leaves camber, pressure, and `Fy` demand unavailable. Those states remain evidence-only with zero design weight.

A later reviewed vehicle-state/QSS source must supply representative force-demand states before the PR #30 path can participate in WUFR design ranking.

## Benchmark acceptance

`BENCH-STEER-0021` must demonstrate:

- bounded force inversion with no force extrapolation;
- no hidden operating-point interpolation;
- PR #28 endpoint pro-Ackermann diagnostic from the actual R25B 1.3-degree peak-slip differential;
- PR #28 near-center anti-Ackermann diagnostic;
- synthetic mixed-regime force-demand target;
- complete analyzer feasibility/evaluation through `MOD-STEER-0001`;
- deterministic report generation;
- explicit separation of real R25B diagnostic values from synthetic force-branch values.

## Prohibited interpretations

The following remain prohibited after merge:

- “R25B always wants anti-Ackermann” as a software assumption;
- “PR #28 proved pro-Ackermann is optimal”;
- use of synthetic force branches as tire data;
- interpolation/extrapolation beyond reviewed source branches;
- inference of missing `Fy`, camber, pressure, or load states;
- a Python Magic Formula rewrite for this steering stage;
- automatic use of the historical `2/3` sandpaper-to-road scaling;
- production or global-optimality claims.

## Final CI freeze

Pending final PR-head CI, test count, benchmark report artifact, and frozen result record.

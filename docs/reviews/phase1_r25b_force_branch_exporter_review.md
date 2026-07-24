# Phase 1 R25B force-branch exporter review

**PR:** #32  
**Task:** `P1-STR-006K`  
**Benchmark:** `BENCH-STEER-0022`  
**Review state:** implementation in progress; source-specific software boundary established, real binary-source export pending

## Review question

Does PR #32 establish a source-specific, auditable route from the existing WUFR-26 processed R25B Cornering Trojan into the generic PR #30 force-demand branch contract without silently changing preprocessing, inventing response points, applying track scaling, or introducing a new tire model?

## Decision boundary

Approval of this PR permits the named processed-Trojan exporter to:

1. verify the frozen source hash;
2. select an exact stored Fz/inclination/pressure state;
3. choose the documented negative-SA / positive-FY into-turn source quadrant;
4. convert selected values to positive magnitude exchange values;
5. retain the source pre-peak branch only when it is strictly monotonic;
6. serialize that branch into the existing `TireLateralForceBranchSet` TOML exchange schema.

Approval does not make a branch design-authoritative merely because it can be exported.

## Source identity and preprocessing freeze

The profile record freezes:

- `Hoosier 43105 R25B Cornering Trojan.mat`, Box `1890914118742`, SHA-1 `475338b18b6cba21b967c7e75bdd12d9a0e3437a`;
- Round 6 cornering run 21, Box `1890899727782`, SHA-1 `fca6c5b5116ae7fb16e2036b757ff294e0f790f6`;
- Round 6 cornering run 22, Box `1890911183790`, SHA-1 `a995a2a89290dc32c5372b22e7bb5f469b6cf949`;
- `April_Interpolator.m`, Box `1890897878209`, SHA-1 `e73eb559b1e0be42cc9c135d86be69e168d9e606`;
- `PARSER_April.m`, Box `1890915592715`, SHA-1 `32608eef763acacb7b233b82b8690bd3250752cc`;
- fitted `Hoosier 18 x 7.5 - 10 R25B 43105.tir`, Box `1952385546497`, SHA-1 `27b100c306ec4f207c9c42506edeeb23c95d4247`.

The source and intended tire identities remain separate:

- source: `HOOSIER_43105_18X7.5-10_R25B`;
- intended: `HOOSIER_43104_18X7.5-10_R20`.

## Why one preprocessing route is frozen

`April_Interpolator.m` and `PARSER_April.m` are not interchangeable descriptions of the same operation.

The April interpolation script uses the raw Round 6 data with approximately ±100 N Fz, ±5 kPa pressure, ±1 degree inclination, zero longitudinal slip, and a 40 km/h ±10 km/h speed window before smoothing-spline generation. It then writes exact target channels and a 100-point -12 to +12 degree source slip-angle sweep into the Trojan file.

The TyDex parser uses its own bins/tolerances, including ±150 N Fz and ±0.2 degree inclination, and performs explicit SAE-to-ISO sign and unit conversion.

PR #32 consumes the **already processed Trojan**. It does not rerun either preprocessing route and does not apply the parser sign conversion on top of the Trojan data. A different route requires a different reviewed profile.

## Failure behavior

The exporter fails when:

- required source channels are absent, empty, nonfinite, or unequal in length;
- the exact stored operating point is unavailable;
- the selected quadrant has fewer than two usable samples;
- repeated/non-increasing slip magnitudes would make the branch ambiguous;
- the retained source pre-peak force response is nonmonotonic.

A failure is not converted to smoothing, extrapolation, clipping, or a penalty-only steering state.

## Source-data limitation in repository CI

The binary Cornering Trojan is intentionally not committed to this repository. The connected source currently exposes its identity and metadata but not a text representation suitable for GitHub CI. Therefore the current benchmark verifies the exporter with synthetic Trojan-shaped arrays while freezing the real source identity/profile separately.

This distinction matters: synthetic test values are software evidence only and may never be presented as R25B response values.

## Required real-source promotion step

Before PR #30 force-demand targets can rank WUFR steering geometry, a source-side run must export actual branches from the frozen MAT file and review them.

The first useful cross-check pair is:

- Fz 222 N, IA 0 deg, P 82.7 kPa;
- Fz 1112 N, IA 2 deg, P 82.7 kPa.

The existing PR #28 summary family labels the pressure as 83 kPa and reports peak behavior around 694 N / -9.6 deg and 2738 N / -10.9 deg respectively. The real exporter result should be compared with those summaries, not forced to equal them by pressure rounding or hidden interpolation.

## Prohibited interpretations

After this PR, the following remain prohibited:

- treating the R25B source as literal R20 data;
- applying `yaw_moment.m`'s historical `2/3` force/moment scale automatically;
- calling synthetic exporter tests tire data;
- constructing a Python Magic Formula implementation to fill missing source values;
- silently switching to TyDex parser tolerances or ISO signs while claiming the April Trojan profile;
- interpolating missing Fz, inclination, pressure, speed, temperature, or other operating states;
- using post-peak response when the pre-peak force demand is unavailable;
- WUFR steering ranking without reviewed vehicle force-demand states and exported real branches.

## Acceptance disposition

`BENCH-STEER-0022` is satisfied at software level when the synthetic source tests, deterministic TOML round-trip, registry validation, and all prior steering/vehicle reports pass. Actual R25B branch values remain a separate source-data promotion artifact until the binary MAT export is executed and reviewed.

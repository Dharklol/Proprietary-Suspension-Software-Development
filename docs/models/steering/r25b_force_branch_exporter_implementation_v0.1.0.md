# R25B processed TTC force-branch exporter v0.1.0

## Purpose

PR #32 adds the source-specific bridge needed by the PR #30 force-demand steering target provider. The runtime force-demand contract intentionally accepts only explicit monotonic pre-peak `|Fy|` versus `|alpha|` branches at exact tire operating points. PR #32 defines how one existing WUFR-26 source can produce those branches without adding another tire model.

The first supported source is the processed file:

`Hoosier 43105 R25B Cornering Trojan.mat` — Box ID `1890914118742`, SHA-1 `475338b18b6cba21b967c7e75bdd12d9a0e3437a`.

The source tire remains Hoosier 43105 18x7.5-10 R25B. The intended WUFR tire remains Hoosier 43104 18x7.5-10 R20. The project-approved engineering-equivalence assumption allows the R25B data/model to support steering development, but the two identities are never collapsed.

## Why the processed Trojan route is explicit

`April_Interpolator.m` generated the R25B Cornering Trojan from the Round 6 cornering runs. For the 18-inch source it selects raw data near requested Fz, pressure, inclination, 40 km/h speed, and zero longitudinal slip, fits MATLAB smoothing splines with smoothing parameter `0.01`, and evaluates a 100-point slip-angle sweep from -12 to +12 degrees. The exported Trojan stores positive target Fz values and V = 40.2 km/h.

`PARSER_April.m` is a different route. It uses different steady-state bin tolerances, converts units, and explicitly converts SAE signs to ISO. PR #32 therefore does **not** use the parser as an implicit convention adapter for the processed Trojan. A future TyDex/raw-data exporter would require its own named profile.

The full source/profile details are frozen in:

`benchmarks/tires/WUFR26_H43105_R25B_CORNERING_TROJAN_EXPORT_PROFILE_V0.toml`.

## Export algorithm

`pssd_tire.ttc_cornering.export_cornering_trojan_branch` performs the following steps only:

1. require the source channels `FZ`, `SL`, `SA`, `P`, `IA`, `FY`, and `V` with equal finite row counts;
2. select an exact stored Trojan operating point `(Fz, IA, P)`, `SL = 0`, and `V = 40.2 km/h` within floating-point tolerance;
3. select the source quadrant documented by the team's comparison script for the desired into-turn behavior: negative source slip angle and positive source lateral force;
4. convert those selected values to positive `|alpha|` and `|Fy|` exchange magnitudes;
5. sort by increasing `|alpha|`;
6. truncate through the first source maximum `|Fy|`;
7. require the retained pre-peak `|Fy|` values to increase strictly;
8. emit the existing `LateralForceBranch` contract plus an audit record containing source-row counts and exported bounds.

The exporter deliberately refuses to repair a nonmonotonic source branch. It does not smooth, envelope, average duplicate values, discard inconvenient points, fit a polynomial/spline, or evaluate Magic Formula. Such operations would change the source-processing authority and require a separately reviewed profile.

## Offline MAT command

`scripts/export_r25b_cornering_force_branches.py` is the intended source-side command. It:

- requires the local binary Cornering Trojan MAT file;
- validates its SHA-1 against the frozen Box source hash by default;
- accepts one or more explicit states as `ID:FZ_N:IA_DEG:P_KPA`;
- invokes the source-specific exporter using the optional SciPy MAT reader;
- collects accepted branches into the generic `TireLateralForceBranchSet`;
- writes deterministic TOML that round-trips through the PR #30 runtime loader.

SciPy remains optional and is needed only to run the source export command. It is not added as a core runtime dependency.

Example source-side invocation:

```text
python scripts/export_r25b_cornering_force_branches.py \
  "Hoosier 43105 R25B Cornering Trojan.mat" \
  r25b_branches.toml \
  --state inside_ref:222:0:82.7 \
  --state outside_ref:1112:2:82.7
```

This command does not imply that those two reference states are the final WUFR design states. They are useful first cross-check states because PR #28 already has source-summary peak evidence at the corresponding load/camber conditions.

## Deterministic exchange writer

`pssd_tire.toml_exchange` implements only the narrow `explicit_lateral_force_branches` TOML schema already consumed by PR #30. It is not a general TOML serialization library. Round-trip tests verify branch identity, exact operating point, response samples, and provenance.

## Source cross-check expected after real export

Before a source-derived branch file becomes design input, the exported reference branches should be compared with the already frozen Tire Selection Notes summaries. In particular, the 83 kPa summary family reports approximately:

- 222 N, IA 0 deg: peak Fy 694 N at slip angle -9.6 deg;
- 1112 N, IA 2 deg: peak Fy 2738 N at slip angle -10.9 deg.

The processed Trojan uses the actual source pressure target 82.7 kPa rather than the rounded 83 kPa label used by the compact PR #28 summary fixture. A cross-check must preserve that distinction and should not force equality by rounding or hidden interpolation.

## Current authority boundary

CI can verify the exporter logic with synthetic Trojan-shaped channel arrays, the source manifest, deterministic failure behavior, and TOML round-trip. The repository does not contain the binary TTC/Trojan source data, so CI does not yet freeze actual R25B intermediate `Fy(alpha)` values.

Consequently PR #32 by itself still does not authorize WUFR steering design ranking. That additionally requires:

- a reviewed source-derived branch table produced from the frozen binary source;
- source-summary/raw-data cross-checks;
- representative vehicle states with per-wheel Fz, inclination, pressure, and Fy demand;
- requested force states inside the exported tire envelope;
- reviewed target-state weighting.

The historical `yaw_moment.m` factor of `2/3` is not applied anywhere in this exporter.

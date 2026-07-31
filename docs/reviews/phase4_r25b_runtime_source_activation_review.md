# Phase 4 R25B runtime source activation review

## Decision

The exact R25B generator provenance gap is closed.

The uploaded `TTC_Spline_Fitter.mlx` matches the Box identity previously recorded for the candidate live script. Its extracted MATLAB code exactly explains the processed Cornering Trojan's 5x3x4 operating-state lattice, 9,630-row allocation, variable 100/130/160/190-point sweeps, source selection, target-load scaling, smoothing parameter, and -12 to +12 degree slip grids.

The Round 6 raw input lineage has also been independently reproduced. The complete signed source-native `SA/FY` exchange is now frozen for all 60 states and all 9,630 source points.

The source-specific runtime provider remains disabled. The next gate is no longer generator provenance or curve availability; it is review of the source-to-canonical adapter, with the FSAE TTC pressure-channel gauge-versus-absolute basis still unresolved.

## Exact live-script identity

The supplied file is an OOXML MATLAB live script with the following exact identity:

- name: `TTC_Spline_Fitter.mlx`;
- Box file ID: `1890916633802`;
- Box version ID: `2085677125802`;
- size: 286,864 bytes;
- SHA-1: `c78a66751be956b60ff0f879cd0f733638a71ce3`;
- SHA-256: `a4e8a0d079d9ba64fbba428885d9c1c2c0699ca80c12f7d5a3c05b88988aa248`;
- MATLAB release: R2024b Update 3;
- title: *Creating Workable Tire Data from FSAE TTC Run Data Using Spline Fits*.

The code was extracted structurally from `matlab/document.xml`; no OCR was used.

## Exact cornering-generator profile

For a 10-inch rim, the live script declares:

- FZ targets: 222, 445, 667, 890, and 1112 N;
- pressure targets, in source loop order: 96.5, 82.7, 68.9, and 55.2 kPa;
- inclination targets: 0, 2, and 4 degrees;
- 60 operating states;
- 9,630 preallocated rows;
- source speed filter `abs(V - 40) < 10`;
- state selection using the source FZ, P, IA, and zero-SL tolerances;
- source-output normalization by source FZ and rescaling to `-target_FZ`;
- MATLAB `smoothingspline` fits with smoothing parameter 0.5;
- simulated slip grids from -12 to +12 degrees.

The variable point-count rule is:

- start at 100 points;
- add 30 when FZ is at least 667 N;
- add 30 when pressure is at least 68.9 kPa;
- add 30 when inclination is at most 2 degrees.

That rule produces exactly:

- 2 states with 100 points;
- 13 states with 130 points;
- 27 states with 160 points;
- 18 states with 190 points;
- 9,630 total points.

This is an exact structural match to the processed Trojan. The earlier `April_Interpolator.m` remains frozen as a historical supporting artifact, but its 4x3x3 fixed-100-point description is now explicitly non-governing for this binary.

## Raw-input lineage reproduction

The exact processed Trojan was independently reproduced from:

- `Round6_Run21.mat`, SHA-1 `fca6c5b5116ae7fb16e2036b757ff294e0f790f6`;
- `Round6_Run22.mat`, SHA-1 `a995a2a89290dc32c5372b22e7bb5f469b6cf949`.

The two files contain 115,060 rows before the live-script speed filter and 102,276 rows afterward.

The independent oracle follows the live script's source selection, normalization, target-FZ scaling, operating-state order, point-count rule, and slip grids. It uses SciPy's smoothing-spline implementation with lambda 1.0, equivalent to the MATLAB p=0.5 objective, after stable count-weighted aggregation of duplicate slip coordinates.

The independent result matches the exact processed Trojan with:

- exact FZ, IA, P, SL, N, and V arrays;
- maximum SA difference `2.665e-15 deg`;
- maximum FX difference `1.073e-6 N`;
- maximum FY difference `5.545e-5 N`;
- maximum MX difference `8.802e-7 N-m`;
- maximum MZ difference `1.123e-6 N-m`.

These differences are numerical implementation cross-checks, not a replacement source fit. The exact hashed processed Trojan remains the governing source.

## Complete signed source-native exchange

The complete source-native exchange is frozen at:

`benchmarks/tires/WUFR26_H43105_R25B_COMPLETE_SIGNED_SOURCE_NATIVE_V0/manifest.toml`

It contains:

- one deterministic gzip-compressed little-endian binary64 payload and a human-readable manifest;
- exact source channels `SA`, `FY`, `FZ`, `IA`, `P`, `V`, and `SL`;
- 60 unique contiguous operating-state curves;
- 9,630 exact source `SA/FY` samples;
- both source slip signs;
- source peak and post-peak regions;
- the nine curves that fail the legacy strictly increasing pre-peak policy;
- exact source row order and whole-payload compressed/uncompressed SHA-256 identities.

No additional smoothing, refit, point deletion, envelope construction, symmetry completion, branch repair, clipping, extrapolation, or track scaling was applied.

The nine legacy pre-peak rejections no longer block preservation of the full signed source data. They still block the old magnitude-only pre-peak export policy for those states, and no source-specific named pre-peak/post-peak segment classification is authorized by this PR.

## Source convention evidence

The FSAE TTC Round 6 contents document states that all data is reported in SAE sign convention and identifies the SI channels as:

- SA in degrees;
- FY in N;
- IA in degrees;
- P in kPa.

Milliken and Milliken, *Race Car Vehicle Dynamics*, page 62 and Figure 2.33, define the cited SAE J670 tire system with +z down, identify positive slip angle as the wheel slipping to the right, and explicitly state that the road applies the listed forces and moments to the tire.

The source and repository canonical frames therefore differ by reversing y and z while retaining x. Under the repository's explicit alpha definition and road-on-tire force role, the current adapter candidate is:

- `alpha_rad = deg_to_rad(source_SA_deg)`;
- `Fy_canonical_N = -source_FY_N`;
- `inclination_rad = deg_to_rad(source_IA_deg)`;
- `pressure_Pa = 1000 * source_P_kPa`.

This candidate gives positive local canonical `dFy/dalpha` for all 60 source states.

`PARSER_April.m` is not copied directly. It declares a separate SAE-to-ISO route and negates SA and FY under that route's definitions. The repository canonical slip-angle definition is different, so mixing the two routes implicitly would be a sign-convention error.

## Remaining pressure-basis gate

The supplied TTC Round 6 contents and run guide call P “tire pressure” or “inflation pressure” and provide psi/kPa units. They do not explicitly state whether the channel is gauge or absolute pressure.

`AUTH-TIRE-0001` requires the source adapter to declare that basis and prohibits inference. Consequently:

- the source-native pressure values are preserved exactly;
- the numerical kPa-to-Pa conversion is known;
- the gauge-versus-absolute metadata is not resolved;
- the canonical adapter candidate is not reviewed;
- no executable canonical R25B table is published;
- `SOURCE_SPECIFIC_R25B_RUNTIME_ACTIVATION_AUTHORIZED` remains `False`.

## Activation gates

Completed:

- exact processed-source identity verification;
- exact live-script identity verification;
- exact generator-profile reconciliation;
- Round 6 raw-input lineage reproduction;
- source-channel and state-lattice audit;
- two source-derived pre-peak reference exports;
- complete signed source-native exchange;
- representative peak cross-checks;
- source-axis, slip-angle, and road-on-tire force-role evidence;
- deterministic source-native validation tests.

Still blocked:

- authoritative or explicitly reviewed pressure-basis decision;
- review of the complete source-to-canonical adapter;
- separate source-specific R25B authorization;
- executable canonical-provider benchmark and activation.

## Stopping point

PR #100 now stops at the pressure-basis and source-specific authorization boundary.

The next valid evidence is an authoritative TTC/Calspan statement identifying the P channel as gauge or absolute pressure. A reviewer may instead explicitly authorize a documented engineering interpretation, but it must not be represented as source fact. After that decision, the canonical adapter, executable R25B table, and a separate source-specific authorization can be reviewed before runtime activation.

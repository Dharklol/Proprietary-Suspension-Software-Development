# Phase 4 R25B runtime source activation review

## Decision

The exact hashed R25B Cornering Trojan source is now locally verified and audited. Two first-reference pre-peak branches were exported and frozen as quarantined evidence. The complete `MOD-TIRE-0001` R25B provider remains disabled.

Runtime activation is blocked because the observed binary structure does not match the frozen generator description attributed to the supplied, hash-matched `April_Interpolator.m` revision. The mismatch is material provenance evidence and cannot be repaired by assumption.

## Verified source package

The supplied files match the existing frozen source identities where those identities were already recorded:

- `Hoosier 43105 R25B Cornering Trojan.mat`: 333,286 bytes, SHA-1 `475338b18b6cba21b967c7e75bdd12d9a0e3437a`;
- `April_Interpolator.m`: SHA-1 `e73eb559b1e0be42cc9c135d86be69e168d9e606`;
- `PARSER_April.m`: SHA-1 `32608eef763acacb7b233b82b8690bd3250752cc`;
- `Round6_Run21.mat`: SHA-1 `fca6c5b5116ae7fb16e2036b757ff294e0f790f6`;
- `Round6_Run22.mat`: SHA-1 `a995a2a89290dc32c5372b22e7bb5f469b6cf949`;
- `Hoosier 18 x 7.5 - 10 R25B 43105.tir`: SHA-1 `27b100c306ec4f207c9c42506edeeb23c95d4247`.

`Comparisons.m` was also supplied and frozen for this review at SHA-1 `49f0758d61a5724c7b4aed10505c072bb6441725`.

The binary source is not committed to GitHub. Only its identities, structural audit, and quarantined derived reference values are retained.

## Source-native binary audit

The exact Cornering Trojan contains finite channels `ET`, `FX`, `FY`, `FZ`, `IA`, `MX`, `MZ`, `N`, `P`, `SA`, `SL`, and `V` with a common row count of 9,630.

The observed operating-state lattice is:

- normal load: 222, 445, 667, 890, and 1112 N;
- inclination: 0, 2, and 4 degrees;
- pressure: 55.2, 68.9, 82.7, and 96.5 kPa;
- speed: 40.2 km/h;
- longitudinal slip: zero.

All 60 state sweeps are stored contiguously, have strictly increasing source slip angle, and span -12 to +12 degrees. Their row counts are not uniform:

- 2 states have 100 rows;
- 13 states have 130 rows;
- 27 states have 160 rows;
- 18 states have 190 rows.

## Frozen generator-description mismatch

The supplied and hash-matched `April_Interpolator.m` describes a cornering output with:

- normal-load targets 222, 445, 667, and 1112 N;
- pressure targets 96.5, 82.7, and 68.9 kPa;
- inclination targets 0, 2, and 4 degrees;
- 100 points per state from -12 to +12 degrees;
- an implied total of 3,600 rows.

The exact binary instead has 9,630 rows, includes an additional 890 N load plane and 55.2 kPa pressure plane, and uses variable point counts. Therefore the currently supplied generator revision cannot be asserted to have produced the binary even though both hashes independently match the previously frozen manifest.

This review does not infer an undocumented loop, later script revision, append operation, or resampling rule. The exact generator revision or equivalent provenance record remains required.

## Candidate provenance artifact discovered in Box

A separate MATLAB live script was found in the same `TIRE SELECTION` Box folder:

- name: `TTC_Spline_Fitter.mlx`;
- Box file ID: `1890916633802`;
- Box file-version ID: `2085677125802`;
- size: 286,864 bytes;
- SHA-1: `c78a66751be956b60ff0f879cd0f733638a71ce3`;
- source content-modified time: `2025-05-24T06:12:37Z`.

Its name and timing make it a relevant candidate for the missing generation provenance, but its contents have not been inspected. The connector exposed metadata and download permission but not the raw `.mlx` bytes or an extracted representation. This review therefore does not claim that the live script generated the Cornering Trojan. The exact file must be obtained and inspected before the provenance gate can change.

## Real reference export

The frozen exporter interpretation was exercised on the two previously identified reference states. No smoothing, envelope, refit, point deletion, pressure rounding, track scale, or hidden operating-state interpolation was applied.

### Inside reference

At 222 N, 0 degrees inclination, and 82.7 kPa:

- 160 exact-state rows were available;
- 80 rows were in the selected negative-SA/positive-FY source quadrant;
- 64 rows formed a strictly increasing pre-peak magnitude branch;
- the source peak was 694.041896190421 N at -9.584905660377357 degrees.

### Outside reference

At 1112 N, 2 degrees inclination, and 82.7 kPa:

- 190 exact-state rows were available;
- 95 rows were in the selected negative-SA/positive-FY source quadrant;
- 86 rows formed a strictly increasing pre-peak magnitude branch;
- the source peak was 2737.8937842052433 N at -10.857142857142856 degrees.

These values agree with the existing rounded 83 kPa summary references of approximately 694 N at -9.6 degrees and 2738 N at -10.9 degrees. The agreement supports the two curve selections but does not resolve the generator mismatch.

The exact exported arrays are frozen in `benchmarks/tires/WUFR26_H43105_R25B_QUARANTINED_REFERENCE_EXPORT_V0.toml`. The file is explicitly not runtime authorized.

## Strict exporter diagnostics across the binary

Using the existing first-maximum and strictly increasing pre-peak rule:

- 51 of 60 observed states pass;
- 9 of 60 observed states are rejected;
- 29 of the 36 states on the previously documented 4x3x3 lattice pass;
- 7 of those 36 states are rejected.

The rejected curves contain small non-increasing source-spline increments before their first maximum. The exporter correctly refuses to smooth, envelope, delete points, or silently relax its tolerance. A different policy would be a new source-processing authorization, not a bug fix.

## Convention boundary

`Comparisons.m` identifies the comparison data as SI values in an SAE tire coordinate system with z down and documents the negative-SA/positive-FY quadrant as the desired leaning-into-turn branch. `PARSER_April.m` defines a separate TyDex route that negates slip angle, lateral force, overturning moment, and aligning moment while converting units to base SI.

Those two routes must not be mixed implicitly. The complete steady-state lateral provider needs a separately reviewed adapter that states:

- source and canonical axis handedness;
- source slip-angle definition and sign;
- lateral-force sign and force-role convention;
- inclination definition and sign;
- pressure unit and gauge/absolute basis;
- source preprocessing identity;
- whether both slip signs and post-peak ranges are admitted.

No canonical adapter is approved in this PR.

## Activation gates

Completed:

- exact source identity verification;
- supporting-artifact hash verification;
- source-channel and state-lattice audit;
- two source-derived reference branch exports;
- representative peak cross-checks;
- deterministic quarantined evidence record.

Still blocked:

- inspection of `TTC_Spline_Fitter.mlx` or equivalent generator evidence;
- exact generator-revision reconciliation;
- policy for the nine nonmonotonic pre-peak states;
- complete signed source-native curve exchange;
- source-to-canonical adapter review;
- source-specific runtime authorization.

## Stopping point

Further activation work would require inventing provenance or changing source-processing authority. The next valid input is the exact `TTC_Spline_Fitter.mlx` binary, another exact MATLAB generator revision, a dated generation log, or another reviewable record explaining the 9,630-row lattice and variable sweep lengths. Until that evidence is available, `SOURCE_SPECIFIC_R25B_RUNTIME_ACTIVATION_AUTHORIZED` remains `False`.

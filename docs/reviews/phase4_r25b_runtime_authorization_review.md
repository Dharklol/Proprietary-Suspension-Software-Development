# Phase 4 R25B source-specific runtime authorization review

## Decision

Reviewer **Dharklol** authorized the FSAE TTC Round 6 `P` channel to be treated as **gauge pressure** for the source-specific R25B runtime adapter on 2026-07-31.

This is a reviewer-authorized engineering interpretation. It is not represented as a TTC or Calspan statement, because no authoritative source documentation identifying the channel as gauge or absolute pressure was found.

## Authorized source

The authorization applies only to the frozen source-native exchange `WUFR26_H43105_R25B_COMPLETE_SIGNED_SOURCE_NATIVE_V0`:

- source tire: Hoosier 43105 18x7.5-10 R25B;
- intended engineering-proxy tire: Hoosier 43104 18x7.5-10 R20;
- processed source SHA-1: `475338b18b6cba21b967c7e75bdd12d9a0e3437a`;
- generator SHA-1: `c78a66751be956b60ff0f879cd0f733638a71ce3`;
- payload SHA-256: `3084bce3d519e088a3e3aa32f30ec8d45cf4f365e5d33028b8da45ca3f2fc438`;
- 60 operating-state curves and 9,630 exact source samples.

The source R25B identity and intended R20 proxy identity remain separate in every adapted curve and result.

## Reviewed canonical adapter

The explicit adapter is:

- `alpha_rad = deg_to_rad(source_SA_deg)`;
- `Fy_canonical_N = -source_FY_N`;
- `inclination_rad = deg_to_rad(source_IA_deg)`;
- `pressure_Pa = 1000 * source_P_kPa`, with the source value interpreted as gauge pressure;
- `normal_load_N = source_FZ_N` as a positive compressive magnitude.

The source force remains road-on-tire. The coordinate transform keeps source `+x` and reverses source `+y` and `+z` into the repository canonical left/up tire frame. The separate `PARSER_April.m` route is not reused or mixed into this adapter.

All 60 adapted curves produce positive local canonical `dFy/dalpha` around zero slip. This is a consistency check, not a replacement for the reviewed convention decision.

## Runtime scope

Authorized:

- exact loading and hash validation of the frozen exchange;
- exact sample-by-sample canonical adaptation;
- bounded forward evaluation;
- complete-cell interpolation over load, inclination, and pressure;
- all-root signed force inversion;
- explicitly labeled R25B-to-R20 engineering-proxy use.

Still excluded:

- claiming the gauge basis is a source-stated fact;
- implicit ambient-pressure addition or conversion to absolute pressure;
- literal R20 test-data claims;
- named pre-peak or post-peak branch selection;
- surface/track correction;
- aligning moment, longitudinal force, combined slip, transient, thermal, wear, or vertical-compliance behavior;
- vehicle equilibrium, steering design ranking, installed-car correlation, setup recommendations, or production authority.

## Verification

The source-specific provider must fail closed when the authorization, source identity, adapter identity, payload hash, state coverage, or gauge interpretation is changed. Its frozen verification checks:

- 60 unique states and 9,630 samples with no row loss;
- exact sign and unit transforms at representative samples;
- exact knot recovery;
- positive local canonical slope in every state;
- bounded eight-corner interpolation in an interior operating-state cell;
- rejection outside the supported pressure range;
- rejection of a tampered pressure-basis decision.

## Next checkpoint

Named inverse-branch selection remains blocked because the 60 source curves are retained as complete signed, unclassified responses. A separate branch-classification policy and authorization are required before a caller may request a named pre-peak or post-peak root. Aligning moment and vehicle/steering integration remain later, separately authorized work.

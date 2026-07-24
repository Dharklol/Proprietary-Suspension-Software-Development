# Phase 1 steering tire-informed target provider review

**PR:** #28  
**Task:** P1-STR-006H  
**Benchmark:** BENCH-STEER-0020  
**Review state:** ready for team review after final CI freeze

## Review question

Does PR #28 add the minimum tire fidelity needed to continue steering target development while preserving the existing steering evaluator, minimizing runtime dependencies, and leaving a nonredundant path to richer tire/vehicle models later?

## Implementation under review

PR #28 adds two deliberately separate layers.

### Reusable tire data layer

`src/pssd_tire/`

- source-preserving lateral summary grid;
- explicit tire operating point `(Fz, inclination, pressure)`;
- bounded trilinear interpolation with no extrapolation;
- explicit source peak-slip censor handling;
- dependency-free TIR metadata parser;
- optional SciPy MAT TTC channel reader;
- no Magic Formula evaluator in the core package.

### Steering target adapter

`src/pssd_steering/optimization/tire_targets.py`

- reuses the existing exact Ackermann helper;
- preserves the base inside-wheel target trajectory;
- adds an explicit utilization-scaled outside-minus-inside tire peak-slip differential to the outside-wheel Ackermann reference;
- emits the existing `OperatingStateTargetSet` contract;
- leaves candidate mechanism evaluation to MOD-STEER-0001.

No second steering solver or numerical optimizer is introduced.

## Tire source decision

The intended tire is Hoosier 43104 18 x 7.5 - 10 R20. The available TTC/model data are for Hoosier 43105 18 x 7.5 - 10 R25B.

The project explicitly approved use of the R25B TTC behavior as the engineering data equivalent for steering development. PR #28 records this as an engineering proxy rather than collapsing the source and intended tire identities.

Frozen source:

`benchmarks/tires/WUFR26_H43105_R25B_LATERAL_SUMMARY_V0.toml`

Source package records TTC Round 6 cornering runs 21/22 and drive/brake runs 35/36.

## Source-data safeguards

The lateral source sweep ends at approximately +/-12 deg slip angle. Any source peak reported at exactly 12 deg magnitude is marked censored. A default peak-slip steering query rejects any interpolation stencil touching such a point.

The provider also rejects pressure, inclination, or normal-load extrapolation outside the reviewed source grid.

These rules prevent the two most consequential silent source assumptions: treating a test-limit value as the true peak and extrapolating tire behavior beyond the data used to create the target.

## Historical MATLAB model treatment

The existing team MATLAB/Magic Formula chain is preserved in:

`benchmarks/tires/WUFR26_H43105_R25B_MATLAB_REFERENCE_V0.toml`

It is useful higher-fidelity external evidence, but it includes additional vehicle/model assumptions, including the historical hard-coded 2/3 lateral force and aligning-moment scale. PR #28 does not import that scale into the TTC data provider.

The Python steering runtime does not require MATLAB, the Magic Formula Tyre library, or SciPy.

## BENCH-STEER-0020

The deterministic development reference pair is intentionally chosen from uncensored source values at 83 kPa:

| role | Fz | IA | peak slip magnitude |
| --- | ---: | ---: | ---: |
| inside | 222 N | 0 deg | 9.6 deg |
| outside | 1112 N | 2 deg | 10.9 deg |

The tire differential is therefore:

`alpha*_out - alpha*_in = +1.3 deg`

The benchmark uses the existing historical steering rack/input sampling and an explicit development-only utilization schedule `abs(input_deg)/102`.

At the full-input endpoint, the existing base inside-wheel magnitude is 32.18468832 deg. Using the WUFR nominal wheelbase and steering-axis track, exact geometric Ackermann produces an outside-wheel reference of approximately 22.8686960462 deg; full tire differential produces approximately 24.1686960462 deg.

These are software-composition values. The benchmark wheel states/utilization schedule are not claimed as actual WUFR corner states.

## Tests

`tests/test_tire_lateral_summary.py` covers:

- exact source values;
- bounded trilinear interpolation;
- censor propagation and rejection;
- no extrapolation;
- TIR metadata parsing;
- optional MAT dependency behavior.

`tests/test_steering_tire_targets.py` covers:

- frozen 9.6 / 10.9 / 1.3 deg reference values;
- preservation of the inside-wheel target;
- mirrored outside correction;
- censored state rejection;
- explicit zero utilization at rack center.

The benchmark script additionally evaluates the generated target through the existing operating-state candidate evaluator.

## Governance changes

`AUTH-STEER-0002` is advanced to v0.9.0 with a dedicated PR #28 merge gate. It permits bounded tire-summary/target-provider work while continuing to prohibit a second steering evaluator, hidden TTC extrapolation, censored-peak promotion, automatic historical track scaling, production tire-optimal claims from development wheel states, and a full tire/vehicle equilibrium model inside this steering stage.

`P1-STR-006G` is recorded complete at PR #27 merge commit `34e6c98f1f47e1b986777bf05249db8e54b89ff2`.

`P1-STR-006H` records this PR as the tire-informed target-provider slice. P1-STR-006D rack-load/effort and P1-STR-006E physical installed correlation remain separate and unchanged.

## Review boundary

Approval of PR #28 means the software has a reviewed route from bounded TTC lateral behavior to explicit steering target curves.

It does **not** mean the benchmark target is the production optimum. Production-relevant tire targets still require a reviewed WUFR provider for realistic left/right wheel load, camber, pressure, and force demand. The architecture is intended to accept that provider later without changing the steering mechanism solver.

## Final CI freeze

Pending final PR-head CI run and generated `steering-tire-informed-target-reports` artifact. Exact benchmark-result values and final run number will be frozen here before review-ready closeout.

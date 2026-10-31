# Native computational-envelope study

## Scope and controls

This is an AUTH-VEH-0012 development orchestration study, not a new force law or
a vehicle grip/stability calculation. It reuses the native geometry, material
contact, mass, spring/ARB and signed tire providers already verified in the
development stack. No source data, force law, installed setup, tire symmetry
policy, target weight or physical acceptance tolerance is changed.

The selected 306.17484975 kg driver/no-fuel reference and the existing source
fixture controls remain explicit: V=8 m/s, four gauge pressures=68.9 kPa,
front/rear ARB setting 1 and the source spring reference. They are not recommended
setup defaults. The producer checks the native seed report's source hashes,
re-solves its straight seeds with current providers and starts two independent
signed searches from those accepted states.

The coarse curvature magnitudes are 0.02, 0.06, 0.10 and 0.14 per metre, preceded
by the explicit zero-curvature solve. At the first failed coarse attempt, retain
it and bisect the accepted/failed magnitude pair for at most three refinements,
stopping sooner only if its width reaches 0.001 per metre. Every new initial
point comes from an accepted state. Speed, setup, pressure, source revisions,
solver scales and original coordinate bounds stay fixed across that branch.

The original sideslip bounds are +/-0.08 rad. They are declared numerical
controls, not a tire-data boundary or identified physical sideslip limit.

## Method and interpretation

Every coarse and refinement attempt remains in the full report, including the
initial coordinates, requested case, final iterate, tire evidence, branch
signature, iterations, conditioning, scaled residual, independent physical
wrench and raw rejected-trial failures. A successful solve on a different source
branch is rejected and retained. The original direct/reflected inclination seam
is not crossed or smoothed.

Terminal failures are classified separately as tire source-domain failures,
geometry/contact/suspension failures, declared coordinate-bound failures,
confirmed reflection-boundary changes, other branch transitions, physical-closure
rejection, source/configuration mismatch, numerical/derivative failures or an
unclassified failure. A terminal line-search failure remains numerical even
when some rejected trial points had source-domain failures. Unrecorded skipped
out-of-bound trials cannot be reconstructed from an empty trial-failure list.

Per-axis lower/upper coordinate margins and source-query margins are retained.
The compact report identifies the closest solver bound after normalization by
its explicit coordinate scale, rather than comparing metres, radians and newtons
directly. Global tire-axis extents are labelled necessary, not sufficient:
complete-cell validity is still enforced by the existing tire evaluator. Slip
margins use the common supported interval of the actual participating curves.

The report's `status=pass` means both branch searches completed and recovered
their first requested nonzero sample; it does not mean all attempted states
passed. A successful last grid point is right-censored by the chosen grid, not a
failure or a limit. Refinement produces a pair of tested accepted/failed cases,
not proof of monotonic feasibility or support for every point between samples.

## Original-bound results

All 16 original-bound attempts are retained: ten accepted states and six failed
states. Both directions have the same coarse/refinement outcome:

| Curvature magnitude (1/m) | Stage | Outcome |
|---:|---|---|
| 0 | Seed | Accepted |
| 0.02 | Coarse | Accepted |
| 0.06 | Coarse | Accepted |
| 0.10 | Coarse | Accepted |
| 0.14 | Coarse | Decreasing line-search failure |
| 0.12 | Refinement | Accepted |
| 0.13 | Refinement | Decreasing line-search failure |
| 0.125 | Refinement | Decreasing line-search failure |

The last accepted magnitude is 0.12 per metre and the nearest tested failed
upper magnitude is 0.125 per metre. The machine field
`first_failed_magnitude_per_m` denotes this final failed upper endpoint; the
separate `first_coarse_failure_magnitude_per_m` retains the chronological first
coarse failure at 0.14. The stopping reason is `refinement_budget_exhausted`:
the final 0.005-wide pair does not meet the requested 0.001 resolution. No finer
boundary is claimed.

At magnitude 0.12, the kinematic acceleration magnitude V^2*abs(kappa) is
7.68 m/s^2, about 0.783 g using the fixture's g=9.81 m/s^2. All ten accepted
states pass the unchanged 1e-6 N / 1e-6 N*m physical gates; their largest force
and moment norms are approximately 1.51e-8 N and 1.21e-8 N*m.

| At magnitude 0.12 | Negative curvature | Positive curvature |
|---|---:|---:|
| Sideslip (rad) | -0.0773225 | +0.0776917 |
| FL normal load (N) | 1030.50 | 597.71 |
| FR normal load (N) | 586.19 | 1019.24 |
| RL normal load (N) | 1042.88 | 363.82 |
| RR normal load (N) | 344.02 | 1022.81 |

The failed final iterates approach the original lower/upper sideslip bounds to
roughly 1.8e-10 and 5.9e-10 rad. This observation motivates a numerical control
experiment; it is not reclassified as a tire grip limit or a converged state.
Failed-case force residuals remain visible and must not be compared with the
accepted-state residual maxima above.

## Separate sideslip-bound control

At each nearest failed magnitude (0.125 per metre), rerun from the original
accepted 0.12 state with only the sideslip box widened to +/-0.10 rad.
All other numerical settings, physical gates and case/source inputs remain
unchanged. The original envelope and its failed records are not overwritten.

Both separate controls converge on the original source branch:

| Direction | Recovered sideslip (rad) | Force norm (N) | Moment norm (N*m) |
|---|---:|---:|---:|
| Negative | -0.0800991 | 1.58e-8 | 9.51e-9 |
| Positive | +0.0804875 | 1.16e-8 | 1.33e-8 |

These recovered roots lie just outside the old sideslip box and inside the
new one. The original numerical bound excluded these particular solutions;
the old stopping point therefore does not establish a physical handling limit.
This does not prove uniqueness, rule out other roots in the old box or certify
the rest of the widened envelope. The new bound is a declared control input for
this experiment, not a change to the original fixture or a setup recommendation.

## Reproduction, packaging and verification

For each sign separately, with sign set to -1 and then +1:

```bash
python scripts/run_native_computational_envelope.py \
  --directions -1 --curvatures .02 .06 .10 .14 \
  --refinement-steps 3 --curvature-resolution .001 \
  --output native_envelope_-1.json --summary-output native_envelope_-1_summary.json
python scripts/run_native_envelope_bound_control.py \
  --report native_envelope_-1.json --sideslip-bound .10 \
  --output native_envelope_bound_control_-1.json
```

Use the corresponding +1 direction and `_1` paths for the positive branch. Then:

```bash
python scripts/package_native_computational_envelope.py \
  --reports native_envelope_-1.json native_envelope_1.json \
  --bound-controls native_envelope_bound_control_-1.json native_envelope_bound_control_1.json \
  --output native_envelope_combined_summary.json \
  --compact-output native_envelope_compact_summary.json
```

The compact reference is
`benchmarks/vehicle/native_computational_envelope_summary_v0.1.0.json`. The
packager rejects mixed source hashes, revisions, controls, pressure/setup states,
duplicate directions, mismatched attempt identities and authority promotion.
Input-report hashes bind the compact evidence to the full branch/control files.
Current source hashes are verified before packaging. Exact cross-runtime JSON
equality is not required.

Ten orchestration/packaging/control tests cover warm starts, failed-record
retention, censored grid ends, source/reflection branch rejection, seed failure,
conservative failure attribution, input/control validation, source/pressure
mixing, bound-distance normalization and changing only the declared sideslip
bounds. Existing kernel/motion tests remain unchanged. CI maps both directions
in separate jobs, uploads all produced branch evidence even on a job failure,
and packages only when both jobs succeed.

## Next analytical work

Separate numerical-control sensitivity from physical-input sensitivity before
declaring a larger usable envelope. In particular, any wider search must state
its sideslip/rack/load bounds and distinguish source-table edges from actual
force-capacity conclusions. Pressure, spring/ARB and alignment studies still
require explicit supported inputs and re-equilibration. Nothing here requests
hardware correlation or enables steering design ranking.

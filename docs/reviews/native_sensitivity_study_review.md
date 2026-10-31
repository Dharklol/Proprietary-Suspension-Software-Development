# Native numerical-control and physical-input sensitivity

## Scope and protocol

This follows the straight-state audit, manufactured low-force references and
native computational-envelope study. It adds no production force law, tire
extension, source extrapolation, installed setup, target weight or design ranking.
The owner requested continued analytical development before hardware exists.

Use the same source-verified 306.17484975 kg driver/no-fuel native reference,
V=8 m/s, source spring reference and baseline front/rear ARB setting 1. Source
pressures are 55.2, 68.9, 82.7 and 96.5 kPa gauge. Baseline 68.9 kPa is an
interior source knot, not the low edge of the table. These remain explicit
verification inputs, not selected vehicle setup recommendations.

The study controls are in
`benchmarks/vehicle/native_sensitivity_controls_v0.1.0.toml`:

- Physical cases: signed curvature +/-0.10 per metre, approximately 0.652 g.
- Uniform four-tire pressure increments: -2, -1, +1 and +2 kPa, separately.
- Front ARB setting 1 to 2 with rear held at 1; rear 1 to 2 with front held at 1.
- Numerical cases: signed curvature +/-0.125 per metre, with sideslip box
  +/-0.10 rad, comparison box +/-0.12 rad and a separate half-Jacobian-step case.
- Original scaled residual tolerance 1e-10 and physical closure limits
  1e-6 N / 1e-6 N*m remain unchanged.
- Numerical coordinate agreement criterion: max(abs(delta_x_i)/scale_i)<=1e-5,
  declared in the controls before comparison. This is numerical repeatability,
  not a vehicle accuracy interval.

All cases use the existing coupled solve. Each physical perturbation starts
from the same accepted physical anchor and re-equilibrates body pose, sideslip,
rack, holding force and four normal reactions. Geometry, wheel inclinations,
actual slip and tire queries are recomputed. A converged result on a different
source branch is retained but cannot supply a response comparison.

Saved coordinates are only seeds. Before use, verify all recorded source hashes
and packager identity, bind current provider revisions, and re-solve. The report
retains both stored and current revisions. Identical source bytes may yield
different numerical revision strings across supported runtime environments;
no saved equilibrium is promoted by rebinding its case metadata.

## Pressure and ARB responses

Each direction has seven physical runs: one anchor, four pressure increments
and two individual ARB changes. All fourteen converge on the accepted source
branch. The baseline rack magnitudes are about 9.19 and 9.21 mm.

The table gives maximum absolute changes across the two turn directions.
Fz change is the maximum change of any individual wheel, not total vehicle load.

| Perturbation | Rack change (micrometres) | Max individual Fz change (N) | Sideslip change (deg) |
|---|---:|---:|---:|
| Pressure -2 kPa, all tires | 4.612 | 0.0441 | 0.00701 |
| Pressure +2 kPa, all tires | 2.075 | 0.1164 | 0.00429 |
| Front ARB 1 to 2 | 0.835 | 4.3674 | 0.00356 |
| Rear ARB 1 to 2 | 2.299 | 5.3645 | 0.00413 |

The +/-1 kPa cases are retained separately in the report. The pressure response
is not centrally averaged across the source knot: each side has its own
finite-step output change divided by its signed pressure increment. These are
piecewise-source finite responses, not a claim of a unique smooth derivative
or a calibrated uncertainty distribution. ARB setting changes are discrete
comparisons, not stiffness derivatives.

For the two individual ARB changes, roll magnitude decreases in this fixture.
Maximum absolute roll changes are about 0.00201 degrees for the front setting
change and 0.00424 degrees for the rear setting change. This does not by itself
rank steady handling or establish a transient understeer/oversteer conclusion.

The local pressure-induced rack changes are small at this state and perturbation
size. The ARB change has a larger wheel-load redistribution than the pressure
changes tested. These observations cannot be extrapolated to other maneuvers,
alignment, larger pressure changes, different ARB settings or the real car.

## Numerical root evaluation versus recovery

The first six numerical runs re-evaluate accepted +/-0.125 states under three
settings (two anchors, two wider-box cases and two half-step cases). Their
coordinates remain identical. This checks root acceptance and tangent/rank
evaluation, but starting at a root does not meaningfully exercise recovery.

A separate experiment therefore uses the common explicit perturbation in
`benchmarks/vehicle/native_numerical_recovery_controls_v0.1.0.toml`:

| Coordinate | Added offset |
|---|---:|
| Body heave | +0.0001 m |
| Roll | +0.00005 rad |
| Pitch | -0.00005 rad |
| Sideslip | +0.001 rad |
| Rack | +0.0001 m |
| Holder and four Fz coordinates | 0 |

Every numerical variant in a direction receives exactly the same perturbed
initial coordinates. The seed must be inside every declared control box;
nonfinite/zero offsets, wrong coordinate order and clipping are rejected.
Acceptance additionally requires a nonzero initial residual above tolerance
and at least one Newton iteration, preventing a trivial zero-iteration pass.

The original Python 3.11 CI run exposed a contact-root precision floor: two
positive-turn variants stalled at a scaled residual of 1.1554e-10 against the
unchanged 1e-10 criterion. They remain rejected in
`benchmarks/vehicle/native_recovery_ci_precision_failure_v0.1.0.json`, with the
original run, artifact, iteration history and failed statuses retained.

The recovery study now explicitly evaluates the nested road-contact root at
1e-14 m, with a fourth variant at 5e-15 m. This tightens evaluation precision;
it does not relax Newton or physical acceptance. The baseline provider remains
at 1e-13 m. Physical geometry and component data are unchanged; distinct setup
revisions bind the numerical road configuration. Each direction now has four
off-root variants, including the independent tighter-contact comparison.
Both Python 3.11 and 3.12 pass all eight recovery cases in 3-7 iterations.
The maximum scaled-coordinate discrepancy is 5.04e-10, within the declared
1e-5 comparison criterion, with the same local source branch retained. This is a local recovery check, not
proof of uniqueness or convergence from arbitrary initial guesses.

The recorded protocol comprises 28 runs: fourteen physical, six numerical root
evaluations and eight off-root recoveries. No residual tolerance, physical gate
or source domain was relaxed. Numerical sideslip-box and contact-root controls
do not modify the baseline fixture or become physical vehicle limits.

## Reproduction and evidence

For direction -1 (repeat with direction +1 and `_1` paths):

```bash
python scripts/run_native_sensitivity_study.py \
  --seed-report benchmarks/vehicle/native_computational_envelope_summary_v0.1.0.json \
  --controls benchmarks/vehicle/native_sensitivity_controls_v0.1.0.toml \
  --directions -1 --output native_sensitivity_-1.json \
  --summary-output native_sensitivity_-1_summary.json
python scripts/run_native_numerical_recovery.py \
  --study native_sensitivity_-1.json \
  --controls benchmarks/vehicle/native_numerical_recovery_controls_v0.1.0.toml \
  --output native_numerical_recovery_-1.json \
  --summary-output native_numerical_recovery_-1_summary.json
```

Combine both signed studies and their matching recoveries:

```bash
python scripts/package_native_sensitivity_study.py \
  --studies native_sensitivity_-1.json native_sensitivity_1.json \
  --recoveries native_numerical_recovery_-1.json native_numerical_recovery_1.json \
  --output native_sensitivity_combined.json \
  --summary-output native_sensitivity_combined_summary.json
```

The compact reference is
`benchmarks/vehicle/native_sensitivity_summary_v0.1.0.json`. Full records retain
case/configuration identity, initial point, solved coordinates, signed tire
evidence, branch signature, iteration history and physical wrench. Failed or
branch-incomparable results cannot become zero response values. The packager
rejects mixed sources/controls, duplicate directions, missing protocol cases,
wrong recovery-to-study identity and authority promotion. Current source hashes
and input-report hashes bind the evidence; exact JSON equality across runtimes
is not required. CI regenerates both signed studies and recoveries in separate
jobs, uploads produced evidence even on failure, and combines only successful
jobs.

Eleven new tests cover perturbation isolation, numerical-control isolation,
nonlinear left/right finite-step responses, source changes, invalid controls,
common off-root seeds, clipping rejection and report packaging. The seventeen
existing kernel/motion tests and ten existing envelope/control tests are also
included in focused regression validation.

## Development implications

The numerical engine is stable under the limited controls tested at these two
states. Small local pressure changes and one discrete ARB increment produce
resolved, source-consistent responses. This supports bounded analytical
comparisons; it does not quantify vehicle-model accuracy or justify an optimum
setup from these small response differences.

The next high-return work is to freeze a representative intended configuration
and operating-case set, then examine the larger alignment/tire-assumption
sensitivities before a small re-equilibrated geometry comparison. Physical
correlation remains deferred until hardware exists. R25B-to-R20 proxy identity,
assumed negative-inclination symmetry, source bias, rigid circular contact,
uniform-acceleration lumped inertia and the virtual speed holder remain explicit
limitations. Actual tire-generated steering effort requires additional reviewed
moment/load modeling; existing prescribed-torque compliance screens remain a
separate capability.

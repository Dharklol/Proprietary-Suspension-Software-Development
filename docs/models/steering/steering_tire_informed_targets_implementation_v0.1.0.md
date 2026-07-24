# Tire-informed steering target provider implementation v0.1.0

## Purpose

PR #28 adds the first tire-informed target-generation path needed by the steering inverse-design stack. The implementation is deliberately split into a reusable tire-data layer and a steering-specific target adapter so future tire work can become richer without duplicating data parsing, source governance, or steering kinematics.

The implementation does **not** add a second steering evaluator, a Python Magic Formula clone, a load-transfer solver, or a full steady-state vehicle equilibrium model. Candidate mechanism behavior is still evaluated exclusively by `MOD-STEER-0001` through the existing `OperatingStateTargetSet` path.

## Source and tire identity

The current selected/intended tire is the Hoosier 43104 18 x 7.5 - 10 R20. The available TTC data/model package is the Hoosier 43105 18 x 7.5 - 10 R25B. The project explicitly authorized the R25B TTC behavior as the engineering data proxy for steering development on 2026-07-24.

The implementation therefore preserves two separate identifiers everywhere:

- source tire: `HOOSIER_43105_18X7.5-10_R25B`;
- intended tire: `HOOSIER_43104_18X7.5-10_R20`.

The proxy decision is authority metadata, not a claim that the compounds or part numbers are literally identical.

The frozen source record is:

`benchmarks/tires/WUFR26_H43105_R25B_LATERAL_SUMMARY_V0.toml`

The Box source package records TTC Round 6 cornering runs 21 and 22 and drive/brake runs 35 and 36. PR #28 consumes the lateral/cornering information needed for steering and inventories the drive/brake material for later expansion.

## Reusable tire layer

`src/pssd_tire/lateral.py` defines a source-neutral operating-point contract:

`TireOperatingPoint(Fz, inclination, pressure)`

and a `TireLateralSummaryGrid` containing:

- cornering-stiffness magnitude;
- peak lateral-force magnitude;
- source peak slip angle;
- explicit peak-slip censor status;
- source and intended tire identities;
- authority and provenance.

The first grid contains 36 operating points over:

- pressure: 69, 83, 97 kPa;
- inclination: 0, 2, 4 deg;
- normal load: 222, 445, 667, 1112 N.

Interpolation is bounded trilinear interpolation. Extrapolation is rejected.

### Peak-slip censoring

The source lateral sweeps terminate at approximately +/-12 deg slip angle. A source entry whose recorded peak occurs at `abs(SA) = 12 deg` is therefore treated as censored by the test boundary rather than a verified physical peak.

Default peak-slip queries reject an interpolation stencil that touches any censored source point. A caller may request the interpolated summary with censor information preserved for reporting, but that result is not admitted as an uncensored peak steering target.

This prevents the target generator from silently interpreting a test-limit value as an actual optimum.

## Optional source-file readers

`src/pssd_tire/io.py` provides two ingestion helpers without increasing core runtime dependencies:

### `.tir`

TIR files are parsed with the Python standard library into section/key metadata. This path intentionally does not evaluate Magic Formula equations.

### `.mat`

TTC MATLAB channels may be loaded when SciPy is already installed. SciPy is an optional reader dependency, not a package requirement. The reader exposes selected numeric source channels only and performs no fitting, filtering, sign conversion, or tire-force calculation.

The default channel inventory follows the historical team loader:

`FZ, SL, SA, P, IA, FX, FY, MX, MZ, N, V, TSTC`.

This separation allows later work to consume raw TTC or fitted TIR data without making MATLAB, the historical Magic Formula Tyre library, or SciPy mandatory for steering optimization.

## Historical MATLAB/Magic Formula reference

The team already has a substantially richer MATLAB/Magic Formula chain. PR #28 preserves it as external integration evidence in:

`benchmarks/tires/WUFR26_H43105_R25B_MATLAB_REFERENCE_V0.toml`

The historical `yaw_moment.m` model uses the H43105 fitted tire and includes vehicle mass, wheelbase, front/rear load distribution, load-transfer rates, static camber, and individual wheel force/moment calls.

It also applies a hard-coded `2/3` scale to lateral force and aligning moment as a sandpaper-to-real-road correction. PR #28 explicitly does **not** promote that scale into the TTC-derived tire layer. That factor belongs to the historical vehicle/model-correlation chain unless later track evidence independently authorizes it.

The MATLAB reference is therefore useful for future regression/parity work without becoming a runtime dependency or hidden authority source.

## Steering target adapter

`src/pssd_steering/optimization/tire_targets.py` converts tire slip behavior into an explicit differential steering request.

For each nonzero steering sample, the adapter:

1. preserves the base target's inside-wheel incremental heading;
2. obtains the exact zero-slip outside-wheel Ackermann reference from the existing reviewed `exact_ackermann_outside_reference` helper;
3. queries uncensored inside and outside peak-slip magnitudes at explicitly supplied tire operating points;
4. applies a visible slip-utilization factor `u` in `[0, 1]`;
5. constructs an ordinary `OperatingStateTargetSet` consumed by the existing operating-state evaluator.

The first differential relation is:

`delta_out,target = delta_out,Ackermann + u * (alpha*_out - alpha*_in)`

where `alpha*` denotes the peak-slip-angle magnitude from the tire provider.

The utilization schedule is explicit input data. It is zero at rack center. PR #28 does not infer force demand, lateral acceleration, wheel load, camber, or utilization from rack displacement.

That boundary is important: the adapter introduces tire-informed relative steering geometry without pretending that rack position alone determines the vehicle's operating state.

## BENCH-STEER-0020 development reference

The benchmark uses an uncensored TTC-envelope pair at 83 kPa:

- inside: Fz = 222 N, IA = 0 deg, peak-slip magnitude = 9.6 deg;
- outside: Fz = 1112 N, IA = 2 deg, peak-slip magnitude = 10.9 deg;
- outside-minus-inside peak-slip differential = +1.3 deg.

The benchmark utilization schedule is `abs(input_deg) / 102` over the existing historical steering sampling contract. These operating points and this schedule are software/development references, not claims that they are the WUFR-27 wheel states at a given steering input.

At full utilization the differential target shifts the exact Ackermann outside-wheel reference by +1.3 deg while preserving the base inside-wheel endpoint.

`BENCH-STEER-0020` verifies:

- source/intended tire identity preservation;
- source-grid interpolation and no-extrapolation behavior;
- source peak censor rejection;
- explicit 9.6 / 10.9 / 1.3 deg reference values;
- exact-Ackermann composition rather than duplicated steering equations;
- left/right mirrored target behavior;
- compatibility with the existing `OperatingStateTargetSet` evaluator;
- optional TIR/MAT ingestion boundaries;
- preservation of the MATLAB model chain as evidence rather than a core dependency.

## Expansion path

The architecture is intentionally reusable.

Future tire work can add richer response providers behind `TireOperatingPoint`-style contracts, including raw TTC interpolation, fitted TIR/Magic Formula evaluation, combined-slip behavior, aligning moment, or track-correlation layers. Those future providers should preserve the same source/provenance separation rather than reimplementing tire parsing inside steering.

For steering specifically, the next fidelity step is not another tire equation. It is a reviewed WUFR vehicle operating-state provider that supplies realistic front-left/front-right load, camber, pressure, and force-demand/utilization states. That provider can replace the PR #28 development reference pair without changing the steering mechanism evaluator or target aggregation architecture.

Aligning moment is intentionally retained in the source inventory because it will also be relevant to the later rack-load/steering-effort provider, but PR #28 does not couple it into steering effort.

## Authority boundary

PR #28 supports tire-informed **development targets**. It does not establish:

- production tire-optimal Ackermann;
- WUFR-27 or WUFR-28 production geometry authority;
- real wheel-load/camber states from the benchmark pair;
- track-corrected tire forces;
- installed tire correlation;
- combined-slip or transient tire truth;
- steering effort/rack-load authority;
- global/Pareto optimality.

Those claims remain behind their existing provider and physical-evidence gates.

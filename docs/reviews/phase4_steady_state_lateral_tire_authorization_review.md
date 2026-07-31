# Phase 4 steady-state lateral tire authorization review

## Review decision

`AUTH-TIRE-0001` is review-ready as the first shared tire-domain implementation authorization.

It authorizes `MOD-TIRE-0001`, a provider-neutral steady-state pure-lateral `Fy(alpha,Fz,inclination,pressure)` response kernel with:

- an explicit canonical tire contact frame and road-on-tire force role;
- coherent SI inputs and outputs;
- source-preserving signed curve records;
- piecewise-linear slip interpolation;
- bounded complete-cell operating-state interpolation;
- local piecewise slope reporting;
- all-root signed force inversion;
- structured fail-closed behavior.

## Why this is the correct next slice

Program B now supplies an accepted static load-path exchange, but maneuver integration still lacks a reusable tire-force provider.

The repository already contains:

- a bounded lateral summary grid;
- exact monotonic pre-peak branch inversion;
- a source-specific processed-Trojan exporter;
- source and intended tire identity governance.

The missing reusable layer is the signed forward response contract that vehicle, steering, and later QSS components can share.

This authorization builds that architecture without pretending that the real R25B full-curve source has already been recovered.

## Important scope correction

The initial implementation will be generic and synthetically verified. It will **not** activate a real Hoosier curve provider.

The existing 36-point R25B summary contains stiffness, peak force, peak slip, and censor information. Those quantities do not uniquely determine nonlinear `Fy(alpha)` shape.

The processed-Trojan exporter has been software-verified using synthetic arrays, but the hashed binary source has not yet produced a reviewed frozen branch table in the repository.

Accordingly:

```text
source_specific_r25b_runtime_activation_authorized = false
```

This is a source gate, not an architecture blocker.

## Canonical convention disposition

The shared interface freezes:

- right-handed tire contact frame;
- `+x` forward, `+z` road-normal upward, `+y` leftward;
- positive slip angle from velocity direction to tire-forward direction about `+z`;
- road-on-tire `Fy` positive along `+y`;
- radians, newtons, pascals, and N/rad internally.

Every external source requires an explicit adapter. No source sign, pressure basis, inclination sign, or force direction is assumed.

## Numerical disposition

The kernel is an exchange-table evaluator rather than a fit.

Allowed:

- affine interpolation between adjacent supplied slip samples;
- ordinary multilinear interpolation inside a complete compatible state cell;
- exact segment slopes;
- all-root affine segment inversion.

Not allowed:

- spline, polynomial, Magic Formula, brush, ML, or other fitting;
- extrapolation;
- clipping;
- nearest-neighbor repair;
- hidden smoothing;
- odd-symmetry completion;
- arbitrary branch selection.

## Verification disposition

The implementation must satisfy:

- `BENCH-TIRE-0001`: exact signed curve and slope mechanics;
- `BENCH-TIRE-0002`: complete-cell state interpolation and failure boundaries;
- `BENCH-TIRE-0003`: branch-aware inversion and blocked real-source activation.

Synthetic fixtures must be labeled as software verification and must not carry Hoosier or WUFR data authority.

## Deferred scope

Separate authorization is required for:

1. source-specific R25B full-curve activation;
2. aligning moment `Mz`;
3. longitudinal force `Fx`;
4. combined slip;
5. transient/relaxation response;
6. thermal, wear, speed, and pressure evolution;
7. tire vertical compliance and loaded radius;
8. four-corner vehicle/QSS integration;
9. physical track correlation;
10. steering, setup, design-release, or production decisions.

## Merge gate

After this authorization is reviewed and merged, the next branch may implement the generic kernel, synthetic fixtures, deterministic benchmark records, and dedicated CI.

The implementation must keep the real R25B provider disabled and visible in the result record until the source promotion gates are satisfied.

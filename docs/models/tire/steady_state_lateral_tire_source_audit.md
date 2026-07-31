# Steady-state lateral tire source audit

## Decision

The next reusable tire layer is a provider-neutral steady-state **pure-lateral** response kernel, not a new tire fit and not a vehicle equilibrium model.

The authorized first relation is

\[
F_y = f(\alpha, F_z, \gamma, P)
\]

with explicit source, frame, sign, domain, censor, and fidelity metadata. Aligning moment is the next planned tire quantity, but it is outside `AUTH-TIRE-0001`.

## Literature basis

Pacejka, *Tyre and Vehicle Dynamics*, second edition:

- Chapter 1, Sections 1.1–1.2 describes the nonlinear lateral-force characteristic, identifies small-slip cornering stiffness as the local slope, shows vertical-load dependence, and distinguishes pure lateral slip from combined slip.
- Chapter 3 develops physical steady-state slip-force generation and makes clear that saturation and peak/post-peak behavior are physical curve features rather than quantities recoverable from one stiffness and one peak point.
- Chapter 4, Section 4.2.1 treats pure-slip reference functions and their variation with wheel load and camber.

Guiggiani, *The Science of Vehicle Dynamics* (2022), Chapter 11 and Section 11.5.2 frame the steady-state tire behavior as an action surface and distinguish it from transient tire response.

These sources support a state-dependent steady response and explicit model boundaries. They do not make the current WUFR R25B/R20 proxy data complete.

## Existing repository tire assets

### Shared summary provider

`src/pssd_tire/lateral.py` and
`benchmarks/tires/WUFR26_H43105_R25B_LATERAL_SUMMARY_V0.toml`
provide a reviewed 36-point summary grid over:

- normal load: 222, 445, 667, and 1112 N;
- inclination: 0, 2, and 4 degrees;
- pressure: 69, 83, and 97 kPa.

The grid stores cornering-stiffness magnitude, peak lateral-force magnitude, source peak slip angle, and sweep-boundary censor status. It performs bounded trilinear interpolation and rejects extrapolation.

This summary is valuable for operating-envelope and peak/stiffness evidence, but it does **not** contain enough signed `Fy(alpha)` samples to reconstruct arbitrary nonlinear curves. In particular, a stiffness, a peak, and a 12-degree sweep-limit entry do not determine the intervening or post-peak response.

### Exact pre-peak branch inversion

`src/pssd_tire/force_demand.py` stores explicit monotonic pre-peak magnitude branches at exact operating points and inverts a bounded `|Fy|` demand into `|alpha|` by adjacent-sample interpolation.

This is already a useful source-preserving exchange contract. It is intentionally limited to:

- one exact operating point;
- one selected monotonic pre-peak branch;
- magnitudes rather than a project-wide signed tire convention;
- no operating-state interpolation;
- no post-peak root handling.

`MOD-TIRE-0001` generalizes the software mechanics without changing this existing contract.

### Processed-Trojan exporter

The repository contains:

- `src/pssd_tire/ttc_cornering.py`;
- `scripts/export_r25b_cornering_force_branches.py`;
- `benchmarks/tires/WUFR26_H43105_R25B_CORNERING_TROJAN_EXPORT_PROFILE_V0.toml`;
- `BENCH-STEER-0022` and associated synthetic exporter tests.

The exporter preserves a named processed-Trojan preprocessing route, selects exact operating states, and can emit the existing explicit pre-peak branch schema. Its software behavior is verified with synthetic Trojan-shaped arrays.

The repository does not yet contain a reviewed output from executing the hashed binary processed-Trojan source. Therefore, the actual R25B curve values remain unavailable for runtime activation.

## Tire identity boundary

The project-authorized development proxy remains:

- source tire: `HOOSIER_43105_18X7.5-10_R25B`;
- intended tire: `HOOSIER_43104_18X7.5-10_R20`.

These identities must remain separate. The proxy decision does not establish literal compound identity, installed-tire correlation, or track-corrected force truth.

## Canonical convention decision for the shared interface

The shared interface uses coherent SI units and a right-handed tire contact frame:

- `+x_t`: forward in the wheel plane projected onto the road;
- `+z_t`: road normal upward;
- `+y_t = +z_t × +x_t`: leftward.

The origin is the current contact-center reference on the road plane.

Positive slip angle is the signed angle about `+z_t` from the contact-patch velocity direction to `+x_t`. For positive forward transport,

\[
\alpha = -\operatorname{atan2}(v_{y,t},v_{x,t}).
\]

The returned lateral force is **road on tire**, positive along `+y_t`. A normal uncoupled response therefore has positive `Fy` for positive `alpha` under this convention.

Source conventions are never assumed compatible. Every source-specific adapter must retain and explicitly transform:

- source axes and handedness;
- slip-angle sign and unit;
- lateral-force sign and road-on-tire/tire-on-road role;
- inclination/camber sign and definition;
- pressure unit and absolute/gauge basis;
- source preprocessing and branch selection.

The real R25B adapter is still a promotion gate.

## Interpolation decision

### Slip interpolation

Between adjacent supplied signed slip samples, the kernel may use piecewise-linear interpolation. This is an exchange-table operation, not a tire-law fit.

No spline, polynomial, Magic Formula, brush model, neural network, smoothing, or outlier repair is authorized.

### Operating-state interpolation

Bounded interpolation in normal load, inclination, and pressure is authorized only when all corners of the bracketing Cartesian cell exist and are identity-compatible.

At the requested slip angle, the kernel first evaluates each participating curve independently, then blends the resulting forces with ordinary multilinear weights. The source curves therefore do not need a common slip grid, but every participating curve must support the requested slip angle.

Missing corners, incompatible source/adapter/fidelity identities, or a slip outside any participating curve fail the query. Nearest-neighbor substitution and extrapolation are prohibited.

## Inverse decision

A nonlinear or post-peak force curve can intersect one signed force demand more than once. The shared inverse therefore returns all roots and their segment/branch identities.

The kernel does not silently choose:

- minimum slip;
- maximum slip;
- pre-peak;
- post-peak;
- positive slip;
- negative slip.

A caller may request a branch only through an explicit reviewed branch policy.

## Source gaps that remain

Before a real R25B provider can be activated:

1. execute the hashed binary processed-Trojan source through the existing exporter;
2. freeze and review the actual curve exchange;
3. review the exact source-to-canonical sign, unit, pressure, inclination, and frame adapter;
4. determine which slip signs and post-peak ranges the source actually supports;
5. determine whether a complete interpolation cell exists at the required states;
6. cross-check representative curves against the selection notes and source plots;
7. keep any sandpaper-to-track correction outside the core provider until separately supported by track evidence.

## Deferred models

The following remain separate authorizations:

- `Mz(alpha,Fz,gamma,P)` and pneumatic-trail/rack-effort use;
- `Fx(kappa,Fz,gamma,P)`;
- combined slip;
- relaxation/transient response;
- speed, temperature, wear, pressure evolution, and surface evolution;
- tire vertical compliance and loaded radius;
- vehicle equilibrium, load transfer, QSS, steering ranking, lap simulation, and correlation.

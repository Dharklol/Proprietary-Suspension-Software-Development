# Steering Preimplementation Freeze Packet

**Status:** Proposed for review  
**Scope:** Analytical and synthetic verification required before rigid steering mechanism code  
**Target:** `MOD-STEER-0001`, `EQ-STEER-0001` through `EQ-STEER-0007`  
**Excluded from this freeze:** WUFR-26 Level E CAD signal/datum closure and physical Level F validation

## 1. Freeze intent

This packet freezes the model form, function behavior, synthetic fixture, expected analytical values, and failure semantics needed to implement a bounded rigid steering evaluator. It does not freeze WUFR-26 car parameters that still depend on CAD/FDR/drawing review.

The implementation gate is intentionally split:

1. **Fundamental evaluator gate:** exact geometry, equations, branch handling, analytical cases, and synthetic fixture.
2. **WUFR-26 cross-tool gate:** final car geometry, SolidWorks signal identities, static toe/datum, stops, and comparison tolerance.
3. **Physical-correlation gate:** measured steering sweep with uncertainty, compliance, backlash, and hysteresis.

Only the first gate is proposed for freeze here.

## 2. Frozen equation and function set

The proposed first evaluator contains:

- `EQ-STEER-0001`: exact low-speed Ackermann reference;
- `EQ-STEER-0002`: rigid tie-rod closure;
- `EQ-STEER-0003`: spatial steering position solution and wheel-heading extraction;
- `EQ-STEER-0004`: explicit steering-wheel/pinion/rack transmission chain;
- `EQ-STEER-0005`: local gain and secant ratio;
- `EQ-STEER-0006`: named kinematic turning-radius construction;
- `EQ-STEER-0007`: inside/outside assignment and Ackermann error.

The normative human-readable specification is `docs/models/steering/rigid_steering_function_specification.md`.

## 3. Source and validity hierarchy

| Function family | Equation authority | Why used | Main validity boundary |
|---|---|---|---|
| Rigid translation and axis-angle rotation | Euclidean rigid-body kinematics | Exact preservation of mechanism geometry; supports caster and steering-axis inclination | Bodies and steering axes rigid/fixed in the named state |
| Tie-rod closure | Rigid holonomic distance constraint | Direct mechanism law; no fitted curve required | Joint-center geometry and articulation valid |
| Ackermann reference | Guiggiani 3.4.1; Gillespie Ch. 8 | Exact low-speed no-slip analytical reference | Not a universal tire-performance optimum |
| Static toe versus incremental steer | Guiggiani 3.4 and recovered WUFR evidence | Prevents forced-zero curves and setup/kinematic ambiguity | Requires reviewed rack-center state |
| Local derivative and ratio chain | Implicit differentiation and chain rule; Gillespie Ch. 8 | Preserves angle-dependent steering ratio and clear signal identity | Away from singular/zero-gain states |
| Bracketed root solution | Standard safeguarded scalar root methods | Preserves a valid root bracket and reduces branch jumping | A valid bracket on the intended branch must exist |
| Shape-preserving imported-map interpolation | Fritsch-Carlson-type monotone cubic or reviewed linear interpolation | Avoids global polynomial oscillation and extrapolation | Comparison evidence only, inside source domain |

## 4. Synthetic geometry fixture

`GEO-STEER-BASIC-001.toml` is the frozen machine-readable fixture candidate.

It is a planar symmetric special case of the proposed three-dimensional model:

- body frame: `+x` forward, `+y` left, `+z` up;
- flat road plane `z=0`;
- vertical steering axes separated by `1.2 m`;
- wheelbase `1.6 m`;
- rear-steer rack translating along `+y`;
- zero static toe;
- identical left/right tie rods;
- intended branch passes through zero upright rotation at rack center;
- operational rack range `[-10 mm, +10 mm]`;
- geometric branch fold near `|s| = 12.3112188518 mm`.

This fixture is intentionally not dimensioned like a WUFR car. Its purpose is to expose sign, closure, branch, symmetry, derivative, and failure defects without relying on proprietary CAD interpretation.

## 5. Frozen analytical Ackermann cases

For wheelbase `l = 1.6 m` and steering-axis track `t = 1.2 m`, the following exact pairs are proposed:

| Inside incremental angle | Outside reference angle | Rear-axle-center radius | Cotangent difference |
|---:|---:|---:|---:|
| `5 deg` | `4.693539843118893 deg` | `18.888083684418152 m` | `0.75 = t/l` |
| `15 deg` | `12.577388257044907 deg` | `6.5712812921102035 m` | `0.75 = t/l` |
| `25 deg` | `19.059109112714346 deg` | `4.031211072815294 m` | `0.75 = t/l` |
| `35 deg` | `24.660121411405886 deg` | `2.885036810787384 m` | `0.75 = t/l` |

These values verify the exact equations, angle-unit conversions, quadrant handling, and radius reconstruction.

## 6. Frozen synthetic mechanism states

The expected states are stored at full precision in `GEO-STEER-BASIC-001.toml`. Review-facing values are:

| Rack displacement | Left heading | Right heading | Intended turn |
|---:|---:|---:|---|
| `-10 mm` | `+14.020640663 deg` | `+9.066487784 deg` | Left |
| `-5 mm` | `+5.782318646 deg` | `+4.810504238 deg` | Left |
| `0 mm` | `0 deg` | `0 deg` | Straight |
| `+5 mm` | `-4.810504238 deg` | `-5.782318646 deg` | Right |
| `+10 mm` | `-9.066487784 deg` | `-14.020640663 deg` | Right |

At rack center,

```text
d(delta_left)/ds = d(delta_right)/ds = -18.125 rad/m
```

or approximately `-1.038617 deg/mm`.

The fixture deliberately does not have exact Ackermann geometry. At `5 mm` rack displacement the outside-wheel Ackermann error is approximately `-0.56613746 deg`; at `10 mm` it is approximately `-2.81091130 deg`. This verifies that the evaluator can report a nonzero error without changing the mechanism response.

## 7. Benchmark definitions

### `BENCH-STEER-0002` — exact Ackermann relation

Verify all four analytical pairs, cotangent identity, and inside/outside radius reconstruction.

### `BENCH-STEER-0003` — reference closure

At rack center:

- derive equal left/right tie-rod length `0.3138470965295043 m`;
- recover zero total and incremental heading;
- report physical closure residual below `1e-10 m`;
- preserve the declared near-zero branch instead of the alternate assembly root.

### `BENCH-STEER-0004` — sweep, mirror, branch, and singularity

Over the five frozen rack states:

- reproduce left/right headings within `2e-8 rad`;
- satisfy mirror symmetry within `2e-8 rad`;
- preserve continuous branch identity;
- report monotonically signed response over each half sweep;
- fail at `s = +/-0.013 m` rather than substituting another assembly branch;
- warn before the active branch fold near `|s|=0.0123112188518 m`.

### `BENCH-STEER-0005` — transmission identity

For a synthetic constant relation, use:

```text
pinion angle per steering-wheel angle = 1.0
rack displacement per pinion angle = 0.010 m/rad
```

Then `theta_sw = +/-1 rad` must produce `s = +/-0.010 m`. Unit conversions between `m/rad` and `mm/rev` must agree:

```text
0.010 m/rad = 62.83185307179586 mm/rev
```

This test verifies the staged relation only. It does not assign the WUFR rack C-factor.

### `BENCH-STEER-0006` — local and secant ratios

At fixture rack center:

- implicit local gains are `-18.125 rad/m` on both sides;
- centered finite differences agree within relative `1e-6`;
- with the synthetic `0.010 m/rad` rack relation and one-to-one steering-wheel/pinion relation, local road-wheel gain is `-0.18125 rad/rad`;
- conventional local ratio magnitude is `5.517241379310345 steering-wheel rad / road-wheel rad`;
- the output name and sign remain explicit.

The reciprocal must be rejected when gain is zero or when the input identity is not steering-wheel angle.

### `BENCH-STEER-0007` — turning-radius construction

For each exact Ackermann pair, inside-derived and outside-derived rear-axle-center radii agree within `2e-9 m`.

For the synthetic non-Ackermann mechanism, report both derived radii and their mismatch. Do not silently average them into one authoritative radius.

### `BENCH-STEER-0008` — Ackermann error sign and toe treatment

- exact reference pairs produce zero error within `2e-10 rad`;
- synthetic fixture states reproduce the stored negative errors;
- adding equal-and-opposite static toe to total headings does not alter incremental-angle error after correct toe removal;
- inferring inside/outside from angle magnitude is prohibited.

## 8. Solver acceptance

The first implementation must demonstrate:

- deterministic results independent of sweep direction within tolerance;
- a bracket on the intended branch at every accepted point;
- root residual and physical length residual reported separately;
- no hidden clipping to wheel-angle or rack limits;
- no continuation across a singularity threshold;
- no replacement of a failed state with the alternate assembly root;
- no extrapolation beyond the requested or source domain;
- clear separation between numerical failure and physical infeasibility.

The exact root library is not frozen. The behavior is.

## 9. Result schema acceptance

Every point must retain:

- geometry-set ID and revision;
- equation/model revisions;
- input quantity identity and units;
- rack displacement;
- left/right total and incremental headings;
- inside/outside alias and turn direction;
- closure residuals;
- branch ID and root bracket;
- singularity/Jacobian diagnostic;
- Ackermann reference/error;
- named radius values;
- solver status and failure code.

Plots and UI tables are downstream views of these results and are not part of this freeze.

## 10. WUFR-26 items intentionally left open

The following do not block the synthetic evaluator but block final WUFR-26 benchmark freeze or higher maturity:

- exact steering FDR file/version/hash;
- WUFR-26 static toe and alignment configuration;
- identity of SolidWorks `Steer Input`;
- identity and orientation of `Dimension2`;
- monitor datum needed to produce toe-inclusive wheel heading;
- active SolidWorks configuration, motion-study settings, suppression state, and warnings;
- installed rack-stop travel and road-wheel mechanical limits;
- exact current-car steering-axis and joint coordinates with frame metadata;
- Test 1 fit-source discrepancy;
- physical sweep data and uncertainty.

The recovered `20.57 deg` value at zero input is an angular-monitor observation. It is not frozen as the toe-inclusive datum.

## 11. Authorization recommendation after review

After this packet is reviewed and merged, `MOD-STEER-0001` may be considered for **bounded prototype authorization** limited to:

- the rigid nominal-height evaluator;
- synthetic and analytical fixtures;
- WUFR geometry ingestion only when required definitions are supplied;
- no optimizer, tire target, steering effort, compliance, or design authority yet.

The implementation PR must include tests implementing the frozen cases. Passing registry CI alone is not engineering verification.
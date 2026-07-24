# Suspension geometry source contract v0.1.0

## Purpose

PR #38 starts the suspension R&D vertical slice by freezing the geometry boundary **before** implementing motion equations.

The contract is intentionally source preserving:

`reviewed source identity -> explicit source-frame coordinates -> reviewed transform -> canonical axle-local geometry -> future MOD-SUSP-0001 solver`

No suspension kinematics, load transfer, wheel-center construction, steering closure, compliance, or optimization is implemented in this slice.

## Frozen source

The nominal source is the Box file `WUFR-26 FINAL 8.21.2025.xlsx`:

- Box file ID `2014803790843`;
- Box version ID `2224178574043`;
- provider SHA-1 `15eadfb93369192038888da92ebaa6674db56cfa`;
- source vehicle setup `WUFR-26 FINAL 8.21.2025`, OptimumK version `2.0.2`;
- front setup `WUFR-26 Front FINAL 8.21.2025 0.5 and Front Fix`;
- rear setup `WUFR-26 Rear FINAL 8.2.2025 Fix 1`.

The file's Box text representation was inspected on 2026-07-24 and the hardpoint/setup values were transcribed into `data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml` without smoothing, fitting, mirroring, or kinematic inference.

A project SHA-256 of the raw XLSX bytes is **not** claimed in PR #38 because the Box raw-download action was unavailable. Provider file/version identity and provider SHA-1 are therefore frozen, and the missing raw-byte SHA-256 remains explicit.

## Coordinate convention

The source records the coordinate matrix `[[1,0,0],[0,-1,0],[0,0,1]]`. The reviewed conversion is:

```text
[x_can, y_can, z_can]_m = 0.001 * [x_optk, -y_optk, z_optk]_mm
```

Canonical orientation is right-handed:

- `+x` forward;
- `+y` vehicle left;
- `+z` upward.

Both source and converted coordinates remain available in the Python geometry objects.

### Origin boundary

The front and rear suspension definitions are retained in their respective OptimumK suspension-reference origins. The source `Reference Distance = 1562.400 mm` is preserved separately.

PR #38 does **not** infer a rear-to-front translation or claim that the two suspension-local origins already form one global body origin. That relationship must be explicitly reviewed before whole-vehicle placement is used by later models or visualization.

## Geometry represented

Each corner carries explicit source-backed records for:

### Double wishbone

- `CHAS_LowFor` — lower-arm forward chassis pickup;
- `CHAS_LowAft` — lower-arm aft chassis pickup;
- `CHAS_UppFor` — upper-arm forward chassis pickup;
- `CHAS_UppAft` — upper-arm aft chassis pickup;
- `UPRI_LowPnt` — lower upright joint;
- `UPRI_UppPnt` — upper upright joint.

### Chassis-to-upright lateral link

- `CHAS_TiePnt`;
- `UPRI_TiePnt`.

The link role is explicit rather than inferred from the common source naming:

- front: `steering_tie_rod`;
- rear: `chassis_locating_toe_link`.

This distinction is critical. The future front suspension solver must leave tie-rod-induced steering rotation unresolved so `MOD-STEER-0001` remains the steering closure authority. The rear source explicitly uses a chassis-attached toe link and later rear kinematics may use it as a locating constraint under a separate equation authorization.

### Actuation geometry

The source Push/Pull points are preserved for future motion-ratio and spring/damper work:

- `NSMA_PPAttPnt_L`;
- `CHAS_AttPnt_L`;
- `CHAS_RocAxi_L`;
- `CHAS_RocPiv_L`;
- `ROCK_RodPnt_L`;
- `ROCK_CoiPnt_L`.

The source attachment role is also frozen:

- front actuation attached to the upper A-arm;
- rear actuation attached to the lower A-arm.

No actuation equation is implemented in PR #38.

## Wheel/setup values

The source half-track, offsets, static camber, static toe, rim diameter, tire diameter, and tire width are retained as setup metadata.

PR #38 deliberately does **not** calculate a wheel-center point from these values. The earlier steering viewer omitted wheel centers for the same reason: the source meaning of the wheel offsets/reference origin must be reviewed before a coordinate is promoted to model authority.

This prevents a visually plausible but unreviewed wheel-center construction from becoming a hidden kinematic input.

## WUFR-27 baseline rule

`WUFR27_SUSPENSION_BASELINE_V0` inherits the frozen WUFR-26 source geometry with no current WUFR-27 geometry-change intent.

This is a development baseline for:

- native suspension-kinematics development;
- regression against OptimumK;
- future steering `SuspensionPoseSet` generation;
- visualization;
- later physical correlation.

It is not an as-built geometry declaration.

## Steering authority boundary

The OptimumK front `CHAS_TiePnt` and `UPRI_TiePnt` are retained because they are part of the suspension source package, but they do **not** replace the later steering-FDR tie-rod coordinates used by the nominal steering configuration.

For steering:

`WUFR-26 final OptimumK upright points + later steering-FDR tie-rod pickups -> MOD-STEER-0001`

For suspension-source recovery:

`WUFR-26 final OptimumK hardpoint file -> PR38 suspension geometry snapshot`

The two authorities are intentionally kept separate.

## Next implementation gate

`MOD-SUSP-0001` is registered as proposed only. Before rigid motion code is merged, a separate reviewed authorization must freeze at least:

1. the independent suspension-state coordinate for the first solver;
2. rigid control-arm and upright constraints;
3. zero-steer front upright-reference transport around the otherwise unresolved steering-axis DOF;
4. branch/continuity rules;
5. numerical method and failure states;
6. synthetic limiting-case benchmarks;
7. OptimumK comparison channels and acceptance rules.

That is the intended boundary between PR #38 and the following suspension-kinematics implementation slice.

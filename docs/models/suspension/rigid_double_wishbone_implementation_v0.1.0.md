# MOD-SUSP-0001 rigid double-wishbone implementation v0.1.0

**Authorization:** `AUTH-SUSP-0001`, merged through PR #39  
**Geometry baseline:** `WUFR27_SUSPENSION_BASELINE_V0`  
**Implementation:** `src/pssd_suspension/kinematics.py`  
**Scope:** rigid, ideal-joint position kinematics only

## Architecture

`MOD-SUSP-0001` consumes the source-preserving PR38 suspension geometry and evaluates one corner from an explicit internal lower-arm rotation `q_L`. The first implementation deliberately does not expose `q_L` as wheel jounce, rebound, heave, roll, damper travel, or tire vertical displacement.

Front chain:

```text
source hardpoints
  -> rigid lower/upper A-arm position solve
  -> minimum-twist zero-steer upright transform
  -> later SuspensionPoseSet adapter
  -> MOD-STEER-0001 front tie-rod closure
```

Rear chain:

```text
source hardpoints
  -> rigid lower/upper A-arm position solve
  -> minimum-twist reference
  -> rear chassis toe-link twist closure
  -> complete rear upright reference transform
```

Front tie-rod steering remains explicitly outside this module.

## Implemented equations

### EQ-SUSP-0001 — rigid A-arm rotation

Each outboard joint is rotated exactly around the fore-to-aft inboard hinge axis with Rodrigues axis-angle rotation. This preserves both A-arm leg lengths by construction; both physical leg residuals are still reported.

### EQ-SUSP-0002 — upper-arm closure

Given `q_L`, the lower upright joint is direct. The upper-arm angle `q_U` is the single unknown satisfying invariant upper/lower upright joint separation. The implementation uses an expanding continuation bracket around the predecessor state followed by bisection. It does not use unconstrained Newton or select a distant alternate assembly root after branch loss.

### EQ-SUSP-0003 — minimum-twist upright reference

The shortest rotation maps the nominal kingpin direction onto the current kingpin direction. Translation is anchored at the lower upright joint. Parallel same-direction axes give identity rotation; antiparallel axes fail explicitly because the shortest-axis rotation is not unique.

For the front this transform is only the deterministic unresolved-steering reference required by the steering provider contract. It is not a physical free-upright steering prediction.

### EQ-SUSP-0004 — rear chassis toe-link twist

For rear corners tagged `chassis_locating_toe_link`, the minimum-twist toe-outboard reference is rotated around the current kingpin axis and a scalar closure is solved against invariant toe-link length. The function rejects the front `steering_tie_rod` role.

## Numerical and failure behavior

The public solver returns structured results rather than silently clipping or repairing geometry. Explicit failure codes cover nonfinite input, out-of-domain request, degenerate hinge axis, missing closure root, branch ambiguity, root nonconvergence, zero kingpin length, antiparallel reference axis, and invalid rear toe-link role.

The current prototype angular domains default to ±90 deg and are reported with a provisional-domain warning. These are numerical development bounds, not hardware articulation limits.

The rear synthetic benchmark is intentionally a tangent/singular closure fixture at +10 deg. Its near-zero derivative is recorded as singular-limit evidence. The v0.1 benchmark samples the exact frozen solution; general singular-limit continuation can be hardened separately without changing the rigid equations.

## Result contract

A successful corner result includes:

- axle/side identity and requested `q_L`;
- solved `q_U`;
- lower/upper upright joint positions;
- current kingpin direction;
- minimum-twist reference transform and final rear transform when applicable;
- A-arm leg, upright separation, and rear toe-link residuals;
- closure derivative diagnostics;
- root bracket/iterations and continuation predecessor;
- warnings/failure state;
- geometry/configuration/source authority strings.

No wheel center, wheel plane, contact patch, roll center, motion ratio, spring/damper travel, rocker motion, ARB state, force, or compliance result is produced.

## Verification

`BENCH-SUSP-0001` verifies exact analytical parallel-arm motion. The frozen PR40 report gives maximum point error `8.01e-14 m`, maximum upper-angle error `2.13e-13 rad`, and maximum upright-separation residual `8.01e-14 m`.

`BENCH-SUSP-0002` compares the right-front WUFR geometry to the frozen OptimumK ±1 in pure-heave export. Across 11 states the maximum joint-center discrepancy is `5.106e-7 m` (0.511 µm), maximum `q_U` discrepancy is `1.277e-8 rad`, and maximum internal separation residual is `9.684e-14 m`, all inside the frozen acceptance limits.

`BENCH-SUSP-0003` recovers the synthetic +10 deg rear toe-link twist exactly within floating-point precision and records a closure derivative of approximately `1.39e-18 m²/rad`, confirming that the fixture is a tangent/singular limit.

Generated reports are produced by `scripts/run_suspension_kinematics_benchmarks.py` and the dedicated `Suspension kinematics validation` workflow.

## Wheelbase clarification

The team confirmed during PR39 review that `Reference Distance = 1562.4 mm` is the WUFR wheelbase. v0.1 records that fact but does not automatically translate PR38 rear source-local hardpoints into the front source frame. Whole-vehicle placement still needs an explicit source-origin adapter so wheelbase meaning and source-origin semantics are not conflated.

## Next gates

1. Review authoritative wheel-center/wheel-plane construction and define a state adapter from meaningful wheel/body displacement coordinates into `q_L`.
2. Compose front zero-steer suspension states with `MOD-STEER-0001` for native bump-steer verification.
3. Authorize actuation geometry separately before pushrod/pullrod, rocker, damper, motion-ratio, or ARB calculations.
4. Add suspension geometry to the 3D scene after the state and wheel-plane contracts are reviewed.

# WUFR-25 `Steering_range_optimization.m` Audit

**Status:** Structural and semantic inventory complete; engineering acceptance not granted  
**Box file ID:** `2025945253796`  
**Box SHA-1:** `4a4dfbf78a96e00840aef9f86e30dfee06331d65`  
**Source path:** `WashURacing/5. WUFR-25/WUFR-25 CAD & SOLIDWORKS DRAWINGS/4. STEERING/GEOMETRY`  
**Related migration:** `MIG-STR-0001`

## Observed purpose

Despite its name, the script does not solve rack, tie-rod, steering-arm, or Ackermann geometry. It performs a one-variable trade study for a dimensionless steering gear/range factor.

The script:

1. sweeps a factor `x` from `0.5` to `2.0` using 1000 samples;
2. calculates a baseline effort from a hard-coded torque/load-like value and a hard-coded angular/rack relationship;
3. defines a target effort equal to 80% of baseline;
4. calculates steering effort as an inverse function of `x`;
5. calculates steering input as `90*x`;
6. minimizes a weighted sum of normalized squared effort error and squared deviation of `x` from 1;
7. reports the selected factor, resulting effort, and steering input;
8. plots effort, input, and the scalar objective.

## Observed constants and settings

| Item | Observed value | Audit concern |
|---|---:|---|
| Sweep lower bound | `0.5` | Source of bound not documented in the script |
| Sweep upper bound | `2.0` | Source of bound not documented in the script |
| Samples | `1000` | Dense grid, but no convergence or resolution study |
| Hard-coded numerator | `79.5` | Physical quantity and unit not defined in code |
| Baseline input | `90` | Presumed degrees, but unit is not encoded |
| Hard-coded rack relation | `1/25` | Meaning and units not encoded |
| Target effort multiplier | `0.8` | Design rationale not encoded |
| Effort weight | `0.5` | Arbitrary unless supported by PDR/FDR requirement |
| Range weight | `0.5` | Arbitrary unless supported by PDR/FDR requirement |

## Preliminary disposition

**Disposition:** `benchmark_only` / historical design-intent evidence.

The script is useful for showing that WUFR-25 explicitly traded steering effort against steering range/input. It is not suitable as the canonical optimizer because:

- the variable is an aggregate factor rather than physical geometry;
- the effort expression is not linked to tire forces, steering-axis moments, efficiency, friction, or compliance;
- constants and units are implicit;
- objective terms and normalizations are hard-coded;
- no hard constraints or infeasibility result are represented;
- no left/right road-wheel map or Ackermann curve is calculated;
- no uncertainty, sensitivity, or alternate feasible solution is reported.

## Migration value

The replacement workflow should preserve the underlying design question without preserving this formulation:

- steering range or maximum steering-wheel input can be a hard bound, acceptable band, or target;
- steering effort can be a target or hard limit evaluated at declared operating conditions;
- weights and normalization must be named requirement records;
- the optimizer must expose the tradeoff rather than hide it in one unexplained scalar objective;
- geometry, transmission ratio, tire state, compliance state, and operating condition must remain separate inputs.

## Verification and recovery needs

Before using the script as a historical benchmark, recover the related PDR/FDR text that defines:

- the meaning of `79.5`;
- the source and units of `1/25`;
- why a 20% effort reduction was targeted;
- why equal weights were selected;
- whether `90*x` represents steering-wheel, shaft, or pinion angle;
- which final factor was selected and whether the design actually implemented it.

Any numerical reproduction should use the original source unchanged and report its output as a legacy study result, not as accepted steering physics.

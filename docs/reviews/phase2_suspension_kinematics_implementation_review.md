# Phase 2 suspension kinematics implementation review

**Model:** `MOD-SUSP-0001`  
**Authorization:** `AUTH-SUSP-0001`  
**Implementation PR:** #40  
**Review state:** implementation review-ready after final CI

## Decision scope

PR40 implements only the rigid ideal-joint equations authorized in PR39. It does not add wheel-center inference, front steering closure, actuation/motion-ratio physics, loads, compliance, vehicle equilibrium, or installed/as-built authority.

## Implemented behavior

- exact Rodrigues rotation of each A-arm outboard joint about its source-defined fore-to-aft hinge axis;
- one-scalar upper-arm closure from invariant upright joint separation;
- predecessor-centered bracket search and bisection, with no unconstrained Newton default or alternate assembly-root substitution;
- shortest-rotation/minimum-twist zero-steer upright reference transport;
- rear-only chassis toe-link twist closure;
- structured feasibility, residual, convergence, singularity, branch, and provenance diagnostics;
- explicit rejection of front `steering_tie_rod` use by the rear closure function.

## Verification evidence

Dedicated report source: `scripts/run_suspension_kinematics_benchmarks.py`.

Frozen result: `benchmarks/suspension/rigid_double_wishbone_result_v0.1.0.toml`.

At head `357d46d5b8e896201c0ed02089cc868879feb58e`, dedicated workflow run `30145980876` succeeded. Artifact `8616008771` has digest `sha256:392c8b198c880f0ee788083295453d3351467eb25683ba20effe291006755b6e`.

### BENCH-SUSP-0001

Analytical parallel-arm fixture:

- max point error: `8.0103e-14 m`;
- max `q_U` error: `2.1311e-13 rad`;
- max upright-separation residual: `8.0103e-14 m`.

All are inside the frozen analytical tolerances.

### BENCH-SUSP-0002

WUFR-26 right-front cross-tool comparison against `WUFR-26 8.21 Heaves 1inch.xlsx`, SHA-256 `db071b7e696149ec82213e9ed05aa557349d18d19debe7925e7e01058534e4b8`, OptimumK Result v2.3.0:

- 11 states from `-25.4` to `+25.4 mm` source heave;
- max upright-joint point discrepancy: `5.1058e-7 m` = `0.511 µm` versus `2 µm` acceptance;
- max upper-arm rotation discrepancy: `1.2766e-8 rad` versus `2e-5 rad` acceptance;
- max internal upright-separation residual: `9.6839e-14 m` versus `1e-9 m` acceptance.

This is historical external-kinematics cross-tool evidence only. Tie-rod/toe/steer/wheel-plane channels remain excluded from unresolved suspension-pose authority.

### BENCH-SUSP-0003

The synthetic rear fixture recovers the frozen `+10 deg` twist exactly within floating-point precision. The closure derivative is approximately `1.39e-18 m²/rad`, confirming the fixture is a tangent/singular limit rather than a well-conditioned operating state.

The current v0.1 benchmark deliberately samples that exact known root. Future singular-limit numerical hardening may improve detection of tangent roots that are not sampled directly; that does not change the authorized rigid geometry equations.

## Wheelbase clarification

During PR39 review the team confirmed `1562.4 mm` is the WUFR wheelbase. PR40 records the confirmation as provenance/context. It does not infer from that statement alone that the PR38 rear source-local hardpoint origin must be translated by exactly `-1.5624 m` relative to the front source origin. A later whole-vehicle placement adapter should make that frame relationship explicit.

## Remaining restrictions

The implementation is suitable for prototype rigid suspension-kinematics development and cross-tool comparison. It is not sufficient for:

- as-built suspension claims;
- authoritative wheel travel/camber/track outputs before wheel-center/wheel-plane construction is reviewed;
- front bump-steer without composition through `MOD-STEER-0001`;
- motion ratio, damper/rocker/ARB kinematics;
- packaging/articulation release;
- load transfer, tire force, compliance, or vehicle-response prediction;
- production suspension geometry optimization.

## Recommended disposition

Accept PR40 as the first implemented `MOD-SUSP-0001` prototype once final repository-wide and dedicated CI remain green. The next R&D slice should review the wheel-center/wheel-plane state construction and expose a physically meaningful displacement-state adapter before expanding the viewer or derived suspension metrics.

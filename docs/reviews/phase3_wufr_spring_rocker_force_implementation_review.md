# Phase 3 WUFR physical spring force at rocker implementation review

## Implemented scope

`src/pssd_suspension/wufr_spring_rocker_force.py` implements only `EQ-SUSP-0028` under `AUTH-SUSP-0014`.

The implementation takes a successful `MOD-SUSP-0003` current actuation state and a successful source-matched `MOD-SUSP-0004` spring state. It uses the exact current chassis eye, rocker eye, rocker pivot, and rocker axis; it does not reconstruct force direction from a scalar motion ratio.

For spring compression-force magnitude `F_s`, chassis eye `C`, rocker eye `D`, rocker pivot `R`, and unit rocker axis `a`, it returns:

- `e=(D-C)/||D-C||`;
- `F_rocker=F_s e`;
- `F_chassis=-F_s e`;
- `tau_s=a·((D-R)×F_rocker)`;
- `dL_d/dtheta=e·[a×(D-R)]`;
- an independent exact residual on `tau_s-F_s*dL_d/dtheta`.

## Failure behavior

The implementation fails closed for upstream actuation or spring failure, source/configuration mismatch, nonfinite geometry, negative spring-force magnitude, degenerate eye line or rocker axis, mismatch between the spring state's current coilover length and the exact current eye geometry, action/reaction residual, or rocker-torque identity residual.

No failed case is repaired by clipping, scalar motion ratio, guessed force direction, or a guessed non-spring damper contribution.

## Verification

`tests/test_suspension_wufr_spring_rocker_force.py` covers:

- nominal front/rear and bilateral current-car states;
- recovery of the existing reviewed nominal spring force values;
- exact equal/opposite physical eye forces;
- exact rocker-torque/virtual-work identity;
- mirrored right-side geometry;
- an arbitrary synthetic three-dimensional case;
- degenerate eye, negative force, source mismatch, and current-eye-length mismatch failures.

`scripts/run_wufr_spring_rocker_force_benchmarks.py` generates the `BENCH-SUSP-0025` diagnostics and retains the spring-only/non-installed authority boundary.

## Remaining boundary

This implementation does not make the KW spring/damper assembly a fully characterized static force element. Damper gas force, static seal friction/hysteresis, stops, and side loads remain outside authority.

The next structural step is a rocker free-body model combining the Level-1 push/pull force, this spring force, and the physical ARB linkage force. Before its pivot reaction can be described as a complete physical hardware load, the omitted non-spring damper effects need an explicit modeling/source decision.

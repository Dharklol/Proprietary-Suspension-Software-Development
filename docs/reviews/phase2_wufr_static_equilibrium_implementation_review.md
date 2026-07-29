# Phase 2 corrected WUFR static-equilibrium implementation review

## Decision

Accept the v0.2 implementation for review subject to the focused result-regeneration gate and the repository validation workflows.

The implementation applies the `AUTH-VEH-0010` correction without changing component force laws, ARB settings, contact geometry, gravity allocation, or the `MOD-VEH-0004` equilibrium solver. It retains the compatible unsprung-gravity direct and mapped terms separately and prohibits fallback to superseded `EQ-VEH-0016`.

## Primary frozen result

The deterministic setting-1/1 verification fixture converged in three iterations to:

```text
q_body = [-0.00269470796894 m,
          -0.0000801436408051 rad,
           0.00270600628303 rad]
```

Recovered road-normal reactions in `[FL, FR, RL, RR]` order are:

```text
[790.983101538,
 779.595626103,
 726.438934540,
 706.557613919] N
```

The final scaled residual norm is `2.49736e-11`. Independent physical closure is `5.18924e-8 N` resultant force and `4.61456e-8 N*m` resultant moment, both inside the unchanged `1e-6` gates.

## Independent correction evidence

The compatible unsprung-gravity chain-rule oracle passes at nominal and bounded nonzero body states. The maximum discrepancy against two-step compatible gravitational-potential differentiation is `9.01928e-7`, below the `1e-5` benchmark tolerance.

At the retained failed-probe body state:

- the superseded `EQ-VEH-0016` physical mismatch is `1.37727808188` in the force/moment residual vector and fails the physical-closure gate;
- corrected `EQ-VEH-0019` matches the independently assembled physical wrench to `2.65183e-8` maximum component mismatch;
- no balancing wrench is used.

This demonstrates that the prior disagreement was an omitted compatible generalized-force term rather than a solver-tolerance issue.

## Continuation and failure gates

The primary and alternate bounded initial guesses reach the same solution:

```text
maximum q_body difference       1.88940e-12
maximum road-reaction difference 1.41279e-7 N
```

The implementation also retains structured failure for invalid or missing ARB settings and does not introduce default settings, interpolation, state clipping, fitted retries, historical corner-load reconstruction, or old-equation fallback.

## Authority boundary

The frozen result is an `uncorrelated_design_intent_static_gravity` fixture. Setting `1/1` is verification-only.

The result is not installed/as-built authority, physical correlation, a setup recommendation, a maneuver load case, a complete carrier wrench, or structural-release evidence.

## Next gate

After this implementation is reviewed and merged, the next separate authorization may assemble a complete per-corner carrier external wrench from the accepted road reaction/contact point and source-owned unsprung gravity point load. Structural propagation through `MOD-SUSP-0007` remains downstream of that authorization.

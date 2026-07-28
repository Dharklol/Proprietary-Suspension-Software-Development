# Phase 3 WUFR partial rocker included-load authorization review

## Decision

Authorize the next narrow structural slice as `AUTH-SUSP-0016`: an explicitly **partial** rocker free body composed only from force contributions that are already physical and reviewed at the rocker boundary.

Included inputs are:

1. the Level-1 push/pull-rod axial reaction from `AUTH-SUSP-0012`;
2. the spring-only rocker-eye force from `AUTH-SUSP-0014`;
3. the physical ARB-link force from `AUTH-SUSP-0013`;
4. the exact current rocker pivot, axis, and application points from the reviewed actuation/Z-bar geometry stack.

The output may be an included-load pivot force resultant and equivalent transverse support couple. It must not be called the complete rocker pivot or hardware load.

## Why this is the correct continuation

The latest implemented spring bridge deliberately stopped before rocker equilibrium. The roadmap's Program B3 calls for actuation/reaction propagation while preserving local source ownership. The current stack now has the necessary exact physical vectors for the push/pull rod, spring, and ARB linkage, so those contributions can be composed without duplicating constitutive laws or using scalar motion-ratio shortcuts.

`AUTH-SUSP-0015` separately established that the KW V5 static damper contribution is not numerically authorized. Available project material identifies the purchased V5 piggyback damper family, but it does not supply the effective pressure area, nitrogen charge reference, gas volume/position law, or defensible static-friction loop. The WUFR26 dyno export is not a substitute: its metadata is internally inconsistent and does not uniquely separate gas bias from seal friction.

Therefore the useful mechanically honest result is an included-load reaction with a hard completeness boundary, rather than either stopping all rocker work or silently setting the omitted damper force to zero.

## Mechanics

For exact current rocker pivot `R`, reviewed unit rocker axis `a`, and included rocker forces applied at their exact points,

`F_sum = F_act + F_s + F_arb`

`R_pivot,included = -F_sum`

The ideal revolute support cannot provide a reaction couple about `a`, so the independently assembled scalar residual

`tau_axis = a dot sum((P_i-R) cross F_i)`

must be zero within the authorization tolerance. A nonzero residual is a failed or inconsistent upstream state, not permission to add a hidden balancing torque.

The perpendicular part of the applied moment sum may be returned as an equivalent support couple. It is not a bearing, bolt, tab, or frame-member load split.

## Source and topology checks required by implementation

The implementation must verify:

- axle, side, configuration, and geometry-source agreement;
- successful upstream result status;
- exact application-point identity rather than coordinate coincidence alone where IDs exist;
- the actuation force is mapped to the rocker as the equal-and-opposite remote-end force from the Level-1 result;
- correct left/right ARB-link result selection;
- finite vectors and a nondegenerate reviewed rocker axis;
- force and moment residuals independently reconstructed from returned vectors.

## Explicit boundary

The following remain omitted and must remain visible in every result/report:

- KW V5 gas/static extension force;
- seal friction and hysteresis;
- velocity-dependent damping;
- bump/top-out stops and side load;
- rocker weight and bearing friction/preload;
- bearing/tab/bolt load distribution;
- compliance, stress, buckling, fatigue, factor of safety, and installed/as-built authority.

A successful result is named `partial_design_intent_included_load_reaction`. Wording such as “total rocker load,” “complete pivot reaction,” or “rocker bearing load” is prohibited.

## Verification plan

`BENCH-SUSP-0026` should cover nominal front/rear and bilateral WUFR states, independent exact force/moment reconstruction, mirrored-side behavior, an arbitrary 3D analytical free body, and failures for source mismatch, application-point mismatch, degenerate axis, and non-closing rocker-axis moment.

No least-squares repair, clipping, absolute-value force handling, guessed damper offset, scalar motion ratio, or moved application point is allowed.

## Next gate after authorization

After review and merge, implement only `MOD-SUSP-0009` / `EQ-SUSP-0029` and `BENCH-SUSP-0026`. Complete rocker equilibrium remains blocked until a later authorization consumes traceable KW V5 static-force data or a reviewed slow bidirectional force-versus-position measurement.

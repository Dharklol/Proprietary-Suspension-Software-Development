# R25B steering force-demand branch handoff review

## Purpose

This checkpoint replaces the quarantined, magnitude-only reference export with an executable handoff derived from the exact `AUTH-TIRE-0003` classified R25B runtime curves. It does not create a vehicle force schedule or authorize steering ranking.

## Selected source response

The existing steering adapter consumes monotonic `|Fy|` versus `|alpha|` branches at exact operating points. The source-backed handoff selects the explicit canonical `negative_slip_pre_peak` branch and records the projection:

- `slip_angle_magnitude_deg = abs(alpha)`;
- `lateral_force_magnitude_n = -Fy`;
- source slip sign: negative;
- source canonical force sign: negative.

This is not a side guess based on magnitude. The signed source branch identity is fixed before the projection.

## Exact states

The first handoff is intentionally limited to the two long-standing reference states:

- inside reference: 222 N, 0 deg inclination, 82.7 kPa gauge pressure;
- outside reference: 1112 N, 2 deg inclination, 82.7 kPa gauge pressure.

The exact source branches contain 64 and 86 samples respectively. The inside range begins at approximately 0.07547 deg and 50.972 N and ends at approximately 9.58491 deg and 694.042 N. The outside range begins at approximately 0.06349 deg and 275.836 N and ends at approximately 10.85714 deg and 2737.894 N.

The previously rounded 83 kPa representation is not accepted as an exact operating state.

## Preserved boundaries

No zero-force anchor is inserted. A zero demand therefore lies below both explicit source branches and fails closed. This is different from the synthetic software fixture, which includes a hand-authored zero anchor.

The adapter introduces no smoothing, refit, point deletion, monotonic envelope, tolerance repair, symmetry completion, state interpolation, nearest-neighbor substitution, force extrapolation, or track-surface scaling.

The R25B source identity and intended R20 engineering-proxy identity remain separate.

## Steering boundary and next checkpoint

`AUTH-STEER-0003` already permits a source-specific exact-state pre-peak branch exchange. This handoff satisfies the tire-response side of that contract.

It does not supply the physical inside/outside lateral-response schedule for each steering sample. A source-backed steering target still requires reviewed state ownership and synchronization of:

- wheel load;
- inclination;
- gauge pressure;
- lateral-response demand;
- suspension pose;
- vehicle motion;
- target-state weighting.

Until that schedule is reviewed, the exact source branch may be exercised as a bounded provider and regression fixture, but it is not a WUFR steering design-ranking input.

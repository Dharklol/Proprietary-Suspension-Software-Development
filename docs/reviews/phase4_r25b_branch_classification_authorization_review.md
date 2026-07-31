# R25B named-branch authorization review

Reviewer **Dharklol** approved the recommended package on 2026-07-31. `AUTH-TIRE-0003` is downstream of the exact `AUTH-TIRE-0002` canonical R25B runtime table.

## Approved policy

- Use a strict monotonic prefix for each signed pre-peak branch.
- Label the existing segment crossing `alpha = 0` as `central_transition`; do not insert a zero-slip knot.
- When a first global side extremum is at the +/-12 degree source boundary, publish no post-peak branch for that side.
- Use explicit positive-slip and negative-slip branch IDs.
- Fail closed when a named branch is unavailable or identifies more than one root.
- Keep complete-curve all-root inversion available.

## Audit basis

The audit covers 60 curves, 9,630 exact samples, and 120 signed sides. No curve contains an exact zero-slip knot. Reversals before the first global side extremum affect 13 sides across 12 curves; the maximum local reversal is `0.48474469855204916 N`.

The strict-prefix worst case loses `6.812387228250657 N`, or `1.3213031258643019%`, and truncates `1.9622641509433962 deg`. The rejected global-extremum alternative can produce three side-local roots over a maximum ambiguous force span of `0.7573035179882481 N`.

A demonstrated post-peak decline is unavailable on 13 positive-slip sides and 18 negative-slip sides because the extremum is at the source boundary.

## Segment rules

Starting at the first same-side knot outward of the center-crossing segment, pre-peak classification continues only while outward response increases strictly. The first reversal segment and the remaining approach to the first global side extremum are side-specific `indeterminate_peak_approach`, not post-peak. Segments outward of an interior first global side extremum are side-specific post-peak.

Named selection is authorized only at exact source operating states. Forward evaluation and all-root inversion remain available at bounded interpolated states. Zero named matches produce `inverse_branch_unavailable`; multiple matches produce `inverse_branch_ambiguous` with no selected candidate.

## No-repair and authority boundary

Classification changes metadata only. It does not smooth, refit, envelope, delete, reorder, tolerance-repair, symmetrize, clip, extrapolate, add a zero-slip knot, or apply track scaling.

The R25B response remains an explicitly labeled engineering proxy for the intended R20 tire. This review does not authorize Mz, Fx, combined slip, transient response, thermal or wear state, tire vertical compliance, track correction, vehicle equilibrium, steering ranking, installed-car correlation, setup recommendation, or production authority.

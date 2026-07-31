# Phase 4 R25B named-branch classification audit

## Purpose and authority boundary

This audit evaluates possible named pre-peak and post-peak classifications for the exact canonical R25B runtime table authorized by `AUTH-TIRE-0002`.

It is diagnostic only. It does **not** assign `segment_branch_ids`, change any source sample, select a named inverse candidate, or authorize steering/vehicle use. Generic all-root signed inversion remains the only authorized inverse behavior.

## Source coverage

The audit uses the exact runtime table without smoothing, refitting, clipping, symmetry completion, pressure conversion, or track scaling:

- 60 operating-state curves;
- 9,630 exact source samples;
- 120 independently audited curve sides;
- signed slip domain from -12 to +12 degrees;
- source R25B identity retained separately from the intended R20 engineering proxy.

None of the 60 source grids contains an exact zero-slip knot. Each grid has an existing piecewise-linear segment that crosses `alpha = 0`. A branch policy must explicitly decide how that center-crossing segment is labeled; it cannot silently invent a new source knot.

## Exact findings

On each side, the audit walks outward from the sample nearest zero slip and defines the positional peak as the first global side extremum of outward response:

- positive side response: canonical `Fy` for positive slip;
- negative side response: `-Fy` for negative slip.

Small outward force reversals occur before the global side extremum on:

- 4 positive-slip sides, containing 7 reversal segments;
- 9 negative-slip sides, containing 13 reversal segments;
- 13 sides total across 12 unique curves.

The largest individual reversal is `0.48474469855204916 N`.

The source domain does not demonstrate a post-peak decline on every side. The global side extremum is at the +/-12 degree boundary on:

- 13 positive-slip sides;
- 18 negative-slip sides.

Those sides cannot honestly receive a demonstrated post-peak branch from this source domain.

## Candidate 1: strict monotonic prefix

Definition: classify outward segments as pre-peak only until the first force reversal. Stop before the decreasing segment. The remainder before the global extremum receives an indeterminate role rather than being mislabeled post-peak.

Properties:

- preserves every stored sample value;
- guarantees a monotonic side-local pre-peak branch and therefore a unique side-local inverse;
- reduces usable pre-peak reach on the 13 affected sides;
- requires an explicit indeterminate peak-approach role.

Worst observed cost:

- force shortfall: `6.812387228250657 N`;
- relative peak-force shortfall: `0.013213031258643019` or about 1.3213%;
- slip-domain truncation: `1.9622641509433962 deg`.

This is the conservative policy when unique named inversion is more important than retaining the full source approach to the global extremum.

## Candidate 2: global-extremum positional classification

Definition: classify every outward segment from the center region through the first global side extremum as positionally pre-peak, even when the exact response contains a small local reversal. Segments beyond a demonstrated interior extremum may be positionally post-peak.

Properties:

- preserves every stored sample value and the full global-extremum force reach;
- avoids deleting or repairing small source wiggles;
- creates narrow force intervals with multiple roots inside the named positional pre-peak region;
- therefore cannot promise a unique named candidate.

The largest ambiguous force-span union on one side is `0.7573035179882481 N`; the maximum observed side-local root count in these intervals is 3.

A valid implementation of this policy must fail closed when a named query has more than one candidate. It must return the candidate set and no silently selected root.

## Rejected under current authority: tolerance or isotonic repair

A tolerance-based monotonic envelope, isotonic regression, point deletion, or smoothing rule could remove the small reversals. Every such option changes the exact source response or its topology.

That conflicts with the current no-repair authorization. It would require a new fitted-data artifact, explicit error metrics, a separately reviewed authorization, and a new benchmark freeze. It is not a third implementation option under `AUTH-TIRE-0002`.

## Additional decisions required

A complete named-branch authorization must resolve all of the following together:

1. Choose strict monotonic-prefix or global-extremum positional pre-peak semantics.
2. Assign the existing segment crossing `alpha = 0` without inventing a zero-slip source knot.
3. Declare post-peak unavailable on sides whose extremum occurs at the source boundary.
4. Define fail-closed output when a named branch contains multiple inverse roots.
5. Define side/sign branch identifiers precisely enough that camber thrust does not cause magnitude-based branch guessing.

## Recommendation at this checkpoint

Do not authorize named branch selection yet.

For steering force-demand work, the strict monotonic-prefix policy is the safer default because its named branch can guarantee one side-local answer and its worst measured force-reach cost is only about 1.32%. The global-extremum positional policy is defensible when retaining complete peak reach is the higher priority, but it must expose ambiguity rather than selecting a root.

The next action is a reviewer decision between those two non-repair policies, including the center-crossing and boundary-peak rules. Until then, the executable R25B provider remains unchanged and generic all-root inversion remains authoritative.

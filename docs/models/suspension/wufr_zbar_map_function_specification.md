# WUFR Z-Bar Deformation-Map Function Specification

**Authorization:** `AUTH-SUSP-0006`  
**Status:** source contract frozen; WUFR numerical implementation blocked pending explicit mechanism fixture

## Intended interface

A future source-specific adapter will consume reviewed left/right suspension/rocker states and return a signed blade-tip elastic deformation and Jacobian:

`(q_L, q_R, mechanism_fixture, reference) -> delta_b, J_delta_b, diagnostics`

with

`J_delta_b = [partial(delta_b)/partial(q_L), partial(delta_b)/partial(q_R)]`.

`delta_b` is in meters. The existing WUFR blade constitutive adapter then evaluates

`F_b = k_b delta_b`

`U_b = 0.5 k_b delta_b^2`

and, only when `J_delta_b` is available,

`Q_ARB = -J_delta_b^T F_b`.

## Required mechanism fixture

The fixture must explicitly identify, for each axle:

- chassis-fixed blade pivot and blade rotation axis;
- blade working point and signed elastic working direction/observable;
- linkage endpoints and rigid linkage length;
- left/right rocker ARB pickup points in their reviewed rocker frames;
- transform from the `MOD-SUSP-0003` rocker state to each ARB pickup;
- frame convention and SI units;
- nominal zero-preload state and mechanism branch.

Raw sketch row ordering is not a fixture.

## Solver requirements

A later implementation may use direct rigid-body geometry or branch-preserving nonlinear closure. It must:

- preserve left/right identity and sign;
- enumerate or otherwise account for valid closure branches;
- continue from the named nominal branch;
- return structured failure for unreachable, singular, or ambiguous geometry;
- never repair a nominal residual with a hidden offset;
- expose closure residual and branch/conditioning diagnostics.

## Jacobian requirements

Analytic derivatives are preferred where practical. A numerical Jacobian is acceptable only when it:

- perturbs the actual reviewed input coordinates;
- remains on the same closure branch;
- uses declared finite-difference steps;
- checks at least two step sizes;
- fails rather than crossing a singularity or branch change.

## Explicitly forbidden substitutes

The implementation must not define WUFR `delta_b` from:

- body roll angle;
- track or half-track multiplication;
- left-right wheel travel difference by itself;
- historical `MR_f`, `MR_r`, OptimumK `Motion Ratio Heave`, or another scalar ratio;
- exporter sketch point row order;
- inverse fitting to historical axle `N*m/rad` or MATLAB `N*m/deg` values.

Those quantities may be used later as independent comparison checks only when their semantics are preserved.

## Reference behavior

The design-intent setup has zero intentional ARB preload. The nominal reviewed mechanism branch must therefore correspond to the zero-energy blade reference. If an explicit geometric fixture does not close at that state, the adapter must report a source/configuration inconsistency rather than subtracting the residual silently.

## Verification gate

No WUFR numerical implementation is authorized by this specification alone. The explicit mechanism fixture must first be frozen in the source record and reviewed. A later implementation PR must add numerical common/differential cases, closure residual tests, branch/failure tests, and independent two-step Jacobian checks before vehicle-coordinate generalized ARB force is available.

# WUFR Z-Bar Deformation-Map Function Specification

**Authorization:** `AUTH-SUSP-0006`  
**Status:** named nominal mechanism fixture frozen; scalar blade elastic-coordinate reduction still blocked

## Intended interface

A future source-specific adapter will consume reviewed left/right suspension/rocker states and the frozen nominal mechanism fixture and return a signed scalar blade deformation and Jacobian:

`(q_L, q_R, mechanism_fixture, reference) -> delta_b, J_delta_b, diagnostics`

with

`J_delta_b = [partial(delta_b)/partial(q_L), partial(delta_b)/partial(q_R)]`.

The existing WUFR blade constitutive adapter then evaluates

`F_b = k_b delta_b`

`U_b = 0.5 k_b delta_b^2`

and, only when `J_delta_b` is available,

`Q_ARB = -J_delta_b^T F_b`.

## Frozen mechanism fixture

`WUFR26_ZBAR_MECHANISM_V0` now explicitly identifies, for each axle:

- central blade/housing pivot;
- `+z` blade/housing pivot axis;
- left/right blade-link joints at opposite blade ends;
- left/right rocker ARB pickups;
- the corresponding reviewed rocker pivots and `+x` axes;
- nominal rigid linkage joint-center lengths;
- nominal blade-arm/link angles;
- coordinate-frame and source-registration rules.

The point roles come from cross-source agreement among populated geometry/assembly identity, Simscape topology evidence, the ARB owner's manual, and the WUFR-25 FDR. Raw sketch row order is not used as connectivity authority.

## Rocker pickup transport

Each ARB pickup is rigidly fixed to its rocker.

A future solver must obtain the moving pickup position from the already-reviewed `MOD-SUSP-0003` rocker state using the same one-axis rigid point transport represented by:

`src/pssd_suspension/actuation.py::rocker_point_at_angle`

A scalar historical motion ratio is not a substitute.

## Rear source-frame registration

The frozen rear ARB source requires the historical translation

`[+1.5604, 0, 0] m`

from the raw rear ARB sketch x origin into the rear OptimumK local suspension frame. It exactly aligns the recovered central ARB pivot with rear-local rocker x `-0.022225 m`.

This is a source-frame registration only. It must not replace or modify the separately reviewed current WUFR-27 wheelbase of `1.5624 m`.

## Remaining scalar-coordinate requirement

The nominal point mechanism is no longer the blocking source gap.

The remaining requirement is to freeze the exact physical definition of the **single** PR50 scalar `delta_b` for the installed two-ended blade.

The recovered sources establish two blade ends and two linkages, but do not state unambiguously whether the governing SolidWorks `k_b` is:

- a one-arm / one-end tip stiffness; or
- an already condensed symmetric two-ended blade-mode stiffness.

Therefore no implementation may create a scalar `delta_b` by introducing an unreviewed factor of `2`, `1/2`, `sqrt(2)`, or another modal scaling. The PR50 law must not be duplicated or stacked merely because two blade ends exist.

## Future mechanism solver requirements

After the scalar coordinate definition is reviewed, a numerical implementation may solve the linkage/blade mechanism against the frozen fixture. It must:

- preserve left/right identity and sign;
- move the rocker pickups with the reviewed rocker state;
- preserve the named blade/housing pivot and axis;
- enforce the reviewed rigid-link closure;
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
- inverse fitting to historical axle `N*m/rad` or MATLAB `N*m/deg` values;
- an inferred two-arm stiffness or energy multiplier.

Those quantities may be used later as independent comparison checks only when their semantics are preserved.

## Reference behavior

The design-intent setup has zero intentional ARB preload. The reviewed nominal mechanism branch must correspond to the zero-energy blade reference once the scalar `delta_b` definition is frozen. If the eventual closure does not satisfy the nominal source geometry, the adapter must report a source/configuration inconsistency rather than subtracting the residual silently.

## Verification gate

`BENCH-SUSP-0014` freezes nominal mechanism identity. It does **not** authorize a scalar WUFR numerical map.

A later implementation PR must add numerical common/differential cases, closure residual tests, branch/failure tests, and independent two-step Jacobian checks before vehicle-coordinate generalized ARB force is available.

# Tire force-demand to slip-angle inversion design

## Why the PR28 endpoints can look pro-Ackermann

PR28 did not solve the lateral force demanded from each front tire. It compared the **peak-slip magnitudes** at one manually supplied inside/outside operating-point pair:

- inside: 9.6 deg;
- outside: 10.9 deg;
- outside-minus-inside: +1.3 deg.

A positive differential commands **more outside-wheel steer relative to exact Ackermann**, so its correction direction is toward less Ackermann / anti-Ackermann. That does not imply the final wheel-angle pair crosses through parallel steer into geometrically anti-Ackermann. The exact Ackermann inside/outside separation can be larger than the 1.3 deg correction, leaving the final pair with inside angle still greater than outside angle. In that absolute geometric sense the endpoint still looks pro-Ackermann, even though the tire correction moved it in the anti-Ackermann direction.

This distinction is now made explicit:

1. **absolute geometry classification:** inside-minus-outside wheel angle relative to parallel steer;
2. **correction tendency:** tire-informed target relative to the exact Ackermann reference.

## Why peak-slip comparison is not enough

The tire does not generally operate at peak lateral force at every steering sample. The required slip angle depends on the force each tire must actually produce. A loaded outside tire may have a larger peak-slip angle while still requiring less, equal, or more slip than the inside tire at a particular force-demand split.

Therefore PR30 replaces the interim peak-slip utilization assumption with the provider boundary:

`(Fz, inclination, pressure, requested Fy) -> required slip-angle magnitude`

The steering correction is then based on:

`required outside slip - required inside slip`

Its sign may change with vehicle state, force split, camber, pressure, and the nonlinear tire curves. PR30 must therefore permit pro-Ackermann, less-Ackermann, and anti-Ackermann tendencies instead of assuming one globally.

## First implementation boundary

The initial `LateralForceSlipCurve` contract:

- accepts an explicit positive-magnitude monotone Fy(alpha) branch at one operating point;
- preserves source authority and provenance;
- performs bounded piecewise-linear inversion;
- rejects force demands above the reviewed curve maximum;
- does not extrapolate;
- does not fit or evaluate Magic Formula;
- does not infer wheel loads or force demands;
- reports the outside-minus-inside required-slip differential and its steering-correction tendency.

Synthetic curves verify software behavior only. R25B conclusions require reviewed TTC/TIR curves and representative vehicle force-demand states.

## Source/model work still required

The compact PR28 summary contains cornering stiffness, peak force, and peak slip, but not the full monotone Fy(alpha) branch needed for defensible inversion. PR30 must therefore add a reviewed source adapter from one or both of:

- filtered raw TTC cornering sweeps;
- the historical fitted TIR/Magic Formula chain, preserving its assumptions and excluding the historical automatic 2/3 track scale unless separately authorized.

The PR29 edge-case outside-front loads exceed the compact PR28 grid. No extrapolation from that grid is allowed. Representative weighted states and a tire response source covering their load envelope must be established before a WUFR steering target is frozen.

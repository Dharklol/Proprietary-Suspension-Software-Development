# Native steady-cornering upright transport

Development slice under AUTH-VEH-0012, ASM-VEH-0006 through ASM-VEH-0008,
and EQ-VEH-0023 through EQ-VEH-0026. This is not native equilibrium or
correlation evidence and does not extend the static contact authorization.

`steady_cornering_upright.close_native_upright` consumes the native suspension
wheel reference in the reconciled steering axle frame (metres, x forward,
y left, z up). Front minimum-twist transport moves the steering axis and outer
tie-rod joint while the rack joint remains chassis-fixed. MOD-STEER-0001 then
closes the tie rod at the explicit rack displacement exactly once. That angle
rotates every upright material point and direction, including the wheel center,
plane normal and forward hint. Rear wheels retain the native toe-link-closed
transform, independent of rack position.

The wheel coordinate remains the native pre-steering reference displacement,
the coordinate conjugate to the existing spring/ARB force composition. The
fully steered center can acquire additional vertical displacement. A future
contact adapter must differentiate this full transport with respect to that
same reference coordinate; copying the static centered-rack plane-only map is
not valid.

Road heading uses the existing wheel-plane/road intersection primitive. The
transported forward vector chooses orientation; simply projecting that vector
onto the road is not equivalent for an inclined steering axis and camber.

Four native-source tests verify both front sides at a one-degree lower-arm
state and an explicit 3 mm rack fixture, exact center/plane transport, tie-rod
closure, rigid material-point distances, intersection heading, both rear
toe-link states, rejection of already-steered input, and rack-domain failures.
These are verification controls, not a requested WUFR operating maneuver.

## Remaining composition and source gate

The shared-frame precondition must be checked by the final WUFR adapter,
including source identities and axle-origin translation. Body/road datum
transport, current material-point Jacobians, road compatibility, spring/ARB
composition and the accepted 306.17484975 kg driver/no-fuel allocation remain
to be integrated with the coupled kernel.

## Signed inclination source audit

Milliken and Milliken, *Race Car Vehicle Dynamics*, printed page 62, Figure
2.33 (page 94 of the supplied PDF), defines positive SAE inclination with
wheel top leaning toward tire-frame right. The active AUTH-TIRE-0002 adapter
preserves source IA sign when y/z are reversed into canonical left/up axes.
Pacejka, *Tyre and Vehicle Dynamics*, second edition, Chapter 1, Section 1.1,
also defines positive inclination as top-right when looking from behind.

Orient the fully transported plane normal toward contact-frame left, then use
`gamma = atan2(normal_left dot road_up, normal_left dot contact_left)`.
This is a right-handed rotation about forward and retains the signed result.
The normal's outward source orientation is reconciled without reflecting gamma.
The added test covers both sides, positive/negative static camber, and nonzero
static toe. Top-outward source camber maps to negative IA on the left and
positive IA on the right. Body rotation must precede this measurement in the
final heading-frame adapter.

The table contains only 0, 2 and 4 degree IA source curves. Opposite signed
inclinations therefore expose a real coverage gap. Unsupported queries must
fail. A future symmetry extension would need an explicit reviewed assumption
and simultaneous slip/force/inclination reflection, rather than absolute IA
alone. No such rule, extrapolation or source-table modification is introduced
here. Pressures and actual maneuver schedules remain explicit caller inputs.

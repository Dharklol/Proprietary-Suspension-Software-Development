# Native WUFR development composition

## Scope and owner decision

AUTH-VEH-0012 / MOD-VEH-0009 / EQ-VEH-0023 through EQ-VEH-0026 now compose
native suspension, front tie-rod steering, rear toe-link closure, rigid-circle
contact, the reviewed 306.17484975 kg driver/no-fuel mass allocation, existing
conservative spring/ARB forces, and the classified R25B forward table.
ASM-VEH-0006/0007/0008 remain the base maneuver approximations.

The owner explicitly accepted ASM-VEH-0009 on 2026-10-10 after being told the
source table has no negative-IA data. The optional runtime policy is
`development_negative_IA_reflect_slip_inclination_and_force`:

`Fy(alpha,Fz,gamma,P) = -Fy(-alpha,Fz,-gamma,P)` for `gamma < 0`.

It is an engineering symmetry assumption for uncorrelated development, not
measured negative-IA data, literal R20 data, or installed/predictive/setup
authority. AUTH-TIRE-0002/0003 and their source tables are unchanged. Explicit
provider selection is required in addition to the base case assumptions.

## Frames and coordinate ownership

Both front nominal kingpin joints are checked against the steering axis line
and its polarity before accepting the shared axle-local frame. Front minimum
twist transports the axis and outer tie-rod pickup, then MOD-STEER-0001 closes
the tie rod at the actual rack position exactly once. Every upright point and
direction uses that full rigid transform. Rear native toe closure is retained.

Axle-local points receive the reviewed front/rear x placement, followed by the
whole-vehicle source-to-body translation. Body rotation is `Ry(theta) Rx(phi)`.
The new heading-frame origin uses the reference CG x/y and source road z=0;
the reference body origin is consequently at `(0,0,z_CG_reference)`, plus body
heave. This explicitly reconciles the older static road frame's CG-height datum
with the coupled kernel's road at heading-frame z=0. The current mass-weighted
CG is computed from actual transported points, not substituted by that origin.

Road heading is the plane/road intersection with the transported forward hint.
Signed IA is measured after body rotation from the fully steered plane, with
plane normal oriented toward contact-frame left. The generic manufactured
fixture supplies its own horizontal force basis for synthetic virtual-work
checks; it is not the native wheel-plane heading authority.

The generalized wheel coordinate remains MOD-SUSP-0002's native pre-steering
reference-center vertical displacement. Front steering about an inclined axis
can move the actual center vertically; neither that center nor its map is frozen.
Contact roots use native q_L only as an internal parameter, bounded by the
source-owned inversion of the reviewed z_w domain. All force/Jacobian results
are chained back to the original z_w, preserving spring/ARB conjugacy.

## Contact roots and material virtual work

The fixed-radius geometric lowest point determines the current contact location.
Its full rigid-upright inverse freezes today's material point. Analytical body
Jacobians and two central q_L scales (0.0002/0.0001 rad), divided by the native
z_w/q_L derivative, give material virtual displacement. Richardson refinement
is accepted only after the existing absolute/relative convergence test passes.
Implicit contact reduction is `J_wb = -g_q/c`, using the same normal material
derivative. Separate body perturbations and virtual work at two scales verify it.

The source wheel bounds are +/-20 mm; body bounds are +/-10 mm and +/-0.01 rad.
Bounded root scans must find one root, every provider failure propagates, and
derivatives require two-sided domain. High-precision native settings are required
explicitly. The existing public component loader supplies road tolerance 1e-13 m
and kinematics/physical inversion tolerances 1e-14. Static equilibrium is never
called for a maneuver and the static contact implementation is unchanged.

The native solver fixture uses a 1e-10 scaled residual tolerance. An exploratory
1e-11 trial reached the source numerical floor (~1.56e-11 scaled) and correctly
failed its decreasing line search despite a physical force residual ~6.4e-9 N.
The chosen fixture criterion accommodates that observed floor; the independent
1e-6 N / 1e-6 N*m acceptance limits are unchanged and mandatory.

## Tire lookup and branch boundaries

Each output retains the requested signed query and the actual transformed
source query, source curves/segments, interpolation weights, fractions, exact
knot status, signed source labels and provenance. Force changes sign under
reflection; left/right slip derivative roles swap. Load and pressure do not
change. Transformed out-of-domain queries fail without clipping/extrapolation.

The forward continuation signature joins positive/negative pre-peak and central
transition only where source segments have positive slope. This is a connected
central-region guard, not named inverse selection. Original signed source labels
remain explicit; post-peak and indeterminate approaches remain distinct. A
direct/reflected boundary change is blocked by the coupled solver's branch check.

The measured zero-IA curves need not be odd. At the verification probe
alpha=0, Fz=700 N and P=75 kPa, direct zero-IA Fy is -46.2255318888 N; the
negative-IA reflected limit is opposite, giving a ~92.4510637776 N jump. This
is an artificial seam in the assumed extension, not tire physics. No smoothing
or bias removal is authorized. No successful reported native sample crosses it.

## Verification fixtures and remaining work

Four upright tests, six tire-extension tests and five native geometry tests pass.
The native benchmark runner solves eight samples in two continuation branches:
V=8 m/s, curvature 0 and +/-0.005, +/-0.01, +/-0.02 per metre, four explicitly
selected source gauge pressures of 68.9 kPa, and discrete front/rear ARB setting 1.
The spring reference is the source package's zero-preload/full-extension reference.
These are labelled source-integration verification controls, not user operating
defaults, setup recommendations or a real simulation export.

`benchmarks/vehicle/wufr_steady_cornering_native_development_v0.1.0.json` retains
all cases, numerical controls, source hashes, geometry/Jacobians, five mass points,
current CG/inertia/holder, tire query evidence, complete wrench contributions,
root/branch and iteration records. CI regenerates and uploads the native report.
The measured force/moment maxima are on the order of 1e-8; exact values are in
the report. No full-producer promotion is claimed by this bounded fixture slice.

Next is the synchronized operating-state/paired unresolved-front-pose exchange
and source-preserving varying-state steering consumer. PR 106 remains the paired
native pose adapter dependency; this scalar force/geometry composition does not
duplicate or land that adapter. Actual maneuver schedules, four pressures and
discrete ARB settings remain explicit caller inputs. Any predictive, installed,
structural or design-ranking promotion remains a separate review gate.

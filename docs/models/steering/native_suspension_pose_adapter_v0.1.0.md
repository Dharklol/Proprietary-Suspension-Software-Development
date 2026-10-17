# Native suspension pose adapter

The project owner authorized native pose composition on 2026-10-10 and selected
the reviewed 306.17484975 kg driver/no-fuel vehicle reference. This adapter composes
existing EQ-SUSP-0003 minimum-twist transport and the steering pose contract;
MOD-STEER-0001 continues to solve tie-rod closure. It adds no maneuver equations.

`build_native_front_pose` takes a reviewed suspension geometry set, successful
left/right front corner results, a named pose state, and a `NativePoseFrameMap`.
It verifies corner identities, geometry/configuration/source authority, canonical
axes, and availability of the minimum-twist transform. The transform is checked
against minimum twist reconstructed from the upright joints, so an added kingpin
rotation is rejected even if its role label claims zero steering.

Both input and output frames use metres and x-forward/y-left/z-up. The explicit
origin map is `p_steering = p_suspension + o`. Consequently a native transform
`R p + t` becomes `R p_steering + t + o - R o`. An origin offset is required even
when it is zero. Arbitrary axis changes, rear poses, body-to-road rotation, and
already-steered poses are outside this adapter.

The reviewed WUFR26 coordinate reconciliation requires no translation for the
front nominal geometry. The integration fixture checks the actual steering-axis
lower points against native front lower upright points before using this zero
offset. This is specific to those frozen sources, not a default for future CAD
models. Source frame, catalog/version, geometry ID, configuration ID, mapping
revision/path, and origin offset are retained in pose provenance. Caller revisions
remain declarations; a matching label is not physical correlation.

The returned pose can be passed to `apply_pose_state`, `SuspensionPoseSet`, or
the synchronized sample composer. Rack geometry and tie-rod length remain owned
by the existing steering candidate. Native transport moves upright-bound steering
geometry; the existing steering solver then resolves steering once. The adapter
does not use OptimumK front tie pickups to overwrite the final steering-FDR points.

Verification covers nominal identity, symmetric positive/negative and asymmetric arm travel,
nonzero-origin point and direction parity, native identity/source mismatches,
missing transforms, invalid mappings, role and hidden-rotation rejection, and
WUFR steering composition at rack positions -10, 0, and +10 mm. These checks
establish software consistency, not installed bump-steer correlation.

Remaining work is a maneuver producer supplying compatible four-wheel loads,
body motion, signed force demands, tire pressure, and contact-frame inclination.
Minimum-twist wheel-plane inclination alone is not final steered tire inclination.
The 320 kg workbook loads remain separate evidence; choosing the 306 kg reference
does not authorize scaling those loads or selecting target weights.

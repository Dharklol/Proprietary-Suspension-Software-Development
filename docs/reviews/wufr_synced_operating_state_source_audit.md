# WUFR synchronized operating-state source audit

Audit date: 2026-10-10. Repository baseline: `c2e08edd3bcc52afdfea5b43606d365edacb5c20`
(PR 105). Status: source audit only; no new model or maneuver authority.

## Decision

The synchronized exchange, tire readiness, and bounded steering consumer now exist.
The reviewed repository sources do not yet populate a compatible WUFR maneuver
package. Do not create a target by mixing static results, nominal alignment,
spreadsheet loads, and a constructed body-motion schedule.

This audit covers checked-in providers and source records. It does not establish
that no suitable export exists elsewhere in team storage.

## Provider capability and remaining work

| Required quantity | Existing owner/evidence | Available capability | Remaining boundary |
|---|---|---|---|
| Configuration, mass, CG, geometry | `pssd_vehicle.reference`, whole-vehicle and gravity records | Reviewed driver/no-fuel reference, 306.17484975 kg | Maneuver configuration must identify the same assembly, driver/fuel state, frame, and source revisions |
| Four normal loads | `wufr_static_equilibrium_core` / runtime, `AUTH-VEH-0010` | Four recovered static road-normal reactions and independent wrench closure | Uncorrelated static gravity only; no maneuver loads or installed setup authority |
| Development maneuver loads | `WUFR27_SUSPENSION_CALCULATIONS_OPERATING_STATES_V0.toml` | Two explicit four-wheel 1.2 g cases at 17.8816 m/s | Evidence-only, zero weight, no ARB contribution, different mass reference, front load-domain failures |
| Wheel geometry / inclination inputs | `pssd_suspension.wheel_reference` | Transported wheel center, plane normal, forward reference, upstream state | Inclination must be derived in the current tire/contact frame with body pose and steering closure; nominal camber is not maneuver inclination |
| Front zero-steer pose | Native `minimum_twist_transform`, existing steering pose and external import contracts | Native transform excludes front steering twist; external pose interface is implemented | No native-to-`SteeringPoseState` publication path found in the reviewed optimization modules; verify frame/origin and parity in a separate bridge increment |
| Tire gauge pressure | Tire source tables and runtime | Response at explicit source pressures; reviewed pressure-basis interpretation | Source test pressure is not the selected vehicle setup; obtain an explicit setup/schedule pressure |
| Signed per-wheel lateral demand | Wheel-state contract and tire providers | Stores demand and evaluates/inverts response once supplied | No reviewed maneuver producer supplies the required demand schedule; tire inversion cannot allocate vehicle force |
| Body u/v/r | `pssd_vehicle.planar_kinematics` | Exact kinematics and explicit motion-schedule contract | Does not predict sideslip/yaw response; selected workbook supplies speed, not synchronized u/v/r |
| Rack grid and synchronization | PR 105 sample/sweep contracts | Exact grid, state/configuration/revision checks, source preservation | An upstream exporter must supply matching sample identities; stamps are assertions, not independent correlation |
| Target weights and authority | Existing vehicle/target contracts | Explicit role and positive design-input weight | Development workbook is evidence-only; no weight or design-input promotion is authorized |

## First concrete case inspected

Candidate evidence: `SC26_EDGE4_1P2G_LEFT_AERO_NO_ARB`, from the frozen development
workbook exchange. This is a source-inspection case, not a selected design maneuver.

- Left turn; canonical ay = +1.2 g; ax = 0; speed = 17.8816 m/s.
- Front inside/left Fz = 516.8481725 N: within the scalar R25B load interval, but
  not an exact source knot. Complete-cell availability still requires inclination
  and pressure; interval membership alone does not establish runtime feasibility.
- Front outside/right Fz = 1388.941263 N: above the 1112 N source maximum.
- Inclination, pressure, lateral demands, suspension pose, and u/v/r schedule are
  missing. Weight remains zero and role remains evidence-only.

The right-turn case is also unusable: inside 186.2139907 N is below 222 N, and
outside 1719.575445 N exceeds 1112 N. PR 103's readiness conclusion remains valid.
Do not reduce acceleration, clip loads, or substitute tire knots to make either case
pass. A different maneuver must come from its own reviewed source or an explicitly
authorized engineering schedule.

## Source compatibility issues

The selected workbook states declare 320 kg and 50/50 front/rear static balance.
The reviewed driver/no-fuel provider instead derives 306.17484975 kg from the
675 lb reference and retains its own CG/scale allocation. The 13.82515025 kg
difference is a source-state discrepancy, not a correction factor. Preserve each
source separately until assembly, driver/fuel, mass, and CG assumptions are reconciled.

The static setting-1/1 fixture has approximately [790.9831, 779.5956, 726.4389,
706.5576] N reactions. Those numbers are inside the scalar R25B load interval,
but remain static verification results. They do not provide cornering inclination,
force demand, pressure, or body motion, and setting 1/1 is verification-only.

The full signed runtime and the exact magnitude handoff remain distinct. The latter
currently supplies only the reviewed 222 N / 0 deg / 82.7 kPa and
1112 N / 2 deg / 82.7 kPa branches. A complete-cell runtime success at another point
does not make that point available to the exact-branch steering consumer. Broader
target inversion requires a separately scoped consumer/provider decision.

## Minimum incoming package for one maneuver

Provide a simulation/measurement export or separately authorized design-intent
schedule with:

1. Configuration and source revision; mass/CG and driver/fuel/assembly setup;
   spring/perch and front/rear ARB settings; tire identity and gauge pressure.
2. A named maneuver and explicit rack grid/sample IDs; canonical axes, origins,
   units, body u/v/r, and acceleration definitions.
3. Four normal loads per sample and their equilibrium/source provenance; front
   signed lateral demands and tire inclination at the same resolution.
4. Front upright transforms with tie-rod steering twist excluded, or sufficient
   reviewed native suspension/body/steering state to generate them through an
   authorized adapter. Record which transforms are body-relative versus road-relative.
5. Explicit source authority/fidelity and intended use. A target weight is a separate
   design-objective decision; an incoming evidence export does not acquire one.

For the current consumer, one pose and constant inside/outside tire operating points
are required across turning samples. An incoming varying maneuver should retain its
true values and trigger a consumer extension decision, not be flattened to fit.

## Stopping point and next increment

No WUFR target can be published from the inspected sources. A predictive integrated
maneuver-QSS producer is still gated by static physical correlation and separate
authorization in `post_rigid_contact_program_v0.1.0.md`.

The independent software increment that can be prepared now is a native zero-steer
pose bridge specification: map the reviewed minimum-twist upright transforms into
the existing pose contract, establish exact frame/origin semantics, and define
nominal/nonzero-travel parity and double-steering rejection checks. This would close
an adapter gap without claiming to supply maneuver loads or body response.

To choose the first real operating-state demonstration, the remaining information
needed is whether a suitable synchronized simulation export exists and which named
vehicle/setup it describes. Without one, define a separately reviewed engineering
schedule proposal before any numerical values are treated as WUFR design inputs.

## Evidence references

- `data_catalog/wufr26_whole_vehicle_frame_v0.toml`
- `data_catalog/wufr27_static_gravity_allocation_v0.toml`
- `data_catalog/wufr27_static_equilibrium_composition_v1.toml`
- `docs/reviews/phase2_wufr_static_equilibrium_implementation_review.md`
- `src/pssd_suspension/wheel_reference.py` (`transport_wheel_reference`)
- `src/pssd_steering/optimization/poses.py` and `external_poses.py`
- `benchmarks/vehicle/WUFR27_SUSPENSION_CALCULATIONS_OPERATING_STATES_V0.toml`
- `data_catalog/r25b_steering_target_input_readiness_v1.toml`
- `docs/reviews/phase4_r25b_steering_target_input_readiness_review.md`
- `docs/models/vehicle/synced_state_producer_implementation_v0.1.0.md`
- `docs/roadmaps/post_rigid_contact_program_v0.1.0.md`

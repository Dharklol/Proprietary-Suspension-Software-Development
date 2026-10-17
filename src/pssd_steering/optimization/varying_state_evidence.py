"""Per-sample native steering replay and all-root signed tire evidence.

Composes MOD-STEER-0001, MOD-VEH-0002/0009 and the reviewed tire kernel.
Outputs remain zero-weight evidence, not optimizer targets or candidate ranking.
"""
from dataclasses import dataclass, replace
import math

from pssd_suspension import build_nominal_wheel_reference
from pssd_tire.steady_state_lateral import (
    SteadyStateLateralFailure, SteadyStateLateralInverseCandidate,
    SteadyStateLateralInverseResult, invert_lateral_force,
)
from pssd_vehicle.force_coordinates import rotation_matrix_yaw_pitch_roll
from pssd_vehicle.operating_states import WheelPosition
from pssd_vehicle.planar_kinematics import (
    WheelPlanarLocation, required_wheel_heading_rad, tire_slip_kinematics,
)
from pssd_vehicle.steady_cornering import (
    RESULT_LABEL, CorneringFailure, CorneringTireQuery, CorneringTireResponse,
)
from pssd_vehicle.steady_cornering_export import (
    NativeCorneringExport, NativeCorneringExportSeries, export_native_cornering,
)
from pssd_vehicle.steady_cornering_tire import (
    R25BDevelopmentCorneringTireProvider, SYMMETRY_ASSUMPTION_ID, SYMMETRY_POLICY,
)
from ..core import PositionResult, cross, dot, rotate_direction_about_axis, rotate_point_about_axis, solve_corner_position
from ..projection import road_intersection_direction
from .geometry import GeneratedSteeringGeometry
from .poses import PosedSteeringGeometry, apply_pose_state


def _require(condition, code, message):
    if not condition:
        raise CorneringFailure(code, message)


def _mv(matrix, vector):
    return tuple(sum(a*b for a, b in zip(row, vector)) for row in matrix)


@dataclass(frozen=True)
class SignedSlipRoot:
    slip_angle_rad: float
    required_heading_rad: float
    source_candidate: SteadyStateLateralInverseCandidate


@dataclass(frozen=True)
class SignedInverseEvidence:
    requested_query: CorneringTireQuery
    requested_lateral_force_n: float
    reflected: bool
    source_inclination_rad: float
    source_force_n: float
    source_result: SteadyStateLateralInverseResult
    roots: tuple[SignedSlipRoot, ...]
    assumption_id: str = SYMMETRY_ASSUMPTION_ID
    policy: str = SYMMETRY_POLICY


def signed_inverse_evidence(query: CorneringTireQuery, *, requested_lateral_force_n: float,
                            velocity_heading_rad: float,
                            tire_provider: R25BDevelopmentCorneringTireProvider) -> SignedInverseEvidence:
    """Map all source roots through the accepted negative-IA reflection.

    Preserve source candidate order and classification, never abs(Fy), choose a
    named root, extrapolate or apply a different symmetry rule at zero IA.
    """
    _require(tire_provider.accepted_assumption_id == SYMMETRY_ASSUMPTION_ID
             and tire_provider.policy == SYMMETRY_POLICY,
             'symmetry_not_authorized', 'Explicit accepted reflection policy required')
    tire_provider(query)  # existing source/proxy/convention/revision/domain gates
    reflected = query.inclination_rad < 0
    source_force = -requested_lateral_force_n if reflected else requested_lateral_force_n
    source_inclination = -query.inclination_rad if reflected else query.inclination_rad
    result = invert_lateral_force(tire_provider.table, normal_load_N=query.normal_load_n,
        inclination_rad=source_inclination, pressure_Pa=query.pressure_pa,
        requested_lateral_force_N=source_force, source_id=query.source_tire_id,
        source_convention_id=query.convention_id, state_id=query.state_id,
        branch_selector=None)
    roots = tuple(SignedSlipRoot(
        -root.slip_angle_rad if reflected else root.slip_angle_rad,
        required_wheel_heading_rad(velocity_heading_rad,
            -root.slip_angle_rad if reflected else root.slip_angle_rad), root)
        for root in result.candidates)
    return SignedInverseEvidence(query, requested_lateral_force_n, reflected,
                                  source_inclination, source_force, result, roots)


@dataclass(frozen=True)
class FrontWheelEvidence:
    corner_id: str
    center_heading_m: tuple[float, float, float]
    wheel_heading_rad: float
    velocity_heading_rad: float
    slip_angle_rad: float
    inclination_rad: float
    forward_response: CorneringTireResponse
    inverse: SignedInverseEvidence
    observed_root_indices: tuple[int, ...]


@dataclass(frozen=True)
class SteeringSampleEvidence:
    sample_id: str
    packet: NativeCorneringExport
    ok: bool
    posed_geometry: PosedSteeringGeometry | None
    closure_results: tuple[PositionResult, ...]
    front_wheels: tuple[FrontWheelEvidence, ...]
    failure_code: str | None = None
    message: str = ''
    result_role: str = 'evidence_only'
    objective_weight: float = 0.

    def __post_init__(self):
        _require(self.result_role == 'evidence_only' and self.objective_weight == 0.,
                 'authority_not_authorized', 'Steering replay remains zero-weight evidence')


@dataclass(frozen=True)
class VaryingStateSteeringEvidence:
    series_id: str
    samples: tuple[SteeringSampleEvidence, ...]
    complete: bool
    authority: str = RESULT_LABEL
    optimizer_target_publication_permitted: bool = False

    def __post_init__(self):
        _require(self.authority == RESULT_LABEL and not self.optimizer_target_publication_permitted,
                 'authority_not_authorized', 'No target publication or ranking authority')
        _require(self.complete == all(s.ok for s in self.samples), 'invalid_contract', 'Completion flag mismatch')


def _source_reference(geometry):
    """Wrap the source baseline for the existing posed evaluator; no search."""
    return GeneratedSteeringGeometry('native_reference_replay', 'unranked_source_reference',
        geometry.geometry_id, geometry, geometry.left.tie_rod_length, geometry.right.tie_rod_length,
        solve_corner_position(geometry, 'left', 0.), solve_corner_position(geometry, 'right', 0.), ())


def consume_native_steering_evidence(series: NativeCorneringExportSeries, *,
                                     geometry_provider, tire_provider, solver_config) -> VaryingStateSteeringEvidence:
    """Revalidate and replay every packet independently, retaining failures.

    No series-wide pose, nominal camber, common tire point, sign/magnitude
    conversion, centered-rack zero-demand override, root selection or scoring.
    The observed equilibrium root is identified only as a reconstruction check.
    """
    NativeCorneringExportSeries(series.series_id, series.packets, series.authority)
    samples = []
    for packet in series.packets:
        posed, closures, wheels = None, [], []
        try:
            fresh = export_native_cornering(packet.equilibrium, geometry_provider=geometry_provider,
                tire_provider=tire_provider, solver_config=solver_config,
                sample_id=packet.sample.vehicle_source.sample_id,
                synchronization_revision=packet.sample.vehicle_source.synchronization_revision)
            _require(fresh == packet, 'source_mismatch', 'Packet differs from current native source export')
            posed = apply_pose_state(_source_reference(geometry_provider.road.steering_geometry), packet.sample.pose)
            body = packet.body_pose
            rotation = rotation_matrix_yaw_pitch_roll(psi_rad=body.psi_rad,
                                                      theta_rad=body.theta_rad, phi_rad=body.phi_rad)
            evaluation = packet.equilibrium.evaluation
            cg = evaluation.inertia.current_total_cg_heading_m
            for slot, (side, transform) in enumerate(zip(('left', 'right'),
                    (packet.sample.pose.left_transform, packet.sample.pose.right_transform))):
                corner_id = 'front_'+side
                corner = getattr(posed.geometry, side)
                closed = solve_corner_position(posed.geometry, side, packet.sample.rack_displacement_m)
                closures.append(closed)
                _require(closed.ok and closed.upright_rotation is not None,
                         str(closed.failure_code), closed.message)
                nominal = build_nominal_wheel_reference(geometry_provider.road.wheel_profile, 'front', side)
                axle_center = rotate_point_about_axis(transform.apply_point(nominal.center_m),
                                                      corner.steering_axis, closed.upright_rotation)
                body_center = tuple(a+b for a, b in zip(axle_center, packet.front_axle_origin_body_m))
                center = tuple(v+body.body_origin_position_m[i]+(body.z_s_m if i == 2 else 0.)
                               for i, v in enumerate(_mv(rotation, body_center)))
                plane = _mv(rotation, rotate_direction_about_axis(transform.apply_direction(nominal.plane_normal),
                                   corner.steering_axis.direction, closed.upright_rotation))
                hint = _mv(rotation, rotate_direction_about_axis(transform.apply_direction(nominal.forward_reference),
                                  corner.steering_axis.direction, closed.upright_rotation))
                forward = road_intersection_direction(plane, forward_hint=hint)
                heading = math.atan2(forward[1], forward[0])
                left = cross((0., 0., 1.), forward)
                polarity = 1 if dot(plane, left)>0 else -1
                inclination = math.atan2(polarity*plane[2], polarity*dot(plane, left))
                original_wheel = evaluation.geometry.wheels[slot]
                _require(math.dist(center, original_wheel.center.point.position_m) <= 1e-10
                         and math.dist(forward, original_wheel.forward_heading) <= 1e-10
                         and abs(inclination-original_wheel.inclination_rad) <= 1e-10,
                         'steering_replay_mismatch', 'Source steering replay differs from native geometry')
                location = WheelPlanarLocation(WheelPosition(corner_id), center[0]-cg[0], center[1]-cg[1])
                slip = tire_slip_kinematics(packet.sample.motion, location, heading)
                original = evaluation.tires[slot]
                query = replace(original.query, slip_angle_rad=slip.slip_angle_rad, inclination_rad=inclination)
                response = tire_provider(query)
                _require(abs(response.lateral_force_n-original.lateral_force_n) <= 1e-6
                         and response.branch_id == original.branch_id,
                         'tire_replay_mismatch', 'Forward replay differs from equilibrium force/branch')
                inverse = signed_inverse_evidence(query, requested_lateral_force_n=original.lateral_force_n,
                    velocity_heading_rad=slip.velocity_heading_rad, tire_provider=tire_provider)
                matches = tuple(i for i, root in enumerate(inverse.roots)
                                if abs(root.slip_angle_rad-slip.slip_angle_rad) <= 1e-9)
                wheels.append(FrontWheelEvidence(corner_id, center, heading, slip.velocity_heading_rad,
                    slip.slip_angle_rad, inclination, response, inverse, matches))
                _require(inverse.source_result.ok, str(inverse.source_result.failure_code), inverse.source_result.message)
                _require(len(matches) == 1, 'observed_root_not_unique', 'Expected one reconstructed observed root among all source roots')
            samples.append(SteeringSampleEvidence(packet.sample.vehicle_source.sample_id, packet, True,
                                                   posed, tuple(closures), tuple(wheels)))
        except (ValueError, ArithmeticError) as error:
            code = str(getattr(error, 'code', getattr(error, 'failure_code', 'provider_failure')))
            samples.append(SteeringSampleEvidence(packet.sample.vehicle_source.sample_id, packet, False,
                posed, tuple(closures), tuple(wheels), code, str(error)))
    return VaryingStateSteeringEvidence(series.series_id, tuple(samples), all(s.ok for s in samples))

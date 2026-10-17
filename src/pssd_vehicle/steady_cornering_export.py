"""Atomic native maneuver evidence with explicit steering/body/heading frames.

AUTH-VEH-0012 development export only. The old fixed-pose/fixed-tire sweep
consumer remains unchanged. A varying-state consumer must use the full packet,
including the body-to-heading mapping and current wheel-center locations.
"""
from dataclasses import asdict, dataclass
import json
import math

from pssd_steering.optimization.native_poses import NativePoseFrameMap, build_native_front_pose

from .force_coordinates import BodyPose
from .operating_states import VehicleOperatingState, VehicleStateRole, WheelOperatingState, WheelPosition
from .planar_kinematics import PlanarMotionSample
from .steady_cornering import (
    CORNERS, RESULT_LABEL, CorneringFailure, CorneringSolveResult,
    CorneringSolverConfig, evaluate_cornering,
)
from .synced_state import CANONICAL_FRAME, StateSourceStamp, SyncedStateSample, compose_synced_state_sample
from .wufr_steady_cornering_geometry import WUFRCorneringGeometryProvider

EXPORT_CONTRACT = 'native_steady_cornering_varying_state_evidence_v1'
STEERING_FRAME_ID = 'WUFR27_NATIVE_FRONT_AXLE_STEERING_REFERENCE'


def _require(condition, message):
    if not condition:
        raise CorneringFailure('unverified_export', message)


@dataclass(frozen=True)
class NativeCorneringExport:
    sample: SyncedStateSample
    equilibrium: CorneringSolveResult
    body_pose: BodyPose
    front_axle_origin_body_m: tuple[float, float, float]
    pose_frame_map: NativePoseFrameMap
    consumer_contract: str = EXPORT_CONTRACT

    def __post_init__(self):
        _require(self.equilibrium.ok and self.equilibrium.evaluation is not None,
                 'A successful equilibrium is required')
        _require(self.equilibrium.result_label == RESULT_LABEL, 'Development result label required')
        _require(self.consumer_contract == EXPORT_CONTRACT, 'Full varying-state frame contract required')
        state = self.sample.vehicle
        _require(state.role is VehicleStateRole.EVIDENCE_ONLY and state.state_weight == 0.,
                 'Exports remain zero-weight evidence')
        _require(state.state_id == self.equilibrium.case.state_id, 'Case/sample state mismatch')
        _require(self.sample.rack_displacement_m == self.equilibrium.coordinates[4], 'Rack mismatch')
        case, evaluation = self.equilibrium.case, self.equilibrium.evaluation
        _require((self.body_pose.z_s_m, self.body_pose.phi_rad, self.body_pose.theta_rad)
                 == self.equilibrium.coordinates[:3] and self.body_pose.psi_rad == 0., 'Body attitude mismatch')
        _require((self.body_pose.inertial_frame_id, self.body_pose.inertial_origin_id)
                 == (case.heading_frame_id, case.origin_id), 'Body/heading frame mismatch')
        _require(self.pose_frame_map.source_revision == case.geometry_revision, 'Pose source revision mismatch')
        _require(state.authority == RESULT_LABEL, 'Vehicle authority cannot be promoted')
        _require((state.ax_g, state.ay_g) == tuple(a/case.gravity_m_s2 for a in evaluation.motion.acceleration_m_s2[:2]),
                 'Acceleration mismatch')
        _require((self.sample.motion.longitudinal_velocity_mps, self.sample.motion.lateral_velocity_mps,
                  self.sample.motion.yaw_rate_radps) == (evaluation.motion.forward_velocity_m_s,
                  evaluation.motion.lateral_velocity_m_s, evaluation.motion.yaw_rate_rad_s), 'Motion mismatch')
        for i, wheel in enumerate(evaluation.geometry.wheels):
            supplied = state.wheel(wheel.corner_id)
            _require((supplied.normal_load_n, supplied.inclination_deg, supplied.pressure_kpa,
                      supplied.lateral_force_demand_n, supplied.longitudinal_force_demand_n)
                     == (self.equilibrium.coordinates[6+i], math.degrees(wheel.inclination_rad),
                         case.pressures_pa[i]/1000., evaluation.tires[i].lateral_force_n, 0.),
                     'Wheel operating state differs from equilibrium')
        for stamp in (self.sample.vehicle_source, self.sample.pose_source, self.sample.motion_source):
            _require(stamp.configuration_id == case.configuration_id, 'Stamp configuration mismatch')
            try:
                bridge = json.loads(stamp.source_path.partition(':')[2])
            except (ValueError, TypeError) as error:
                raise CorneringFailure('unverified_export', 'Missing explicit packet frame bridge') from error
            _require(bridge.get('body_pose') == json.loads(json.dumps(asdict(self.body_pose)))
                     and bridge.get('front_axle_origin_body_m') == list(self.front_axle_origin_body_m)
                     and bridge.get('pose_frame_map') == json.loads(json.dumps(asdict(self.pose_frame_map)))
                     and bridge.get('current_total_cg_heading_m') == list(evaluation.inertia.current_total_cg_heading_m),
                     'Packet frame bridge differs from source stamps')


@dataclass(frozen=True)
class NativeCorneringExportSeries:
    series_id: str
    packets: tuple[NativeCorneringExport, ...]
    authority: str = RESULT_LABEL

    def __post_init__(self):
        _require(bool(self.series_id.strip()) and bool(self.packets), 'Named nonempty series required')
        _require(self.authority == RESULT_LABEL, 'Series authority cannot be promoted')
        ids = [p.sample.vehicle_source.sample_id for p in self.packets]
        _require(len(set(ids)) == len(ids), 'Duplicate sample identity')
        def sources(packet):
            case = packet.equilibrium.case
            return (case.configuration_id, case.geometry_revision, case.setup_revision,
                    case.tire_revision, case.heading_frame_id, case.origin_id,
                    packet.sample.vehicle_source.synchronization_revision)
        _require(all(sources(p) == sources(self.packets[0]) for p in self.packets),
                 'Series cannot mix source/frame/synchronization revisions')


def export_native_cornering(result: CorneringSolveResult, *,
                            geometry_provider: WUFRCorneringGeometryProvider,
                            tire_provider, solver_config: CorneringSolverConfig,
                            sample_id: str, synchronization_revision: str) -> NativeCorneringExport:
    """Revalidate source-bound evidence before composing one synchronized sample.

    Pose excludes steering closure and body attitude. The packet explicitly
    carries body attitude, axle placement, heading datum, current CG and full
    geometry/forces; no component can be frozen at another sample's state.
    """
    _require(result.ok and result.failure_code is None and result.evaluation is not None,
             'Failed or missing equilibrium cannot be exported')
    _require(result.result_label == RESULT_LABEL, 'Development authority required')
    _require(result.reciprocal_pivot_ratio is not None
             and result.reciprocal_pivot_ratio >= solver_config.minimum_reciprocal_pivot_ratio,
             'Verified nonsingular tangent required')
    case, coordinates = result.case, result.coordinates
    _require(all(lo <= x <= hi for x, lo, hi in zip(coordinates, solver_config.lower_bounds,
                                                   solver_config.upper_bounds)), 'Solver domain mismatch')
    fresh = evaluate_cornering(case, coordinates, geometry_provider=geometry_provider,
                              tire_provider=tire_provider)
    _require(fresh == result.evaluation, 'Stored result differs from current source evaluation')
    _require(max(abs(r)/s for r, s in zip(fresh.residual, solver_config.residual_scales))
             <= solver_config.scaled_residual_tolerance, 'Residual acceptance failed')
    _require(math.hypot(*fresh.physical_wrench.resultant_force_N) <= 1e-6
             and math.hypot(*fresh.physical_wrench.resultant_moment_Nm) <= 1e-6,
             'Independent physical closure acceptance failed')
    body_pose = geometry_provider.body_pose(coordinates[:3])
    from .force_coordinates import rotation_matrix_yaw_pitch_roll
    rotation = rotation_matrix_yaw_pitch_roll(psi_rad=0., theta_rad=body_pose.theta_rad,
                                             phi_rad=body_pose.phi_rad)
    states = []
    for corner in CORNERS[:2]:
        angle = geometry_provider._root(corner, coordinates[4], body_pose, rotation)
        wheel = geometry_provider._native(corner, angle)
        slot = CORNERS.index(corner)
        _require(abs(wheel.delta_z_wc_body_m-fresh.geometry.wheel_coordinates_m[slot]) <= 1e-13,
                 'Unresolved pose and equilibrium wheel state differ')
        states.append(wheel.upstream_state)
    frame_map = NativePoseFrameMap(STEERING_FRAME_ID, (0., 0., 0.), case.geometry_revision,
                                  'configurations/steering/WUFR27_STEERING_BASELINE_V0.toml')
    pose = build_native_front_pose(geometry_provider.road.suspension_geometry, *states,
                                  state_id=case.state_id, frame_map=frame_map)
    motion = PlanarMotionSample(fresh.motion.forward_velocity_m_s,
                                fresh.motion.lateral_velocity_m_s, fresh.motion.yaw_rate_rad_s)
    wheels = tuple(WheelOperatingState(
        position=WheelPosition(wheel.corner_id), normal_load_n=coordinates[6+i],
        inclination_deg=math.degrees(wheel.inclination_rad),
        pressure_kpa=case.pressures_pa[i]/1000., lateral_force_demand_n=tire.lateral_force_n,
        longitudinal_force_demand_n=0., provenance=(
            ('tire_query', json.dumps(asdict(tire.query), sort_keys=True)),
            ('tire_branch_id', tire.branch_id), ('tire_revision', case.tire_revision),
            ('longitudinal_force_rule', 'zero_local_Fx_under_pure_lateral_development_model'),
            ('full_tire_source_evidence', 'equilibrium.evaluation.tires'),
        )) for i, (wheel, tire) in enumerate(zip(fresh.geometry.wheels, fresh.tires)))
    vehicle = VehicleOperatingState(
        case.state_id, VehicleStateRole.EVIDENCE_ONLY, motion.turn_direction,
        fresh.motion.acceleration_m_s2[0]/case.gravity_m_s2,
        fresh.motion.acceleration_m_s2[1]/case.gravity_m_s2, case.speed_m_s, wheels,
        state_weight=0., suspension_pose_state_id=pose.state_id, authority=RESULT_LABEL,
        provenance=(('export_contract', EXPORT_CONTRACT), ('configuration_id', case.configuration_id),
            ('geometry_revision', case.geometry_revision), ('setup_revision', case.setup_revision),
            ('tire_revision', case.tire_revision), ('heading_frame_id', case.heading_frame_id),
            ('heading_origin_id', case.origin_id),
            ('current_total_cg_heading_m', json.dumps(fresh.inertia.current_total_cg_heading_m)),
            ('assumptions_and_force_evidence', 'equilibrium.case and equilibrium.evaluation'),
            ('virtual_hold_is_not_a_wheel_Fx', json.dumps(asdict(fresh.holder), sort_keys=True))))
    whole = geometry_provider.road.whole_vehicle
    front_origin = tuple(whole.source_to_body_translation_m[i]
                         + (whole.front_axle_source_position_m[0] if i == 0 else 0.) for i in range(3))
    frame_evidence = json.dumps({
        'contract': EXPORT_CONTRACT, 'heading_frame_id': case.heading_frame_id,
        'heading_origin_id': case.origin_id, 'body_pose': asdict(body_pose),
        'front_axle_origin_body_m': front_origin,
        'pose_frame_map': asdict(frame_map),
        'motion_origin': 'current_total_cg_heading_m',
        'current_total_cg_heading_m': fresh.inertia.current_total_cg_heading_m,
        'wheel_geometry': 'equilibrium.evaluation.geometry.wheels',
        'zero_steer_pose_source': pose.source_path,
    }, sort_keys=True)
    def stamp(component, revision, authority):
        return StateSourceStamp(case.configuration_id, case.state_id, sample_id,
            synchronization_revision, CANONICAL_FRAME, component+':'+frame_evidence,
            revision, authority, RESULT_LABEL)
    sample = compose_synced_state_sample(
        rack_displacement_m=coordinates[4], vehicle=vehicle, pose=pose, motion=motion,
        vehicle_source=stamp('native_coupled_vehicle', case.setup_revision+':'+case.tire_revision, RESULT_LABEL),
        pose_source=stamp('native_unresolved_front_pose', case.geometry_revision, pose.authority),
        motion_source=stamp('native_CG_heading_motion', case.geometry_revision+':'+case.setup_revision, RESULT_LABEL))
    return NativeCorneringExport(sample, result, body_pose, front_origin, frame_map)

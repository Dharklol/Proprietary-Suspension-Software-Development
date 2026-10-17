"""Native WUFR geometry/force composition under AUTH-VEH-0012.

Uses source-owned suspension, steering, spring and ARB providers; no maneuver
inputs are inferred. Native q_L is only an internal root parameter. Returned
wheel coordinates and force/Jacobian conjugacy retain the reviewed native
pre-steering body-vertical wheel-reference displacement.
"""
from dataclasses import asdict
from functools import lru_cache
import hashlib
import json
import math

from pssd_suspension import build_nominal_wheel_reference, solve_body_vertical_displacement
from pssd_suspension.wheel_reference import solve_wheel_reference_state
from pssd_steering.core import cross, dot, norm
from pssd_steering.projection import road_intersection_direction

from .force_coordinates import BodyPose, PointReference, analytical_pose_jacobians, rotation_matrix_yaw_pitch_roll
from .steady_cornering import (
    CORNERS, CorneringCase, CorneringFailure, CorneringGeometry, CorneringMass,
    CorneringWheel, KinematicPoint,
)
from .steady_cornering_upright import close_native_upright
from .wufr_road_contact import ideal_rigid_circle_contact
from .wufr_static_equilibrium_core import WUFRStaticEquilibriumProvider, evaluate_wufr_suspension_composition

HEADING_FRAME_ID = "WUFR27_STEADY_CORNERING_HEADING"
ROAD_ORIGIN_ID = "WUFR27_REFERENCE_CG_XY_SOURCE_ROAD_DATUM"


def _mv(matrix, vector):
    return tuple(sum(matrix[i][j]*vector[j] for j in range(3)) for i in range(3))


def _transpose(matrix):
    return tuple(tuple(matrix[j][i] for j in range(3)) for i in range(3))


def _add(a, b):
    return tuple(x+y for x, y in zip(a, b))


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _fingerprint(*records):
    return hashlib.sha256(json.dumps([asdict(r) for r in records], sort_keys=True,
                                     default=str, allow_nan=False).encode()).hexdigest()


class WUFRCorneringGeometryProvider:
    """Immutable-source composition with cached native corner kinematics.

    No default rack, pressures, ARB settings, gravity or maneuver schedule. The
    component bundle is reused as data/providers; its static solver is not used.
    """

    def __init__(self, components: WUFRStaticEquilibriumProvider):
        self.components = components
        self.road = components.road_contact
        if (self.road.config.road_gap_tolerance_m > 1e-13
                or self.road.config.kinematics_length_residual_tolerance_m > 1e-14
                or self.road.config.physical_q_L_tolerance_rad > 1e-14):
            raise CorneringFailure("numerical_contract", "High-precision native provider settings required for physical closure")
        self.geometry_revision = _fingerprint(self.road.suspension_geometry,
            self.road.wheel_profile, self.road.steering_geometry, self.road.whole_vehicle)
        self.setup_revision = _fingerprint(components.source, components.gravity,
            components.spring_package, components.front_zbar_fixture, components.rear_zbar_fixture,
            self.road.config, components.rocker_derivative)
        if abs(components.gravity.total_mass_kg-306.17484975) > 1e-9:
            raise CorneringFailure("source_mismatch", "Accepted driver/no-fuel mass source required")
        self._nominal = {}
        self._bounds = {}
        for corner in CORNERS:
            axle, side = corner.split('_')
            nominal = build_nominal_wheel_reference(self.road.wheel_profile, axle, side)
            self._nominal[corner] = nominal
            native = self._native(corner, 0.)
            if axle == 'front':
                original = getattr(self.road.steering_geometry, side)
                axis = original.steering_axis
                upstream = native.upstream_state
                # Explicit zero-offset shared-frame proof against both kingpin joints.
                for point in (upstream.lower_upright_m, upstream.upper_upright_m):
                    if norm(cross(_sub(point, axis.point), axis.direction)) > 1e-9:
                        raise CorneringFailure("frame_error", "Native/steering kingpin lines do not share axle frame")
                if dot(axis.direction, upstream.kingpin_direction) < 1-1e-10:
                    raise CorneringFailure("frame_error", "Native/steering axis polarity mismatch")
            limits = []
            for displacement in (self.road.config.wheel_coordinate_min_m, self.road.config.wheel_coordinate_max_m):
                state = solve_body_vertical_displacement(
                    self.road.suspension_geometry.corner(axle, side), nominal, displacement,
                    self.road.config.physical_state_solver,
                    kinematics_config=self.road.config.kinematics_solver,
                    geometry_id=self.road.suspension_geometry.geometry_id,
                    configuration_id=self.components.source.configuration_id,
                    source_authority=self.road.suspension_geometry.authority,
                )
                if not state.ok or state.q_L_rad is None:
                    raise CorneringFailure("suspension_failure", f"Cannot bind reviewed wheel domain: {state.message}")
                limits.append(state.q_L_rad)
            self._bounds[corner] = tuple(sorted(limits))

    @lru_cache(maxsize=8192)
    def _native(self, corner, angle):
        axle, side = corner.split('_')
        result = solve_wheel_reference_state(
            self.road.suspension_geometry.corner(axle, side), self._nominal[corner], angle,
            kinematics_config=self.road.config.kinematics_solver,
            geometry_id=self.road.suspension_geometry.geometry_id,
            configuration_id=self.components.source.configuration_id,
            source_authority=self.road.suspension_geometry.authority,
        )
        if not result.ok:
            raise CorneringFailure("suspension_failure", f"{corner}: {result.failure_code}: {result.message}")
        return result

    @lru_cache(maxsize=8192)
    def _upright(self, corner, angle, rack):
        try:
            return close_native_upright(self._native(corner, angle), self.road.steering_geometry, rack)
        except ValueError as error:
            if isinstance(error, CorneringFailure):
                raise
            raise CorneringFailure("steering_failure", str(error)) from error

    def body_pose(self, q):
        whole = self.road.whole_vehicle
        return BodyPose(HEADING_FRAME_ID, ROAD_ORIGIN_ID, whole.body_frame_id, whole.body_origin_id,
                        (0., 0., whole.cg_source_position_m[2]), *q, authority="AUTH-VEH-0012")

    def _body_point(self, corner, axle_point):
        whole = self.road.whole_vehicle
        axle_origin = (whole.front_axle_source_position_m if corner.startswith('front')
                       else whole.rear_axle_source_position_m)
        return _add(_add(axle_point, (axle_origin[0], 0., 0.)), whole.source_to_body_translation_m)

    def _world(self, corner, point, pose, rotation):
        return _add(_mv(rotation, self._body_point(corner, point)),
                    _add(pose.body_origin_position_m, (0., 0., pose.z_s_m)))

    def _contact(self, corner, angle, rack, pose, rotation):
        upright = self._upright(corner, angle, rack)
        center = self._world(corner, upright.center_m, pose, rotation)
        plane = _mv(rotation, upright.plane_normal)
        return ideal_rigid_circle_contact(center, plane, (0., 0., 1.), self.road.tire_radius_m)

    def _root(self, corner, rack, pose, rotation):
        low, high = self._bounds[corner]
        count = self.road.config.road_scan_intervals
        samples = [(low+(high-low)*i/count) for i in range(count+1)]
        gaps = [self._contact(corner, a, rack, pose, rotation).contact_point_m[2] for a in samples]
        tolerance = self.road.config.road_gap_tolerance_m
        exact = [a for a, g in zip(samples, gaps) if abs(g) <= tolerance]
        brackets = [(samples[i], samples[i+1], gaps[i], gaps[i+1])
                    for i in range(count) if gaps[i]*gaps[i+1] < 0
                    and abs(gaps[i]) > tolerance and abs(gaps[i+1]) > tolerance]
        if len(exact)+len(brackets) != 1:
            raise CorneringFailure("road_root_ambiguous" if len(exact)+len(brackets)>1 else "road_root_unbracketed",
                                  f"{corner}: expected one bounded native contact root")
        if exact:
            return exact[0]
        low, high, gl, gh = brackets[0]
        for _ in range(self.road.config.root_max_iterations):
            middle = .5*(low+high)
            gap = self._contact(corner, middle, rack, pose, rotation).contact_point_m[2]
            if abs(gap) <= tolerance:
                return middle
            if gap*gl > 0:
                low, gl = middle, gap
            else:
                high, gh = middle, gap
        raise CorneringFailure("road_root_nonconvergence", f"{corner}: bounded contact solve exhausted")

    def _point(self, case, corner, point_id, material, angle, rack, pose, rotation, derivative):
        upright = self._upright(corner, angle, rack)
        axle_point = upright.transport_point(material)
        body_point = self._body_point(corner, axle_point)
        world = self._world(corner, axle_point, pose, rotation)
        body_jacobian, _ = analytical_pose_jacobians(body_point, pose)
        slot = CORNERS.index(corner)
        wheel_jacobian = tuple(tuple(derivative[i] if j == slot else 0. for j in range(4)) for i in range(3))
        reference = PointReference(point_id, HEADING_FRAME_ID, ROAD_ORIGIN_ID, world,
            point_id, self.road.suspension_geometry.geometry_id, case.configuration_id,
            'AUTH-VEH-0012', 'instantaneous_upright_material_point',
            (("state_id", case.state_id), ("geometry_revision", self.geometry_revision),
             ("setup_revision", self.setup_revision), ("source_role", upright.steering_owner)))
        return KinematicPoint(reference, body_jacobian, wheel_jacobian, 'material_application_point')

    def _derivatives(self, corner, material_points, angle, rack, rotation):
        # Chain internal q_L derivatives to the actual source-owned z_w.
        # Two central scales must agree; no nominal or frozen derivative fallback.
        estimates = []
        for h in (2e-4, 1e-4):
            if angle-h < self._bounds[corner][0] or angle+h > self._bounds[corner][1]:
                raise CorneringFailure("derivative_domain_failure", "Native contact root lacks two-sided derivative domain")
            plus = self._upright(corner, angle+h, rack)
            minus = self._upright(corner, angle-h, rack)
            dw = (plus.wheel_state.delta_z_wc_body_m-minus.wheel_state.delta_z_wc_body_m)/(2*h)
            if abs(dw) < 1e-3:
                raise CorneringFailure("coordinate_derivative_degenerate", "Native z_w/q_L mapping is singular")
            estimates.append(tuple(_mv(rotation, tuple(
                (a-b)/(2*h*dw) for a, b in zip(plus.transport_point(p), minus.transport_point(p))))
                for p in material_points))
        cfg = self.road.config
        for coarse, fine in zip(*estimates):
            for a, b in zip(coarse, fine):
                if abs(a-b) > cfg.derivative_absolute_tolerance+cfg.derivative_relative_tolerance*max(abs(a), abs(b)):
                    raise CorneringFailure("derivative_not_converged", "Full material-point wheel Jacobian failed h/h2 check")
        return tuple(tuple((4*b-a)/3 for a, b in zip(coarse, fine))
                     for coarse, fine in zip(*estimates))

    @lru_cache(maxsize=512)
    def __call__(self, case: CorneringCase, q, rack):
        if (case.configuration_id != self.components.source.configuration_id
                or case.geometry_revision != self.geometry_revision or case.setup_revision != self.setup_revision
                or case.spring_reference_id != self.components.spring_package.reference.reference_id):
            raise CorneringFailure("source_mismatch", "Current WUFR configuration/revisions/spring reference required")
        if (case.heading_frame_id, case.origin_id) != (HEADING_FRAME_ID, ROAD_ORIGIN_ID):
            raise CorneringFailure("frame_error", "Explicit heading-frame road datum required")
        if len(q) != 3 or not all(math.isfinite(x) for x in (*q, rack)):
            raise CorneringFailure("nonfinite_input", "Finite body coordinates and rack required")
        cfg = self.road.config
        if any(abs(a)>b for a, b in zip(q, (cfg.body_z_limit_m, cfg.body_roll_limit_rad, cfg.body_pitch_limit_rad))):
            raise CorneringFailure("body_pose_outside_domain", "Body pose exceeds reviewed local geometry domain")
        source_rack = self.road.steering_geometry.rack
        if not source_rack.displacement_min <= rack <= source_rack.displacement_max:
            raise CorneringFailure("steering_failure", "Rack displacement exceeds source domain")
        pose = self.body_pose(q)
        rotation = rotation_matrix_yaw_pitch_roll(psi_rad=pose.psi_rad, theta_rad=pose.theta_rad, phi_rad=pose.phi_rad)
        wheels, coordinates, gaps, coefficients, rows = [], [], [], [], []
        for corner in CORNERS:
            angle = self._root(corner, rack, pose, rotation)
            upright = self._upright(corner, angle, rack)
            contact = self._contact(corner, angle, rack, pose, rotation)
            # Geometric lowest point picks today's application location. Freeze
            # its upright material coordinates for virtual-work differentiation.
            world_delta = _sub(contact.contact_point_m, self._world(corner, upright.center_m, pose, rotation))
            axle_contact = _add(upright.center_m, _mv(_transpose(rotation), world_delta))
            material_contact = upright.material_coordinates(axle_contact)
            material_center = self._nominal[corner].center_m
            dc, dp = self._derivatives(corner, (material_center, material_contact), angle, rack, rotation)
            center = self._point(case, corner, corner+':center', material_center, angle, rack, pose, rotation, dc)
            point = self._point(case, corner, corner+':contact', material_contact, angle, rack, pose, rotation, dp)
            c = dp[2]
            if abs(c) < cfg.contact_coefficient_min_abs:
                raise CorneringFailure("contact_coefficient_degenerate", corner)
            plane = _mv(rotation, upright.plane_normal)
            hint = _mv(rotation, upright.transport_direction(self._nominal[corner].forward_reference))
            heading = road_intersection_direction(plane, forward_hint=hint)
            left = cross((0., 0., 1.), heading)
            polarity = 1 if dot(plane, left)>0 else -1
            inclination = math.atan2(polarity*plane[2], polarity*dot(plane, left))
            wheels.append(CorneringWheel(corner, center, point, heading, inclination, upright.steering_owner))
            coordinates.append(upright.wheel_state.delta_z_wc_body_m)
            gaps.append(contact.contact_point_m[2])
            coefficients.append(c)
            rows.append(tuple(-a/c for a in point.J_body[2]))
        suspension = evaluate_wufr_suspension_composition(self.components, tuple(coordinates),
            front_arb_setting=case.front_arb_setting, rear_arb_setting=case.rear_arb_setting)
        if not suspension.ok:
            raise CorneringFailure("suspension_force_failure", f"{suspension.failure_code}: {suspension.message}")
        gravity = self.components.gravity
        sprung_body = gravity.sprung.body_position_m
        sprung_world = _add(_mv(rotation, sprung_body), _add(pose.body_origin_position_m, (0., 0., pose.z_s_m)))
        sprung_reference = PointReference(gravity.sprung.point_id, HEADING_FRAME_ID, ROAD_ORIGIN_ID,
            sprung_world, 'sprung_mass', gravity.record_id, case.configuration_id, 'AUTH-VEH-0012',
            provenance=(("state_id", case.state_id), ("mass_source", gravity.state_id)))
        sprung_jacobian, _ = analytical_pose_jacobians(sprung_body, pose)
        sprung = KinematicPoint(sprung_reference, sprung_jacobian, ((0.,)*4,)*3, 'material_application_point')
        masses = (CorneringMass(gravity.sprung.mass_kg, sprung), *(CorneringMass(m.mass_kg, wheel.center)
            for m, wheel in zip(gravity.unsprung, wheels)))
        sources = ('AUTH-VEH-0012', 'ASM-VEH-0006', 'ASM-VEH-0007', 'ASM-VEH-0008',
            self.road.suspension_geometry.geometry_id, self.road.wheel_profile.fixture_id,
            self.road.steering_geometry.geometry_id, self.road.whole_vehicle.adapter_id,
            gravity.record_id, self.components.spring_package.source_record_id,
            self.components.spring_package.reference.reference_id,
            self.components.front_zbar_fixture.fixture_id, self.components.rear_zbar_fixture.fixture_id)
        return CorneringGeometry(tuple(q), rack, case.state_id, case.configuration_id,
            self.geometry_revision, self.setup_revision, tuple(coordinates), tuple(rows), tuple(coefficients),
            tuple(gaps), suspension.generalized_suspension_force_N, tuple(masses), tuple(wheels), sources,
            'native_reference_connected_unique_contact_roots')

from dataclasses import asdict, replace
import json
from pathlib import Path
import unittest

from pssd_steering import solve_corner_position
from pssd_steering.core import rotate_point_about_axis
from pssd_steering.optimization.geometry import GeneratedSteeringGeometry
from pssd_steering.optimization.poses import STEERING_DOF_RULE, apply_pose_state
from pssd_vehicle.force_coordinates import rotation_matrix_yaw_pitch_roll
from pssd_vehicle.operating_states import VehicleStateRole
from pssd_vehicle.steady_cornering import CorneringFailure, solve_cornering
from pssd_vehicle.steady_cornering_export import (
    NativeCorneringExportSeries, export_native_cornering,
)
from pssd_vehicle.synced_state import SyncedStateSweep
from tests.wufr_cornering_fixture import providers, case, solver_config

ROOT = Path(__file__).resolve().parents[1]


class NativeCorneringExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geometry, cls.tire = providers()
        report = json.loads((ROOT/'benchmarks/vehicle/wufr_steady_cornering_native_development_v0.1.0.json').read_text())
        # Saved coordinates are seeds only. The current source providers and
        # solver recheck residual, tangent rank and physical closure at runtime.
        seeds = [report['branches'][0]['samples'][0], report['branches'][1]['samples'][2],
                 report['branches'][0]['samples'][2]]
        cls.solutions, cls.packets = [], []
        for i, seed in enumerate(seeds):
            current = case(cls.geometry, cls.tire, seed['case']['curvature_per_m'], state_id=f'export_fixture_{i}')
            result = solve_cornering(current, tuple(seed['coordinates']), geometry_provider=cls.geometry,
                                    tire_provider=cls.tire, config=solver_config())
            if not result.ok:
                raise AssertionError(f'{result.failure_code}: {result.message}')
            cls.solutions.append(result)
            cls.packets.append(cls.export(result, f'export_sample_{i}'))

    @classmethod
    def export(cls, result, sample_id='sample'):
        return export_native_cornering(result, geometry_provider=cls.geometry, tire_provider=cls.tire,
            solver_config=solver_config(), sample_id=sample_id, synchronization_revision='export_verification_v1')

    def test_atomic_four_wheel_motion_force_and_authority_records(self):
        for packet in self.packets:
            sample, result = packet.sample, packet.equilibrium
            self.assertTrue(sample.front_inputs_complete)
            self.assertEqual(sample.vehicle.state_id, result.case.state_id)
            self.assertEqual(sample.pose.state_id, result.case.state_id)
            self.assertEqual(sample.vehicle_source.synchronization_key, sample.pose_source.synchronization_key)
            self.assertEqual(sample.vehicle.role, VehicleStateRole.EVIDENCE_ONLY)
            self.assertEqual(sample.vehicle.state_weight, 0.)
            self.assertEqual(sample.pose.steering_dof_rule, STEERING_DOF_RULE)
            for i, (wheel, tire) in enumerate(zip(sample.vehicle.wheels, result.evaluation.tires)):
                self.assertEqual(wheel.normal_load_n, result.coordinates[6+i])
                self.assertEqual(wheel.lateral_force_demand_n, tire.lateral_force_n)
                self.assertAlmostEqual(wheel.pressure_kpa*1000, tire.query.pressure_pa)
                self.assertEqual(wheel.longitudinal_force_demand_n, 0.)
            self.assertEqual(sample.motion.yaw_rate_radps, result.evaluation.motion.yaw_rate_rad_s)
            self.assertEqual(sample.vehicle.ax_g, result.evaluation.motion.acceleration_m_s2[0]/result.case.gravity_m_s2)
            self.assertEqual(sample.vehicle.ay_g, result.evaluation.motion.acceleration_m_s2[1]/result.case.gravity_m_s2)

    def test_unresolved_pose_recloses_once_and_reconstructs_current_heading_centers(self):
        source = self.geometry.road.steering_geometry
        generated = GeneratedSteeringGeometry('export_verification', 'unranked_baseline', source.geometry_id,
            source, source.left.tie_rod_length, source.right.tie_rod_length,
            solve_corner_position(source, 'left', 0.), solve_corner_position(source, 'right', 0.), ())
        for packet in self.packets:
            posed = apply_pose_state(generated, packet.sample.pose)
            body = packet.body_pose
            rotation = rotation_matrix_yaw_pitch_roll(psi_rad=0., phi_rad=body.phi_rad, theta_rad=body.theta_rad)
            for i, (side, transform) in enumerate(zip(('left', 'right'),
                    (packet.sample.pose.left_transform, packet.sample.pose.right_transform))):
                corner = getattr(posed.geometry, side)
                closed = solve_corner_position(posed.geometry, side, packet.sample.rack_displacement_m)
                self.assertTrue(closed.ok, closed.message)
                nominal = self.geometry._nominal['front_'+side]
                current_axle = rotate_point_about_axis(transform.apply_point(nominal.center_m),
                                                        corner.steering_axis, closed.upright_rotation)
                body_point = tuple(a+b for a, b in zip(current_axle, packet.front_axle_origin_body_m))
                heading_point = tuple(sum(rotation[row][j]*body_point[j] for j in range(3))
                    + body.body_origin_position_m[row]+(body.z_s_m if row == 2 else 0.) for row in range(3))
                wanted = packet.equilibrium.evaluation.geometry.wheels[i].center.point.position_m
                for actual, expected in zip(heading_point, wanted):
                    self.assertAlmostEqual(actual, expected, delta=1e-12)

    def test_failed_stale_source_and_tampered_force_evidence_cannot_export(self):
        result = self.solutions[0]
        tampered = replace(result.evaluation.tires[0], lateral_force_n=123456.)
        altered = replace(result.evaluation, tires=(tampered, *result.evaluation.tires[1:]))
        for candidate in (replace(result, ok=False), replace(result, evaluation=None),
                          replace(result, reciprocal_pivot_ratio=None), replace(result, result_label=None),
                          replace(result, evaluation=altered),
                          replace(result, case=replace(result.case, geometry_revision='stale'))):
            with self.assertRaises(CorneringFailure):
                self.export(candidate)
        with self.assertRaises(ValueError):
            self.export(result, '')

    def test_series_preserves_order_and_varying_states_without_legacy_flattening(self):
        series = NativeCorneringExportSeries('verification_series', tuple(self.packets))
        self.assertEqual(series.packets, tuple(self.packets))
        self.assertNotEqual(series.packets[0].sample.pose, series.packets[1].sample.pose)
        self.assertNotEqual(series.packets[0].sample.vehicle.wheels, series.packets[1].sample.vehicle.wheels)
        with self.assertRaises(ValueError):
            NativeCorneringExportSeries('duplicates', (self.packets[0], self.packets[0]))
        with self.assertRaises(ValueError):
            SyncedStateSweep('cannot_flatten', tuple(p.sample.rack_displacement_m for p in self.packets),
                             tuple(p.sample for p in self.packets), 'evidence')

    def test_promotion_rejected_and_full_frame_and_force_evidence_serializes(self):
        packet = self.packets[1]
        promoted = replace(packet.sample.vehicle, role=VehicleStateRole.DESIGN_INPUT, state_weight=1.)
        with self.assertRaises(CorneringFailure):
            replace(packet, sample=replace(packet.sample, vehicle=promoted))
        with self.assertRaises(CorneringFailure):
            replace(packet, body_pose=replace(packet.body_pose, body_origin_position_m=(0., 0., 999.)))
        with self.assertRaises(CorneringFailure):
            replace(packet, front_axle_origin_body_m=(99., 0., 0.))
        with self.assertRaises(CorneringFailure):
            replace(packet, sample=replace(packet.sample, vehicle=replace(packet.sample.vehicle, ay_g=99.)))
        record = json.loads(json.dumps(asdict(packet), allow_nan=False))
        self.assertEqual(record['sample']['vehicle']['role'], 'evidence_only')
        self.assertIn('current_total_cg_heading_m', record['equilibrium']['evaluation']['inertia'])
        self.assertIn('holder', record['equilibrium']['evaluation'])
        self.assertEqual(record['pose_frame_map']['suspension_origin_in_steering_m'], [0., 0., 0.])
        self.assertNotEqual(record['body_pose']['phi_rad'], 0.)
        self.assertEqual(record['sample']['vehicle']['suspension_pose_state_id'], record['sample']['pose']['state_id'])


if __name__ == '__main__':
    unittest.main()

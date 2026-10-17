from dataclasses import replace
import math
import unittest

from pssd_steering.optimization.poses import RigidTransform
from pssd_steering.optimization.varying_state_evidence import (
    consume_native_steering_evidence, signed_inverse_evidence,
)
from pssd_vehicle.planar_kinematics import WheelPlanarLocation, wheel_center_kinematics
from pssd_vehicle.operating_states import WheelPosition
from pssd_vehicle.steady_cornering import CorneringFailure
from pssd_tire.steady_state_lateral import SteadyStateLateralFailure
from pssd_vehicle.steady_cornering_export import NativeCorneringExportSeries
from tests.varying_state_evidence_fixture import bundle, series
from tests.wufr_cornering_fixture import solver_config


class VaryingStateSteeringEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geometry, cls.tire, _ = bundle()
        cls.series = series()
        cls.result = cls.consume(cls.series)

    @classmethod
    def consume(cls, values, tire=None):
        return consume_native_steering_evidence(values, geometry_provider=cls.geometry,
            tire_provider=tire or cls.tire, solver_config=solver_config())

    def test_each_pose_center_motion_and_tire_point_is_preserved(self):
        self.assertTrue(self.result.complete)
        self.assertEqual([s.sample_id for s in self.result.samples],
                         [p.sample.vehicle_source.sample_id for p in self.series.packets])
        for result in self.result.samples:
            self.assertTrue(result.ok, result.message)
            evaluation = result.packet.equilibrium.evaluation
            for i, wheel in enumerate(result.front_wheels):
                original = evaluation.geometry.wheels[i]
                self.assertAlmostEqual(math.dist(wheel.center_heading_m, original.center.point.position_m), 0., delta=1e-12)
                self.assertAlmostEqual(wheel.inclination_rad, original.inclination_rad, places=12)
                self.assertAlmostEqual(wheel.forward_response.lateral_force_n, evaluation.tires[i].lateral_force_n, delta=1e-6)
                cg = evaluation.inertia.current_total_cg_heading_m
                location = WheelPlanarLocation(WheelPosition(wheel.corner_id),
                    wheel.center_heading_m[0]-cg[0], wheel.center_heading_m[1]-cg[1])
                velocity = wheel_center_kinematics(result.packet.sample.motion, location)
                self.assertEqual(wheel.velocity_heading_rad, velocity.velocity_heading_rad)
                self.assertEqual(len(wheel.observed_root_indices), 1)
                self.assertFalse(wheel.inverse.source_result.branch_selection_applied)
                root = wheel.inverse.roots[wheel.observed_root_indices[0]]
                self.assertAlmostEqual(root.required_heading_rad, wheel.wheel_heading_rad, delta=1e-9)
        self.assertNotEqual(self.result.samples[0].front_wheels[0].center_heading_m,
                            self.result.samples[1].front_wheels[0].center_heading_m)
        self.assertNotEqual(self.result.samples[0].front_wheels[0].inclination_rad,
                            self.result.samples[1].front_wheels[0].inclination_rad)

    def test_zero_curvature_keeps_nonzero_signed_alignment_forces(self):
        straight = self.result.samples[0]
        self.assertEqual(straight.packet.equilibrium.case.curvature_per_m, 0.)
        self.assertTrue(all(abs(w.forward_response.lateral_force_n)>1 for w in straight.front_wheels))
        self.assertLess(straight.front_wheels[0].forward_response.lateral_force_n
                        * straight.front_wheels[1].forward_response.lateral_force_n, 0.)

    def test_reflected_source_keeps_every_real_tire_root_and_signed_force(self):
        base = self.series.packets[0].equilibrium.evaluation.tires[1].query
        query = replace(base, slip_angle_rad=math.radians(12), normal_load_n=222.,
                        inclination_rad=-math.radians(2), pressure_pa=82700.)
        force = self.tire(query).lateral_force_n
        result = signed_inverse_evidence(query, requested_lateral_force_n=force,
                                         velocity_heading_rad=.02, tire_provider=self.tire)
        self.assertGreaterEqual(len(result.roots), 2)
        self.assertEqual(result.source_force_n, -force)
        self.assertEqual(result.source_inclination_rad, -query.inclination_rad)
        self.assertFalse(result.source_result.branch_selection_applied)
        for root, source in zip(result.roots, result.source_result.candidates):
            self.assertEqual(root.slip_angle_rad, -source.slip_angle_rad)
            self.assertEqual(root.source_candidate, source)
            forward = self.tire(replace(query, slip_angle_rad=root.slip_angle_rad))
            self.assertAlmostEqual(forward.lateral_force_n, force, delta=1e-6)

    def test_bad_state_is_retained_without_hiding_other_samples(self):
        blocked = self.series.packets[1].equilibrium.case.state_id
        original = self.tire
        class BrokenProvider:
            def __getattr__(self, name):
                return getattr(original, name)
            def __call__(self, query):
                if query.state_id == blocked:
                    raise CorneringFailure('source_fixture_unavailable', 'Deliberate provider gate')
                return original(query)
        result = self.consume(self.series, BrokenProvider())
        self.assertFalse(result.complete)
        self.assertEqual([s.ok for s in result.samples], [True, False, True])
        self.assertEqual(result.samples[1].failure_code, 'source_fixture_unavailable')
        self.assertEqual(result.samples[1].packet, self.series.packets[1])

    def test_frozen_pose_and_source_revision_substitution_fail(self):
        first, current, last = self.series.packets
        wrong_pose = replace(current.sample.pose, left_transform=RigidTransform.identity())
        wrong = replace(current, sample=replace(current.sample, pose=wrong_pose))
        values = NativeCorneringExportSeries('bad_pose', (first, wrong, last))
        result = self.consume(values)
        self.assertEqual(result.samples[1].failure_code, 'source_mismatch')
        self.assertEqual([s.ok for s in result.samples], [True, False, True])

    def test_missing_domains_and_authority_are_not_repaired(self):
        query = self.series.packets[0].equilibrium.evaluation.tires[1].query
        with self.assertRaises(ValueError):
            signed_inverse_evidence(replace(query, inclination_rad=-math.radians(5)),
                requested_lateral_force_n=0., velocity_heading_rad=0., tire_provider=self.tire)
        with self.assertRaises(SteadyStateLateralFailure) as missing:
            signed_inverse_evidence(query, requested_lateral_force_n=1e9,
                                    velocity_heading_rad=0., tire_provider=self.tire)
        self.assertEqual(missing.exception.failure_code, 'force_demand_out_of_domain')
        with self.assertRaises(CorneringFailure):
            replace(self.result, optimizer_target_publication_permitted=True)
        with self.assertRaises(CorneringFailure):
            replace(self.result.samples[0], objective_weight=1.)


if __name__ == '__main__':
    unittest.main()

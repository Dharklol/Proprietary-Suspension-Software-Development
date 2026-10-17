from dataclasses import replace
import math
import unittest

from pssd_vehicle.steady_cornering import CORNERS, CorneringFailure, point_generalized_force, evaluate_cornering
from pssd_vehicle.force_coordinates import rotation_matrix_yaw_pitch_roll
from pssd_vehicle.wufr_static_equilibrium_core import evaluate_wufr_suspension_composition
from pssd_vehicle.wufr_steady_cornering_geometry import WUFRCorneringGeometryProvider, _fingerprint
from tests.wufr_cornering_fixture import providers, case, initial


class NativeCorneringGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.geometry, cls.tire = providers()
        cls.case = case(cls.geometry, cls.tire)

    def test_current_sources_mass_contacts_and_suspension_composition(self):
        result = self.geometry(self.case, (.001,.003,-.002), .003)
        self.assertEqual(sum(m.mass_kg for m in result.masses), 306.17484975)
        self.assertEqual(len(result.masses), 5)
        self.assertLess(max(abs(g) for g in result.contact_gaps_m), 1e-12)
        expected = evaluate_wufr_suspension_composition(self.geometry.components,
            result.wheel_coordinates_m, front_arb_setting=1, rear_arb_setting=1)
        self.assertTrue(expected.ok, expected.message)
        self.assertEqual(result.suspension_force_n, expected.generalized_suspension_force_N)
        for slot, wheel in enumerate(result.wheels):
            self.assertEqual(wheel.contact.point.frame_id, self.case.heading_frame_id)
            self.assertEqual(wheel.center.point.origin_id, self.case.origin_id)
            self.assertEqual(result.masses[slot+1].point, wheel.center)
            self.assertAlmostEqual(wheel.forward_heading[2], 0., places=12)
            self.assertEqual(wheel.contact.J_wheel[2][slot], result.contact_coefficients[slot])
            for j in range(3):
                self.assertAlmostEqual(wheel.contact.J_body[2][j]
                    + result.contact_coefficients[slot]*result.J_wb[slot][j], 0., places=12)

    def test_contact_reduction_matches_independent_body_perturbations(self):
        q, rack = (.001,.003,-.002), .003
        base = self.geometry(self.case, q, rack)
        h = 1e-5
        for coordinate in range(3):
            plus, minus = list(q), list(q)
            plus[coordinate] += h
            minus[coordinate] -= h
            high = self.geometry(self.case, tuple(plus), rack)
            low = self.geometry(self.case, tuple(minus), rack)
            for slot in range(4):
                derivative = (high.wheel_coordinates_m[slot]-low.wheel_coordinates_m[slot])/(2*h)
                self.assertAlmostEqual(derivative, base.J_wb[slot][coordinate], delta=2e-6)

    def test_instantaneous_material_contact_virtual_work_at_two_scales(self):
        q, rack = (.001,.003,-.002), .003
        base = self.geometry(self.case, q, rack)
        slot, force, direction = 0, (17., -31., 5.), (.2, -.3, .1)
        point = base.wheels[slot].contact
        direct, wheel = point_generalized_force(point, force)
        reduced = tuple(direct[j]+sum(base.J_wb[i][j]*wheel[i] for i in range(4)) for j in range(3))
        expected = sum(a*b for a, b in zip(reduced, direction))
        pose = self.geometry.body_pose(q)
        rotation = rotation_matrix_yaw_pitch_roll(psi_rad=0., phi_rad=q[1], theta_rad=q[2])
        corner = CORNERS[slot]
        angle = self.geometry._root(corner, rack, pose, rotation)
        upright = self.geometry._upright(corner, angle, rack)
        center = self.geometry._world(corner, upright.center_m, pose, rotation)
        delta = tuple(point.point.position_m[i]-center[i] for i in range(3))
        axle_point = tuple(upright.center_m[i]+sum(rotation[j][i]*delta[j] for j in range(3)) for i in range(3))
        frozen = upright.material_coordinates(axle_point)
        for step in (1e-5, 5e-6):
            positions = []
            for sign in (1, -1):
                moved_q = tuple(a+sign*step*b for a, b in zip(q, direction))
                moved_pose = self.geometry.body_pose(moved_q)
                moved_rotation = rotation_matrix_yaw_pitch_roll(psi_rad=0., phi_rad=moved_q[1], theta_rad=moved_q[2])
                moved_angle = self.geometry._root(corner, rack, moved_pose, moved_rotation)
                moved_upright = self.geometry._upright(corner, moved_angle, rack)
                positions.append(self.geometry._world(corner, moved_upright.transport_point(frozen), moved_pose, moved_rotation))
            actual = sum(force[i]*(positions[0][i]-positions[1][i])/(2*step) for i in range(3))
            self.assertAlmostEqual(actual, expected, delta=2e-6)

    def test_rack_contact_and_current_inclination_are_not_frozen(self):
        a = self.geometry(self.case, (0.,0.,0.), 0.)
        b = self.geometry(self.case, (0.,0.,0.), .003)
        self.assertNotEqual(a.wheel_coordinates_m[:2], b.wheel_coordinates_m[:2])
        self.assertNotEqual(a.wheels[0].inclination_rad, b.wheels[0].inclination_rad)
        self.assertEqual(a.wheels[2:], b.wheels[2:])
        self.assertGreater(a.wheels[0].inclination_rad, 0.)
        self.assertLess(a.wheels[1].inclination_rad, 0.)
        evaluation = evaluate_cornering(self.case, initial(), geometry_provider=self.geometry, tire_provider=self.tire)
        self.assertEqual(tuple(t.query.inclination_rad for t in evaluation.tires),
                         tuple(w.inclination_rad for w in evaluation.geometry.wheels))
        self.assertIn('reflected_negative_IA', evaluation.tires[1].branch_id)
        self.assertTrue(any('ASM-VEH-0009' == s for s in evaluation.tires[1].source_ids))

    def test_source_frame_setup_and_domain_failures(self):
        for changes in ({'geometry_revision':'wrong'}, {'setup_revision':'wrong'},
                        {'spring_reference_id':'wrong'}, {'origin_id':'wrong'}):
            with self.assertRaises(CorneringFailure):
                self.geometry(replace(self.case, **changes), (0.,0.,0.), 0.)
        for q, rack in (((.011,0.,0.),0.), ((0.,0.,0.),1.), ((0.,float('nan'),0.),0.)):
            with self.assertRaises(CorneringFailure):
                self.geometry(self.case, q, rack)

    def test_revision_ignores_checkout_location_and_binds_numeric_geometry(self):
        source = self.geometry.road.steering_geometry
        relocated = replace(source, metadata={**source.metadata,
            'source_path':'/another/checkout/configurations/steering/WUFR27_STEERING_BASELINE_V0.toml',
            'inherited_source_path':'/another/checkout/configurations/steering/WUFR26_DESIGN_NOMINAL_V0.toml'})
        road = replace(self.geometry.road, steering_geometry=relocated)
        alternate = WUFRCorneringGeometryProvider(replace(self.geometry.components, road_contact=road))
        self.assertEqual(alternate.geometry_revision, self.geometry.geometry_revision)
        self.assertEqual(alternate.setup_revision, self.geometry.setup_revision)
        changed = replace(source, wheelbase=source.wheelbase+.001)
        self.assertNotEqual(_fingerprint(changed), _fingerprint(source))


if __name__ == '__main__':
    unittest.main()

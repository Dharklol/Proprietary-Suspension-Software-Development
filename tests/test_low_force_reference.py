import unittest

from scripts.run_low_force_reference_benchmarks import build_report
from tests.low_force_reference_fixture import analytic_geometry, reference_inputs, single_track_reference
from tests.steady_cornering_fixture import case, center_position, mv, rotation


class LowForceReferenceTests(unittest.TestCase):
    def test_analytic_material_point_derivatives_against_two_step_perturbations(self):
        q, rack = (.18,.03,-.02), .006
        g = analytic_geometry(case(.01),q,rack)
        transpose = tuple(tuple(rotation(q)[j][i] for j in range(3)) for i in range(3))
        for index,wheel in enumerate(g.wheels):
            center = center_position(q,g.wheel_coordinates_m,index)
            local_radial = mv(transpose,tuple(a-b for a,b in zip(wheel.contact.point.position_m,center)))
            for point,radial in ((wheel.center,(0.,0.,0.)),(wheel.contact,local_radial)):
                def position(qb):
                    return tuple(a+b for a,b in zip(center_position(qb,g.wheel_coordinates_m,index),
                                                    mv(rotation(qb),radial)))
                for h in (1e-4,5e-5):
                    for column in range(3):
                        low=position(tuple(v-h if j==column else v for j,v in enumerate(q)))
                        high=position(tuple(v+h if j==column else v for j,v in enumerate(q)))
                        for row in range(3):
                            self.assertAlmostEqual((high[row]-low[row])/(2*h),
                                                   point.J_body[row][column],delta=5e-9)

    def test_hand_calculated_axle_reference_and_speed_squared_response(self):
        equal = single_track_reference(**reference_inputs(8.,3200.,3200.))
        self.assertAlmostEqual(equal['steer_per_curvature_m'],1.5)
        self.assertAlmostEqual(equal['front_force_per_curvature_nm'],3840.)
        self.assertAlmostEqual(equal['rear_force_per_curvature_nm'],3840.)
        self.assertAlmostEqual(equal['sideslip_per_curvature_m'],-.45)
        front = single_track_reference(**reference_inputs(8.,2400.,3600.))
        rear = single_track_reference(**reference_inputs(8.,3600.,2400.))
        self.assertAlmostEqual(front['steer_per_curvature_m'],2.033333333333333)
        self.assertAlmostEqual(rear['steer_per_curvature_m'],.9666666666666666)
        slower = single_track_reference(**reference_inputs(4.,2400.,3600.))
        self.assertAlmostEqual(front['steer_per_curvature_m']-1.5,
                               4*(slower['steer_per_curvature_m']-1.5))
        with self.assertRaises(ValueError):
            single_track_reference(**reference_inputs(8.,0.,3200.))

    def test_coupled_solver_matches_all_independent_small_angle_limits(self):
        report = build_report()
        self.assertEqual(report['status'],'pass',
            [(r['fixture'],r['inputs']['speed_m_s'],r['passed']) for r in report['fixtures']])
        self.assertEqual(report['case_count'],42)
        self.assertEqual(report['fixture_count'],6)
        for record in report['fixtures']:
            self.assertTrue(record['convergence_passed'])
            self.assertTrue(record['straight']['ok'])
            self.assertTrue(record['straight_passed'])
            self.assertEqual(len(record['steps']),3)
            for step in record['steps']:
                self.assertEqual(len(step['samples']),2)
                self.assertTrue(all(sample['ok'] for sample in step['samples']))
        self.assertFalse(report['native_tire_or_vehicle_validation'])
        self.assertFalse(report['design_ranking_permitted'])


if __name__ == '__main__':
    unittest.main()

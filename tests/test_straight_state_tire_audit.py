from dataclasses import replace
import unittest

from scripts.run_straight_state_tire_audit import (
    audit_query, build_report, finite_difference_decomposition,
)
from tests.varying_state_evidence_fixture import bundle, packet


class StraightStateTireAuditTests(unittest.TestCase):
    def test_nonadditive_surface_keeps_bias_and_interaction(self):
        # Independently manufactured F(a,g)=7+3a+5g+2ag at a=2,g=4.
        parts = finite_difference_decomposition(7., 13., 27., 49.)
        self.assertEqual(parts, {'source_bias_n': 7.,
            'slip_increment_at_zero_IA_n': 6.,
            'inclination_increment_at_zero_slip_n': 20., 'interaction_n': 16.})
        self.assertEqual(sum(parts.values()), 49.)

    def test_reflected_decomposition_keeps_one_sided_limit_separate(self):
        _, tire, _ = bundle()
        query = packet(0, 0).equilibrium.evaluation.tires[1].query
        self.assertLess(query.inclination_rad, 0.)
        audit = audit_query(query, tire)
        self.assertTrue(audit['reflected'])
        self.assertEqual(audit['zero_IA_probe_rule'], 'reflected_side_limit')
        self.assertAlmostEqual(audit['original_side_zero_IA_limit_force_n'],
            -tire(replace(query, slip_angle_rad=-query.slip_angle_rad,
                          inclination_rad=0.)).lateral_force_n, places=10)
        self.assertGreater(abs(audit['zero_IA_boundary_jump_at_fixed_slip_n']), 1.)
        self.assertLess(audit['decomposition_reconstruction_error_n'], 1e-9)
        for probe in audit['source_probes'].values():
            self.assertEqual(probe['source_state']['normal_load_N'], query.normal_load_n)
            self.assertEqual(probe['source_state']['pressure_Pa'], query.pressure_pa)
        self.assertFalse(audit['design_ranking_permitted'])

    def test_all_four_wheels_explain_straight_state_and_holder(self):
        report = build_report()
        self.assertEqual(report['status'], 'pass')
        self.assertEqual(len(report['wheels']), 4)
        self.assertTrue(all(abs(x) < 1e-6 for x in report['independent_horizontal_balance_n']))
        self.assertLess(abs(report['independent_vertical_balance_n']), 1e-6)
        self.assertGreater(report['holder']['power_w'], 0.)
        for w in report['wheels']:
            self.assertLess(w['decomposition_reconstruction_error_n'], 1e-9)
            self.assertEqual(w['probe_role'], 'conditional_table_queries_not_vehicle_equilibria')
            if not w['reflected']:
                self.assertEqual(w['zero_IA_boundary_jump_at_fixed_slip_n'], 0.)


if __name__ == '__main__':
    unittest.main()

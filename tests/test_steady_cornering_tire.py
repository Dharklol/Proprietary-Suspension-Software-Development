from dataclasses import replace
import math
import unittest

from pssd_tire.r25b_runtime import R25B_CANONICAL_SOURCE_CONVENTION_ID, load_r25b_steady_state_lateral_table
from pssd_tire.r25b_source_native import EXPECTED_SOURCE_TIRE_ID
from pssd_tire.steady_state_lateral import SteadyStateLateralOperatingState, SteadyStateLateralFailure, evaluate_table
from pssd_vehicle.steady_cornering_tire import (
    SYMMETRY_ASSUMPTION_ID, SYMMETRY_POLICY, evaluate_development_r25b,
    R25BDevelopmentCorneringTireProvider,
)
from pssd_vehicle.steady_cornering import CorneringTireQuery, CorneringFailure
from pssd_tire.r25b_source_native import EXPECTED_INTENDED_TIRE_ID


class DevelopmentTireSymmetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.table = load_r25b_steady_state_lateral_table()

    def query(self, **changes):
        return replace(SteadyStateLateralOperatingState(
            .04, 700., math.radians(-1), 75000., 'reflection_fixture',
            EXPECTED_SOURCE_TIRE_ID, R25B_CANONICAL_SOURCE_CONVENTION_ID), **changes)

    def evaluate(self, query, **kwargs):
        return evaluate_development_r25b(query, table=self.table,
            accepted_assumption_id=SYMMETRY_ASSUMPTION_ID, policy=SYMMETRY_POLICY, **kwargs)

    def test_reflects_all_three_signed_values_and_retains_lookup_provenance(self):
        query = self.query()
        actual = self.evaluate(query)
        lookup = replace(query, slip_angle_rad=-query.slip_angle_rad,
                         inclination_rad=-query.inclination_rad)
        expected = evaluate_table(self.table, lookup)
        self.assertTrue(actual.reflected)
        self.assertEqual(actual.requested_state, query)
        self.assertEqual(actual.source_response, expected)
        self.assertEqual(actual.lateral_force_N, -expected.lateral_force_N)
        self.assertEqual(actual.left_segment_slope_N_per_rad, expected.right_segment_slope_N_per_rad)
        self.assertEqual(actual.right_segment_slope_N_per_rad, expected.left_segment_slope_N_per_rad)
        # Merely making IA positive evaluates the opposite source-slip location.
        wrong = evaluate_table(self.table, replace(query, inclination_rad=-query.inclination_rad))
        self.assertGreater(abs(actual.lateral_force_N - wrong.lateral_force_N), 1.)

    def test_nonnegative_queries_preserve_source_exactly(self):
        for curve in self.table.curves:
            query = self.query(normal_load_N=curve.normal_load_N,
                inclination_rad=curve.inclination_rad, pressure_Pa=curve.pressure_Pa,
                slip_angle_rad=curve.slip_angle_rad[len(curve.slip_angle_rad)//2])
            result = self.evaluate(query)
            self.assertFalse(result.reflected)
            self.assertEqual(result.source_response, evaluate_table(self.table, query))
            self.assertEqual(result.lateral_force_N, result.source_response.lateral_force_N)

    def test_authorization_identity_and_transformed_domains_fail_closed(self):
        with self.assertRaises(SteadyStateLateralFailure) as failure:
            evaluate_development_r25b(self.query(), accepted_assumption_id='', policy=SYMMETRY_POLICY)
        self.assertEqual(failure.exception.failure_code, 'symmetry_not_authorized')
        for changes in ({'source_id': 'wrong'}, {'source_convention_id': 'wrong'},
                        {'inclination_rad': math.radians(-5)}, {'pressure_Pa': 50000.},
                        {'normal_load_N': 100.}, {'slip_angle_rad': 1.}):
            with self.assertRaises(SteadyStateLateralFailure):
                self.evaluate(self.query(**changes))

    def test_reflected_slip_derivative_and_zero_IA_bias_are_not_smoothed(self):
        query = self.query()
        step = 1e-7
        derivative = (self.evaluate(replace(query, slip_angle_rad=query.slip_angle_rad+step)).lateral_force_N
            - self.evaluate(replace(query, slip_angle_rad=query.slip_angle_rad-step)).lateral_force_N)/(2*step)
        self.assertAlmostEqual(derivative, self.evaluate(query).left_segment_slope_N_per_rad, places=4)
        zero = self.query(slip_angle_rad=0., inclination_rad=0.)
        direct = self.evaluate(zero)
        negative_limit = self.evaluate(replace(zero, inclination_rad=-1e-12))
        self.assertEqual(direct.lateral_force_N, evaluate_table(self.table, zero).lateral_force_N)
        self.assertAlmostEqual(negative_limit.lateral_force_N, -direct.lateral_force_N, places=7)
        self.assertGreater(abs(direct.lateral_force_N), 1e-3)

    def test_reflected_exact_knot_reverses_left_right_derivative_roles(self):
        curve = next(c for c in self.table.curves if c.inclination_rad > 0)
        source_slip = curve.slip_angle_rad[len(curve.slip_angle_rad)//2]
        query = self.query(normal_load_N=curve.normal_load_N, inclination_rad=-curve.inclination_rad,
                           pressure_Pa=curve.pressure_Pa, slip_angle_rad=-source_slip)
        result = self.evaluate(query)
        self.assertTrue(result.source_response.exact_knot)
        self.assertEqual(result.left_segment_slope_N_per_rad, result.source_response.right_segment_slope_N_per_rad)
        self.assertEqual(result.right_segment_slope_N_per_rad, result.source_response.left_segment_slope_N_per_rad)

    def test_kernel_bridge_retains_requested_query_and_guards_IA_boundary(self):
        provider = R25BDevelopmentCorneringTireProvider(
            accepted_assumption_id=SYMMETRY_ASSUMPTION_ID, policy=SYMMETRY_POLICY)
        source = self.query()
        query = CorneringTireQuery(source.state_id, 'front_right', EXPECTED_SOURCE_TIRE_ID,
            EXPECTED_INTENDED_TIRE_ID, provider.tire_revision, source.source_convention_id,
            source.slip_angle_rad, source.normal_load_N, source.inclination_rad, source.pressure_Pa)
        result = provider(query)
        self.assertEqual(result.query, query)
        self.assertEqual(result.lateral_force_n, self.evaluate(source).lateral_force_N)
        self.assertTrue(any(s.startswith('source_response:') for s in result.source_ids))
        self.assertTrue(any(s.startswith('source_segment_labels:') for s in result.source_ids))
        direct = provider(replace(query, inclination_rad=0.))
        self.assertNotEqual(result.branch_id, direct.branch_id)
        central_a = provider(replace(query, slip_angle_rad=-1e-4))
        central_b = provider(replace(query, slip_angle_rad=1e-4))
        self.assertEqual(central_a.branch_id, central_b.branch_id)
        post = provider(replace(query, slip_angle_rad=.2))
        self.assertNotEqual(result.branch_id, post.branch_id)
        for changes in ({'tire_revision':'wrong'}, {'intended_tire_id':'wrong'}, {'source_tire_id':'wrong'}):
            with self.assertRaises(CorneringFailure):
                provider(replace(query, **changes))


if __name__ == '__main__':
    unittest.main()

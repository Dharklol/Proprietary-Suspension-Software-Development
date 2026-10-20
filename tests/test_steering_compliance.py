"""Regression and contract tests for optional WUFR-27 compliance calculations."""
import math
import unittest

from pssd_steering.compliance import (
    CircularSpan, ClevisPinScreen, ComplianceDefinitionError, DoubleDProfile,
    ToleranceEnvelope, evaluate_circular_spans, wufr27_provisional_circular_spans,
)


class SteeringComplianceTests(unittest.TestCase):
    def test_baseline_four_free_spans(self):
        result = evaluate_circular_spans(wufr27_provisional_circular_spans(), 35.54700928)
        self.assertAlmostEqual(result.twist_deg, 1.571068, places=4)
        self.assertGreater(result.stiffness_nm_per_deg, 22)
        self.assertLess(result.stiffness_nm_per_deg, 23)

    def test_unfactored_torque_scales_linearly(self):
        spans = wufr27_provisional_circular_spans()
        high = evaluate_circular_spans(spans, 35.54700928)
        low = evaluate_circular_spans(spans, 23.69800619)
        self.assertAlmostEqual(low.twist_rad / high.twist_rad, 2 / 3, places=6)

    def test_zero_and_reversed_torque(self):
        spans = wufr27_provisional_circular_spans()
        z = evaluate_circular_spans(spans, 0)
        a = evaluate_circular_spans(spans, 12)
        b = evaluate_circular_spans(spans, -12)
        self.assertEqual(z.twist_deg, 0)
        self.assertTrue(math.isinf(z.stiffness_nm_per_deg))
        self.assertAlmostEqual(a.twist_deg, -b.twist_deg)

    def test_torque_multiplier_explicit(self):
        s = CircularSpan("x", 2, .59, torque_multiplier=2)
        a = CircularSpan("y", 2, .59)
        self.assertAlmostEqual(s.input_referenced_twist_rad(10),
                               2 * a.input_referenced_twist_rad(10))

    def test_geometry_and_tolerance(self):
        profile = DoubleDProfile()
        self.assertAlmostEqual(profile.flat_depth_in, .059)
        self.assertAlmostEqual(profile.flat_chord_in, .354, places=3)
        self.assertEqual(ToleranceEnvelope(.472, .005, .005).clearance_range_in,
                         (-.01, .01))

    def test_pin_double_shear_screen(self):
        self.assertAlmostEqual(ClevisPinScreen().allowable_shear_force_n(), 585.4, delta=1)

    def test_reject_invalid(self):
        with self.assertRaises(ComplianceDefinitionError):
            CircularSpan("bad", 1, .5, .5)
        with self.assertRaises(ComplianceDefinitionError):
            DoubleDProfile(radius_in=.1, across_flats_in=.3)
        with self.assertRaises(ComplianceDefinitionError):
            ToleranceEnvelope(.472, -.001, 0)
        with self.assertRaises(ComplianceDefinitionError):
            evaluate_circular_spans((), 5)
        with self.assertRaises(ComplianceDefinitionError):
            evaluate_circular_spans((CircularSpan("a", 1, .5),
                                     CircularSpan("a", 2, .5)), 5)


if __name__ == "__main__":
    unittest.main()

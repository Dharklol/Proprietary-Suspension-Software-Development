"""Opt-in rigid vs prescribed elastic steering comparison regression checks."""
from __future__ import annotations

import math
from pathlib import Path
import unittest
from unittest.mock import patch

from pssd_steering import load_geometry
from pssd_steering.compliance import (
    ComplianceDefinitionError, wufr27_provisional_circular_spans,
)
from pssd_steering.compliance_bridge import (
    PrescribedTorqueInput, SteeringTransmission, evaluate_prescribed_torque_sweep,
)
from pssd_steering.core import FailureCode, solve_sweep

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = ROOT / "benchmarks" / "steering" / "GEO-STEER-BASIC-001.toml"
WUFR = ROOT / "configurations" / "steering" / "WUFR27_STEERING_BASELINE_V0.toml"
SPANS = wufr27_provisional_circular_spans()
# Synthetic transmission, not an as-built rack conversion.
SYNTHETIC_MAP = SteeringTransmission(1.0, 0.010, "BENCH-STEER synthetic 1:1 map")


class ComplianceBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.synthetic = load_geometry(SYNTHETIC)
        cls.wufr = load_geometry(WUFR)

    def case(self, angle, torque):
        return PrescribedTorqueInput(angle, torque, "explicit synthetic load case")

    def test_zero_torque_preserves_rigid_solver_exactly(self):
        cases = tuple(self.case(angle, 0.0) for angle in (-0.5, 0, 0.5))
        output = evaluate_prescribed_torque_sweep(
            self.synthetic, cases, SYNTHETIC_MAP, spans=SPANS,
        )
        self.assertEqual(len(output), 3)
        for item in output:
            self.assertTrue(item.both_mechanisms_valid)
            self.assertEqual(item.elastic_twist.twist_rad, 0)
            self.assertEqual(item.effective_steering_wheel_rad, item.case.steering_wheel_rad)
            self.assertEqual(item.rigid_transmission, item.elastic_transmission)
            for side in ("left", "right"):
                cmp = getattr(item, side)
                self.assertEqual(cmp.rigid_position, cmp.elastic_position)
                self.assertEqual(cmp.rigid_heading, cmp.elastic_heading)
                self.assertEqual(cmp.incremental_heading_difference_rad, 0.0)

    def test_applied_torque_reduces_rack_travel_for_positive_input(self):
        cases = (self.case(0.5, 35.54700928),)
        with patch("pssd_steering.compliance_bridge.solve_sweep",
                   wraps=solve_sweep) as solver:
            result = evaluate_prescribed_torque_sweep(
                self.synthetic, cases, SYNTHETIC_MAP, spans=SPANS,
            )
        self.assertEqual(solver.call_count, 2)
        item = result[0]
        self.assertTrue(item.both_mechanisms_valid)
        self.assertAlmostEqual(math.degrees(item.elastic_twist.twist_rad), 1.571, delta=.001)
        self.assertLess(item.elastic_transmission.rack_displacement,
                        item.rigid_transmission.rack_displacement)
        self.assertAlmostEqual(
            item.rigid_transmission.rack_displacement
            - item.elastic_transmission.rack_displacement,
            item.elastic_twist.twist_rad * .010,
            places=14,
        )
        self.assertIsNotNone(item.left.incremental_heading_difference_rad)
        self.assertIsNotNone(item.right.incremental_heading_difference_rad)
        self.assertNotEqual(item.left.incremental_heading_difference_rad, 0.0)

    def test_signed_reverse_torque_and_gear_orientation(self):
        a = evaluate_prescribed_torque_sweep(
            self.synthetic, (self.case(-.4, -23.69800619),),
            SYNTHETIC_MAP, spans=SPANS,
        )[0]
        self.assertLess(a.elastic_twist.twist_rad, 0)
        self.assertGreater(a.elastic_transmission.rack_displacement,
                           a.rigid_transmission.rack_displacement)
        reverse_map = SteeringTransmission(-1.0, .010, "synthetic reversed gear")
        b = evaluate_prescribed_torque_sweep(
            self.synthetic, (self.case(.4, 23.69800619),),
            reverse_map, spans=SPANS,
        )[0]
        self.assertGreater(b.elastic_transmission.rack_displacement,
                           b.rigid_transmission.rack_displacement)

    def test_domain_failure_is_not_clipped_or_hidden(self):
        sample = evaluate_prescribed_torque_sweep(
            self.synthetic, (self.case(2.0, 0),), SYNTHETIC_MAP, spans=SPANS,
        )[0]
        self.assertFalse(sample.both_mechanisms_valid)
        self.assertEqual(sample.left.rigid_position.failure_code,
                         FailureCode.INPUT_OUTSIDE_DOMAIN)
        self.assertEqual(sample.left.elastic_heading.failure_code,
                         FailureCode.INPUT_OUTSIDE_DOMAIN)
        self.assertIsNone(sample.left.incremental_heading_difference_rad)

    def test_wufr_missing_heading_basis_is_explicit(self):
        sample = evaluate_prescribed_torque_sweep(
            self.wufr, (self.case(.05, 0),), SYNTHETIC_MAP, spans=SPANS,
        )[0]
        self.assertFalse(sample.left.rigid_heading.available)
        self.assertEqual(sample.left.rigid_heading.failure_code,
                         FailureCode.DERIVED_OUTPUT_UNAVAILABLE)
        self.assertIsNone(sample.left.incremental_heading_difference_rad)

    def test_invalid_input_rejected(self):
        with self.assertRaises(ComplianceDefinitionError):
            SteeringTransmission(0, .010, "synthetic")
        with self.assertRaises(ComplianceDefinitionError):
            SteeringTransmission(1, .010, "")
        with self.assertRaises(ComplianceDefinitionError):
            PrescribedTorqueInput(.3, float("nan"), "test")
        with self.assertRaises(ComplianceDefinitionError):
            evaluate_prescribed_torque_sweep(
                self.synthetic, (), SYNTHETIC_MAP, spans=SPANS,
            )


if __name__ == "__main__":
    unittest.main()

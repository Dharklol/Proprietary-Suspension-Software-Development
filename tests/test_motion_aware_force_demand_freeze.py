from __future__ import annotations
from pathlib import Path
import tomllib
import unittest

ROOT=Path(__file__).resolve().parents[1]

class MotionAwareForceDemandFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls)->None:
        with (ROOT/"benchmarks/vehicle/planar_slip_kinematics_result_v0.1.0.toml").open("rb") as f: cls.vehicle=tomllib.load(f)
        with (ROOT/"benchmarks/steering/motion_aware_force_demand_result_v0.1.0.toml").open("rb") as f: cls.steering=tomllib.load(f)

    def test_rear_axle_velocity_center_recovers_ackermann_limiting_case(self)->None:
        item=self.vehicle["rear_axle_velocity_center_zero_slip"]
        self.assertAlmostEqual(item["left_heading_deg"],item["left_expected_deg"],places=12)
        self.assertAlmostEqual(item["right_heading_deg"],item["right_expected_deg"],places=12)
        self.assertLess(item["max_abs_error_deg"],1e-12)

    def test_parallel_steer_relative_slip_changes_with_velocity_center(self)->None:
        rel=self.vehicle["parallel_steer_relative_slip"]
        self.assertLess(rel["rear_to_front_interval"]["left_minus_right_slip_deg"],0.0)
        self.assertAlmostEqual(rel["front_axle"]["left_minus_right_slip_deg"],0.0,places=12)
        self.assertGreater(rel["forward_of_front"]["left_minus_right_slip_deg"],0.0)

    def test_same_required_tire_slips_can_change_final_ackermann_regime(self)->None:
        c=self.steering["same_tire_demands_velocity_center_comparison"]
        self.assertAlmostEqual(c["inside_required_slip_deg"],2.5)
        self.assertAlmostEqual(c["outside_required_slip_deg"],9.714285714285714)
        self.assertEqual(c["rear_axle_velocity_center"]["regime"],"pro_ackermann")
        self.assertEqual(c["front_axle_velocity_center"]["regime"],"anti_ackermann")

    def test_motion_aware_target_does_not_use_ackermann_anchor(self)->None:
        for state in self.steering["target_states"].values():
            self.assertFalse(state["ackermann_anchor_used"])
            self.assertEqual(state["target_mapping"],"wheel_velocity_heading_plus_required_tire_slip")
        self.assertIn("pro_ackermann:14",self.steering["target_states"]["nominal"]["regime_counts"])
        self.assertIn("anti_ackermann:10",self.steering["target_states"]["symmetric_bump_5mm"]["regime_counts"])

    def test_reference_candidate_is_mechanism_feasible_but_nonphysical(self)->None:
        self.assertTrue(self.steering["reference_candidate"]["feasible"])
        self.assertFalse(self.steering["production_claim"])
        self.assertEqual(self.steering["reference_candidate"]["objective_count"],2)

if __name__=="__main__": unittest.main()

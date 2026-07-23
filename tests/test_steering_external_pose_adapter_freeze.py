from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "benchmarks" / "steering" / "steering_external_pose_adapter_result_v0.1.0.toml"


class SteeringExternalPoseAdapterFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with RESULT_PATH.open("rb") as stream:
            cls.result = tomllib.load(stream)

    def test_frozen_parity_is_exact(self) -> None:
        self.assertEqual(3, self.result["state_count"])
        self.assertTrue(self.result["all_imported_states_feasible"])
        self.assertEqual(0.0, self.result["max_abs_transform_component_difference"])
        self.assertEqual(0.0, self.result["max_abs_coordinate_difference"])
        self.assertEqual(0.0, self.result["max_abs_heading_difference_deg"])
        self.assertEqual(0.0, self.result["max_abs_dynamic_toe_difference_deg"])

    def test_frozen_source_discovery_gate_remains_open(self) -> None:
        self.assertEqual(
            "no_reviewed_machine_readable_wufr_zero_steer_upright_transform_series_identified",
            self.result["source_discovery_status"],
        )
        authority = self.result["authority"]
        self.assertFalse(authority["wufr_suspension_motion_authority"])
        self.assertFalse(authority["optimumk_authority"])
        self.assertFalse(authority["cad_motion_authority"])
        self.assertFalse(authority["physical_authority"])
        self.assertFalse(authority["design_ranking_authority"])

    def test_contract_failure_checks_are_frozen(self) -> None:
        acceptance = self.result["acceptance"]
        self.assertTrue(acceptance["steering_response_double_count_rejection_tested"])
        self.assertTrue(acceptance["source_revision_requirement_tested"])
        self.assertTrue(acceptance["canonical_translation_unit_requirement_tested"])


if __name__ == "__main__":
    unittest.main()

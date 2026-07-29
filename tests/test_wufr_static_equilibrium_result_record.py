from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
FULL_RESULT = ROOT / "benchmarks/vehicle/wufr_static_equilibrium_result_v0.2.0.json"
SUMMARY_RECORD = ROOT / "benchmarks/vehicle/wufr_static_equilibrium_result_v0.2.0.toml"


class WufrStaticEquilibriumResultRecordTests(unittest.TestCase):
    def test_frozen_result_retains_authorized_gates_and_boundaries(self) -> None:
        report = json.loads(FULL_RESULT.read_text(encoding="utf-8"))
        with SUMMARY_RECORD.open("rb") as stream:
            summary = tomllib.load(stream)

        digest = hashlib.sha256(FULL_RESULT.read_bytes()).hexdigest()
        self.assertEqual(digest, summary["full_result_sha256"])
        self.assertEqual(report["version"], "0.2.0")
        self.assertEqual(report["status"], "pass")
        self.assertEqual(report["authorization_id"], "AUTH-VEH-0010")
        self.assertEqual(report["model_id"], "MOD-VEH-0007")
        self.assertEqual(
            report["equation_ids"],
            ["EQ-VEH-0015", "EQ-VEH-0017", "EQ-VEH-0018", "EQ-VEH-0019"],
        )
        self.assertEqual(
            report["result_label"], "uncorrelated_design_intent_static_gravity"
        )

        primary = report["primary"]
        self.assertTrue(primary["ok"])
        self.assertTrue(primary["complete_static_road_reaction"])
        self.assertTrue(primary["physical_closure"]["ok"])
        self.assertLessEqual(
            primary["physical_closure"]["maximum_force_residual_N"], 1.0e-6
        )
        self.assertLessEqual(
            primary["physical_closure"]["maximum_moment_residual_Nm"], 1.0e-6
        )
        self.assertTrue(all(value >= 0.0 for value in primary["contact"]["normal_reaction_N"]))
        self.assertLessEqual(
            max(abs(value) for value in primary["contact"]["wheel_equilibrium_residual_N"]),
            1.0e-8,
        )

        self.assertTrue(report["continuation_comparison"]["same_continuation_solution"])
        self.assertTrue(
            all(item["pass"] for item in report["gravity_reduction_oracles"].values())
        )
        evidence = report["old_equation_negative_evidence"]
        self.assertTrue(evidence["old_equation_fails_physical_closure"])
        self.assertTrue(evidence["corrected_equation_matches_physical_wrench"])
        self.assertFalse(evidence["balancing_wrench_used"])

        self.assertFalse(report["invalid_setting_failure"]["ok"])
        self.assertEqual(
            report["invalid_setting_failure"]["failure_code"], "invalid_arb_setting"
        )
        self.assertTrue(all(value is False for value in report["boundaries"].values()))


if __name__ == "__main__":
    unittest.main()

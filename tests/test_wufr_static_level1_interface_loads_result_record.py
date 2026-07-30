from __future__ import annotations

import json
from pathlib import Path
import unittest

from scripts.run_wufr_static_level1_interface_load_benchmarks import build_report, summary_toml

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "benchmarks/suspension/wufr_static_level1_interface_loads_result_v0.1.0.json"
TOML_PATH = ROOT / "benchmarks/suspension/wufr_static_level1_interface_loads_result_v0.1.0.toml"


class WufrStaticLevel1InterfaceLoadsResultRecordTests(unittest.TestCase):
    def test_frozen_full_record_regenerates_exactly(self) -> None:
        expected = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        self.assertEqual(build_report(), expected)

    def test_frozen_summary_record_regenerates_exactly(self) -> None:
        report = build_report()
        self.assertEqual(summary_toml(report), TOML_PATH.read_text(encoding="utf-8"))

    def test_frozen_boundaries_remain_restricted(self) -> None:
        report = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        boundary = report["boundaries"]
        self.assertTrue(boundary["complete_for_authorized_static_gravity_case"])
        for key in (
            "complete_physical_vehicle_load_case",
            "maneuver_complete",
            "individual_a_arm_joint_split_authorized",
            "rocker_result_publication_authorized",
            "installed_as_built_authority",
            "production_authority",
        ):
            self.assertFalse(boundary[key])


if __name__ == "__main__":
    unittest.main()

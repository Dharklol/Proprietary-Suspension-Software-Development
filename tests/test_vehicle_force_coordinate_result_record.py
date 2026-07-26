from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from scripts.run_vehicle_force_coordinate_benchmarks import build_report


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "benchmarks/vehicle/vehicle_force_coordinate_result_v0.1.0.toml"


class VehicleForceCoordinateResultRecordTests(unittest.TestCase):
    def test_frozen_record_matches_current_benchmark_runner(self) -> None:
        with RESULT.open("rb") as stream:
            frozen = tomllib.load(stream)
        report = build_report()

        b3 = report["BENCH-VEH-0003"]
        f3 = frozen["BENCH-VEH-0003"]
        self.assertEqual(f3["pass"], b3["pass"])
        self.assertEqual(f3["verification_level"], "B")
        for key in (
            "transport_error_m",
            "wrench_moment_error_Nm",
            "generalized_force_max_error",
            "numerical_convergence_error",
        ):
            self.assertEqual(f3[key], b3[key], key)
        self.assertEqual(f3["q_z_s_N"], b3["generalized_force"][0])
        self.assertEqual(f3["q_phi_Nm"], b3["generalized_force"][1])
        self.assertEqual(f3["q_theta_Nm"], b3["generalized_force"][2])

        b4 = report["BENCH-VEH-0004"]
        f4 = frozen["BENCH-VEH-0004"]
        self.assertEqual(f4["pass"], b4["pass"])
        self.assertEqual(f4["verification_level"], "B")
        for key in (
            "valid_contact_status",
            "negative_reaction_status",
            "negative_reaction_preserved_N",
            "wufr_wheelbase_m",
            "wufr_front_track_m",
            "wufr_rear_track_m",
            "wufr_cg_to_front_axle_m",
            "wufr_cg_to_rear_axle_m",
            "wufr_contact_max_gap_m",
            "installed_authority",
        ):
            self.assertEqual(f4[key], b4[key], key)

        self.assertFalse(frozen["performance_authority"])
        self.assertFalse(frozen["installed_as_built_authority"])
        self.assertFalse(frozen["force_law_authority"])
        self.assertFalse(frozen["equilibrium_authority"])
        self.assertFalse(frozen["linkage_force_authority"])


if __name__ == "__main__":
    unittest.main()

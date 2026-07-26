from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class SuspensionWufrZBarMapAuthorizationTests(unittest.TestCase):
    def test_authorization_keeps_numerical_wufr_map_blocked(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0006.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0006")
        self.assertEqual(auth["status"], "review_ready")
        self.assertEqual(auth["scope"]["model_ids"], ["MOD-SUSP-0005"])
        self.assertEqual(auth["scope"]["benchmark_ids"], ["BENCH-SUSP-0013"])
        self.assertFalse(auth["scope"]["implementation_authorized"])
        self.assertFalse(auth["numerics"]["body_roll_substitution_allowed"])
        self.assertFalse(auth["numerics"]["track_width_approximation_allowed"])
        self.assertFalse(auth["numerics"]["wheel_travel_shortcut_allowed"])
        self.assertFalse(auth["numerics"]["historical_motion_ratio_allowed"])
        self.assertFalse(auth["numerics"]["sketch_row_connectivity_allowed"])
        self.assertFalse(auth["numerics"]["implementation_authorized"])

        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        self.assertIn("body roll", prohibited)
        self.assertIn("track width", prohibited)
        self.assertIn("wheel-travel", prohibited)
        self.assertIn("motion ratios", prohibited)
        self.assertIn("sketch row", prohibited)
        self.assertIn("vehicle-coordinate q_arb", prohibited)

    def test_source_record_freezes_recovered_sources_and_gap(self) -> None:
        source = _load("data_catalog/wufr27_zbar_mapping_source_v0.toml")
        self.assertEqual(source["record_id"], "WUFR27_ZBAR_MAPPING_SOURCE_V0")
        self.assertFalse(source["map_authorized"])
        self.assertFalse(source["jacobian_authorized"])
        self.assertEqual(
            source["governing_constitutive_context"]["blade_settings_N_per_m"],
            [280000.0, 300000.0, 400000.0, 700000.0, 2300000.0],
        )

        recovered = source["recovered_sources"]
        self.assertEqual(recovered["inboard_calculator"]["box_file_id"], "2026725896730")
        self.assertEqual(
            recovered["inboard_calculator"]["sha1"],
            "2f98937654a43914bb586a7e0a1ae9908d97bcb5",
        )
        self.assertEqual(
            recovered["arb_force_calculation"]["google_drive_file_id"],
            "1pm6DgBXh4sUUca1xnoesmautUZxdcLNU",
        )
        self.assertEqual(
            recovered["arb_calculations"]["google_drive_file_id"],
            "1o7wbbLSiNtu51q8WpGCYHXycQKR3TGzA",
        )
        self.assertIn("no assembled z-bar", recovered["inboard_calculator"]["finding"].lower())
        self.assertIn("historical comparison", recovered["arb_force_calculation"]["finding"].lower())
        self.assertIn("does not provide", recovered["arb_calculations"]["finding"].lower())

        shortcuts = source["blocked_shortcuts"]
        self.assertTrue(shortcuts["body_roll_equals_blade_deflection"])
        self.assertTrue(shortcuts["track_width_lever_approximation"])
        self.assertTrue(shortcuts["wheel_travel_difference_as_blade_deflection"])
        self.assertTrue(shortcuts["historical_scalar_motion_ratio"])
        self.assertTrue(shortcuts["exporter_sketch_row_connectivity"])
        self.assertTrue(shortcuts["reduced_axle_roll_stiffness_back_conversion"])
        self.assertEqual(source["decision"]["implementation_status"], "blocked_pending_explicit_mechanism_fixture")

    def test_benchmark_requires_explicit_future_mechanism_fixture(self) -> None:
        bench = _load("registry/records/benchmarks/BENCH-SUSP-0013.toml")["record"]
        self.assertEqual(bench["id"], "BENCH-SUSP-0013")
        self.assertEqual(bench["verification_level"], "B")
        self.assertIn("MOD-SUSP-0005", bench["target_ids"])
        criteria = "\n".join(bench["acceptance_criteria"]).lower()
        for term in (
            "blade pivot/axis",
            "blade working point",
            "linkage endpoints",
            "rocker arb pickup",
            "zero-preload branch",
            "q_arb remains unavailable",
        ):
            self.assertIn(term, criteria)
        self.assertEqual(bench["implementation"], "not_authorized_current_source_gap")

    def test_current_arb_authority_remains_discrete_solidworks_blade_law(self) -> None:
        package = _load("data_catalog/wufr27_anti_roll_bar_package_v0.toml")
        governing = package["governing_solidworks_fea"]
        self.assertEqual(governing["stiffness_N_per_mm"], [280.0, 300.0, 400.0, 700.0, 2300.0])
        self.assertEqual(governing["stiffness_N_per_m"], [280000.0, 300000.0, 400000.0, 700000.0, 2300000.0])
        self.assertFalse(package["authority_boundaries"]["interpolation_authorized"])
        self.assertFalse(package["authority_boundaries"]["z_bar_geometry_map_authorized"])


if __name__ == "__main__":
    unittest.main()

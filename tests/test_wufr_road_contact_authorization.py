from __future__ import annotations

from pathlib import Path
import math
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class WUFRRoadContactAuthorizationTests(unittest.TestCase):
    def test_failed_prior_contact_assumption_remains_rejected(self) -> None:
        auth6 = _load("authorizations/vehicle/AUTH-VEH-0006.toml")
        auth7 = _load("authorizations/vehicle/AUTH-VEH-0007.toml")
        assumption4 = _load("registry/records/assumptions/ASM-VEH-0004.toml")["record"]
        result = _load("benchmarks/vehicle/wufr_road_contact_assumption_probe_v0.1.0.toml")
        b8 = _load("registry/records/benchmarks/BENCH-VEH-0008.toml")["record"]

        self.assertEqual(auth6["status"], "suspended_by_AUTH-VEH-0007")
        self.assertFalse(auth6["implementation_authorized"])
        self.assertFalse(auth7["implementation_authorized"])
        self.assertEqual(assumption4["status"], "deprecated")
        self.assertFalse(result["pass"])
        probe = result["historical_front_left_reconstruction"]
        self.assertAlmostEqual(probe["required_max_euclidean_error_m"], 5.0e-6, places=15)
        self.assertAlmostEqual(probe["observed_max_euclidean_error_m"], 0.0008458158026623031, places=15)
        self.assertGreater(probe["observed_max_euclidean_error_m"], 100.0 * probe["required_max_euclidean_error_m"])
        self.assertEqual(b8["status"], "active")
        self.assertIn("invalidated", b8["outcome"])

    def test_auth_veh_0008_is_explicit_replacement_not_revival(self) -> None:
        auth8 = _load("authorizations/vehicle/AUTH-VEH-0008.toml")
        model = _load("registry/records/models/MOD-VEH-0006.toml")["record"]
        assumption5 = _load("registry/records/assumptions/ASM-VEH-0005.toml")["record"]
        eq14 = _load("registry/records/equations/EQ-VEH-0014.toml")["record"]

        self.assertEqual(auth8["status"], "review_ready")
        self.assertTrue(auth8["implementation_authorized"])
        self.assertEqual(auth8["scope"]["prior_hold"], "AUTH-VEH-0007")
        self.assertEqual(auth8["scope"]["failed_prior_assumption"], "ASM-VEH-0004")
        self.assertEqual(auth8["scope"]["assumption_ids"], ["ASM-VEH-0005"])
        self.assertIn("EQ-VEH-0014", auth8["scope"]["equation_ids"])
        self.assertEqual(model["status"], "proposed")
        self.assertEqual(model["authorization_id"], "AUTH-VEH-0008")
        self.assertEqual(model["active_contact_assumption_id"], "ASM-VEH-0005")
        self.assertEqual(model["invalidated_assumption_id"], "ASM-VEH-0004")
        self.assertEqual(model["maturity"], "M1")
        self.assertEqual(model["verification_level"], "B")
        self.assertIn("implemented_in_PR67", model["authorization_state"])
        self.assertEqual(assumption5["status"], "active")
        self.assertEqual(eq14["status"], "proposed")

    def test_source_radius_is_single_frozen_nominal_radius(self) -> None:
        wheel = _load("benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml")
        auth8 = _load("authorizations/vehicle/AUTH-VEH-0008.toml")
        assumption5 = _load("registry/records/assumptions/ASM-VEH-0005.toml")["record"]
        self.assertAlmostEqual(float(wheel["nominal_source"]["tire_radius_mm"]), 232.41, places=12)
        self.assertIn("0.23241", assumption5["description"])
        self.assertIn("232.41", auth8["source_boundary"]["radius_source"])
        self.assertIn("not measured loaded radius", auth8["source_boundary"]["radius_role"])

    def test_circle_equation_has_required_geometry_and_exclusions(self) -> None:
        eq14 = _load("registry/records/equations/EQ-VEH-0014.toml")["record"]
        canonical = eq14["canonical_equation"]
        self.assertIn("n_R - (n_R dot n_w)n_w", canonical)
        self.assertIn("r_cp=r_wc-R e", canonical)
        self.assertIn("s>s_min", canonical)
        failures = "\n".join(eq14["failure_behavior"]).lower()
        self.assertIn("body vertical", failures)
        self.assertIn("loaded radius", failures)
        self.assertIn("historical optimumk contact patch", failures)

    def test_nominal_geometry_values_are_formula_outputs_not_fitted_contact_patch_targets(self) -> None:
        wheel = _load("benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml")
        bench = _load("registry/records/benchmarks/BENCH-VEH-0010.toml")["record"]
        R = 0.001 * float(wheel["nominal_source"]["tire_radius_mm"])
        expected = {
            ("front", "left"): (0.000159242280, 0.615984170, 0.0),
            ("front", "right"): (0.000159242280, -0.615984170, 0.0),
            ("rear", "left"): (-0.000035395821, 0.603285406, 0.0),
            ("rear", "right"): (-0.000035395821, -0.603285406, 0.0),
        }
        for row in wheel["nominal_expected"]:
            center = tuple(float(v) for v in row["wheel_center_m"])
            normal = tuple(float(v) for v in row["plane_normal"])
            road = (0.0, 0.0, 1.0)
            dot = sum(a * b for a, b in zip(road, normal))
            v = tuple(road[i] - dot * normal[i] for i in range(3))
            norm = math.sqrt(sum(x * x for x in v))
            e = tuple(x / norm for x in v)
            contact = tuple(center[i] - R * e[i] for i in range(3))
            target = expected[(row["axle"], row["side"])]
            for actual, frozen in zip(contact, target):
                self.assertAlmostEqual(actual, frozen, places=9)
            self.assertAlmostEqual(contact[2], 0.0, places=12)
        text = "\n".join(bench["acceptance_criteria"])
        self.assertIn("not fitted targets", text)
        self.assertIn("nonzero longitudinal offsets", text)

    def test_compatibility_records_preserve_authorization_state_after_implementation(self) -> None:
        model = _load("registry/records/models/MOD-VEH-0006.toml")["record"]
        self.assertEqual(model["status"], "proposed")
        self.assertEqual(model["maturity"], "M1")
        self.assertEqual(model["verification_level"], "B")
        self.assertEqual(model["implementation_pr"], 67)

        for relative in (
            "registry/records/equations/EQ-VEH-0011.toml",
            "registry/records/equations/EQ-VEH-0012.toml",
            "registry/records/equations/EQ-VEH-0013.toml",
            "registry/records/equations/EQ-VEH-0014.toml",
        ):
            self.assertEqual(_load(relative)["record"]["status"], "proposed")

        for relative in (
            "registry/records/benchmarks/BENCH-VEH-0009.toml",
            "registry/records/benchmarks/BENCH-VEH-0010.toml",
        ):
            bench = _load(relative)["record"]
            self.assertEqual(bench["status"], "active")
            self.assertEqual(bench["implementation_pr"], 67)
            self.assertIn("benchmarks/vehicle/wufr_road_contact_result_v0.1.0.toml", bench["result_record"])

        auth8 = _load("authorizations/vehicle/AUTH-VEH-0008.toml")
        prohibited = "\n".join(auth8["prohibited"]["items"]).lower()
        for phrase in (
            "asm-veh-0004",
            "loaded radius",
            "tire width",
            "body-roll-times-track",
            "scalar motion ratio",
            "road reactions",
            "installed/as-built",
        ):
            self.assertIn(phrase, prohibited)

    def test_historical_contact_output_record_points_to_separate_replacement_authority(self) -> None:
        source = _load("data_catalog/wufr26_road_contact_reference_v0.toml")
        replacement = source["replacement_contact_authority"]
        self.assertEqual(replacement["authorization_id"], "AUTH-VEH-0008")
        self.assertEqual(replacement["assumption_id"], "ASM-VEH-0005")
        self.assertEqual(replacement["equation_id"], "EQ-VEH-0014")
        self.assertAlmostEqual(replacement["radius_m"], 0.23241, places=12)
        self.assertIn("not derived or fitted", replacement["relationship_to_this_record"])
        self.assertFalse(source["authority_boundaries"]["loaded_radius_authority"])
        self.assertFalse(source["authority_boundaries"]["tire_deflection_authority"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import math
from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class SuspensionSpringForceAuthorizationTests(unittest.TestCase):
    def test_authorization_is_bounded_and_review_ready(self) -> None:
        auth = _load("authorizations/suspension/AUTH-SUSP-0004.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-SUSP-0004")
        self.assertEqual(auth["status"], "review_ready")
        self.assertEqual(auth["scope"]["model_ids"], ["MOD-SUSP-0004"])
        self.assertEqual(
            auth["scope"]["equation_ids"],
            ["EQ-SUSP-0013", "EQ-SUSP-0014", "EQ-SUSP-0015"],
        )
        self.assertEqual(auth["scope"]["benchmark_ids"], ["BENCH-SUSP-0009", "BENCH-SUSP-0010"])
        self.assertEqual(auth["scope"]["assumption_ids"], ["ASM-SUSP-0002"])
        self.assertEqual(auth["scope"]["upstream_model_ids"], ["MOD-SUSP-0003"])
        self.assertFalse(auth["numerics"]["hidden_clipping_allowed"])
        self.assertFalse(auth["numerics"]["constitutive_extrapolation_allowed"])
        self.assertFalse(auth["numerics"]["progressive_endpoint_averaging_allowed"])
        self.assertFalse(auth["numerics"]["scalar_motion_ratio_substitution_allowed"])

        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        self.assertIn("constant 30, 33, or 36 n/mm", prohibited)
        self.assertIn("spring_unseated", prohibited)
        self.assertIn("damper velocity force", prohibited)
        self.assertIn("shock-pot", prohibited)
        self.assertIn("vehicle heave/roll/pitch equilibrium", prohibited)

    def test_model_equation_benchmark_and_assumption_links_are_frozen(self) -> None:
        model = _load("registry/records/models/MOD-SUSP-0004.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-SUSP-0004")
        self.assertEqual(model["upstream_model_ids"], ["MOD-SUSP-0003"])
        self.assertEqual(
            model["equation_ids"],
            ["EQ-SUSP-0013", "EQ-SUSP-0014", "EQ-SUSP-0015", "EQ-SUSP-0028"],
        )
        self.assertEqual(
            model["benchmark_ids"],
            ["BENCH-SUSP-0009", "BENCH-SUSP-0010", "BENCH-SUSP-0025"],
        )
        self.assertEqual(model["physical_vector_authorization_document"], "authorizations/suspension/AUTH-SUSP-0014.toml")
        assumption = _load("registry/records/assumptions/ASM-SUSP-0002.toml")["record"]
        self.assertEqual(assumption["id"], "ASM-SUSP-0002")
        self.assertEqual(assumption["severity"], "high")
        self.assertIn("57 mm", assumption["description"])
        self.assertIn("185.7 mm", assumption["description"])

        for equation_id in ("EQ-SUSP-0013", "EQ-SUSP-0014", "EQ-SUSP-0015"):
            equation = _load(f"registry/records/equations/{equation_id}.toml")["record"]
            self.assertEqual(equation["id"], equation_id)
            self.assertEqual(equation["verification_level"], "none")
            self.assertEqual(set(equation["benchmark_ids"]), {"BENCH-SUSP-0009", "BENCH-SUSP-0010"})
        physical_eq = _load("registry/records/equations/EQ-SUSP-0028.toml")["record"]
        self.assertEqual(physical_eq["verification_level"], "A")
        self.assertEqual(physical_eq["benchmark_ids"], ["BENCH-SUSP-0025"])

        for benchmark_id in model["benchmark_ids"]:
            benchmark = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertEqual(benchmark["id"], benchmark_id)
            self.assertIn("MOD-SUSP-0004", benchmark["target_ids"])

    def test_wufr_package_preserves_reviewed_setup_and_assumptions(self) -> None:
        package = _load("data_catalog/wufr27_spring_package_v0.toml")
        setup = package["reviewed_setup"]
        self.assertEqual(package["configuration_id"], "WUFR27_SUSPENSION_BASELINE_V0")
        self.assertFalse(package["installed_as_built_authority"])
        self.assertAlmostEqual(setup["spring_free_length_m"], 0.100)
        self.assertEqual(setup["intentional_preload"], "zero")
        self.assertEqual(setup["tender_or_helper_spring"], "none")
        self.assertEqual(setup["front_spring_description"], "36 N/mm linear")
        self.assertEqual(setup["front_linear_rate_N_per_m"], 36000.0)
        self.assertEqual(setup["rear_rate_start_N_per_m"], 30000.0)
        self.assertEqual(setup["rear_rate_end_N_per_m"], 36000.0)
        self.assertEqual(setup["rear_progression_law_status"], "reviewed_team_modeling_assumption")
        self.assertAlmostEqual(setup["rear_progression_span_m"], 0.057)
        self.assertIn("not a KW-published", setup["rear_progression_assumption"])
        self.assertEqual(
            package["actuation_interface"]["spring_seat_mapping_status"],
            "frozen_design_intent_assumption_under_ASM-SUSP-0002",
        )

    def test_vendor_and_geometry_reference_reconstruct_nominal_compression(self) -> None:
        package = _load("data_catalog/wufr27_spring_package_v0.toml")
        vendor = package["kw_vendor_attachment"]
        geometry = package["wufr26_suspension_geometry"]
        reference = package["wufr27_zero_preload_reference"]

        self.assertEqual(
            vendor["sha256"],
            "647b7b451612174852293b0bd65d193452991c6a3c697a242c07b04860cea36c",
        )
        self.assertAlmostEqual(vendor["damper_travel_mm"], 57.0)
        self.assertAlmostEqual(vendor["piggyback_full_extension_eye_to_eye_mm"], 185.7)
        self.assertAlmostEqual(geometry["front_nominal_eye_to_eye_from_export_m"], 0.16459934705216787)
        self.assertAlmostEqual(geometry["rear_nominal_eye_to_eye_from_export_m"], 0.1646105387908077)
        self.assertAlmostEqual(
            reference["front_nominal_spring_compression_m"],
            0.1857 - geometry["front_nominal_eye_to_eye_from_export_m"],
        )
        self.assertAlmostEqual(
            reference["rear_nominal_spring_compression_m"],
            0.1857 - geometry["rear_nominal_eye_to_eye_from_export_m"],
        )
        self.assertIn("not installed/as-built", reference["nominal_force_status"])

    def test_wufr_nominal_front_and_rear_force_hand_cases(self) -> None:
        package = _load("data_catalog/wufr27_spring_package_v0.toml")
        ref = package["wufr27_zero_preload_reference"]
        setup = package["reviewed_setup"]

        x_front = ref["front_nominal_spring_compression_m"]
        front_force = setup["front_linear_rate_N_per_m"] * x_front
        self.assertTrue(math.isclose(front_force, 759.6235061219563, rel_tol=1e-12, abs_tol=1e-12))
        self.assertTrue(math.isclose(front_force, ref["front_nominal_force_N_under_reviewed_model"], rel_tol=1e-12))

        x_rear = ref["rear_nominal_spring_compression_m"]
        k0 = setup["rear_rate_start_N_per_m"]
        k1 = setup["rear_rate_end_N_per_m"]
        span = setup["rear_progression_span_m"]
        a = (k1 - k0) / span
        rear_tangent = k0 + a * x_rear
        rear_force = k0 * x_rear + 0.5 * a * x_rear * x_rear
        rear_energy = 0.5 * k0 * x_rear * x_rear + (a / 6.0) * x_rear**3

        self.assertTrue(math.isclose(rear_tangent, 32219.94328517813, rel_tol=1e-12))
        self.assertTrue(math.isclose(rear_force, 656.0925401754539, rel_tol=1e-12))
        self.assertGreater(rear_energy, 0.0)
        self.assertNotAlmostEqual(rear_force, rear_tangent * x_rear)
        self.assertTrue(math.isclose(rear_force, ref["rear_nominal_force_N_under_reviewed_model"], rel_tol=1e-12))

    def test_linear_hand_case_force_energy_tangent_and_signed_generalized_force(self) -> None:
        k = 10000.0
        x_s = 0.020
        force = k * x_s
        energy = 0.5 * k * x_s * x_s
        tangent = k
        dL_dq = -0.25
        generalized_force = force * dL_dq

        self.assertAlmostEqual(force, 200.0)
        self.assertAlmostEqual(energy, 2.0)
        self.assertAlmostEqual(tangent, 10000.0)
        self.assertAlmostEqual(generalized_force, -50.0)

        h = 1.0e-6
        x_plus = x_s - dL_dq * h
        x_minus = x_s + dL_dq * h
        u_plus = 0.5 * k * x_plus * x_plus
        u_minus = 0.5 * k * x_minus * x_minus
        q_fd = -(u_plus - u_minus) / (2.0 * h)
        self.assertTrue(math.isclose(q_fd, generalized_force, rel_tol=1.0e-10, abs_tol=1.0e-9))

    def test_explicit_preload_reference_and_unseated_boundary(self) -> None:
        x_pre = 0.005
        L_ref = 0.200
        L_d = 0.190
        x_s = x_pre + L_ref - L_d
        self.assertAlmostEqual(x_s, 0.015)
        zero_preload_x = 0.0 + L_ref - 0.201
        self.assertLess(zero_preload_x, 0.0)

        eq = _load("registry/records/equations/EQ-SUSP-0013.toml")["record"]
        failures = "\n".join(eq["failure_behavior"]).lower()
        self.assertIn("spring_unseated", failures)
        self.assertIn("do not clip", failures)

    def test_synthetic_piecewise_progressive_hand_case(self) -> None:
        x0, f0 = 0.010, 100.0
        x1, f1 = 0.020, 240.0
        x = 0.015
        slope = (f1 - f0) / (x1 - x0)
        force = f0 + slope * (x - x0)
        energy_first_segment = 0.5 * (0.0 + 100.0) * 0.010
        energy_partial_second = 0.5 * (100.0 + force) * (x - x0)
        energy = energy_first_segment + energy_partial_second
        self.assertAlmostEqual(slope, 14000.0)
        self.assertAlmostEqual(force, 170.0)
        self.assertAlmostEqual(energy, 1.175)

    def test_historical_sources_and_shockpot_do_not_override_reviewed_model(self) -> None:
        package = _load("data_catalog/wufr27_spring_package_v0.toml")
        self.assertEqual(package["wufr26_optimumk_setup"]["observed_rear_rate_N_per_mm"], 36.0)
        self.assertEqual(package["wufr26_historical_inboard_calculator"]["observed_rear_rate_N_per_m"], 30000.0)
        self.assertIn("not the current", package["wufr26_optimumk_setup"]["rate_warning"])
        self.assertEqual(package["reviewed_setup"]["rear_spring_description"], "30 to 36 N/mm linear-progressive")
        self.assertEqual(package["shockpot_ride_height_note"]["reported_raw"], "44m")
        self.assertIn("do not use", package["shockpot_ride_height_note"]["physics_use"])


if __name__ == "__main__":
    unittest.main()

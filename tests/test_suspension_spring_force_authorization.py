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
        self.assertEqual(
            auth["scope"]["benchmark_ids"],
            ["BENCH-SUSP-0009", "BENCH-SUSP-0010"],
        )
        self.assertEqual(auth["scope"]["upstream_model_ids"], ["MOD-SUSP-0003"])
        self.assertFalse(auth["numerics"]["hidden_clipping_allowed"])
        self.assertFalse(auth["numerics"]["constitutive_extrapolation_allowed"])
        self.assertFalse(auth["numerics"]["progressive_endpoint_averaging_allowed"])
        self.assertFalse(auth["numerics"]["scalar_motion_ratio_substitution_allowed"])

        prohibited = "\n".join(auth["prohibited"]["items"])
        self.assertIn("30, 33, or 36 N/mm", prohibited)
        self.assertIn("57 mm", prohibited)
        self.assertIn("spring_unseated", prohibited)
        self.assertIn("Damper velocity force", prohibited)
        self.assertIn("vehicle heave/roll/pitch equilibrium", prohibited)

    def test_model_equation_benchmark_links_are_frozen(self) -> None:
        model = _load("registry/records/models/MOD-SUSP-0004.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-SUSP-0004")
        self.assertEqual(model["upstream_model_ids"], ["MOD-SUSP-0003"])
        self.assertEqual(
            model["equation_ids"],
            ["EQ-SUSP-0013", "EQ-SUSP-0014", "EQ-SUSP-0015"],
        )
        self.assertEqual(model["benchmark_ids"], ["BENCH-SUSP-0009", "BENCH-SUSP-0010"])
        for equation_id in model["equation_ids"]:
            equation = _load(f"registry/records/equations/{equation_id}.toml")["record"]
            self.assertEqual(equation["id"], equation_id)
            self.assertEqual(equation["verification_level"], "none")
            self.assertEqual(set(equation["benchmark_ids"]), {"BENCH-SUSP-0009", "BENCH-SUSP-0010"})
        for benchmark_id in model["benchmark_ids"]:
            benchmark = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertEqual(benchmark["id"], benchmark_id)
            self.assertIn("MOD-SUSP-0004", benchmark["target_ids"])

    def test_wufr_package_preserves_current_setup_and_source_gaps(self) -> None:
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
        self.assertEqual(setup["rear_progression_law_status"], "incomplete_parameter_authority")
        self.assertIn("Do not average", setup["rear_progression_gap"])
        self.assertIn("Do not", setup["rear_progression_gap"])
        self.assertIn("not_yet_frozen", package["actuation_interface"]["spring_seat_mapping_status"])

    def test_vendor_damper_data_cannot_become_spring_progression_or_reference(self) -> None:
        package = _load("data_catalog/wufr27_spring_package_v0.toml")
        vendor = package["kw_vendor_attachment"]
        self.assertEqual(
            vendor["sha256"],
            "647b7b451612174852293b0bd65d193452991c6a3c697a242c07b04860cea36c",
        )
        self.assertAlmostEqual(vendor["damper_travel_mm"], 57.0)
        self.assertAlmostEqual(vendor["piggyback_dimension_eye_to_eye_mm"], 185.7)
        self.assertIn("not spring-rate-curve authority", vendor["source_role"])
        self.assertIn("do not by themselves establish", vendor["reference_length_warning"])

        b10 = _load("registry/records/benchmarks/BENCH-SUSP-0010.toml")["record"]
        criteria = "\n".join(b10["acceptance_criteria"])
        self.assertIn("57 mm", criteria)
        self.assertIn("33", criteria)
        self.assertIn("progression law incomplete", criteria)

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

        # Independent potential-energy finite difference for L(q)=L0+dL_dq*q.
        # x(q)=x0-dL_dq*q, so Q=-dU/dq=F*dL_dq.
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
        failures = "\n".join(eq["failure_behavior"])
        self.assertIn("spring_unseated", failures)
        self.assertIn("Do not clip", failures)

    def test_synthetic_piecewise_progressive_hand_case(self) -> None:
        # Frozen BENCH-SUSP-0009 table:
        # (0,0), (0.01,100), (0.02,240), evaluated at x=0.015.
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

    def test_historical_sources_do_not_override_reviewed_current_rear_identity(self) -> None:
        package = _load("data_catalog/wufr27_spring_package_v0.toml")
        self.assertEqual(package["wufr26_optimumk_setup"]["observed_rear_rate_N_per_mm"], 36.0)
        self.assertEqual(package["wufr26_historical_inboard_calculator"]["observed_rear_rate_N_per_m"], 30000.0)
        self.assertIn("do not define", package["wufr26_historical_inboard_calculator"]["method_warning"])
        self.assertIn("not the current", package["wufr26_optimumk_setup"]["rate_warning"])
        self.assertEqual(package["reviewed_setup"]["rear_spring_description"], "30 to 36 N/mm linear-progressive")


if __name__ == "__main__":
    unittest.main()

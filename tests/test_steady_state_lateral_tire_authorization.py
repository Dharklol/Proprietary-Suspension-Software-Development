from __future__ import annotations

from pathlib import Path
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


class SteadyStateLateralTireAuthorizationTests(unittest.TestCase):
    def test_auth_tire_0001_is_pure_lateral_and_source_bounded(self) -> None:
        auth = _load("authorizations/tire/AUTH-TIRE-0001.toml")
        self.assertEqual(auth["authorization_id"], "AUTH-TIRE-0001")
        self.assertEqual(auth["status"], "review_ready")
        self.assertTrue(auth["implementation_authorized"])
        scope = auth["scope"]
        for key in (
            "provider_neutral_pure_lateral_force_authorized",
            "canonical_signed_response_contract_authorized",
            "exact_operating_point_curve_evaluation_authorized",
            "bounded_operating_state_interpolation_authorized",
            "local_piecewise_slope_authorized",
            "branch_aware_inverse_authorized",
            "synthetic_verification_fixtures_authorized",
        ):
            self.assertTrue(scope[key])
        for key in (
            "source_specific_r25b_runtime_activation_authorized",
            "aligning_moment_authorized",
            "longitudinal_force_authorized",
            "combined_slip_authorized",
            "transient_or_relaxation_authorized",
            "temperature_or_wear_state_authorized",
            "vehicle_equilibrium_authorized",
            "steering_design_ranking_authorized",
            "track_surface_correction_authorized",
            "installed_as_built_authority",
            "production_authority",
        ):
            self.assertFalse(scope[key])

    def test_canonical_units_frame_and_force_role_are_frozen(self) -> None:
        auth = _load("authorizations/tire/AUTH-TIRE-0001.toml")
        state = auth["canonical_operating_state"]
        self.assertEqual(state["slip_angle_unit"], "rad")
        self.assertEqual(state["normal_load_unit"], "N")
        self.assertEqual(state["inclination_unit"], "rad")
        self.assertEqual(state["pressure_unit"], "Pa")
        frame = auth["canonical_tire_frame"]
        self.assertEqual(frame["frame_id"], "CANONICAL_TIRE_CONTACT_ISO_LEFT_UP")
        self.assertEqual(frame["handedness"], "right_handed")
        self.assertIn("velocity direction to +x_t", frame["slip_angle_definition"])
        self.assertIn("road-on-tire", frame["lateral_force_definition"])
        self.assertIn("explicit adapter operation", frame["source_adapter_rule"])

    def test_forward_interpolation_is_bounded_and_complete_cell_only(self) -> None:
        auth = _load("authorizations/tire/AUTH-TIRE-0001.toml")
        forward = auth["forward_evaluation"]
        self.assertIn("Piecewise-linear", forward["method"])
        self.assertFalse(forward["slip_extrapolation_allowed"])
        self.assertFalse(forward["operating_state_extrapolation_allowed"])
        self.assertFalse(forward["hidden_zero_or_odd_symmetry_allowed"])
        self.assertFalse(forward["clipping_allowed"])
        state = auth["operating_state_interpolation"]
        self.assertIn("complete bracketing Cartesian cell", state["cell_rule"])
        self.assertIn("independently", state["nested_evaluation_rule"])
        self.assertIn("no nearest-neighbor substitution", state["missing_corner_rule"])
        self.assertIn("does not convert", state["censor_rule"])

    def test_derivative_and_inverse_keep_nonsmooth_and_multiple_root_behavior(self) -> None:
        auth = _load("authorizations/tire/AUTH-TIRE-0001.toml")
        derivative = auth["derivative_contract"]
        self.assertEqual(derivative["unit"], "N/rad")
        self.assertIn("left and right slopes separately", derivative["knot_rule"])
        self.assertIn("may be reported only", derivative["cornering_stiffness_rule"])
        inverse = auth["inverse_contract"]
        self.assertIn("return every corresponding", inverse["method"])
        self.assertIn("remain distinct candidates", inverse["multiple_root_rule"])
        self.assertFalse(inverse["force_extrapolation_allowed"])
        self.assertIn("structured out-of-domain failure", inverse["empty_result_rule"])

    def test_real_r25b_runtime_activation_remains_blocked(self) -> None:
        auth = _load("authorizations/tire/AUTH-TIRE-0001.toml")
        source = auth["source_status"]
        self.assertEqual(source["source_tire_id"], "HOOSIER_43105_18X7.5-10_R25B")
        self.assertEqual(source["intended_tire_id"], "HOOSIER_43104_18X7.5-10_R20")
        self.assertEqual(
            source["current_full_curve_status"],
            "blocked_pending_binary_processed_Trojan_execution_and_review",
        )
        self.assertIn("not sufficient", source["current_summary_limitation"])
        self.assertIn("synthetic Trojan-shaped arrays", source["current_export_limitation"])
        self.assertIn("must remain disabled", source["r25b_activation_rule"])

    def test_no_curve_reconstruction_or_hidden_repair_is_authorized(self) -> None:
        auth = _load("authorizations/tire/AUTH-TIRE-0001.toml")
        curve = auth["curve_contract"]
        for phrase in (
            "No smoothing",
            "odd-symmetry completion",
            "post-peak invention",
        ):
            self.assertIn(phrase, curve["source_preservation_rule"])
        numerics = auth["numerics"]
        for key in (
            "least_squares_allowed",
            "regularization_allowed",
            "smoothing_allowed",
            "implicit_symmetry_allowed",
            "nearest_neighbor_repair_allowed",
            "force_or_slip_clipping_allowed",
        ):
            self.assertFalse(numerics[key])
        prohibited = "\n".join(auth["prohibited"]["items"]).lower()
        for phrase in (
            "summary grid alone",
            "odd symmetry",
            "magic formula",
            "2/3",
            "combined slip",
            "vehicle equilibrium",
        ):
            self.assertIn(phrase, prohibited)

    def test_registry_records_and_source_contract_are_consistent(self) -> None:
        auth = _load("authorizations/tire/AUTH-TIRE-0001.toml")
        model = _load("registry/records/models/MOD-TIRE-0001.toml")["record"]
        self.assertEqual(model["authorization_id"], "AUTH-TIRE-0001")
        self.assertEqual(model["equation_ids"], auth["scope"]["equation_ids"])
        self.assertEqual(model["benchmark_ids"], auth["scope"]["benchmark_ids"])
        for equation_id in model["equation_ids"]:
            equation = _load(f"registry/records/equations/{equation_id}.toml")["record"]
            self.assertEqual(equation["type"], "equation")
        for benchmark_id in model["benchmark_ids"]:
            benchmark = _load(f"registry/records/benchmarks/{benchmark_id}.toml")["record"]
            self.assertIn("MOD-TIRE-0001", benchmark["target_ids"])
        source = _load("data_catalog/shared_steady_state_lateral_tire_v0.toml")
        self.assertEqual(source["record_id"], "SHARED_STEADY_STATE_LATERAL_TIRE_V0")
        self.assertEqual(source["authorization_id"], "AUTH-TIRE-0001")
        self.assertEqual(source["model_id"], "MOD-TIRE-0001")
        self.assertFalse(source["fidelity"]["real_r25b_curve_provider_active"])
        self.assertFalse(source["fidelity"]["combined_slip_complete"])

    def test_failure_and_promotion_gates_are_explicit(self) -> None:
        auth = _load("authorizations/tire/AUTH-TIRE-0001.toml")
        codes = auth["failure_behavior"]["codes"]
        for code in (
            "slip_out_of_domain",
            "operating_state_out_of_domain",
            "interpolation_cell_incomplete",
            "derivative_nonunique",
            "force_demand_out_of_domain",
            "source_specific_activation_blocked",
        ):
            self.assertIn(code, codes)
        gates = "\n".join(auth["promotion_gates"]["items"]).lower()
        for phrase in (
            "processed cornering trojan",
            "source-to-canonical adapter",
            "separately authorize mz",
            "separately authorize fx and combined slip",
            "physical correlation",
        ):
            self.assertIn(phrase, gates)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import math
from pathlib import Path
import tempfile
import tomllib
import unittest

from pssd_tire.r25b_runtime import (
    DEFAULT_R25B_RUNTIME_AUTHORIZATION,
    DEFAULT_R25B_SOURCE_NATIVE_MANIFEST,
    R25B_CANONICAL_SOURCE_CONVENTION_ID,
    R25B_PRESSURE_BASIS,
    R25B_RUNTIME_ADAPTER_ID,
    R25B_RUNTIME_AUTHORIZATION_ID,
    SOURCE_SPECIFIC_R25B_RUNTIME_ACTIVATION_AUTHORIZED,
    evaluate_r25b_steady_state_lateral,
    load_r25b_steady_state_lateral_table,
    require_r25b_runtime_activation,
)
from pssd_tire.r25b_source_native import load_r25b_source_native_exchange
from pssd_tire.steady_state_lateral import (
    SteadyStateLateralFailure,
    SteadyStateLateralOperatingState,
)


class R25bRuntimeProviderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = load_r25b_source_native_exchange(
            DEFAULT_R25B_SOURCE_NATIVE_MANIFEST
        )
        cls.table = load_r25b_steady_state_lateral_table()

    def test_authorization_records_gauge_as_interpretation_not_source_fact(self) -> None:
        with DEFAULT_R25B_RUNTIME_AUTHORIZATION.open("rb") as stream:
            authorization = tomllib.load(stream)
        self.assertEqual(authorization["authorization_id"], R25B_RUNTIME_AUTHORIZATION_ID)
        self.assertEqual(authorization["status"], "reviewed")
        self.assertTrue(authorization["implementation_authorized"])
        decision = authorization["review_decision"]
        self.assertEqual(decision["pressure_basis"], "gauge")
        self.assertEqual(
            decision["pressure_basis_source_type"],
            "reviewer_authorized_engineering_interpretation",
        )
        self.assertFalse(decision["pressure_basis_is_source_stated_fact"])
        self.assertFalse(decision["source_documentation_found"])

    def test_runtime_activation_is_authorized_and_validated(self) -> None:
        self.assertTrue(SOURCE_SPECIFIC_R25B_RUNTIME_ACTIVATION_AUTHORIZED)
        self.assertEqual(R25B_PRESSURE_BASIS, "gauge")
        require_r25b_runtime_activation()

    def test_complete_exact_exchange_is_adapted_without_row_loss(self) -> None:
        self.assertEqual(len(self.source.curves), 60)
        self.assertEqual(self.source.sample_count, 9630)
        self.assertEqual(len(self.table.curves), 60)
        self.assertEqual(sum(len(curve.slip_angle_rad) for curve in self.table.curves), 9630)
        self.assertEqual(len({curve.state_key for curve in self.table.curves}), 60)
        self.assertTrue(all(curve.adapter_id == R25B_RUNTIME_ADAPTER_ID for curve in self.table.curves))
        self.assertTrue(all(not curve.segment_branch_ids for curve in self.table.curves))

    def test_sample_sign_units_and_identity_transform_are_exact(self) -> None:
        source_curve = self.source.curves[0]
        canonical_curve = self.table.curves[0]
        self.assertEqual(canonical_curve.source_tire_id, self.source.source_tire_id)
        self.assertEqual(canonical_curve.intended_tire_id, self.source.intended_tire_id)
        self.assertAlmostEqual(
            canonical_curve.inclination_rad,
            math.radians(source_curve.inclination_deg),
            places=15,
        )
        self.assertAlmostEqual(
            canonical_curve.pressure_Pa,
            1000.0 * source_curve.pressure_kpa,
            places=12,
        )
        for index in (0, len(source_curve.source_slip_angle_deg) // 2, -1):
            self.assertAlmostEqual(
                canonical_curve.slip_angle_rad[index],
                math.radians(source_curve.source_slip_angle_deg[index]),
                places=15,
            )
            self.assertEqual(
                canonical_curve.lateral_force_N[index],
                -source_curve.source_lateral_force_n[index],
            )
        self.assertIn(
            "pressure_basis_is_not_source_stated_fact",
            canonical_curve.domain_and_censor_metadata,
        )

    def test_all_states_have_positive_local_canonical_slope(self) -> None:
        for curve in self.table.curves:
            for index, (left, right) in enumerate(
                zip(curve.slip_angle_rad, curve.slip_angle_rad[1:])
            ):
                if left <= 0.0 <= right:
                    slope = (
                        curve.lateral_force_N[index + 1]
                        - curve.lateral_force_N[index]
                    ) / (right - left)
                    self.assertGreater(slope, 0.0, curve.curve_id)
                    break
            else:
                self.fail(f"zero slip not bracketed by {curve.curve_id}")

    def test_exact_knot_evaluation_recovers_adapted_source_force(self) -> None:
        curve = self.table.curves[17]
        sample_index = len(curve.slip_angle_rad) // 3
        state = SteadyStateLateralOperatingState(
            slip_angle_rad=curve.slip_angle_rad[sample_index],
            normal_load_N=curve.normal_load_N,
            inclination_rad=curve.inclination_rad,
            pressure_Pa=curve.pressure_Pa,
            state_id="R25B_EXACT_KNOT",
            source_id=curve.source_tire_id,
            source_convention_id=R25B_CANONICAL_SOURCE_CONVENTION_ID,
        )
        response = evaluate_r25b_steady_state_lateral(state, table=self.table)
        self.assertTrue(response.ok)
        self.assertTrue(response.exact_knot)
        self.assertEqual(response.lateral_force_N, curve.lateral_force_N[sample_index])
        self.assertEqual(response.participating_curve_ids, (curve.curve_id,))

    def test_complete_cell_interpolation_is_available_and_bounded(self) -> None:
        state = SteadyStateLateralOperatingState(
            slip_angle_rad=0.0,
            normal_load_N=333.5,
            inclination_rad=math.radians(1.0),
            pressure_Pa=62_050.0,
            state_id="R25B_INTERIOR_CELL",
            source_id=self.source.source_tire_id,
            source_convention_id=R25B_CANONICAL_SOURCE_CONVENTION_ID,
        )
        response = evaluate_r25b_steady_state_lateral(state, table=self.table)
        self.assertTrue(response.ok)
        self.assertEqual(len(response.participating_curve_ids), 8)
        self.assertAlmostEqual(
            sum(weight for _, weight in response.state_interpolation_weights),
            1.0,
            places=14,
        )
        self.assertTrue(math.isfinite(response.lateral_force_N))

        outside = SteadyStateLateralOperatingState(
            slip_angle_rad=0.0,
            normal_load_N=333.5,
            inclination_rad=math.radians(1.0),
            pressure_Pa=40_000.0,
            state_id="R25B_OUTSIDE_CELL",
            source_id=self.source.source_tire_id,
            source_convention_id=R25B_CANONICAL_SOURCE_CONVENTION_ID,
        )
        with self.assertRaises(SteadyStateLateralFailure) as context:
            evaluate_r25b_steady_state_lateral(outside, table=self.table)
        self.assertEqual(context.exception.failure_code, "operating_state_out_of_domain")

    def test_authorization_tampering_fails_closed(self) -> None:
        text = DEFAULT_R25B_RUNTIME_AUTHORIZATION.read_text(encoding="utf-8")
        tampered = text.replace(
            'pressure_basis = "gauge"',
            'pressure_basis = "absolute"',
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "AUTH-TIRE-0002.toml"
            path.write_text(tampered, encoding="utf-8")
            with self.assertRaises(SteadyStateLateralFailure) as context:
                require_r25b_runtime_activation(path)
        self.assertEqual(context.exception.failure_code, "source_adapter_mismatch")


if __name__ == "__main__":
    unittest.main()

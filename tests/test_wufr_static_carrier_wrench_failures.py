from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
import tempfile
import unittest

from pssd_vehicle.wufr_static_carrier_wrench import (
    WUFRStaticCarrierWrenchError,
    WUFRStaticCarrierWrenchConfig,
    WUFRStaticCarrierWrenchFailureCode,
    evaluate_wufr_static_carrier_wrenches,
    load_accepted_static_equilibrium_record,
    load_wufr_static_carrier_wrench_provider,
)


ROOT = Path(__file__).resolve().parents[1]


def _provider():
    return load_wufr_static_carrier_wrench_provider(
        source_path=ROOT / "data_catalog/wufr27_static_carrier_wrench_v0.toml",
        static_equilibrium_result_path=ROOT / "benchmarks/vehicle/wufr_static_equilibrium_result_v0.2.0.json",
        static_equilibrium_source_path=ROOT / "data_catalog/wufr27_static_equilibrium_composition_v1.toml",
        road_contact_source_path=ROOT / "data_catalog/wufr26_road_contact_reference_v0.toml",
        suspension_geometry_path=ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml",
        wheel_profile_path=ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml",
        steering_geometry_path=ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml",
        whole_vehicle_path=ROOT / "data_catalog/wufr26_whole_vehicle_frame_v0.toml",
        gravity_path=ROOT / "data_catalog/wufr27_static_gravity_allocation_v0.toml",
        spring_package_path=ROOT / "data_catalog/wufr27_spring_package_v0.toml",
        zbar_fixture_path=ROOT / "benchmarks/suspension/WUFR26_ZBAR_MECHANISM_V0.toml",
    )


class WufrStaticCarrierWrenchFailureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.provider = _provider()

    def test_unsuccessful_upstream_result_fails_closed(self) -> None:
        result = evaluate_wufr_static_carrier_wrenches(
            replace(
                self.provider,
                accepted_result=replace(self.provider.accepted_result, primary_ok=False),
            )
        )
        self.assertFalse(result.ok)
        self.assertEqual(
            result.failure_code,
            WUFRStaticCarrierWrenchFailureCode.UPSTREAM_RESULT_FAILURE,
        )
        self.assertFalse(result.complete_for_authorized_static_gravity_case)

    def test_negative_reaction_is_not_clipped_or_reordered(self) -> None:
        reactions = list(self.provider.accepted_result.road_reactions_N)
        reactions[1] = -0.01
        result = evaluate_wufr_static_carrier_wrenches(
            replace(
                self.provider,
                accepted_result=replace(
                    self.provider.accepted_result,
                    road_reactions_N=tuple(reactions),
                ),
            )
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WUFRStaticCarrierWrenchFailureCode.NEGATIVE_REACTION)
        self.assertFalse(result.hidden_balancing_wrench_used)

    def test_nonfinite_reaction_fails_as_structured_invalid_load(self) -> None:
        reactions = list(self.provider.accepted_result.road_reactions_N)
        reactions[0] = math.nan
        result = evaluate_wufr_static_carrier_wrenches(
            replace(
                self.provider,
                accepted_result=replace(
                    self.provider.accepted_result,
                    road_reactions_N=tuple(reactions),
                ),
            )
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WUFRStaticCarrierWrenchFailureCode.NONFINITE_INPUT)

    def test_wrong_upstream_result_label_is_source_mismatch(self) -> None:
        result = evaluate_wufr_static_carrier_wrenches(
            replace(
                self.provider,
                accepted_result=replace(
                    self.provider.accepted_result,
                    result_label="wrong_result_label",
                ),
            )
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WUFRStaticCarrierWrenchFailureCode.SOURCE_MISMATCH)

    def test_incomplete_static_road_reaction_is_rejected(self) -> None:
        result = evaluate_wufr_static_carrier_wrenches(
            replace(
                self.provider,
                accepted_result=replace(
                    self.provider.accepted_result,
                    complete_static_road_reaction=False,
                ),
            )
        )
        self.assertFalse(result.ok)
        self.assertEqual(
            result.failure_code,
            WUFRStaticCarrierWrenchFailureCode.UPSTREAM_RESULT_FAILURE,
        )

    def test_reordered_wheel_coordinate_contract_is_rejected(self) -> None:
        result = evaluate_wufr_static_carrier_wrenches(
            replace(
                self.provider,
                accepted_result=replace(
                    self.provider.accepted_result,
                    wheel_coordinate_order=(
                        "front_right",
                        "front_left",
                        "rear_left",
                        "rear_right",
                    ),
                ),
            )
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WUFRStaticCarrierWrenchFailureCode.SOURCE_MISMATCH)

    def test_altered_prototype_unsprung_mass_is_rejected(self) -> None:
        gravity = self.provider.equilibrium_provider.gravity
        masses = list(gravity.unsprung)
        masses[0] = replace(masses[0], mass_kg=5.1)
        altered_equilibrium = replace(
            self.provider.equilibrium_provider,
            gravity=replace(gravity, unsprung=tuple(masses)),
        )
        result = evaluate_wufr_static_carrier_wrenches(
            replace(self.provider, equilibrium_provider=altered_equilibrium)
        )
        self.assertFalse(result.ok)
        self.assertEqual(
            result.failure_code,
            WUFRStaticCarrierWrenchFailureCode.GRAVITY_SOURCE_MISMATCH,
        )

    def test_round_trip_above_declared_tolerance_fails_without_identity_fallback(self) -> None:
        result = evaluate_wufr_static_carrier_wrenches(
            replace(
                self.provider,
                config=WUFRStaticCarrierWrenchConfig(
                    wrench_transport_tolerance_N=1.0e-16,
                    wrench_transport_tolerance_Nm=1.0e-16,
                ),
            )
        )
        self.assertFalse(result.ok)
        self.assertEqual(
            result.failure_code,
            WUFRStaticCarrierWrenchFailureCode.ROUND_TRIP_FAILURE,
        )
        self.assertFalse(result.hidden_balancing_wrench_used)

    def test_changed_physical_point_is_rejected(self) -> None:
        points = list(self.provider.accepted_result.contact_points_road_m)
        points[2] = (points[2][0], points[2][1] + 1.0e-5, points[2][2])
        result = evaluate_wufr_static_carrier_wrenches(
            replace(
                self.provider,
                accepted_result=replace(
                    self.provider.accepted_result,
                    contact_points_road_m=tuple(points),
                ),
            )
        )
        self.assertFalse(result.ok)
        self.assertEqual(
            result.failure_code,
            WUFRStaticCarrierWrenchFailureCode.PHYSICAL_POINT_MISMATCH,
        )

    def test_frame_identity_mismatch_is_not_treated_as_implicit_identity(self) -> None:
        result = evaluate_wufr_static_carrier_wrenches(
            replace(
                self.provider,
                source=replace(self.provider.source, road_frame_id="wrong_road_frame"),
            )
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WUFRStaticCarrierWrenchFailureCode.FRAME_MISMATCH)

    def test_changed_accepted_closure_returns_reconstruction_failure(self) -> None:
        result = evaluate_wufr_static_carrier_wrenches(
            replace(
                self.provider,
                accepted_result=replace(
                    self.provider.accepted_result,
                    physical_closure_moment_Nm=(0.0, 1.0, 0.0),
                ),
            )
        )
        self.assertFalse(result.ok)
        self.assertEqual(
            result.failure_code,
            WUFRStaticCarrierWrenchFailureCode.RECONSTRUCTION_FAILURE,
        )
        self.assertFalse(result.hidden_balancing_wrench_used)

    def test_reordered_physical_point_keys_are_rejected_by_record_loader(self) -> None:
        document = json.loads(
            (ROOT / "benchmarks/vehicle/wufr_static_equilibrium_result_v0.2.0.json").read_text(
                encoding="utf-8"
            )
        )
        original = document["primary"]["physical_points"]
        document["primary"]["physical_points"] = {
            "front_right": original["front_right"],
            "front_left": original["front_left"],
            "rear_left": original["rear_left"],
            "rear_right": original["rear_right"],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaises(WUFRStaticCarrierWrenchError) as raised:
                load_accepted_static_equilibrium_record(path)
        self.assertEqual(
            raised.exception.code,
            WUFRStaticCarrierWrenchFailureCode.CORNER_CONTRACT_MISMATCH,
        )


if __name__ == "__main__":
    unittest.main()

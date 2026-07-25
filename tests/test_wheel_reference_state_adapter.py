from __future__ import annotations

import math
from pathlib import Path
import tomllib
import unittest
from unittest.mock import patch

from pssd_suspension import (
    Axle,
    AxleWheelReferenceSource,
    KinematicsStatus,
    PhysicalStateResult,
    PhysicalStateSolverConfig,
    Side,
    SuspensionCornerStateResult,
    UprightReferenceTransform,
    WheelReferenceError,
    WheelReferenceFailureCode,
    WheelReferenceSourceProfile,
    WheelReferenceState,
    WheelReferenceStatus,
    build_nominal_wheel_reference,
    load_optimumk_geometry_snapshot,
    load_wufr26_wheel_reference_profile,
    minimum_twist_upright_transform,
    reconstruct_source_steering_twist,
    remove_source_steering_from_point,
    solve_body_vertical_displacement,
    solve_wheel_reference_state,
    transport_wheel_reference,
)

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml"
SOURCE_3D_PATHS = (
    ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_HEAVE_FRONT_LEFT_WHEEL_REFERENCE_SOURCE_V0.toml",
    ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_HEAVE_FRONT_RIGHT_WHEEL_REFERENCE_SOURCE_V0.toml",
)
KINEMATICS_PATH = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_HEAVE_FRONT_KINEMATICS_V0.toml"
GEOMETRY_PATH = ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"


def _load(path: Path) -> dict:
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _recover_twists(source: dict) -> list[float]:
    nominal = source["nominal"]
    recovered_values: list[float] = []
    for state in source["states"]:
        transform = minimum_twist_upright_transform(
            tuple(nominal["lower_m"]), tuple(nominal["upper_m"]),
            tuple(state["lower_m"]), tuple(state["upper_m"]),
        )
        recovered = reconstruct_source_steering_twist(
            transform, tuple(nominal["tie_m"]), tuple(state["lower_m"]),
            tuple(state["upper_m"]), tuple(state["tie_m"]),
        )
        if not recovered.ok or recovered.twist_rad is None:
            raise AssertionError(recovered.message)
        recovered_values.append(recovered.twist_rad)
    return recovered_values


class NominalWheelReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = load_wufr26_wheel_reference_profile(PROFILE_PATH)
        self.fixture = _load(PROFILE_PATH)

    def test_bench_susp_0004_nominal_centers_and_plane_basis(self) -> None:
        rows = {(row["axle"], row["side"]): row for row in self.fixture["nominal_expected"]}
        center_tol = self.fixture["tolerances"]["nominal_wheel_center_m"]
        plane_tol = self.fixture["tolerances"]["nominal_plane_component"]
        for axle in Axle:
            for side in Side:
                reference = build_nominal_wheel_reference(self.profile, axle, side)
                expected = rows[(axle.value, side.value)]
                for got, want in zip(reference.center_m, expected["wheel_center_m"]):
                    self.assertLessEqual(abs(got - want), center_tol)
                for got, want in zip(reference.forward_reference, expected["forward_reference"]):
                    self.assertLessEqual(abs(got - want), plane_tol)
                for got, want in zip(reference.plane_normal, expected["plane_normal"]):
                    self.assertLessEqual(abs(got - want), plane_tol)
                self.assertEqual(reference.source_profile_id, self.fixture["fixture_id"])
                self.assertEqual(reference.source_authority, self.fixture["authority"])

    def test_nonzero_source_offsets_are_rejected(self) -> None:
        bad_front = AxleWheelReferenceSource(
            half_track_m=self.profile.front.half_track_m,
            static_camber_rad=self.profile.front.static_camber_rad,
            static_toe_out_rad=self.profile.front.static_toe_out_rad,
            tire_radius_m=self.profile.front.tire_radius_m,
            longitudinal_offset_m=0.001,
        )
        bad = WheelReferenceSourceProfile(
            fixture_id="bad", authority="test_only", source_setup="synthetic",
            source_result="synthetic", front=bad_front, rear=self.profile.rear,
        )
        with self.assertRaises(WheelReferenceError):
            build_nominal_wheel_reference(bad, Axle.FRONT, Side.LEFT)

    def test_front_transport_uses_unresolved_minimum_twist_transform(self) -> None:
        nominal = build_nominal_wheel_reference(self.profile, Axle.FRONT, Side.LEFT)
        identity = UprightReferenceTransform(
            rotation=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            translation_m=(0.0, 0.0, 0.0), source_role="minimum_twist_zero_steer_reference",
        )
        intentionally_wrong_final = UprightReferenceTransform(
            rotation=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            translation_m=(0.1, 0.2, 0.3), source_role="should_not_be_used_for_front",
        )
        upstream = SuspensionCornerStateResult(
            axle=Axle.FRONT, side=Side.LEFT, requested_q_L_rad=0.0,
            status=KinematicsStatus.SUCCESS, minimum_twist_transform=identity,
            upright_transform=intentionally_wrong_final,
        )
        result = transport_wheel_reference(nominal, upstream)
        self.assertTrue(result.ok)
        self.assertEqual(result.current_center_m, nominal.center_m)
        self.assertEqual(result.transform_role, "front_minimum_twist_unresolved_steering")


class SourceSteeringRemovalTests(unittest.TestCase):
    def test_bench_susp_0005_recovers_both_front_3d_twists_and_unsteers_wheel_centers(self) -> None:
        recovered_by_side: dict[str, list[float]] = {}
        for source_path in SOURCE_3D_PATHS:
            source = _load(source_path)
            nominal = source["nominal"]
            point_tol = source["tolerances"]["source_unsteer_point_m"]
            twist_tol = source["tolerances"]["reconstructed_twist_rad"]
            recovered_values: list[float] = []
            max_point_error = 0.0
            max_twist_error = 0.0
            for state in source["states"]:
                transform = minimum_twist_upright_transform(
                    tuple(nominal["lower_m"]), tuple(nominal["upper_m"]),
                    tuple(state["lower_m"]), tuple(state["upper_m"]),
                )
                recovered = reconstruct_source_steering_twist(
                    transform, tuple(nominal["tie_m"]), tuple(state["lower_m"]),
                    tuple(state["upper_m"]), tuple(state["tie_m"]),
                )
                self.assertTrue(recovered.ok, recovered.message)
                self.assertFalse(recovered.scalar_steer_angle_used_as_rotation)
                assert recovered.twist_rad is not None
                recovered_values.append(recovered.twist_rad)
                max_twist_error = max(
                    max_twist_error,
                    abs(recovered.twist_rad - math.radians(state["expected_twist_deg"])),
                )
                unsteered_wc = remove_source_steering_from_point(
                    tuple(state["wheel_center_m"]), tuple(state["lower_m"]),
                    tuple(state["upper_m"]), recovered.twist_rad,
                )
                reference_wc = transform.apply_point(tuple(nominal["wheel_center_m"]))
                max_point_error = max(max_point_error, _distance(unsteered_wc, reference_wc))
            self.assertLessEqual(max_point_error, point_tol)
            self.assertLessEqual(max_twist_error, twist_tol)
            recovered_by_side[source["corner"]] = recovered_values

        bilateral_tol = _load(PROFILE_PATH)["tolerances"]["bilateral_twist_sum_rad"]
        left = recovered_by_side["front_left"]
        right = recovered_by_side["front_right"]
        self.assertEqual(len(left), len(right))
        self.assertLessEqual(max(abs(l + r) for l, r in zip(left, right)), bilateral_tol)

    def test_scalar_steer_angle_is_not_3d_twist_on_either_front_corner(self) -> None:
        for source_path in SOURCE_3D_PATHS:
            source = _load(source_path)
            endpoint = source["states"][0]
            self.assertGreater(
                abs(endpoint["scalar_steer_angle_deg"] - endpoint["expected_twist_deg"]), 0.08
            )
            nominal_state = min(source["states"], key=lambda state: abs(state["heave_mm"]))
            self.assertAlmostEqual(nominal_state["expected_twist_deg"], 0.0, places=9)
            self.assertGreater(abs(nominal_state["scalar_steer_angle_deg"]), 7e-4)


class PhysicalStateInversionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = load_wufr26_wheel_reference_profile(PROFILE_PATH)
        self.geometry = load_optimumk_geometry_snapshot(GEOMETRY_PATH)
        self.corner = self.geometry.corner(Axle.FRONT, Side.RIGHT)
        self.nominal = build_nominal_wheel_reference(self.profile, Axle.FRONT, Side.RIGHT)
        source = _load(KINEMATICS_PATH)
        q_values = [math.radians(state["q_L_deg"]) for state in source["states"]]
        self.domain = PhysicalStateSolverConfig(
            q_L_min_rad=min(q_values) - math.radians(0.15),
            q_L_max_rad=max(q_values) + math.radians(0.15),
            scan_intervals_per_side=30, q_L_tolerance_rad=2e-9,
            displacement_tolerance_m=2e-9,
        )
        self.source_states = source["states"]

    def test_bench_susp_0006_nominal_request_recovers_zero(self) -> None:
        result = solve_body_vertical_displacement(
            self.corner, self.nominal, 0.0, self.domain,
            geometry_id=self.geometry.geometry_id,
            configuration_id="WUFR27_SUSPENSION_BASELINE_V0",
            source_authority=self.geometry.authority,
        )
        self.assertTrue(result.ok, result.message)
        self.assertAlmostEqual(result.q_L_rad or 0.0, 0.0, places=12)
        self.assertIsNotNone(result.wheel_state)
        self.assertEqual(result.wheel_state.transform_role, "front_minimum_twist_unresolved_steering")

    def test_bench_susp_0006_recovers_selected_wufr_q_l_states(self) -> None:
        for index in (0, 2, 8, 10):
            expected_q = math.radians(self.source_states[index]["q_L_deg"])
            forward = solve_wheel_reference_state(
                self.corner, self.nominal, expected_q,
                geometry_id=self.geometry.geometry_id,
                configuration_id="WUFR27_SUSPENSION_BASELINE_V0",
                source_authority=self.geometry.authority,
            )
            self.assertTrue(forward.ok, forward.message)
            assert forward.delta_z_wc_body_m is not None
            inverse = solve_body_vertical_displacement(
                self.corner, self.nominal, forward.delta_z_wc_body_m, self.domain,
                geometry_id=self.geometry.geometry_id,
                configuration_id="WUFR27_SUSPENSION_BASELINE_V0",
                source_authority=self.geometry.authority,
            )
            self.assertTrue(inverse.ok, inverse.message)
            self.assertLessEqual(abs((inverse.q_L_rad or 0.0) - expected_q), 2e-7)
            self.assertLessEqual(abs(inverse.residual_m or 0.0), self.domain.displacement_tolerance_m)

    def test_outside_reachable_domain_fails_without_clipping(self) -> None:
        result = solve_body_vertical_displacement(
            self.corner, self.nominal, 0.2, self.domain,
            geometry_id=self.geometry.geometry_id,
            configuration_id="WUFR27_SUSPENSION_BASELINE_V0",
            source_authority=self.geometry.authority,
        )
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WheelReferenceFailureCode.REQUEST_OUTSIDE_REACHABLE_DOMAIN)
        self.assertIsNone(result.q_L_rad)

    def test_nonmonotonic_sample_mapping_is_rejected_as_ambiguous(self) -> None:
        def sample(q: float, dz: float) -> WheelReferenceState:
            return WheelReferenceState(
                axle=Axle.FRONT, side=Side.RIGHT, status=WheelReferenceStatus.SUCCESS,
                nominal=self.nominal, q_L_rad=q, delta_z_wc_body_m=dz,
            )
        synthetic = (
            sample(-0.1, -0.01), sample(-0.05, 0.005), sample(0.0, 0.0),
            sample(0.05, 0.005), sample(0.1, -0.01),
        )
        with patch("pssd_suspension.wheel_reference._branch_samples", return_value=synthetic):
            result = solve_body_vertical_displacement(self.corner, self.nominal, 0.002, self.domain)
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WheelReferenceFailureCode.AMBIGUOUS_MAPPING)

    def test_upstream_failure_is_propagated(self) -> None:
        failure = PhysicalStateResult(
            status=WheelReferenceStatus.FAILURE, requested_delta_z_wc_body_m=math.nan,
            failure_code=WheelReferenceFailureCode.UPSTREAM_KINEMATICS_FAILURE,
            message="synthetic upstream failure",
        )
        with patch("pssd_suspension.wheel_reference._branch_samples", return_value=failure):
            result = solve_body_vertical_displacement(self.corner, self.nominal, 0.001, self.domain)
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, WheelReferenceFailureCode.UPSTREAM_KINEMATICS_FAILURE)
        self.assertIn("synthetic upstream failure", result.message)


if __name__ == "__main__":
    unittest.main()

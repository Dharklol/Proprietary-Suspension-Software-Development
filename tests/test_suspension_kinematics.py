from __future__ import annotations

import math
from pathlib import Path
import tomllib
import unittest

from pssd_suspension import (
    ActuationAttachment,
    ActuationGeometry,
    Axle,
    DoubleWishboneGeometry,
    KinematicsFailureCode,
    KinematicsSolverConfig,
    KinematicsStatus,
    Side,
    SuspensionCornerGeometry,
    SuspensionKinematicsError,
    SuspensionPoint,
    ToeLinkGeometry,
    ToeLinkRole,
    UprightReferenceTransform,
    WheelSetup,
    load_optimumk_geometry_snapshot,
    minimum_twist_upright_transform,
    solve_corner_state,
    solve_corner_sweep,
    solve_rear_toe_twist,
)


ROOT = Path(__file__).resolve().parents[1]


def _load(relative: str) -> dict:
    with (ROOT / relative).open("rb") as stream:
        return tomllib.load(stream)


def _point(name: str, value: tuple[float, float, float]) -> SuspensionPoint:
    return SuspensionPoint(source_name=name, source_position_mm=value, position_m=value)


def _dummy_actuation() -> ActuationGeometry:
    p = _point("dummy", (0.0, 0.0, 0.0))
    return ActuationGeometry(
        outboard_attachment=p,
        chassis_attachment=p,
        rocker_axis_reference=p,
        rocker_pivot=p,
        rocker_rod_point=p,
        rocker_coil_point=p,
        attachment=ActuationAttachment.LOWER_ARM,
    )


def _wheel_setup() -> WheelSetup:
    return WheelSetup(
        half_track_m=0.6,
        longitudinal_offset_m=0.0,
        lateral_offset_m=0.0,
        vertical_offset_m=0.0,
        static_camber_deg=0.0,
        static_toe_deg=0.0,
        rim_diameter_m=0.254,
        tire_diameter_m=0.46,
        tire_width_m=0.19,
    )


def _parallel_corner() -> SuspensionCornerGeometry:
    wishbone = DoubleWishboneGeometry(
        lower_fore_inboard=_point("lf", (0.0, 0.0, 0.0)),
        lower_aft_inboard=_point("la", (1.0, 0.0, 0.0)),
        upper_fore_inboard=_point("uf", (0.0, 0.0, 0.2)),
        upper_aft_inboard=_point("ua", (1.0, 0.0, 0.2)),
        lower_upright=_point("lj", (0.0, 0.4, 0.0)),
        upper_upright=_point("uj", (0.0, 0.4, 0.2)),
    )
    return SuspensionCornerGeometry(
        axle=Axle.FRONT,
        side=Side.LEFT,
        wishbone=wishbone,
        toe_link=ToeLinkGeometry(
            inboard=_point("ti", (0.0, 0.0, 0.1)),
            outboard=_point("to", (0.0, 0.4, 0.1)),
            role=ToeLinkRole.STEERING_TIE_ROD,
        ),
        actuation=_dummy_actuation(),
        wheel_setup=_wheel_setup(),
    )


def _rear_toe_corner() -> SuspensionCornerGeometry:
    wishbone = DoubleWishboneGeometry(
        lower_fore_inboard=_point("lf", (0.0, -0.2, 0.0)),
        lower_aft_inboard=_point("la", (1.0, -0.2, 0.0)),
        upper_fore_inboard=_point("uf", (0.0, -0.2, 0.2)),
        upper_aft_inboard=_point("ua", (1.0, -0.2, 0.2)),
        lower_upright=_point("lj", (0.0, 0.0, 0.0)),
        upper_upright=_point("uj", (0.0, 0.0, 0.2)),
    )
    return SuspensionCornerGeometry(
        axle=Axle.REAR,
        side=Side.LEFT,
        wishbone=wishbone,
        toe_link=ToeLinkGeometry(
            inboard=_point("ti", (0.4, 0.0, 0.1)),
            outboard=_point("to", (0.1, 0.0, 0.1)),
            role=ToeLinkRole.CHASSIS_LOCATING_TOE_LINK,
        ),
        actuation=_dummy_actuation(),
        wheel_setup=_wheel_setup(),
    )


class SuspensionKinematicsTests(unittest.TestCase):
    def test_bench_susp_0001_parallel_arms(self) -> None:
        fixture = _load("benchmarks/suspension/GEO-SUSP-BASIC-001.toml")
        states = {state["q_L_deg"]: state for state in fixture["states"]}
        corner = _parallel_corner()
        for branch in ([0.0, 10.0, 20.0], [0.0, -10.0, -20.0]):
            results = solve_corner_sweep(corner, [math.radians(value) for value in branch])
            self.assertEqual(len(results), len(branch))
            for q_deg, result in zip(branch, results):
                self.assertTrue(result.ok, result.message)
                expected = states[q_deg]
                self.assertAlmostEqual(
                    result.q_U_rad or 0.0,
                    math.radians(expected["expected_q_U_deg"]),
                    delta=fixture["tolerances"]["angle_rad"],
                )
                assert result.lower_upright_m is not None
                assert result.upper_upright_m is not None
                for actual, reference in zip(
                    result.lower_upright_m, expected["expected_lower_upright_m"]
                ):
                    self.assertAlmostEqual(actual, reference, delta=fixture["tolerances"]["position_m"])
                for actual, reference in zip(
                    result.upper_upright_m, expected["expected_upper_upright_m"]
                ):
                    self.assertAlmostEqual(actual, reference, delta=fixture["tolerances"]["position_m"])
                self.assertLessEqual(
                    abs(result.upright_separation_residual_m or 0.0),
                    fixture["tolerances"]["length_residual_m"],
                )
                assert result.minimum_twist_transform is not None
                for row, identity_row in zip(
                    result.minimum_twist_transform.rotation,
                    ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
                ):
                    for actual, reference in zip(row, identity_row):
                        self.assertAlmostEqual(
                            actual, reference, delta=fixture["tolerances"]["rotation_matrix"]
                        )

    def test_bench_susp_0002_wufr_front_matches_optimumk(self) -> None:
        geometry = load_optimumk_geometry_snapshot(
            ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"
        )
        corner = geometry.corner(Axle.FRONT, Side.RIGHT)
        fixture = _load(
            "benchmarks/suspension/WUFR26_OPTIMUMK_HEAVE_FRONT_KINEMATICS_V0.toml"
        )
        for state in fixture["states"]:
            result = solve_corner_state(
                corner,
                math.radians(state["q_L_deg"]),
                geometry_id=geometry.geometry_id,
                configuration_id="WUFR27_SUSPENSION_BASELINE_V0",
                source_authority=geometry.authority,
            )
            self.assertTrue(result.ok, result.message)
            assert result.q_U_rad is not None
            assert result.lower_upright_m is not None
            assert result.upper_upright_m is not None
            self.assertAlmostEqual(
                result.q_U_rad,
                math.radians(state["expected_q_U_deg"]),
                delta=fixture["tolerances"]["upper_rotation_rad"],
            )
            for actual, reference in zip(
                result.lower_upright_m, state["expected_lower_upright_m"]
            ):
                self.assertAlmostEqual(
                    actual, reference, delta=fixture["tolerances"]["position_m"]
                )
            for actual, reference in zip(
                result.upper_upright_m, state["expected_upper_upright_m"]
            ):
                self.assertAlmostEqual(
                    actual, reference, delta=fixture["tolerances"]["position_m"]
                )
            self.assertLessEqual(
                abs(result.upright_separation_residual_m or 0.0),
                fixture["tolerances"]["internal_length_residual_m"],
            )
            self.assertEqual(result.geometry_id, geometry.geometry_id)
            self.assertEqual(result.configuration_id, "WUFR27_SUSPENSION_BASELINE_V0")

    def test_bench_susp_0003_rear_toe_twist(self) -> None:
        fixture = _load("benchmarks/suspension/GEO-SUSP-REAR-TOE-001.toml")
        angle = math.radians(-10.0)
        c = math.cos(angle)
        s = math.sin(angle)
        minimum_twist = UprightReferenceTransform(
            rotation=((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0)),
            translation_m=(0.0, 0.0, 0.0),
        )
        root, residual, derivative, transform = solve_rear_toe_twist(
            _rear_toe_corner(),
            minimum_twist,
            current_lower_m=(0.0, 0.0, 0.0),
            current_upper_m=(0.0, 0.0, 0.2),
            config=KinematicsSolverConfig(initial_bracket_step_rad=math.radians(10.0)),
        )
        self.assertTrue(root.ok, root.message)
        assert root.root_rad is not None
        self.assertAlmostEqual(
            root.root_rad,
            math.radians(fixture["expected"]["twist_deg"]),
            delta=fixture["tolerances"]["angle_rad"],
        )
        self.assertAlmostEqual(
            residual or 0.0,
            fixture["expected"]["physical_length_residual_m"],
            delta=fixture["tolerances"]["length_residual_m"],
        )
        self.assertIsNotNone(derivative)
        assert transform is not None
        actual = transform.apply_point((0.1, 0.0, 0.1))
        for value, reference in zip(actual, fixture["expected"]["toe_outboard_m"]):
            self.assertAlmostEqual(value, reference, delta=fixture["tolerances"]["position_m"])

    def test_out_of_domain_is_structured_failure(self) -> None:
        result = solve_corner_state(_parallel_corner(), math.radians(100.0))
        self.assertEqual(result.status, KinematicsStatus.FAILURE)
        self.assertEqual(result.failure_code, KinematicsFailureCode.INPUT_OUTSIDE_DOMAIN)

    def test_unreachable_upper_closure_does_not_select_alternate_root(self) -> None:
        config = KinematicsSolverConfig(
            lower_angle_min_rad=math.radians(-30.0),
            lower_angle_max_rad=math.radians(30.0),
            upper_angle_min_rad=math.radians(-5.0),
            upper_angle_max_rad=math.radians(5.0),
        )
        result = solve_corner_state(_parallel_corner(), math.radians(20.0), config=config)
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, KinematicsFailureCode.NO_CLOSURE_ROOT)

    def test_degenerate_hinge_axis_is_structured_failure(self) -> None:
        corner = _parallel_corner()
        bad = SuspensionCornerGeometry(
            axle=corner.axle,
            side=corner.side,
            wishbone=DoubleWishboneGeometry(
                lower_fore_inboard=corner.wishbone.lower_fore_inboard,
                lower_aft_inboard=corner.wishbone.lower_fore_inboard,
                upper_fore_inboard=corner.wishbone.upper_fore_inboard,
                upper_aft_inboard=corner.wishbone.upper_aft_inboard,
                lower_upright=corner.wishbone.lower_upright,
                upper_upright=corner.wishbone.upper_upright,
            ),
            toe_link=corner.toe_link,
            actuation=corner.actuation,
            wheel_setup=corner.wheel_setup,
        )
        result = solve_corner_state(bad, 0.1)
        self.assertFalse(result.ok)
        self.assertEqual(result.failure_code, KinematicsFailureCode.DEGENERATE_HINGE_AXIS)

    def test_zero_and_antiparallel_kingpin_reference_fail_explicitly(self) -> None:
        with self.assertRaisesRegex(SuspensionKinematicsError, "zero"):
            minimum_twist_upright_transform(
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 1.0),
            )
        with self.assertRaisesRegex(SuspensionKinematicsError, "antiparallel"):
            minimum_twist_upright_transform(
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 1.0),
                (0.0, 0.0, 0.0),
                (0.0, 0.0, -1.0),
            )

    def test_front_steering_tie_rod_is_rejected_by_rear_closure(self) -> None:
        corner = _parallel_corner()
        transform = UprightReferenceTransform(
            rotation=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
            translation_m=(0.0, 0.0, 0.0),
        )
        root, residual, derivative, final_transform = solve_rear_toe_twist(
            corner,
            transform,
            current_lower_m=(0.0, 0.4, 0.0),
            current_upper_m=(0.0, 0.4, 0.2),
        )
        self.assertFalse(root.ok)
        self.assertEqual(root.failure_code, KinematicsFailureCode.INVALID_REAR_TOE_LINK_ROLE)
        self.assertIsNone(residual)
        self.assertIsNone(derivative)
        self.assertIsNone(final_transform)


if __name__ == "__main__":
    unittest.main()

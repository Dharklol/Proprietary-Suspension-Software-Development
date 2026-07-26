from __future__ import annotations

import math
from pathlib import Path
import tempfile
import unittest

from pssd_vehicle.force_coordinates import (
    AppliedWrench,
    BodyPose,
    ContactCornerInput,
    ContactStatus,
    ForceCoordinateError,
    ForceCoordinateFailureCode,
    PointReference,
    RoadPlane,
    analytical_generalized_force,
    assemble_wrenches,
    classify_rigid_four_contact,
    load_wufr_whole_vehicle_adapter,
    numerical_generalized_force,
    road_plane_from_wufr_adapter,
    translate_wrench,
    transport_body_fixed_point,
)


ROOT = Path(__file__).resolve().parents[1]
WUFR_ADAPTER = ROOT / "data_catalog/wufr26_whole_vehicle_frame_v0.toml"


def point(
    point_id: str,
    xyz: tuple[float, float, float],
    *,
    frame: str = "BODY",
    origin: str = "CG",
    fixed_role: str = "body_fixed",
) -> PointReference:
    return PointReference(
        point_id=point_id,
        frame_id=frame,
        origin_id=origin,
        position_m=xyz,
        role="synthetic",
        source_id="BENCH-VEH-0003",
        configuration_id="SYNTHETIC",
        authority="synthetic benchmark",
        fixed_role=fixed_role,
    )


class VehicleForceCoordinateImplementationTests(unittest.TestCase):
    def test_point_transport_identity_and_elemental_rotations(self) -> None:
        p = point("p", (1.0, 2.0, 3.0))
        identity = BodyPose(
            "ROAD",
            "R0",
            "BODY",
            "CG",
            body_origin_position_m=(4.0, 5.0, 6.0),
        )
        got = transport_body_fixed_point(p, identity)
        for value, expected in zip(got.position_m, (5.0, 7.0, 9.0)):
            self.assertAlmostEqual(value, expected, places=14)

        yaw = BodyPose("ROAD", "R0", "BODY", "CG", psi_rad=math.pi / 2.0)
        got_yaw = transport_body_fixed_point(point("x", (1.0, 0.0, 0.0)), yaw)
        self.assertAlmostEqual(got_yaw.position_m[0], 0.0, places=14)
        self.assertAlmostEqual(got_yaw.position_m[1], 1.0, places=14)

        roll = BodyPose("ROAD", "R0", "BODY", "CG", phi_rad=math.pi / 2.0)
        got_roll = transport_body_fixed_point(point("y", (0.0, 1.0, 0.0)), roll)
        self.assertAlmostEqual(got_roll.position_m[1], 0.0, places=14)
        self.assertAlmostEqual(got_roll.position_m[2], 1.0, places=14)

    def test_wrench_translation_sum_and_reference_change(self) -> None:
        app = point(
            "P",
            (2.0, 0.0, 0.0),
            frame="ROAD",
            origin="R0",
            fixed_role="road_fixed",
        )
        origin = point(
            "O",
            (0.0, 0.0, 0.0),
            frame="ROAD",
            origin="R0",
            fixed_role="road_fixed",
        )
        shifted = point(
            "A",
            (0.5, 0.0, 0.0),
            frame="ROAD",
            origin="R0",
            fixed_role="road_fixed",
        )
        action = AppliedWrench(
            "W1",
            "ROAD",
            "R0",
            app,
            force_N=(0.0, 10.0, 0.0),
            free_couple_Nm=(1.0, 2.0, 3.0),
        )
        about_o = translate_wrench(action, origin)
        self.assertEqual(about_o.force_moment_Nm, (0.0, 0.0, 20.0))
        self.assertEqual(about_o.moment_Nm, (1.0, 2.0, 23.0))

        about_a = translate_wrench(action, shifted)
        self.assertEqual(about_a.moment_Nm, (1.0, 2.0, 18.0))

        second = AppliedWrench(
            "W2",
            "ROAD",
            "R0",
            origin,
            force_N=(3.0, -2.0, 1.0),
            free_couple_Nm=(0.5, 0.0, -1.0),
        )
        result = assemble_wrenches((action, second), origin)
        self.assertEqual(result.resultant_force_N, (3.0, 8.0, 1.0))
        self.assertEqual(result.resultant_moment_Nm, (1.5, 2.0, 22.0))

    def test_generalized_force_matches_analytic_and_centered_virtual_work(self) -> None:
        p = point("load", (0.7, -0.35, 0.22))
        pose = BodyPose(
            "ROAD",
            "R0",
            "BODY",
            "CG",
            body_origin_position_m=(1.2, -0.4, 0.3),
            z_s_m=0.04,
            phi_rad=0.13,
            theta_rad=-0.09,
            psi_rad=0.27,
        )
        force = (130.0, -75.0, 410.0)
        couple = (12.0, -7.0, 3.5)
        exact = analytical_generalized_force(
            p,
            pose,
            force_N=force,
            free_couple_Nm=couple,
        )
        numerical = numerical_generalized_force(
            p,
            pose,
            force_N=force,
            free_couple_Nm=couple,
            steps=(1.0e-5, 2.0e-5, 2.0e-5),
            convergence_tolerance=2.0e-7,
        )
        self.assertEqual(exact.coordinate_units, ("N", "N*m", "N*m"))
        self.assertEqual(exact.coordinate_order, ("z_s_m", "phi_rad", "theta_rad"))
        self.assertAlmostEqual(exact.generalized_force[0], force[2], places=12)
        for a, b in zip(exact.generalized_force, numerical.generalized_force):
            self.assertAlmostEqual(a, b, places=7)
        self.assertLessEqual(float(numerical.convergence_error or 0.0), 1.0e-6)
        self.assertEqual(exact.virtual_work_residual, 0.0)

    def test_structured_frame_and_jacobian_failures(self) -> None:
        pose = BodyPose("ROAD", "R0", "BODY", "CG")
        with self.assertRaises(ForceCoordinateError) as frame_error:
            transport_body_fixed_point(
                point("wrong", (0.0, 0.0, 0.0), frame="OTHER"),
                pose,
            )
        self.assertEqual(
            frame_error.exception.code,
            ForceCoordinateFailureCode.FRAME_MISMATCH,
        )

        with self.assertRaises(ForceCoordinateError) as role_error:
            transport_body_fixed_point(
                point("not-fixed", (0.0, 0.0, 0.0), fixed_role="source_local"),
                pose,
            )
        self.assertEqual(
            role_error.exception.code,
            ForceCoordinateFailureCode.MISSING_TRANSFORM_AUTHORITY,
        )

        with self.assertRaises(ForceCoordinateError) as jac_error:
            numerical_generalized_force(
                point("load", (1.0, 0.0, 0.0)),
                pose,
                force_N=(1.0, 2.0, 3.0),
                steps=(1.0e-5, 0.0, 1.0e-6),
            )
        self.assertEqual(
            jac_error.exception.code,
            ForceCoordinateFailureCode.JACOBIAN_UNAVAILABLE,
        )

    def test_contact_gap_sign_four_contact_and_wheel_lift(self) -> None:
        road = RoadPlane(
            "ROAD",
            "R0",
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 1.0),
            "synthetic",
        )
        corners = ("front_left", "front_right", "rear_left", "rear_right")

        valid = classify_rigid_four_contact(
            road,
            tuple(
                ContactCornerInput(
                    corner,
                    point(
                        corner,
                        (0.0, 0.0, 0.0),
                        frame="ROAD",
                        origin="R0",
                        fixed_role="road_fixed",
                    ),
                    normal_reaction_N=100.0 + index,
                )
                for index, corner in enumerate(corners)
            ),
        )
        self.assertTrue(valid.ok)

        above = list(
            ContactCornerInput(
                corner,
                point(
                    corner,
                    (0.0, 0.0, 0.001 if index == 0 else 0.0),
                    frame="ROAD",
                    origin="R0",
                    fixed_role="road_fixed",
                ),
                100.0,
            )
            for index, corner in enumerate(corners)
        )
        opened = classify_rigid_four_contact(road, tuple(above))
        self.assertEqual(opened.status, ContactStatus.OPEN_GAP)
        self.assertGreater(opened.corners[0].gap_m, 0.0)

        below = list(
            ContactCornerInput(
                corner,
                point(
                    corner,
                    (0.0, 0.0, -0.001 if index == 2 else 0.0),
                    frame="ROAD",
                    origin="R0",
                    fixed_role="road_fixed",
                ),
                100.0,
            )
            for index, corner in enumerate(corners)
        )
        penetrated = classify_rigid_four_contact(road, tuple(below))
        self.assertEqual(penetrated.status, ContactStatus.PENETRATION)
        self.assertLess(penetrated.corners[2].gap_m, 0.0)

        lift = classify_rigid_four_contact(
            road,
            tuple(
                ContactCornerInput(
                    corner,
                    point(
                        corner,
                        (0.0, 0.0, 0.0),
                        frame="ROAD",
                        origin="R0",
                        fixed_role="road_fixed",
                    ),
                    -4.0 if corner == "rear_right" else 100.0,
                )
                for corner in corners
            ),
        )
        self.assertEqual(lift.status, ContactStatus.WHEEL_LIFT)
        rr = next(item for item in lift.corners if item.corner_id == "rear_right")
        self.assertEqual(rr.normal_reaction_N, -4.0)
        self.assertEqual(
            rr.failure_code,
            ForceCoordinateFailureCode.NEGATIVE_NORMAL_REACTION,
        )

    def test_unsupported_contact_model_is_explicit(self) -> None:
        road = RoadPlane(
            "ROAD",
            "R0",
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 1.0),
            "synthetic",
            model="curb_contact",
        )
        result = classify_rigid_four_contact(road, ())
        self.assertEqual(result.status, ContactStatus.UNSUPPORTED_CONTACT_MODEL)

    def test_wufr_adapter_freezes_explicit_frame_axles_tracks_and_contact_references(self) -> None:
        adapter = load_wufr_whole_vehicle_adapter(WUFR_ADAPTER)
        self.assertEqual(adapter.configuration_id, "WUFR27_SUSPENSION_BASELINE_V0")
        self.assertFalse(adapter.installed_authority)
        self.assertAlmostEqual(adapter.wheelbase_m, 1.5624, places=12)
        self.assertAlmostEqual(adapter.front_track_m, 1.231972, places=12)
        self.assertAlmostEqual(adapter.rear_track_m, 1.206572, places=12)
        self.assertAlmostEqual(
            adapter.cg_to_front_axle_m,
            0.8516226415094339,
            places=12,
        )
        self.assertAlmostEqual(
            adapter.cg_to_rear_axle_m,
            0.7107773584905661,
            places=12,
        )
        self.assertAlmostEqual(
            adapter.cg_source_position_m[1],
            0.0015043731656184725,
            places=15,
        )
        self.assertAlmostEqual(adapter.cg_source_position_m[2], 0.29, places=12)

        road = road_plane_from_wufr_adapter(adapter)
        self.assertAlmostEqual(road.reference_point_m[2], -0.29, places=12)
        self.assertEqual(
            set(adapter.contact_points_body),
            {"front_left", "front_right", "rear_left", "rear_right"},
        )
        for contact in adapter.contact_points_body.values():
            gap = sum(
                road.normal[index]
                * (contact.position_m[index] - road.reference_point_m[index])
                for index in range(3)
            )
            self.assertAlmostEqual(gap, 0.0, places=14)

    def test_wufr_loader_does_not_accept_wheelbase_only_fixture(self) -> None:
        content = '''\
version = "0.1.0"
adapter_id = "WUFR26_WHOLE_VEHICLE_FRAME_V0"
configuration_id = "WUFR27_SUSPENSION_BASELINE_V0"
source_record_id = "bad"
[frame]
body_frame_id = "B"
body_origin_id = "O"
source_frame_id = "S"
source_origin_id = "SO"
road_frame_id = "R"
road_origin_id = "RO"
[geometry]
wheelbase_m = 1.5624
[cg_reference]
source_position_m = [0.0,0.0,0.0]
[authority_boundaries]
installed_authority = false
whole_vehicle_placement = "missing"
contact_reference = "missing"
[provenance]
source = "synthetic incomplete fixture"
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.toml"
            path.write_text(content, encoding="utf-8")
            with self.assertRaises((KeyError, ForceCoordinateError)):
                load_wufr_whole_vehicle_adapter(path)

    def test_module_exposes_no_linkage_or_equilibrium_solver(self) -> None:
        import pssd_vehicle.force_coordinates as module

        names = set(dir(module))
        self.assertNotIn("solve_equilibrium", names)
        self.assertNotIn("solve_linkage_forces", names)
        self.assertNotIn("spring_force", names)
        self.assertNotIn("arb_force", names)


if __name__ == "__main__":
    unittest.main()

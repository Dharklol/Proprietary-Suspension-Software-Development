from __future__ import annotations

import math
from pathlib import Path
import unittest

from pssd_suspension import (
    ActuationAttachment,
    Axle,
    Side,
    SuspensionGeometryError,
    ToeLinkRole,
    load_optimumk_geometry_snapshot,
)


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data_catalog" / "wufr26_optimumk_suspension_hardpoints_v0.toml"


class SuspensionGeometryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.geometry = load_optimumk_geometry_snapshot(SNAPSHOT)

    def assertPointAlmostEqual(self, actual, expected, places: int = 12) -> None:
        self.assertEqual(len(actual), 3)
        for value, target in zip(actual, expected):
            self.assertAlmostEqual(value, target, places=places)

    def test_source_identity_is_frozen(self) -> None:
        source = self.geometry.source
        self.assertEqual(source.catalog_id, "CAT-SUSP-GEO-0001")
        self.assertEqual(source.file_id, "2014803790843")
        self.assertEqual(source.file_version_id, "2224178574043")
        self.assertEqual(source.provider_sha1, "15eadfb93369192038888da92ebaa6674db56cfa")
        self.assertEqual(source.source_frame_id, "OPTK_WUFR26_EXPORT")
        self.assertIn("not_captured", source.raw_byte_sha256_state)

    def test_four_explicit_corners_are_present(self) -> None:
        self.assertEqual(len(self.geometry.corners), 4)
        for axle in Axle:
            for side in Side:
                self.assertEqual(self.geometry.corner(axle, side).axle, axle)
                self.assertEqual(self.geometry.corner(axle, side).side, side)

    def test_optimumk_to_canonical_orientation_is_explicit(self) -> None:
        front_left = self.geometry.corner(Axle.FRONT, Side.LEFT)
        front_right = self.geometry.corner(Axle.FRONT, Side.RIGHT)
        self.assertPointAlmostEqual(
            front_left.wishbone.lower_upright.position_m,
            (0.0, 0.587096, 0.157117),
        )
        self.assertPointAlmostEqual(
            front_right.wishbone.lower_upright.position_m,
            (0.0, -0.587096, 0.157117),
        )
        self.assertPointAlmostEqual(
            front_left.wishbone.upper_upright.position_m,
            (-0.006487, 0.564662, 0.305056),
        )

    def test_source_coordinates_are_preserved_alongside_canonical(self) -> None:
        point = self.geometry.corner("front", "left").wishbone.lower_fore_inboard
        self.assertPointAlmostEqual(point.source_position_mm, (167.480, -209.065, 120.966), places=9)
        self.assertPointAlmostEqual(point.position_m, (0.167480, 0.209065, 0.120966))

    def test_source_left_right_geometry_is_explicit_not_runtime_mirrored(self) -> None:
        for axle in Axle:
            left = self.geometry.corner(axle, Side.LEFT)
            right = self.geometry.corner(axle, Side.RIGHT)
            left_points = (
                left.wishbone.lower_fore_inboard,
                left.wishbone.lower_aft_inboard,
                left.wishbone.upper_fore_inboard,
                left.wishbone.upper_aft_inboard,
                left.wishbone.lower_upright,
                left.wishbone.upper_upright,
                left.toe_link.inboard,
                left.toe_link.outboard,
            )
            right_points = (
                right.wishbone.lower_fore_inboard,
                right.wishbone.lower_aft_inboard,
                right.wishbone.upper_fore_inboard,
                right.wishbone.upper_aft_inboard,
                right.wishbone.lower_upright,
                right.wishbone.upper_upright,
                right.toe_link.inboard,
                right.toe_link.outboard,
            )
            for lp, rp in zip(left_points, right_points):
                self.assertAlmostEqual(lp.position_m[0], rp.position_m[0], places=12)
                self.assertAlmostEqual(lp.position_m[1], -rp.position_m[1], places=12)
                self.assertAlmostEqual(lp.position_m[2], rp.position_m[2], places=12)

    def test_front_and_rear_toe_link_roles_are_not_conflated(self) -> None:
        self.assertIs(
            self.geometry.corner("front", "left").toe_link.role,
            ToeLinkRole.STEERING_TIE_ROD,
        )
        self.assertIs(
            self.geometry.corner("rear", "left").toe_link.role,
            ToeLinkRole.CHASSIS_LOCATING_TOE_LINK,
        )

    def test_actuation_attachment_roles_match_source(self) -> None:
        self.assertIs(
            self.geometry.corner("front", "left").actuation.attachment,
            ActuationAttachment.UPPER_ARM,
        )
        self.assertIs(
            self.geometry.corner("rear", "left").actuation.attachment,
            ActuationAttachment.LOWER_ARM,
        )

    def test_reference_distance_and_setup_are_preserved_without_wheel_center_inference(self) -> None:
        self.assertAlmostEqual(self.geometry.reference_distance_m, 1.5624, places=12)
        front = self.geometry.corner("front", "left").wheel_setup
        rear = self.geometry.corner("rear", "left").wheel_setup
        self.assertAlmostEqual(front.half_track_m, 0.615986, places=12)
        self.assertAlmostEqual(front.static_camber_deg, -2.25, places=12)
        self.assertAlmostEqual(front.static_toe_deg, -1.0, places=12)
        self.assertAlmostEqual(rear.half_track_m, 0.603286, places=12)
        self.assertAlmostEqual(rear.static_camber_deg, -1.0, places=12)
        self.assertAlmostEqual(rear.static_toe_deg, 0.5, places=12)
        self.assertIn("not_derived", self.geometry.wheel_center_rule)

    def test_all_loaded_coordinates_are_finite(self) -> None:
        for corner in self.geometry.corners:
            points = (
                corner.wishbone.lower_fore_inboard,
                corner.wishbone.lower_aft_inboard,
                corner.wishbone.upper_fore_inboard,
                corner.wishbone.upper_aft_inboard,
                corner.wishbone.lower_upright,
                corner.wishbone.upper_upright,
                corner.toe_link.inboard,
                corner.toe_link.outboard,
                corner.actuation.outboard_attachment,
                corner.actuation.chassis_attachment,
                corner.actuation.rocker_axis_reference,
                corner.actuation.rocker_pivot,
                corner.actuation.rocker_rod_point,
                corner.actuation.rocker_coil_point,
            )
            for point in points:
                self.assertTrue(all(math.isfinite(value) for value in point.position_m))

    def test_missing_snapshot_is_not_silently_defaulted(self) -> None:
        with self.assertRaises(FileNotFoundError):
            load_optimumk_geometry_snapshot(ROOT / "data_catalog" / "does_not_exist.toml")


if __name__ == "__main__":
    unittest.main()

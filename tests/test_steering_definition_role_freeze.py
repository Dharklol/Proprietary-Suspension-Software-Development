from __future__ import annotations

import math
from pathlib import Path
import tomllib
import unittest

from pssd_steering import reference_from_static_alignment, road_intersection_direction


ROOT = Path(__file__).resolve().parents[1]


class SteeringDefinitionRoleFreezeTests(unittest.TestCase):
    def test_definition_contract_is_frozen(self) -> None:
        with (ROOT / "schemas" / "steering_definition_contract.toml").open("rb") as stream:
            contract = tomllib.load(stream)
        self.assertEqual("frozen_for_rigid_steering_evaluator", contract["status"])
        self.assertEqual("CANONICAL_ISO8855_BODY", contract["body_frame"]["id"])
        self.assertEqual("QTY-STEER-0006", contract["road_wheel_heading"]["left_quantity_id"])
        self.assertEqual("QTY-STEER-0007", contract["road_wheel_heading"]["right_quantity_id"])
        self.assertFalse(contract["result_map"]["extrapolation_allowed_default"])

    def test_reviewed_quantity_records_are_active_m1(self) -> None:
        quantity_ids = [
            "QTY-GEO-0001",
            "QTY-GEO-0004",
            "QTY-ALIGN-0001",
            "QTY-ALIGN-0002",
            "QTY-STEER-0001",
            "QTY-STEER-0002",
            "QTY-STEER-0003",
            "QTY-STEER-0004",
            "QTY-STEER-0005",
            "QTY-STEER-0006",
            "QTY-STEER-0007",
            "QTY-STEER-0010",
            "QTY-STEER-0011",
            "QTY-STEER-0012",
            "QTY-STEER-0013",
            "QTY-STEER-0014",
            "QTY-STEER-0015",
        ]
        for quantity_id in quantity_ids:
            path = ROOT / "registry" / "records" / "quantities" / f"{quantity_id}.toml"
            with path.open("rb") as stream:
                record = tomllib.load(stream)["record"]
            self.assertEqual("active", record["status"], quantity_id)
            self.assertEqual("M1", record["maturity"], quantity_id)
            self.assertEqual(
                "docs/reviews/phase0_steering_definition_role_closeout.md",
                record["review_record"],
                quantity_id,
            )

    def test_side_local_toe_maps_to_mirrored_global_headings(self) -> None:
        with (
            ROOT / "configurations" / "steering" / "WUFR26_DESIGN_NOMINAL_V0.toml"
        ).open("rb") as stream:
            configuration = tomllib.load(stream)
        left_toe = float(configuration["left"]["static_toe"])
        right_toe = float(configuration["right"]["static_toe"])
        left_camber = float(configuration["left"]["static_camber"])
        right_camber = float(configuration["right"]["static_camber"])

        left = reference_from_static_alignment("left", toe_out=left_toe, camber=left_camber)
        right = reference_from_static_alignment("right", toe_out=right_toe, camber=right_camber)
        left_direction = road_intersection_direction(
            left.normal_at_center, forward_hint=left.forward_at_center
        )
        right_direction = road_intersection_direction(
            right.normal_at_center, forward_hint=right.forward_at_center
        )
        left_heading = math.atan2(left_direction[1], left_direction[0])
        right_heading = math.atan2(right_direction[1], right_direction[0])

        self.assertAlmostEqual(left_toe, left_heading, places=12)
        self.assertAlmostEqual(-right_toe, right_heading, places=12)
        self.assertAlmostEqual(-left_heading, right_heading, places=12)

    def test_frozen_benchmark_has_no_active_optimizer_roles(self) -> None:
        path = (
            ROOT
            / "configurations"
            / "steering"
            / "WUFR26_STEERING_REQUIREMENT_ROLES_V0.toml"
        )
        with path.open("rb") as stream:
            requirement_set = tomllib.load(stream)
        self.assertEqual("evaluation_only", requirement_set["solver_mode"])
        self.assertFalse(requirement_set["optimizer_authorized"])
        items = requirement_set["items"]
        ids = [item["id"] for item in items]
        self.assertEqual(len(ids), len(set(ids)))
        allowed = set(requirement_set["role_vocabulary"]["allowed"])
        self.assertTrue(all(item["role"] in allowed for item in items))
        prohibited_active_roles = {
            "bounded_design_variable",
            "discrete_option",
            "acceptable_band",
            "target_value",
            "target_curve",
        }
        self.assertTrue(prohibited_active_roles.isdisjoint({item["role"] for item in items}))
        self.assertEqual("template_only_not_active", requirement_set["future_design_study"]["status"])


if __name__ == "__main__":
    unittest.main()

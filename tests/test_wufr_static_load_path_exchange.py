from __future__ import annotations

import hashlib
from pathlib import Path
import unittest

from pssd_suspension.wufr_static_load_path_exchange import (
    AUTHORIZATION_ID,
    CONFIGURATION_ID,
    CORNER_ORDER,
    MODEL_ID,
    RESULT_LABEL,
    ROOT,
    SOURCE_KEYS,
    STATIC_STATE_ID,
    canonical_json_bytes,
    evaluate_wufr_static_load_path_exchange,
    load_wufr_static_load_path_source_documents,
)


REQUIRED_FIELDS = {
    "record_id",
    "corner_id",
    "load_role",
    "acting_on_body_id",
    "counterparty_body_id",
    "frame_id",
    "point_or_reference_id",
    "application_or_reference_point_m",
    "force_N",
    "moment_Nm",
    "source_model_id",
    "source_authorization_id",
    "source_result_path",
    "source_field_path",
    "sign_convention",
    "fidelity_label",
    "complete_for_named_source_record",
}


class WufrStaticLoadPathExchangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = evaluate_wufr_static_load_path_exchange(root=ROOT)
        if not cls.result.ok or cls.result.packet is None:
            raise RuntimeError(f"{cls.result.failure_code}: {cls.result.message}")
        cls.packet = cls.result.packet
        cls.documents = load_wufr_static_load_path_source_documents(root=ROOT)

    def test_packet_identity_and_sections(self) -> None:
        identity = self.packet["packet_identity"]
        self.assertEqual(identity["result_label"], RESULT_LABEL)
        self.assertEqual(identity["model_id"], MODEL_ID)
        self.assertEqual(identity["authorization_id"], AUTHORIZATION_ID)
        self.assertEqual(identity["configuration_id"], CONFIGURATION_ID)
        self.assertEqual(identity["static_state_id"], STATIC_STATE_ID)
        self.assertEqual(identity["front_arb_setting"], 1)
        self.assertEqual(identity["rear_arb_setting"], 1)
        self.assertEqual(identity["corner_order"], list(CORNER_ORDER))
        self.assertEqual(
            list(self.packet),
            [
                "packet_identity",
                "source_manifest",
                "vehicle_static_state",
                "carrier_external_wrenches",
                "level1_interface_loads",
                "rocker_included_loads",
                "missing_and_deferred_loads",
                "diagnostics",
                "fidelity_and_use_boundaries",
            ],
        )

    def test_exact_source_sections_are_copied(self) -> None:
        self.assertEqual(
            self.packet["vehicle_static_state"]["primary"],
            self.documents["vehicle_equilibrium"]["primary"],
        )
        self.assertEqual(
            self.packet["carrier_external_wrenches"]["corners"],
            self.documents["carrier_wrench"]["corners"],
        )
        self.assertEqual(
            self.packet["level1_interface_loads"]["corners"],
            self.documents["level1_interface"]["corners"],
        )
        self.assertEqual(
            self.packet["rocker_included_loads"]["corners"],
            self.documents["rocker_included"]["corners"],
        )

    def test_source_manifest_hashes_exact_files(self) -> None:
        expected_paths = {
            "vehicle_equilibrium": ROOT / "benchmarks/vehicle/wufr_static_equilibrium_result_v0.2.0.json",
            "carrier_wrench": ROOT / "benchmarks/vehicle/wufr_static_carrier_wrench_result_v0.1.0.json",
            "level1_interface": ROOT / "benchmarks/suspension/wufr_static_level1_interface_loads_result_v0.1.0.json",
            "rocker_included": ROOT / "benchmarks/suspension/wufr_static_rocker_included_loads_result_v0.1.0.json",
        }
        manifest = {entry["source_key"]: entry for entry in self.packet["source_manifest"]}
        self.assertEqual(tuple(manifest), SOURCE_KEYS)
        for key, path in expected_paths.items():
            self.assertEqual(manifest[key]["source_sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(manifest[key]["source_byte_count"], len(path.read_bytes()))
            self.assertTrue(manifest[key]["exact_source_record_copied"])

    def test_every_load_record_is_complete_traceable_and_unique(self) -> None:
        record_ids: list[str] = []
        expected_counts = {
            "carrier_external_wrenches": 4,
            "level1_interface_loads": 40,
            "rocker_included_loads": 16,
        }
        for section_name, expected_count in expected_counts.items():
            section = self.packet[section_name]
            records = []
            for corner_id in CORNER_ORDER:
                corner_records = section["records_by_corner"][corner_id]
                self.assertTrue(corner_records)
                for record in corner_records:
                    self.assertTrue(REQUIRED_FIELDS.issubset(record))
                    self.assertEqual(record["corner_id"], corner_id)
                    self.assertEqual(len(record["application_or_reference_point_m"]), 3)
                    self.assertEqual(len(record["force_N"]), 3)
                    self.assertEqual(len(record["moment_Nm"]), 3)
                    self.assertTrue(record["frame_id"])
                    self.assertTrue(record["point_or_reference_id"])
                    self.assertTrue(record["source_result_path"])
                    self.assertTrue(record["source_field_path"])
                    record_ids.append(record["record_id"])
                records.extend(corner_records)
            self.assertEqual(len(records), expected_count)
        self.assertEqual(len(record_ids), len(set(record_ids)))

    def test_level1_action_reaction_signs_are_not_repaired(self) -> None:
        by_corner = self.packet["level1_interface_loads"]["records_by_corner"]
        for corner_id in CORNER_ORDER:
            records = {record["record_id"]: record for record in by_corner[corner_id]}
            for element in (
                "front_pullrod" if corner_id.startswith("front") else "rear_pushrod",
                "front_tie_rod" if corner_id.startswith("front") else "rear_toe_link",
            ):
                body = records[f"{corner_id}:{element}:on_body"]["force_N"]
                remote = records[f"{corner_id}:{element}:on_remote"]["force_N"]
                self.assertEqual([a + b for a, b in zip(body, remote)], [0.0, 0.0, 0.0])

    def test_missing_damper_and_fidelity_boundaries_remain_explicit(self) -> None:
        missing = self.packet["missing_and_deferred_loads"]
        self.assertEqual(missing["required_missing_force_id"], "KW_V5_non_spring_static_force")
        self.assertFalse(missing["kw_v5_actual_force_available"])
        self.assertFalse(missing["zero_damper_force_assumption_used"])
        self.assertTrue(missing["unit_damper_influence_is_geometry_sensitivity_only"])
        boundary = self.packet["fidelity_and_use_boundaries"]
        self.assertTrue(boundary["complete_for_named_upstream_record_exchange"])
        for key in (
            "complete_physical_hardware_load_case",
            "complete_rocker_equilibrium",
            "complete_chassis_pickup_load_set",
            "structural_load_case_authority",
            "fea_boundary_condition_authority",
            "structural_release_authority",
            "installed_as_built_authority",
            "production_authority",
        ):
            self.assertFalse(boundary[key])

    def test_canonical_generation_is_byte_stable(self) -> None:
        second = evaluate_wufr_static_load_path_exchange(root=ROOT)
        self.assertTrue(second.ok, second.message)
        self.assertIsNotNone(second.packet)
        self.assertEqual(canonical_json_bytes(self.packet), canonical_json_bytes(second.packet))


if __name__ == "__main__":
    unittest.main()

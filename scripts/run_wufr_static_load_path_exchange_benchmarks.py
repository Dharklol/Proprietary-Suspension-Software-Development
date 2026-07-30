#!/usr/bin/env python3
"""Generate and freeze BENCH-SUSP-0035..0037 load-path exchange evidence."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from pssd_suspension.wufr_static_load_path_exchange import (
    AUTHORIZATION_ID,
    CONFIGURATION_ID,
    CORNER_ORDER,
    MODEL_ID,
    RESULT_LABEL,
    ROOT,
    SCHEMA_VERSION,
    SOURCE_KEYS,
    STATIC_STATE_ID,
    WUFRStaticLoadPathExchangeFailureCode,
    canonical_json_bytes,
    evaluate_wufr_static_load_path_exchange,
    load_wufr_static_load_path_source_documents,
)

REQUIRED_LOAD_FIELDS = {
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


def _all_records(packet: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    records: list[Mapping[str, Any]] = []
    for section_name in (
        "carrier_external_wrenches",
        "level1_interface_loads",
        "rocker_included_loads",
    ):
        by_corner = packet[section_name]["records_by_corner"]
        for corner_id in CORNER_ORDER:
            records.extend(by_corner[corner_id])
    return records


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _failure_documents() -> dict[str, dict[str, Any]]:
    return load_wufr_static_load_path_source_documents(root=ROOT)


def _failure_case(mutator) -> tuple[str | None, bool]:
    documents = _failure_documents()
    mutator(documents)
    result = evaluate_wufr_static_load_path_exchange(root=ROOT, source_documents=documents)
    return (result.failure_code.value if result.failure_code else None, result.packet is not None)


def _mutate_reordered_corners(documents: dict[str, dict[str, Any]]) -> None:
    corners = documents["carrier_wrench"]["corners"]
    corners[0], corners[1] = corners[1], corners[0]


def _mutate_configuration(documents: dict[str, dict[str, Any]]) -> None:
    documents["level1_interface"]["configuration_id"] = "wrong_configuration"


def _mutate_nonfinite(documents: dict[str, dict[str, Any]]) -> None:
    documents["rocker_included"]["corners"][0]["included"]["point_loads"][0]["force_N"][0] = math.nan


def _mutate_missing_boundary(documents: dict[str, dict[str, Any]]) -> None:
    documents["rocker_included"]["corners"][0]["included"]["missing_load_ids"] = []


def _mutate_prohibited_authority(documents: dict[str, dict[str, Any]]) -> None:
    documents["rocker_included"]["boundaries"]["structural_release_authority"] = True


def _mutate_moved_point(documents: dict[str, dict[str, Any]]) -> None:
    point = documents["level1_interface"]["corners"][0]["solve"]["actuation"]["remote_point_m"]
    point[0] += 1.0e-4
    # The exchange is an exact-copy layer. A moved point is still a finite source
    # value, so expose it through a cross-source mismatch by leaving the rocker
    # push/pull point unchanged and changing the Level-1 source state.
    documents["level1_interface"]["corners"][0]["geometry"]["actuation_remote_point_m"] = list(point)


def build_report() -> dict[str, Any]:
    result = evaluate_wufr_static_load_path_exchange(root=ROOT)
    if not result.ok or result.packet is None:
        raise RuntimeError(f"Static load-path exchange failed: {result.failure_code} {result.message}")
    packet = deepcopy(result.packet)
    documents = load_wufr_static_load_path_source_documents(root=ROOT)

    manifest = {entry["source_key"]: entry for entry in packet["source_manifest"]}
    source_paths = {
        "vehicle_equilibrium": ROOT / "benchmarks/vehicle/wufr_static_equilibrium_result_v0.2.0.json",
        "carrier_wrench": ROOT / "benchmarks/vehicle/wufr_static_carrier_wrench_result_v0.1.0.json",
        "level1_interface": ROOT / "benchmarks/suspension/wufr_static_level1_interface_loads_result_v0.1.0.json",
        "rocker_included": ROOT / "benchmarks/suspension/wufr_static_rocker_included_loads_result_v0.1.0.json",
    }
    source_hash_error = max(
        int(manifest[key]["source_sha256"] != _sha256(source_paths[key]))
        for key in SOURCE_KEYS
    )
    exact_copy_checks = {
        "vehicle_primary": packet["vehicle_static_state"]["primary"] == documents["vehicle_equilibrium"]["primary"],
        "carrier_corners": packet["carrier_external_wrenches"]["corners"] == documents["carrier_wrench"]["corners"],
        "level1_corners": packet["level1_interface_loads"]["corners"] == documents["level1_interface"]["corners"],
        "rocker_corners": packet["rocker_included_loads"]["corners"] == documents["rocker_included"]["corners"],
    }
    records = _all_records(packet)
    missing_required_fields = sorted({
        field
        for record in records
        for field in REQUIRED_LOAD_FIELDS - set(record)
    })
    traceable = all(
        record["source_result_path"]
        and record["source_field_path"]
        and record["frame_id"]
        and record["point_or_reference_id"]
        for record in records
    )

    first_bytes = canonical_json_bytes(packet)
    second_result = evaluate_wufr_static_load_path_exchange(root=ROOT)
    if not second_result.ok or second_result.packet is None:
        raise RuntimeError("Second deterministic exchange generation failed")
    second_bytes = canonical_json_bytes(second_result.packet)
    record_ids = [str(record["record_id"]) for record in records]
    required_sections = [
        "packet_identity",
        "source_manifest",
        "vehicle_static_state",
        "carrier_external_wrenches",
        "level1_interface_loads",
        "rocker_included_loads",
        "missing_and_deferred_loads",
        "diagnostics",
        "fidelity_and_use_boundaries",
    ]

    failure_codes = {}
    partial_publication = {}
    for name, mutator in (
        ("reordered_corners", _mutate_reordered_corners),
        ("configuration_mismatch", _mutate_configuration),
        ("nonfinite_source_value", _mutate_nonfinite),
        ("missing_boundary", _mutate_missing_boundary),
        ("prohibited_authority", _mutate_prohibited_authority),
    ):
        code, packet_observed = _failure_case(mutator)
        failure_codes[name] = code
        partial_publication[name] = packet_observed
    expected_failure_codes = {
        "reordered_corners": WUFRStaticLoadPathExchangeFailureCode.CORNER_COUNT_OR_ORDER_MISMATCH.value,
        "configuration_mismatch": WUFRStaticLoadPathExchangeFailureCode.CONFIGURATION_MISMATCH.value,
        "nonfinite_source_value": WUFRStaticLoadPathExchangeFailureCode.NONFINITE_SOURCE_VALUE.value,
        "missing_boundary": WUFRStaticLoadPathExchangeFailureCode.MISSING_BOUNDARY_NOT_DECLARED.value,
        "prohibited_authority": WUFRStaticLoadPathExchangeFailureCode.PROHIBITED_AUTHORITY_FLAG.value,
    }

    bench35 = {
        "pass": (
            source_hash_error == 0
            and all(exact_copy_checks.values())
            and not missing_required_fields
            and traceable
        ),
        "maximum_source_hash_error": source_hash_error,
        "exact_copy_checks": exact_copy_checks,
        "load_record_count": len(records),
        "missing_required_load_record_fields": missing_required_fields,
        "all_records_traceable_to_source_field": traceable,
    }
    bench36 = {
        "pass": (
            list(packet) == required_sections
            and packet["packet_identity"]["corner_order"] == list(CORNER_ORDER)
            and len(record_ids) == len(set(record_ids))
            and first_bytes == second_bytes
        ),
        "required_sections": required_sections,
        "actual_sections": list(packet),
        "record_count": len(record_ids),
        "unique_record_count": len(set(record_ids)),
        "canonical_byte_count": len(first_bytes),
        "canonical_sha256_before_benchmark_blocks": hashlib.sha256(first_bytes).hexdigest(),
        "byte_stable_regeneration": first_bytes == second_bytes,
    }
    boundaries = packet["fidelity_and_use_boundaries"]
    bench37 = {
        "pass": (
            failure_codes == expected_failure_codes
            and not any(partial_publication.values())
            and boundaries["complete_physical_hardware_load_case"] is False
            and boundaries["complete_rocker_equilibrium"] is False
            and boundaries["structural_load_case_authority"] is False
            and boundaries["fea_boundary_condition_authority"] is False
            and boundaries["structural_release_authority"] is False
            and packet["missing_and_deferred_loads"]["required_missing_force_id"] == "KW_V5_non_spring_static_force"
            and packet["missing_and_deferred_loads"]["zero_damper_force_assumption_used"] is False
        ),
        "failure_codes": failure_codes,
        "expected_failure_codes": expected_failure_codes,
        "partial_packet_observed": partial_publication,
        "prohibited_authority_flags": {
            key: boundaries[key]
            for key in (
                "complete_physical_hardware_load_case",
                "complete_rocker_equilibrium",
                "structural_load_case_authority",
                "fea_boundary_condition_authority",
                "structural_release_authority",
                "installed_as_built_authority",
                "production_authority",
            )
        },
    }
    packet["diagnostics"]["BENCH-SUSP-0035"] = bench35
    packet["diagnostics"]["BENCH-SUSP-0036"] = bench36
    packet["diagnostics"]["BENCH-SUSP-0037"] = bench37
    if not all(block["pass"] for block in (bench35, bench36, bench37)):
        raise RuntimeError("Static load-path exchange benchmark acceptance failed")
    return packet


def summary_toml(packet: Mapping[str, Any]) -> str:
    identity = packet["packet_identity"]
    diagnostics = packet["diagnostics"]
    boundaries = packet["fidelity_and_use_boundaries"]
    source_hashes = diagnostics["source_hashes"]
    counts = diagnostics["load_record_counts"]
    canonical = canonical_json_bytes(packet)
    lines = [
        'version = "0.1.0"',
        f'schema_version = "{SCHEMA_VERSION}"',
        f'result_label = "{RESULT_LABEL}"',
        f'authorization_id = "{AUTHORIZATION_ID}"',
        f'model_id = "{MODEL_ID}"',
        f'configuration_id = "{CONFIGURATION_ID}"',
        f'static_state_id = "{STATIC_STATE_ID}"',
        'status = "accepted"',
        'corner_order = ["front_left", "front_right", "rear_left", "rear_right"]',
        f"front_arb_setting = {identity['front_arb_setting']}",
        f"rear_arb_setting = {identity['rear_arb_setting']}",
        f'canonical_packet_sha256 = "{hashlib.sha256(canonical).hexdigest()}"',
        f"canonical_packet_byte_count = {len(canonical)}",
        f"carrier_load_record_count = {counts['carrier_external_wrenches']}",
        f"level1_load_record_count = {counts['level1_interface_loads']}",
        f"rocker_load_record_count = {counts['rocker_included_loads']}",
        f"complete_for_named_upstream_record_exchange = {str(boundaries['complete_for_named_upstream_record_exchange']).lower()}",
        f"complete_physical_hardware_load_case = {str(boundaries['complete_physical_hardware_load_case']).lower()}",
        f"complete_rocker_equilibrium = {str(boundaries['complete_rocker_equilibrium']).lower()}",
        f"complete_chassis_pickup_load_set = {str(boundaries['complete_chassis_pickup_load_set']).lower()}",
        f"structural_load_case_authority = {str(boundaries['structural_load_case_authority']).lower()}",
        f"fea_boundary_condition_authority = {str(boundaries['fea_boundary_condition_authority']).lower()}",
        f"structural_release_authority = {str(boundaries['structural_release_authority']).lower()}",
        f"installed_as_built_authority = {str(boundaries['installed_as_built_authority']).lower()}",
        f"production_authority = {str(boundaries['production_authority']).lower()}",
        f"bench_susp_0035_pass = {str(diagnostics['BENCH-SUSP-0035']['pass']).lower()}",
        f"bench_susp_0036_pass = {str(diagnostics['BENCH-SUSP-0036']['pass']).lower()}",
        f"bench_susp_0037_pass = {str(diagnostics['BENCH-SUSP-0037']['pass']).lower()}",
        "",
        "[source_hashes]",
    ]
    for key in SOURCE_KEYS:
        lines.append(f'{key} = "{source_hashes[key]}"')
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="benchmarks/suspension/wufr_static_load_path_exchange_result_v0.1.0.json",
    )
    parser.add_argument(
        "--summary-output",
        default="benchmarks/suspension/wufr_static_load_path_exchange_result_v0.1.0.toml",
    )
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    packet = build_report()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(packet))
    summary = summary_toml(packet)
    summary_output = Path(args.summary_output)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.write_text(summary)
    if args.summary:
        print(summary, end="")


if __name__ == "__main__":
    main()

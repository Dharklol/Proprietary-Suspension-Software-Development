#!/usr/bin/env python3
"""Generate BENCH-VEH-0015..0017 static carrier-wrench diagnostics."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence

from pssd_suspension.geometry import Axle
from pssd_vehicle.force_coordinates import BodyPose
from pssd_vehicle.wufr_static_carrier_wrench import (
    CORNER_ORDER,
    WUFRStaticCarrierWrenchFailureCode,
    build_level1_to_road_transform,
    evaluate_wufr_static_carrier_wrenches,
    load_wufr_static_carrier_wrench_provider,
    pullback_road_wrench_to_level1,
    pushforward_level1_wrench_to_road,
    transform_level1_point_to_road,
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


def _v(values: Sequence[float]) -> list[float]:
    return [float(value) for value in values]


def _point(point) -> dict | None:
    if point is None:
        return None
    return {
        "point_id": point.point_id,
        "frame_id": point.frame_id,
        "origin_id": point.origin_id,
        "position_m": _v(point.position_m),
        "role": point.role,
        "source_id": point.source_id,
        "configuration_id": point.configuration_id,
        "authority": point.authority,
        "fixed_role": point.fixed_role,
        "provenance": [list(item) for item in point.provenance],
    }


def _applied(wrench) -> dict | None:
    if wrench is None:
        return None
    return {
        "wrench_id": wrench.wrench_id,
        "frame_id": wrench.frame_id,
        "origin_id": wrench.origin_id,
        "application_point": _point(wrench.application_point),
        "force_N": _v(wrench.force_N),
        "free_couple_Nm": _v(wrench.free_couple_Nm),
        "source_id": wrench.source_id,
        "authority": wrench.authority,
    }


def _resultant(wrench) -> dict | None:
    if wrench is None:
        return None
    return {
        "reference_point_id": wrench.reference_point_id,
        "frame_id": wrench.frame_id,
        "origin_id": wrench.origin_id,
        "resultant_force_N": _v(wrench.resultant_force_N),
        "resultant_moment_Nm": _v(wrench.resultant_moment_Nm),
        "contributions": [
            {
                "wrench_id": item.wrench_id,
                "reference_point_id": item.reference_point_id,
                "force_N": _v(item.force_N),
                "moment_Nm": _v(item.moment_Nm),
                "moment_arm_m": _v(item.moment_arm_m),
                "force_moment_Nm": _v(item.force_moment_Nm),
                "free_couple_Nm": _v(item.free_couple_Nm),
                "source_id": item.source_id,
                "authority": item.authority,
            }
            for item in wrench.contributions
        ],
    }


def _corner_record(corner) -> dict:
    transform = corner.frame_transform
    level1 = corner.level1_wrench
    road = corner.road_representation
    return {
        "ok": corner.ok,
        "status": corner.status.value,
        "failure_code": corner.failure_code.value if corner.failure_code else None,
        "message": corner.message,
        "corner_id": corner.corner_id,
        "axle": corner.axle,
        "side": corner.side,
        "configuration_id": corner.configuration_id,
        "static_state_id": corner.static_state_id,
        "road_reaction_N": corner.road_reaction_N,
        "road_normal": _v(corner.road_normal or ()),
        "contact_point_road": _point(corner.contact_point_road),
        "wheel_center_road": _point(corner.wheel_center_road),
        "upper_spherical_level1_m": _v(corner.upper_spherical_level1_m or ()),
        "lower_spherical_level1_m": _v(corner.lower_spherical_level1_m or ()),
        "carrier_reference_level1_m": _v(corner.carrier_reference_level1_m or ()),
        "carrier_reference_source_m": _v(corner.carrier_reference_source_m or ()),
        "carrier_reference_body_m": _v(corner.carrier_reference_body_m or ()),
        "carrier_reference_road": _point(corner.carrier_reference_road),
        "frame_transform": (
            {
                "source_frame_id": transform.source_frame_id,
                "target_frame_id": transform.target_frame_id,
                "target_origin_id": transform.target_origin_id,
                "rotation_target_from_source": [
                    _v(row) for row in transform.rotation_target_from_source
                ],
                "translation_target_of_source_origin_m": _v(
                    transform.translation_target_of_source_origin_m
                ),
                "axle_source_x_m": transform.axle_source_x_m,
                "body_pose": {
                    "z_s_m": transform.body_pose.z_s_m,
                    "phi_rad": transform.body_pose.phi_rad,
                    "theta_rad": transform.body_pose.theta_rad,
                    "psi_rad": transform.body_pose.psi_rad,
                },
                "authority": transform.authority,
            }
            if transform is not None
            else None
        ),
        "road_force_wrench": _applied(corner.road_force_wrench),
        "unsprung_gravity_wrench": _applied(corner.unsprung_gravity_wrench),
        "road_resultant": _resultant(corner.road_resultant),
        "road_representation": (
            {
                "frame_id": road.frame_id,
                "origin_id": road.origin_id,
                "reference_point_id": road.reference_point_id,
                "reference_point_m": _v(road.reference_point_m),
                "force_N": _v(road.force_N),
                "moment_Nm": _v(road.moment_Nm),
            }
            if road is not None
            else None
        ),
        "level1_wrench": (
            {
                "frame_id": level1.frame_id,
                "reference_point_m": _v(level1.reference_point_m),
                "force_N": _v(level1.force_N),
                "moment_Nm": _v(level1.moment_Nm),
                "source_id": level1.source_id,
                "load_case_id": level1.load_case_id,
                "complete": level1.complete,
            }
            if level1 is not None
            else None
        ),
        "round_trip_force_residual_N": corner.round_trip_force_residual_N,
        "round_trip_moment_residual_Nm": corner.round_trip_moment_residual_Nm,
        "complete_for_authorized_static_gravity_case": corner.complete_for_authorized_static_gravity_case,
        "complete_physical_hardware_wrench": corner.complete_physical_hardware_wrench,
        "maneuver_complete": corner.maneuver_complete,
        "installed_as_built_authority": corner.installed_as_built_authority,
    }


def _max_cross_product_error(corner) -> float:
    resultant = corner.road_resultant
    carrier = corner.carrier_reference_road
    road = corner.road_force_wrench
    gravity = corner.unsprung_gravity_wrench
    assert resultant and carrier and road and gravity

    def cross(a, b):
        return (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )

    def sub(a, b):
        return tuple(a[i] - b[i] for i in range(3))

    expected_force = tuple(road.force_N[i] + gravity.force_N[i] for i in range(3))
    m_road = cross(sub(road.application_point.position_m, carrier.position_m), road.force_N)
    m_gravity = cross(
        sub(gravity.application_point.position_m, carrier.position_m), gravity.force_N
    )
    expected_moment = tuple(m_road[i] + m_gravity[i] for i in range(3))
    return max(
        *(abs(expected_force[i] - resultant.resultant_force_N[i]) for i in range(3)),
        *(abs(expected_moment[i] - resultant.resultant_moment_Nm[i]) for i in range(3)),
    )


def _bounded_nonzero_transform_probe(provider) -> dict[str, float | list[float]]:
    nominal = provider.equilibrium_provider.nominal_body_pose()
    pose = BodyPose(
        inertial_frame_id=nominal.inertial_frame_id,
        inertial_origin_id=nominal.inertial_origin_id,
        body_frame_id=nominal.body_frame_id,
        body_origin_id=nominal.body_origin_id,
        body_origin_position_m=nominal.body_origin_position_m,
        z_s_m=0.004,
        phi_rad=0.012,
        theta_rad=-0.016,
        psi_rad=0.0,
        authority="BENCH-VEH-0015 bounded synthetic nonzero pose",
    )
    transform = build_level1_to_road_transform(provider, pose, Axle.FRONT)
    point_level1 = (0.031, 0.544, 0.207)
    point_road = transform_level1_point_to_road(transform, point_level1)
    force_level1 = (117.0, -43.0, 612.0)
    moment_level1 = (8.2, -3.1, 1.7)
    force_road, moment_road = pushforward_level1_wrench_to_road(
        transform, force_level1, moment_level1
    )
    recovered_force, recovered_moment = pullback_road_wrench_to_level1(
        transform, force_road, moment_road
    )
    return {
        "q_body": [pose.z_s_m, pose.phi_rad, pose.theta_rad],
        "point_level1_m": _v(point_level1),
        "point_road_m": _v(point_road),
        "force_level1_N": _v(force_level1),
        "force_road_N": _v(force_road),
        "moment_level1_Nm": _v(moment_level1),
        "moment_road_Nm": _v(moment_road),
        "force_round_trip_residual_N": max(
            abs(recovered_force[i] - force_level1[i]) for i in range(3)
        ),
        "moment_round_trip_residual_Nm": max(
            abs(recovered_moment[i] - moment_level1[i]) for i in range(3)
        ),
        "component_rotation_magnitude_N": max(
            abs(force_road[i] - force_level1[i]) for i in range(3)
        ),
    }


def build_report() -> dict[str, Any]:
    provider = _provider()
    result = evaluate_wufr_static_carrier_wrenches(provider)
    if not result.ok:
        raise RuntimeError(f"Static carrier-wrench benchmark failed: {result.failure_code} {result.message}")

    max_composition_error = max(_max_cross_product_error(corner) for corner in result.corners)
    max_force_round_trip = max(
        float(corner.round_trip_force_residual_N or 0.0) for corner in result.corners
    )
    max_moment_round_trip = max(
        float(corner.round_trip_moment_residual_Nm or 0.0) for corner in result.corners
    )
    synthetic_transform = _bounded_nonzero_transform_probe(provider)
    max_point_record_error = 0.0
    for index, corner in enumerate(result.corners):
        assert corner.contact_point_road and corner.wheel_center_road
        max_point_record_error = max(
            max_point_record_error,
            max(
                abs(corner.contact_point_road.position_m[axis] - provider.accepted_result.contact_points_road_m[index][axis])
                for axis in range(3)
            ),
            max(
                abs(corner.wheel_center_road.position_m[axis] - provider.accepted_result.wheel_centers_road_m[index][axis])
                for axis in range(3)
            ),
        )

    failure_cases = {}
    incomplete = evaluate_wufr_static_carrier_wrenches(
        replace(provider, accepted_result=replace(provider.accepted_result, primary_ok=False))
    )
    failure_cases["unsuccessful_upstream"] = (
        incomplete.failure_code.value if incomplete.failure_code else None
    )
    negative_values = list(provider.accepted_result.road_reactions_N)
    negative_values[0] = -1.0
    negative = evaluate_wufr_static_carrier_wrenches(
        replace(
            provider,
            accepted_result=replace(
                provider.accepted_result,
                road_reactions_N=tuple(negative_values),
            ),
        )
    )
    failure_cases["negative_reaction"] = negative.failure_code.value if negative.failure_code else None
    shifted_points = list(provider.accepted_result.contact_points_road_m)
    shifted_points[0] = (
        shifted_points[0][0] + 1.0e-4,
        shifted_points[0][1],
        shifted_points[0][2],
    )
    point_failure = evaluate_wufr_static_carrier_wrenches(
        replace(
            provider,
            accepted_result=replace(
                provider.accepted_result,
                contact_points_road_m=tuple(shifted_points),
            ),
        )
    )
    failure_cases["physical_point_mismatch"] = (
        point_failure.failure_code.value if point_failure.failure_code else None
    )
    closure_failure = evaluate_wufr_static_carrier_wrenches(
        replace(
            provider,
            accepted_result=replace(
                provider.accepted_result,
                physical_closure_force_N=(1.0, 0.0, 0.0),
            ),
        )
    )
    failure_cases["reconstruction_disagreement"] = (
        closure_failure.failure_code.value if closure_failure.failure_code else None
    )
    expected_failures = {
        "unsuccessful_upstream": WUFRStaticCarrierWrenchFailureCode.UPSTREAM_RESULT_FAILURE.value,
        "negative_reaction": WUFRStaticCarrierWrenchFailureCode.NEGATIVE_REACTION.value,
        "physical_point_mismatch": WUFRStaticCarrierWrenchFailureCode.PHYSICAL_POINT_MISMATCH.value,
        "reconstruction_disagreement": WUFRStaticCarrierWrenchFailureCode.RECONSTRUCTION_FAILURE.value,
    }

    benchmark_15_pass = (
        tuple(corner.corner_id for corner in result.corners) == CORNER_ORDER
        and max_composition_error <= provider.config.component_composition_tolerance
        and max_point_record_error <= provider.config.point_match_tolerance_m
        and max_force_round_trip <= provider.config.wrench_transport_tolerance_N
        and max_moment_round_trip <= provider.config.wrench_transport_tolerance_Nm
        and float(synthetic_transform["force_round_trip_residual_N"])
        <= provider.config.wrench_transport_tolerance_N
        and float(synthetic_transform["moment_round_trip_residual_Nm"])
        <= provider.config.wrench_transport_tolerance_Nm
        and float(synthetic_transform["component_rotation_magnitude_N"]) > 1.0e-3
    )
    benchmark_16_pass = (
        result.complete_for_authorized_static_gravity_case
        and not result.complete_physical_hardware_wrench
        and not result.maneuver_complete
        and not result.installed_as_built_authority
        and result.maximum_force_residual_N is not None
        and result.maximum_force_residual_N <= provider.config.four_corner_force_reconstruction_tolerance_N
        and result.maximum_moment_residual_Nm is not None
        and result.maximum_moment_residual_Nm <= provider.config.four_corner_moment_reconstruction_tolerance_Nm
        and result.accepted_force_match_residual_N is not None
        and result.accepted_force_match_residual_N <= provider.config.accepted_closure_match_tolerance_N
        and result.accepted_moment_match_residual_Nm is not None
        and result.accepted_moment_match_residual_Nm <= provider.config.accepted_closure_match_tolerance_Nm
    )
    benchmark_17_pass = failure_cases == expected_failures
    if not (benchmark_15_pass and benchmark_16_pass and benchmark_17_pass):
        raise RuntimeError(
            f"Carrier-wrench acceptance failed: B15={benchmark_15_pass} B16={benchmark_16_pass} B17={benchmark_17_pass}"
        )

    return {
        "version": "0.1.0",
        "status": "pass",
        "model_id": result.model_id,
        "authorization_id": result.authorization_id,
        "source_record_id": provider.source.record_id,
        "configuration_id": result.configuration_id,
        "static_state_id": result.static_state_id,
        "result_label": result.result_label,
        "upstream": {
            "model_id": provider.accepted_result.model_id,
            "authorization_id": provider.accepted_result.authorization_id,
            "result_path": provider.accepted_result.source_path,
            "result_label": provider.accepted_result.result_label,
            "front_arb_setting": provider.accepted_result.front_arb_setting,
            "rear_arb_setting": provider.accepted_result.rear_arb_setting,
            "q_body": _v(provider.accepted_result.q_body),
            "wheel_coordinates_m": _v(provider.accepted_result.wheel_coordinates_m),
            "road_reactions_N": _v(provider.accepted_result.road_reactions_N),
        },
        "corners": [_corner_record(corner) for corner in result.corners],
        "reconstruction": {
            "at_road_origin": _resultant(result.reconstruction_at_road_origin),
            "at_body_origin": _resultant(result.reconstruction_at_body_origin),
            "accepted_closure_force_N": _v(result.accepted_closure_force_N or ()),
            "accepted_closure_moment_Nm": _v(result.accepted_closure_moment_Nm or ()),
            "maximum_force_residual_N": result.maximum_force_residual_N,
            "maximum_moment_residual_Nm": result.maximum_moment_residual_Nm,
            "accepted_force_match_residual_N": result.accepted_force_match_residual_N,
            "accepted_moment_match_residual_Nm": result.accepted_moment_match_residual_Nm,
        },
        "BENCH-VEH-0015": {
            "pass": benchmark_15_pass,
            "maximum_direct_composition_error": max_composition_error,
            "maximum_accepted_point_record_error_m": max_point_record_error,
            "maximum_round_trip_force_residual_N": max_force_round_trip,
            "maximum_round_trip_moment_residual_Nm": max_moment_round_trip,
            "bounded_nonzero_transform_probe": synthetic_transform,
        },
        "BENCH-VEH-0016": {
            "pass": benchmark_16_pass,
            "corner_count": len(result.corners),
            "complete_for_authorized_static_gravity_case": result.complete_for_authorized_static_gravity_case,
            "maximum_force_residual_N": result.maximum_force_residual_N,
            "maximum_moment_residual_Nm": result.maximum_moment_residual_Nm,
            "accepted_force_match_residual_N": result.accepted_force_match_residual_N,
            "accepted_moment_match_residual_Nm": result.accepted_moment_match_residual_Nm,
        },
        "BENCH-VEH-0017": {
            "pass": benchmark_17_pass,
            "failure_cases": failure_cases,
            "expected_failure_cases": expected_failures,
        },
        "boundaries": {
            "complete_for_authorized_static_gravity_case": result.complete_for_authorized_static_gravity_case,
            "complete_physical_hardware_wrench": result.complete_physical_hardware_wrench,
            "maneuver_complete": result.maneuver_complete,
            "installed_as_built_authority": result.installed_as_built_authority,
            "integrated_level1_linkage_result_authority": result.integrated_level1_linkage_result_authority,
            "historical_scale_reconstruction_used": result.historical_scale_reconstruction_used,
            "hidden_balancing_wrench_used": result.hidden_balancing_wrench_used,
            "structural_load_case_authority": False,
            "rocker_reaction_authority": False,
        },
    }


def _write_toml_summary(
    path: Path, report: dict[str, Any], *, full_result_sha256: str
) -> None:
    b15 = report["BENCH-VEH-0015"]
    b16 = report["BENCH-VEH-0016"]
    b17 = report["BENCH-VEH-0017"]
    lines = [
        'version = "0.1.0"',
        f'model_id = "{report["model_id"]}"',
        f'authorization_id = "{report["authorization_id"]}"',
        f'source_record_id = "{report["source_record_id"]}"',
        f'configuration_id = "{report["configuration_id"]}"',
        f'static_state_id = "{report["static_state_id"]}"',
        f'result_label = "{report["result_label"]}"',
        'status = "pass"',
        f'full_result_sha256 = "{full_result_sha256}"',
        '',
        '[BENCH-VEH-0015]',
        f'pass = {str(b15["pass"]).lower()}',
        f'maximum_direct_composition_error = {b15["maximum_direct_composition_error"]:.17g}',
        f'maximum_accepted_point_record_error_m = {b15["maximum_accepted_point_record_error_m"]:.17g}',
        f'maximum_round_trip_force_residual_N = {b15["maximum_round_trip_force_residual_N"]:.17g}',
        f'maximum_round_trip_moment_residual_Nm = {b15["maximum_round_trip_moment_residual_Nm"]:.17g}',
        f'synthetic_force_round_trip_residual_N = {b15["bounded_nonzero_transform_probe"]["force_round_trip_residual_N"]:.17g}',
        f'synthetic_moment_round_trip_residual_Nm = {b15["bounded_nonzero_transform_probe"]["moment_round_trip_residual_Nm"]:.17g}',
        f'synthetic_component_rotation_magnitude_N = {b15["bounded_nonzero_transform_probe"]["component_rotation_magnitude_N"]:.17g}',
        '',
        '[BENCH-VEH-0016]',
        f'pass = {str(b16["pass"]).lower()}',
        f'corner_count = {b16["corner_count"]}',
        f'complete_for_authorized_static_gravity_case = {str(b16["complete_for_authorized_static_gravity_case"]).lower()}',
        f'maximum_force_residual_N = {b16["maximum_force_residual_N"]:.17g}',
        f'maximum_moment_residual_Nm = {b16["maximum_moment_residual_Nm"]:.17g}',
        f'accepted_force_match_residual_N = {b16["accepted_force_match_residual_N"]:.17g}',
        f'accepted_moment_match_residual_Nm = {b16["accepted_moment_match_residual_Nm"]:.17g}',
        '',
        '[BENCH-VEH-0017]',
        f'pass = {str(b17["pass"]).lower()}',
        f'unsuccessful_upstream_failure = "{b17["failure_cases"]["unsuccessful_upstream"]}"',
        f'negative_reaction_failure = "{b17["failure_cases"]["negative_reaction"]}"',
        f'physical_point_mismatch_failure = "{b17["failure_cases"]["physical_point_mismatch"]}"',
        f'reconstruction_disagreement_failure = "{b17["failure_cases"]["reconstruction_disagreement"]}"',
        '',
        '[boundaries]',
    ]
    for key, value in report["boundaries"].items():
        lines.append(f'{key} = {str(bool(value)).lower()}')
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    full_result_text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    full_result_sha256 = hashlib.sha256(full_result_text.encode("utf-8")).hexdigest()
    if args.output:
        args.output.write_text(full_result_text, encoding="utf-8")
    if args.summary_output:
        _write_toml_summary(
            args.summary_output,
            report,
            full_result_sha256=full_result_sha256,
        )
    if args.summary:
        print(
            json.dumps(
                {
                    "model_id": report["model_id"],
                    "status": report["status"],
                    "corner_count": report["BENCH-VEH-0016"]["corner_count"],
                    "maximum_force_residual_N": report["BENCH-VEH-0016"]["maximum_force_residual_N"],
                    "maximum_moment_residual_Nm": report["BENCH-VEH-0016"]["maximum_moment_residual_Nm"],
                },
                sort_keys=True,
            )
        )
    elif not args.output and not args.summary_output:
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

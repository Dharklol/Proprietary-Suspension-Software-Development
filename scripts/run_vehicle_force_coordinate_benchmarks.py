#!/usr/bin/env python3
"""Generate BENCH-VEH-0003/0004 whole-vehicle force-coordinate diagnostics."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from pssd_vehicle.force_coordinates import (
    AppliedWrench,
    BodyPose,
    ContactCornerInput,
    ContactStatus,
    PointReference,
    RoadPlane,
    analytical_generalized_force,
    assemble_wrenches,
    classify_rigid_four_contact,
    load_wufr_whole_vehicle_adapter,
    numerical_generalized_force,
    road_plane_from_wufr_adapter,
    transport_body_fixed_point,
)

ROOT = Path(__file__).resolve().parents[1]


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
        role="synthetic_benchmark",
        source_id="BENCH-VEH-0003",
        configuration_id="SYNTHETIC",
        authority="synthetic benchmark",
        fixed_role=fixed_role,
    )


def bench_0003() -> dict:
    p = point("p", (1.0, 0.0, 0.0))
    yaw_pose = BodyPose("ROAD", "R0", "BODY", "CG", psi_rad=math.pi / 2.0)
    transported = transport_body_fixed_point(p, yaw_pose)
    transport_error = math.dist(transported.position_m, (0.0, 1.0, 0.0))

    app = point(
        "P",
        (2.0, 0.0, 0.0),
        frame="ROAD",
        origin="R0",
        fixed_role="road_fixed",
    )
    ref = point(
        "O",
        (0.0, 0.0, 0.0),
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
    resultant = assemble_wrenches((action,), ref)
    wrench_error = math.dist(resultant.resultant_moment_Nm, (1.0, 2.0, 23.0))

    load = point("load", (0.7, -0.35, 0.22))
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
        load,
        pose,
        force_N=force,
        free_couple_Nm=couple,
    )
    numeric = numerical_generalized_force(
        load,
        pose,
        force_N=force,
        free_couple_Nm=couple,
        steps=(1.0e-5, 2.0e-5, 2.0e-5),
    )
    generalized_force_error = max(
        abs(a - b) for a, b in zip(exact.generalized_force, numeric.generalized_force)
    )
    passed = (
        transport_error <= 1.0e-14
        and wrench_error <= 1.0e-14
        and generalized_force_error <= 2.0e-7
        and exact.generalized_force[0] == force[2]
    )
    return {
        "transport_error_m": transport_error,
        "wrench_moment_error_Nm": wrench_error,
        "generalized_force_max_error": generalized_force_error,
        "numerical_convergence_error": numeric.convergence_error,
        "generalized_force": exact.generalized_force,
        "coordinate_units": exact.coordinate_units,
        "pass": passed,
    }


def bench_0004() -> dict:
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
                100.0,
            )
            for corner in corners
        ),
    )
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
                -1.0 if corner == "rear_right" else 100.0,
            )
            for corner in corners
        ),
    )
    adapter = load_wufr_whole_vehicle_adapter(
        ROOT / "data_catalog/wufr26_whole_vehicle_frame_v0.toml"
    )
    adapter_road = road_plane_from_wufr_adapter(adapter)
    max_gap = max(
        abs(
            sum(
                adapter_road.normal[i]
                * (p.position_m[i] - adapter_road.reference_point_m[i])
                for i in range(3)
            )
        )
        for p in adapter.contact_points_body.values()
    )
    passed = (
        valid.status == ContactStatus.FOUR_CONTACT_ADMISSIBLE
        and lift.status == ContactStatus.WHEEL_LIFT
        and max_gap <= 1.0e-14
        and not adapter.installed_authority
    )
    return {
        "valid_contact_status": valid.status.value,
        "negative_reaction_status": lift.status.value,
        "negative_reaction_preserved_N": next(
            item.normal_reaction_N
            for item in lift.corners
            if item.corner_id == "rear_right"
        ),
        "wufr_wheelbase_m": adapter.wheelbase_m,
        "wufr_front_track_m": adapter.front_track_m,
        "wufr_rear_track_m": adapter.rear_track_m,
        "wufr_cg_to_front_axle_m": adapter.cg_to_front_axle_m,
        "wufr_cg_to_rear_axle_m": adapter.cg_to_rear_axle_m,
        "wufr_contact_max_gap_m": max_gap,
        "installed_authority": adapter.installed_authority,
        "pass": passed,
    }


def build_report() -> dict:
    b3 = bench_0003()
    b4 = bench_0004()
    if not b3["pass"] or not b4["pass"]:
        raise RuntimeError("Vehicle force-coordinate benchmark acceptance failed")
    return {
        "model_id": "MOD-VEH-0003",
        "authorization_id": "AUTH-VEH-0003",
        "authority": (
            "software verification plus reviewed WUFR design-intent frame adapter; "
            "no force-law/equilibrium/installed authority"
        ),
        "BENCH-VEH-0003": b3,
        "BENCH-VEH-0004": b4,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("vehicle_force_coordinate_report.json"),
    )
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.summary:
        b3 = report["BENCH-VEH-0003"]
        b4 = report["BENCH-VEH-0004"]
        print(
            "MOD-VEH-0003: "
            f"q_error={b3['generalized_force_max_error']:.6g}, "
            f"wheelbase={b4['wufr_wheelbase_m']:.7g} m, "
            f"contact_gap={b4['wufr_contact_max_gap_m']:.3g} m"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

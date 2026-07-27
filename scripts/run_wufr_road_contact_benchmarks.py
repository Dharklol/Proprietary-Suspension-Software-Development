#!/usr/bin/env python3
"""Generate BENCH-VEH-0009/0010 WUFR rigid-circle compatibility diagnostics."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
import math
from pathlib import Path

from pssd_suspension import Axle, Side, build_nominal_wheel_reference, load_wufr26_wheel_reference_profile
from pssd_vehicle import load_wufr_static_gravity_allocation
from pssd_vehicle.wufr_road_contact import (
    CORNER_ORDER,
    evaluate_wufr_road_contact,
    ideal_rigid_circle_contact,
    load_wufr_road_contact_provider,
    solve_road_compatibility,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_catalog/wufr26_road_contact_reference_v0.toml"
SUSPENSION = ROOT / "data_catalog/wufr26_optimumk_suspension_hardpoints_v0.toml"
WHEEL_PROFILE = ROOT / "benchmarks/suspension/WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0.toml"
STEERING = ROOT / "configurations/steering/WUFR27_STEERING_BASELINE_V0.toml"
WHOLE_VEHICLE = ROOT / "data_catalog/wufr26_whole_vehicle_frame_v0.toml"
GRAVITY = ROOT / "data_catalog/wufr27_static_gravity_allocation_v0.toml"


def _list3(value: tuple[float, float, float]) -> list[float]:
    return [float(item) for item in value]


def build_report() -> dict:
    profile = load_wufr26_wheel_reference_profile(WHEEL_PROFILE)
    provider = load_wufr_road_contact_provider(
        source_path=SOURCE,
        suspension_geometry_path=SUSPENSION,
        wheel_profile_path=WHEEL_PROFILE,
        steering_geometry_path=STEERING,
        whole_vehicle_path=WHOLE_VEHICLE,
    )
    gravity = load_wufr_static_gravity_allocation(GRAVITY)
    pose = provider.nominal_body_pose()

    nominal_circle: dict[str, dict] = {}
    identities = (
        ("front_left", Axle.FRONT, Side.LEFT),
        ("front_right", Axle.FRONT, Side.RIGHT),
        ("rear_left", Axle.REAR, Side.LEFT),
        ("rear_right", Axle.REAR, Side.RIGHT),
    )
    for corner, axle, side in identities:
        reference = build_nominal_wheel_reference(profile, axle, side)
        circle = ideal_rigid_circle_contact(
            reference.center_m,
            reference.plane_normal,
            (0.0, 0.0, 1.0),
            provider.tire_radius_m,
        )
        radial = tuple(circle.contact_point_m[i] - reference.center_m[i] for i in range(3))
        nominal_circle[corner] = {
            "wheel_center_m": _list3(reference.center_m),
            "wheel_plane_normal": _list3(reference.plane_normal),
            "contact_point_m": _list3(circle.contact_point_m),
            "radius_error_m": abs(math.sqrt(sum(v * v for v in radial)) - provider.tire_radius_m),
            "wheel_plane_membership_residual_m": abs(sum(radial[i] * reference.plane_normal[i] for i in range(3))),
            "projection_magnitude": circle.projection_magnitude,
        }

    nominal = evaluate_wufr_road_contact(provider, pose, gravity)
    if not nominal.ok or nominal.compatibility.wheel_coordinates_m is None or nominal.jacobian is None or nominal.jacobian.jacobian is None:
        raise RuntimeError(f"BENCH-VEH-0009 nominal evaluation failed: {nominal.message}")
    pure = solve_road_compatibility(provider, replace(pose, z_s_m=0.004))
    combined = solve_road_compatibility(provider, replace(pose, z_s_m=0.0015, phi_rad=0.0020, theta_rad=-0.0015))
    if not pure.ok or not combined.ok or pure.wheel_coordinates_m is None or combined.wheel_coordinates_m is None:
        raise RuntimeError(f"BENCH-VEH-0009 nonzero compatibility failed: pure={pure.message}; combined={combined.message}")

    nominal_roots = {}
    for root, coefficient, gravity_force in zip(
        nominal.compatibility.roots,
        nominal.contact_coefficients,
        nominal.unsprung_gravity_forces,
    ):
        if root.state is None or coefficient.value is None or gravity_force.value is None:
            raise RuntimeError(f"Incomplete BENCH-VEH-0009 state for {root.corner_id}")
        nominal_roots[root.corner_id] = {
            "wheel_coordinate_m": root.wheel_coordinate_m,
            "road_gap_m": root.state.road_gap_m,
            "contact_point_road_m": _list3(root.state.contact_road.position_m),
            "wheel_center_road_m": _list3(root.state.wheel_center_road.position_m),
            "contact_coefficient": coefficient.value,
            "contact_coefficient_coarse": coefficient.coarse_value,
            "contact_coefficient_two_step_error": coefficient.convergence_error,
            "unsprung_gravity_generalized_force_N": gravity_force.value,
            "unsprung_gravity_coarse_N": gravity_force.coarse_value,
            "unsprung_gravity_two_step_error_N": gravity_force.convergence_error,
            "steering_rotation_rad": root.state.point_state.steering_rotation_rad,
            "steering_closure_residual_m": root.state.point_state.steering_closure_residual_m,
            "contact_projection_magnitude": root.state.circle_contact.projection_magnitude,
        }

    max_circle_radius_error = max(item["radius_error_m"] for item in nominal_circle.values())
    max_circle_plane_error = max(item["wheel_plane_membership_residual_m"] for item in nominal_circle.values())
    max_nominal_wheel_coordinate = max(abs(v) for v in nominal.compatibility.wheel_coordinates_m)
    max_nominal_gap = max(abs(item["road_gap_m"]) for item in nominal_roots.values())

    if max_circle_radius_error > 1.0e-12 or max_circle_plane_error > 1.0e-12:
        raise RuntimeError("BENCH-VEH-0010 circle geometry acceptance failed")
    if max_nominal_wheel_coordinate > 2.0e-8 or max_nominal_gap > 2.0e-9:
        raise RuntimeError("BENCH-VEH-0009 nominal road compatibility acceptance failed")

    return {
        "model_id": "MOD-VEH-0006",
        "authorization_id": "AUTH-VEH-0008",
        "assumption_id": "ASM-VEH-0005",
        "equation_ids": ["EQ-VEH-0011", "EQ-VEH-0012", "EQ-VEH-0013", "EQ-VEH-0014"],
        "authority": "uncorrelated WUFR-27 design-intent static road compatibility only; no road-reaction authority",
        "BENCH-VEH-0010": {
            "pass": True,
            "radius_m": provider.tire_radius_m,
            "radius_source": provider.source.radius_source,
            "maximum_radius_error_m": max_circle_radius_error,
            "maximum_wheel_plane_membership_residual_m": max_circle_plane_error,
            "nominal_circle": nominal_circle,
            "loaded_radius_used": False,
            "tire_vertical_compliance_used": False,
            "historical_contact_patch_fitted": False,
        },
        "BENCH-VEH-0009": {
            "pass": True,
            "coordinate_order": list(CORNER_ORDER),
            "body_coordinate_order": list(nominal.jacobian.coordinate_order),
            "nominal": nominal_roots,
            "nominal_wheel_coordinates_m": list(nominal.compatibility.wheel_coordinates_m),
            "maximum_nominal_wheel_coordinate_m": max_nominal_wheel_coordinate,
            "maximum_nominal_road_gap_m": max_nominal_gap,
            "J_wb": [list(row) for row in nominal.jacobian.jacobian],
            "J_wb_coarse": [list(row) for row in (nominal.jacobian.coarse_jacobian or ())],
            "J_wb_two_step_error": nominal.jacobian.convergence_error,
            "pure_heave_0p004_wheel_coordinates_m": list(pure.wheel_coordinates_m),
            "combined_pose": {"z_s_m": 0.0015, "phi_rad": 0.0020, "theta_rad": -0.0015},
            "combined_wheel_coordinates_m": list(combined.wheel_coordinates_m),
            "unsprung_corner_mass_kg": [item.mass_kg for item in gravity.unsprung],
            "road_reactions_available": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("wufr_road_contact_report.json"))
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        b9 = report["BENCH-VEH-0009"]
        b10 = report["BENCH-VEH-0010"]
        print(
            "MOD-VEH-0006: "
            f"R={b10['radius_m']:.6f} m, "
            f"max_circle_error={b10['maximum_radius_error_m']:.3g} m, "
            f"max_nominal_z_w={b9['maximum_nominal_wheel_coordinate_m']:.3g} m, "
            f"max_gap={b9['maximum_nominal_road_gap_m']:.3g} m, "
            f"J_error={b9['J_wb_two_step_error']:.3g}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run and print the frozen rigid-steering benchmark summary."""

from __future__ import annotations

import json
import math
from pathlib import Path

from pssd_steering import (
    ackermann_error,
    conventional_steering_ratio,
    exact_ackermann_outside_reference,
    load_geometry,
    local_road_wheel_gain,
    solve_corner_position,
    turning_radii,
    wheel_heading,
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    fixture = load_geometry(root / "benchmarks" / "steering" / "GEO-STEER-BASIC-001.toml")
    wufr = load_geometry(root / "configurations" / "steering" / "WUFR26_DESIGN_NOMINAL_V0.toml")

    states = []
    for displacement in (-0.010, -0.005, 0.0, 0.005, 0.010):
        left = solve_corner_position(fixture, "left", displacement)
        right = solve_corner_position(fixture, "right", displacement)
        if not left.ok or not right.ok:
            raise RuntimeError(f"Synthetic solve failed at {displacement}: {left.message}; {right.message}")
        _, left_heading = wheel_heading(fixture.left, left.upright_rotation or 0.0)
        _, right_heading = wheel_heading(fixture.right, right.upright_rotation or 0.0)
        state = {
            "rack_displacement_m": displacement,
            "left_heading_deg": math.degrees(left_heading),
            "right_heading_deg": math.degrees(right_heading),
            "left_closure_residual_m": left.closure_length_residual,
            "right_closure_residual_m": right.closure_length_residual,
            "left_branch_signature": left.branch_signature,
            "right_branch_signature": right.branch_signature,
        }
        if displacement != 0.0:
            assignment, reference, error = ackermann_error(
                left_heading,
                right_heading,
                fixture.wheelbase or 0.0,
                fixture.steering_axis_track or 0.0,
            )
            radii = turning_radii(
                assignment.inside_incremental_magnitude,
                assignment.outside_incremental_magnitude,
                fixture.wheelbase or 0.0,
                fixture.steering_axis_track or 0.0,
            )
            state.update(
                {
                    "turn_direction": assignment.turn_direction,
                    "ackermann_outside_reference_deg": math.degrees(reference),
                    "ackermann_error_deg": math.degrees(error),
                    "radius_from_inside_m": radii.rear_axle_center_from_inside,
                    "radius_from_outside_m": radii.rear_axle_center_from_outside,
                }
            )
        states.append(state)

    center = solve_corner_position(fixture, "left", 0.0)
    local_gain = center.local_upright_gain_rad_per_m or 0.0
    chained_gain = local_road_wheel_gain(local_gain, 0.010, 1.0)

    wufr_states = []
    for displacement in (-0.0127, -0.00635, 0.0, 0.00635, 0.0127):
        left = solve_corner_position(wufr, "left", displacement)
        right = solve_corner_position(wufr, "right", displacement)
        wufr_states.append(
            {
                "rack_displacement_m": displacement,
                "left_upright_rotation_deg": (
                    math.degrees(left.upright_rotation) if left.upright_rotation is not None else None
                ),
                "right_upright_rotation_deg": (
                    math.degrees(right.upright_rotation) if right.upright_rotation is not None else None
                ),
                "left_status": left.status.value,
                "right_status": right.status.value,
                "left_closure_residual_m": left.closure_length_residual,
                "right_closure_residual_m": right.closure_length_residual,
            }
        )

    output = {
        "authorization_id": "AUTH-STEER-0001",
        "model_id": "MOD-STEER-0001",
        "benchmark_ids": [f"BENCH-STEER-{value:04d}" for value in range(2, 9)],
        "synthetic_states": states,
        "center_local_gain_rad_per_m": local_gain,
        "synthetic_road_wheel_gain_rad_per_rad": chained_gain,
        "synthetic_conventional_ratio_magnitude": conventional_steering_ratio(chained_gain),
        "ackermann_25_deg_reference_deg": math.degrees(
            exact_ackermann_outside_reference(math.radians(25.0), 1.6, 1.2)
        ),
        "wufr26_nominal_incremental_rotation_states": wufr_states,
        "wufr26_unavailable_outputs": [
            "projected_road_wheel_heading",
            "absolute_toe_inclusive_heading",
            "steering_wheel_to_road_wheel_ratio",
            "ackermann_error",
            "turning_radius",
        ],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

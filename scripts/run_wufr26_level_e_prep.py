#!/usr/bin/env python3
"""Generate the WUFR-26 nominal sweep on the recovered Design Study input grid."""

from __future__ import annotations

import json
import math
from pathlib import Path

from pssd_steering import level_e_missing_metadata, load_geometry, solve_sweep


SOURCE_INPUT_MIN_DEG = -102
SOURCE_INPUT_MAX_DEG = 102
RACK_TRAVEL_IN_PER_REV = 3.5
RACK_TRAVEL_M_PER_INPUT_DEG = RACK_TRAVEL_IN_PER_REV * 0.0254 / 360.0


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    geometry = load_geometry(root / "configurations/steering/WUFR26_DESIGN_NOMINAL_V0.toml")

    source_inputs_deg = list(range(SOURCE_INPUT_MIN_DEG, SOURCE_INPUT_MAX_DEG + 1))
    displacements = [value * RACK_TRAVEL_M_PER_INPUT_DEG for value in source_inputs_deg]
    if displacements[0] < geometry.rack.displacement_min or displacements[-1] > geometry.rack.displacement_max:
        raise RuntimeError("Recovered Design Study input mapping exceeds the declared geometry domain")

    solved = solve_sweep(geometry, displacements)

    states = []
    for index, (input_deg, displacement) in enumerate(zip(source_inputs_deg, displacements)):
        left = solved["left"][index]
        right = solved["right"][index]
        states.append(
            {
                "steer_input_deg": input_deg,
                "rack_displacement_m": displacement,
                "left_status": left.status.value,
                "left_upright_rotation_rad": left.upright_rotation,
                "left_upright_rotation_deg": (
                    math.degrees(left.upright_rotation)
                    if left.upright_rotation is not None
                    else None
                ),
                "left_closure_residual_m": left.closure_length_residual,
                "left_singularity_ratio": left.singularity_ratio_to_reference,
                "right_status": right.status.value,
                "right_upright_rotation_rad": right.upright_rotation,
                "right_upright_rotation_deg": (
                    math.degrees(right.upright_rotation)
                    if right.upright_rotation is not None
                    else None
                ),
                "right_closure_residual_m": right.closure_length_residual,
                "right_singularity_ratio": right.singularity_ratio_to_reference,
            }
        )

    metadata = {
        "source_file_id_and_version": "box:2357045252883/version:2611346929683",
        "source_hash": "69d71c0977287a13385683204344e78816b48512",
        "active_solidworks_configuration": "FSA STEERING with GEOMETRY FINAL steering component",
        "motion_study_name_and_settings": "Design Study 1; 205 scenarios from -102 to +102 deg",
        "input_signal_identity": (
            "steering/pinion input angle with reported 1:1 steering-wheel relation; "
            "rack displacement = input_deg * 3.5 in/rev / 360 deg/rev"
        ),
        "output_signal_identity": "unresolved",
        "input_sign_and_unit": (
            "degrees; positive input increases native Rack Length and maps to canonical +y rack translation"
        ),
        "output_sign_unit_and_monitor_definition": "unresolved",
        "rack_center_or_zero_input_definition": "Steer Input = 0 deg is the centered design-study rack state",
        "static_toe_and_wheel_plane_reference": "unresolved",
        "evaluated_domain_and_stop_state": (
            "-102 to +102 deg maps to -0.0251883333 to +0.0251883333 m; "
            "nominal design travel is +/-1.0 in, not proof of installed physical stops"
        ),
    }

    report = {
        "geometry_id": geometry.geometry_id,
        "geometry_version": geometry.version,
        "authorization_id": "AUTH-STEER-0001",
        "sample_count": len(source_inputs_deg),
        "source_input_domain_deg": [source_inputs_deg[0], source_inputs_deg[-1]],
        "rack_metres_per_input_degree": RACK_TRAVEL_M_PER_INPUT_DEG,
        "mapped_source_rack_domain_m": [displacements[0], displacements[-1]],
        "declared_nominal_rack_domain_m": [
            geometry.rack.displacement_min,
            geometry.rack.displacement_max,
        ],
        "states": states,
        "level_e_missing_metadata": list(level_e_missing_metadata(metadata)),
        "comparison_status": "blocked_only_on_output_monitor_identity_and_required_heading_basis",
        "prohibited_interpretation": (
            "Dimension2 is not treated as upright rotation or road-wheel heading until its two reference entities and sign are reviewed"
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

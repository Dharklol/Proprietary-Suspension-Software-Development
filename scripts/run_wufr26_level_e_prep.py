#!/usr/bin/env python3
"""Generate a dense nominal steering sweep and report the Level E metadata gate."""

from __future__ import annotations

import json
from pathlib import Path

from pssd_steering import level_e_missing_metadata, load_geometry, solve_sweep


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    geometry = load_geometry(root / "configurations/steering/WUFR26_DESIGN_NOMINAL_V0.toml")

    sample_count = 205
    lower = geometry.rack.displacement_min
    upper = geometry.rack.displacement_max
    displacements = [lower + index * (upper - lower) / (sample_count - 1) for index in range(sample_count)]
    solved = solve_sweep(geometry, displacements)

    states = []
    for index, displacement in enumerate(displacements):
        left = solved["left"][index]
        right = solved["right"][index]
        states.append(
            {
                "rack_displacement_m": displacement,
                "left_status": left.status.value,
                "left_upright_rotation_rad": left.upright_rotation,
                "left_closure_residual_m": left.closure_length_residual,
                "left_singularity_ratio": left.singularity_ratio_to_reference,
                "right_status": right.status.value,
                "right_upright_rotation_rad": right.upright_rotation,
                "right_closure_residual_m": right.closure_length_residual,
                "right_singularity_ratio": right.singularity_ratio_to_reference,
            }
        )

    metadata = {
        "source_file_id_and_version": "box:2357045252883/version:2611346929683",
        "source_hash": "69d71c0977287a13385683204344e78816b48512",
        "active_solidworks_configuration": "unresolved",
        "motion_study_name_and_settings": "unresolved",
        "input_signal_identity": "unresolved",
        "output_signal_identity": "unresolved",
        "input_sign_and_unit": "Steer Input in degrees; physical identity/sign unresolved",
        "output_sign_unit_and_monitor_definition": "Dimension2 in degrees; definition unresolved",
        "rack_center_or_zero_input_definition": "zero input observed; construction unresolved",
        "static_toe_and_wheel_plane_reference": "nonzero toe confirmed; numerical basis unresolved",
        "evaluated_domain_and_stop_state": "-102 to +102 degree source domain; stop relation unresolved",
    }

    report = {
        "geometry_id": geometry.geometry_id,
        "geometry_version": geometry.version,
        "authorization_id": "AUTH-STEER-0001",
        "sample_count": sample_count,
        "rack_domain_m": [lower, upper],
        "states": states,
        "level_e_missing_metadata": list(level_e_missing_metadata(metadata)),
        "comparison_status": "blocked_until_signal_and_reference_metadata_are_reviewed",
        "prohibited_interpretation": (
            "upright rotation is not a SolidWorks monitor angle or road-wheel heading without a reviewed mapping"
        ),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

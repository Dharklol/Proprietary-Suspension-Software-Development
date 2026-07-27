#!/usr/bin/env python3
"""Generate BENCH-VEH-0007 WUFR static-gravity allocation diagnostics."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pssd_vehicle.force_coordinates import BodyPose
from pssd_vehicle.wufr_gravity import load_wufr_static_gravity_allocation


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data_catalog/wufr27_static_gravity_allocation_v0.toml"


def build_report() -> dict:
    allocation = load_wufr_static_gravity_allocation(SOURCE)
    pose = BodyPose(
        "WUFR27_NOMINAL_ROAD",
        "WUFR27_NOMINAL_ROAD_ORIGIN",
        "WUFR27_BODY_DRIVER_NO_FUEL_REFERENCE",
        "WUFR27_CG_DRIVER_NO_FUEL_REFERENCE",
    )
    body_gravity = allocation.sprung_body_generalized_gravity(pose)
    mass_error = abs(allocation.reconstructed_total_mass_kg - allocation.total_mass_kg)
    moment_residual = allocation.first_moment_residual_kg_m()
    max_moment_error = max(abs(v) for v in moment_residual)
    passed = mass_error <= 1.0e-12 and max_moment_error <= 1.0e-11
    if not passed:
        raise RuntimeError("BENCH-VEH-0007 mass/first-moment acceptance failed")
    return {
        "model_id": "MOD-VEH-0005",
        "authorization_id": "AUTH-VEH-0005",
        "authority": "reviewed prototype WUFR driver/no-fuel static-gravity allocation under ASM-VEH-0003; no road-reaction authority",
        "BENCH-VEH-0007": {
            "pass": True,
            "record_id": allocation.record_id,
            "assumption_id": allocation.assumption_id,
            "total_mass_kg": allocation.total_mass_kg,
            "unsprung_corner_mass_kg": [item.mass_kg for item in allocation.unsprung],
            "total_unsprung_mass_kg": allocation.total_unsprung_mass_kg,
            "sprung_mass_kg": allocation.sprung.mass_kg,
            "sprung_cg_source_m": list(allocation.sprung.source_position_m),
            "sprung_cg_body_offset_m": list(allocation.sprung.body_position_m or ()),
            "mass_recombination_error_kg": mass_error,
            "first_moment_residual_kg_m": list(moment_residual),
            "maximum_first_moment_error_kg_m": max_moment_error,
            "g_mps2": allocation.g_mps2,
            "sprung_weight_N": -allocation.sprung.force_N(allocation.g_mps2)[2],
            "each_nominal_unsprung_weight_N": -allocation.unsprung[0].force_N(allocation.g_mps2)[2],
            "sprung_body_generalized_gravity_nominal": list(body_gravity.generalized_force),
            "installed_as_built_authority": allocation.installed_as_built_authority,
            "maneuver_unsprung_inertia_authority": allocation.maneuver_unsprung_inertia_authority,
            "wheel_gravity_generalized_force_hardcoded": False,
            "road_reactions_available": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("wufr_static_gravity_report.json"))
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    report = build_report()
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        b = report["BENCH-VEH-0007"]
        print(
            "MOD-VEH-0005: "
            f"m_total={b['total_mass_kg']:.9f} kg, "
            f"m_sprung={b['sprung_mass_kg']:.9f} kg, "
            f"moment_error={b['maximum_first_moment_error_kg_m']:.3g} kg*m"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

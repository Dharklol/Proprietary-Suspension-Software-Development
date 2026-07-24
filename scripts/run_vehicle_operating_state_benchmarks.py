#!/usr/bin/env python3
"""Generate source-preserving vehicle operating-state provider reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tomllib

from pssd_vehicle import (
    LATERAL_TIRE_DEMAND_FIELDS,
    TIRE_OPERATING_POINT_FIELDS,
    front_inside_outside_assignment,
    load_vehicle_operating_state_set,
)


def _wheel_record(wheel) -> dict:
    return {
        "position": wheel.position.value,
        "normal_load_n": wheel.normal_load_n,
        "inclination_deg": wheel.inclination_deg,
        "pressure_kpa": wheel.pressure_kpa,
        "lateral_force_demand_n": wheel.lateral_force_demand_n,
        "longitudinal_force_demand_n": wheel.longitudinal_force_demand_n,
        "missing_tire_operating_point_fields": wheel.completeness_record(
            TIRE_OPERATING_POINT_FIELDS
        ),
        "missing_lateral_tire_demand_fields": wheel.completeness_record(
            LATERAL_TIRE_DEMAND_FIELDS
        ),
        "provenance": dict(wheel.provenance),
    }


def build_report() -> dict:
    root = Path(__file__).resolve().parents[1]
    fixture = (
        root
        / "benchmarks"
        / "vehicle"
        / "WUFR27_SUSPENSION_CALCULATIONS_OPERATING_STATES_V0.toml"
    )
    state_set = load_vehicle_operating_state_set(fixture)
    with fixture.open("rb") as stream:
        raw = tomllib.load(stream)

    states: list[dict] = []
    for state in state_set.states:
        assignment = front_inside_outside_assignment(state)
        states.append(
            {
                "state_id": state.state_id,
                "role": state.role.value,
                "turn_direction": state.turn_direction.value,
                "ax_g": state.ax_g,
                "ay_g": state.ay_g,
                "speed_mps": state.speed_mps,
                "state_weight": state.state_weight,
                "total_normal_load_n": state.total_normal_load_n,
                "front_inside_position": assignment.inside_position.value,
                "front_outside_position": assignment.outside_position.value,
                "front_inside_normal_load_n": assignment.inside_wheel.normal_load_n,
                "front_outside_normal_load_n": assignment.outside_wheel.normal_load_n,
                "wheels": [_wheel_record(wheel) for wheel in state.wheels],
                "authority": state.authority,
                "provenance": dict(state.provenance),
            }
        )

    rejected = raw.get("source_audit", {}).get("rejected_states", [])
    return {
        "result_id": "VEHICLE-OPERATING-STATE-PROVIDER-BENCHMARKS-V0",
        "benchmark_id": "BENCH-VEH-0001",
        "model_id": "MOD-VEH-0001",
        "steering_consumer_model_id": "MOD-STEER-0002",
        "state_set_id": state_set.state_set_id,
        "source_type": state_set.source_type,
        "source_path": state_set.source_path,
        "source_revision": state_set.source_revision,
        "canonical_body_axes": state_set.canonical_body_axes,
        "lateral_acceleration_convention": state_set.lateral_acceleration_convention,
        "state_count": len(state_set.states),
        "states": states,
        "rejected_source_states": rejected,
        "source_provenance": dict(state_set.provenance),
        "authority_boundary": (
            "MOD-VEH-0001 stores explicit upstream vehicle/wheel states and missing-data "
            "reasons only. It does not calculate load transfer, aero, suspension motion, "
            "camber, tire pressure, Fy/Fx demand, or vehicle equilibrium. The selected "
            "1.2g source states are current development evidence and remain evidence_only. "
            "The current workbook 1.7g left-turn draft is rejected because it contains a "
            "negative rear-left normal load; no clipping or silent repair is permitted."
        ),
    }


def summary_report(report: dict) -> dict:
    return {
        "result_id": report["result_id"],
        "benchmark_id": report["benchmark_id"],
        "model_id": report["model_id"],
        "state_set_id": report["state_set_id"],
        "source_revision": report["source_revision"],
        "state_count": report["state_count"],
        "states": [
            {
                "state_id": state["state_id"],
                "role": state["role"],
                "turn_direction": state["turn_direction"],
                "ay_g": state["ay_g"],
                "speed_mps": state["speed_mps"],
                "total_normal_load_n": state["total_normal_load_n"],
                "front_inside_position": state["front_inside_position"],
                "front_outside_position": state["front_outside_position"],
                "front_inside_normal_load_n": state["front_inside_normal_load_n"],
                "front_outside_normal_load_n": state["front_outside_normal_load_n"],
            }
            for state in report["states"]
        ],
        "rejected_source_states": report["rejected_source_states"],
        "authority_boundary": report["authority_boundary"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = build_report()
    payload = summary_report(report) if arguments.summary else report
    serialized = json.dumps(payload, indent=2, sort_keys=True)
    if arguments.output is not None:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

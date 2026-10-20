#!/usr/bin/env python3
"""Reproducible synthetic rigid-versus-elastic steering comparison JSON report.

Synthetic wheel geometry/transmission; user-supplied WUFR-27 shaft dimensions.
This is NOT WUFR-27 as-built road-wheel heading or tire self-aligning prediction.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from pssd_steering import load_geometry
from pssd_steering.compliance import (
    DoubleDProfile, ClevisPinScreen, ToleranceEnvelope,
    wufr27_provisional_circular_spans,
)
from pssd_steering.compliance_bridge import (
    PrescribedTorqueInput, SteeringTransmission, evaluate_prescribed_torque_sweep,
)


def _degrees_if_available(value: float | None) -> float | None:
    return math.degrees(value) if value is not None else None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    geometry = load_geometry(root / "benchmarks/steering/GEO-STEER-BASIC-001.toml")
    transmission = SteeringTransmission(
        1.0, 0.010, "BENCH-STEER synthetic; 0.010 m/rad is NOT the WUFR rack ratio",
    )
    angles = tuple(math.radians(x) for x in (-25, -15, 0, 15, 25))
    cases = tuple(
        PrescribedTorqueInput(
            steering_wheel_rad=angle,
            input_torque_nm=math.copysign(torque, angle) if angle else 0.0,
            torque_authority="prescribed illustrative input torque; not measured",
        )
        for torque in (0.0, 23.69800619, 35.54700928)
        for angle in angles
    )
    results = evaluate_prescribed_torque_sweep(
        geometry, cases, transmission,
        spans=wufr27_provisional_circular_spans(),
    )
    states = []
    for row in results:
        state = {
            "driver_angle_deg": math.degrees(row.case.steering_wheel_rad),
            "torque_nm": row.case.input_torque_nm,
            "elastic_twist_deg": row.elastic_twist.twist_deg,
            "rigid_rack_m": row.rigid_transmission.rack_displacement,
            "elastic_rack_m": row.elastic_transmission.rack_displacement,
            "valid": row.both_mechanisms_valid,
        }
        for side in ("left", "right"):
            comparison = getattr(row, side)
            state[f"{side}_rigid_incremental_heading_deg"] = _degrees_if_available(
                comparison.rigid_heading.incremental_heading
            )
            state[f"{side}_elastic_incremental_heading_deg"] = _degrees_if_available(
                comparison.elastic_heading.incremental_heading
            )
            state[f"{side}_delta_incremental_heading_deg"] = _degrees_if_available(
                comparison.incremental_heading_difference_rad
            )
            state[f"{side}_rigid_failure_code"] = (
                comparison.rigid_position.failure_code.value
                if comparison.rigid_position.failure_code else None
            )
            state[f"{side}_elastic_failure_code"] = (
                comparison.elastic_position.failure_code.value
                if comparison.elastic_position.failure_code else None
            )
        states.append(state)

    profile = DoubleDProfile()
    output = {
        "model": "WUFR27_PROVISIONAL_ELASTIC_BRIDGE_V1",
        "status": "synthetic_kinematic_benchmark_not_physical_validation",
        "rigid_geometry_id": geometry.geometry_id,
        "input_torque_authority": "illustrative prescribed; high case is factored structural torque",
        "synthetic_transmission_authority": transmission.authority,
        "shaft_span_assumption": "circular-only / 80 GPa steel / common shaft torque / 1:1",
        "d_profile_major_diameter_in": 2 * profile.radius_in,
        "d_profile_across_flats_in": profile.across_flats_in,
        "d_profile_engagement_in": profile.engagement_in,
        "inhouse_across_flats_tolerance_in": 0.005,
        "relative_fit_clearance_envelope_in":
            ToleranceEnvelope(.472, .005, .005).clearance_range_in,
        "pin_double_shear_allowable_n_screen_only":
            ClevisPinScreen().allowable_shear_force_n(),
        "sample_states": states,
        "excluded": [
            "double-D profile torsional rigidity",
            "actual WUFR rack gearing and as-built heading basis",
            "backlash, joint wear, hysteresis, gear/rack compliance",
            "tire aligning-moment equilibrium",
            "pin bending/lug failure, measured pin axial forces",
        ],
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

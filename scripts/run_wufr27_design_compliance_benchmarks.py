#!/usr/bin/env python3
"""WUFR-27 nominal design-source rigid vs elastic projected-heading sweep report.

Only the rack/input relation and nominal wheel geometry are WUFR-specific.
All torques are prescribed illustrative cases, NOT measured steering effort.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from pssd_steering.compliance import wufr27_provisional_circular_spans
from pssd_steering.compliance_bridge import PrescribedTorqueInput
from pssd_steering.wufr27_design_compliance import (
    evaluate_wufr27_design_source_sweep, load_wufr27_design_source,
)


def _deg(value: float | None) -> float | None:
    return math.degrees(value) if value is not None else None


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    source = load_wufr27_design_source(root)
    design_input_degrees = (-100, -75, -50, -25, 0, 25, 50, 75, 100)
    # Workbook column C15 = 14.444... (cornering), C10 = 23.698... (unfactored
    # parked), C9 = 35.547... (factored parked); NONE are measured torque.
    torque_scenarios = (
        ("zero_torque_rigid_baseline", 0.0),
        ("calculated_cornering_column_moment", 14.44408009),
        ("calculated_unfactored_parked_column_moment", 23.69800619),
        ("calculated_factored_parked_column_moment", 35.54700928),
    )
    inputs = []
    scenario_by_index = []
    for scenario, magnitude in torque_scenarios:
        for deg in design_input_degrees:
            # Input shaft resisting-torque sign is deliberately a chosen
            # hypothetical scenario, NOT a prediction of its actual polarity.
            signed = math.copysign(magnitude, deg) if deg else 0.0
            inputs.append(PrescribedTorqueInput(
                steering_wheel_rad=math.radians(deg),
                input_torque_nm=signed,
                torque_authority=(
                    f"{scenario}; sign chosen to oppose commanded input; "
                    "calculated load case, not measured driver torque"
                ),
            ))
            scenario_by_index.append(scenario)

    results = evaluate_wufr27_design_source_sweep(
        source, tuple(inputs), spans=wufr27_provisional_circular_spans()
    )
    output_rows = []
    for name, result in zip(scenario_by_index, results):
        c = result.comparison
        row = {
            "load_scenario": name,
            "driver_command_deg": _deg(c.case.steering_wheel_rad),
            "prescribed_input_torque_nm": c.case.input_torque_nm,
            "free_span_elastic_twist_deg": c.elastic_twist.twist_deg,
            "rigid_rack_mm": 1000 * c.rigid_transmission.rack_displacement,
            "loaded_rack_mm": 1000 * c.elastic_transmission.rack_displacement,
            "rigid_and_loaded_closure_valid": c.both_mechanisms_valid,
        }
        for side in ("left", "right"):
            heading = getattr(result, side)
            row[f"{side}_rigid_total_deg"] = _deg(heading.rigid_total_rad)
            row[f"{side}_loaded_total_deg"] = _deg(heading.loaded_total_rad)
            row[f"{side}_rigid_incremental_deg"] = _deg(heading.rigid_incremental_rad)
            row[f"{side}_loaded_incremental_deg"] = _deg(heading.loaded_incremental_rad)
            row[f"{side}_loaded_minus_rigid_incremental_deg"] = _deg(
                heading.delta_incremental_rad
            )
            row[f"{side}_unavailable_reason"] = heading.unavailable_reason
        output_rows.append(row)
    report = {
        "report": "WUFR27_NOMINAL_DESIGN_SOURCE_COMPLIANCE_V1",
        "evidence_role": source.evidence_role,
        "geometry_id": source.geometry.geometry_id,
        "source_parameter_id": source.source_parameter_id,
        "transmission_authority": source.transmission.authority,
        "rack_m_per_input_radian": (
            source.transmission.rack_m_per_pinion_rad
            * source.transmission.pinion_angle_per_input_rad
        ),
        "reference": (
            "canonical ISO +x forward, +y left, +z up, "
            "positive signed rack +y; toe-out positive side-local"
        ),
        "elastic_assumption": (
            "four circular free spans only, 80 GPa provisional G, "
            "equal input torque in all segments under nominal 1:1 bevel relation"
        ),
        "torque_source": (
            "Suspension Calculations 2026 Google workbook, Steering Column Forces; "
            "C15 cornering, C10 unfactored parked, C9 factored parked. "
            "Magnitudes not measured driver torque; signs illustrative."
        ),
        "not_supported": (
            "installed/as-built steering map or physical loaded wheel angle; "
            "tire moment equilibrium, joint backlash, bending, "
            "gear/rack/QR compliance, or complete double-D torsion"
        ),
        "states": output_rows,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

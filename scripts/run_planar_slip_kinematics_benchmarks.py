#!/usr/bin/env python3
"""Generate BENCH-VEH-0002 planar wheel-velocity/tire-slip diagnostics."""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
from pssd_vehicle import (
    FourWheelPlanarGeometry, PlanarMotionSample, WheelPosition,
    front_required_heading_pair, tire_slip_kinematics, wheel_center_kinematics,
)


def build_report() -> dict:
    geometry = FourWheelPlanarGeometry(0.8, 0.7, 1.2, 1.2, authority="synthetic software evidence")
    field_motion = PlanarMotionSample(10.0, 0.3, 1.5)
    fl = wheel_center_kinematics(field_motion, geometry.location(WheelPosition.FRONT_LEFT))
    fr = wheel_center_kinematics(field_motion, geometry.location(WheelPosition.FRONT_RIGHT))

    r = 1.25; radius = 8.0
    ack_motion = PlanarMotionSample(radius*r, r*geometry.cg_to_rear_axle_m, r)
    ack = front_required_heading_pair(ack_motion, geometry, left_required_slip_rad=0.0, right_required_slip_rad=0.0)
    half_track = 0.5*geometry.front_wheel_center_track_m
    expected_left = math.atan2(geometry.wheelbase_m, radius-half_track)
    expected_right = math.atan2(geometry.wheelbase_m, radius+half_track)

    parallel = math.radians(5.0)
    relative = {}
    for label, s in (("rear_to_front_interval",0.0),("front_axle",geometry.cg_to_front_axle_m),("forward_of_front",1.3)):
        motion = PlanarMotionSample(10.0, -s, 1.0)
        left = tire_slip_kinematics(motion, geometry.location(WheelPosition.FRONT_LEFT), parallel)
        right = tire_slip_kinematics(motion, geometry.location(WheelPosition.FRONT_RIGHT), parallel)
        relative[label] = {
            "S_m": motion.velocity_center_longitudinal_m,
            "left_slip_deg": math.degrees(left.slip_angle_rad),
            "right_slip_deg": math.degrees(right.slip_angle_rad),
            "left_minus_right_slip_deg": math.degrees(left.slip_angle_rad-right.slip_angle_rad),
        }
    return {
        "benchmark_id":"BENCH-VEH-0002",
        "authority":"synthetic planar kinematics software evidence only",
        "equations":["EQ-VEH-0001","EQ-VEH-0002","EQ-VEH-0003"],
        "rigid_body_field":{"front_left_vx_mps":fl.velocity_x_mps,"front_left_vy_mps":fl.velocity_y_mps,"front_right_vx_mps":fr.velocity_x_mps,"front_right_vy_mps":fr.velocity_y_mps},
        "rear_axle_velocity_center_zero_slip":{"S_m":ack_motion.velocity_center_longitudinal_m,"left_heading_deg":math.degrees(ack.left_required_wheel_heading_rad),"right_heading_deg":math.degrees(ack.right_required_wheel_heading_rad),"left_expected_deg":math.degrees(expected_left),"right_expected_deg":math.degrees(expected_right),"max_abs_error_deg":max(abs(math.degrees(ack.left_required_wheel_heading_rad-expected_left)),abs(math.degrees(ack.right_required_wheel_heading_rad-expected_right)))},
        "parallel_steer_relative_slip":relative,
        "physics_exclusions":{"vehicle_equilibrium":False,"tire_force_model":False,"load_transfer":False,"motion_response_prediction":False},
    }


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,default=Path("planar_slip_kinematics_report.json")); p.add_argument("--summary",action="store_true"); a=p.parse_args()
    r=build_report(); a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    if a.summary:
        rel=r["parallel_steer_relative_slip"]
        print(f"BENCH-VEH-0002: ackermann_error_deg={r['rear_axle_velocity_center_zero_slip']['max_abs_error_deg']:.3g}, interval_dalpha={rel['rear_to_front_interval']['left_minus_right_slip_deg']:.6g}, S=a1_dalpha={rel['front_axle']['left_minus_right_slip_deg']:.6g}, S>a1_dalpha={rel['forward_of_front']['left_minus_right_slip_deg']:.6g}")
    return 0
if __name__ == "__main__": raise SystemExit(main())

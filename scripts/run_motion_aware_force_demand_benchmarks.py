#!/usr/bin/env python3
"""Generate BENCH-STEER-0023 motion-aware force-demand steering diagnostics."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from pssd_steering import load_geometry
from pssd_steering.optimization import (
    evaluate_operating_state_candidate, load_historical_fit_target, load_pose_set,
    load_requirement_set, resolve_candidate,
)
from pssd_steering.optimization.motion_force_targets import (
    MotionAwareForceDemandStateDefinition,
    build_motion_aware_force_demand_operating_target_set,
    motion_aware_force_demand_heading_pair,
)
from pssd_tire import TireOperatingPoint, load_lateral_force_branch_set
from pssd_vehicle import FourWheelPlanarGeometry, PlanarMotionSample, PlanarMotionSchedule


def _schedule(sampling, state_id: str, s_m: float) -> PlanarMotionSchedule:
    maximum=max(abs(x) for x in sampling.inputs); samples=[]
    for x in sampling.inputs:
        q=abs(x)/maximum
        if x == 0.0: samples.append(PlanarMotionSample(5.0,0.0,0.0)); continue
        sign=1.0 if x>0 else -1.0; r=sign*2.0*q
        samples.append(PlanarMotionSample(5.0,-s_m*r,r))
    return PlanarMotionSchedule(state_id=state_id,samples=tuple(samples),authority="synthetic u-v-r schedule; software evidence only",provenance=(("physical_authority","none"),))


def build_report() -> dict:
    root=Path(__file__).resolve().parents[1]
    steering=load_geometry(root/"configurations/steering/WUFR27_STEERING_BASELINE_V0.toml")
    requirement=load_requirement_set(root/"configurations/steering/STEERING_INVERSE_DESIGN_DEV_V0.toml")
    sampling=load_historical_fit_target(root/"benchmarks/steering/WUFR26_27_HISTORICAL_RESPONSE_REGRESSION_V0.toml")
    poses=load_pose_set(root/"benchmarks/steering/STEERING_SYNTHETIC_POSE_SET_V0.toml")
    branches=load_lateral_force_branch_set(root/"benchmarks/tires/SYNTHETIC_FORCE_DEMAND_BRANCHES_V0.toml")
    assert steering.wheelbase is not None
    geometry=FourWheelPlanarGeometry(0.8,steering.wheelbase-0.8,1.2,1.2,authority="synthetic wheel-center geometry")
    inside=TireOperatingPoint(222.0,0.0,83.0); outside=TireOperatingPoint(1112.0,2.0,83.0)
    maximum=max(abs(x) for x in sampling.inputs); util=tuple(abs(x)/maximum for x in sampling.inputs)
    inside_force=tuple(300.0*q for q in util); outside_force=tuple(2500.0*q for q in util)
    defs=(
        MotionAwareForceDemandStateDefinition("nominal",_schedule(sampling,"nominal",-geometry.cg_to_rear_axle_m),inside,outside,inside_force,outside_force,authority="synthetic rear-axle velocity-center state"),
        MotionAwareForceDemandStateDefinition("symmetric_bump_5mm",_schedule(sampling,"symmetric_bump_5mm",geometry.cg_to_front_axle_m),inside,outside,inside_force,outside_force,authority="synthetic S=a1 velocity-center state"),
    )
    targets=build_motion_aware_force_demand_operating_target_set(sampling,poses,geometry,branches,defs,target_set_id="SYNTHETIC_MOTION_AWARE_FORCE_DEMAND_V0",version="0.1.0",authority="BENCH-STEER-0023 software evidence only",source_path="scripts/run_motion_aware_force_demand_benchmarks.py")
    rear_full=motion_aware_force_demand_heading_pair(PlanarMotionSample(5.0,-(-geometry.cg_to_rear_axle_m)*2.0,2.0),geometry,branches,inside,outside,inside_lateral_force_magnitude_n=300.0,outside_lateral_force_magnitude_n=2500.0,left_pose_reference_heading_rad=0.0,right_pose_reference_heading_rad=0.0)
    front_full=motion_aware_force_demand_heading_pair(PlanarMotionSample(5.0,-geometry.cg_to_front_axle_m*2.0,2.0),geometry,branches,inside,outside,inside_lateral_force_magnitude_n=300.0,outside_lateral_force_magnitude_n=2500.0,left_pose_reference_heading_rad=0.0,right_pose_reference_heading_rad=0.0)
    candidate=resolve_candidate(requirement,candidate_id="MOTION-AWARE-REFERENCE-CANDIDATE")
    evaluation=evaluate_operating_state_candidate(steering,requirement,candidate,targets,poses)
    return {
        "benchmark_id":"BENCH-STEER-0023",
        "authorization_ids":["AUTH-STEER-0004","AUTH-VEH-0002","AUTH-STEER-0003"],
        "authority":"synthetic motion/tire software evidence only",
        "same_tire_demands_velocity_center_comparison":{
            "inside_required_slip_deg":rear_full.left_required_slip_deg,
            "outside_required_slip_deg":rear_full.right_required_slip_deg,
            "rear_axle_velocity_center":{"S_m":-geometry.cg_to_rear_axle_m,"left_heading_deg":rear_full.left_required_incremental_heading_deg,"right_heading_deg":rear_full.right_required_incremental_heading_deg,"regime":rear_full.regime.value if rear_full.regime else "not_classified"},
            "front_axle_velocity_center":{"S_m":geometry.cg_to_front_axle_m,"left_heading_deg":front_full.left_required_incremental_heading_deg,"right_heading_deg":front_full.right_required_incremental_heading_deg,"regime":front_full.regime.value if front_full.regime else "not_classified"},
        },
        "target_states":{
            item.state_id:{"regime_counts":dict(item.provenance)["regime_counts"],"ackermann_anchor_used":dict(item.provenance)["ackermann_anchor_used"],"target_mapping":dict(item.provenance)["target_mapping"],"left_endpoint_deg":[item.left_outputs[0],item.left_outputs[-1]],"right_endpoint_deg":[item.right_outputs[0],item.right_outputs[-1]]}
            for item in targets.state_targets
        },
        "reference_candidate":{"feasible":evaluation.feasible,"total_objective":evaluation.total_objective,"objective_count":len(evaluation.objectives)},
        "production_claim":False,
    }


def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--output",type=Path,default=Path("motion_aware_force_demand_report.json")); p.add_argument("--summary",action="store_true"); a=p.parse_args(); r=build_report(); a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    if a.summary:
        c=r["same_tire_demands_velocity_center_comparison"]; print(f"BENCH-STEER-0023: same_slips={c['inside_required_slip_deg']:.6g}/{c['outside_required_slip_deg']:.6g} deg, rear_S_regime={c['rear_axle_velocity_center']['regime']}, front_S_regime={c['front_axle_velocity_center']['regime']}, feasible={r['reference_candidate']['feasible']}, objective={r['reference_candidate']['total_objective']}")
    return 0
if __name__=="__main__": raise SystemExit(main())

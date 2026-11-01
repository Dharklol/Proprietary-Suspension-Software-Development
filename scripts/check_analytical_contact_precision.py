#!/usr/bin/env python3
"""Re-solve the retained CI seed under two explicitly tighter contact controls."""
from copy import deepcopy
from dataclasses import asdict
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from pssd_vehicle.analytical_workflow import (
    DEFAULT_PLAN, build_geometry, load_plan, source_manifest, solver_config,
    load_wufr_static_equilibrium_provider, R25BDevelopmentCorneringTireProvider,
    SYMMETRY_ASSUMPTION_ID, SYMMETRY_POLICY,
)
from pssd_vehicle.steady_cornering import CorneringCase, solve_cornering


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    plan=load_plan(ROOT/DEFAULT_PLAN)
    archive_path=ROOT/'benchmarks/vehicle/analytical_workflow_rejected_ci_case_v0.1.0.json'
    archive=json.loads(archive_path.read_text())
    seed=archive['rejected_cell']
    components=load_wufr_static_equilibrium_provider(**{k:ROOT/v for k,v in plan['sources'].items()})
    tire=R25BDevelopmentCorneringTireProvider(accepted_assumption_id=SYMMETRY_ASSUMPTION_ID,policy=SYMMETRY_POLICY)
    records=[];config=solver_config(plan)
    for tolerance in (1e-15,5e-16):
        variant=deepcopy(plan);variant['reference']['road_gap_tolerance_m']=tolerance
        geometry=build_geometry(variant,variant['candidates'][0],variant['assumptions'][0],components)
        raw=dict(seed['case'])
        for key in ('pressures_pa','accepted_assumptions'):raw[key]=tuple(raw[key])
        raw.update(configuration_id=geometry.components.source.configuration_id,
            geometry_revision=geometry.geometry_revision,setup_revision=geometry.setup_revision,tire_revision=tire.tire_revision)
        case=CorneringCase(**raw)
        result=solve_cornering(case,tuple(seed['initial_coordinates']),geometry_provider=geometry,tire_provider=tire,config=config)
        item={'contact_tolerance_m':tolerance,'case':asdict(case),'result':asdict(result),
            'branch_signature':None if result.evaluation is None else result.evaluation.branch_signature,
            'force_norm_n':None,'moment_norm_nm':None}
        if result.evaluation is not None:
            wrench=result.evaluation.physical_wrench
            item.update(force_norm_n=math.hypot(*wrench.resultant_force_N),moment_norm_nm=math.hypot(*wrench.resultant_moment_Nm))
        records.append(item)
        print(json.dumps({'tolerance_m':tolerance,'ok':result.ok,'iterations':result.iterations,
            'scaled_residual_norm':result.scaled_residual_norm}),flush=True)
    delta=max(abs(x-y)/s for x,y,s in zip(records[0]['result']['coordinates'],records[1]['result']['coordinates'],config.coordinate_scales))
    limit=1e-5
    passed=(all(r['result']['ok'] and r['force_norm_n']<=1e-6 and r['moment_norm_nm']<=1e-6 for r in records)
        and records[0]['branch_signature']==records[1]['branch_signature'] and delta<=limit)
    report={'status':'pass' if passed else 'fail','scope':'contact_precision_control_only',
        'python_version':sys.version,'common_initial_coordinates':seed['initial_coordinates'],
        'scaled_coordinate_difference_limit':limit,'maximum_scaled_coordinate_difference':delta,
        'solver_config':asdict(config),'source_hashes':source_manifest(plan,ROOT/DEFAULT_PLAN),
        'probe_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'archive_sha256':hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        'variants':records,'objective_weight':0.,'design_ranking_permitted':False}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':report['status'],'maximum_scaled_coordinate_difference':delta}),flush=True)
    return 0 if passed else 1


if __name__=='__main__':raise SystemExit(main())

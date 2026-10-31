#!/usr/bin/env python3
"""Exercise convergence from the same explicit off-root seed under each control."""
from dataclasses import asdict, replace
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import tomllib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from pssd_vehicle.steady_cornering import solve_cornering
from pssd_vehicle.wufr_steady_cornering_geometry import WUFRCorneringGeometryProvider
from scripts.run_native_sensitivity_study import (
    StudyControls, _case, numerical_variants, output_values, verify_sources,
)
from scripts.run_wufr_steady_cornering_benchmarks import _sample
from tests.wufr_cornering_fixture import providers, solver_config

COORDINATE_ORDER=('body_heave_m','roll_rad','pitch_rad','sideslip_rad','rack_m','holder_force_n',
                  'Fz_front_left_n','Fz_front_right_n','Fz_rear_left_n','Fz_rear_right_n')


def common_perturbed_seed(anchor,order,offsets,configs):
    if tuple(order)!=COORDINATE_ORDER or len(offsets)!=10 or len(anchor)!=10:
        raise ValueError('Explicit ten-coordinate order and offsets required')
    if not all(math.isfinite(x) for x in offsets) or not any(offsets):
        raise ValueError('Finite nonzero off-root perturbation required')
    seed=tuple(a+d for a,d in zip(anchor,offsets))
    if not all(all(lo<=x<=hi for x,lo,hi in zip(seed,c.lower_bounds,c.upper_bounds)) for c in configs):
        raise ValueError('Common perturbed seed must be inside every declared control box')
    return seed


def refined_contact_geometry(geometry,tolerance_m):
    if (not math.isfinite(tolerance_m) or tolerance_m<=0
            or tolerance_m>=geometry.road.config.road_gap_tolerance_m):
        raise ValueError('Explicit contact precision must strictly tighten the original tolerance')
    road=replace(geometry.road,config=replace(geometry.road.config,road_gap_tolerance_m=tolerance_m))
    refined=WUFRCorneringGeometryProvider(replace(geometry.components,road_contact=road))
    if refined.geometry_revision!=geometry.geometry_revision:
        raise ValueError('Numerical precision refinement changed physical geometry identity')
    return refined


def run_recovery(study,order,offsets,road_gap_tolerance_m,comparison_road_gap_tolerance_m,progress=None):
    if study['objective_weight']!=0. or study['physical_or_ranking_authority'] is not False:
        raise ValueError('Unpromoted study required')
    verify_sources(study['source_hashes'])
    values=dict(study['controls']); values['pressure_steps_pa']=tuple(values['pressure_steps_pa'])
    controls=StudyControls(**values)
    original_geometry,tire=providers()
    if comparison_road_gap_tolerance_m>=road_gap_tolerance_m:
        raise ValueError('Comparison contact tolerance must be tighter than primary recovery precision')
    geometry=refined_contact_geometry(original_geometry,road_gap_tolerance_m)
    finer_geometry=refined_contact_geometry(original_geometry,comparison_road_gap_tolerance_m)
    configs=numerical_variants(solver_config(),controls)
    configs['tighter_contact_root']=configs['anchor']
    records=[]
    for direction in study['directions']:
        sign=direction['direction_sign']
        anchor=next(r for r in direction['numerical'] if r['tag']=='numerical_anchor')
        if not anchor['comparison_supported']:
            raise ValueError('Accepted numerical anchor required')
        coordinates=anchor['result']['coordinates']
        guess=common_perturbed_seed(coordinates,order,offsets,configs.values())
        record={'direction_sign':sign,'common_initial_coordinates':guess,
                'reference_coordinates':coordinates,'variants':[],'passed':True}
        records.append(record)
        for tag,config in configs.items():
            active_geometry=finer_geometry if tag=='tighter_contact_root' else geometry
            c=_case(anchor['case'],active_geometry,tire,sign,controls.numerical_curvature_magnitude_per_m,
                    f'numerical_recovery_{sign}:{tag}')
            result=solve_cornering(c,guess,geometry_provider=active_geometry,tire_provider=tire,config=config)
            same_branch=(result.evaluation is not None and
                tuple(result.evaluation.branch_signature)==tuple(anchor['branch_signature']))
            actually_iterated=(result.iterations>0 and bool(result.residual_history) and
                result.residual_history[0]>config.scaled_residual_tolerance)
            difference=None if not result.ok else max(abs(x-y)/scale for x,y,scale in
                zip(result.coordinates,coordinates,configs['anchor'].coordinate_scales))
            passed=(result.ok and same_branch and actually_iterated and
                    difference<=controls.numerical_coordinate_difference_limit)
            item={'variant':tag,'solver_config':asdict(config),'result':_sample(result),
                'native_road_config':asdict(active_geometry.road.config),
                'initial_scaled_residual':result.residual_history[0] if result.residual_history else None,
                'actually_iterated':actually_iterated,'same_source_branch':same_branch,
                'maximum_scaled_coordinate_change':difference,
                'outputs':output_values(result),'passed':passed}
            record['variants'].append(item)
            record['passed']=record['passed'] and passed
            if progress is not None:progress(sign,item)
    return {'status':'pass' if all(r['passed'] for r in records) else 'fail',
        'scope':'common_off_root_numerical_recovery_only','coordinate_order':tuple(order),
        'coordinate_offsets':tuple(offsets),'difference_limit':controls.numerical_coordinate_difference_limit,
        'original_native_road_config':asdict(original_geometry.road.config),
        'road_gap_tolerance_m':road_gap_tolerance_m,
        'comparison_road_gap_tolerance_m':comparison_road_gap_tolerance_m,
        'geometry_revision':geometry.geometry_revision,
        'primary_precision_setup_revision':geometry.setup_revision,
        'comparison_precision_setup_revision':finer_geometry.setup_revision,
        'directions':records,'objective_weight':0.,'physical_or_ranking_authority':False}


def compact_recovery(report):
    summary={k:v for k,v in report.items() if k!='directions'}
    summary['directions']=[]
    for direction in report['directions']:
        record={k:v for k,v in direction.items() if k!='variants'}
        record['variants']=[]
        for item in direction['variants']:
            row={k:v for k,v in item.items() if k not in ('result','solver_config')}
            row.update({'ok':item['result']['ok'],'iterations':item['result']['iterations'],
                'failure_code':item['result']['failure_code'],
                'physical_force_norm_n':item['result'].get('physical_force_norm_n'),
                'physical_moment_norm_nm':item['result'].get('physical_moment_norm_nm')})
            record['variants'].append(row)
        summary['directions'].append(record)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study',type=Path,required=True)
    parser.add_argument('--controls',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--summary-output',type=Path,required=True)
    args=parser.parse_args()
    study=json.loads(args.study.read_text())
    controls=tomllib.loads(args.controls.read_text())
    def progress(sign,item):
        print(json.dumps({'direction':sign,'variant':item['variant'],'passed':item['passed'],
            'iterations':item['result']['iterations'],'maximum_scaled_change':item['maximum_scaled_coordinate_change'],
            'failure':item['result']['failure_code']}),flush=True)
    report=run_recovery(study,controls['coordinate_order'],controls['coordinate_offsets'],
        controls['road_gap_tolerance_m'],controls['comparison_road_gap_tolerance_m'],progress)
    paths=('scripts/run_native_numerical_recovery.py','tests/test_native_numerical_recovery.py')
    report['source_hashes']={**study['source_hashes'],**{
        p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}
    report['input_study_sha256']=hashlib.sha256(args.study.read_bytes()).hexdigest()
    report['recovery_controls_sha256']=hashlib.sha256(args.controls.read_bytes()).hexdigest()
    summary=compact_recovery(report)
    for path,value in ((args.output,report),(args.summary_output,summary)):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':report['status']},indent=2))
    return 0 if report['status']=='pass' else 1


if __name__=='__main__':raise SystemExit(main())

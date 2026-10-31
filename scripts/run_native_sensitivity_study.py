#!/usr/bin/env python3
"""Re-equilibrated native numerical-control and physical-input response study.

Saved coordinates are source-checked seeds only. Pressure responses at the
baseline knot are separate left/right finite-step differences, not a smoothed
or centrally averaged tire derivative. No design ranking or setup advice.
"""
from dataclasses import asdict, dataclass, replace
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import tomllib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from pssd_vehicle.steady_cornering import CorneringCase, solve_cornering
from scripts.run_native_envelope_bound_control import widen_sideslip_bound
from scripts.run_wufr_steady_cornering_benchmarks import _sample
from tests.wufr_cornering_fixture import providers, solver_config


@dataclass(frozen=True)
class StudyControls:
    physical_curvature_magnitude_per_m: float
    numerical_curvature_magnitude_per_m: float
    pressure_steps_pa: tuple[float,...]
    numerical_sideslip_bound_rad: float
    wider_sideslip_bound_rad: float
    fd_step_multiplier: float
    front_arb_target: int
    rear_arb_target: int
    numerical_coordinate_difference_limit: float

    def __post_init__(self):
        positive=(self.physical_curvature_magnitude_per_m,self.numerical_curvature_magnitude_per_m,
            self.numerical_sideslip_bound_rad,self.wider_sideslip_bound_rad,
            self.fd_step_multiplier,self.numerical_coordinate_difference_limit,*self.pressure_steps_pa)
        if not all(math.isfinite(x) and x>0 for x in positive):
            raise ValueError('Explicit finite positive controls required')
        if len(self.pressure_steps_pa)!=2 or self.pressure_steps_pa[0]>=self.pressure_steps_pa[1]:
            raise ValueError('Two ordered positive pressure step sizes required')
        if self.wider_sideslip_bound_rad<=self.numerical_sideslip_bound_rad or self.fd_step_multiplier==1.:
            raise ValueError('Distinct declared numerical-control variants required')
        if any(type(x) is not int or x not in range(1,6) for x in (self.front_arb_target,self.rear_arb_target)):
            raise ValueError('Discrete ARB targets must be integers 1..5')


def verify_sources(hashes,root=ROOT):
    for path,expected in hashes.items():
        if hashlib.sha256((root/path).read_bytes()).hexdigest()!=expected:
            raise ValueError('Seed source changed: '+path)


def numerical_variants(config,controls):
    anchor=widen_sideslip_bound(config,controls.numerical_sideslip_bound_rad)
    return {'anchor':anchor,
        'wider_sideslip_box':widen_sideslip_bound(config,controls.wider_sideslip_bound_rad),
        'half_fd_steps':replace(anchor,fd_steps=tuple(x*controls.fd_step_multiplier for x in anchor.fd_steps))}


def pressure_case(base,delta_pa,tag):
    if not math.isfinite(delta_pa) or delta_pa==0:
        raise ValueError('Explicit finite nonzero pressure increment required')
    return replace(base,state_id=tag,pressures_pa=tuple(p+delta_pa for p in base.pressures_pa))


def output_values(result):
    if not result.ok or result.evaluation is None:
        return None
    ev=result.evaluation
    names=('body_heave_m','roll_rad','pitch_rad','sideslip_rad','rack_m','holder_force_n',
           'Fz_front_left_n','Fz_front_right_n','Fz_rear_left_n','Fz_rear_right_n')
    values=dict(zip(names,result.coordinates))
    values['virtual_holder_power_w']=ev.holder.power_w
    for tire in ev.tires:
        corner=tire.query.corner_id
        values['Fy_'+corner+'_n']=tire.lateral_force_n
        values['slip_'+corner+'_rad']=tire.query.slip_angle_rad
        values['inclination_'+corner+'_rad']=tire.query.inclination_rad
    return values


def finite_step_response(baseline,changed,step):
    if baseline is None or changed is None:
        return None
    if not math.isfinite(step) or step==0 or baseline.keys()!=changed.keys():
        raise ValueError('Matching outputs and finite nonzero input step required')
    return {key:{'absolute_change':changed[key]-value,
                 'finite_step_slope_per_pa':(changed[key]-value)/step}
            for key,value in baseline.items()}


def _case(values,geometry,tire,sign,magnitude,tag):
    raw=dict(values)
    for key in ('pressures_pa','accepted_assumptions'):raw[key]=tuple(raw[key])
    raw.update(state_id=tag,curvature_per_m=sign*magnitude,
        geometry_revision=geometry.geometry_revision,setup_revision=geometry.setup_revision,
        tire_revision=tire.tire_revision)
    return CorneringCase(**raw)


def run_study(seed,controls,directions,progress=None):
    if len(set(directions))!=len(directions) or not directions or any(
            type(s) is not int or s not in (-1,1) for s in directions):
        raise ValueError('Explicit unique direction signs required')
    if (seed['objective_weight']!=0. or seed['design_ranking_permitted'] is not False
            or seed['physical_limit_or_stability_claim'] is not False):
        raise ValueError('Unpromoted development seeds required')
    verify_sources(seed['source_hashes'])
    if hashlib.sha256((ROOT/'scripts/package_native_computational_envelope.py').read_bytes()).hexdigest()!=seed['packager_sha256']:
        raise ValueError('Seed packager changed')
    geometry,tire=providers()
    original=solver_config()
    if json.loads(json.dumps(asdict(original)))!=seed['solver_config']:
        raise ValueError('Original solver controls changed')
    configs=numerical_variants(original,controls)
    records=[]
    for sign in directions:
        branch=next(b for b in seed['branches'] if b['direction_sign']==sign)
        physical_seed=next(a for a in branch['attempts'] if a['ok'] and
            abs(a['signed_curvature_per_m'])==controls.physical_curvature_magnitude_per_m)
        numerical_seed=next(c for c in seed['separate_sideslip_bound_controls']
            if c['direction_sign']==sign and c['ok'] and c['same_source_branch'] and
            abs(c['case']['curvature_per_m'])==controls.numerical_curvature_magnitude_per_m)
        verify_sources(numerical_seed['source_hashes'])
        record={'direction_sign':sign,'physical':[],'numerical':[],'pressure_responses':{},
                'arb_responses':{},'passed':False}
        records.append(record)

        def solve(tag,c,guess,config,reference_signature=None):
            result=solve_cornering(c,tuple(guess),geometry_provider=geometry,tire_provider=tire,config=config)
            signature=result.evaluation.branch_signature if result.evaluation is not None else None
            comparable=result.ok and (reference_signature is None or tuple(signature)==tuple(reference_signature))
            item={'tag':tag,'case':asdict(c),'solver_config':asdict(config),
                'initial_coordinates':tuple(guess),'comparison_supported':comparable,
                'branch_signature':signature,'failure_code':result.failure_code,
                'outputs':output_values(result) if comparable else None,'result':_sample(result)}
            if progress is not None:progress(sign,item)
            return result,item

        physical_case=_case(seed['fixed_case_controls'],geometry,tire,sign,
            controls.physical_curvature_magnitude_per_m,f'sensitivity_{sign}:physical_anchor')
        baseline,base_record=solve('physical_anchor',physical_case,physical_seed['coordinates'],original,
                                  branch['reference_branch_signature'])
        record['physical'].append(base_record)
        if not base_record['comparison_supported']:
            record['stopping_reason']='physical_anchor_unavailable'
            continue
        base_outputs=base_record['outputs']
        for sign_pressure in (-1,1):
            side='decreasing_pressure' if sign_pressure<0 else 'increasing_pressure'
            steps=[]
            for magnitude in controls.pressure_steps_pa:
                delta=sign_pressure*magnitude
                tag=f'pressure_{delta:+g}_pa'
                c=pressure_case(physical_case,delta,physical_case.state_id+':'+tag)
                _,item=solve(tag,c,baseline.coordinates,original,baseline.evaluation.branch_signature)
                record['physical'].append(item)
                steps.append({'pressure_increment_pa':delta,'comparison_supported':item['comparison_supported'],
                    'response':finite_step_response(base_outputs,item['outputs'],delta)})
            record['pressure_responses'][side]={'interpretation':'one_sided_finite_step_responses_at_source_pressure_knot',
                'steps':steps,'central_derivative_claim':False}
        for axle,target in (('front',controls.front_arb_target),('rear',controls.rear_arb_target)):
            field=axle+'_arb_setting'
            if target==getattr(physical_case,field):
                raise ValueError('ARB comparison must change exactly one discrete setting')
            tag=field+'_'+str(target)
            c=replace(physical_case,state_id=physical_case.state_id+':'+tag,**{field:target})
            _,item=solve(tag,c,baseline.coordinates,original,baseline.evaluation.branch_signature)
            record['physical'].append(item)
            record['arb_responses'][axle]={'original_setting':getattr(physical_case,field),'target_setting':target,
                'comparison_supported':item['comparison_supported'],
                'absolute_changes':None if item['outputs'] is None else {
                    key:item['outputs'][key]-value for key,value in base_outputs.items()},
                'derivative_claim':False}

        c=_case(numerical_seed['case'],geometry,tire,sign,controls.numerical_curvature_magnitude_per_m,
                f'sensitivity_{sign}:numerical_anchor')
        anchor,anchor_record=solve('numerical_anchor',c,numerical_seed['coordinates'],configs['anchor'],
                                   branch['reference_branch_signature'])
        record['numerical'].append(anchor_record)
        if not anchor_record['comparison_supported']:
            record['stopping_reason']='numerical_anchor_unavailable'
            continue
        numerical_ok=True
        for tag in ('wider_sideslip_box','half_fd_steps'):
            result,item=solve(tag,replace(c,state_id=c.state_id+':'+tag),anchor.coordinates,configs[tag],
                              anchor.evaluation.branch_signature)
            record['numerical'].append(item)
            if item['comparison_supported']:
                delta=max(abs(x-y)/scale for x,y,scale in
                    zip(result.coordinates,anchor.coordinates,configs['anchor'].coordinate_scales))
                item['maximum_scaled_coordinate_change']=delta
                item['absolute_output_changes']={key:item['outputs'][key]-value
                    for key,value in anchor_record['outputs'].items()}
                item['numerical_comparison_passed']=delta<=controls.numerical_coordinate_difference_limit
            else:
                item['maximum_scaled_coordinate_change']=None
                item['numerical_comparison_passed']=False
            numerical_ok=numerical_ok and item['numerical_comparison_passed']
        record['passed']=numerical_ok and all(x['comparison_supported'] for x in record['physical'])
    return {'status':'pass' if all(r['passed'] for r in records) else 'fail',
        'scope':'explicit_re_equilibrated_native_fixture_response_study_only',
        'controls':asdict(controls),'directions':records,
        'stored_seed_revisions':{key:seed[key] for key in ('geometry_revision','setup_revision','tire_revision')},
        'current_provider_revisions':{'geometry_revision':geometry.geometry_revision,
            'setup_revision':geometry.setup_revision,'tire_revision':tire.tire_revision},
        'stored_coordinates_are_seeds_only':True,
        'pressure_knot_note':'Separate left/right finite-step responses; no central or smooth tire derivative claimed',
        'source_pressure_levels_pa':sorted({c.pressure_Pa for c in tire.table.curves}),
        'physical_or_ranking_authority':False,'objective_weight':0.}


def compact_report(report):
    summary={k:v for k,v in report.items() if k!='directions'}
    summary['directions']=[]
    for direction in report['directions']:
        d={k:v for k,v in direction.items() if k not in ('physical','numerical')}
        for group in ('physical','numerical'):
            d[group]=[]
            for item in direction[group]:
                small={k:v for k,v in item.items() if k not in ('result','initial_coordinates','solver_config')}
                small.update({'ok':item['result']['ok'],
                    'physical_force_norm_n':item['result'].get('physical_force_norm_n'),
                    'physical_moment_norm_nm':item['result'].get('physical_moment_norm_nm')})
                d[group].append(small)
        summary['directions'].append(d)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed-report',type=Path,required=True)
    parser.add_argument('--controls',type=Path,required=True)
    parser.add_argument('--directions',type=int,nargs='+',choices=(-1,1),required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--summary-output',type=Path,required=True)
    args=parser.parse_args()
    values=tomllib.loads(args.controls.read_text()); values['pressure_steps_pa']=tuple(values['pressure_steps_pa'])
    controls=StudyControls(**values)
    seed=json.loads(args.seed_report.read_text())
    def progress(sign,item):
        print(json.dumps({'direction':sign,'tag':item['tag'],'ok':item['result']['ok'],
            'comparison_supported':item['comparison_supported'],'failure':item['failure_code']}),flush=True)
    report=run_study(seed,controls,tuple(args.directions),progress)
    paths=('scripts/run_native_sensitivity_study.py','tests/test_native_sensitivity_study.py')
    report['source_hashes']={**seed['source_hashes'],**{
        p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}
    report['controls_sha256']=hashlib.sha256(args.controls.read_bytes()).hexdigest()
    report['seed_report_sha256']=hashlib.sha256(args.seed_report.read_bytes()).hexdigest()
    report['seed_report_path']=str(args.seed_report)
    summary=compact_report(report)
    for path,value in ((args.output,report),(args.summary_output,summary)):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':report['status'],'directions':[
        {'sign':d['direction_sign'],'passed':d['passed'],'physical_cases':len(d['physical']),
         'numerical_cases':len(d['numerical'])} for d in report['directions']]},indent=2))
    return 0 if report['status']=='pass' else 1


if __name__=='__main__':raise SystemExit(main())

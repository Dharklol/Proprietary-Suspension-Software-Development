#!/usr/bin/env python3
"""Combine source-identical signed envelope reports without promoting their limits."""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCOPE = 'explicit_native_fixture_warm_started_computational_reachability_only'


def combine_reports(reports):
    if len(reports) != 2:
        raise ValueError('Exactly two signed branch reports required')
    first = reports[0]['summary']
    invariant_keys = ('scope','controls','solver_config','geometry_revision','setup_revision',
                      'tire_revision','source_hashes','status_meaning')
    seen, branches, fixed_case = set(),[],None
    for report in reports:
        summary = report['summary']
        if summary['scope'] != SCOPE or any(summary[k] != first[k] for k in invariant_keys):
            raise ValueError('Cannot combine different source, control or revision reports')
        if (summary.get('objective_weight') != 0.
                or summary.get('design_ranking_permitted') is not False
                or summary.get('physical_limit_or_stability_claim') is not False):
            raise ValueError('Envelope packaging cannot promote development evidence')
        if len(summary['branches']) != 1 or len(report['branches']) != 1:
            raise ValueError('Each input must contain exactly one signed branch')
        branch = summary['branches'][0]
        full = report['branches'][0]
        sign = branch['direction_sign']
        if sign not in (-1,1) or sign in seen or full['direction_sign'] != sign:
            raise ValueError('Distinct matching -1 and +1 branch reports required')
        seen.add(sign)
        if len(branch['attempts']) != len(full['attempts']):
            raise ValueError('Summary/full attempt count mismatch')
        for item,raw in zip(branch['attempts'],full['attempts']):
            result = raw['result']
            c = result['case']
            if (item['ok'] != result['ok'] or item['stage'] != raw['stage']
                    or item['category'] != raw['category']
                    or item['signed_curvature_per_m'] != c['curvature_per_m']
                    or item['coordinates'] != result['coordinates']
                    or item['initial_coordinates'] != raw['initial_coordinates']
                    or item['failure_code'] != result['failure_code']
                    or sign*c['curvature_per_m'] < 0):
                raise ValueError('Summary/full attempt identity mismatch')
            current = {k:v for k,v in c.items() if k not in ('state_id','curvature_per_m')}
            if current['result_role'] != 'evidence_only' or current['state_weight'] != 0.:
                raise ValueError('Source cases must remain zero-weight development evidence')
            if fixed_case is not None and current != fixed_case:
                raise ValueError('Mixed vehicle/setup/speed/pressure controls')
            fixed_case = current
        branches.append(deepcopy(branch))
    if seen != {-1,1}:
        raise ValueError('Both turn directions required')
    combined = {k:deepcopy(v) for k,v in first.items() if k not in ('branches','status')}
    combined.update({'status':'pass' if all(r['summary']['status']=='pass' for r in reports) else 'fail',
        'branches':sorted(branches,key=lambda b:b['direction_sign']),
        'fixed_case_controls':fixed_case,
        'packager_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    return combined


def compact_summary(combined):
    compact = {k:deepcopy(v) for k,v in combined.items() if k!='branches'}
    compact['branches'] = []
    for branch in combined['branches']:
        result = {k:deepcopy(v) for k,v in branch.items() if k!='attempts'}
        result['attempts'] = []
        for item in branch['attempts']:
            point = {k:deepcopy(v) for k,v in item.items()
                     if k not in ('initial_coordinates','coordinate_bound_margins','wheels')}
            axes = ('body_heave_m','roll_rad','pitch_rad','sideslip_rad','rack_m','holder_n',
                    'Fz_front_left_n','Fz_front_right_n','Fz_rear_left_n','Fz_rear_right_n')
            normalized = [(margin/scale,index,side,margin,scale)
                for index,(pair,scale) in enumerate(zip(item['coordinate_bound_margins'],
                    combined['solver_config']['coordinate_scales']))
                for side,margin in zip(('lower','upper'),pair)]
            distance,index,side,margin,scale = min(normalized)
            point['closest_normalized_solver_bound'] = {'axis':axes[index],'side':side,
                'margin_in_axis_units':margin,'coordinate_scale':scale,
                'dimensionless_margin':distance}
            if 'wheels' in item:
                point['normal_loads_n'] = [w['query']['normal_load_n'] for w in item['wheels']]
                point['inclinations_rad'] = [w['query']['inclination_rad'] for w in item['wheels']]
                point['slip_angles_rad'] = [w['query']['slip_angle_rad'] for w in item['wheels']]
                point['lateral_forces_n'] = [w['lateral_force_n'] for w in item['wheels']]
            result['attempts'].append(point)
        compact['branches'].append(result)
    return compact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports',nargs=2,type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--compact-output',type=Path,required=True)
    parser.add_argument('--bound-controls',nargs=2,type=Path)
    args = parser.parse_args()
    combined = combine_reports([json.loads(p.read_text()) for p in args.reports])
    combined['input_report_sha256'] = {
        p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.reports}
    if args.bound_controls is not None:
        controls=[]
        signs=set()
        for path in args.bound_controls:
            control=json.loads(path.read_text())
            if (control['original_report_sha256'] not in combined['input_report_sha256'].values()
                    or control['direction_sign'] in signs
                    or control['objective_weight']!=0.
                    or control['physical_limit_or_stability_claim'] is not False):
                raise ValueError('Mixed or promoted bound control report')
            signs.add(control['direction_sign'])
            for p,expected in control['source_hashes'].items():
                if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=expected:
                    raise ValueError('Bound control source changed: '+p)
            result=control['result']
            controls.append({'status':control['status'],'direction_sign':control['direction_sign'],
                'case':control['case'],'original_report_sha256':control['original_report_sha256'],
                'control_report_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                'original_sideslip_bounds_rad':[
                    control['original_solver_config']['lower_bounds'][3],
                    control['original_solver_config']['upper_bounds'][3]],
                'control_sideslip_bounds_rad':[
                    control['control_solver_config']['lower_bounds'][3],
                    control['control_solver_config']['upper_bounds'][3]],
                'original_failure_code':control['original_failure_code'],
                'original_failed_coordinates':control['original_failed_coordinates'],
                'coordinates':result['coordinates'],'ok':result['ok'],
                'failure_code':result['failure_code'],'same_source_branch':control['same_source_branch'],
                'physical_force_norm_n':result.get('physical_force_norm_n'),
                'physical_moment_norm_nm':result.get('physical_moment_norm_nm'),
                'source_hashes':control['source_hashes']})
        if signs!={-1,1}:
            raise ValueError('Both bound control directions required')
        combined['separate_sideslip_bound_controls']=sorted(controls,key=lambda c:c['direction_sign'])
    for p,expected in combined['source_hashes'].items():
        if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=expected:
            raise ValueError('Source changed after envelope generation: '+p)
    compact = compact_summary(combined)
    for path,value in ((args.output,combined),(args.compact_output,compact)):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':combined['status'],'branches':[
        {k:v for k,v in b.items() if k!='attempts'} for b in combined['branches']]},indent=2))
    return 0 if combined['status']=='pass' else 1


if __name__=='__main__':raise SystemExit(main())

#!/usr/bin/env python3
"""Combine source-identical signed sensitivity/recovery evidence."""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.run_native_sensitivity_study import compact_report, verify_sources
from scripts.run_native_numerical_recovery import compact_recovery


def combine_signed_reports(studies,recoveries):
    if len(studies)!=2 or len(recoveries)!=2:
        raise ValueError('Exactly two study and two recovery reports required')
    study_keys=('scope','controls','stored_seed_revisions','current_provider_revisions',
                'source_hashes','controls_sha256','seed_report_sha256')
    recovery_keys=('scope','coordinate_order','coordinate_offsets','difference_limit',
                   'source_hashes','recovery_controls_sha256','road_gap_tolerance_m',
                   'comparison_road_gap_tolerance_m','geometry_revision',
                   'primary_precision_setup_revision','comparison_precision_setup_revision')
    for group,keys in ((studies,study_keys),(recoveries,recovery_keys)):
        signs=set()
        for report in group:
            if (report['objective_weight']!=0. or report['physical_or_ranking_authority'] is not False
                    or any(report[k]!=group[0][k] for k in keys)):
                raise ValueError('Mixed source/control reports or authority promotion')
            if len(report['directions'])!=1:
                raise ValueError('One signed direction per input report required')
            sign=report['directions'][0]['direction_sign']
            if sign not in (-1,1) or sign in signs:
                raise ValueError('Both distinct direction signs required')
            signs.add(sign)
        if signs!={-1,1}:raise ValueError('Both directions required')
    for report in studies:
        direction=report['directions'][0]
        if (len(direction['physical'])!=7 or len(direction['numerical'])!=3
                or len({x['tag'] for x in direction['physical']})!=7
                or {x['tag'] for x in direction['numerical']}!={
                    'numerical_anchor','wider_sideslip_box','half_fd_steps'}):
            raise ValueError('Incomplete sensitivity protocol')
    for report in recoveries:
        if len(report['directions'][0]['variants'])!=4:
            raise ValueError('Incomplete off-root recovery protocol')
    study={k:deepcopy(v) for k,v in studies[0].items() if k not in ('status','directions')}
    recovery={k:deepcopy(v) for k,v in recoveries[0].items() if k not in ('status','directions','input_study_sha256')}
    for combined,group in ((study,studies),(recovery,recoveries)):
        combined['status']='pass' if all(r['status']=='pass' for r in group) else 'fail'
        combined['directions']=sorted([deepcopy(r['directions'][0]) for r in group],key=lambda d:d['direction_sign'])
    return {'status':'pass' if study['status']=='pass' and recovery['status']=='pass' else 'fail',
        'study':study,'off_root_recovery':recovery,
        'objective_weight':0.,'physical_or_ranking_authority':False}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--studies',type=Path,nargs=2,required=True)
    parser.add_argument('--recoveries',type=Path,nargs=2,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--summary-output',type=Path,required=True)
    args=parser.parse_args()
    studies=[json.loads(p.read_text()) for p in args.studies]
    recoveries=[json.loads(p.read_text()) for p in args.recoveries]
    study_hashes={s['directions'][0]['direction_sign']:hashlib.sha256(p.read_bytes()).hexdigest()
                  for s,p in zip(studies,args.studies)}
    for recovery in recoveries:
        sign=recovery['directions'][0]['direction_sign']
        if recovery['input_study_sha256']!=study_hashes[sign]:
            raise ValueError('Recovery does not belong to the signed study input')
    for report in (*studies,*recoveries):verify_sources(report['source_hashes'])
    combined=combine_signed_reports(studies,recoveries)
    combined['input_report_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in (*args.studies,*args.recoveries)}
    combined['packager_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    combined['packager_test_sha256']=hashlib.sha256(
        (ROOT/'tests/test_native_sensitivity_package.py').read_bytes()).hexdigest()
    summary={**combined,'study':compact_report(combined['study']),
             'off_root_recovery':compact_recovery(combined['off_root_recovery'])}
    for path,value in ((args.output,combined),(args.summary_output,summary)):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':combined['status'],'study_case_count':20,'off_root_case_count':8},indent=2))
    return 0 if combined['status']=='pass' else 1


if __name__=='__main__':raise SystemExit(main())

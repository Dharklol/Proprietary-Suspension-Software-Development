"""Audit every A0701 source mass row without promoting joint lumps to rigid bodies."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT / 'data_catalog/wufr26_front_corner_inventory_v0.json'
    snapshot = json.loads(source.read_text())
    old = json.loads((ROOT / 'data_catalog/wufr26_com_pitch_snapshot_v0.json').read_text())
    reference = next(g for g in old['groups'] if g['sheet'] == 'SU' and g['header_row'] == 19)
    tubes = json.loads((ROOT / 'data_catalog/wufr26_front_arm_tubes_inertia_v0.json').read_text())
    tube_rows = {m['row']: m for m in tubes['members']}
    # Explicit instance mapping, not an automatic nearest-point ownership rule.
    endcaps = {108:'upper',109:'upper',110:'lower',111:'lower',112:'upper',113:'upper',114:'lower',115:'lower'}
    assignments = []
    for row in snapshot['rows']:
        n, name = row['sheet_row'], row['part_name']
        side = 'left' if row['cg_in'][1] > 0 else 'right'
        item = dict(row, side=side, rigid_owner=None, candidate_owner=None,
                    status='unresolved', nominal_contribution_verified=False)
        if n in tube_rows:
            tube = tube_rows[n]
            item.update(family='arm_tube', rigid_owner=f"{side}_{tube['arm']}_arm",
                        status='verified_nominal_tube', nominal_contribution_verified=True,
                        evidence='BENCH-SUSP-0040; per-instance geometry/tensor/motion gates')
        elif 100 <= n <= 103:
            arm = 'lower' if n <= 101 else 'upper'
            item.update(family='bearing_housing', rigid_owner=f'{side}_{arm}_arm',
                        status='source_supported_owner',
                        evidence='Named upper/lower housing; welded A-arm architecture in topology source audit. Full tensor/pose gates pending.')
        elif n in endcaps:
            item.update(family='arm_endcap', rigid_owner=f'{side}_{endcaps[n]}_arm',
                        status='source_supported_owner', evidence='Owner confirmed fixed attachment to corresponding arm tubes; exact row/leg geometry checked in welded-arm gravity study.')
        elif n in (104,105,106,107):
            item.update(family='pullrod_endcap', rigid_owner=f'{side}_pullrod', status='source_supported_owner', evidence='Owner confirmed turnbuckle endcaps fixed to their rod tubes; no arm-transform substitution.')
        elif n in (98,99):
            item.update(family='pullrod_tube', rigid_owner=f'{side}_pullrod',status='source_supported_owner',evidence='Named rod tube; native endpoint closure and conditional rigid rod pose verified by BENCH-VEH-0027.')
        elif n in (56,57,58,59):
            item.update(family='pullrod_body_parts', candidate_owner=f'{side}_pullrod',
                        status='candidate', evidence='Named pullrod/turnbuckle endcaps or adjacent jam nuts. Separate moving member; no arm transform substitution.')
        elif 84 <= n <= 89:
            item.update(family='pullrod_attachment', rigid_owner=f'{side}_upper_arm',
                        status='source_supported_owner', evidence='Front Pull Rod and Connector Welding Jigs Assembly, Box 2212895915302, includes tabs/connector with upper tubes/housing. Gravity ownership only; no new inertia authority.')
        elif 80 <= n <= 83:
            item.update(family='spherical_bearing', status='joint_split_required',
                        evidence='HAB-4TG export combines inner and outer bearing bodies at arm/upright joint. No whole-part rigid owner assigned.')
        elif 116 <= n <= 127:
            item.update(family='rod_end', status='joint_split_required',
                        evidence='Rod-end shank/body and inner ball have different relative rotations; endpoint/shank assignment and mass split pending.')
        else:
            item.update(family='joint_hardware', evidence='Fastener, washer, nut or spacer requires clamping-stack ownership; position alone does not establish rotation.')
        assignments.append(item)
    expected = {r[0]:r for r in reference['rows']}
    actual = {r['sheet_row']:r for r in assignments}
    checks = {
        'exact_row_manifest': len(assignments)==124 and len(actual)==124 and set(actual)==set(expected),
        'unchanged_CAD_mass_and_CG': all(r['CAD_mass_lb']==expected[n][1] and r['cg_in']==expected[n][2:5] for n,r in actual.items()),
        'tube_subset_preserved': all(actual[n]['CAD_mass_lb']==t['mass_lb'] and actual[n]['side']==t['side'] for n,t in tube_rows.items()),
        'only_tubes_have_verified_nominal_contribution': {r['sheet_row'] for r in assignments if r['nominal_contribution_verified']}==set(tube_rows),
        'unresolved_joint_owners_empty': all(r['rigid_owner'] is None for r in assignments if r['status'] in ('joint_split_required','unresolved','candidate')),
    }
    totals = defaultdict(lambda:dict(count=0,mass_lb=0.))
    for r in assignments:
        group=totals[r['status']]
        group['count']+=1
        group['mass_lb']+=r['CAD_mass_lb']
    mass=sum(r['CAD_mass_lb'] for r in assignments)
    checks['CAD_assembly_mass_closure']=abs(mass-5.068)<1e-12
    checks['status_partition_mass_closure']=abs(sum(g['mass_lb'] for g in totals.values())-mass)<1e-12
    checks['named_housing_manifest']=sum(r['family']=='bearing_housing' for r in assignments)==4
    # Counts are instance counts, never multiplication of an already-instanced mass.
    counts=Counter()
    for r in assignments:
        for part in ('91847A429','91845A105','94450A220'):
            if part in r['part_name']: counts[part]+=1
    checks['nut_discrepancy_preserved'] = dict(counts)=={'94450A220':2,'91847A429':2,'91845A105':8}
    report=dict(scope='WUFR26 bilateral front-corner A0701 ownership audit only',
        source_url=snapshot['source_url'],source_range=snapshot['range'],
        CAD_mass_lb=mass,CAD_mass_kg=mass*.45359237,status_totals=dict(totals),
        source_nut_counts=dict(counts),
        drawing_discrepancies=[dict(part='91847A429',drawing_count=10,COM_count=counts['91847A429'],unlisted_COM_part='91845A105',unlisted_count=counts['91845A105'],resolution='Open; do not silently substitute.'),
            dict(field='weight_label_lb',drawing=5.06,COM_row_sum=5.068,resolution='Separate source labels retained; CAD row sum used.')],
        checks=checks,passed=all(checks.values()),assignments=assignments,
        source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (source,Path(__file__),ROOT/'data_catalog/wufr26_welded_arm_ownership_evidence_v0.json',ROOT/'data_catalog/wufr26_endcap_attachment_confirmation_v0.json',ROOT/'scripts/run_rod_gravity_map.py',ROOT/'src/pssd_suspension/rod_pose.py',ROOT/'data_catalog/wufr26_com_pitch_snapshot_v0.json',ROOT/'data_catalog/wufr26_front_arm_tubes_inertia_v0.json')})
    destination=ROOT/'docs/reports/front_corner_ownership_v0.1.0'
    destination.mkdir(parents=True,exist_ok=True)
    (destination/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('assignments','source_sha256')},indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())

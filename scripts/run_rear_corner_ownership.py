"""BENCH-VEH-0029: rear inventory ownership and bilateral coverage ledger."""
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from run_welded_arm_gravity import WeldedArmGravity

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = ROOT/'data_catalog/wufr26_rear_corner_inventory_v0.json'
    inventory = json.loads(source.read_text())
    fixture = WeldedArmGravity()
    arms = {r['sheet_row']: r for r in fixture.members if r['axle']=='rear'}
    confirmation = fixture.confirmation
    rod_caps = set(confirmation['rod_endcap_rows']['rear'])
    reference = next(g for g in fixture.snapshot['groups'] if g['sheet']=='SU' and g['header_row']==151)
    expected = {r[0]:r for r in reference['rows']}
    assignments = []
    for row in inventory['rows']:
        n = row['sheet_row']
        side = 'left' if row['cg_in'][1]>0 else 'right'
        item = dict(row, side=side, rigid_owner=None, candidate_owner=None,
                    status='unresolved', family='joint_hardware', nominal_contribution_verified=False,
                    evidence='Clamping-stack ownership is not established by proximity or assembly membership.')
        if n in arms:
            member = arms[n]
            item.update(rigid_owner=member['owner'], status='source_supported_owner',
                        family='arm_attached',
                        evidence='Existing welded-arm ownership and fixed-endcap confirmation; BENCH-VEH-0026. Gravity subset only; no new tensor or pose authority.')
        elif n in (190,191) or n in rod_caps:
            item.update(rigid_owner=f'rear_{side}_pushrod', status='source_supported_owner',
                        family='pushrod_tube' if n in (190,191) else 'pushrod_endcap',
                        evidence='Named tube or owner-confirmed fixed rod endcap; conditional rod gravity BENCH-VEH-0027. Thread metadata discrepancy remains open.')
        elif n in (192,193,206,207,208,209):
            item.update(candidate_owner=f'rear_{side}_toe_link', status='candidate',
                        family='toe_link_tube' if n in (192,193) else 'toe_link_endcap',
                        evidence='Named toe-link components; fixed attachment and compatible motion mapping not yet established. Arm/rod endcap confirmation is not extended to these aluminum caps.')
        elif 'HAB-4TG' in row['part_name'] or 'Rod End' in row['part_name']:
            item.update(status='joint_split_required',family='spherical_bearing' if 'HAB-4TG' in row['part_name'] else 'rod_end',
                        evidence='Joint center definition does not establish inner-ball/shank or race ownership; BENCH-VEH-0028.')
        assignments.append(item)
    totals = defaultdict(lambda:dict(count=0,mass_lb=0.))
    for r in assignments:
        totals[r['status']]['count'] += 1
        totals[r['status']]['mass_lb'] += r['CAD_mass_lb']
    actual = {r['sheet_row']:r for r in assignments}
    mass = sum(r['CAD_mass_lb'] for r in assignments)
    checks = dict(
        exact_154_unique_rows=len(assignments)==len(actual)==154 and set(actual)==set(expected),
        source_mass_CG_preserved=all(r['CAD_mass_lb']==expected[n][1] and r['cg_in']==expected[n][2:5] for n,r in actual.items()),
        exact_26_arm_members=len(arms)==26 and {r['sheet_row'] for r in assignments if r['family']=='arm_attached'}==set(arms),
        exact_six_pushrod_members=sum(r['family'] in ('pushrod_tube','pushrod_endcap') for r in assignments)==6,
        exact_six_toe_candidates={r['sheet_row'] for r in assignments if r['status']=='candidate'}=={192,193,206,207,208,209},
        exact_20_joint_rows=sum(r['status']=='joint_split_required' for r in assignments)==20,
        unresolved_owners_empty=all(r['rigid_owner'] is None for r in assignments if r['status']!='source_supported_owner'),
        no_new_nominal_inertia=not any(r['nominal_contribution_verified'] for r in assignments),
        mass_closure=abs(mass-5.641)<1e-12 and abs(sum(v['mass_lb'] for v in totals.values())-mass)<1e-12)
    front = json.loads((ROOT/'docs/reports/front_corner_ownership_v0.1.0/results.json').read_text())
    combined = defaultdict(lambda:dict(count=0,mass_lb=0.))
    for r in front['assignments']+assignments:
        category = 'owner_supported' if r['status'] in ('source_supported_owner','verified_nominal_tube') else r['status']
        combined[category]['count'] += 1
        combined[category]['mass_lb'] += r['CAD_mass_lb']
    checks['bilateral_coverage_closure'] = sum(v['count'] for v in combined.values())==278 and abs(sum(v['mass_lb'] for v in combined.values())-10.709)<1e-12
    sources = (source, Path(__file__), ROOT/'scripts/run_welded_arm_gravity.py', ROOT/'data_catalog/wufr26_endcap_attachment_confirmation_v0.json',ROOT/'data_catalog/wufr26_com_pitch_snapshot_v0.json',ROOT/'docs/reports/front_corner_ownership_v0.1.0/results.json')
    report = dict(scope='Rear A0702 inventory and bilateral corner ownership coverage; no equilibrium promotion',source_url=inventory['source_url'],source_range=inventory['range'],CAD_mass_lb=mass,status_totals=dict(totals),bilateral_status_totals=dict(combined),assignments=assignments,checks=checks,passed=all(checks.values()),native_equilibrium_gate_passed=False,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    out = ROOT/'docs/reports/rear_corner_ownership_v0.1.0'; out.mkdir(parents=True,exist_ok=True)
    (out/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('assignments','source_sha256')},indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate all candidate evidence and produce the offline comparison package."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from pssd_vehicle.analytical_workflow import combine_reports, compact_report
from pssd_viz.analytical_workflow_report import render_comparison_html, render_comparison_figures


def add_assumption_responses(report):
    """Pair stresses to the same candidate/case nominal result; never fill failures."""
    cells = {(c['candidate_id'], c['assumption_id'], c['case_id']): c for c in report['cells']}
    responses = []
    for cell in report['cells']:
        baseline = cells[cell['candidate_id'], 'nominal', cell['case_id']]
        supported = (cell['result']['ok'] and baseline['result']['ok']
                     and cell['branch_signature'] == baseline['branch_signature'])
        responses.append({k: cell[k] for k in ('candidate_id', 'assumption_id', 'case_id')} | {
            'comparison_supported': supported,
            'reason': None if supported else ('solve_failed' if not cell['result']['ok']
                or not baseline['result']['ok'] else 'source_branch_changed'),
            'delta_from_nominal': {m: cell['metrics'][m]-baseline['metrics'][m]
                for m in report['metric_definitions']} if supported else None})
    report['assumption_responses'] = responses
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', type=Path, nargs='+', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--figures', action='store_true', help='Requires the optional viz extra')
    args = parser.parse_args()
    report = add_assumption_responses(combine_reports([json.loads(p.read_text()) for p in args.reports]))
    report['input_report_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.reports}
    report['reporting_source_hashes'] = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
        'scripts/package_analytical_design_workflow.py', 'src/pssd_viz/analytical_workflow_report.py',
        'tests/test_analytical_workflow_reporting.py')}
    summary = compact_report(report)
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    for name, value in (('full.json', report), ('summary.json', summary)):
        (out/name).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    columns = ['candidate_id', 'assumption_id', 'case_id', 'comparison_supported', 'reason', *report['metric_definitions']]
    with (out/'comparisons.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n')
        writer.writeheader()
        for cell in report['comparisons']:
            writer.writerow({**{k: cell[k] for k in columns[:5]}, **(cell['delta_from_reference'] or {})})
    render_comparison_html(summary, out/'index.html')
    if args.figures:
        render_comparison_figures(summary, out/'figures')
    artifacts = sorted(p for p in out.rglob('*') if p.is_file() and p.name != 'manifest.json')
    manifest = dict(plan_fingerprint=report['plan_fingerprint'], source_hashes=report['source_hashes'],
        artifacts={str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts})
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'status': report['status'], 'cells': len(report['cells']), 'output_dir': str(out)}))
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())

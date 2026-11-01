#!/usr/bin/env python3
"""Run one explicit candidate, checkpointing every solved or failed cell."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
from pssd_vehicle.analytical_workflow import DEFAULT_PLAN, load_plan, run_candidate, source_manifest


def write_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, default=ROOT/DEFAULT_PLAN)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    plan = load_plan(args.plan)
    if args.candidate not in {c['id'] for c in plan['candidates']}:
        parser.error('Candidate must be declared in the plan')
    hashes = source_manifest(plan, args.plan)
    seed = json.loads((ROOT/plan['seed_report']).read_text())

    def progress(report, cell):
        write_report(args.output, report)
        print(json.dumps({'candidate': cell['candidate_id'], 'assumption': cell['assumption_id'],
            'case': cell['case_id'], 'ok': cell['result']['ok'], 'failure': cell['result']['failure_code'],
            'iterations': cell['result']['iterations']}), flush=True)

    report = run_candidate(plan, args.candidate, seed, hashes, progress=progress)
    write_report(args.output, report)
    print(json.dumps({'status': report['status'], 'cells': len(report['cells'])}), flush=True)
    return 0 if report['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())

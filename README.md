# Proprietary Suspension Software Development

Private, local-first vehicle-dynamics engineering platform for WashU Racing.

## Current phase

The project has progressed from Phase 0 assurance into reviewed subsystem mechanics and an **uncorrelated steady-cornering development pipeline**. Model assurance remains a requirement: no physical model, equation, parameter, or legacy calculator is authoritative merely because it already exists.

The current consolidation and dependency status is recorded in [the development checkpoint](docs/reviews/analytical_development_consolidation_2026-10-31.md). The next increment is [analytical verification, operating-envelope mapping and sensitivity](docs/roadmaps/analytical_development_program_v0.1.0.md). Physical correlation is deferred until hardware is available; analytical development does not depend on collecting measurements now. Predictive, installed/setup and production claims retain their existing evidence requirements.

Every result used for a design decision must be traceable to its definition, derivation, assumptions, evidence, uncertainty, applicable operating range, numerical behavior, dependencies, and verification status.

## Analytical comparison workbench

The first [analytical design workflow](docs/reviews/analytical_design_workflow_review.md)
defines a provisional source configuration, operating cases, assumption stresses
and three re-equilibrated rack candidates. Reproduce its offline comparison UI,
JSON/CSV evidence and static figures with:

```bash
python -m pip install -e '.[viz]'
python scripts/run_analytical_design_workflow.py --candidate reference --output candidate_reference.json
python scripts/run_analytical_design_workflow.py --candidate rack_aft_5mm --output candidate_rack_aft_5mm.json
python scripts/run_analytical_design_workflow.py --candidate rack_forward_5mm --output candidate_rack_forward_5mm.json
python scripts/package_analytical_design_workflow.py \
  --reports candidate_reference.json candidate_rack_aft_5mm.json candidate_rack_forward_5mm.json \
  --output-dir analytical_comparison --figures
```

Open `analytical_comparison/index.html` locally. No external JavaScript or web
service is required. The UI filters solved evidence; configuration/run inputs
remain explicit CLI controls in this first slice. No preferred design is selected.
The [recorded comparison viewer](docs/reports/analytical_design_workflow_v0.1.0/index.html)
contains the first complete 51-case result.

## Source-of-truth boundaries

- **Git** owns machine-readable definitions, schemas, tests, audit records, migration decisions, and release history.
- **The application database/UI** will present and edit those records without creating a second source of truth.
- **Google Drive** holds review-facing documents, calibration procedures, design-review material, and approved exports.
- **Raw telemetry and large datasets** remain immutable external files referenced by hashes and metadata.
- **External tools** such as OptimumK, ADAMS, VI-Grade, and ANSYS are optional adapters, not hidden dependencies of the core model.

## Development rules

1. Use reviewed branches and pull requests.
2. Do not add hidden constants, untyped parameters, or untraceable equations.
3. Preserve raw data and legacy logic; deprecate through explicit migration records.
4. Separate sensor calibration, parameter identification, and model validation datasets.
5. Treat numerical convergence and physical correctness as separate acceptance criteria.

Run the Phase registry checks with:

```bash
python scripts/validate_registry.py
python -m unittest discover -s tests
```

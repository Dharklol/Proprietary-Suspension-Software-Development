# Proprietary Suspension Software Development

Private, local-first vehicle-dynamics engineering platform for WashU Racing.

## Current phase

The project begins with **Phase 0: Model Assurance and Migration**. No physical model, equation, parameter, or legacy calculator is authoritative merely because it already exists. Every result used for a design decision must be traceable to its definition, derivation, assumptions, evidence, uncertainty, applicable operating range, numerical behavior, dependencies, and verification status.

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

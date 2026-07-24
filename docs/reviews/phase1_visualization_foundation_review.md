# Phase 1 Visualization Foundation Review

## Scope

This review covers the first engineering visualization increment after steering R&D closeout. It introduces no new vehicle physics and does not change any existing steering, tire, or vehicle result.

## Decision

The visualization layer is accepted for development as a strictly downstream consumer of already-computed result values. Numerical/model packages remain headless and dependency-light. Matplotlib is isolated behind the optional `viz` dependency group and a dedicated renderer module.

## Required behaviors

- Figure identity, quantity labels/units, model ID, configuration ID, state IDs, source IDs, authority, and notes travel with the figure specification.
- Available figures require explicit finite series values.
- Missing source data must render an explicit `FIGURE UNAVAILABLE` result with a reason; blank figures and inferred replacement data are prohibited.
- SVG is the preferred review artifact, with PNG as a convenience export.
- Rendered artifacts are hashed and associated with the canonical figure specification through JSON manifests.
- Rendering is headless and does not import Matplotlib through the base `pssd_viz` package.
- No plotting helper may calculate steering, tire, suspension, or vehicle physics.

## Verification

`tests/test_visualization_foundation.py` verifies contract validation, finite-series requirements, deterministic spec fingerprints, artifact hashing, report manifests, available/unavailable rendering, and deterministic SVG output when the optional backend is installed.

`.github/workflows/visualization-validation.yml` installs `.[viz]`, executes the visualization tests, generates the smoke report, and uploads both SVG and PNG outputs with sidecar manifests.

The smoke values are synthetic visualization evidence only and are explicitly labeled as such.

## Deferred scope

The following are separate follow-on increments:

- steering-specific engineering figure adapters and the PDR figure suite;
- comparison/constraint/sensitivity plot layouts beyond the generic line renderer;
- 3D scene interchange schema;
- browser/Three.js engineering viewer;
- CAD meshes;
- interactive GUI/workbench;
- subsystem physics changes.

# Phase 1 steering 3D viewer review

## Scope

This review covers the provider-neutral engineering scene contract, the WUFR-27 rigid steering scene adapter, and the lightweight browser viewer proof-of-concept.

It does not authorize new steering or suspension physics.

## Reviewed implementation

- `src/pssd_viz/scene3d.py`
- `src/pssd_viz/steering_scene.py`
- `src/pssd_viz/viewer3d.py`
- `scripts/run_steering_3d_viewer.py`
- `tests/test_scene3d_viewer.py`
- `docs/visualization/engineering_3d_scene_contract_v0.1.0.md`
- `docs/visualization/engineering_symbols_and_terminology_v0.1.0.md`

## Accepted boundaries

1. State-dependent steering joint positions originate from `MOD-STEER-0001`; the viewer does not solve linkage closure.
2. The scene is expressed in the canonical right-handed body orientation `+x` forward, `+y` vehicle left, `+z` upward.
3. Standard engineering symbols accompany full labels, including `x_r`, `θ_u`, `L_tr`, `ΔL_tr`, `x_B`, `y_B`, and `z_B`.
4. The body-axis display anchor at the rack-axis origin is visualization-only and is not a body-origin claim.
5. Wheel centres, wheel planes, tire geometry, suspension links, and chassis surfaces are omitted rather than inferred from incomplete steering-only data.
6. Infeasible model states must render an explicit warning rather than silently displaying stale geometry.
7. Interactive visualization is for understanding/debugging. Static reports and machine-readable model outputs remain the engineering evidence path.
8. The Three.js browser dependency remains outside the Python physics runtime.

## Promotion rule

This viewer may be used in the R&D workflow to inspect coordinate conventions, rack/tie-rod motion, branch continuity, and later subsystem integration. It does not establish installed steering geometry, physical compliance/backlash, wheel-centre position, suspension kinematics, or production authority.

## Next integration

The next high-value 3D expansion should occur with `MOD-SUSP-0001`, adding reviewed suspension hardpoints, wheel centres, upright/wheel orientation, and bump/heave/roll states through the same scene contract. The viewer should not grow a second kinematics implementation while waiting for those sources.

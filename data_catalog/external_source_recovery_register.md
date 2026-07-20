# External Source Recovery Register

**Status:** Active Phase 0 recovery backlog  
**Purpose:** Recover the exact files, versions, input decks, scripts, exports, and raw measurements referenced by the legacy calculators.

Catalog IDs identify artifacts and searches, not equation/model records.

## Required metadata

Every recovered artifact requires exact name/type, controlled location, SHA-256, owner, timestamps, software/version, vehicle/setup revision, input definitions, coordinate/sign conventions, procedure, output definitions, access restrictions, related registry IDs, and evidence role.

Provider hashes such as Box SHA-1 support discovery and change detection but do not replace project SHA-256.

## Recovery backlog

| Catalog ID | Artifact or source | Current status | Required recovery result | Evidence role |
|---|---|---|---|---|
| `CAT-EXT-0001` | Legacy tie-rod optimization process | Selection chain located | Link FDR Test 3 selection, final CAD, candidate studies, final-motion export, variables, bounds, objective, and final tie-rod definition | Legacy reproduction and design intent |
| `CAT-EXT-0002` | WUFR-24 steering CAD motion study | Calculator export present; parent missing | CAD revision, study definition, inputs/outputs, resolution, raw export hash | Historical cross-tool evidence |
| `CAT-EXT-0003` | WUFR-25 steering CAD motion study | CAD candidates, raw/converted export, and MATLAB trade study located | Establish exact CAD-to-export lineage and preserve wheel-angle transformation separately from effort/range objective | Historical cross-tool benchmark |
| `CAT-EXT-0004` | WUFR-26 final steering CAD and motion study | `GEOMETRY FINAL.SLDPRT`, FDR Test 3 mapping, and final export located | Record configuration, studies, dependencies, quantity definitions, angle transformation, operational domain, warnings, and SHA-256 | Primary legacy CAD benchmark |
| `CAT-EXT-0005` | MATLAB tire fitting script | Not recovered | Script, dependencies, input hashes, formulation, weighting, residuals, units | Derived-model provenance |
| `CAT-EXT-0006` | Source tire test dataset | Not recovered | Tire/rim/pressure/speed/load/camber/slip/temperature/surface metadata and license | Historical tire evidence |
| `CAT-EXT-0007` | Current tire dataset and processing chain | Unresolved | Current data, preprocessing, signs/units, filtering, model, uncertainty | Identification and validation, partitioned |
| `CAT-EXT-0008` | MATLAB steering-breakaway result | Source missing | Script/model, tire state, load, camber, pressure, slip, speed, output definition | Legacy benchmark candidate |
| `CAT-EXT-0009` | `ARB Calculations.xlsx` | Missing | Workbook, hash, geometry, material, installation ratio, definitions, validation | Legacy source or retired artifact |
| `CAT-EXT-0010` | Natural-frequency linked source | Missing | Exact file, formulas, assumptions, vehicle revision | Historical context |
| `CAT-EXT-0011` | Tire/vehicle transient MATLAB simulations | Missing or unindexed | Scripts, maneuvers, parameters, solvers, exports | Research evidence |
| `CAT-EXT-0012` | Box tire-force source folders | Not catalogued | Paths, contents, access, hashes, ownership, revisions | Recovery container |
| `CAT-EXT-0013` | Sheet8 corner-weight/ride-height test | Unknown | Date, vehicle/load, calibration, method, raw readings, repeatability | Calibration evidence or archive |
| `CAT-EXT-0014` | Alignment fixture/procedure | Partial notes | Fixture geometry, calibration, sign, uncertainty, procedure | Calibration/procedure source |
| `CAT-EXT-0015` | Understeer/cornering-stiffness polynomial source | Basis unclear | Tire/model source, fit range, units, derivation, vehicle state | Benchmark or retired provenance |
| `CAT-EXT-0016` | Steering-force and steering-axis geometry | Final/supporting CAD located | Caster/KPI/scrub/trail, steering axes, rack/tie-rod hardpoints, frame, units, uncertainty | Geometry evidence |
| `CAT-EXT-0017` | Steering-column gear/bearing design source | CAD/drawings located; linkage incomplete | Drawings, supports, gear data, efficiency, material, load cases | Structural provenance |
| `CAT-EXT-0018` | Sheet18 source context | Unknown | Identify study, x-axis, torque source, charts, units | Unknown |
| `CAT-EXT-0019` | LLTD raw logger file | Paste area only | Original file, export settings, logger setup, test/setup/maneuver, hash | Identification/validation candidate |
| `CAT-EXT-0020` | LLTD ride-height calibration | Zero/scales only | Rig, curve, target, pose, uncertainty, temperature | Sensor calibration |
| `CAT-EXT-0021` | LLTD damper-pot calibration/kinematics | Constant scales only | Pot calibration, mounting, suspension map, variable motion ratio, uncertainty | Calibration/kinematic evidence |
| `CAT-EXT-0022` | Chassis torsional-stiffness source | Value present; definition unresolved | Test/FEA, planes, fixtures, load path, linear range, uncertainty | Parameter evidence |
| `CAT-EXT-0023` | Front/rear ARB installed stiffness | Conflicting definitions | Bar torsion, arms, links, wheel/roll contribution, test/CAD source | Parameter evidence |
| `CAT-EXT-0024` | Sensor registry/logger revisions | Inventory partial | Channel IDs, logger names, units, rates, filters, clocks, calibrations, poses | Sensor registry source |
| `CAT-EXT-0025` | Physical steering sweep | Not identified | Rack and left/right wheel angles versus input, setup, uncertainty, load/compliance | Independent physical validation |
| `CAT-EXT-0026` | Steering FDR final-results table | Selection text and interpretation confirmed; exact artifact not catalogued | Exact file/path, table, author/revision, Test 3 selection, final specifications, hash | Design-selection authority |
| `CAT-EXT-0027` | WUFR-25 `Steering_range_optimization.m` | Source text and Box SHA-1 recorded | SHA-256 and PDR/FDR definitions for constants, units, target, selected result | Historical effort/range intent |
| `CAT-EXT-0028` | `2026Ackermann.csv` | Final-motion export located and structurally parsed | SHA-256, parent-study identity, driver/monitor definitions, straight-ahead reference, branch orientation, physical domain | Primary WUFR-26 final-response export |

## Steering source detail

Recovered steering evidence is documented in:

- `data_catalog/steering_source_recovery_log.md`;
- `data_catalog/steering_box_source_manifest.toml`;
- `data_catalog/steering_box_directory_inventory.md`;
- `data_catalog/wufr26_test3_selected_lineage.md`;
- `migration/legacy_calculators/steering_tie_rod_optimizer/wufr25_matlab_audit.md`;
- `migration/legacy_calculators/steering_tie_rod_optimizer/steer_ratio_fit_reconstruction.md`;
- `benchmarks/steering/wufr26_ackermann_export.toml`.

## Recovery procedure

1. Search Drive, Box, Git, team computers, CAD/PDM, MATLAB folders, logger exports, and binders.
2. Preserve original bytes without modification.
3. Compute SHA-256 before freezing extracted results.
4. Identify source, export, derivative, calibration, identification, and validation relationships.
5. Record unknown metadata explicitly.
6. Link artifacts to migration/model/benchmark records.
7. Freeze derived benchmark extracts separately with parent hashes.
8. Mark formally unavailable only after documented searches and reviewer signoff.

## Priority

**Priority A:** `CAT-EXT-0001` through `0008`, `0019` through `0023`, and `0025` through `0028`.  
**Priority B:** `0009`, `0013` through `0017`, and `0024`.  
**Priority C:** `0010` and `0018`.

## Completion criterion

An artifact is recovered only when immutable bytes, project hash, location, ownership, revision, configuration, definitions, and evidence role are recorded. A similarly named file, copied polynomial, screenshot, or summary table is insufficient.

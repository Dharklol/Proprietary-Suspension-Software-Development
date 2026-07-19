# External Source Recovery Register

**Status:** Active Phase 0 recovery backlog  
**Purpose:** Recover the exact files, versions, input decks, scripts, exports, and raw measurements referenced by the legacy calculators.

Catalog IDs in this file identify artifacts and searches. They are not equation/model registry IDs.

## Required metadata for every recovered artifact

- catalog ID;
- exact file name and file type;
- storage location;
- SHA-256 hash;
- author/owner;
- creation and modification date;
- software and version;
- vehicle and setup revision;
- source inputs and their units;
- coordinate/sign conventions;
- calculation/sweep/test procedure;
- output definitions;
- access restrictions;
- related migration, quantity, equation, model, benchmark, and risk IDs;
- whether the artifact is a source, derived copy, calibration item, identification item, validation item, or historical context.

## Recovery backlog

| Catalog ID | Artifact or source | Referenced by | Current status | Required recovery result | Intended evidence role |
|---|---|---|---|---|---|
| `CAT-EXT-0001` | Legacy tie-rod-length optimizer | `MIG-STR-0001` | Not located | Exact workbook/script/CAD design study, inputs, bounds, objective, software, vehicle revision, and output definition | Legacy reproduction benchmark |
| `CAT-EXT-0002` | WUFR-24 steering CAD motion study | `MIG-SC26-SR-001`, `MIG-SC26-ACK-002` | Spreadsheet export present; source model missing | CAD assembly revision, motion-study definition, input coordinate, output wheel-angle definitions, sweep resolution, exported table hash | Cross-tool evidence and historical context |
| `CAT-EXT-0003` | WUFR-25 steering CAD motion study | `MIG-SC26-SR-003`, `MIG-SC26-ACK-002` | Spreadsheet export present; source model missing | Same metadata as `CAT-EXT-0002` | Cross-tool evidence and historical context |
| `CAT-EXT-0004` | WUFR-26 steering motion study or measurement source | `MIG-SC26-ACK-002`, `MIG-STR-0001` | Values present without full provenance | Geometry revision, source model/test, zero and sign, left/right definitions, uncertainty | Current-design benchmark candidate |
| `CAT-EXT-0005` | MATLAB tire fitting script | `MIG-SC26-TIRE-001`, `MIG-SC26-SB-001`, understeer and steering-force sheets | Not recovered | Script, dependency versions, input file names/hashes, fit formulation, weighting, residuals, and output units | Derived-model provenance |
| `CAT-EXT-0006` | Source tire test dataset | `MIG-SC26-TIRE-001` | Not recovered | Exact tire, rim, pressure, speed, load, camber, slip, temperature/condition, surface, channels, and license/access metadata | Historical tire evidence; possible benchmark only |
| `CAT-EXT-0007` | Current tire dataset and processing chain | Future canonical tire model | Location/status unresolved | Current tire data, preprocessing, sign/unit conversions, filtering, fitting/lookup method, and uncertainty | Parameter identification and model validation, partitioned |
| `CAT-EXT-0008` | MATLAB steering-breakaway result | `MIG-SC26-SB-001` | Result referenced; source missing | Model/script, selected tire state, normal load, camber, pressure, slip, speed, and output force/moment definition | Legacy benchmark candidate |
| `CAT-EXT-0009` | `ARB Calculations.xlsx` | `MIG-SC26-ARB-001` | Missing | Exact workbook, hash, author/date, bar geometry, material, installation ratio, unit definitions, and validation | Legacy source or retired artifact |
| `CAT-EXT-0010` | Natural-frequency linked source | `MIG-SC26-NF-001` | Missing | Exact file/link target, formulas, assumptions, vehicle revision | Historical context or benchmark |
| `CAT-EXT-0011` | Tire/vehicle transient MATLAB simulations referenced in notes | Load transfer, tire, steering, handling sheets | Missing or unindexed | Scripts/models, maneuver definitions, parameter files, solver settings, result exports | Research evidence |
| `CAT-EXT-0012` | Box folders referenced by tire-force notes | `MIG-SC26-TIRE-001/002` | Box location not catalogued | Folder path, contained files, access control, hashes, ownership, revision history | Source recovery container |
| `CAT-EXT-0013` | Original Sheet8 corner-weight/ride-height test record | `MIG-SC26-CAL-001` | Unknown | Date, vehicle, driver/load state, scale calibration, ride-height method, raw readings, repeatability | Installation-calibration evidence or archive |
| `CAT-EXT-0014` | Alignment fixture geometry and measurement procedure | `MIG-SC26-ALIGN-001/002/003` | Partial spreadsheet notes only | String/bar locations, rim diameter/measurement points, calibration, sign, uncertainty, technician steps | Calibration/procedure source |
| `CAT-EXT-0015` | Understeer/cornering-stiffness polynomial source | `MIG-SC26-US-001/003/004/005/006/007/008` | Embedded formulas; source basis unclear | Tire/model source, fit range, units, derivation, vehicle state, intended metric | Benchmark or retired-model provenance |
| `CAT-EXT-0016` | Steering-force geometry source | `MIG-SC26-SF-*` | Spreadsheet values only | CAD/measurement source for caster, KPI, scrub, trail, steering-axis, rack/tie-rod geometry | Parameter evidence |
| `CAT-EXT-0017` | Steering-column gear and bearing design source | `MIG-SC26-SCF-*` | Spreadsheet geometry only | Drawings/CAD, support locations, gear data, efficiency assumptions, material and load cases | Structural benchmark provenance |
| `CAT-EXT-0018` | Sheet18 source context | `MIG-SC26-UNK-001` | Unknown | Identify original study, x-axis quantity, torque source, charts, and units | Unknown until recovered |
| `CAT-EXT-0019` | LLTD raw logger file used by workbook | `MIG-LLTD-RAW-001` | Paste area exists; original file not catalogued | Original immutable logger file, export settings, logger configuration, test date, vehicle setup, maneuver, and hash | Identification/validation candidate after partition |
| `CAT-EXT-0020` | LLTD ride-height sensor calibration | `MIG-LLTD-IN-002`, `MIG-LLTD-DER-002/003` | Zero values/scales only | Calibration rig, voltage/distance curve, target properties, sensor pose, uncertainty, temperature behavior | Sensor and installation calibration |
| `CAT-EXT-0021` | LLTD damper-pot calibration and kinematic conversion | `MIG-LLTD-IN-002`, `MIG-LLTD-DER-001/004` | Constant scales only | Pot calibration, mounting geometry, suspension map, motion-ratio variation, uncertainty | Sensor/install calibration and kinematic evidence |
| `CAT-EXT-0022` | Chassis torsional-stiffness measurement/FEA source | `MIG-LLTD-IN-003`, future coupled chassis model | Value present; definition unresolved | Bare-frame/installed test or FEA, front/rear plane locations, fixture compliance, load path, linear range, uncertainty | Parameter evidence and validation |
| `CAT-EXT-0023` | Front/rear ARB installed stiffness source | `MIG-LLTD-IN-003`, `MIG-SC26-LT-004/005` | Conflicting values/definitions | Bar torsion, arm geometry, link motion, wheel-rate and axle-roll contribution, test/CAD source | Parameter evidence |
| `CAT-EXT-0024` | WUFR sensor registry and logger configuration revisions | LLTD and Phase 5 planning | Sensor list available; detailed channel metadata incomplete | Channel IDs, logger names, units, sampling, filters, clocks, calibration revisions, sensor poses | Canonical sensor/channel registry source |
| `CAT-EXT-0025` | Physical steering sweep measurements | `BENCH-STEER-0001`, future verification level F | Not yet identified | Rack displacement and left/right road-wheel angle versus input, setup state, uncertainty, compliance/load condition | Independent physical validation |

## Search and recovery procedure

1. Search Drive, Box, Git history, team laptops, CAD PDM, MATLAB folders, logger exports, and archived design binders using exact and variant names.
2. Copy recovered artifacts into their appropriate controlled storage location without modifying the original bytes.
3. Compute SHA-256 and create a catalog entry before extracting results.
4. Identify source versus export versus derivative relationships.
5. Record missing metadata as explicit unknowns rather than inferring it silently.
6. Link every recovered artifact to the migration blocks it can verify or explain.
7. Freeze benchmark extracts as separate, versioned derived artifacts with parent hashes.
8. Mark an item `formally unavailable` only after the search locations and responsible reviewer are documented.

## Recovery priority

### Priority A — blocks first implementation or high-risk interpretation

- `CAT-EXT-0001` through `CAT-EXT-0008`;
- `CAT-EXT-0019` through `CAT-EXT-0023`;
- `CAT-EXT-0025`.

### Priority B — preserves useful structural/setup work

- `CAT-EXT-0009`;
- `CAT-EXT-0013` through `CAT-EXT-0017`;
- `CAT-EXT-0024`.

### Priority C — may be deprecated after documented search

- `CAT-EXT-0010`;
- `CAT-EXT-0018`.

## Completion criteria

An artifact is recovered only when its bytes, hash, location, ownership, revision, configuration, definitions, and evidence role are recorded. Finding a similarly named file or a screenshot is not sufficient.

# Steering Source-Recovery Log

**Status:** Active; WUFR-26 final Test 3 lineage established  
**Related IDs:** `MIG-STR-0001`, `MOD-STEER-0001`, `BENCH-STEER-0001`, `CAT-EXT-0001` through `CAT-EXT-0004`, `CAT-EXT-0016`, `CAT-EXT-0025`

## Purpose

This log records actual searches and recovered steering artifacts separately from the recovery backlog. It prevents a similarly named file, copied curve, screenshot, remembered value, or final summary table from being treated as the complete mechanism source.

## Evidence-state vocabulary

- **Not searched:** no documented search has been performed.
- **Search attempted:** one or more locations were searched, but completeness is not established.
- **Candidate located:** a possibly relevant artifact was found; identity and lineage remain unverified.
- **Source located:** the original source item and provider metadata were found, but project hashing or internal model metadata may remain open.
- **Export recovered:** a derived table, CSV, screenshot, or report exists, but its exact source configuration is not fully mapped.
- **Source recovered:** immutable bytes, project hash, lineage, definitions, and required metadata are catalogued.
- **Benchmark source designated:** the team has selected the source that should define the legacy comparison.
- **Selection mapping established:** the design-decision record, candidate label, raw export, and parent model have been linked, but benchmark definitions or hashes remain open.
- **Benchmark frozen:** a versioned extract with parent hash, expected inputs, expected outputs, and tolerances is approved.
- **Formally unavailable:** required locations and responsible reviewers have completed and documented the search.

## Search records

### Search `SRCH-STEER-0001`

- **Date:** 2026-07-18
- **Locations attempted:** indexed project sources available to ChatGPT, GitHub repository, and direct Google Drive connector invocation.
- **Result:** spreadsheet exports and historical values were located, but the exact CAD source was not yet found.
- **Limitation:** Drive search was unavailable during this attempt.
- **Disposition:** superseded by the Box-assisted search below; retained as search history.

### Search `SRCH-STEER-0002`

- **Date:** 2026-07-19
- **Locations searched:** Box WUFR-26 and WUFR-25 CAD trees, the WUFR-26 `6. STEERING/998. GEOMETRY` directory, and the WUFR-25 steering geometry directory.
- **Team clarifications applied:**
  - `GEOMETRY FINAL.SLDPRT` is the final WUFR-26 benchmark geometry;
  - `Steering Length Optimization Tests.xlsx` is a reference comparison workbook, not the final authority;
  - the final selected result is recorded in a steering FDR table;
  - `Steering_range_optimization.m` is the sole MATLAB file for the WUFR-25 steering-range study;
  - six CSVs represent different studies produced from the second motion study to graph Ackermann curves;
  - the calculator `Steer Ratio` tab contains WUFR-24 and WUFR-25 SolidWorks exports only;
  - one of the six CSVs contains the WUFR-26 curve.
- **Result:** the principal CAD source, six study exports, comparison workbook, supporting SolidWorks parts, and WUFR-25 MATLAB script were located and provider hashes recorded.
- **Disposition:** source recovery now proceeds through configuration/study extraction, SHA-256 capture, CSV-to-test mapping, and FDR linkage rather than broad file discovery.

### Selection clarification `SRCH-STEER-0003`

- **Date:** 2026-07-19
- **Team authority statement:** the WUFR-26 steering FDR table beneath `SO EVERYONE KNOWS, here is the FINAL geometry specifications:` states that the final geometry is based on `Test 3`.
- **Relative placement meaning:** `0.5 inch back` means the chosen rack placement is 0.5 in rearward relative to the previous-year rack placement.
- **Mapped reference record:** the `Test 3` column in `Steering Length Optimization Tests.xlsx`.
- **Mapped raw export:** `Test_3.csv`, Box file ID `1938821987892`, Box SHA-1 `2753dd225b2c95c2cc0c6635f9e3f7b1493692cc`.
- **Mapped parent CAD:** `GEOMETRY FINAL.SLDPRT`, Box file ID `1971276311204`.
- **Disposition:** `Selection mapping established`. The selected CSV is no longer open, but the exact FDR file/hash, SolidWorks internal study metadata, output identity, canonical frame, and project SHA-256 remain required before benchmark freeze.

The detailed lineage and workbook observations are recorded in `data_catalog/wufr26_test3_selected_lineage.md`.

## Recovered WUFR-26 source directory

**Box path:** `WashURacing/6. WUFR-26/WUFR-26 CAD AND DRAWINGS/6. STEERING/998. GEOMETRY`  
**Box folder ID:** `333299255935`

The controlled manifest is `data_catalog/steering_box_source_manifest.toml`. The human-readable directory inventory is `data_catalog/steering_box_directory_inventory.md`.

### Primary benchmark source

| Field | Recovered value |
|---|---|
| File | `GEOMETRY FINAL.SLDPRT` |
| Box file ID | `1971276311204` |
| Box file version ID | `2551939123052` |
| Box SHA-1 | `7323d2abfc391e3c814a94573e027f101318458c` |
| Size | `104508` bytes |
| Vehicle | WUFR-26 |
| Team authority statement | Final benchmark geometry |
| Current evidence state | `Benchmark source designated` |

This designation identifies which CAD source should be reproduced. It does not yet freeze a benchmark because the active SolidWorks configuration, motion-study definitions, units, coordinate system, warnings, external references, and raw-byte SHA-256 remain open.

### Selected second-motion-study export

| Field | Recovered value |
|---|---|
| Selected candidate | `Test 3` |
| File | `Test_3.csv` |
| Box file ID | `1938821987892` |
| Box SHA-1 | `2753dd225b2c95c2cc0c6635f9e3f7b1493692cc` |
| Selection authority | WUFR-26 steering FDR final geometry table |
| Reference cross-check | `Test 3` column in `Steering Length Optimization Tests.xlsx` |
| Current evidence state | `Selection mapping established` |

The extracted CSV representation identifies a SolidWorks design study with 231 scenario columns, a driver row named `Steer_Angle`, and a monitored angular row named `Measurement1`. The leading scenario cells appear incomplete in the extracted representation. The raw bytes must therefore be parsed before the sweep domain or expected point count is frozen.

### Alternative second-motion-study CSV set

The other five files are preserved as alternative geometry studies used to graph Ackermann curves:

| File | Box file ID | Box SHA-1 | Current state |
|---|---:|---|---|
| `3.5INREV_WUFR25.csv` | `1939621786957` | `2b698b9819431fb36a1812c0a51808bf698c28e5` | Export recovered; alternative-study mapping open |
| `Test_1.csv` | `1938720503009` | `195964c13ae1d3720711f2c4ebb0f9ff9c8a0012` | Export recovered; alternative-study mapping open |
| `Test_2.csv` | `1938779118142` | `593c2f8b918ee4c103168af30c8b7e763f5bbff8` | Export recovered; alternative-study mapping open |
| `Test_4.csv` | `1939641496772` | `4464738af0fa8b8fc43edd1f71c51734b37ce57d` | Export recovered; alternative-study mapping open |
| `WUFR_25.csv` | `1939617196379` | `b7a1d419995a4f63132839c819d18460b825a401` | Export recovered; historical/alternative mapping open |

These files remain useful evidence. Non-selected studies are not deleted, averaged, or relabeled as bad data.

### Reference comparison workbook

| Field | Recovered value |
|---|---|
| File | `Steering Length Optimization Tests.xlsx` |
| Box file ID | `1939770957296` |
| Box SHA-1 | `2069922fc3dac8889d84a92275e35486caef3284` |
| Selected reference column | `Test 3` |
| Current evidence role | Candidate-test reference and design-intent evidence |
| Authority restriction | Not the final selected-result authority |

The workbook `Test 3` column includes rack offset/type, rack displacement, tie-rod length, steering-arm length, left/right turn outputs, steering input, effort-reduction estimate, and joint coordinates. These values are retained in the workbook's native definitions until units, coordinate frame, datums, and output meanings are documented.

The FDR's relative `0.5 inch back` statement must not be silently equated to the workbook's `Rack Offset = 2.62` field. The former controls relative design intent; the latter remains a legacy workbook quantity until its reference is resolved.

### Supporting SolidWorks items

- `STEERING ACKERMAN CALC.SLDPRT`, Box ID `1938696794169`, SHA-1 `5f167423d028189c6f844a524474eb1ecc210516`;
- `STEERING GEOMETRY 2.SLDPRT`, Box ID `1938932569209`, SHA-1 `c72aaeeef42bc0cb2ad1ae0b1c01af388f6147c6`;
- `STEERING GEOMETRY.SLDPRT`, Box ID `1938693851076`, SHA-1 `2136e377e144fe513d5750d807b082ce5a33a6e1`;
- `ASSEMBLIES` subfolder, Box ID `337880624540`.

These are candidate dependencies or predecessors. They do not supersede `GEOMETRY FINAL.SLDPRT` and must be examined only to establish external references, study lineage, and implementation context.

## WUFR-25 MATLAB source

| Field | Recovered value |
|---|---|
| File | `Steering_range_optimization.m` |
| Box file ID | `2025945253796` |
| Box SHA-1 | `4a4dfbf78a96e00840aef9f86e30dfee06331d65` |
| Path | `WUFR-25 CAD & SOLIDWORKS DRAWINGS/4. STEERING/GEOMETRY` |
| Current evidence state | Source text recovered and inventoried |

The script performs a one-variable steering-range/effort trade study. It does not calculate tie-rod geometry, left/right road-wheel kinematics, or Ackermann curves. Its preliminary disposition is historical design-intent evidence and benchmark-only reproduction. The detailed audit is `migration/legacy_calculators/steering_tie_rod_optimizer/wufr25_matlab_audit.md`.

## Calculator lineage

The `Steer Ratio` sheet in `Suspension Calculations 2026` contains imported SolidWorks data for WUFR-24 and WUFR-25. It remains useful historical export evidence but is not the WUFR-26 source. The WUFR-26 curve enters the migration through `Test_3.csv` and its parent `GEOMETRY FINAL.SLDPRT` source.

## Artifact-specific status

| Catalog ID | Artifact | Current state | Evidence presently available | Next recovery action |
|---|---|---|---|---|
| `CAT-EXT-0001` | Legacy tie-rod optimization process | Selection mapping established | Test 3 FDR selection, Test 3 workbook column, `Test_3.csv`, final CAD source | Recover exact objective/bounds, final tie-rod definition, and SolidWorks study metadata |
| `CAT-EXT-0002` | WUFR-24 steering CAD motion study | Export recovered | Pasted design-study table in `Steer Ratio` | Recover original WUFR-24 CAD model only if needed for historical regression |
| `CAT-EXT-0003` | WUFR-25 steering CAD motion study | Source candidates and export recovered | Calculator export, WUFR-25 CAD geometry, and MATLAB range trade study | Freeze exact parent CAD/export relationship before historical benchmark use |
| `CAT-EXT-0004` | WUFR-26 steering CAD and motion-study source | Selection mapping established | `GEOMETRY FINAL.SLDPRT`, `Test_3.csv`, FDR Test 3 statement, reference workbook | Catalog exact FDR artifact; capture SolidWorks metadata, output definitions, and SHA-256 |
| `CAT-EXT-0016` | Steering geometry source | Source located | Final and supporting WUFR-26 CAD parts plus steering assembly/drawings | Export canonical hardpoints and steering-axis/rack definitions with frame and units |
| `CAT-EXT-0025` | Physical steering sweep | Not yet identified | No confirmed raw physical sweep | Search testing records or define a new fixture test |

## Next controlled actions

1. Catalog the exact WUFR-26 steering FDR file, table location, version, and hash.
2. Download immutable bytes for `GEOMETRY FINAL.SLDPRT`, `Test_3.csv`, the workbook, and the FDR and compute SHA-256.
3. Inspect `GEOMETRY FINAL.SLDPRT` in SolidWorks and record active configuration, study names, dimensions, equations, mates, coordinate system, units, warnings, and external references.
4. Map `Steer_Angle` and `Measurement1` to canonical driver and road-wheel output quantities; locate the complementary wheel-angle output used for the Ackermann graph.
5. Parse the complete selected steering map without polynomial fitting or manual repair and identify valid populated scenario rows.
6. Resolve the previous-year datum and coordinate direction behind the FDR's `0.5 inch back` specification.
7. Freeze the other five CSVs as alternative-configuration evidence for optimizer regression and tradeoff review.
8. Create a physical sweep plan if no independent vehicle/fixture data can be recovered.

## Recovery decision rules

1. `GEOMETRY FINAL.SLDPRT` is the selected legacy CAD source, but source designation alone is not benchmark freeze.
2. The FDR selects Test 3; `Test_3.csv` defines the selected legacy response once its output meanings are resolved.
3. The reference workbook documents Test 3 inputs and summary outputs but cannot independently prove the response it summarizes.
4. The phrase `0.5 inch back` is a relative design specification and cannot become a canonical coordinate without a declared frame and datum.
5. A polynomial copied into the calculator is not the mechanism source.
6. A curve used to identify unknown geometry cannot also be claimed as independent validation of that identified geometry.
7. The five alternative CSVs are preserved; non-selected studies are not deleted as bad data.
8. A provider SHA-1 is recorded for discovery, but project SHA-256 remains required before freeze.
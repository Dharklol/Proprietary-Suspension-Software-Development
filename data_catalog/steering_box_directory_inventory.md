# WUFR-26 Steering Geometry Box Inventory

**Status:** Recovered directory inventory; benchmark extraction remains open  
**Box folder:** `WashURacing/6. WUFR-26/WUFR-26 CAD AND DRAWINGS/6. STEERING/998. GEOMETRY`  
**Box folder ID:** `333299255935`  
**Related IDs:** `MIG-STR-0001`, `MOD-STEER-0001`, `BENCH-STEER-0001`

## Authority and lineage decisions

The team has confirmed the following source hierarchy:

1. `GEOMETRY FINAL.SLDPRT` is the final WUFR-26 geometry and the primary SolidWorks benchmark source.
2. The steering FDR table records the final selected design result. It is the design-decision authority for identifying the chosen output, but it does not replace the CAD mechanism or raw motion-study export.
3. `Steering Length Optimization Tests.xlsx` is a comparison/reference table for several tests. It is not the final design authority.
4. The six CSV files in this directory are exports from different studies performed using the second SolidWorks motion study to graph Ackermann curves. One contains the WUFR-26 final output; the FDR table must be used to identify it rather than selecting by filename or apparent numerical quality.
5. The `Steer Ratio` sheet in `Suspension Calculations 2026` contains SolidWorks exports for WUFR-24 and WUFR-25 only. It does not contain the WUFR-26 curve.
6. The WUFR-25 MATLAB script is a historical steering-range/effort trade study, not the geometry mechanism or final tie-rod optimizer.

## Directory contents

| Manifest ID | File | Box ID | Box SHA-1 | Evidence role | Current disposition |
|---|---|---:|---|---|---|
| `STEER-BOX-0001` | `GEOMETRY FINAL.SLDPRT` | `1971276311204` | `7323d2abfc391e3c814a94573e027f101318458c` | Final WUFR-26 geometry and primary SolidWorks benchmark source | Preserve; extract configuration, studies, dimensions, mates, and raw curves |
| `STEER-BOX-0002` | `Steering Length Optimization Tests.xlsx` | `1939770957296` | `2069922fc3dac8889d84a92275e35486caef3284` | Candidate-test comparison table | Historical/reference evidence only |
| `STEER-BOX-0003` | `3.5INREV_WUFR25.csv` | `1939621786957` | `2b698b9819431fb36a1812c0a51808bf698c28e5` | Second-motion-study export | Preserve; map to study configuration and FDR result |
| `STEER-BOX-0004` | `Test_1.csv` | `1938720503009` | `195964c13ae1d3720711f2c4ebb0f9ff9c8a0012` | Second-motion-study export | Preserve; map to study configuration and FDR result |
| `STEER-BOX-0005` | `Test_2.csv` | `1938779118142` | `593c2f8b918ee4c103168af30c8b7e763f5bbff8` | Second-motion-study export | Preserve; map to study configuration and FDR result |
| `STEER-BOX-0006` | `Test_3.csv` | `1938821987892` | `2753dd225b2c95c2cc0c6635f9e3f7b1493692cc` | Second-motion-study export | Preserve; map to study configuration and FDR result |
| `STEER-BOX-0007` | `Test_4.csv` | `1939641496772` | `4464738af0fa8b8fc43edd1f71c51734b37ce57d` | Second-motion-study export | Preserve; map to study configuration and FDR result |
| `STEER-BOX-0008` | `WUFR_25.csv` | `1939617196379` | `b7a1d419995a4f63132839c819d18460b825a401` | Second-motion-study export | Preserve; likely historical comparison, but do not infer without study mapping |
| `STEER-BOX-0009` | `STEERING ACKERMAN CALC.SLDPRT` | `1938696794169` | `5f167423d028189c6f844a524474eb1ecc210516` | Supporting SolidWorks calculation part | Inspect and document relationship to motion studies |
| `STEER-BOX-0010` | `STEERING GEOMETRY 2.SLDPRT` | `1938932569209` | `c72aaeeef42bc0cb2ad1ae0b1c01af388f6147c6` | Supporting geometry and probable second-study source | Inspect; do not supersede `GEOMETRY FINAL.SLDPRT` |
| `STEER-BOX-0011` | `STEERING GEOMETRY.SLDPRT` | `1938693851076` | `2136e377e144fe513d5750d807b082ce5a33a6e1` | Earlier/supporting geometry | Establish revision lineage |

The directory also contains an `ASSEMBLIES` subfolder. Its dependencies must be captured when `GEOMETRY FINAL.SLDPRT` is opened or exported, because a SolidWorks part may reference external geometry, equations, design tables, or linked values that are not visible from the file name alone.

## Recovered reference-table structure

`Steering Length Optimization Tests.xlsx` contains a baseline and five candidate tests with entries for:

- rack offset;
- rack type;
- rack displacement;
- tie-rod length;
- steering-arm length;
- right and left turn outputs;
- steering input;
- estimated steering-effort decrease;
- geometry joint coordinates.

The workbook is valuable for reconstructing what was swept and what tradeoffs were considered. Its values remain observations until the FDR selection, SolidWorks study definitions, units, coordinate system, and tie-rod-length definition are linked.

## Recovered CSV structure

At least two inspected exports show standard SolidWorks design-study tables with:

- scenario count and scenario columns;
- a signed steering-input sweep in degrees;
- one monitored wheel-angle quantity;
- a `WHEEL OUTPUT` row;
- non-identical positive and negative output ranges.

This confirms they are rawer evidence than the spreadsheet polynomial fits. It does not yet establish which monitored dimension is the left wheel, which is the right wheel, whether the output is an upright rotation or road-wheel angle, or which CSV represents the selected WUFR-26 design.

## Required extraction before benchmark freeze

1. Download immutable bytes and compute project SHA-256 for the final CAD file, six CSVs, reference workbook, MATLAB script, and FDR artifact.
2. Open `GEOMETRY FINAL.SLDPRT` in a compatible SolidWorks environment and record:
   - SolidWorks version;
   - active configuration;
   - external references and equations;
   - units;
   - coordinate-system definition;
   - named dimensions and global variables;
   - motion-study names and driver definitions;
   - mates, suppression state, and warnings.
3. Identify the second motion study and map each of the six CSVs to its exact geometry/test configuration.
4. Recover the steering FDR and use its table to identify the selected final test and final tie-rod result.
5. Define every CSV output as left/right road-wheel angle, inner/outer angle, upright rotation, or another monitored dimension.
6. Freeze a benchmark extract from the selected CSV without polynomial fitting or manual editing.
7. Retain the other five curves as alternative-design evidence and optimizer regression cases, not as failed data.

## Non-circular-use rule

The selected SolidWorks curve may verify that the replacement mechanism reproduces the legacy CAD mechanism. It must not be used both to fit hidden geometry corrections and then to claim independent validation. Any geometry reconstructed from the same curve is an identification result; validation then requires another CAD output, analytical case, or physical steering sweep.

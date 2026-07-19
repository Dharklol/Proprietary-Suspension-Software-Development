# WUFR-26 Selected Steering Geometry Lineage

**Status:** Selection mapping established; benchmark freeze still pending source hashes and SolidWorks metadata  
**Related IDs:** `BENCH-STEER-0001`, `MIG-STR-0001`, `MOD-STEER-0001`, `CAT-EXT-0001`, `CAT-EXT-0004`

## Authority chain

The final WUFR-26 steering selection is now mapped as follows:

1. **Design-decision authority:** the WUFR-26 steering FDR table beneath the text `SO EVERYONE KNOWS, here is the FINAL geometry specifications:`.
2. **Selected candidate:** `Test 3`.
3. **Relative rack-placement intent:** `0.5 inch back` means the selected rack placement is 0.5 in rearward relative to the previous-year rack placement. This is a relative design statement; it must not be silently converted into a canonical coordinate until the vehicle frame, positive longitudinal direction, reference point, and previous-year datum are documented.
4. **Reference-workbook record:** the `Test 3` column in `Steering Length Optimization Tests.xlsx`.
5. **Raw SolidWorks export:** `Test_3.csv`, Box file ID `1938821987892`, Box SHA-1 `2753dd225b2c95c2cc0c6635f9e3f7b1493692cc`.
6. **Parent CAD benchmark source:** `GEOMETRY FINAL.SLDPRT`, Box file ID `1971276311204`.

This mapping identifies the selected legacy configuration. It does not prove physical correctness and does not make the FDR table or workbook independent validation evidence.

## Test 3 reference-workbook observations

The following values were recovered from the `Test 3` column. They remain in the workbook's native labels, units, and coordinate convention until those definitions are recovered.

| Workbook field | Test 3 value | Audit note |
|---|---:|---|
| Rack Offset | `2.62` | Native workbook quantity; do not equate directly to the FDR's relative `0.5 inch back` statement without the missing datum and axis definition |
| Rack Type | `New rack, 3.5` | Exact meaning of `3.5` and units remain to be documented |
| Rack displacement | `1` | Workbook note says `as before`; units and sign require confirmation |
| Tie rod length | `13` | Definition must distinguish center-to-center link length from projected or nominal length |
| Steering arm length | `2.70` | Measurement endpoints and units require confirmation |
| Right turn angle | `22.43` | Output zero, sign, wheel identity, and units require confirmation |
| Left turn angle | `32.08` | Output zero, sign, wheel identity, and units require confirmation |
| Steer input | `102` | Must identify steering-wheel, shaft, pinion, rack-driver, or study angle |
| Steering effort decrease from 2025 | `~14%` | Design-intent estimate; method and operating condition remain unresolved |
| Tie rod inner ball joint | `[x: 8.7, y: 6.28, z: -2.62]` | Legacy frame and units unresolved |
| Tie rod outer ball joint | `[x: 21.63, y: 7.57, z: -2.39]` | Legacy frame and units unresolved |
| Pivot point | `[x: 22.88, y: 7.76, z: 0]` | Exact steering-axis point definition unresolved |

The apparent numerical difference between the workbook's `Rack Offset` values and the FDR's `0.5 inch back` statement is retained as an explicit definition issue. The FDR controls the selected relative placement intent; the workbook value controls only its own legacy field until the reference geometry is reconstructed.

## Test_3.csv observations

The recovered CSV is a SolidWorks design-study export titled `Design Study 1` with 231 scenario columns. The populated steering-driver row is named `Steer_Angle`; the monitored output row is named `Measurement1` and is labeled in degrees.

The extracted representation presently shows blank leading scenario cells before the populated sweep begins. Therefore the raw CSV bytes must be parsed and checked before freezing the sweep domain or assuming that every scenario from 1 through 231 contains a valid point.

Open questions:

- Is `Steer_Angle` the same 102-degree quantity stated in the FDR/workbook, and where is it applied?
- Does `Measurement1` represent the left road wheel, right road wheel, inside wheel, outside wheel, or an intermediate angular dimension?
- Where is the complementary road-wheel output used to construct the Ackermann curve?
- Are the six CSVs single-wheel exports paired by sign, or separate geometry studies with additional hidden measurements?
- What SolidWorks configuration, equations, mates, and dimension names generated this file?

## Benchmark use

`BENCH-STEER-0001` will use `Test_3.csv` as the selected Level E legacy response after:

- immutable downloaded bytes receive project SHA-256 hashes;
- the FDR artifact and exact table location are catalogued and hashed;
- the SolidWorks study and active configuration are recorded;
- the driver and output quantities are mapped to canonical definitions;
- the sweep's valid populated rows are identified without polynomial fitting or manual curve repair;
- expected tolerances are approved based on CAD/export resolution.

The remaining five CSVs remain alternative-configuration regression evidence and must not be averaged into the selected result.
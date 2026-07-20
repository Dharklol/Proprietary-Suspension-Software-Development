# WUFR-26 Selected Steering Geometry Lineage

**Status:** Final configuration and final-motion export located; benchmark freeze pending definitions and project hashes  
**Related IDs:** `BENCH-STEER-0001`, `MIG-STR-0001`, `MOD-STEER-0001`, `CAT-EXT-0001`, `CAT-EXT-0004`

## Authority chain

1. The WUFR-26 steering FDR table beneath `SO EVERYONE KNOWS, here is the FINAL geometry specifications:` is the design-selection authority.
2. The selected candidate is `Test 3`.
3. `0.5 inch back` means the rack was selected 0.5 in rearward relative to the previous-year placement. It is not an absolute coordinate until the previous-year datum, rack reference point, frame, and longitudinal sign are recorded.
4. The `Test 3` column in `Steering Length Optimization Tests.xlsx` is a reference candidate record.
5. `Test_3.csv` is the selection-era SolidWorks response for Test 3.
6. `2026Ackermann.csv` is the team-provided export from the final-geometry second motion study.
7. `GEOMETRY FINAL.SLDPRT` is the parent mechanism source.

| Artifact | Box ID | Box SHA-1 | Role |
|---|---:|---|---|
| `GEOMETRY FINAL.SLDPRT` | `1971276311204` | `7323d2abfc391e3c814a94573e027f101318458c` | Final mechanism source |
| `Test_3.csv` | `1938821987892` | `2753dd225b2c95c2cc0c6635f9e3f7b1493692cc` | Selection-era response and cross-check |
| `2026Ackermann.csv` | `2357045252883` | `69d71c0977287a13385683204344e78816b48512` | Primary final-motion export |
| `Steering Length Optimization Tests.xlsx` | `1939770957296` | `2069922fc3dac8889d84a92275e35486caef3284` | Design-intent and summary reference |

## Final specification observations

The Test 3 reference column lists rack offset `2.62`, rack displacement `1`, tie-rod length `13`, steering-arm length `2.70`, turn-angle summaries `22.43` and `32.08`, steer input `102`, and joint coordinates. Those values retain their workbook definitions until the units, frame, datums, and endpoints are frozen. The workbook `Rack Offset` value must not be silently equated to the FDR's relative `0.5 inch back` statement.

## `Test_3.csv`

The export contains a signed `Measurement1` response versus `Steer_Angle`. The populated input visible in the file spans `-102 deg` through `+115 deg`; blank leading scenario cells remain in the 231-scenario container. At `+102 deg`, `Measurement1` is approximately `22.24 deg`, close to the workbook summary `22.43 deg`.

This is useful selection-era evidence, but its exact parent model, monitor definition, and relationship to the final-motion export remain open.

## `2026Ackermann.csv`

The export contains 205 points of `Dimension2` versus `Steer Input`, from `-102 deg` through `+102 deg` in `1 deg` increments. The raw angular monitor reaches `0.17 deg` at inputs `-77 deg` and `-76 deg`, then increases on both sides. That pattern is an angular-measurement branch crossing, not a physical reversal.

The provisional legacy reconstruction is:

```text
continuous monitored angle
  = opposite orientation signs on the two sides of the -77/-76 deg crossing

road-wheel angle
  = continuous monitored angle - straight-ahead reference angle
```

Taking exported input `0 deg` as a provisional straight-ahead state gives a reference angle of `20.57 deg`. That value is not frozen until the CAD input and monitor definitions are reviewed.

Recovered WUFR-25 files prove the historical reference-subtraction operation: `WUFR_25.csv` uses approximately `32.9 deg`, while `3.5INREV_WUFR25.csv` uses approximately `33.0 deg`.

The calculator quantity labeled `Steer Ratio` is actually

```text
Delta road-wheel angle / Delta steering input
```

which is local road-wheel gain. Conventional steering ratio is its reciprocal only after the exported input is confirmed to be steering-wheel angle.

Detailed equations, cubic fit coefficients, residuals, and implementation guidance are in `migration/legacy_calculators/steering_tie_rod_optimizer/steer_ratio_fit_reconstruction.md`. Machine-readable source and fit metadata are in `benchmarks/steering/wufr26_ackermann_export.toml`.

## Benchmark use

`BENCH-STEER-0001` uses `GEOMETRY FINAL.SLDPRT` as mechanism source, the FDR as selection authority, `2026Ackermann.csv` as primary final-motion response, and `Test_3.csv` as a cross-check.

Freeze still requires immutable SHA-256 hashes, the exact FDR file/version, SolidWorks configuration and study metadata, input/output identities, reviewed angle unwrapping and straight-ahead reference, physical steering limits, and approved CAD-export tolerances.

The fitted curve is not independent validation of its parent geometry. The transformed raw table remains the expected legacy response.

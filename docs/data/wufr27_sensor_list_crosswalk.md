# WUFR 27 Sensor List Crosswalk

The shared `WUFR 27 Sensor List` remains the team-facing inventory and procurement source. The repository does not import the full spreadsheet or duplicate its counts and notes.

## Current steering mappings

| Drive row | Registry sensor | Canonical quantity | Treatment |
|---|---|---|---|
| `Sensors!A21:J21`, Steering Pot, `MLS130/100/R/N Penny n Giles` | `SNS-STEER-0001` | `QTY-STEER-0004` rack displacement | Source-native model identity is mirrored for traceability; inventory and status remain in Drive. |
| No row in revision 140 | `SNS-STEER-0002` | `QTY-STEER-0002` primary-shaft angle | Remains planned. Selection and procurement must use the Drive request/inventory workflow before product metadata is assigned. |

## Optional Drive reference columns

The only repository-related columns suitable for the shared sensor list are:

- `Registry Sensor ID`;
- `Canonical Quantity ID`;
- `Measurement Metadata State`.

These are crosswalks, not a second acquisition schema. Logger channel, sample rate, calibration coefficients, polarity, zero, and session setup remain in the versioned measurement package.

# Measurement Data Tooling Change Set

**Branch:** `phase-0-steering-canonical-data-tooling`  
**Phase 0 workstream:** `P0-W06` sensor and data registry  
**Related steering task:** `P0-STR-011`

## Added

- A versioned physical-measurement package contract for session, channel, calibration, raw-sample, and settled-point files.
- A standard-library validator for exact headers, stable IDs, referential integrity, units, calibration linkage, sample ordering, and quality flags.
- Steering settled-point reductions that preserve separate increasing/decreasing centers before reporting hysteresis and repeatability.
- Blank templates for Level F collection without invented logger, sample-rate, calibration, or setup values.
- Registry calibration placeholders for the installed rack potentiometer and planned primary-shaft potentiometer.
- A source crosswalk to the WUFR 27 Sensor List revision 140.

## Authority and redundancy decisions

- The Drive sensor list remains authoritative for inventory, procurement, subsystem ownership, source-native product identity, and team planning notes.
- `SNS-*` registry records provide stable engineering identity and canonical quantity linkage, not duplicate inventory counts.
- Session `channels.csv` contains logger binding, sample rate, polarity, zero, and calibration reference only for the actual acquisition session.
- `calibrations.csv` contains immutable conversion and uncertainty evidence; coefficients are not copied into sensor or channel records.
- `raw_samples.csv` contains only time, sequence, channel ID, raw value, and quality flag.
- The planned primary-shaft rotary potentiometer remains unselected; no product, inventory, logger, rate, or calibration values are guessed.

## Open gates

- Freeze the rack-pot electrical/ADC interface and perform a bidirectional multi-point calibration.
- Select and install the primary-shaft rotary potentiometer through the Drive request/inventory workflow.
- Assign actual logger channels, sample rates, clock identities, polarities, and zero references.
- Collect repeated bidirectional rack-to-wheel and shaft-to-rack sweeps.
- Quantify calibration, fixture, repeatability, and setup uncertainty before a Level F acceptance rule is proposed.

# Physical Measurement Data Contract

**Status:** Active Phase 0 contract  
**Machine-readable schema:** `schemas/measurement_data_contract.toml`  
**Validator:** `pssd_measurements.validate_measurement_package`

## Purpose

This contract keeps inventory, sensor identity, acquisition metadata, calibration evidence, raw samples, and processed engineering points traceable without copying the same information into every file.

The first use is the WUFR-26 steering Level F test, but the package structure is intentionally generic enough for suspension, vehicle dynamics, and other physical measurements.

## Authority split

### Google Drive sensor list

`WUFR 27 Sensor List` is the human-maintained authority for:

- sensor inventory and desired counts;
- procurement and installation status;
- owning subsystem;
- source-native product name;
- test-planning notes and links.

Current source snapshot used for this contract:

- Google Drive file ID: `1APgi55-rLtcLoeSK4UWYo2qJabf8i14NYZl0O5fAguU`;
- Drive revision: `140`;
- modified: `2026-07-18T06:24:38.347Z`;
- primary tabs: `Sensors` and `Sensor Testing`;
- steering rack potentiometer row: `Sensors!A21:J21`;
- corresponding test-planning row: `Sensor Testing!A16:J16`.

Inventory counts, purchasing status, and general notes are not copied into the GitHub registry or measurement CSVs. The Drive row is referenced instead.

### Registry sensor records

A `SNS-*` record supplies the stable engineering identity needed by models and datasets:

- stable sensor ID;
- measured canonical quantity;
- installed or planned location;
- lifecycle and calibration state;
- source spreadsheet/revision/range;
- applicability and evidence role.

A sensor record does not become an inventory database. It may mirror the source-native model name only when required to identify the physical device used for a dataset.

### Channel metadata

`channels.csv` is session-specific. One row describes one logged channel and links:

- a stable `CH-*` channel ID;
- one `SNS-*` sensor;
- one `QTY-*` measurand;
- acquisition device and input name;
- raw and canonical units;
- sample rate and clock;
- one `CAL-*` calibration;
- polarity and zero reference.

It does not repeat sensor inventory, product notes, purchasing state, or calibration coefficients.

### Calibration metadata

`calibrations.csv` contains the calibration evidence required to transform raw readings into one canonical quantity. A calibration row is self-contained and immutable for the dataset:

- calibration ID;
- sensor and quantity IDs;
- method and input/output units;
- validity interval;
- coefficients;
- fit residual and uncertainty;
- source-file SHA-256 where available.

A new calibration receives a new ID. Old calibrations are not overwritten.

### Raw samples

`raw_samples.csv` is long-form and intentionally minimal:

```text
time_s,sequence,channel_id,raw_value,quality_flag
```

Sensor name, units, location, model, and calibration are obtained through the channel and calibration tables. This prevents repeated metadata from drifting between millions of sample rows.

### Processed steering points

`steering_points.csv` stores settled, calibrated engineering points for the Level F rack-to-wheel sweep. Unit-bearing names are fixed in the header and use canonical SI values:

- rack displacement in metres;
- shaft and wheel angles in radians;
- steering-wheel torque in newton-metres;
- hold windows in seconds.

Optional unavailable signals remain blank. They are not filled with zero.

## Package layout

```text
<session_id>/
  session.toml
  channels.csv
  calibrations.csv
  raw_samples.csv
  steering_points.csv       # optional for non-steering tests
  setup.md
  photos/
  calibration_sources/
  analysis/
```

The five structured files use fixed names so filenames do not need to be repeated in the session manifest.

## Session roles

Every session declares exactly one primary data role:

- `calibration`: establishes a sensor transformation;
- `identification`: estimates model parameters or compliance;
- `validation`: independent evidence used to assess a frozen model;
- `diagnostic`: troubleshooting evidence not used for model acceptance.

The same raw file must not silently serve as both calibration and validation evidence. A derived copy may reference the same source only when the role relationship is explicit.

## Steering-specific rules

1. Rack displacement uses `QTY-STEER-0004` and canonical positive rack motion along the declared rack axis.
2. Primary-shaft angle uses `QTY-STEER-0002` and remains distinct from steering-wheel and pinion angle.
3. Left and right projected headings use `QTY-STEER-0006` and `QTY-STEER-0007`.
4. A center point is retained separately for each repeat and approach direction before incremental headings are calculated.
5. Increasing and decreasing approaches are never averaged before hysteresis is reported.
6. Missing primary-shaft or steering-wheel channels remain blank in the settled-point table.
7. Whole-system free play, component backlash, and elastic compliance remain separate reductions.

## Validation behavior

`scripts/validate_measurement_package.py` checks:

- exact CSV headers and order;
- required session metadata;
- stable ID syntax;
- unique channel and calibration IDs;
- positive sample rates;
- channel-to-calibration sensor, quantity, and unit consistency;
- monotonic time and sequence fields;
- declared channel references;
- quality flags;
- settled-point numeric fields and hold-window ordering.

The validator checks structure and referential consistency. It does not certify calibration quality, fixture stiffness, uncertainty magnitude, physical correctness, or Level F acceptance.

## Drive crosswalk rule

The only fields recommended for addition to the shared Drive `Sensors` tab are reference fields such as:

- `Registry Sensor ID`;
- `Canonical Quantity ID`;
- `Measurement Metadata State`.

Detailed logger channels, calibration coefficients, sample rates, and session-specific setup do not belong in the inventory row. This keeps the Drive list useful to the full team while the immutable test package remains reproducible.

## Change control

Changing a CSV column, unit, enum, or ID meaning requires:

1. a schema-version increment;
2. validator and test updates;
3. migration instructions for existing packages;
4. a changelog entry;
5. reprocessing only when the semantic change affects calculated outputs.

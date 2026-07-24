# Vehicle operating-state provider implementation v0.1.0

**Model:** `MOD-VEH-0001`  
**Task:** `P1-STR-006I`  
**Benchmark:** `BENCH-VEH-0001`  
**PR:** #29

## Purpose

PR #29 introduces the shared state boundary that was missing between vehicle-dynamics calculations and the tire/steering stack.

`MOD-VEH-0001` is deliberately an **exchange/provider contract**, not a vehicle-dynamics solver. It stores vehicle and per-wheel operating quantities already determined by an upstream source and preserves missing fields, source authority, sign conversion, and design-use role explicitly.

The immediate steering path is:

`upstream VD source -> VehicleOperatingStateSet -> explicit front inside/outside wheel states -> TireOperatingPoint -> PR28 tire target provider -> MOD-STEER-0001`

A later QSS, telemetry reducer, reviewed load-transfer model, LLTD tool, OptimumK/native suspension model, or manual reviewed table can populate the same contract without changing the tire or steering mechanism APIs.

## Contract

`src/pssd_vehicle/operating_states.py` defines:

- `WheelPosition`: front-left, front-right, rear-left, rear-right;
- `WheelOperatingState`: optional `Fz`, inclination/camber, pressure, `Fy` demand, `Fx` demand, missing reasons, provenance;
- `VehicleOperatingState`: named acceleration/speed state, explicit turn direction, four wheel records, role, state weight, optional suspension-pose link, authority, provenance;
- `VehicleOperatingStateSet`: source path/revision, canonical body axes, lateral-acceleration convention, authority, and named states;
- TOML loading for explicit source tables.

No missing numeric value is replaced with zero. `normal_load_n=0` remains available to represent wheel lift in the generic state contract, but a tire operating point requires positive contact load. Negative source normal loads are rejected.

### State roles

The first contract distinguishes:

- `evidence_only`: source evidence that may be reported but has `state_weight=0`;
- `report_only`: valid state retained outside design scoring, also weight zero;
- `design_input`: reviewed state permitted to carry a positive downstream design weight.

This prevents a current spreadsheet result from becoming an optimization state merely because it was successfully loaded.

## Tire bridge

`src/pssd_vehicle/tire_bridge.py` contains no tire or vehicle equations. It:

1. uses explicit `turn_direction` to assign front inside/outside wheel identity;
2. reports missing fields for the PR28 tire operating-point contract (`Fz`, inclination, pressure);
3. separately reports missing `Fy` demand for the planned force-demand/slip-angle layer;
4. constructs `TireOperatingPoint` only when all required values were supplied upstream.

Right turn maps front inside/outside to FR/FL. Left turn maps FL/FR.

## First WUFR source fixture

`benchmarks/vehicle/WUFR27_SUSPENSION_CALCULATIONS_OPERATING_STATES_V0.toml` freezes selected current values from the Google Sheet **Suspension Calculations 2026**, sheet `Load Transfer`.

Source revision frozen for PR #29:

`sha256:505f567a132296fe90876b1202d9bd626d8b0f302ff4c6316d013d0306ab24fc`

The workbook states that right turns are positive lateral acceleration. The provider's canonical body convention is `+x forward, +y vehicle left, +z upward`, therefore the source signs are converted explicitly:

- source right-turn `+1.2 g` -> canonical `ay_g=-1.2`;
- source left-turn `-1.2 g` -> canonical `ay_g=+1.2`.

No downstream code guesses this conversion.

### Selected 1.2 g source states

The selected workbook section includes the workbook's simple cornering aero calculation at 40 mph and excludes ARB contribution.

| state | FL Fz [N] | FR Fz [N] | RL Fz [N] | RR Fz [N] | total [N] |
|---|---:|---:|---:|---:|---:|
| 1.2 g right | 1719.575445 | 186.2139907 | 1737.984573 | 173.2530798 | 3817.0270885 |
| 1.2 g left | 516.8481725 | 1388.941263 | 510.345799 | 1400.891854 | 3817.0270885 |

Both are frozen as `evidence_only`, not design inputs. The selected source does **not** provide wheel inclination/camber, tire pressure, `Fy` demand, `Fx` demand, or a reviewed suspension-pose link, so those fields remain unavailable.

## Source-audit rejection

The current later workbook section labeled `Load Transfer with Aero + ARB Contribution [USE THIS ONE]` contains a 1.7 g left-turn draft with:

`rear_left Fz = -285.3358453 N`

PR #29 does not clip that value to zero, swap wheel identities, or silently replace the state with another calculation. The value is recorded only in the source-audit section and the generic provider rejects negative normal loads.

This does **not** prove that the intended upstream method is invalid; it proves that this current calculated state is not admissible as an explicit tire contact-load state until the upstream model/assumptions are reviewed.

## Why PR #29 does not implement load transfer

The current project authorization matrix still lists canonical lateral/longitudinal load-transfer equations as not authorized pending separation of total, geometric, elastic, unsprung, and aero terms and parameter review. The current workbook also contains multiple sections with different assumptions.

Embedding one of those equations in steering would create exactly the redundant and weakly governed dependency the shared provider is intended to avoid.

PR #29 therefore establishes the durable interface first. A later reviewed vehicle-state generator can implement canonical/QSS physics behind this interface.

## Downstream expansion path

The contract intentionally already contains fields needed beyond PR #29:

- `lateral_force_demand_n` for the planned `Fy -> slip angle` tire target;
- `longitudinal_force_demand_n` for later combined-slip work;
- `suspension_pose_state_id` for synchronizing tire/vehicle and zero-steer upright states;
- per-state authority/role/weight for realistic operating-state families;
- source revision/provenance for telemetry, QSS, spreadsheet, or external-solver producers.

No new field requires a steering mechanism change.

## Explicitly excluded

PR #29 does not add:

- canonical load-transfer equations;
- LLTD or roll equilibrium;
- aero-force calculation;
- suspension kinematics;
- camber prediction;
- tire pressure prediction;
- tire-force equilibrium or `Fy -> alpha` inversion;
- combined-slip or transient tire modeling;
- lap/QSS simulation;
- steering effort or rack loads;
- production WUFR operating-state authority.

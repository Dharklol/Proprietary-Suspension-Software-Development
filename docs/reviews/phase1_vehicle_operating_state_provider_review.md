# Phase 1 vehicle operating-state provider review

**PR:** #29  
**Task:** P1-STR-006I  
**Model:** MOD-VEH-0001  
**Benchmark:** BENCH-VEH-0001  
**Review state:** ready for team review

## Review question

Does PR #29 establish a reusable, source-preserving vehicle operating-state boundary that can feed the tire/steering stack now and richer VD/QSS work later, without prematurely authorizing or duplicating load-transfer/vehicle-equilibrium physics?

## Architectural decision

PR #29 creates `src/pssd_vehicle/` as a shared package rather than placing vehicle-state generation inside `pssd_steering` or `pssd_tire`.

The first version is an explicit state contract only. Upstream tools provide vehicle/wheel values; `MOD-VEH-0001` validates identity, units/domain, availability, role, and provenance. It does not calculate the values.

This keeps three responsibilities separate:

- **vehicle-state source:** determines wheel loads/camber/pressure/force demand;
- **tire provider:** turns an explicit tire operating point/force demand into tire response;
- **steering:** produces and evaluates geometry response through MOD-STEER-0001.

## Current WUFR source audit

The current `Suspension Calculations 2026` workbook was selected as the first development source because it is actively used by current suspension/vehicle-dynamics work and exposes explicit left/right load matrices.

The source is frozen at:

`sha256:505f567a132296fe90876b1202d9bd626d8b0f302ff4c6316d013d0306ab24fc`

The selected 1.2 g section contains simple cornering aero at 40 mph and excludes ARB contribution. It is therefore useful source evidence but not sufficient design authority.

The workbook also explicitly uses a source lateral-acceleration convention where right turns are positive. PR #29 records the sign adapter to the project body convention (`+y` left) rather than allowing consumers to infer it.

## Frozen evidence states

| turn | canonical ay | FL [N] | FR [N] | RL [N] | RR [N] | total [N] |
|---|---:|---:|---:|---:|---:|---:|
| right | -1.2 g | 1719.575445 | 186.2139907 | 1737.984573 | 173.2530798 | 3817.0270885 |
| left | +1.2 g | 516.8481725 | 1388.941263 | 510.345799 | 1400.891854 | 3817.0270885 |

The provider maps front inside/outside as:

- right: FR / FL;
- left: FL / FR.

These states are `evidence_only` and carry `state_weight=0`.

## Missing-data boundary

The selected source states do not provide:

- wheel inclination/camber;
- tire pressure;
- requested/achieved tire lateral force;
- tire longitudinal force;
- reviewed zero-steer suspension-pose identity.

PR #29 retains those values as unavailable and records reasons. The PR28 `TireOperatingPoint` bridge fails until `Fz`, inclination, and pressure are all explicit. Future `Fy -> alpha` work can additionally require `lateral_force_demand_n` without changing this state schema.

## Tire-model domain finding

The PR #28 tabulated TTC lateral-summary grid currently ends at `Fz = 1112 N`. The frozen PR #29 edge-case outside-front loads are `1719.575445 N` for the right-turn state and `1388.941263 N` for the left-turn state.

Those edge-case loads therefore cannot be sent through the PR #28 tabulated grid by extrapolation, and PR #28's no-extrapolation rule remains intact. This is another reason the current load matrices stay evidence-only rather than being promoted directly to steering design targets.

The next tire/vehicle step should identify representative weighted operating states and/or use a reviewed richer fitted-TIR/raw-TTC response provider where the required load envelope exceeds the compact PR #28 grid. This matches the current Vehicle Dynamics goal of identifying the common load band and weighting its significance rather than optimizing only an arbitrary edge case.

## Important source discrepancy

The current later workbook section labeled `Load Transfer with Aero + ARB Contribution [USE THIS ONE]` contains a 1.7 g left-turn calculation with rear-left normal load:

`-285.3358453 N`

That state is retained in the fixture only as rejected source-audit evidence. Negative normal loads are not clipped to zero or silently repaired.

This is intentionally a source-quality gate, not a claim that the underlying intended method is permanently wrong.

## BENCH-VEH-0001

The benchmark verifies:

- exact source path/revision and sign conversion;
- exact four-wheel values and totals for both 1.2 g states;
- front inside/outside identity;
- evidence-only/zero-weight behavior;
- missing tire-input preservation;
- successful conversion of a fully explicit synthetic wheel state to `TireOperatingPoint`;
- rejection of negative normal load;
- no new vehicle/load-transfer equations.

Frozen result:

`benchmarks/vehicle/vehicle_operating_state_result_v0.1.0.toml`

## Governance boundary

PR #29 does not promote `EQ-LOAD-0001` through `0006`, LLTD, simple aero, or other current workbook equations to active physics. The existing authorization matrix still governs those models independently.

`MOD-VEH-0001` is therefore classified as a non-physics provider/exchange contract under `AUTH-VEH-0001`. A later reviewed QSS or canonical load-state generator should output this contract rather than replace it.

PR #28 / `P1-STR-006H` is closed at merge commit `5ec28ed1932994c75ff616e4d208912259895f7e`. PR #29 is tracked as `P1-STR-006I`.

## Review outcome required

Approval means:

- `MOD-VEH-0001` may be used as the shared explicit state boundary;
- current frozen workbook states may be used as development evidence and software-integration fixtures;
- downstream code may require explicit fields and reject incomplete/invalid states.

Approval does **not** mean:

- the selected 1.2 g workbook states are production wheel-load truth;
- the workbook load-transfer method is canonically authorized;
- missing camber/pressure/Fy may be inferred;
- the rejected 1.7 g state may be repaired by clipping;
- the PR #28 compact tire grid may be extrapolated to the PR #29 edge-case outside loads;
- a tire-optimal steering target has yet been established.

## CI freeze

The implementation/governance head `f6f528d4d65648c35a1e0d367a2ad1f2c623d3e5` passed GitHub Actions run **345** (`30062513258`).

- registry validation: success;
- **175 unit tests**: success;
- WUFR-26 Level E reports: success;
- steering nominal optimizer reports: success;
- steering constraint/sensitivity reports: success;
- steering suspension-pose reports: success;
- steering operating-state target reports: success;
- steering external-pose adapter reports: success;
- steering state-metric objective reports: success;
- steering tire-informed target reports: success;
- new vehicle operating-state reports: success.

Vehicle report artifact:

- artifact ID: `8585084467`;
- digest: `sha256:91b2d27d1371d6b4f3666b9311f427f035626919adc8c1a590a84a8e5cdf12ab`.

Any later review-document-only head must also remain green before merge; this recorded run is the frozen implementation/governance validation reference.

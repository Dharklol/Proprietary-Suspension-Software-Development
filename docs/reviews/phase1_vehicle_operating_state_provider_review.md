# Phase 1 vehicle operating-state provider review

**PR:** #29  
**Task:** P1-STR-006I  
**Model:** MOD-VEH-0001  
**Benchmark:** BENCH-VEH-0001  
**Review state:** implementation in progress; final CI freeze pending

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

## Governance boundary

PR #29 does not promote `EQ-LOAD-0001` through `0006`, LLTD, simple aero, or other current workbook equations to active physics. The existing authorization matrix still governs those models independently.

`MOD-VEH-0001` is therefore classified as a non-physics provider/exchange contract. A later reviewed QSS or canonical load-state generator should output this contract rather than replace it.

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
- a tire-optimal steering target has yet been established.

## Final CI freeze

Pending final PR-head CI, final test count, and `vehicle-operating-state-reports` artifact.

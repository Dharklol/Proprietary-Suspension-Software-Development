# Vehicle operating-state provider changelog

## v0.1.0 — PR #29

- Added `MOD-VEH-0001`, a shared explicit vehicle/per-wheel operating-state exchange contract.
- Added `AUTH-VEH-0001` and `BENCH-VEH-0001`.
- Added `pssd_vehicle` with source-preserving state loading, role/weight controls, negative-load rejection, front inside/outside assignment, tire-input readiness, and explicit `TireOperatingPoint` conversion.
- Froze current `Suspension Calculations 2026` 1.2 g left/right development wheel-load evidence at source SHA256 `505f567a132296fe90876b1202d9bd626d8b0f302ff4c6316d013d0306ab24fc`.
- Recorded the source right-turn-positive lateral-acceleration convention and explicit conversion to the project `+y`-left body convention.
- Kept source states `evidence_only` with zero design weight because camber, pressure, Fy/Fx demand, and reviewed suspension-pose linkage are unavailable.
- Recorded the current 1.7 g left-turn draft with rear-left `Fz=-285.3358453 N` as rejected source-audit evidence; no clipping or silent repair is allowed.
- Added CI generation of `vehicle-operating-state-reports`.
- Closed `P1-STR-006H` at PR #28 merge commit `5ec28ed1932994c75ff616e4d208912259895f7e` and opened `P1-STR-006I` for this provider bridge.

This release does not authorize or implement load-transfer, aero, LLTD, suspension-motion, tire-force-equilibrium, or QSS equations.

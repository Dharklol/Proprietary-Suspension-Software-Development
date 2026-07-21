# Phase 0 Steering Source Hash Review

**Task:** `P0-STR-002`  
**Status:** Review ready; not complete  
**Manifest:** `data_catalog/steering_source_hash_manifest.toml`

## Review conclusion

The legacy steering selection chain and the best available WUFR-26 CAD/motion-study package are now identified by stable project artifact IDs, provider file IDs, version IDs where available, byte sizes, provider SHA-1 values where available, and evidence roles.

This review does **not** declare the task complete. Provider hashes are discovery/change-detection evidence only. Project SHA-256 must be computed over immutable downloaded bytes, or a reviewer must formally accept the exact artifact as unavailable.

## Identified source chain

1. `SRC-STEER-0001` — `GEOMETRY FINAL.SLDPRT`, final nominal geometry and SolidWorks benchmark parent.
2. `SRC-STEER-0002` — `2026Ackermann.csv`, final second-motion-study response.
3. `SRC-STEER-0003` — `Test_3.csv`, selection-era Test 3 response cross-check.
4. `SRC-STEER-0004` — `Steering Length Optimization Tests.xlsx`, candidate-study comparison/reference workbook.
5. `SRC-STEER-0005` — `WUFR-26 FINAL 8.21.2025.xlsx`, final suspension geometry and steering-axis source.
6. `SRC-STEER-0006` — `Steering_range_optimization.m`, historical WUFR-25 effort/range trade study.
7. `SRC-STEER-0007` — `WUFR 27 Sensor List`, sensor inventory/planning source only.

## Authority and redundancy rules

- Filenames are not identities; provider file/version IDs plus hashes identify exact bytes.
- Box SHA-1 values do not replace project SHA-256.
- Raw files are hashed before parsing, conversion, spreadsheet resave, or CAD export.
- Derived polynomial coefficients and frozen benchmark JSON remain derivatives and must retain parent artifact IDs/hashes.
- The sensor list remains the authority for inventory/procurement metadata, not steering geometry or calibration coefficients.
- The FDR selection record remains a separate missing source artifact even though its Test 3 interpretation is already accepted.

## Remaining completion gates

1. Acquire immutable raw bytes for the identified source package.
2. Run `scripts/hash_source_artifacts.py` and record size plus SHA-256.
3. Add missing Box version IDs where the provider record was not captured.
4. Recover and catalog the exact FDR document/table used to select Test 3.
5. Record SolidWorks version, active configuration, driver/monitor definitions, dependencies, warnings, and suppression state.
6. Formally review any artifact that cannot be recovered and record why its absence is acceptable for the bounded prototype.

## Reopening rule

Reopen the identity mapping if a provider file/version ID changes, a SHA-256 mismatch occurs, the FDR selects a different artifact, or the final CAD/export lineage is contradicted by native SolidWorks evidence.

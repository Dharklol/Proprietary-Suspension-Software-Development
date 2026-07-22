# Phase 0 Steering Source Hash Closeout

**Task:** `P0-STR-002`  
**Status:** Complete  
**Manifest:** `data_catalog/steering_source_hash_manifest.toml`  
**Freeze date:** 2026-07-22

## Review conclusion

The legacy steering-selection chain and the best available WUFR-26 CAD/Design Study package now have stable `SRC-STEER-*` identities, exact provider identities where applicable, project SHA-256 values over the captured bytes, derivative lineage, and explicit authority boundaries.

The task is complete for the bounded rigid-steering prototype. Completion does not make every historical artifact authoritative and does not promote any installed-state or Level F claim.

## Authoritative CAD configuration

`Default` is the steering-geometry authority for `ST-A0603-AA STEERING GEOMETRY.SLDASM`.

`FSA` is retained as a full-car-assembly optimized configuration. It is not used as the nominal steering-geometry authority and does not replace the `Default` metadata report or raw source hash.

The frozen SOLIDWORKS reports record application revision `34.3.2`. The native source and metadata reports keep their pre-existing dirty-state observations; the metadata extractor did not save, rebuild, switch configurations, or resolve components.

## Final source chain

The blocking source chain is:

1. `SRC-STEER-0008` - Drive FDR revision `21560` exported to PDF. It contains the final geometry table, states that `GEOMETRY FINAL` is the best reference, and records that the simulation geometry was based on Test 3.
2. `SRC-STEER-0004` - candidate-study comparison workbook.
3. `SRC-STEER-0003` - selected Test 3 response export.
4. `SRC-STEER-0011` - provider-identified historical native Test 3 part, with the bounded formal disposition below.
5. `SRC-STEER-0001` - final nominal `GEOMETRY FINAL.SLDPRT` authority.
6. `SRC-STEER-0009` - parent steering-geometry assembly using the frozen `Default` configuration.
7. `SRC-STEER-0010` and `SRC-STEER-0002` - final Ackermann Design Study part and its response export.
8. `SRC-STEER-0005` - final OptimumK suspension/steering-axis workbook.
9. `SRC-STEER-0006` - historical range/effort study retained as benchmark history only.
10. `SRC-STEER-0007` - revision-pinned sensor-list export retained as inventory/planning authority only.

All blocking captured files have project SHA-256 values. The manifest corrects the missing Box version IDs for `Test_3.csv`, `Steering Length Optimization Tests.xlsx`, and `Steering_range_optimization.m`, and corrects the final OptimumK workbook size from zero to `18692` bytes.

## Design Study lineage

### Final Ackermann study

`STEERING ACKERMAN CALC.SLDPRT` is directly linked to `2026Ackermann.csv`:

- both identify `Design Study 1`;
- the native metadata contains `steering_input = -41` and the CSV initial `Steer Input` is `-41`;
- the native metadata contains the `Dimension2` sensor and the CSV monitor is `Dimension2`;
- the CSV contains 205 populated scenarios from `-102 deg` through `+102 deg` at `1 deg` increments.

### Historical Test 3 study

`STEERING GEOMETRY.SLDPRT` is source-associated with `Test_3.csv`:

- the native metadata contains the historical steering geometry variables and `Measurement1`/`Measurement2` sensor records;
- the CSV identifies `Design Study 1`, drives `Steer_Angle`, and monitors `Measurement1`;
- the comparison workbook and FDR separately identify Test 3 as the chosen design basis.

The CSV declares 231 scenarios, but populated results begin at Scenario 14 (`-102 deg`) and continue through Scenario 231 (`+115 deg`). The absent `-115 deg` through `-103 deg` results are not silently reconstructed.

The general MotionManager API exposed an empty `Motion Study 1` tab. These engineering sweeps are SOLIDWORKS **Design Studies**, so they are not relabeled as Motion studies merely because that API was available.

## Formal disposition for the historical native Test 3 part

The raw bytes of `STEERING GEOMETRY.SLDPRT` were not included in the supplied freeze package. The exact Box file/version identity, provider SHA-1, Test 3 CSV, metadata report, comparison workbook, and FDR selection are available and frozen.

The missing project SHA-256 for that historical native part is formally accepted for bounded prototype scope because:

- it is not the final nominal geometry authority;
- the selected response export itself is SHA-256 verified;
- the final geometry and final Ackermann native sources are SHA-256 verified;
- no current model output depends on reopening the missing `-115 deg` through `-103 deg` Test 3 range.

This disposition must be reopened if future work requires reproducing the historical Design Study inside SOLIDWORKS rather than using its frozen output and final-geometry successors.

## Derived evidence and non-substitution rules

- `Pack And Go.zip` is a reproducibility derivative. Its packaged assembly and `GEOMETRY FINAL` copies differ bytewise from the provider-authoritative raw files, so they cannot replace `SRC-STEER-0009` or `SRC-STEER-0001`.
- `GEOMETRY FINAL.STEP` is a wireframe neutral export containing points, lines, and trimmed curves. It is geometry-access evidence, not native feature/configuration/study authority.
- `find_reference.pdf` and the four metadata JSON reports are evidence supplements with explicit parent source IDs.
- Google-native FDR and sensor-list files are frozen through revision-pinned PDF/XLSX export snapshots. The Drive file ID and revision remain the native-source identity; the SHA-256 applies to the named export bytes.
- The sensor list remains authoritative for inventory, ownership, procurement, and planning metadata. `SNS-*`, `CAL-*`, and session channel files reference stable identities without copying that inventory metadata into raw data rows.

## Historical compliance evidence

`Compliance_calculator.m` and its `.asv` predecessor are now source-identified and SHA-256 verified.

The active `.m` file explicitly includes placeholder comments and assumes `2.0 deg` bevel-box backlash plus `0.2 deg` rack backlash. It is historical exploratory calculated evidence only. Those assumed values must not be added to the measured approximately `4 deg` whole-system free play, used as current component attribution, or treated as Level F acceptance evidence. The `.asv` file is provenance only.

`Steering_range_optimization.m` remains a historical ratio/effort trade study and does not authorize a steering optimizer or active target.

## Completion and reopening rules

`P0-STR-002` is complete because every blocking source is either SHA-256 verified or covered by an explicit bounded disposition. Remaining installed-state work belongs to `P0-STR-006` and `P0-STR-011`, not source recovery.

Reopen this closeout when:

- a provider file or version ID changes;
- a project SHA-256 mismatch is found;
- the FDR selection is contradicted;
- native CAD evidence changes the frozen `Default`-configuration lineage;
- future scope requires exact historical Test 3 Design Study regeneration.

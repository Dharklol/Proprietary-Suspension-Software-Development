# WUFR-26 Steering Level E Preparation

**Status:** Comparison infrastructure ready; numerical comparison waits for a reviewed SolidWorks export  
**Model:** `MOD-STEER-0001`  
**Authorization:** `AUTH-STEER-0001`

## Work sequence decision

Continue the evaluator and comparison infrastructure first, then stop at the SolidWorks export gate. This allows the source parser, signal schema, datum handling, interpolation, residual metrics, dense nominal sweep and failure behavior to be reviewed before asking for CAD measurements.

## Added infrastructure

`src/pssd_steering/comparison.py` provides:

- traceable scalar signal-series records;
- exact-label parsing of the transposed motion-study CSV layout;
- periodic-angle unwrapping using a declared period;
- explicit sign and center-datum transformations;
- domain-limited linear interpolation without extrapolation;
- comparison only when quantity identities and units match;
- bias, RMSE, maximum error and point residuals;
- explicit unavailable states for signal, unit or domain conflicts.

`scripts/run_wufr26_level_e_prep.py` generates 205 nominal rack states across the provisional `-12.7 mm` to `+12.7 mm` range and reports unresolved Level E metadata. Matching the source point count is only a convenient sampling choice; it does not identify the source input as rack displacement.

## Current comparison block

The evaluator returns upright rotation about the inclined steering axis versus rack displacement. The recovered export contains `Steer Input` and `Dimension2`. Their physical definitions are not yet reviewed, so the following mappings remain prohibited assumptions:

- `Steer Input` as rack displacement, pinion angle or steering-wheel angle;
- `Dimension2` as upright rotation or road-wheel heading.

A numerical residual before those definitions are resolved would be physically undefined even when the curves look similar.

## SolidWorks export gate

The comparison requires one reviewed packet containing:

1. source file ID, version and hash;
2. active assembly and subassembly configuration names;
3. motion-study name, driver, settings and suppression state;
4. exact definition, sign and unit of `Steer Input`;
5. exact definition, sign, unit and construction of `Dimension2`;
6. rack-center or zero-input construction;
7. evaluated range and mechanical/operational stop state;
8. pinion or steering-input angle versus signed rack displacement;
9. left and right wheel-forward directions plus per-wheel static toe;
10. independently exported front-right steering hardpoints.

## Comparison sequence after export

1. Verify source identity and active configuration.
2. Map both signals to canonical quantities.
3. Preserve the raw table unchanged.
4. Apply only the reviewed unwrap, sign and center transformation.
5. Generate the same evaluator quantity over the same physical domain.
6. Interpolate only inside the overlapping domain.
7. Report residuals, mean error, RMSE and maximum absolute error.
8. Review residual shape before freezing a Level E tolerance.
9. Keep physical Level F validation separate.

The nominal dense sweep remains design-source mechanism evidence, not an installed/as-built claim.

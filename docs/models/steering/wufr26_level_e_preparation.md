# WUFR-26 Steering Level E Preparation

**Status:** Input axis and nominal domain resolved; `Dimension2` is identified as a folded internal ray angle, but its second selected ray is not yet frozen  
**Model:** `MOD-STEER-0001`  
**Authorization:** `AUTH-STEER-0001`

## Work sequence decision

The evaluator and comparison infrastructure were completed before requesting CAD measurements. Team screenshots, the recovered `2026Ackermann.csv`, the steering-length test workbook, the existing coordinate adapter, and follow-up construction evidence now resolve most of the SolidWorks gate without reopening the native model.

## Added infrastructure

`src/pssd_steering/comparison.py` provides traceable signal records, periodic normalization, domain-limited interpolation, residual metrics, and explicit unavailable states.

`src/pssd_steering/solidworks.py` adds:

- parsing of the native SolidWorks Design Study scenario-column CSV layout;
- preservation of scenario order and exclusion of the separate Initial Value column;
- explicit positive-slope linear input mapping with named quantities and units;
- rejection of undeclared units, count mismatches, and silent evidence reordering.

## Recovered SolidWorks state

The design-source steering assembly is `FSA STEERING`, with `GEOMETRY FINAL.SLDPRT` as the steering geometry component. The component contains the rack, columns, steering-wheel outline, and tie rods. The relevant study is a SolidWorks **Design Study** named `Design Study 1`, not a dynamic Motion Study.

Team evidence records:

- SolidWorks 2025 SP3.2 Academic Use Only;
- the reference chassis model suppressed;
- no reported errors or warnings;
- `Steer Input` swept from `-102 deg` through `+102 deg`;
- `Dimension2` stored as a `Monitor Only` angular result;
- rack equation `Rack Length = 8.7 + Steer Input * rack ratio`;
- `rack ratio = 3.5 / 360` inches per input degree;
- a reported 1:1 steering-wheel-to-pinion relation for the design assembly.

The reviewed coordinate adapter maps increasing native rack length to canonical `+y` rack translation. Therefore:

```text
rack_displacement_m = Steer_Input_deg * 3.5 in/rev * 0.0254 m/in / 360 deg/rev
                    = Steer_Input_deg * 0.00024694444444444446 m/deg
```

The exported `-102 deg` to `+102 deg` range maps to approximately `-25.1883 mm` to `+25.1883 mm`.

## Rack-travel correction

The earlier interpretation of `1.00 in total travel` was wrong. The nominal design study permits approximately **1.00 in to either side of center**, or **2.00 in total**. The configuration domain is now `-25.4 mm` to `+25.4 mm`; the historical CSV samples the slightly smaller range produced by its `+/-102 deg` limits.

This is design-study authority only. Installed physical stops, backlash, compliance, and operational margin still require CAD inspection or measurement.

## Optimizer versus response study

The supplied `STEERING GEOMETRY 2` optimizer screenshots show steering-arm length and historical tie-rod configurations being assessed against right- and left-turn goals near `25 deg` and `33 deg`. One visible state uses a `2.75 in` steering arm and `13.5 in` tie rod. The final/Test 3 response evidence separately supports approximately `13.0 in` tie-rod joint-center length.

A team Slack exchange gives the intended turn-angle goal construction: form an axis from the intersection of the wheel-center plane with the ground plane and measure that axis against the SolidWorks x-axis. This is strong evidence for the **optimizer's right/left turn-angle goals**.

It does not automatically identify the different monitor named `Dimension2` in `STEERING ACKERMAN CALC`. These two studies must remain separate evidence chains.

## Revised `Dimension2` interpretation

The follow-up screenshot shows two magenta construction rays sharing the hub or steering-pivot point. Green lines include the imported true tie rod and additional tie-rod-optimization construction lines. At least one magenta ray is connected to the tie-rod/steering-arm construction.

The raw curve itself confirms that `Dimension2` is not a continuously signed wheel-heading result:

- `10.24 deg` at `-102 deg` input;
- a double minimum of `0.17 deg` at `-77 deg` and `-76 deg`;
- `20.57 deg` at zero input;
- `41.84 deg` at `+102 deg` input.

That V-shaped response is characteristic of an unsigned included angle passing through alignment. The raw `20.57 deg` is therefore an internal angular datum, not static toe or absolute wheel heading.

The current classification is:

- output type: unsigned or branch-folded included angle between two hub-centered construction rays;
- probable role: steering-arm/tie-rod or steering-reference construction;
- exact second selected entity: unresolved;
- selected-entity order and sign convention: unresolved;
- direct equality to upright rotation or road-wheel heading: prohibited.

## Diagnostic branch reconstruction

For mechanism diagnosis only, the curve can be made continuous by assigning the negative branch through `-77 deg`, the positive branch from `-76 deg`, and subtracting the zero-input value:

```text
phi_signed = -Dimension2  for Steer Input <= -77 deg
phi_signed = +Dimension2  for Steer Input >= -76 deg
q_diagnostic = phi_signed - 20.57 deg
```

This produces `-30.81 deg` at `-102 deg` input and `+21.27 deg` at `+102 deg` input.

Compared over all 205 scenarios with the nominal rigid evaluator's `-left upright rotation`, the diagnostic gives:

- mean residual: `-0.1444028734 deg`;
- RMSE: `0.9197095305 deg`;
- maximum absolute residual: `2.4685599616 deg` at `-102 deg` input.

The close tracking supports linkage continuity and recovered input scaling. The systematic gain-shaped residual shows that the included-angle monitor is not the same coordinate as the evaluator's upright rotation. These metrics are not Level E validation and have no acceptance tolerance.

The full derivation is recorded in `docs/models/steering/wufr26_dimension2_ray_diagnostic.md`.

## Numerical consistency from the optimizer goals

At the exact source endpoint rack displacement of `25.1883 mm`, the nominal rigid model predicts, in magnitude, approximately:

- `33.27856 deg` on the inner/more-steered nominal side;
- `22.45550 deg` on the outer/less-steered nominal side.

The visible optimizer result is approximately `32.81 deg` and `22.22 deg`. This agreement strongly supports the recovered rack scaling and nominal geometry. It is more relevant to wheel-turn-angle consistency than the separate folded `Dimension2` monitor.

## Remaining critical blocker

A canonical residual requires one of two closures:

1. identify the exact two SolidWorks entities selected by `Dimension2`, including their order, side and branch behavior; or
2. export the direct wheel-plane/ground-intersection versus x-axis turn-angle result used by the optimizer goals.

The team-directed video location is `WUFR-27 / Suspension / PDR-FDR / Steering / Design Study Tutorials`, second tutorial, approximately `1:15` through `2:00`. A timestamped screenshot with the `Dimension2` definition open or the selected entity names would freeze the remaining monitor identity. The connected Drive video was not available for direct inspection during this update.

## Other evidence reviewed

- `Steering Length Optimization Tests` confirms inch-based geometry, angular steering inputs, Test 3's 13-in tie rod, and the historical configuration sequence.
- `2025 Linkage Length Calculations.xlsx` is retained as historical linkage-manufacturing evidence; its tie-rod row is incomplete and does not replace the WUFR-26 nominal joint-center length.
- The `WUFR26 OptK` folder contains many optimization and population exports useful for suspension provenance, but they do not define the SolidWorks `Dimension2` monitor.
- The available Simulink models are supplementary vehicle-model evidence and do not presently establish the CAD monitor construction.

## Comparison sequence after monitor identity

1. Freeze the selected output entities or use the direct optimizer turn-angle output.
2. Preserve the native 205-scenario CSV unchanged.
3. Map `Steer Input` to signed rack displacement using the reviewed linear relation.
4. Apply only the reviewed branch, sign and center transformation.
5. Generate the identical evaluator output over the same rack domain.
6. Interpolate only within overlap and report point residuals, mean error, RMSE and maximum error.
7. Review residual shape before setting a Level E tolerance.
8. Keep physical Level F validation separate.

The nominal geometry remains design-source mechanism evidence, not an installed/as-built claim.

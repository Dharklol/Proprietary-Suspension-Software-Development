# WUFR-26 Steering Level E Preparation

**Status:** Input axis and nominal domain resolved; numerical output comparison waits for the exact `Dimension2` reference construction  
**Model:** `MOD-STEER-0001`  
**Authorization:** `AUTH-STEER-0001`

## Work sequence decision

The evaluator and comparison infrastructure were completed before requesting CAD measurements. Team screenshots, the recovered `2026Ackermann.csv`, the steering-length test workbook, and the existing coordinate adapter now resolve most of the SolidWorks gate without reopening the native model.

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

The supplied steering-geometry optimizer screenshots show steering-arm length and historical tie-rod configurations being assessed against right- and left-turn goals near `25 deg` and `33 deg`. One visible state uses a `2.75 in` steering arm and `13.5 in` tie rod. The final/Test 3 response evidence separately supports approximately `13.0 in` tie-rod joint-center length.

These optimizer states provide design-selection context. They are not interchangeable with the 205-point `Steer Input` versus `Dimension2` response export.

## Numerical consistency before monitor mapping

At the exact source endpoint rack displacement of `25.1883 mm`, the nominal rigid model predicts, in magnitude, approximately:

- `33.27856 deg` on the inner/more-steered nominal side;
- `22.45550 deg` on the outer/less-steered nominal side.

The visible optimizer result is approximately `32.81 deg` and `22.22 deg`. This close agreement strongly supports the recovered rack scaling and nominal geometry, but it is not yet a Level E residual because the model output is upright rotation and `Dimension2` has not been proven to be that same quantity.

## Remaining critical blocker

`Dimension2` is known only as the angle between two pink construction rays in the steering calculator. Direct comparison remains blocked until the following are identified:

1. the exact two selected sketch entities, axes, lines, or rays;
2. which front corner or side the monitor represents;
3. the order/orientation of the two references and resulting sign convention;
4. whether the displayed value is oriented, unsigned, supplementary, or otherwise branch-limited;
5. how the cusp near the negative-input portion of the raw export should be reconstructed from the actual SolidWorks measurement definition.

A screenshot with `Dimension2` edited and both selected references highlighted, or the exact feature/sketch entity names, is sufficient. No full hardpoint export is required for this specific step.

## Other evidence reviewed

- `Steering Length Optimization Tests` confirms inch-based geometry, angular steering inputs, Test 3's 13-in tie rod, and the historical configuration sequence.
- `2025 Linkage Length Calculations.xlsx` is retained as historical linkage-manufacturing evidence; its tie-rod row is incomplete and does not replace the WUFR-26 nominal joint-center length.
- The `WUFR26 OptK` folder contains many optimization and population exports useful for suspension provenance, but they do not define the SolidWorks `Dimension2` monitor.
- The available Simulink models are supplementary vehicle-model evidence and do not presently establish the CAD monitor construction.

## Comparison sequence after monitor identity

1. Freeze the `Dimension2` reference and sign definition.
2. Parse the native 205-scenario CSV without altering the raw table.
3. Map `Steer Input` to signed rack displacement using the reviewed linear relation.
4. Apply only the reviewed angular branch and center transformation.
5. Generate the identical evaluator output over the same rack domain.
6. Interpolate only within overlap and report point residuals, mean error, RMSE, and maximum error.
7. Review residual shape before setting a Level E tolerance.
8. Keep physical Level F validation separate.

The nominal geometry remains design-source mechanism evidence, not an installed/as-built claim.

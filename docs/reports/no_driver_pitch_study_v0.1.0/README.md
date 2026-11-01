# Provisional no-driver/no-fuel inertia-only sensitivity

Reproduce: `PYTHONPATH=src python scripts/run_no_driver_pitch_study.py`.
All three cases pass the predeclared refinement and energy gates.
The archived source rows reproduce the previous CAD inventory and inertia audit.

| Retained mixed-group fraction | Rebuilt body mass, kg | Rebuilt Jy, kg*m² | Study peak pitch acceleration, rad/s² |
|---|---:|---:|---:|
| 0 | 164.396 | 67.771 | 0.52485 |
| 0.5 | 167.945 | 69.932 | 0.51849 |
| 1 | 171.494 | 72.089 | 0.51208 |

The allocation columns describe separate bookkeeping reconstructions. The dynamic
runs deliberately hold mass at the middle case (167.945 kg), geometry and all
other parameters fixed, changing only Jy. Peak pitch acceleration spans about
2.46% of the middle result; peak heave acceleration spans 0.18%. These percentages
are specific to the illustrative 1 mm front/rear bump and the explicitly selected
axle rates, damping and delay. They are not predicted car behavior or global
uncertainty bounds. Fine energy residuals remain below 9.1e-13 J.

The owner-approved 7.186 kg electrical point remains at the reconstructed dry
whole-car CG, with zero intrinsic inertia. Each body CG is recomputed after
outboard removal. Spatially distributed electrical equipment would have nonzero
intrinsic inertia even if its CG coincides with the car CG.

Source: WUFR-26 COM read-only, 2026-11-01, CAD mass/CG/labelled centroidal Lyy.
The snapshot retains source row identities and never consumes the known-invalid
origin tensor columns or mixes production mass into the CAD reconstruction.
Fuel row DT_3!59 (12 lb) is removed; no driver is added. Electrical completes the
449.149 lb dry CAD inventory, which is not reconciled to the 477 lb scale state.
All centroidal tensors are assumed to use the common CAD lateral axis; this is
not yet verified against the export macro.

BOM/assembly-supported partition: WT, brake discs and calipers are outboard;
front/rear wishbone/rod assemblies, tie rods and halfshafts form a separate mixed
bucket. Their 0/50/100% retention is a sensitivity device, not an exact kinetic
energy reduction. Inboard shock/rocker/ARB motion and flexible brake lines remain
approximated by body carriage. Study guards are not installed travel authority.

Stopping point for native dynamic promotion: source-frame verification, inventory
reconciliation and a proper moving-link effective mass/inertia reduction. No
telemetry decoding is needed to reproduce this work. The prior 306 kg driver/no-
fuel static equilibrium is not reused for this no-driver study. Drive is unchanged.

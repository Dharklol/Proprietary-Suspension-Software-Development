# WUFR-26 Steering Design Study Evidence

**Status:** Reviewed design-source evidence; not installed/as-built validation

## SolidWorks study identity

Team screenshots and the recovered export identify:

- full steering geometry assembly: `FSA STEERING`;
- steering geometry component: `GEOMETRY FINAL.SLDPRT`;
- study type and name: SolidWorks `Design Study 1`;
- observed application: SolidWorks 2025 SP3.2 Academic Use Only;
- suppression state: reference chassis suppressed; no other reported suppression;
- warnings: none reported.

`GEOMETRY FINAL.SLDPRT` contains the steering rack, steering columns, steering-wheel outline, and tie rods used by the design-source calculator.

## Response-study input

The `STEERING ACKERMAN CALC` equation table shows:

```text
rack ratio = 3.5 / 360
Rack Length = 8.7 + steering input * rack ratio
```

The Design Study export sweeps `Steer Input` from `-102 deg` through `+102 deg`. The team reports a 1:1 steering-wheel-to-pinion relation and a linear rack. The reviewed input mapping is therefore:

```text
rack displacement = Steer Input * 3.5 in/rev / 360 deg/rev
```

Positive input increases the native `Rack Length` dimension. Through the existing WUFR-26 coordinate adapter, that is canonical `+y` rack translation.

The source sweep maps to approximately `+/-0.9916667 in`, or `+/-25.1883 mm`. The nominal design-study travel is approximately `+/-1.00 in` from center, or `2.00 in` total. This does not establish installed hardware-stop positions.

## Response-study output

`Dimension2` is exported as `Monitor Only` in degrees. Team evidence identifies it as an angle between two pink construction rays in the steering calculator. The exact selected entities, side, orientation, sign, and angular branch construction remain unresolved.

The `20.57 deg` value at zero input remains a raw monitor observation, not a toe, wheel-heading, or upright-rotation datum.

## Steering geometry optimizer context

A separate `STEERING GEOMETRY 2` Design Study evaluates steering-arm and historical tie-rod configurations against left/right turn-angle goals. Visible evidence includes:

- steering-arm range approximately `2.50 in` to `2.75 in`;
- target right-turn angle approximately `25 deg`;
- target left-turn angle approximately `33 deg`;
- one visible state with `2.75 in` steering arm and `13.5 in` tie rod;
- a visible result near `22.22 deg` and `32.81 deg`.

The optimizer is design-selection evidence. It is not the same signal source as the 205-point `Steer Input` versus `Dimension2` response export.

## Supporting Box evidence

- `Steering Length Optimization Tests.xlsx`: Box file `1939770957296`, version `2140326128861`, SHA1 `2069922fc3dac8889d84a92275e35486caef3284`.
- `2025 Linkage Length Calculations.xlsx`: Box file `1673070745766`, version `2435754129317`, SHA1 `c1ea167b1a065c2433a27b4aaf630674e00b4354`.
- `SU-00001-AA 2026 SUSPENSION GEOMETRY.SLDPRT`: Box file `1943897977651`, version `2546941960247`, SHA1 `2cfb771f296961be0857161f7b57a6c178180d7a`.
- `WUFR-26 FINAL 8.21.2025.xlsx`: Box file `2014803790843`, version `2224178574043`, SHA1 `15eadfb93369192038888da92ebaa6674db56cfa`.
- `2026Ackermann.csv`: Box file `2357045252883`, version `2611346929683`, SHA1 `69d71c0977287a13385683204344e78816b48512`.

The 2025 linkage workbook is historical manufacturing evidence. Its tie-rod row is incomplete and is not used to replace the WUFR-26 nominal joint-center length.

The WUFR26 OptK optimization exports and available Simulink models remain supplementary sources. They do not define the SolidWorks `Dimension2` monitor references.

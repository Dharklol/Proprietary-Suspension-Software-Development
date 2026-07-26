# Suspension spring-force source audit

## Purpose

This audit bounds the evidence proposed for `AUTH-SUSP-0004` / `MOD-SUSP-0004`. The program adds only a conservative coil-spring force/energy/generalized-force provider after the reviewed rigid suspension-actuation implementation. It does **not** authorize damping, anti-roll-bar force, vehicle equilibrium, installed limits, or structural loads.

## 1. Upstream reviewed mechanics

`MOD-SUSP-0003` provides ideal coilover eye-to-eye length/displacement and the signed local actuation derivative

```text
delta_L_d = L_d - L_d0               positive extension
rho_dw = d(delta_L_d)/d(delta_z_wc_body)
```

The historical OptimumK `Motion Ratio Heave` channel is comparison-only evidence and is not interchangeable with `rho_dw`.

`AUTH-VEH-0003` / `MOD-VEH-0003` separately establish the project generalized-force architecture through virtual work. The spring provider therefore does not introduce another motion-ratio convention or a hidden wheel-rate force path.

## 2. Reviewer-declared WUFR-27 spring package

The reviewer/user supplied the current setup on 2026-07-26:

```text
Damper: KW V5 Racing Formula Student 4-way piggyback
Front spring: 36 N/mm linear
Rear spring: 30 -> 36 N/mm linear-progressive
Spring free length: 100 mm
Intentional preload: zero
Tender/helper spring: none
WUFR-27: same package/design intent
```

The reviewer then clarified two previously open items:

1. KW does not document the rear progression and the team has not yet tested it. For the current model, **assume the transition between the 30 and 36 N/mm endpoint tangent rates is linear**.
2. The inboard suspension-geometry line from chassis to rocker is the line used to place the piggyback damper in CAD. The adjacent ARB blade geometry is a separate coupled element and is not part of this spring-force law.

These statements are frozen as explicit design-intent assumptions under `ASM-SUSP-0002`; they are not promoted to vendor facts or installed/as-built metrology.

The reviewer also reported a ride-height shock-pot reading as `44m`. In context that is likely `44 mm`, but the unit/zero/span/sign calibration is not frozen, so the value is retained only as a future correlation datum and is not used in force calculations.

## 3. KW vendor attachment

The reviewer attached `kw-v5racing-formula-student-int-technologytesting.pdf`, SHA-256
`647b7b451612174852293b0bd65d193452991c6a3c697a242c07b04860cea36c`.

Rendered vendor pages support:

- KW V5 Formula Student 4-way adjustable piggyback architecture;
- piggyback full-extension eye-to-eye dimension `185.7 mm`;
- `57 mm` damper travel;
- `36 mm` spring inner-diameter compatibility;
- spring-perch click adjustment of `1/6 mm` per click when used in indexed mode;
- vendor dyno sign convention: rebound positive, compression negative.

The vendor document does **not** provide a measured force-versus-deflection curve for the WUFR rear `30 -> 36 N/mm` spring. Therefore the rear progression used by this model is explicitly a team assumption.

Under `ASM-SUSP-0002`, the 57 mm damper stroke is used as the compression span over which the assumed rear tangent rate transitions from 30 to 36 N/mm. That use is a reviewed modeling assumption, not a statement that KW publishes the spring curve over 57 mm and not an installed wheel-travel claim.

## 4. Suspension geometry and damper reference

Current master geometry source:

`SU-00001-AA 2026 SUSPENSION GEOMETRY.SLDPRT`

- Box file `1943897977651`
- version `2546941960247`
- SHA-1 `2cfb771f296961be0857161f7b57a6c178180d7a`

Reviewer-run exporter evidence:

- attachment ZIP SHA-256 `30bf10a4a9c6097fc32f897d0d16a16e1bee802c3bccf5481f0fd253f2fd8085`
- geometry sketch-points CSV SHA-256 `3886507bcae05d243832647efffb4a9daaf4612e6e364fae7292a072b46166ec`
- project frame `+x forward, +y vehicle left, +z up`

The reviewed inboard line gives the following left-side nominal damper placement points in the native CAD frame:

```text
Front chassis eye: (0.000000, 0.046426, 0.171450) m
Front rocker eye:  (0.000000, 0.209221, 0.195755) m
Distance:           0.164599347 m

Rear chassis eye:  (-1.584625, 0.045720, 0.425818) m
Rear rocker eye:   (-1.584625, 0.209829, 0.438658) m
Distance:           0.164610539 m
```

Those distances independently agree with the reviewed `WUFR26_OPTIMUMK_ACTUATION_V0` nominal coilover lengths:

```text
Front: 164.600 mm
Rear:  164.611 mm
```

The geometry line is therefore accepted as design-intent evidence for damper eye-to-eye placement.

## 5. Zero-preload spring-compression mapping

The physically preferred spring coordinate is

```text
x_s = L_free - L_seat
```

where positive `x_s` is spring compression.

For a direct coilover with fixed spring-seat offsets, the equivalent relation is

```text
x_s = x_pre + L_ref - L_d
```

Under `ASM-SUSP-0002` the reviewer-declared zero intentional preload is represented by the spring being just seated at the KW piggyback full-extension eye-to-eye reference:

```text
x_pre = 0
L_ref = 185.7 mm
x_s = 185.7 mm - L_d
```

This gives nominal design-intent compression at the frozen CAD/actuation state:

```text
Front x_s0 = 185.7 - 164.599347 = 21.100653 mm
Rear  x_s0 = 185.7 - 164.610539 = 21.089461 mm
```

With the reviewed 100 mm free spring length, the corresponding model seat separations are approximately 78.899 mm front and 78.911 mm rear.

These are prototype design-intent values, not installed perch metrology. A future measured perch/seat reference or calibrated shock-pot mapping overrides this assumption.

## 6. Team hardware and historical model evidence

### Shock BOM

`SU-A0707-AA SHOCKS.pdf`

- Box file `2027193944590`
- version `2238189987790`
- SHA-1 `18fd915191fb8bf2cb89628e96399e80be88e526`

The BOM text contains `KW 35-36-100`, `35-36 N/MM SPRINGS`, and the KW V5 Formula Student piggyback damper. This corroborates the hardware family and 100 mm spring naming context but does not override the later reviewer-declared front/rear setup.

### Spring CAD

`KW SPRING.SLDPRT`

- Box file `2020245335291`
- version `2269605443663`
- SHA-1 `b9849faacd23eb9e9e8d2b5482eca219a9446b22`

The current Box representation does not expose measured force-deflection data. It is retained as hardware/CAD identity evidence only.

### Historical inboard calculator

`WUFR26InboardSuspensionCalculator.m`

- Box file `2026725896730`
- version `2238161183237`
- SHA-1 `2f98937654a43914bb586a7e0a1ae9908d97bcb5`

The script uses 36 kN/m front and 30 kN/m rear with a legacy scalar motion-ratio / installation-ratio wheel-stiffness calculation. It remains historical evidence only; it is not the governing force architecture and does not replace the reviewed rear progressive assumption.

### Historical OptimumK setup

`WUFR-26 FINAL 8.21.2025.xlsx`

- Box file `2014803790843`
- version `2224178574043`
- SHA-1 `15eadfb93369192038888da92ebaa6674db56cfa`

The frozen setup contains 36 N/mm front and 36 N/mm rear scalar stiffness fields. Those values are historical OptimumK setup inputs and do not replace the current rear progressive model.

## 7. Constitutive and energy architecture

For a seated conservative spring:

```text
F_s = f_s(x_s)
U_s(x_s) = integral_0^x_s F_s(xi) dxi
k_t = dF_s/dx_s
Q_s = -partial U_s/partial q
```

For `x_s=x_pre+L_ref-L_d`,

```text
Q_s = F_s * partial L_d/partial q
```

and for the reviewed physical single-wheel coordinate,

```text
Q_delta_z = F_s * rho_dw
```

The sign of `rho_dw` is retained. No absolute motion ratio is introduced.

## 8. Front law

The reviewed front spring is linear:

```text
k_f = 36 N/mm = 36000 N/m
F_f = k_f x_s
U_f = 0.5 k_f x_s^2
```

At the nominal design-intent compression `x_s0=21.100653 mm`, the model force is approximately

```text
F_f0 = 759.624 N
```

This is a spring-provider benchmark value, not a solved corner load.

## 9. Rear assumed progressive law

Until physical spring testing replaces it, `ASM-SUSP-0002` defines the **tangent rate** as affine in spring compression over the direct-coilover 57 mm compression span:

```text
k_0 = 30000 N/m
k_1 = 36000 N/m
x_span = 0.057 m

a = (k_1-k_0)/x_span
k_t(x_s) = k_0 + a x_s
```

Because `k_t=dF_s/dx_s`, force must be integrated:

```text
F_s(x_s) = k_0 x_s + 0.5 a x_s^2
```

and stored energy is

```text
U_s(x_s) = 0.5 k_0 x_s^2 + (a/6) x_s^3
```

for

```text
0 <= x_s <= 0.057 m
```

Do **not** use `F_s=k_t(x_s)*x_s`; that would treat tangent rate as secant rate and overstate force.

At the nominal design-intent rear compression `21.089461 mm`:

```text
k_t0 ~= 32.2199 N/mm
F_r0  ~= 656.093 N
```

Again, these are spring-provider model values rather than solved wheel loads.

## 10. Seated-spring contact boundary

If a requested setup/state implies `x_s<0`, the spring has left the authorized seated-spring mode. The provider must report `spring_unseated` rather than silently applying `max(x_s,0)`.

For the assumed rear law, `x_s>57 mm` returns `constitutive_domain_exceeded`; the provider does not extrapolate the 30-to-36 progression.

Tender/helper springs are absent in the reviewed WUFR setup, so no secondary spring contact model is included.

## 11. Audit decision

The evidence plus explicit reviewer assumptions are sufficient to authorize:

- an explicit spring compression/preload/reference contract;
- the WUFR design-intent mapping `x_s=0.1857-L_d` under `ASM-SUSP-0002`;
- the front 36 N/mm linear law;
- the rear assumed affine tangent-rate law from 30 to 36 N/mm over 57 mm;
- stored energy and local tangent stiffness;
- generalized spring force from energy/virtual work using the signed actuation Jacobian;
- explicit assumption provenance and replacement gates.

The evidence is **not** sufficient to authorize:

- presenting the rear assumed curve as measured KW spring data;
- using the raw shock-pot reading as a damper-length reference before calibration;
- velocity-dependent damper force, gas force, stops, ARB behavior, tire compliance, equilibrium/load transfer, installed/as-built travel, or structural loads.

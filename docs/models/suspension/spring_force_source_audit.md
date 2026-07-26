# Suspension spring-force source audit

## Purpose

This audit bounds the evidence proposed for `AUTH-SUSP-0004` / `MOD-SUSP-0004`. The program adds only a conservative coil-spring force/energy/generalized-force provider after the reviewed rigid suspension-actuation implementation. It does **not** authorize damping, anti-roll-bar force, vehicle equilibrium, installed limits, or structural loads.

## 1. Upstream reviewed mechanics

`MOD-SUSP-0003` already provides ideal coilover eye-to-eye length/displacement and the signed local actuation derivative

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
WUFR-27: same package/design intent; no large change
```

This is the controlling current R&D setup identity for PR #47. It supersedes older team-model scalar spring entries where those disagree with the current setup, but it does not manufacture missing constitutive detail.

## 3. KW vendor attachment

The reviewer attached `kw-v5racing-formula-student-int-technologytesting.pdf`, SHA-256
`647b7b451612174852293b0bd65d193452991c6a3c697a242c07b04860cea36c`.

The rendered vendor document supports damper hardware/adjustment facts relevant to the boundary:

- KW V5 Formula Student 4-way adjustable piggyback architecture;
- piggyback dimensional drawing with `185.7 mm` eye-to-eye dimension;
- `57 mm` damper travel;
- `36 mm` spring inner-diameter compatibility;
- spring-perch click adjustment of `1/6 mm` per click when used in the indexed mode;
- vendor dyno sign convention: rebound positive, compression negative.

The vendor document does **not** provide the force-versus-compression curve for the WUFR rear `30 -> 36 N/mm` spring. The `57 mm` damper stroke is not a spring-rate-progression interval, and the `185.7 mm` damper dimension is not by itself a WUFR zero-preload spring-seat reference.

## 4. Team hardware and historical model evidence

### Shock BOM

`SU-A0707-AA SHOCKS.pdf`

- Box file `2027193944590`
- version `2238189987790`
- SHA-1 `18fd915191fb8bf2cb89628e96399e80be88e526`

The BOM text contains `KW 35-36-100`, `35-36 N/MM SPRINGS`, and the KW V5 Formula Student piggyback damper. This corroborates the hardware family and 100 mm spring naming context but does not override the later reviewer-declared front/rear setup or define the rear 30-to-36 law.

### Spring CAD

`KW SPRING.SLDPRT`

- Box file `2020245335291`
- version `2269605443663`
- SHA-1 `b9849faacd23eb9e9e8d2b5482eca219a9446b22`

The current Box representation does not expose a force-deflection law. It is retained as hardware/CAD identity evidence only.

### Historical inboard calculator

`WUFR26InboardSuspensionCalculator.m`

- Box file `2026725896730`
- version `2238161183237`
- SHA-1 `2f98937654a43914bb586a7e0a1ae9908d97bcb5`

The script uses 36 kN/m front and 30 kN/m rear with a legacy scalar motion-ratio / installation-ratio wheel-stiffness calculation. It is useful historical evidence that those endpoint-scale rates were used by the team, but it does not define the current progressive rear spring or the governing force architecture.

The script also contains `m_u=10 kg` as a quarter-car value. That conflicts with the reviewer's current measured statement of `10 kg front axle + 10 kg rear axle = 20 kg total`, so this script is explicitly not mass authority.

### Historical OptimumK setup

`WUFR-26 FINAL 8.21.2025.xlsx`

- Box file `2014803790843`
- version `2224178574043`
- SHA-1 `15eadfb93369192038888da92ebaa6674db56cfa`

The frozen setup contains 36 N/mm front and 36 N/mm rear scalar stiffness fields. Those values are historical OptimumK setup inputs and may not replace the reviewer's current 30-to-36 N/mm rear progressive identity.

## 5. Literature basis

Guiggiani's suspension/vehicle-model framework is used to keep elastic constitutive behavior separate from kinematics and equilibrium and to retain nonlinear/hardening spring behavior when it exists rather than forcing one linear rate.

Dixon's spring/restoring-force treatment is retained as an independent general mechanics source for conservative spring force and stored-energy concepts. Neither literature source provides WUFR-specific spring rates, preload, seat offsets, or installed limits.

## 6. Governing spring coordinates

The physically preferred compression definition is

```text
x_s = L_free - L_seat
```

where positive `x_s` is spring compression and `L_seat` is current seat-to-seat spring length.

An algebraically equivalent direct-coilover form may be used after its reference is explicitly frozen:

```text
x_s = x_pre + L_ref - L_d
```

where `x_pre` is intentional compression at the declared zero-load reference and `L_ref` encodes the fixed seat-offset/reference relation.

The reviewer has supplied `x_pre = 0` as the intended setup. That does **not** establish `L_ref`, does not mean spring force is zero at loaded nominal ride height, and does not permit using the nominal `MOD-SUSP-0003` eye-to-eye length as a zero-load spring reference.

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

## 8. WUFR parameter decision

### Front

The reviewed front spring is sufficiently specified to define an ideal linear constitutive law **as a function of explicitly supplied spring compression**:

```text
k_f = 36 N/mm = 36000 N/m
F_f = k_f x_s
U_f = 0.5 k_f x_s^2
```

Absolute WUFR force at a solved vehicle state still requires the spring-seat/reference mapping described above.

### Rear

The reviewed rear identity is **not yet an executable force law**:

```text
30 -> 36 N/mm linear-progressive
```

The endpoint tangent rates do not say at what spring compressions those rates occur. No current source recovered in this audit supplies the progression interval or a force-versus-compression table.

Therefore PR #47 deliberately prohibits:

- constant 30 N/mm substitution;
- endpoint averaging to 33 N/mm;
- constant 36 N/mm substitution;
- interpreting the 57 mm damper stroke as the progression interval;
- importing the historical OptimumK rear 36 N/mm value as the current law.

The correct result is `progressive_law_incomplete` until the missing spring curve/interval is supplied.

## 9. Seated-spring contact boundary

A conventional coil spring does not carry tensile force in this first model. If a requested setup/state implies `x_s<0`, the spring has left the authorized seated-spring mode. The provider must report `spring_unseated` (or equivalent explicit mode failure) rather than silently applying `max(x_s,0)`.

Tender/helper springs are absent in the reviewed WUFR setup, so no secondary spring contact model is included.

## 10. Audit decision

The evidence is sufficient to authorize:

- an explicit spring compression/preload/reference contract;
- a generic conservative linear or source-defined nonlinear spring constitutive provider;
- stored energy and local tangent stiffness;
- generalized spring force from energy/virtual work using the signed actuation Jacobian;
- the WUFR front 36 N/mm linear spring as a compression-input design-intent constitutive law;
- explicit unavailable behavior for the incomplete WUFR rear progressive law.

The evidence is **not** sufficient to authorize:

- an invented WUFR rear force curve;
- absolute WUFR spring force from coilover eye-to-eye state without a reviewed seat/reference mapping;
- velocity-dependent damper force, gas force, stops, ARB behavior, tire compliance, equilibrium/load transfer, installed/as-built travel, or structural loads.

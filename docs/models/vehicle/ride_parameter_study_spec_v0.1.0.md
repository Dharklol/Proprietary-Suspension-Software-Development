# Local ride parameter study specification v0.1.0

Owner continuation on 2026-10-31 authorizes analytical parameter binding and
sensitivity work following manufactured verification. This packet precedes the
study implementation. It extends the use of EQ-SUSP-0038 / MOD-VEH-0010 only to
an explicitly exploratory study; it does not authorize installed predictions.

Use the existing physical wheel-center vertical coordinate q (body fixed), rigid
actuation solver and reviewed zero-preload compression x=0.1857-Ld. At q=0,
centered samples at ±h give rho=(x+−x−)/(2h), eta=(x+−2x0+x−)/h².
Compute loaded local stiffness with the existing spring law and mapping provider.
Require h=0.001 and 0.0005 m derivatives to agree within relative 0.2% in rho,
2% in eta and 0.2% in total stiffness (absolute floors 1e-6, 1e-3/m and 1 N/m).
Compare total stiffness against the independent centered second derivative of
spring stored energy at h=0.0005 m within 0.2% or 1 N/m. Preserve failures.
These are nominal CAD states, not solved gravity equilibria; local modal
sensitivities are illustrative constant-tangent systems about an assumed local
balance. Do not label their results as actual vehicle natural frequencies.

Represented mass proxy per corner: reviewed scale corner mass less the explicit
5 kg prototype unsprung lump. This is a static-load allocation for independent
corner studies, not modal mass identification or a replacement for coupled body
heave/pitch/roll inertia. Preserve all four scale masses, not total mass/4.

The repo-referenced LLTD workbook was read through Drive on 2026-10-31:
1kwAzxos_H7goRRTbuyWT3U6eArh5o65v6DR0wY28b6s, modified
2026-06-23T05:35:52.022Z. Inputs row labelled Tire vertical stiffness contains
180000,180000,190000,190000 N/m in FL,FR,RL,RR order. The workbook is a template
with no identified pressure/load/tire calibration provenance; preserve these as
legacy scenario inputs, not validated tire properties. Its 207 kg sprung mass
and scalar motion ratios are not substituted for current sources.

Sweep tire multiplier 0.8/1/1.2 and damping proxy zeta=0.2/0.4/0.6 with
c=2*zeta*sqrt(ms*ks). Zeta is an engineering scenario axis for the isolated
sprung oscillator, not a coupled modal damping ratio or measured KW coefficient.
No KW gas/friction assumption follows. Use a 1 mm smooth cosine bump with duration
0.2 s and start 0.1 s over 1 s; dt=0.0002 s and 0.0001 s. Require peak body
acceleration and peak incremental normal load changes under 0.5% (absolute floors
1e-5 m/s², 1e-4 N); energy balance within 1e-6 J. Travel guards ±10 mm are study
bounds only, not hardware limits. Failed cases remain in results.

This is an offline study using the verified core; no changes to existing static
or steady-cornering providers. Next: authoritative tire operating conditions,
source-specific KW curves/settings, equilibrium-based local linearization, and
coupled half-car mass/inertia before vehicle modal claims.

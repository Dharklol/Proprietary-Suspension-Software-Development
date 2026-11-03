# COM selected-tube product sign resolution — 2026-11-01

## Evidence and scope

Owner requested resolution after the local rigid-member diagnostic. Axes remain
owner-confirmed +x forward/+y left/+z up. Axis direction and product sign are
separate questions. Read-only source remains COM SU!B96:P96, the nominal front-
left lower fore tube. Do not infer every COM row's convention from this one row.

SOLIDWORKS Help, Mass/Section Property Options (2021), Inertia Tensor section:
https://help.solidworks.com/2021/english/SolidWorks/sldworks/HIDD_MEASURE_OPTIONS.htm?format=P&value=
The official documentation describes selectable positive/negative cross-product
notation. Therefore software name or axes alone is not enough for automatic
selection.

MathWorks Simscape Multibody, Specifying Custom Inertias, Alternate Inertia
Conventions and SolidWorks example (read 2026-11-01):
https://www.mathworks.com/help/sm/ug/specify-custom-inertia.html
It explicitly defines physical matrix entries Ixy=-integral(x*y*dm) and explains
that SolidWorks alternate products without that minus sign must be negated for
physical tensor assembly. Its worked example converts report Lxy=-0.60 to
physical off-diagonal +0.60. No source text or example model is copied.

For the selected row, document this explicit convention:
Iii=Lii; Iij=-Lij for i!=j, with exact lb*in² to kg*m² conversion.
This source declaration is supported by documentation plus independent source
consistency checks, not by changing the tensor validator until it accepts data.

## Independent nominal geometry check, declared before updated adapter run

Using native front-left fore-inboard and lower-upright hardpoints as the reference
leg line, the COM CG lies 1.5638e-5 m from that line, compatible with the displayed
coordinate precision. Require distance <5e-5 m and the projected CG within the
leg segment. For a slender steel tube, the physical tensor's axial Rayleigh moment
must be small relative to its trace; require ratio <0.01 for this selected member.
As-entered ratio is about 0.286; converted ratio about 0.00281. Do not use this
slender-member criterion as a generic rule for arbitrary assemblies.

The original as-entered tensor also fails the unchanged physical-realizability
check. Keep it as a rejected negative control, not a live alternative source law.
The chosen converted tensor must still pass unchanged symmetry, PSD, realizability,
kinetic-energy and native CG-derivative checks. Do not clip or symmetrize entries.

## Implementation and gate change

Add an explicit conversion adapter requiring a declared convention (physical
matrix entries or positive products). No default, sign guessing or format sniffing.
Test against the analytic inertia of two equal point masses at opposite off-axis
positions, comparing direct point-velocity energy independently. Test the identity
policy and invalid declarations to prevent double-negation.

The previous gate requiring BOTH mutually exclusive interpretations physical is
superseded by an evidence-reviewed source convention for this row. Preserve the
previous failed disposition in the version history and narrative. New selected-
member gate requires the declared convention, physical tensor checks, negative
control rejection, geometry checks and existing energy/derivative checks. This is
a source-model resolution, not a tolerance relaxation. It does not close rigid
member ownership, source pose, other COM rows, or full suspension readiness.
The scalar Lyy-based pitch bookkeeping is unchanged.

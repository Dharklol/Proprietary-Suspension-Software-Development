# Bilateral front wishbone tube local inertia study v0.1.0

Owner continued source-mapped moving-link work on 2026-11-01. This offline study
uses MOD-SUSP-0013/EQ-SUSP-0039 and unchanged native kinematics; no transient
force law or half-car mass substitution is introduced. Drive is read-only.

## Source and complete subset manifest

COM SU!B90:P97 contains eight tube instances, PN SU-70105/6/7/8, bilateral upper/
lower fore/aft legs. Snapshot exact rows, masses, CGs and all nine centroidal
entries. Declare positive-products interpretation per row only after unchanged
physicality and slender-member geometry checks. Do not infer a universal COM sign
policy. Source axes are owner-confirmed; part poses must match nominal geometry.
Use the current no-driver middle body CG only as coordinate reference, not a
whole-body inertia contribution. Count the eight source rows exactly once.
This is a complete tube subset, NOT a complete wishbone/corner/vehicle model.

## Coordinates and compatible upper/lower motion

At qL=0 use q=[body heave, positive-front-up pitch, left qL, right qL], units
[m,rad,rad,rad]. For each side compute native lower/upper hinge unit axes uL,uU.
Let d=U-L, l'=uL cross (L-HL), u'=uU cross (U-HU), all at nominal pose.
Differentiate the constant kingpin separation d dot d:
dqU/dqL=(d dot l')/(d dot u'). Reject |d dot u'|<1e-10 m²/rad.
Lower tube relative angular column is uL and CG column uL cross (r-HL).
Upper tube columns are uU*dqU/dqL and its corresponding CG cross product.
The opposite-side qL column is zero. Body columns are ez and (-ey) cross
(r-CGbody), with angular columns 0 and -ey. All tensors/Jacobians use CAD axes.

Check each upper derivative/CG transport independently by solving native upper
closure at qL=±.001,±.0005 rad, then rotating that member CG about its hinge.
Require fine relative CG Jacobian error <1e-6 and fine upper-angle derivative
error <1e-6 relative. Lower CG differences use the same point-transport provider.
Report both step errors without claiming observed order at numerical floors.

## Source and reduction gates

Require tensor symmetry/PSD/physical realizability unchanged. Require tube CG
reference-leg-line distance <1e-4 m, projection inside that leg segment, converted
axial moment/trace <0.01. Retain per-row failures, never clip or choose signs to
pass. Sum eight local matrices through the exact member manifest. Require direct
member kinetic energy at rates [.1,.2,-.3,.4] to match reduced energy <1e-12 J.
Reflect nominal left/right geometry and sources: body-heave/pitch columns are
unchanged, left/right qL columns interchange with sign reversal because hinge
axes are defined by fore-to-aft points. Require reflected full matrix agreement
within 0.5% per entry or absolute 1e-8 in corresponding mixed SI units.

Report total subset mass and fraction of the 5.068 lb front-corner CAD assembly,
explicitly listing all unrepresented hardware classes. No duplicated body/corner
lump is included. Native rod ends, housings, endcaps, bearings, fasteners, pullrods,
uprights and rear assemblies remain outside this tube subset. Before dynamic
use, full rigid ownership, source poses, q-dependent tensor rotation, all remaining
members and convective inertia terms are required. Current HalfCar is unchanged.

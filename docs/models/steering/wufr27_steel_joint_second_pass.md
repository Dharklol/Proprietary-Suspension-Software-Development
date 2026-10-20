# WUFR-27 steel joint mechanical analysis — second-pass screening

**Status:** pre-FDR engineering sensitivity only. None of these numbers is a
certified component capacity, production drawing dimension, physical force
estimate, or accepted safety factor.

## Geometry and source control

Selected WUFR-27 steel UPSC and lower steering column:
- round tube OD **0.750 in** and ID **0.625 in**, wall **0.0625 in**;
- upper/lower free tube spans 4.878/6.600 in and free shaft spans
  0.787/2.753 in;
- male/female D profile Ø0.590-in major, 0.472-in across flats;
- nominal functional D engagement 0.375 in;
- axial-only 18-8 McMaster 90378A114 clevis pin, min Ø0.121 in in two
  nominal shear planes (actual pin 0.121–0.123 in), hole nominal 0.125 in;
- ER70S-2 steel weld consumable specified; actual steel grade/condition and
  as-welded properties not independently verified. Historic 4130/4140 callout
  inconsistency remains open.

Load cases from `Suspension Calculations 2026`:
- **14.44408009 N m**, calculated cornering;
- **23.69800619 N m**, calculated parked, no 1.5 structural factor;
- **35.54700928 N m**, calculated parked with **1.5 already embedded**.

These are workbook structural moments; the two parked levels are related,
not separate service-cycle amplitudes. Do **not** infer they are measured
steering-wheel torque, tire aligning moments or axial clevis-pin load.

## A. Circular weld-group sensitivity — not a released weld

Treat the weld as an annular line in pure torque with uniform shear flow.
For the selected tube wall, the *reference* mean ring radius is
`r_m=(.750+.625)/4=.34375 in = 8.73125 mm` and the nominal tube wall is
`t=(.750-.625)/2=.0625 in =1.5875 mm`.

`q=T/(2*pi*r_m^2)` [N/mm] and
`tau_weld=q/a_effective` [MPa for q in N/mm and a in mm].

| Calculated case | Shear flow, N/mm | Ideal full-wall equivalent stress, MPa |
|---|---:|---:|
| Cornering 14.444 N m | 30.155 | 18.995 |
| Parked unfactored 23.698 N m | 49.474 | 31.165 |
| Parked factored 35.547 N m | 74.211 | 46.747 |

For the **already-factored** 35.547-N m load case, the necessary effective
throat to remain below a given user-specified **admissible shear stress** is:

| Admissible shear MPa | Required effective throat mm | In |
|---|---:|---:|
| 40 | 1.855 | 0.0730 |
| 50 | 1.484 | 0.0584 |
| 60 | 1.237 | 0.0487 |
| 75 | 0.989 | 0.0390 |
| 100 | 0.742 | 0.0292 |

**Important:** a 40-MPa admissible weld stress would require 1.855 mm
effective throat, greater than the original nominal 1.5875-mm tube wall.
It therefore would not satisfy that selected conservative design criterion
if the actual weld were a plain full-wall butt weld. This is **not** proof
of failure at the physical load: 40 MPa is a chosen allowable stress,
not an as-welded verified property. The weld's actual effective throat,
quality and physical r_m have not been measured; penetration is not guaranteed.
An ER70S-2 filler tensile rating is not by itself a strength rating of the
steel base metal/HAZ, weld toe or shaft shoulder.

For orientation only: using *assumed* weakest local steel yield
`S_y=205 MPa`, ideal von Mises shear yield `S_y/sqrt(3)=118.36 MPa`,
the simple line model gives an ideal gross yield-to-applied-stress ratio
of `118.36/46.747=2.53` **against the already-factored torque** at
full nominal effective throat. It is NOT a weld safety factor, since real
throat, discontinuity, residual stress, workmanship, weld failure modes and
service loads are unverified. Requiring an **additional** FoS 3 on yield
against the already-factored torque would correspond to an allowable
39.45 MPa and ~1.88 mm effective throat, above nominal wall thickness.
Do not double-count the original 1.5 applied structural factor accidentally.

### Geometry/review blockers

The CAD review must identify whether the real junction is a full-penetration
circumferential butt weld, partial-penetration seam, fillet weld or hybrid
socket weld. A stated 0.200-in engagement, 0.298-in weld bead intrusion
clearance and 0.130-in shoulder do **not** define effective weld throat,
toe radius or the load path. Resolve axial weld station, collar diameter,
root gap, overlap, HAZ and available radial section before choosing a weld
design formula or calculating local SCFs/FEA boundary conditions.

## B. 1/8-in clevis pin bending — geometry-sensitive screen

The prior min-Ø0.121-in, two-plane pure-shear calculation at
assumed 205-MPa yield and **FoS 3** gave approximately **585 N**.
This should never have been called the whole-joint allowable capacity.

Assume *temporarily* an ideal simply supported beam with two symmetric
outer support reaction centerlines and a single concentrated transverse
force F at the center. If **L** is the measured support-center spacing,
`M_max=F*L/4`, `sigma_b=32*M_max/(pi*d^3)`; hence

`F_allow,bend=(S_y/FS)*pi*d_min^3/(8*L)`.

| Hypothetical support-center spacing L, in | Pin bending-screen F, N |
|---|---:|
| 0.10 | 307 |
| 0.15 | 204 |
| 0.20 | 153 |
| 0.25 | 123 |
| 0.33 | 93 |
| 0.50 | 61 |
| 0.566 | 54 |

This concentrated-force assumption may be very conservative for the
actual distributed bearing, but illustrates why the **585 N double-shear
number cannot be treated as the assembled pin capacity**.

A separate idealized symmetric *distributed central member* of width b
and two outer bearing walls, each width t, gives
`M_max=F*(b/8+t/4)` for uniform central loading and
support reactions at the outer wall midplanes. For the **unverified
illustrative** b=0.472-in and t=0.094-in combination, the equivalent
point-load span is b/2+t=0.330 in, producing **~93 N** at the same
assumed yield and FoS. This is **not** a geometric claim about the
existing D adapter: identify real pin bore contact and bearing widths
in the released section first. Load distribution may be nonuniform.

The reported pin-hole local minimum steel thickness **0.094 in** is
not the plain tube's 0.0625-in nominal wall; annotate which locally
reinforced adapter/lug or flat surface supports that minimum.

## C. Lug edge shear-out — conditional datum sensitivity

For *one* 0.094-in steel lug, assumed yield Sy=205 MPa, FoS=3,
0.125-in nominal hole diameter and a **true center-to-free-edge**
distance `e` **parallel to the axial pullout force**, idealized
two-plane shear-out is

`F_allow,shear-out = 2*t*(e - d_h/2)*(S_y/(sqrt(3)*FS))`, e>d_h/2.

| Hypothetical e, in (true pin-center to free edge) | One-wall capacity screen N |
|---|---:|
| 0.125 | 299 |
| 0.200 | 658 |
| 0.367 | 1,457 |
| 0.687 | 2,988 |

**The 0.367-in and 0.687-in numbers were previously supplied without
unambiguous datum/location and load-direction identification.** They
must not be promoted to true e for the actual lug. Check width,
edge break, loaded material and multiple shear planes before allocating
capacities to any two outer walls. One-wall net-tension screen is
~725 N at assumed true width w=0.300 in and thickness 0.094 in;
the previous one-wall bearing screen is ~501 N with min pin
diameter 0.121 in. Neither defines the central member capacity.
Actual axial service force is UNKNOWN; no installed axial retention
factor of safety is possible yet. Rack-interface heavy-duty *spring
pins* carry TORQUE and require a separate torque-pin/ligament check.

## D. Reversing-torque fatigue — required-property bounds, not life estimates

No source-backed cyclic torque history, notch radius, detail geometry,
actual as-welded endurance condition or corrected material torsional
endurance limit has been established. Consequently, **do not
claim infinite life or 5e8-cycle endurance**.

Use purely hypothetical fully reversed zero-mean torque amplitudes to
state the *required corrected local torsional endurance limit*:

`S_e,tau,required = FS_fatigue*K_f,tau*tau_nominal,alternating`.

Here `K_f,tau` is a chosen FATIGUE notch factor, not an asserted actual
stress concentration factor. Illustration at **FS_fatigue=2**:

| Hypothetical fully reversed torque | Ideal round tube tau_a, MPa | Provisional exact D tau_a, MPa | Required D corrected Se,tau for Kf=1.5, MPa | Required for Kf=2, MPa |
|---|---:|---:|---:|---:|
| +/-14.444 N m | 20.55 | ~33.1 | ~99.3 | ~132.4 |
| +/-23.698 N m | 33.72 | ~54.3 | ~162.9 | ~217.2 |
| +/-35.547 N m | 50.58 | ~81.4 | ~244.2 | ~325.6 |

The hypothetical +/-23.698 or +/-35.547 cases are **not** asserted
true vehicle duty cycles; the last already has the workbook's 1.5
structural factor and must not be used as a measured fatigue amplitude.
The D peak stress estimates are themselves provisional from a
2D Prandtl/Saint-Venant section screen; they do not contain fillet
transition, hole or weld-toe concentrations.

Needed before a steel fatigue pass/fail conclusion: reconciled 4130/4140
grade/heat treatment/stock, specimen surface finish, as-welded HAZ and
weld-toe condition, effective notch radii and fatigue notch sensitivity,
mean and alternating torque with a credible duty history, and a
geometry-supported beam/contact/notch analysis. Steel bulk-shaft endurance
and weld fatigue are **separate details**; do not apply a base-metal
Marin-corrected limit to a weld toe without the correct weld classification.

## Decisions and physical-test boundary

- Keep the original aluminum comparison intact in Design Materials.
- The steel design has enough geometry to bound pure circular tube torque,
  to screen ideal prismatic D torsion, and to expose unsupported material
  and support-span assumptions.
- **Not yet verified:** final weld stress or weld fatigue, pin/lug pullout
  load factor, rack spring-pin tear-out, shoulder SCF, assembled torsional
  stiffness or free-play budget.
- Physical installed correlations remain deferred per project scope.
  Those are distinct from the dimensional CAD details and material specs
  needed to release a steel engineering design.

## Reproducible implementation

`src/pssd_steering/steel_joint_screens.py` contains pure, unit-explicit
engineering sensitivity functions. Regression checks:
`python -m unittest tests.test_steering_steel_joint_screens`.
The tabulated figures are rounded results from that screen plus the
PDR's **provisional** D-profile shear estimates, with each assumption
explicitly labeled. No model-registry permission or vehicle operation
claim is activated by this document.

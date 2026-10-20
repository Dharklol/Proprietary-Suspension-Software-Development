# WUFR-27 steering: pre-FDR hardware definitions and evidence register
**Frozen for design-review *source interpretation* on 2026-10-20, not released manufacturing drawings.**

This packet records what has actually been defined, distinguishes calculations from
verification, and provides the traceability boundary for subsequent FDR rewriting.
The `WUFR-27 Steering PDR` (Google Doc ID
`11oA3n8DkVLHVNrADySI0-5wMeEYW0cistUdlketEXHQ`) remains the review source.
**Preserve its complete abandoned aluminum design analysis**, including original
equations/figures/tables, in its Design Materials tab when reformatting. For now
the source sections are retained intact and labeled historical; do not delete
them, silently recalculate their conclusions as steel, or make 6061-T6 an
active WUFR-27 specification.

## Current chosen hardware definition

| Item | Current design source | Maturity |
|---|---|---|
| UPSC and lower column | Reused/last-year steel, NOT 6061-T6 | Selected material family; grade/heat treatment to confirm |
| Column tubes, both | OD 0.750 in, ID 0.625 in, nominal radial wall 0.0625 in | CAD dimensions supplied |
| Upper/lower column free spans | 4.878 / 6.600 in | CAD dimensions supplied |
| Upper/lower free shaft spans | 0.787 / 2.753 in | CAD dimensions supplied |
| Shaft major radius | 0.295 in (major diameter 0.590 in) | CAD geometry confirmed |
| Male and female D across-flats | Both nominal 0.472 in before tolerancing | CAD geometry confirmed |
| D flat depth each side | `0.295 - 0.472/2 = 0.059 in` | Geometry derived |
| D chord width | `2 sqrt(0.295^2 - 0.236^2) ≈ 0.354 in` | Geometry derived |
| Functional D engagement | Target/minimum 0.375 in | CAD design intent; measure postweld |
| Male shaft | PDR states normalized 4130 in structural passage, 4140 in cost table | **Unresolved conflict**; use actual drawings/cert |
| Female D adapter/column grade | Steel; exact stock grade not recovered | Not verified; no fabricated capacity claim |
| Weld | ER70S-2 filler, regular steel welding, cooled, no post-weld treatment | User-design process intent; procedure/quality still pending |
| Weld geometry | ~0.298 in available intrusion clearance, 0.200 in weld engagement/overlap, 0.130 in shoulder | CAD statements; verify exact section and functional interference |
| Pin in D connection | McMaster 90378A114 18-8 stainless 1/8-in nominal clevis, cotter retained | Selected |
| Clevis diameter tolerance | -0.004/-0.002 in, actual 0.121-0.123 in | User-supplied McMaster screenshot |
| Clevis pin loading | **Two** shear planes, axial retention only; D flats transmit torque | Confirmed intent; real load sharing to verify |
| Pin bore | 0.125 in nominal, fit/hole tolerance to be specified | Dimensional intent |
| Hole surrounding section | User reports min ~0.094 in including tube-side material | **Verify at joint section:** round OD/ID implies 0.0625-in unreinforced wall |
| Lug transverse width | 0.300 in | Supplied; identify loaded section |
| Reported edge/center dimensions | 0.687 in described as free edge distance; 0.367 in reported to centerline | Ambiguous datum/contact direction; do NOT substitute in certified shear-out without drawing |
| Gearbox | Retained housing and 1:1 KHK miter pair per source evidence | Nominal, gear clearance/preload and axial support require review |
| Rack interface | NaRRco-specific heavy-duty *spring pins*, torque-transmitting interface | Analyze separately from axial D-joint clevis |
| Wheel/quick release | Abandoned new aluminum-compatible MPI QR proposal, retained steel-compatibility path | Reconcile final part identity and BOM |
| Primary steering to rack | Design Study 3.5 in/rev, 1:1 reported input mapping; +input to canonical +y rack | **Design-source only**, PAR-STEER-0001 |
| Rigid geometry | WUFR27_STEERING_BASELINE_V0 unchanged from WUFR26_DESIGN_NOMINAL_V0 | Nominal CAD design-source |
| Tire/vehicle correlation | Not supplied; not asserted | Deferred physical/operating-state gate |

No intended running clearance is *not* a machinable drawing tolerance. The actual
assembly is required to be insertable by hand with low backlash, and should
use a **small positive fit clearance**, selected from measured parts/EDM vendor
capability plus worst-case profile contact and finishing allowance. The
in-house across-flat process is +/-0.005 in per part. Independent male/female
dimensions therefore span **-0.010 to +0.010 in relative fit**, creating both
assembly and backlash risk. Wire EDM for the internal female D profile is
recommended; the drawing limits and angular lost-motion acceptance remain OPEN.

## Explicit analytical load-case hierarchy

From `Suspension Calculations 2026` > `Steering Column Forces`:
- C15 = **14.44408009 N m**, calculated cornering moment.
- C10 = **23.69800619 N m**, calculated parked moment without 1.5 factor.
- C9 = **35.54700928 N m**, calculated parked column reaction with 1.5 factor.
These are calculated structural moments, not measured wheel torque or source-
supported tire self-aligning moments. Do not apply an *additional* factor of 1.5
unknowingly to C9. Their positive/negative torque sign in the nominal software
sweep is deliberately prescribed, not a tire physics prediction.

## Screening calculations (NOT joint design approval)

Assume, conservatively and provisionally, 18-8 yield strength 205 MPa,
steel lug yield strength 205 MPa, von Mises shear yield tau_y = Sy/sqrt(3),
and factor of safety 3 on yield. These properties are not lot-certified.

- Pin min diameter 0.121 in and **two** shear planes:
  `F_allow,shear = 2(pi/4)d_min^2 (Sy/(sqrt(3)*3)) ≈ 585 N`.
- One individual loaded 0.094-in-thick wall at diameter 0.121 in:
  `F_allow,bearing ≈ t*d_min*Sy/3 ≈ 501 N` **per wall**.
- If an individual lug truly has 0.300-in transverse width, nominal
  0.125-in hole and 0.094-in thickness:
  `F_allow,net ≈ (w-d_h)*t*Sy/3 ≈ 725 N` **per lug**.
- Bearing sharing, exact net geometry and edge shear-out **not rated** before
  locating the loaded thickness, material grade, physical center-to-edge
  distance and actual shear-out direction.
- Pin bending, cotter retention, pin-hole clearance and interface contact
  remain not rated. Applied axial load is unknown, so **no service-load FoS**
  is claimed. The allowable force above is an illustrative isolated mode,
  NOT a certified capacity for a complete joint.
- Rack spring pins require torque-driven shear, wall bearing, net-section and
  tear-out analyses of the actual NaRRco/pinion bore geometry separately.

## Provisional compliance and stress evidence

- Steel shear modulus `G = 80 GPa` is illustrative pending grade/condition.
- Four free spans modeled as circular sections only: two tubes
  `Do=0.750, Di=0.625 in` and two solid shaft segments `D=0.590 in`.
  At `T=35.547 N m`, the independent module predicts approximately
  **1.57 degrees** total *elastic* twist under common-torque, 1:1 assumptions.
- The 1.57-degree result does not include the D-profile effective torsional
  rigidity, joint compliance, rack, gear, bearing supports, welds or QR.
- It must **not** be added to steering *free play*. The PDR quotes a 7-degree
  total allowable steering wheel free-play rule. Historical ~4-degree, ~5-degree
  and 2.35-degree observations remain distinct sessions/states, not additive.

## Required analytical and review closure

1. Drawing-controlled D profile with male/female actual limits, mating
   clearance, angular backlash contact model, minimum engaged length, and EDM
   inspection scheme (do not release an arbitrary zero-clearance fit).
2. Complete axial pin/lug load path (two pin shear planes, individual wall
   bearing, geometric ligament and pin bending) and separate torque-carrying
   rack spring-pin structural checks.
3. Noncircular double-D shaft/collar torsion, shoulder transitions,
   fatigue/reversing torque, weld effective throat/penetration and toe effects;
   confirm revised 0.298/0.200/0.130-in region from CAD section.
4. Reconcile existing FEA: review BCs/contact/mesh, load matching and the
   anomalous lower peak von Mises accompanied by ~7x displacement increase.
   No verified FEA capacity or displacement assertion until reconciled.
5. Material callouts, tube sourcing, updated exact quick release, final
   manufacturing drawings, assembly/BOM prices and SolidWorks mass exports.
6. Physical installed correlation is intentionally OUT OF SCOPE for this
   design-review cycle and must be documented as a future Level F gate.

## Source documentation in repository

- `docs/models/steering/wufr27_compliance_v1.md`
- `docs/models/steering/wufr27_design_source_compliance_v1.md`
- `docs/models/steering/wufr26_force_compliance_evidence.md`
- `docs/models/steering/wufr26_level_e_preparation.md`
- `docs/verification/steering/wufr26_level_f_measurement_protocol.md`
- User-provided exact dimensions, thread corrections and McMaster screenshot
  from the 2026-10-20 steering FDR work conversation.

**Document handling:** Leave the PDR structure and embedded aluminum analysis
unchanged until review. During the later FDR rewrite, transport the complete
historical aluminum alternative, including original equations, visuals, FEA,
tables and reviewer commentary, to the Design Materials tab **without
discarding or silently replacing original source content**.

# WUFR-27 double-D fit/contact sizing — FDR evidence

**Authority:** analytical comparison of *idealized centered profiles*, not a
released mating-part drawing, general worst-case backlash bound, validated
contact stress, or physical steering test. Supports the PDR's wire-EDM decision
and corrects the one-sided-versus-bidirectional wording.

## Source dimensions

- Symmetric D male: circle radius `R=0.295 in`, major Ø0.590 in.
- Across-flat male nominal `d_af=0.472 in`, so `a=d_af/2=0.236 in`.
- Flat depth `h=R-a=0.059 in`.
- Half chord `b=sqrt(R²-a²)=0.177 in`; chord width `2b=0.354 in`.
- Functional nominal engagement `L_e=0.375 in`.
- Female nominal profile identical **before tolerancing**; actual sliding
  clearance/roundness, weld distortion and inspection not established.

## Derivation: exact ideal centered chord-contact angle

Consider rotation theta about the common axes of perfectly concentric,
sharp-edged symmetric D profiles with the **same radius** and a positive
*diametral* across-flats clearance `C=d_af,female-d_af,male`.

For small positive theta the male's top-right flat-circle intersection at
`(b,a)` supports the highest y-value after rotation:
`a*cos(theta)+b*sin(theta)=a+C/2`.
Since `b²+a²=R²`, the first-contact rotation follows:

```latex
\theta_\mathrm{one}
=\arcsin\!\left(\frac{a+C/2}{R}\right)
-\arcsin\!\left(\frac{a}{R}\right)
\qquad
\Delta\theta_\mathrm{bi}=2\theta_\mathrm{one}
```

For small clearance in radians, `theta_one≈C/(2b)=C/.354`,
i.e. approximately **0.162 degrees of one-sided take-up per 0.001 in**.
**Bidirectional free play is twice this value.** It was previously easy to
misinterpret 1.62 degrees for 0.010-in as the total free play; the more
accurate paired figure is **3.301 degrees per joint bidirectionally**, at
the ideal coaxial geometry. This is NOT the full vehicle system free-play
measurement or a true geometric worst case.

| Across-flats C, in | One-sided rotation, deg | Bidirectional play, deg |
|---:|---:|---:|
| 0.0005 | 0.0810 | 0.1620 |
| 0.0010 | 0.1622 | 0.3243 |
| 0.0015 | 0.2435 | 0.4869 |
| 0.0020 | 0.3249 | 0.6499 |
| 0.0050 | 0.8171 | 1.6341 |
| 0.0100 | 1.6504 | 3.3009 |

If a provisional *single joint* budget is 0.5 deg peak-to-peak, the
**maximum actual** diametral clearance in this centered model is
`Cmax=0.001540 in`. A 0.25 deg budget corresponds to
`Cmax=0.000771 in`. These are possible design-allocation calculations,
not approved acceptance limits. Two joints' play, bevel, rack, quick
release and other free-play sources must be budgeted together.

## Size stack and manufacturing implication

Let `C0=(female nominal)-(male nominal)`, and independent symmetric
male/female across-flat tolerances `tm,tf`:
`Cmin=C0-tm-tf`, `Cmax=C0+tm+tf`. The fit must have a small positive
`Cmin` after form tolerance and remain within allocated `Cmax`.

If independently produced male and female nominal profiles are both held
to the team's feasible in-house **+/-0.005 in**, the clearance envelope
is **[-0.010,+0.010 in]**: the first limit is interference; the second
corresponds to 3.30 deg *bidirectional* ideal single-joint play.

Merely EDM-machining the female to +/-0.0005 in while leaving the male
at +/-0.005 in around its independent nominal still gives an enormous
combined dimension envelope (span 0.011 in). For example `C0=.006`
would achieve `Cmin=.0005` but `Cmax=.0115`, more than 3.8 degrees
of ideal bidirectional play. A low-lash EDM female fit therefore needs
**actual matched male measurement OR tighter male finish tolerances**,
plus profile/form/position inspection. Supplier process capability has not
been established. Do not release these illustration numbers as tolerances.

## Flank reaction sensitivity, not a bearing-pressure proof

Under ideal two-flank opposing equal normal reactions, the maximum normal
force couple lever arm is the half chord `b=.177 in=4.496 mm`. Hence
`N_per_flank >= T/(2b)` if each flank uses the maximum lever. At the
already-factored parked torque `T=35.547 N m`, the lower bound is
**3.953 kN per loaded opposing flank**, assuming this simplified couple.

For engagement `Le=9.525 mm`, hypothetical uniform contact patch width
`wc=1 mm` gives `p=N/(Le wc)=415 MPa`, while `wc=5 mm` gives
`83 MPa`. These numbers are *sensitivity examples, not a Hertzian
pressure solution*; actual contact is nonuniform and involves sharp
profiles, edge radii, clearance, load redistribution, steel properties,
wear and manufacturing distortion. Even the lower-bound force changes
if a single flank or offset contact participates. Full-width bearing
averages are not a substitute for validated contact FEA or matching tests.

## Required geometric closure

1. Final male and female profile drawing limits including circular
   form, angular indexing, edge/chamfer radii, concentricity and post-weld
   profile distortion. The female D can be wire EDM; male tolerance must
   be controlled or matched.
2. A documented allowable total free-play budget divided across both D
   joints, bevel box, rack and quick release. The old PDR cites a 7 deg
   regulatory steering-wheel free-play ceiling; do not claim that 0.5 deg
   per D joint is a rule or a released specification.
3. Contact force distribution versus torque, double-D chord edge radius,
   minimum steel collar wall and fatigue/wear, and verified functional
   engagement >=0.375 in.
4. Confirm actual angular play with a direction-reversing bench measurement
   before asserting a *physical* low-backlash design.

The analytic calculation is independently regression tested in
`pssd_steering.double_d_fit_screen.IdealDoubleDFit`. It does not alter
vehicle software's rigid steering or tire/vehicle operating-state models.

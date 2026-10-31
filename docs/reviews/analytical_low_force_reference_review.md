# Independent analytical low-force reference

## Scope

This verification increment compares the coupled four-wheel development kernel
with independently derived small-angle single-track equations. It uses only
manufactured geometry and tire curves, not the native WUFR setup, R25B data or
its negative-inclination extension. It adds no production force law, setup
default, design ranking, predictive accuracy claim or physical-correlation gate.

The existing synthetic fixture supplies 120 kg total mass, symmetric 0.75 m
front/rear axle offsets, 1 m track, four 10 kN/m vertical guide springs, a
0.2 m rigid tire radius and front wheel steer=10*rack. No static toe or camber
thrust is present. The existing table evaluator receives manufactured constant
cornering-stiffness curves with half of the declared axle stiffness per tire;
the curves are independent of Fz, inclination and pressure within their explicit
finite source domain. This removes those effects for the reference only.

Three axle-stiffness pairs (Cf,Cr), in N/rad, are tested: (3200,3200),
(2400,3600), and (3600,2400), at V=4 and 8 m/s. These are verification controls,
not identified tire parameters. Under/neutral/oversteer descriptions, if used
for these fixtures, refer only to this local single-track steering gradient;
they do not establish transient stability or native vehicle handling.

## Separate derivation

Let a,b be CG-to-axle distances, L=a+b, positive curvature k be a left turn,
delta be front wheel steer and beta the CG velocity heading relative to the
vehicle heading. The project uses positive alpha=wheel heading-velocity heading.
To first order, with no rear steer:

```text
alpha_f = delta-beta-a*k
alpha_r = -beta+b*k
Ff = Cf*alpha_f ; Fr = Cr*alpha_r
Ff+Fr = m*V^2*k
a*Ff-b*Fr = 0
```

Therefore:

```text
Ff/k = m*V^2*b/L
Fr/k = m*V^2*a/L
beta/k = b-m*V^2*a/(L*Cr)
delta/k = L+m*V^2/L*(b/Cf-a/Cr)
```

The reference uses declared fixture constants and arithmetic only. It never
reads solved normal loads, body pose, sideslip or rack position. Axle stiffness
means the sum of both tire stiffnesses, preventing a hidden factor of two.
Force/curvature has units N*m, but is a force gradient, not a torque.

Guiggiani (2022), *The Science of Vehicle Dynamics*, Section 7.5.1, equation
7.51 (printed p. 259), supplies the small-angle axle-slip structure, and
Section 7.5.2, equations 7.57-7.58 (printed p. 261), the steady axle force/yaw
balance. The uploaded source was inspected directly. The equations above are
re-derived in project signs and with whole-axle constant stiffness. The full
four-wheel implementation retains exact wheel-center velocity, force projection
and geometry; it is expected to approach, not equal, this first-order reference
at nonzero curvature. No single-track assumption is inserted into its solve.

## Numerical experiment and acceptance

For each stiffness/speed pair, solve the straight case and signed curvature
pairs at h=0.002, 0.001 and 0.0005 per metre. Centered response gradients are
(f(+h)-f(-h))/(2h). Compare steer=10*rack, beta, summed local front Fy and summed
local rear Fy against the four independent expressions above. Local axle force
and heading-frame lateral force differ at higher order; the first-order limit
is the comparison being tested.

All six straight cases must recover the independent vertical spring balance:
heave=R-m_s*g/(4K)=0.175475 m and four normal loads=120*g/4=294.3 N. Straight
body angles, sideslip, rack and holder must be zero within the documented
numerical checks, and all tire forces below 1e-6 N.

Acceptance was declared before the initial comparison:

- Full physical force and moment norms <=1e-6 N and <=1e-6 N*m for every solve.
- Final response-gradient error <=2e-5 after dividing each absolute discrepancy
  by max(abs(reference), one unit of that gradient's stated units).
- Every gradient error must decrease by a factor <=0.6 on each halving of h,
  unless the finer error is already <=1e-7 in that normalization.

The 2e-5 threshold is a verification criterion for the deliberately small-angle
manufactured experiment, not an assigned accuracy of WUFR predictions. Three
step sizes and both signs make the convergence behavior visible; no case is
removed from the report and a failed solve cannot become a passing comparison.

## Fixture derivative correction

The initial experiment used the pre-existing manufactured geometry's centered
finite-difference point Jacobians. One equal-stiffness 8 m/s case at k=-0.0005
failed the unchanged decreasing line search with scaled residual 1.089e-11,
just above the 1e-11 criterion, despite force/moment closure around 1e-8.
The failed comparison was retained during diagnosis; it was not reclassified
as accepted or repaired by changing a limit.

This new fixture now differentiates Ry(theta)Rx(phi) analytically. Each current
material contact point is frozen in the upright/body frame, as in the original
fixture; J_wb follows -g_body/g_wheel from the same normal material derivative.
The geometry, tire curves, Newton criterion, physical limits and production
providers are unchanged. A separate test compares every wheel-center/contact
body derivative against material-point position perturbations at two step
sizes (1e-4 and 5e-5), including nonzero roll, pitch and rack. The 5e-9 derivative
comparison gate passes. Existing native finite-difference providers are not
modified or implicitly certified by this manufactured fixture correction.

## Results

All 42 solves and all six fixture comparisons pass. Halving curvature reduces
the leading comparison error by approximately four, consistent with the
second-order centered limit. The largest final normalized error is about
6.13e-7. Maximum physical force and moment norms are approximately 3.36e-10 N
and 1.33e-9 N*m, below the unchanged 1e-6 limits.

At 8 m/s, the finest-step front steer/curvature comparisons are:

| Cf,Cr (N/rad) | Analytical (m) | Coupled finite-step gradient (m) |
|---|---:|---:|
| 3200,3200 | 1.50000000 | 1.50000039 |
| 2400,3600 | 2.03333333 | 2.03333430 |
| 3600,2400 | 0.96666667 | 0.96666660 |

The equal-axle steering gradient is independent of speed to first order. The
other two cases reproduce the expected V-squared increment, while the sideslip
and axle force comparisons pass separately. This checks more than symmetry or
net equilibrium closure: it independently constrains response magnitude.

## Reproduction and next step

```bash
python -m unittest tests.test_low_force_reference -v
python scripts/run_low_force_reference_benchmarks.py \
  --output low_force_reference_report.json \
  --summary-output low_force_reference_summary.json
```

The compact reference is
`benchmarks/vehicle/analytical_low_force_reference_summary_v0.1.0.json`. Full
reports retain all successful/failed solves, their coordinates, signed tire
forces, residuals, conditioning, analytical references and per-step errors.
Source hashes bind the fixture, reference, tests and production kernel used.
CI regenerates/uploads both artifacts. No exact cross-runtime JSON equality
is required.

Next is native computational-envelope mapping with explicit failure categories
and retained branch/source limits. Passing this manufactured limit does not
establish a native grip limit, tire accuracy, stability or setup authority.

# Manufactured stiffness, modes and reduced ride verification v0.1.0

## Scope and source

Owner direction on 2026-10-31 permits work on verification cases independently
of the status of car-specific tire/damper data. AUTH-SUSP-0020 and AUTH-VEH-0013
bound this increment to explicit manufactured inputs. MOD-SUSP-0012 maps an
existing successful spring law into a local one-coordinate elastic tangent.
MOD-VEH-0010 provides two-DOF modal calculations and a linear reduced ride
verification engine. Neither selects installed parameters nor modifies the
existing static/steady-cornering providers.

Guiggiani, *The Science of Vehicle Dynamics*, third edition (2022), chapter 10,
printed pp. 440–446, especially equations 10.11–10.15, supplies the reduced
mass/spring/damper/tire structure. The explicit scalar balances below are derived
from point forces; OCR signs in the matrix display are not a source for code.
Guiggiani uses an aggregate whole-vehicle interpretation in section 10.2. Our
manufactured fixture declares its represented system explicitly and never
automatically divides a vehicle mass/rate by four. No inerter or tire damper is
included in this first model. No licensed source text is copied into the repo.

## EQ-SUSP-0038: one-coordinate elastic tangent

Let q be a declared translational coordinate [m], x(q) spring compression [m],
rho=dx/dq [1], and eta=d2x/dq2 [1/m]. The existing spring law supplies compression
force F=dU/dx [N] and tangent k=dF/dx [N/m]. Then

    Q = -F*rho
    K_q = -dQ/dq = k*rho^2 + F*eta

The second term must be retained for a loaded changing-ratio mechanism. The map
requires matching spring/configuration identities and a named derivative source.
It neither estimates derivatives from a motion-ratio scalar nor duplicates the
spring constitutive law. Negative total K_q is reported as a local nonpositive
tangent, not clipped or passed into a stable modal calculation. This is not a
complete axle/body tangent with ARB coupling. Native curvature extraction is a
later adapter and is not silently set to zero.

## EQ-VEH-0027: equilibrium-relative two-DOF ride

Vertical is positive upward. z_s,z_u,r [m] are sprung, unsprung and road
displacements relative to a declared static equilibrium. v_s,v_u are velocities.
Inputs are m_s,m_u [kg], k_s,k_t [N/m], c [N*s/m], positive gravity magnitude g
[m/s^2], explicit compression/extension travel bounds [m] and source/system IDs.
All masses/stiffnesses/bounds are positive, damping nonnegative. These inputs
are independent of any vehicle defaults. Damping is an ideal manufactured law,
not a KW calibration or a claim that damper gas/friction forces vanish.

    f_s = -k_s*(z_s-z_u) - c*(v_s-v_u)
    delta_N = k_t*(r-z_u)
    m_s*a_s = f_s
    m_u*a_u = -f_s + delta_N
    N0 = (m_s+m_u)*g
    N = N0 + delta_N

f_s is the incremental suspension force on the sprung body, with the opposite
force on the unsprung body. The absolute spring support at equilibrium is m_s*g;
gravity is already balanced there and is not added again to incremental ODEs.
Suspension extension is z_s-z_u; damper force on the sprung body is -c*(v_s-v_u).

## EQ-VEH-0028: undamped modal reference

    M = diag(m_s,m_u)
    K = [[k_s,-k_s],[-k_s,k_s+k_t]]
    C = c*[[1,-1],[-1,1]]

Compute eigenvalues of the symmetric mass-normalized K, then mass-normalized
mode shapes with explicit ordering and eigenpair residuals. Frequencies are
undamped system modes, not separate front/rear ride frequencies. The first
mode fixture m_s=m_u=1, k_s=2, k_t=3 has eigenvalues 1 and 6 and physical
eigenvectors proportional to (2,1) and (1,-2). The modal implementation and the
time integrator must not use one another as their independent reference.

## EQ-VEH-0029: perturbation energy and power

    E = .5*m_s*v_s^2 + .5*m_u*v_u^2
        + .5*k_s*(z_s-z_u)^2 + .5*k_t*(z_u-r)^2
    P_loss = c*(v_s-v_u)^2
    P_road = delta_N*r_dot
    dE/dt = P_road - P_loss

This is energy of the perturbation system. It excludes baseline static-load
work and is not the absolute gravitational energy of an installed car. Integrate
loss and road work with the same stage quadrature as the ODE; report E+D-W-E0
separately. Never force the energy residual to zero by adjusting an output.

## Numerics and failure contract

Use explicit fixed-step classical RK4 with declared positive dt, integer step
count, initial time and initial state. Four physical states plus loss/work
quadratures are advanced together. Road providers supply both displacement and
velocity with an explicit source ID: flat, analytic sinusoid or a finite smooth
cosine bump. These provider formulas are not inferred from sparse samples.

Every stage and accepted output must have finite data, positive N, and remain
within declared suspension travel. On failure preserve the last accepted sample
and the failing stage time/code; do not clip forces, repair contact or integrate
past the boundary. These are sampled stage guards, not continuous event-location
proof. An unsupported event time is not an exact wheel-lift time. Fixed-step
completion alone is not an accuracy certificate; time-step refinement belongs
to verification. No adaptive contact switching, bump stop or nonlinear damper
law is implied.

Outputs retain parameter/system/road IDs, states, accelerations, incremental
and total normal load, suspension/damper forces, travel, energy, accumulated
dissipation/work and energy-balance error. Invalid contracts are rejected before
integration; runtime domain failures return structured incomplete results.

## Independent verification fixed before implementation

| ID | Case | Required evidence |
|---|---|---|
| BENCH-SUSP-0038 | Constant ratio; loaded nonlinear compression map; negative geometric tangent; source mismatch | Independent derivatives of U(x(q)) and Q(q), two step sizes; retain F*eta; reject failed/mismatched source |
| BENCH-VEH-0021 | Hand-solvable two-mass modes and undamped eigenmode motion | Eigenvalues 1/6, mass orthogonality, eigenpair residuals and analytic cosine time trace |
| BENCH-VEH-0022 | Zero input, damped free response, sinusoidal steady response, smooth bump | Analytic complex dynamic-stiffness response initialized on its particular solution; passive energy and independently assembled total-force balance |
| BENCH-VEH-0023 | Time-step refinement and failure cases | Harmonic errors at dt=.1/.05/.025 s reduce by ratios 12–20; finite nonnegative dissipation; reject bad inputs and stop at contact/travel/domain loss without clipping |

The harmonic reference solves the scalar complex two-by-two forced system,
independent of RK4 and the production RHS. Closed-form free modes supply the
other trajectory reference. Energy and total-force checks are necessary
additional identities, not independent vehicle validation. A road step is not
used as a finite acceleration-peak truth case. Benchmark tolerances are declared
in the verification script/tests before inspecting results and must not be fitted
to failures. Near-zero convergence errors cannot establish an observed order.

## Source-data disposition and next dependency

The repo already records the reviewed 36 N/mm front and assumed 30–36 N/mm rear
spring law, mass/gravity reference and actuation geometry. The KW attachment is
catalogued with vendor plot sign conventions. Legacy LLTD inputs explicitly
include vertical tire stiffness. These are leads for a bounded native parameter
adapter, not grounds to label all data absent or substitute numerical values.

AUTH-SUSP-0015 concerns unavailable source-specific static gas/friction forces;
it does not prove that no velocity-dependent vendor/dyno data exists. Keep those
questions separate. This verification batch requires neither an installed
damper curve nor a native tire vertical parameter. After it passes, recover the
numeric tire/damper records behind the existing catalog references, verify units,
adjuster/state/domain and provenance, and define the native tangent adapter.
Native ride prediction, pitch/yaw inertia, nonlinear damping, ARB/body coupling,
component loads and physical correlation remain separate milestones.

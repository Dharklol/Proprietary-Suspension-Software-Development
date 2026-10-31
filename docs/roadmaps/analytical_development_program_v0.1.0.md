# Analytical development program v0.1.0

## Decision and authority

Owner direction on 2026-10-31: consolidate the current implementation, then
prioritize analytical work while hardware is unavailable for several months.
The [checkpoint](../reviews/analytical_development_consolidation_2026-10-31.md)
records current implementation, branch dependencies and unresolved claims.

This is a work plan, not a new physics authorization or a claim that the studies
below have passed. Use the existing AUTH-VEH-0012 development scope and explicit
source-owned inputs. Outputs remain uncorrelated, evidence-only and zero-weight.
No tire bias correction, unsupported interpolation/extrapolation, substituted
setup value, inverse-root selection or design ranking is introduced by this plan.

## 1. Consolidation exit

- Preserve the original PR review/dependency boundaries and newer main additions.
- Check the integrated registry, focused interfaces and broad regression suite.
- Reproduce the native/export/steering evidence with current providers and retain
  source hashes. Saved numerical states are seeds, not independent references.
- Keep exact snapshot mismatches under Python 3.12 separate from branch-caused
  regressions; Python 3.11 remains the existing CI environment.
- Record landing status honestly. A locally integrated tree or a green feature
  branch is not a merged main release.

## 2. Independent analytical checks

The initial straight-state source-table audit is implemented; see its
[review and numerical explanation](../reviews/straight_state_tire_force_audit_review.md).
It resolves the fixture's large opposing forces within the source/model chain,
not their physical adequacy. The [manufactured low-force reference](../reviews/analytical_low_force_reference_review.md)
now verifies the zero-alignment straight limit and small-angle steering,
sideslip and axle force responses. Initial native envelope and sensitivity
studies now sit alongside these manufactured references; their scope follows
below.

Write the expected result and acceptance rule before computing the comparison.
Do not use solver outputs as both the reference and the quantity under test.

| Question | Independent reference | Required distinction |
|---|---|---|
| Does motion follow the stated path? | Hand-derived r=V*kappa and steady acceleration in the declared heading frame, including nonzero sideslip | Kinematic identity versus tire/vehicle accuracy |
| Are total reactions consistent? | Sum of prescribed weights and applied vertical forces; explicit global force/moment sums from application points | Necessary balance versus correct load distribution |
| Is load-transfer sign and scaling sensible? | A separately specified ideal flat-road rigid-body fixture, with explicit CG height, track and permitted force assumptions | Total vehicle transfer versus elastic front/rear allocation; no imposed LLTD in the native solve |
| Does the linear low-force limit behave correctly? | A manufactured constant-stiffness planar bicycle case with an independently derived steady solution | Neutral/under/oversteer relation for that fixture versus native tire behavior |
| Is material-point work consistent? | Separate perturbations of a frozen upright material point and direct applied-wrench work | Material point versus moving geometric lowest point |
| Why do straight-state tire forces oppose each other? | Explicit source-table queries and controlled synthetic alignment cases | Toe/slip, inclination thrust, source bias, reflection and force projection |

The manufactured references are analytical verification fixtures, not fits to
WUFR output. If a reference needs a new provider or assumption beyond existing
scope, document that bounded addition before implementation. Preserve existing
physical force/moment acceptance limits; choose any new comparison tolerance
from discretization/convergence evidence rather than the observed residual.

### First investigation: straight-state force decomposition

1. Freeze and identify the current native fixture without altering setup.
2. Report all four wheel headings, center velocities, slip, inclination, Fz,
   pressure, local Fy and its heading-frame force components.
3. Query the existing tire provider at the same supported load/pressure with
   alpha=0 and/or gamma=0 where supported. Retain physical and transformed source
   queries. These are conditional tire probes, not re-equilibrated vehicle cases.
4. Report source bias and the direct/reflected seam separately. Do not assume
   additive linear camber/toe contributions in the nonlinear table.
5. Use a zero-alignment, unbiased manufactured tire fixture as an independent
   symmetry check. A changed native setup must be re-equilibrated and receive a
   distinct source/configuration identity rather than mutating the old state.

The output must explain the observed forces or identify a specific unresolved
convention, source or modeling issue before using these states for optimization.

## 3. Map the supported computational envelope

The first [native computational-envelope study](../reviews/native_computational_envelope_review.md)
is implemented with retained accepted/failed attempts in both directions.
Its original-bound search reaches magnitude 0.12 per metre and fails at the
tested 0.125 endpoint. Separate +/-0.10-rad sideslip-bound controls recover both
0.125 cases on the original source branch. The original +/-0.08-rad solver box
therefore excludes those recovered roots; the stopping point is not established
as a physical grip limit. Further numerical-control and physical-input
sensitivity remain separate next steps.

Continue in both turn directions from individually accepted states, increasing
curvature in declared steps at explicit speed/setup/pressure. Retain all failures
and stop each branch at its first unsupported transition. Refine the bracket
only while the same branch and source domain remain supported.

For each sample record wheel loads, body pose, rack, sideslip, all wheel slips
and inclination, local and global forces, holding force/power, source segments,
branch signatures, iteration count, numerical conditioning and independent
physical residuals. Report distances to source-domain and geometry bounds.

Classify outcomes separately: tire-domain boundary; geometric/contact boundary;
direct/reflected seam; tire branch transition; loss of numerical convergence;
physical closure rejection; or source/configuration mismatch. A failed solve
does not prove physical instability, wheel lift or a grip limit. This study is a
supported computational envelope, not maximum lateral acceleration prediction.

## 4. Sensitivity after the baseline explanation

The first [native sensitivity study](../reviews/native_sensitivity_study_review.md)
now records fourteen physical-case runs, six numerical root evaluations and
eight nontrivial off-root numerical recoveries. Pressure +/-1/+2 kPa and individual
front/rear ARB 1-to-2 changes are re-equilibrated in both directions. Wider
sideslip boxes, halved tangent steps and tighter nested contact roots recover the same local roots to the
declared comparison criterion. These remain small, explicitly scoped response
studies; broader input uncertainty and alignment/tire-assumption sensitivity
are not established by them.

Perturb one explicit supported input at a time: pressure and discrete ARB
settings first; alignment and spring reference only through reviewed setup
providers and distinct configuration identities. Do not add hidden setup knobs.

Use re-equilibrated states for coupled response. Compare +/- perturbations and
at least two step sizes for continuous derivatives where available; discrete
settings remain finite comparisons. Report derivatives only on a common smooth
branch away from the reflection seam and source knots/bounds. Otherwise report
one-sided or discrete results with the boundary identified. Failure is not zero
sensitivity. Preserve absolute changes and their units alongside normalized
values; do not normalize by a near-zero baseline.

The first output is a table of which responses are robust, input-sensitive or
unresolved over the declared perturbations. It does not assign uncertainty
probabilities without evidence and does not rank candidate steering geometries.

## 5. Resume criteria for design comparisons

Review the analytical discrepancies, supported envelope and sensitivities before
implementing varying-state optimizer targets. Then define the design question,
explicit operating cases, root/branch treatment, evaluation metric and candidate
re-equilibration requirements in a separate review. Start with a few controlled
candidates, not a broad search. Existing compliance/structural screens may be
compared under compatible prescribed inputs but may not silently become a
maneuver steering-effort model.

Physical correlation is intentionally deferred. Its eventual collection and
release requirements remain in the earlier roadmaps; no hardware measurements
are required to start sections 1–4 under their existing development scope.

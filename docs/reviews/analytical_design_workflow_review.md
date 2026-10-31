# First analytical design-comparison workflow

## Protocol fixed before evaluation

Owner instruction on 2026-10-31: implement configuration/case definition,
assumption sensitivity, controlled geometry comparisons and repeatable reporting.
Physical correlation remains deferred. This is an unranked, zero-weight
development comparison using the existing native solver and symmetric generator.

The versioned TOML plan freezes a provisional source reference: driver/no-fuel
306.17484975 kg, V=8 m/s, 68.9 kPa gauge, source spring reference, ARB 1/1 and
original solver bounds/acceptance. Nested contact precision is 1e-15 m for this
study only; original fixture defaults are unchanged. Five cases cover straight,
+/-0.06 and +/-0.10 per metre. These are analytical test cases, not a complete
endurance distribution or an owner-selected installed setup.

Three candidates use the original rack and +/-5 mm body-x offsets. The existing
role-resolved symmetric generator moves both inner joints and re-derives tie-rod
lengths to preserve center closure. Steering axes, outer pickups, suspension
hardpoints and rack travel bounds stay fixed. Packaging feasibility is unresolved.

All candidates are re-equilibrated at all five nominal cases. At both +/-0.10
states each candidate also receives six separate stresses: front side-local toe
+/-0.2 degrees, front top-out camber +/-0.5 degrees, and uniform lateral-force
gain 0.95/1.05. Total coverage is 51 solves. No combined stress, smooth derivative
or probability distribution is inferred.

Alignment perturbations create distinct wheel-reference profiles through the
existing zero-offset construction. Camber changes nominal wheel-center y/z as
well as plane orientation. This conceptual setup family does not represent a
physical shim or toe-adjuster mechanism. Rear alignment and suspension hardpoints
remain fixed. Every composed spring/ARB/gravity provider binds the same derived
configuration; numerical source values and source record IDs remain traceable.

The tire-gain wrapper first evaluates the unchanged R25B proxy/reflection provider,
retains its source force/query/provenance, then scales the returned lateral force.
It has a distinct revision and explicit analytical stress label. It is not new
measured tire data or a replacement negative-inclination model. The R25B-to-R20
proxy and negative-inclination reflection remain uncorrelated assumptions.

## Acceptance and comparison rules

Saved coordinates are source-verified seeds only. Every cell is solved using its
own configuration/geometry/setup/tire revisions. Newton and independent physical
force/moment gates remain unchanged. Failed cells retain diagnostics and supply
no response value. A candidate/reference pair must also share a continuation
branch. Reflection-seam or branch changes are incomparable rather than zero.

Descriptive metrics are rack demand, left-minus-right front heading, sideslip,
roll, four wheel reactions and virtual holder force. Heading split is not an
Ackermann percentage. Holder force is not steering effort. Each candidate is
compared with the original rack at the same case and stress. Effect ranges and
sign stability cover only the declared stresses; missing/incomparable coverage
prevents a stability conclusion. Explicit metric thresholds distinguish resolved
signs for reporting and do not claim physical accuracy or design superiority.
Separate assumption-response columns compare each stress to the same candidate
and operating case under nominal assumptions. They are not geometry effects.

## Reproduction and UI boundary

Run each declared candidate through `scripts/run_analytical_design_workflow.py`,
then combine all three using `scripts/package_analytical_design_workflow.py`.
README commands reproduce JSON, CSV, static SVG/PNG figures and an offline HTML
viewer. Candidate runs checkpoint every cell; CI preserves failures as artifacts.
The packager rejects missing/duplicate cells, mixed source plans, authority
promotion and failed cells masquerading as responses. Artifact manifests bind
the generated report to the inputs and rendering code.

The viewer filters solved evidence by case, stress and metric; it runs no physics
and needs no external JavaScript module. This is the first team-facing reporting
slice. Configuration forms, run controls and connection to the existing 3D viewer
are the next application-layer increment.

## Numerical precision closeout

The first Python 3.11 CI reference left-high case was rejected at contact
precision 1e-14 m: line search stalled at scaled residual 1.03454e-10 against
the unchanged 1e-10 gate. Its force/moment norms were 8.44e-10 N / 1.90e-9 N*m.
The complete failed record and artifact provenance are retained separately in
`benchmarks/vehicle/analytical_workflow_rejected_ci_case_v0.1.0.json`.
This historical attempt remains rejected. The intermediate 5e-15 m control also
fails; changing the study-wide nested precision to 1e-15 m permits convergence.

Before rerunning the matrix, compare the exact CI case at contact precision
1e-15 and 5e-16 m on Python 3.11 and 3.12. Both must satisfy original solver and
physical gates, retain the source branch, and agree within the previously used
1e-5 scaled-coordinate numerical comparison criterion. This isolates evaluation
precision without promoting it to a physical accuracy claim. The final full
matrix must be regenerated under the single declared 1e-15 m control.

## Prior local result — superseded precision

The following result uses the original 1e-14 m study control; the final 1e-15 m
matrix is being regenerated. Its source-bound files retain the original plan.
All 51 local Python 3.12 cases pass. Maximum independent force and moment norms
are 9.60e-8 N and 2.58e-8 N*m; the maximum scaled residual is 9.35e-11 against
the unchanged 1e-10 gate. The compact source-bound reference is
`benchmarks/vehicle/analytical_design_workflow_summary_v0.1.0.json`. The committed
[offline viewer](../reports/analytical_design_workflow_v0.1.0/index.html), CSV
and SVG figures are reproducible outputs. CI regenerates the full kernel/tire
records separately on Python 3.11; live PR checks determine its current status.

At the two higher-curvature states, each rack candidate's demand and front-split
effect retains its sign across the seven declared assumptions. The absolute
rack-demand effect is 0.0832–0.0855 mm; signed heading-split changes have magnitude
0.0326–0.0341 degrees. These local sign results do not establish packaging
feasibility, a preferred geometry, real steering effort or robustness outside
the tested cases and one-at-a-time stresses.

For the reference geometry, the largest rack-demand changes across each pair
of stress signs and turn directions are:

| Declared stress | Rack change (mm) | Front heading-split change (deg) |
|---|---:|---:|
| Front toe +/-0.2 deg | 0.0523 | 0.3786 |
| Front camber +/-0.5 deg | 0.0206 | 0.00489 |
| Lateral-force gain 0.95/1.05 | 0.00616 | 0.00466 |

Perturbation sizes have different physical meanings and are not uncertainty
intervals. Toe directly changes the nominal heading split, so its larger split
response does not by itself measure a handling advantage. The finding supports
keeping alignment explicit before attributing a small split change to geometry.

Validation includes 11 new contract/reporting tests and 39 adjacent regressions,
registry validation, static rendering and browser checks for case/stress/metric
selection, failure visibility, rejected invalid JSON, download/reopen, desktop
layout and a 390-pixel viewport without document overflow.

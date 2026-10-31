# First analytical design-comparison workflow

## Protocol fixed before evaluation

Owner instruction on 2026-10-31: implement configuration/case definition,
assumption sensitivity, controlled geometry comparisons and repeatable reporting.
Physical correlation remains deferred. This is an unranked, zero-weight
development comparison using the existing native solver and symmetric generator.

The versioned TOML plan freezes a provisional source reference: driver/no-fuel
306.17484975 kg, V=8 m/s, 68.9 kPa gauge, source spring reference, ARB 1/1 and
original solver bounds/acceptance. Nested contact precision is 1e-14 m for this
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

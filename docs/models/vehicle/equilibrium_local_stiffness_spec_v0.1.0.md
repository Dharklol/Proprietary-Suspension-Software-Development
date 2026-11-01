# Equilibrium local spring stiffness study v0.1.0

Owner direction 2026-10-31 authorizes equilibrium-based analytical calculations
where source data supports them. Reuse AUTH-VEH-0010's unchanged static solver
and its physical closure checks, with explicit front/rear ARB settings 1/1 as a
study scenario, not a recommended or installed setting. Then evaluate the existing
EQ-SUSP-0038 local spring tangent at each solved physical wheel coordinate rather
than nominal CAD q=0. The original native derivative algorithm, h=.001/.0005 m
checks, and independent spring-energy second derivative checks remain unchanged.

The derivative is with respect to each wheel's body-vertical coordinate holding
the body fixed. It is a spring-only local constitutive tangent, not the complete
body heave/pitch stiffness matrix. ARB terms, compatible geometry, gravity and
coordinate transport belong in that later coupled matrix and must not be silently
omitted from a modal prediction. No pitch inertia is required for this calculation.
The static solution uses rigid road contact; no tire deflection equilibrium is
invented from legacy scenario tire rates. All source exclusions remain explicit.

Require the unchanged static solve to succeed with complete included-load road
reaction and physical force/moment closure. Preserve solver residuals, coordinates,
contact loads and closure values. Require all four local derivative/energy checks
to pass at solved coordinates. Report any failure instead of substituting the
nominal state. No vehicle natural frequency or installed dynamic authority.

Pitch inertia source audit: repository search and Box searches for mass properties
and inertia did not identify a usable sprung-body CG pitch-axis mass moment.
Historical OptimumG motion/force workbooks (Box 1577269207147 and 1582602328274)
contain total masses and pitch compliance gradients, not an identified native
sprung pitch inertia. Static corner weights/CG do not determine a second mass
moment. No rectangular-body or point-at-CG inertia is assumed. Testing telemetry
is deferred unless a separate identifiable dynamic experiment is justified.

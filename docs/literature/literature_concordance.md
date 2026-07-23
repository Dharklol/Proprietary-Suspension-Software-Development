# Literature Concordance

**Status:** Active inventory. Equation-level citations and applicability references are populated first for the steering vertical slice and remain open for other subsystems.

| Source | Primary audit role | Initial status |
|---|---|---|
| Guiggiani, *The Science of Vehicle Dynamics* | Definitions, wheel/tire kinematics, slips, equilibrium, suspension analysis, handling maps, telemetry-derived channels | Primary reference |
| Pacejka, *Tyre and Vehicle Dynamics* | Tire force/moment models, load sensitivity, combined slip, relaxation and transient tire behavior | Primary reference |
| Gillespie, *Fundamentals of Vehicle Dynamics* | Fundamental longitudinal, lateral, ride, roll, steering, and compliance decompositions | Primary reference |
| Milliken & Milliken, *Race Car Vehicle Dynamics* | Race-car application, tire-data use, handling diagrams, setup sensitivities, racing terminology | Primary reference |
| Katz, *Race Car Aerodynamics* | Aerodynamic forces, moments, balance, and vehicle-dynamics coupling | Supporting reference |
| Royce, *Learn & Compete* | Formula-car design process and practical competition context | Supporting reference |
| Segers, *Analysis Techniques for Racecar Data Acquisition* | Telemetry quality, channel processing, correlation, and analysis workflows | Supporting reference |
| Deakin et al., chassis-stiffness paper | Coupled front/chassis/rear torsional model and handling-balance sensitivity | Specialized reference |
| Romano, *Multi-Body Modelling and Mechanical Analysis of a Steering System* | Steering mechanism definitions, steering-ratio functions, configuration comparison, and external multibody validation workflow | Specialized reference |
| Hooke & Jeeves, “Direct Search Solution of Numerical and Statistical Problems” | Transparent derivative-free coordinate-pattern search lineage for the first deterministic optimizer baseline | Numerical-method reference |
| Lewis, Torczon & Trosset, “Direct Search Methods: Then and Now” | Direct-search method context, scaling, convergence limitations, and benchmark expectations | Numerical-method reference |
| Third-Order QSS paper | Candidate event/state-quantized transient integration backend | Research reference |
| Huang et al., *Find Optimal Suspension Kinematics Targets for Vehicle Dynamics Using Reinforcement Learning* | Inverse target generation, high-dimensional search, learned-policy reuse, and the distinction between target achievement and physical packaging feasibility | Research reference |
| Quantum-enhanced RL for Newton-Raphson convergence | Learned/quantum-inspired nonlinear-solver initialization; classical solver remains authoritative | Research reference |

## Steering geometry and inverse-design focus

For `MIG-STR-0001`, `MOD-STEER-0001`, and `MOD-STEER-0002`, the literature review distinguishes:

- ideal low-speed Ackermann geometry from the best race-car steering geometry;
- trapezoidal tie-rod linkage behavior from a target inner/outer curve;
- steering-wheel angle, pinion angle, rack displacement, and left/right road-wheel angles;
- static toe, dynamic toe, and suspension-induced steering geometry error;
- one nominal steering ratio from local and secant ratio functions;
- rigid kinematics from loaded/compliant steering response;
- geometric target selection from later tire-force-informed optimization;
- a verified mechanism evaluator from the optimization method that proposes candidates;
- kinematic target achievement from physical packaging and manufacturing feasibility.

### Exact rigid steering basis

- Guiggiani, Chapter 3, especially Sections 3.4.1 through 3.4.3, supports the exact Ackermann construction, nonideal/best steering geometry, and the importance of relative tire slips. This supports using Ackermann as a reference or selectable target rather than a universal optimum.
- Gillespie, Chapter 8, supports rack-and-pinion and trapezoidal steering-linkage geometry, steering ratio, and steering geometry errors. This supports direct mechanism evaluation across the full input domain instead of a single scalar ratio or polynomial replacement.
- `EQ-STEER-0001` through `EQ-STEER-0007` retain the equation-level citations, definitions, and validity limits. `MOD-STEER-0002` must call `MOD-STEER-0001` and may not introduce alternate steering equations.

### Configuration comparison and staged validation

- Romano, Chapters 2 and 4, treats Ackermann and steering ratio as functions, compares steering configurations through steer-angle/ratio behavior, and validates the steering assembly before applying it in suspension and full-vehicle tests. This supports the sequence analyzer -> candidate comparison -> suspension-state integration -> full-vehicle/physical correlation.

### Deterministic numerical baseline

- Hooke and Jeeves (1961) provides the direct-search lineage for exploratory coordinate moves without analytical objective derivatives. The implemented method is a bounded normalized coordinate-pattern baseline rather than a claim of exact reproduction of every historical Hooke-Jeeves step.
- Lewis, Torczon, and Trosset (2000) provides broader direct-search context and reinforces the need to state scaling, polling directions, step contraction, termination, and convergence limitations. `bounded_coordinate_pattern_search_v0.1.0` records each of these controls and treats fixed-seed repeatability as a benchmark requirement.
- The first search method is deliberately transparent and dependency-free. It is a comparison baseline for future local constrained, global, mixed-discrete, surrogate-assisted, or learned methods. No future method may receive a lower verification burden merely because it finds a smaller objective.

### Optimization and feasibility

- Huang et al. (2026), Section 2.1.1, states that generated suspension-kinematics target files do not guarantee a physically feasible suspension and that packaging must be considered with target setup. The steering workflow therefore treats mechanism, packaging, articulation, and manufacturing feasibility as explicit constraints rather than assuming that a low target error is a valid design.
- Huang et al. motivates reusable learned policies for later high-dimensional target generation, but it does not remove the need for a deterministic, verified reference optimizer and a physically authoritative mechanism evaluator. Learned or reinforcement-learning methods remain a later research layer that must be compared against the deterministic baseline.
- Milliken and Pacejka remain the primary sources for later tire-informed operating targets, load sensitivity, combined slip, and handling tradeoffs. Those models enter through the target-provider interface and do not alter the rigid mechanism equations.

## Review rules

1. No single source is the universal authority for all subsystems.
2. Disagreements in definitions or assumptions are recorded rather than silently resolved.
3. Textbook equations are checked against their derivation and validity range before implementation.
4. Team equations require a derivation, independent check, and benchmark burden equivalent to external models.
5. Literature citations belong in equation and model records, not only in this overview.
6. Optimization algorithms require method-level references, scaling, initialization, convergence, failure, repeatability, and benchmark documentation.
7. A successful optimizer objective does not override failed physical or geometric constraints.

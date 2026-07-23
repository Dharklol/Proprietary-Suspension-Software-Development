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
| Fornberg, “Generation of Finite Difference Formulas on Arbitrarily Spaced Grids” | Finite-difference derivative formulation and numerical-method lineage for local sensitivity | Numerical-method reference |
| Saltelli et al., *Global Sensitivity Analysis: The Primer* | Distinction between local derivative sensitivity and broader uncertainty-based/global sensitivity | Numerical-method reference |
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
- kinematic target achievement from physical packaging and manufacturing feasibility;
- local derivative sensitivity from tolerance, uncertainty, and global sensitivity;
- an unavailable physical constraint from a passed physical constraint;
- a suspension-pose provider from the steering mechanism solution that consumes the pose; and
- a report-only suspension state from a state carrying an explicit optimization target and weight.

### Exact rigid steering basis

- Guiggiani, Chapter 3, especially Sections 3.4.1 through 3.4.3, supports the exact Ackermann construction, nonideal/best steering geometry, and the importance of relative tire slips. This supports using Ackermann as a reference or selectable target rather than a universal optimum.
- Gillespie, Chapter 8, supports rack-and-pinion and trapezoidal steering-linkage geometry, steering ratio, and steering geometry errors. This supports direct mechanism evaluation across the full input domain instead of a single scalar ratio or polynomial replacement.
- `EQ-STEER-0001` through `EQ-STEER-0007` retain the equation-level citations, definitions, and validity limits. `MOD-STEER-0002` must call `MOD-STEER-0001` and may not introduce alternate steering equations.

### Suspension-state steering and toe

- Gillespie's vehicle-dynamics terminology defines static toe at a specified wheel load or relative wheel-center position with respect to the sprung mass. Toe therefore belongs to a named suspension state rather than to one geometry-independent scalar when suspension motion is being evaluated.
- Gillespie, Chapter 8, `Steering Geometry Error`, states that suspension motions can create steering action because the body-mounted relay/tie-rod linkage and wheel steering arm follow different paths. Its `Toe Change` and `Roll Steer` subsections explicitly discuss toe and steer changes with jounce, rebound, and body roll. This supports evaluating closure and heading at each declared suspension state rather than applying a nominal correction after the fact.
- Guiggiani, Section 3.14.6, writes the wheel steer angles as functions of driver steer and suspension roll angle when roll steer is present (`delta_ij = delta_ij(delta_v, phi_is)`) and Eq. (3.210) combines static toe, steering ratio, dynamic-toe/Ackermann, and roll-steer terms. Chapter 7 carries that state dependence into handling analysis. This supports indexing steering response by suspension state.
- The first pose-provider contract represents the upright reference pose with the steering degree of freedom unresolved. Steering-axis position/orientation, wheel-plane reference, and upright-bound pickup points may move with suspension state, while tie-rod closure remains the responsibility of `MOD-STEER-0001`. A source that already includes tie-rod-induced toe or bump steer is validation/comparison evidence and cannot be fed back into the steering closure solver as though it were an unsteered pose.
- The pose-provider layer is source-agnostic. An OptimumK export, CAD motion export, lookup table, or future native suspension solver may supply the same canonical zero-steer pose contract after its frame, state coordinates, assumptions, and authority are reviewed.

### Operating-state steering targets

- Guiggiani, Section 3.4.2, states that selecting the best steering-geometry coefficients is not easy because static and dynamic toe affect both tire slips/lateral-force values and the directions of the lateral forces. Section 3.4.3 further shows that the relative front-tire slip angles depend on the position of the vehicle velocity center and discusses different steering-geometry tendencies for race-car versus lower-lateral-acceleration operation. This supports a target-provider architecture rather than one permanent Ackermann percentage.
- Because Guiggiani's steering response may depend on suspension roll and because Gillespie ties steering-geometry error to wheel travel, a multi-state optimizer must identify which suspension states actually carry performance targets. `P1-STR-006C` therefore requires an explicit target role, state weight, sample weights, normalization, convention adapter, source, and authority. A state omitted from the target list is report-only by declared policy; the nominal target is never silently copied to another pose.
- The current state-weighted scalar is a team optimization aggregation, not a vehicle-dynamics law from the literature. Its equation, normalization, and weights are documented and benchmarked directly. Future tire/vehicle models may replace the synthetic or manually authored targets, but they must preserve state-level objective contributions and provenance rather than hiding the operating envelope in one score.
- Milliken and Pacejka remain the planned primary bases for later tire-informed operating targets, load sensitivity, combined slip, and handling tradeoffs. Their future target-generation layer supplies requested wheel headings/relations and operating-state weights; it does not alter the rigid steering equations.

### Configuration comparison and staged validation

- Romano, Chapters 2 and 4, treats Ackermann and steering ratio as functions, compares steering configurations through steer-angle/ratio behavior, and validates the steering assembly before applying it in suspension and full-vehicle tests. This supports the sequence analyzer -> candidate comparison -> suspension-state integration -> operating-state objectives -> full-vehicle/physical correlation.

### Deterministic numerical baseline

- Hooke and Jeeves (1961) provides the direct-search lineage for exploratory coordinate moves without analytical objective derivatives. The implemented method is a bounded normalized coordinate-pattern baseline rather than a claim of exact reproduction of every historical Hooke-Jeeves step.
- Lewis, Torczon, and Trosset (2000) provides broader direct-search context and reinforces the need to state scaling, polling directions, step contraction, termination, and convergence limitations. `bounded_coordinate_pattern_search_v0.1.0` records each of these controls and treats fixed-seed repeatability as a benchmark requirement.
- `P1-STR-006C` reuses the same search method and changes only the candidate-evaluation adapter from one nominal target to an explicit sum of state-level objective terms. A lower multi-state score does not receive a new or weaker numerical verification standard.
- The first search method is deliberately transparent and dependency-free. It is a comparison baseline for future local constrained, global, mixed-discrete, surrogate-assisted, or learned methods. No future method may receive a lower verification burden merely because it finds a smaller objective.

### Local sensitivity and uncertainty boundary

- Fornberg (1988) provides the finite-difference numerical-method lineage used by `bounded_finite_difference_v0.1.0`. The implementation uses bounded central differences when possible and one-sided differences at requirement-set bounds. Every perturbation is reevaluated through the authoritative analyzer rather than through a local response surrogate.
- Saltelli et al. (2008) distinguishes local derivative information from broader sensitivity analysis over uncertain input distributions. The current steering result is therefore described only as local sensitivity. It cannot be promoted to manufacturing tolerance, probabilistic uncertainty, worst-case robustness, or global sensitivity without a reviewed uncertainty model and additional methods.
- Candidate design-distance filtering is a team comparison method rather than a physical or optimization theorem. Its normalization, distance equation, threshold, and non-Pareto authority boundary are documented and benchmarked directly.

### Optimization and feasibility

- Huang et al. (2026), Section 2.1.1, states that generated suspension-kinematics target files do not guarantee a physically feasible suspension and that packaging must be considered with target setup. The steering workflow therefore treats mechanism, packaging, articulation, and manufacturing feasibility as explicit constraints rather than assuming that a low target error is a valid design.
- A physical constraint becomes active only when its geometry, limit, evaluated state, and authority are available. Rod-end articulation, thread engagement, clearances, and installed stops remain unavailable in the development provider because the repository does not yet contain the required reviewed inputs. Their absence is not evidence of passing.
- Huang et al. motivates reusable learned policies for later high-dimensional target generation, but it does not remove the need for a deterministic, verified reference optimizer and a physically authoritative mechanism evaluator. Learned or reinforcement-learning methods remain a later research layer that must be compared against the deterministic baseline.

## Review rules

1. No single source is the universal authority for all subsystems.
2. Disagreements in definitions or assumptions are recorded rather than silently resolved.
3. Textbook equations are checked against their derivation and validity range before implementation.
4. Team equations require a derivation, independent check, and benchmark burden equivalent to external models.
5. Literature citations belong in equation and model records, not only in this overview.
6. Optimization algorithms require method-level references, scaling, initialization, convergence, failure, repeatability, and benchmark documentation.
7. A successful optimizer objective does not override failed physical or geometric constraints.
8. Missing physical inputs remain unavailable; they are never converted into zero margin, infinite margin, or an automatic pass.
9. Local sensitivity, tolerance propagation, robustness, and global sensitivity are separate claims with separate input and verification burdens.
10. Suspension-state inputs must state whether steering/tie-rod closure is already included; a pose that already contains steering response cannot be reused as an unresolved steering input.
11. Operating-state target weights and aggregation rules are explicit team/model inputs unless a reviewed higher-level provider supplies them; no historical or nominal target is silently inherited by another pose.

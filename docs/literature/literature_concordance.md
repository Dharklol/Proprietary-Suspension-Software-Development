# Literature Concordance

**Status:** Initial inventory. Equation-level citations and page references remain to be populated during the audit.

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
| Multi-body steering-system thesis | Steering mechanism definitions, steering ratio as a function, motion-study comparison, and external multibody validation workflow | Specialized reference |
| Third-Order QSS paper | Candidate event/state-quantized transient integration backend | Research reference |
| Suspension-kinematics reinforcement-learning paper | Learned inverse design and reusable optimization policies | Research reference |
| Quantum-enhanced RL for Newton-Raphson convergence | Learned/quantum-inspired nonlinear-solver initialization; classical solver remains authoritative | Research reference |

## Steering geometry audit focus

For `MIG-STR-0001` and `MOD-STEER-0001`, the literature review must distinguish:

- ideal low-speed Ackermann geometry from the best race-car steering geometry;
- trapezoidal tie-rod linkage behavior from a target inner/outer curve;
- steering-wheel angle, pinion angle, rack displacement, and left/right road-wheel angles;
- static toe, dynamic toe, and suspension-induced steering geometry error;
- one nominal steering ratio from local and secant ratio functions;
- rigid kinematics from loaded/compliant steering response;
- geometric target selection from later tire-force-informed optimization.

Initial source directions:

- Guiggiani, Chapter 3, especially steering geometry, Ackermann kinematics, best steering geometry, and relative tire slip angles;
- Gillespie, Chapter 8, especially rack-and-pinion linkage, Ackermann geometry, trapezoidal tie-rod arrangements, and steering geometry errors;
- the multi-body steering thesis, Chapters 2–4, for terminology, steering-ratio curves, motion studies, and comparison of steering configurations;
- Milliken and Pacejka for tire-informed race-car operating targets and effective axle behavior.

## Review rules

1. No single source is the universal authority for all subsystems.
2. Disagreements in definitions or assumptions are recorded rather than silently resolved.
3. Textbook equations are checked against their derivation and validity range before implementation.
4. Team equations require a derivation, independent check, and benchmark burden equivalent to external models.
5. Literature citations belong in equation and model records, not only in this overview.
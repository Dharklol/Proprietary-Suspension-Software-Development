# Phase 1 steering R&D architecture closeout

## Scope of this closeout

This closeout records the end of the current steering-focused R&D implementation sequence. It does **not** close physical steering validation, hardware release, rack-load/effort authority, manufacturing tolerance/robustness, or installed-system correlation.

The R&D architecture is considered feature-complete because the steering mechanism evaluator and inverse-design layer can now consume the upstream state information required for higher-fidelity targets without embedding suspension, tire-force, load-transfer, or vehicle-equilibrium physics inside steering.

## Completed architecture

The implemented stack now includes:

- one deterministic rigid steering analyzer (`MOD-STEER-0001`);
- role-driven parametric steering geometry generation and deterministic inverse design (`MOD-STEER-0002`);
- explicit constraint, infeasibility, sensitivity, and candidate-comparison reporting;
- provider-neutral zero-steer suspension poses and multi-state steering evaluation;
- an external rigid-pose exchange adapter;
- operating-state and scalar dynamic-toe/rack-gain target aggregation;
- a source-preserving R25B lateral summary with explicit 43105 R25B source / 43104 R20 intended identities;
- explicit vehicle/wheel operating-state exchange (`MOD-VEH-0001`);
- bounded pre-peak `|Fy| -> |alpha_required|` inversion;
- a source-specific processed R25B Cornering Trojan exporter path;
- exact planar wheel-center velocity and tire-slip geometry (`MOD-VEH-0002`);
- motion-aware steering target composition using `delta_target = beta_hat + alpha_required`.

## Key engineering conclusion

Pro-, parallel-, or anti-Ackermann is not treated as a global tire property. The tire-required slip difference and the vehicle wheel-center velocity-heading difference are separate quantities. The motion-aware benchmark demonstrates that identical synthetic tire force/slip demands can produce different final steering regimes when only the supplied vehicle velocity field changes.

This establishes the correct software boundary but does not identify the WUFR-27 optimum. That requires synchronized real suspension, tire, wheel-load/force-demand, and body-motion states.

## Source and authority limits

The following remain explicit gates:

- the actual processed R25B binary source must still be executed through the reviewed exporter before real intermediate `Fy(alpha)` branches are frozen;
- no reviewed machine-readable WUFR zero-steer upright transform series is yet the steering pose authority;
- current spreadsheet load states are development evidence, not production vehicle-state authority;
- no reviewed WUFR `(u,v,r)` schedule currently exists for motion-aware steering ranking;
- synthetic benchmarks prove software composition and limiting cases only;
- installed free play, compliance, stops, sensor calibration, and as-built geometry remain physical-correlation work.

## R&D disposition

Major steering-only feature development is paused. Further work should occur only when an upstream model or new physical evidence materially changes the steering decision.

The next primary R&D vertical slice is suspension kinematics, followed by a quasi-static load-state generator, reusable steady-state tire model, and steady-state vehicle trim/QSS. Lap simulation is intentionally deferred until those subsystem models exist independently.

The detailed sequence and visualization/tooling policy are recorded in:

`docs/roadmaps/post_steering_rnd_program_v0.1.0.md`

## Resume conditions

Resume major steering R&D when one or more of the following are reviewed and available:

- WUFR suspension pose authority;
- representative synchronized wheel loads/camber/pressure/Fy demand;
- source-derived R25B force branches at needed operating points;
- reviewed vehicle motion states;
- measured installed rack-to-wheel/backlash/compliance behavior;
- hardware or effort constraints that alter candidate feasibility.

# Steering R&D figure suite v0.1.0

## Purpose

This suite is the first model-specific consumer of the provider-neutral `pssd_viz` layer introduced by PR #35. It converts existing steering/tire/vehicle benchmark outputs into static engineering evidence without adding another steering, tire, suspension, or vehicle solver.

The figure generator is `scripts/run_steering_figure_suite.py`. Every artifact is emitted as SVG and PNG with an adjacent machine-readable figure manifest and SHA-256 hashes. The grouped `report.manifest.json` is the suite index.

## Figures

### FIG-STEER-RND-001

WUFR steering baseline response versus the frozen WUFR-26/27 historical design-source target. The target is the existing historical regression source and the evaluated curves come from `MOD-STEER-0001` at the retained WUFR-27 development baseline.

This is nominal design-source comparison only. It is not installed-state validation and does not include backlash, compliance, fabrication error, or physical stops.

### FIG-STEER-RND-002

Evaluated-minus-target residual for FIG-STEER-RND-001. This exposes small differences that can be visually hidden when target and evaluated curves overlap.

### FIG-STEER-RND-003

Historical steering target compared with the bounded R25B peak-slip-informed development target from BENCH-STEER-0020. Source tire identity remains Hoosier 43105 R25B and intended tire identity remains Hoosier 43104 R20.

The reference inside/outside loads, camber, pressure, and slip-utilization schedule are development inputs. The plot is useful for showing the direction and magnitude of the tire correction, but it is not a production tire-optimal steering target.

### FIG-TIRE-RND-001

The explicit synthetic monotonic pre-peak `|Fy|` versus `|alpha|` branches used by BENCH-STEER-0021/0023 to verify bounded force-demand inversion and motion-aware composition. The plot is intentionally labeled as synthetic software evidence and must not be interpreted as R25B/R20 tire behavior.

### FIG-TIRE-RND-002

An explicit unavailable-source figure for real R25B source-derived pre-peak `Fy(alpha)` branches. Until the hashed Cornering Trojan/raw TTC source is run through the reviewed exporter and the resulting branch values are frozen, the report must show the source gate rather than an inferred or blank curve.

### FIG-STEER-RND-004

The BENCH-STEER-0023 same-tire-demand velocity-center comparison. Required tire slips are held fixed while the supplied planar velocity-center state changes. The resulting wheel-heading pair changes from pro-Ackermann to anti-Ackermann in the synthetic benchmark, demonstrating that absolute steering regime depends on vehicle motion as well as tire slip requirement.

This is software/kinematic evidence only and not a WUFR handling prediction.

## Architecture boundary

The model-specific orchestration script may call reviewed upstream evaluators and benchmark reporters to obtain solved values. `pssd_viz.steering_figures` only packages already-computed values and simple report residuals into `EngineeringFigureSpec` objects.

No model-specific figure builder is allowed to:

- solve tie-rod closure;
- infer suspension motion;
- fit or extrapolate a tire curve;
- calculate vehicle equilibrium;
- silently replace missing data;
- promote synthetic/development authority to production authority.

Missing source data must remain an explicit unavailable figure.

## Next visualization work

The next visualization slice should add the scene interchange contract and lightweight 3D steering proof-of-concept. The static figure suite remains the engineering-evidence path; the interactive viewer is for understanding and debugging rather than the sole record of a design decision.

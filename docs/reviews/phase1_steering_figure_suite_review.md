# Phase 1 steering R&D figure-suite review

## Scope

This review covers the first model-specific static-report consumer of `pssd_viz` after the visualization foundation. It does not authorize new physics.

## Reviewed implementation

- `src/pssd_viz/steering_figures.py`
- `scripts/run_steering_figure_suite.py`
- `tests/test_steering_figure_suite.py`
- `.github/workflows/visualization-validation.yml`
- `docs/visualization/steering_rnd_figure_suite_v0.1.0.md`

## Accepted boundaries

1. Steering/tire/vehicle values originate from existing reviewed evaluators, providers, fixtures, or benchmark reporters.
2. Figure builders perform only data packaging and explicit report transformations such as evaluated-minus-target residuals or alternate-minus-baseline target corrections.
3. Synthetic tire-force branches remain visibly synthetic.
4. The source and intended tire identities remain separate wherever R25B development data are shown.
5. A requested real R25B `Fy(alpha)` figure is rendered as explicitly unavailable until source-derived branch values are frozen.
6. No figure is accepted as installed-state or production authority solely because it renders successfully.
7. Static SVG/PNG plus manifests remain the engineering-evidence path; later interactive 3D visualization must not replace reproducible reports.

## Figure set

- `FIG-STEER-RND-001`: baseline response vs historical design-source target.
- `FIG-STEER-RND-002`: baseline response residual.
- `FIG-STEER-RND-003`: historical target vs R25B peak-slip-informed development target.
- `FIG-STEER-RND-005`: direct R25B target correction relative to historical target.
- `FIG-TIRE-RND-001`: synthetic force-demand inversion branches.
- `FIG-TIRE-RND-002`: explicit unavailable real R25B force-branch figure.
- `FIG-STEER-RND-004`: synthetic motion-aware velocity-center sensitivity.

## Promotion rule

This suite may be used in the R&D PDR to explain the implemented software and current evidence boundary. The synthetic or development figures do not establish a production-optimal Ackermann target, physical tire curve, installed steering response, or whole-vehicle handling result.

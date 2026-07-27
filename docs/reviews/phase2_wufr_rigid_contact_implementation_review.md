# Phase 2 WUFR rigid-contact implementation review

## Scope

PR #67 implements `MOD-VEH-0006` under merged `AUTH-VEH-0008` using only the active `ASM-VEH-0005` / `EQ-VEH-0014` ideal rigid circular centerline tire.

The implementation composes:

- `MOD-SUSP-0002` for physical wheel-center vertical state and wheel-plane pose;
- `MOD-STEER-0001` for front centered-rack steering closure;
- `MOD-VEH-0003` for WUFR body/road frames and point transport;
- `MOD-VEH-0005` for explicit 5 kg/corner prototype unsprung gravity point loads.

It supplies the road-compatible wheel map and derivatives required later by `MOD-VEH-0004`, but it does not solve or publish WUFR road reactions.

## Contact geometry

The runtime contact point is evaluated in the current road frame from the current physical wheel center and fully solved wheel-plane normal:

`v = n_R - (n_R dot n_w) n_w`

`e = v / ||v||`

`r_cp = r_wc - R e`

The only runtime tire radius is loaded from `WUFR26_OPTIMUMK_WHEEL_REFERENCE_V0`; the implementation contains no second literal/fitted radius. The historical OptimumK `Contact Patch` channel is not runtime geometry and rejected `ASM-VEH-0004` has no fallback path.

## Numerical behavior

Each corner solves the flat-road condition in the physical wheel-center vertical coordinate on the reviewed local suspension/steering branch. The solver samples and brackets without coordinate clipping and rejects missing, multiple, or failed roots.

`J_wb`, contact coefficients, and wheel-center gravity projections use centered two-step finite differences. Provider perturbation failures propagate rather than causing an undeclared one-sided derivative. Contact and gravity scalar projections use second-order two-step extrapolation after the coarse/fine convergence gate.

The contact/gravity benchmark requires the final physical-point virtual-work result to agree at the `1e-6 N` level. The outer `MOD-SUSP-0002` wheel-coordinate inversion therefore uses `1e-14 m` displacement residual and `2e-14 rad` bracket-angle tolerances in this provider. These are numerical inversion tolerances only: they do not assert physical geometry accuracy or installed measurement precision. Their purpose is to keep the inversion residual well below the finite-difference derivative scale rather than letting root-solver noise determine the virtual-work result.

## Verification gates

`BENCH-VEH-0010` checks the pure circular geometry independently of the road solver: radius, wheel-plane membership, road-normal minimization, wheel-normal sign invariance, nominal WUFR formula outputs, degeneracy handling, and excluded tire inputs.

`BENCH-VEH-0009` checks nominal and nonzero road roots, body-to-wheel Jacobian convergence, contact virtual work, unsprung-gravity point-potential consistency, centered-rack front steering activity, and structured out-of-domain failure.

The CI benchmark script `scripts/run_wufr_road_contact_benchmarks.py` emits the exact numerical state used for result freezing.

## Authority boundary after merge

A successful PR #67 closes the WUFR rigid-road compatibility provider at design-intent R&D fidelity. It does **not** establish:

- loaded tire radius or tire vertical compliance;
- finite tread/contact-patch behavior;
- installed/as-built suspension, tire, mass, spring-preload, or ARB-preload authority;
- static road-reaction, crossweight, LLTD, or load-transfer authority;
- correlation to the not-yet-built WUFR-27 car.

The next whole-vehicle step, if taken, must be a separate authorization to compose springs + Z-bar + gravity + this compatibility map through the generic QSS kernel. Such a result should remain explicitly uncorrelated design-intent output until WUFR-27 on-car data exist.

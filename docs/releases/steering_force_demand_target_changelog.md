# Steering force-demand target changelog

## v0.1.0 — PR #30

- adds `pssd_tire.force_demand` explicit monotonic pre-peak lateral-force branch exchange/inversion contract;
- adds bounded `|Fy| -> |alpha|` interpolation with no force extrapolation and no operating-point interpolation in the first version;
- adds `pssd_steering.optimization.force_demand_targets` and explicit pro/parallel/anti-Ackermann classification;
- applies `alpha_out - alpha_in` only as a correction to the existing exact Ackermann outside reference while preserving the base inside-wheel trajectory;
- freezes the PR #28 R25B diagnostic showing the +1.3 deg peak-slip differential points toward anti-Ackermann but remains far smaller than the ~9.316 deg full-steer geometric Ackermann split;
- records that the already-merged PR #28 target crosses slightly anti-Ackermann at the +/-15 deg input sample despite remaining pro at its endpoints;
- adds a clearly synthetic force-response branch fixture demonstrating mixed anti/pro regime behavior as steering angle changes;
- inventories the real R25B raw TTC, processed MAT, fitted TIR, and MATLAB source path required for a later physical branch export;
- closes PR #29 `AUTH-VEH-0001`, `MOD-VEH-0001`, and `BENCH-VEH-0001` merge governance;
- introduces supplemental `AUTH-STEER-0003` for the bounded force-demand steering target layer;
- adds `BENCH-STEER-0021`, unit tests, benchmark reporting, and CI artifact generation;
- does not add vehicle equilibrium, load transfer, a Magic Formula rewrite, combined slip, track scaling, or WUFR production steering authority.

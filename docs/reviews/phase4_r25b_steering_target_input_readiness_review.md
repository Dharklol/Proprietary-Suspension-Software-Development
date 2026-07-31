# R25B steering-target input readiness review

## Decision boundary

The exact R25B pure-lateral runtime, named pre-peak branches, and the two-state steering magnitude handoff are now available. This review asks only whether the current WUFR vehicle-state evidence can supply a source-backed steering force-demand target without inventing missing quantities.

It cannot.

## Sources reviewed

- `benchmarks/vehicle/WUFR27_SUSPENSION_CALCULATIONS_OPERATING_STATES_V0.toml`
- `src/pssd_vehicle/tire_bridge.py`
- `src/pssd_tire/r25b_force_demand_adapter.py`
- `data_catalog/r25b_steering_branch_handoff_v1.toml`
- `authorizations/steering/AUTH-STEER-0004.toml`
- `docs/roadmaps/post_steering_rnd_program_v0.1.0.md`
- `docs/roadmaps/post_rigid_contact_program_v0.1.0.md`

## Current vehicle evidence

The selected Suspension Calculations states preserve two 1.2 g development load-transfer cases. They are explicitly evidence-only and have zero target weight. They supply front-wheel normal loads and turn direction, but do not supply wheel inclination, tire gauge pressure, lateral-force demand, or suspension-pose identity. They also do not supply a per-steering-sample planar `u-v-r` schedule.

The current tire bridge correctly refuses to infer any of those fields.

### Right-turn state

- front inside load: `186.2139907 N`, below the R25B minimum of `222 N`;
- front outside load: `1719.575445 N`, above the R25B maximum of `1112 N`.

Neither front wheel lies inside the authorized R25B normal-load domain.

### Left-turn state

- front inside load: `516.8481725 N`, inside the bounded R25B load interval but not at an exact source knot;
- front outside load: `1388.941263 N`, above the R25B maximum of `1112 N`.

The inside load alone does not make this state usable. Inclination, gauge pressure, and lateral-force demand are unavailable, and the outside wheel is outside the source load domain.

## Readiness result

Current counts are:

- vehicle states reviewed: 2;
- states ready for the exact two-branch steering handoff: 0;
- states ready for a bounded complete-cell R25B runtime query: 0;
- states ready for a motion-aware steering target: 0.

No nearest-state substitution, clipping, load extrapolation, nominal camber or pressure insertion, force allocation from lateral acceleration, Ackermann-derived motion, or hidden target weighting is permitted.

## Program disposition

This is the planned upstream-evidence stopping point, not an unimplemented steering feature. The steering mechanism, tire branch, force-demand inversion, suspension-pose, vehicle-state, and planar-motion interfaces already exist. Continuing inside the steering or tire packages would require inventing vehicle equilibrium, suspension motion, or operating-state authority in the wrong subsystem.

PR #103 therefore closes the present R25B-to-steering extension and pauses further steering-only or tire-only target work. The immediate program focus returns to:

- PDR claim closeout and figure selection;
- physical steering decisions and their validation plans;
- the reviewed zero-steer suspension-pose path;
- a vehicle/QSS state producer when adequate source inputs are available.

This disposition is consistent with the post-steering and post-rigid-contact roadmaps. The existing R25B runtime and branch handoff remain available as stable consumers of future upstream state packages.

## Next evidence checkpoint

A reviewed synchronized target-state package is required. At the resolution used by the target, it must provide:

- front inside and outside normal load;
- inclination;
- gauge pressure;
- lateral-force demand;
- suspension pose;
- planar `u`, `v`, and `r` motion;
- an explicit nonzero weight for each target state.

Every query must remain inside the authorized R25B source domain. Acceptable evidence could be a reviewed vehicle simulation or QSS export, a reviewed measured or higher-fidelity simulation package, or a separately authorized engineering schedule that is clearly identified as an interpretation rather than a source-stated fact.

Until that evidence exists, source-backed steering target construction and design ranking remain blocked. Resume this vertical slice only when a reviewed zero-steer suspension-pose series and a synchronized vehicle/tire-demand state package are both available, or when an explicitly authorized engineering schedule is approved for that purpose.

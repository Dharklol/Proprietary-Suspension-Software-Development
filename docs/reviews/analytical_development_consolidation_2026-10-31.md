# Analytical development consolidation — 2026-10-31

## Owner direction and scope

The owner selected consolidation followed by analytical methods while the car
is several months from assembly. No measurement campaign is required for this
increment. Physical correlation remains a later requirement for installed,
predictive and production claims; it does not block the accepted uncorrelated
development experiment.

This checkpoint updates navigation and work priority. It adds no force law,
parameter default, tire extrapolation, target weight, root selection, optimizer
authority or change to AUTH-VEH-0012 and ASM-VEH-0006 through ASM-VEH-0009.

## Implemented development path

| Layer | Existing evidence | Claim supported |
|---|---|---|
| Native suspension-to-steering pose bridge | [Native pose contract](../models/steering/native_suspension_pose_adapter_v0.1.0.md) | Explicit frames, source identity and steering applied once |
| Coupled development kernel | [Kernel review](steady_cornering_development_kernel_review.md) | Synthetic equilibrium, material-point virtual work and independent full-wrench closure |
| Native WUFR composition | [Native composition review](steady_cornering_native_composition_review.md) | Bounded source integration at the selected 306.17484975 kg driver/no-fuel reference |
| Synchronized exchange | [Export review](steady_cornering_synced_export_review.md) | Matching forces, motion, poses, source revisions and frame bridges |
| Varying-state steering replay | [Consumer review](varying_state_steering_evidence_review.md) | Baseline reconstruction and all-root signed tire evidence |
| Current-main steering screens | [Compliance](../models/steering/wufr27_compliance_v1.md), [design-source compliance](../models/steering/wufr27_design_source_compliance_v1.md), [steel screens](../models/steering/wufr27_steel_joint_second_pass.md), [fit/contact](../models/steering/wufr27_double_d_fit_contact_screen.md) | Separate analytical screens under prescribed inputs and their documented assumptions |

The steering screens do not establish maneuver-generated rack torque, steering
effort, validated joint stiffness, structural release or vehicle correlation.
They are preserved alongside the development producer, without feeding their
provisional values back into rigid geometry or equilibrium.

## PR dependency and landing record

Snapshot from the GitHub connection on 2026-10-31; this table is not a live status
service. Each recorded head had eleven successful workflows, no review threads
and no submitted reviews. All five PRs were open drafts, not landed. Successful
workflows do not imply reviewer approval or readiness under every landing rule.

| PR | Head | Current base | Dependency and landing treatment |
|---|---|---|---|
| [106](https://github.com/Dharklol/Proprietary-Suspension-Software-Development/pull/106) | `bee8e72c6b40f5a29f03d106a71352602f7e822e` | main | Pose bridge; land before the export that uses it |
| [107](https://github.com/Dharklol/Proprietary-Suspension-Software-Development/pull/107) | `021719e1de306047737e7d844de0a5e3618c45c0` | main | Accepted development kernel; separate from 106 |
| [108](https://github.com/Dharklol/Proprietary-Suspension-Software-Development/pull/108) | `64149e1f7a412370d9c81cbdbb502e78c6d3d07d` | 107 branch | Native composition after 107 |
| [109](https://github.com/Dharklol/Proprietary-Suspension-Software-Development/pull/109) | `2baca2c9c7d8c6d516023c9e18b6305123eb0097` | 108 branch | Export after 106 and 108 |
| [110](https://github.com/Dharklol/Proprietary-Suspension-Software-Development/pull/110) | `c588a690e5ed079aa72b04631ca8cca32f4276ef` | 109 branch | Varying-state replay after 109 |

Main also contains PRs 111–115 through
`4431820050cc941dbec1ab5a61cb4b146998eb98`, added after the stack branched.
Consolidation integrates that main into a separate branch above 110 without
rewriting the published stack. The integration preserves the compliance and
structural additions. The six files introduced by 106 match the corresponding
content at the 110 integration tip; 109 carries the bridge content without
making 106 a Git ancestor. Content equivalence is not a substitute for landing
106 or checking the eventual main tree.

Land the original PRs in dependency order, retaining their review boundaries.
After each landing, inspect the remaining diffs and base, refresh head-specific
checks where required, and retain the final tree rather than replaying content
blindly. No branch deletion, forced update, PR closure or merge is implied by
this documentation. The consolidation follow-up targets 110 until its ancestors
are landed; it must not be merged into an intermediate feature branch as a
substitute for landing the stack on main.

The prescribed PR watcher currently reports `blocked`: GitHub CLI (`gh`) is not
installed in this workspace. The connected API supplies inspection/publication,
but the PR Completion helper is the required landing surface. Repository
auto-merge is also disabled. No merge or verified helper readiness is claimed.

## Existing verification envelope and open analytical questions

Eight native fixtures use V=8 m/s, curvature 0 and +/-0.005/0.01/0.02 per metre,
four 68.9 kPa gauge pressures, front/rear ARB setting 1, and the documented spring
reference. They are source-integration controls, not a recommended vehicle setup.
The maximum kinematic acceleration magnitude V^2*abs(curvature) is 1.28 m/s^2,
approximately 0.13 standard g. This is neither a measured limit nor a grip limit.

The zero-curvature fixture retains approximately -731 N and +732 N front lateral
forces. Their cancellation and small closure residuals do not independently
explain their magnitude. The first analytical investigation must trace heading,
toe, slip, signed inclination, raw source response and reflection separately.
Do not suppress those forces simply to obtain a conventional straight state.

The negative-inclination extension is an accepted engineering symmetry rule.
Measured zero-IA bias produces an artificial direct/reflected seam (about 92 N
at the documented probe). Crossing that seam, leaving the tire table, hitting
geometry/contact bounds and failing numerically are distinct outcomes. None is
automatically a physical handling limit.

Round-trip replay and full force/moment closure remain necessary checks, not
independent physical validation. Candidate re-equilibration and root-policy
review remain prerequisites to future design ranking.

## Next work

Use [the analytical development program](../roadmaps/analytical_development_program_v0.1.0.md).
Do not add another target/optimization layer during consolidation. No new owner
input is needed to prepare independent analytical checks using the existing
explicit fixtures. A physical-correlation dataset is not requested now.

## Consolidation verification

The merge of main through PR 115 into the PR 110 development tree completed
without conflicts. Registry validation, whitespace checks and all relative
Markdown links in the five edited/new navigation documents pass.

The varying-state report was regenerated in the integrated checkout. All eight
native seeds were re-solved and re-exported against current providers; all
six consumer tests and sixteen front-wheel replays pass. Maximum forward-force
error is 1.1368683772161603e-13 N, center error 2.7755575615628914e-17 m and
observed-heading error 3.963843142607004e-16 rad. These are reconstruction errors,
not independent accuracy bounds. Full broad-suite results belong to this
integration head, not the earlier individual PR runs.

The integrated Python 3.12 broad run completed 815 tests: 812 passed and the
same three previously recorded exact numerical snapshot comparisons failed
(force-coordinate diagnostic and two static Level-1 interface-load records).
No new failing test was reported. Python 3.11 CI must verify the published
integration head; this local result is not described as a fully passing suite.

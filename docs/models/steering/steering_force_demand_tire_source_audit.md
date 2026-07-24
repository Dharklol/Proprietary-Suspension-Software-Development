# Steering force-demand tire source audit

**PR:** #30  
**Scope:** source evidence required for `Fy demand -> required slip angle` steering targets  
**Current decision:** architecture may proceed with synthetic software fixtures, but WUFR design ranking remains gated until source-derived pre-peak force branches are exported and reviewed.

## 1. Why PR #28 can end pro-Ackermann even when the tire trend points anti

PR #28 used one source-derived quantity from the Hoosier 43105 R25B TTC summary at each of two operating points:

- inside reference: `Fz=222 N`, `IA=0 deg`, `P=83 kPa`, peak slip magnitude `9.6 deg`;
- outside reference: `Fz=1112 N`, `IA=2 deg`, `P=83 kPa`, peak slip magnitude `10.9 deg`.

The resulting differential is therefore:

`alpha*_out - alpha*_in = +1.3 deg`.

A positive differential moves the **outside** wheel farther into the turn than geometric Ackermann would. It is therefore an anti-Ackermann-direction correction, not a pro-Ackermann correction.

At the positive endpoint, however, the frozen inside heading is `32.18468832 deg`. Exact geometric Ackermann for the WUFR wheelbase/steering-axis track gives an outside reference of `22.8686960462 deg`, so the geometric inside-minus-outside gap is about `9.315992274 deg`. Adding the full `+1.3 deg` tire correction gives `24.1686960462 deg`, leaving an inside-minus-outside gap of about `8.015992274 deg`. The endpoint is consequently still pro-Ackermann.

The same correction can cross anti-Ackermann at small steer because the geometric Ackermann split is much smaller there. With the PR #28 utilization schedule at the `+15 deg` input sample, the corrected outside target is `3.7104805346 deg` versus the preserved inside target `3.6966375 deg`: a small anti-Ackermann split. Thus PR #28 is already state-dependent in regime even though its endpoints are pro.

This is the central reason PR #30 reports **pro / parallel / anti as an output** rather than treating any one of them as a global tire property.

## 2. Available R25B source chain

The team tire-selection package is in Box:

`WashURacing -> 6. WUFR-26 -> WUFR-26 CAD AND DRAWINGS -> 8. WHEELS & TIRES -> 806. TIRES -> TIRE SELECTION`

Folder ID: `324621167966`.

The Hoosier R25B subfolder is `Hoosier 43105 18x7.5 R25B`, folder ID `325714540497`.

Relevant files include:

| source | Box ID | current role |
|---|---:|---|
| `Hoosier 18 x 7.5 - 10 R25B 43105.tir` | `1952385546497` | team fitted tire model; desired future offline branch exporter |
| `Hoosier 43105 R25B Cornering Trojan.mat` | `1890914118742` | processed cornering-response source |
| `Round6_Run21.mat` | `1890899727782` | raw TTC Round 6 cornering data |
| `Round6_Run22.mat` | `1890911183790` | raw TTC Round 6 cornering data |
| `Tire Selection Notes.xlsx` | `1890901561957` | reviewed summary evidence used by PR #28 |
| `Comparisons.m` | `1890902598335` | historical source-processing/reference script |
| `yaw_moment.m` | `1890898098754` | historical whole-vehicle/Magic Formula integration reference |

The source/intended tire identity rule remains unchanged:

- source data/model: Hoosier **43105 18x7.5-10 R25B**;
- intended WUFR tire: Hoosier **43104 18x7.5-10 R20**;
- project authority: R25B behavior is the explicitly approved engineering-equivalent data source for this steering-development use;
- the two part/compound identities remain separate in provenance.

## 3. What the current summary does and does not contain

`Tire Selection Notes.xlsx` contains useful lateral summaries over pressure, inclination, and normal load, including:

- cornering stiffness at zero slip;
- peak lateral force;
- slip angle at peak lateral force;
- camber thrust at zero slip;
- aligning-moment summaries;
- load sensitivity and peak/dropoff comparisons.

For the R25B at `83 kPa`, examples include:

| IA [deg] | Fz [N] | C-alpha [N/deg] | peak Fy [N] | peak SA into turn [deg] |
|---:|---:|---:|---:|---:|
| 0 | 222 | 299 | 694 | -9.6 |
| 0 | 445 | 414 | 1256 | -9.9 |
| 0 | 667 | 523 | 1803 | -11.1 |
| 0 | 1112 | 657 | 2827 | -11.2 |
| 2 | 222 | 256 | 619 | -10.5 |
| 2 | 445 | 383 | 1164 | -11.4 |
| 2 | 667 | 494 | 1704 | -12.0 (source-boundary censored) |
| 2 | 1112 | 632 | 2738 | -10.9 |

Those summaries are sufficient for PR #28's bounded peak-slip-differential experiment. They are **not** sufficient to reconstruct a unique arbitrary pre-peak `Fy(alpha)` curve. Cornering stiffness, a zero-slip/camber-thrust value, one peak, and a 12-degree dropoff point do not uniquely determine the intervening nonlinear response.

PR #30 therefore does not invent a polynomial, spline, Magic Formula rewrite, or other surrogate from those summaries.

## 4. PR #30 response-branch contract

The first PR #30 tire contract accepts an explicit monotonic pre-peak branch at one exact operating point:

`(|alpha|_0, |Fy|_0), ..., (|alpha|_n, |Fy|_n)`.

It then performs only bounded piecewise-linear **inversion between supplied response samples**. It does not interpolate across `Fz`, inclination, or pressure in this first version, and it does not extrapolate force demand beyond the supplied branch.

The magnitude formulation avoids silently converting SAE/ISO tire-force signs inside steering. The source exporter must choose and document the intended physical branch (for example, leaning into the turn) and retain its original sign convention in provenance.

The synthetic branch table committed with BENCH-STEER-0021 exists solely to verify this software contract. Its interior force/slip values are deliberately **not** represented as R25B data.

## 5. Required real-source export

Before force-demand targets can rank WUFR steering geometry, a reviewed source-specific exporter should produce monotonic pre-peak branches from one of the existing higher-fidelity sources, preferably the team fitted `.tir`/Magic Formula chain cross-checked against raw/processed TTC data.

The export should include at minimum:

- source and intended tire IDs;
- source file/revision/hash;
- `Fz`, inclination, pressure, speed and any other fitted-model state held fixed;
- source force/slip sign convention;
- selected branch rule and pre-peak domain;
- explicit sampled `alpha, Fy` points at adequate resolution;
- whether values are raw, processed, fitted-model outputs, or track-scaled outputs;
- censor/extrapolation disposition;
- model/library version when generated from the fitted `.tir`;
- a cross-check against source TTC data at representative conditions.

The historical `yaw_moment.m` factor `2/3`, described as a sandpaper-to-road correction, remains a separate track-correlation assumption. It must not be applied automatically to the tire branch export.

## 6. Vehicle-state dependency

`MOD-VEH-0001` can already carry per-wheel `Fz`, inclination, pressure, and `Fy` demand, but the first PR #29 current-team workbook fixture supplies only wheel loads. It intentionally leaves camber, pressure, and lateral-force demand unavailable.

Therefore PR #30 can verify the force-demand inversion/steering composition now, but production-relevant WUFR targets still require a reviewed source for the complete wheel states and a reviewed force-demand schedule or vehicle-equilibrium/QSS producer.

## 7. Interpretation rule

A tire may exhibit an outside-minus-inside required-slip tendency that points toward anti-Ackermann while a particular steering state remains geometrically pro-Ackermann. The regime changes only when the tire-required slip differential exceeds the geometric Ackermann inside/outside split at that steering angle.

Consequently:

- `alpha_out - alpha_in > 0` means **movement toward anti-Ackermann**;
- it does not by itself prove the final wheel-angle pair is anti-Ackermann;
- the final regime must be evaluated at each steering/vehicle state;
- no PR #30 benchmark is allowed to force an anti-Ackermann answer in advance.

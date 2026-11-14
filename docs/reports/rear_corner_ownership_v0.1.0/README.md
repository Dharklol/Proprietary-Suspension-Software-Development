# Rear corner ownership and bilateral coverage

BENCH-VEH-0029 / MOD-VEH-0013 / MOD-VEH-0014.
Reproduce: `PYTHONPATH=src python scripts/run_front_corner_ownership.py`, then
`PYTHONPATH=src python scripts/run_rear_corner_ownership.py`.

This ledger accounts for all 154 A0702 COM instances against the independent
SU header-151 mass/CG snapshot. It extends the front ledger to both axle
assemblies without inventing new physical ownership. All ten checks pass.

| Rear category | Instances | CAD mass (lb) |
|---|---:|---:|
| Existing source-supported arm/pushrod owners | 32 | 3.478 |
| Rod ends and spherical bearings needing joint treatment | 20 | 0.932 |
| Toe-link tube/endcap candidates | 6 | 0.404 |
| Unresolved clamp hardware | 96 | 0.827 |
| Total | 154 | 5.641 |

The 26 arm-attached and six pushrod components reuse existing evidence and
owner confirmation. They are not 32 newly resolved components. No rear tube
inertia is promoted to the front tube verification level. Rod mapping remains
conditional on the compatibility limits in BENCH-VEH-0027/0028.

The rear carbon toe-link tubes (SU192/193) and aluminum endcaps (SU206–209)
remain candidates. The explicit arm/rod steel-cap confirmation is not silently
extended to different aluminum toe-link caps. Candidate assignment does not
add a generalized gravity contribution.

## Combined corner coverage

| Category | Instances | CAD mass (lb) |
|---|---:|---:|
| Supported owner, including eight verified front tubes | 64 | 7.122 |
| Joint treatment required | 36 | 1.668 |
| Candidate | 10 | 0.426 |
| Unresolved hardware | 168 | 1.493 |
| Total | 278 | 10.709 |

These totals cover A0701/A0702 only, not uprights, wheels, rockers, ARBs or the
whole car. The 64 supported owners are the same 3.230484859 kg gravity subset
already reported. The remaining 214 rows are not a sprung or unsprung rigid lump.
Status partition closure preserves exact instance mass and CG; it does not prove
physical source correctness, clamping, bearing splits or equilibrium.

## Development sequence

Continue G3/G5a analytical composition. The next independent ownership targets
are toe-link attachment/motion and the clamping stacks, using assembly evidence.
Resolve the front COM instance/configuration discrepancy alongside that work.
Then compose compatible dry gravity, springs, ARBs and contact reactions and
verify independent force/moment balance before native transient integration.
No UI/release milestone or full native-equilibrium completion is claimed here.

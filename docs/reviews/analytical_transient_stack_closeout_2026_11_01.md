# Analytical/transient stack closeout — 2026-11-01

Owner explicitly requested closing the stack and continued development. All seven
PR heads had successful workflows, no review submissions or unresolved review
threads, and clean mergeability. Drafts were marked ready. Each child was retargeted
to main after its parent landed; merge commits preserved the stack ancestry.
Each merge used the checked expected head SHA, without admin or protection bypass.
GitHub readback confirmed all seven merged states.

| PR | Checked head | Merge commit |
|---|---|---|
| 121 | c9975fb6650f722aee8920f2710cd623a358b309 | 8766e5872eff7408788e313301f615d26097498e |
| 122 | 6cba86200cba96f83350d46be40fc20a3e1e583a | f51b001c837b793639c0c042e13c7350086342da |
| 123 | d8b14b9d83feece53a5d00a0c4888ed9e13932dd | ec322c283a702fe427f89973c8493856223b8a9e |
| 124 | 3c68c988c508b224ab2eaceaae0f2dacec32221d | 782c57066b7ca0461e3bf8611761668c97cecda0 |
| 125 | da765ba385f67012d5f053ae8e898c8f6c257476 | 462747d4aa166452fec5462d1487a2166eb00444 |
| 126 | 6208a68438f4e219af645c6e098423a3fc173087 | f61c703bc9aca4055b51d9d7bdafad8c157c7f90 |
| 127 | 2321ed555f13ffd55b2d826e000c7ed2ed0c6f59 | 3300377a39bba1f4b27400794b6f30aa2b1ca00b |

PR 121/122 each had 12 passing workflows; PR 123–127 each had 13. Head-bound
readiness observations preceded landing. No numerical/source promotion follows
from merging. Physical correlation, installed setup authority and source-specific
KW force curves remain outside these development results.

# Phase 2 WUFR road-contact authority correction review

**Authorization:** `AUTH-VEH-0007`  
**Affected model:** `MOD-VEH-0006`  
**Failed assumption:** `ASM-VEH-0004`  
**Failed required benchmark:** `BENCH-VEH-0008`  
**Implementation probe:** PR #64, closed unmerged

## Review question

Does the frozen WUFR-26 OptimumK `Contact Patch` result support treating the nominal contact point as a rigid upright-attached material point for arbitrary-state WUFR road compatibility?

## Evidence

No. The required historical reconstruction check used the existing reviewed suspension minimum-twist transform and independently reconstructed 3D source steering twist. The maximum selected-row Euclidean disagreement was `0.0008458158026623031 m`, versus the frozen acceptance tolerance `0.000005 m`.

The selected OptimumK pure-heave rows also keep Contact Patch on the source road plane; after body re-reference, contact z is exactly the opposite of imposed heave. The channel therefore behaves as a solved road-contact output and does not establish rigid attachment of one material point.

## Decision frozen by this PR

- `AUTH-VEH-0006` implementation permission is suspended for the current assumption.
- `ASM-VEH-0004` is invalidated as a source-validated governing arbitrary-state map.
- PR #64 remains closed/unmerged; its code is retained only as a failed implementation probe.
- The generic QSS kernel, static gravity provider, suspension kinematics, steering closure, spring provider, and WUFR Z-bar provider are unaffected within their existing scopes.
- No WUFR road reactions or wheel-load result may be published until a replacement contact model/source assumption is reviewed and implemented.

## Candidate next decision

The most economical engineering path appears to be an explicitly labeled **rigid circular centerline tire** contact reference built from physical wheel center, wheel-plane orientation, and reviewed nominal tire radius. It would be a low-fidelity geometric assumption, not a claim about the OptimumK Contact Patch or loaded tire behavior. Physical loaded-radius/contact evidence is the higher-fidelity alternative.

Neither candidate is authorized by this correction review. Reviewer approval of a replacement model comes first.

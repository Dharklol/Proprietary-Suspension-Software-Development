# Manufactured reduced ride verification

Reproduce from the repository root:

```sh
PYTHONPATH=src python scripts/run_reduced_ride_verification.py
```

Nine tests pass. Harmonic response errors decrease by 15.96 and 15.97 under
step halving (required 12–20); the finest maximum state-component error is
8.98e-10 in the corresponding SI component units. Bump energy residual is
8.53e-14 J. These values describe the manufactured cases only.

`summary.json` contains parameters, modes, numerical controls, errors and source
hashes. `bump_history.csv` contains the complete accepted bump response.
The source identity applies to the manufactured fixture, not installed hardware.

Stage guards retain accepted history and stop on sampled contact loss, travel
violation or nonfinite evaluation. They do not locate exact continuous events.
No native tire rate, KW force curve, gas/friction force, or vehicle mass allocation
is inferred. Completion alone does not certify integration accuracy.

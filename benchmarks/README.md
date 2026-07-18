# Verification Benchmarks

The benchmark suite follows a verification pyramid:

- **A:** dimensional, algebraic, and sign checks;
- **B:** limiting, symmetry, and invariance cases;
- **C:** textbook or published worked examples;
- **D:** independent implementation or derivation;
- **E:** cross-tool comparison;
- **F:** physical experiment and uncertainty-aware correlation.

Every benchmark record identifies target registry IDs, initial conditions, tolerances, expected outputs, and failure interpretation. Matching another tool is not automatically proof of correctness when both tools share the same assumptions.

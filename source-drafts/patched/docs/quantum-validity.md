# Quantum validity notes

## Critical mathematical correction

The scientific background material that inspired this repo included an incorrect Hadamard normalization factor in one draft explanation. The correct Hadamard matrix is:

H = (1/sqrt(2)) * [[1, 1], [1, -1]]

The scalar must be `1/sqrt(2)` to preserve unitarity and total probability.

## Why this matters

If the normalization is wrong:
- probability conservation fails
- simulation output becomes physically invalid
- derived Bell-state formulas also become incorrectly normalized

## Repo impact

The OpenAPI contract does not encode quantum gate matrices directly, but the implementation notes and verification workflow assume physically valid, unitary circuit semantics.

## Verification requirement

LLM-assisted circuit optimization must pass:
1. unitarity checks
2. equivalence checks against the original intent
3. hardware-constraint checks
4. residual error threshold checks

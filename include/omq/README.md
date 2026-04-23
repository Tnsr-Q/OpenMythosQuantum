# Curvature-Coupled Lindblad Engine

Header-only C++17 library implementing a geometrically-coupled open quantum
system evolver with second-order Strang splitting, exact CPTP dissipative
channel via Liouville-space exponentiation, Ollivier-Ricci curvature via
entropy-regularized Sinkhorn OT, and a single-owner dissipation policy.

## What changed vs. the original Phase C draft

| Concern | Original | Upgraded |
|---|---|---|
| CPTP guarantee | Kraus to O(dt) only | Strang split; each sub-block exactly CPTP to machine precision |
| Trace drift fix | Placeholder verify, no action | Detect-before-symmetrize; verify failures counted but not masked |
| Physicality check | Trace only | Hermiticity, trace, minimum eigenvalue |
| Wasserstein | Hardcoded 1.0 | Log-domain Sinkhorn on union-support with BFS cost matrix |
| Lazy RW measure | Placeholder `{}` | Real μ_x(x)=α, μ_x(y)=(1−α)/deg(x) |
| γ ownership | Duplicated in engine + monitor, could desync | Single immutable `DissipationPolicy` snapshot with generation counter |
| γ responsiveness | Linear only | Baseline + α·max(0,−Ric)^p (baseline allows real thermal floor) |

## File tree

```
include/omq/
  types.hpp              Complex / DensityMatrix / EdgeKey aliases
  graph.hpp              Undirected graph + BFS distances
  policy.hpp             Immutable DissipationPolicy snapshot
  sinkhorn.hpp           Log-domain Sinkhorn W1 solver
  curvature_monitor.hpp  Lazy-RW measures, ORC, policy publication
  dissipator.hpp         Liouville-space superoperator, exp(L*dt)
  verify.hpp             Hermiticity / trace / positivity checks
  lindblad_engine.hpp    Strang-split evolver with policy-driven gamma
test/
  phase_c_test.cpp       10 closed-form validations
Makefile
```

## Data flow (single-owner model)

```
topology (nodes, edges)
      |
      v
CurvatureMonitor
  - lazy RW measures
  - Sinkhorn W1 per edge
  - Ricci table
      |
      | publish_policy(GammaMapping)
      v
DissipationPolicy (immutable, generation-counted, shared_ptr)
      |
      | set_policy() on LindbladEngine
      v
LindbladEngine
  - holds JumpOperatorTemplate list (unscaled L_k)
  - resolves gamma_k from policy at evolve time
  - caches exp(L_diss * dt) until generation or dt changes
```

The engine **never** stores γ. The monitor **never** produces mutable state.
Data flow is one-directional.

## Numerical validation summary

Run `make test` to reproduce. All ten tests pass with these observed errors:

| Test | Measured error | Tolerance |
|---|---|---|
| Sinkhorn identity transport | 5e-44 | 1e-3 |
| Sinkhorn unit shift | 0 | 1e-3 |
| ORC triangle (positive) | κ=0.75 all edges | — |
| ORC bowtie bridge (negative) | κ_bridge=−0.333 (analytic −1/3) | — |
| Policy nonneg + selective | γ=0.167 bridge, 0 triangle | — |
| Unitary limit purity | 4.5e-14 | 1e-9 |
| Spontaneous emission vs exp(−γt) | 4.4e-16 | 1e-6 |
| Long-run hermiticity | 4.4e-17 | 1e-9 |
| Long-run trace drift | 1.1e-13 | 1e-9 |
| Long-run min eigenvalue | +0.240 | ≥ −1e-10 |
| Channel preserves Tr(I/d) | 2.2e-16 | 1e-12 |
| Policy gen -> dissipator rebuild | triggered | — |

## Usage sketch

```cpp
#include "omq/curvature_monitor.hpp"
#include "omq/lindblad_engine.hpp"

using namespace omq;

// 1. Build graph + Ricci
CurvatureMonitor mon;
mon.set_graph(nodes, edges);
mon.recompute_ricci();

// 2. Publish immutable policy
GammaMapping gm;
gm.baseline = 0.01;   // thermal-bath floor
gm.alpha    = 0.5;    // curvature coupling
gm.power    = 1.0;
PolicyPtr policy = mon.publish_policy(gm);

// 3. Assemble engine with jump operator templates
std::vector<JumpOperatorTemplate> jumps = { /* L_k with edge_keys */ };
LindbladEngine eng(dim, jumps, policy);

// 4. Evolve
DensityMatrix rho = /* initial state */;
Operator H = /* Hamiltonian */;
for (int step = 0; step < N; ++step) {
    auto rep = eng.evolve_step(rho, H, dt);
    if (!rep.ok) { /* react to violation */ }
}

// 5. Update topology → republish policy → hot-swap
mon.set_graph(new_nodes, new_edges);
mon.recompute_ricci();
eng.set_policy(mon.publish_policy(gm));  // dissipator cache auto-invalidates
```

## Known tradeoffs / limits

- `build_dissipative_channel` builds a d² × d² matrix and exponentiates it.
  Cost is O(d⁶). Fine for d ≲ 20; for larger systems, switch to Krylov /
  scaling-and-squaring with low-rank structure.
- Strang split error is O(dt²) from [H, L_diss] ≠ 0. For higher accuracy
  use 4th-order Suzuki–Yoshida composition (same sub-blocks, different
  coefficients).
- Sinkhorn regularized cost is biased upward by O(ε·log|support|) vs true W₁.
  Default ε=0.02 gives <1% bias on the support sizes relevant here.
- Policy publication does not interpolate across generation changes. If the
  topology changes abruptly, γ jumps discontinuously. If smooth transitions
  matter, wrap publication in a time-smoothed filter upstream.

## Build

```bash
make          # builds build/phase_c_test
make test     # runs the test suite
make clean
```

Requires GCC ≥ 10 (C++17) and Eigen ≥ 3.4.

GCC 13 + Eigen 3.4 at -O2 emits internal `-Wmaybe-uninitialized` warnings
from `unsupported/Eigen/MatrixFunctions`; these originate in Eigen, not in
this code. Suppress with `-Wno-maybe-uninitialized` if noise is a problem.

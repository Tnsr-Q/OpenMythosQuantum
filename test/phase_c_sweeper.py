"""
Phase C/D cluster parameter sweeper.

Given a graph G with Ollivier-Ricci curvatures kappa_e on each edge, find the
critical coupling alpha_c at which the shadow-chain spectral gap reaches a
target threshold, using the Conjecture 1 ansatz alpha = 1/|kappa_min| as
the seed.

Notation (consistent with the Phase D manuscript):

  Q^G    weighted graph generator with
         Q^G_{u,v} = gamma_{uv} for u != v (edge present),
         Q^G_{u,u} = -sum_{v != u} Q^G_{u,v}.
  -Q^G   positive-semidefinite weighted Laplacian (== D - W).
  lambda_1(-Q^G) = spectral gap of Q^G = second-smallest eigenvalue of -Q^G.

This is the same quantity as the Fiedler value / algebraic connectivity of
the weighted graph. We compute it via eigvalsh on -Q^G.

Phase C mapping:
  gamma_e = alpha * max(0, -kappa_e)  for negatively-curved edges
  gamma_e = gamma_interior            for non-negative-curvature edges
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np
import networkx as nx
from scipy.linalg import eigvalsh
from scipy.optimize import minimize_scalar


@dataclass
class SweepResult:
    alpha_c: float
    lambda2_achieved: float
    ratio_to_ansatz: float        # alpha_c / alpha_ansatz
    lambda2_at_max_alpha: float   # feasibility check value
    converged: bool
    message: str


class PhaseCSweeper:
    """
    Finds the critical coupling alpha_c such that the weighted-Laplacian
    algebraic connectivity reaches `threshold_lambda2`, using the Phase C
    edge-weighting prescription.
    """

    def __init__(
        self,
        target_graph: nx.Graph,
        orc_dict: Dict[Tuple[int, int], float],
        threshold_lambda2: float,
        gamma_interior: float = 1.0,
        orc_tolerance: float = 1e-8,
    ):
        """
        Parameters
        ----------
        target_graph : networkx.Graph
            Undirected graph. Self-loops are ignored. Multi-edges are not
            supported.
        orc_dict : dict
            Mapping edge_tuple -> kappa_e.  Accepts either ordering (u,v)
            or (v,u); the constructor validates that every edge in the
            graph has an entry.
        threshold_lambda2 : float
            Target algebraic connectivity (must be > 0 and <= the
            max-alpha saturation value for the sweep to succeed).
        gamma_interior : float
            Rate assigned to non-negative-curvature edges. Default 1.0
            matches the Phase D universality study convention.
        orc_tolerance : float
            Edges with |kappa_e| < orc_tolerance are treated as flat
            (interior). Sinkhorn numerically produces kappa ~ 1e-12 on
            graphs that are analytically flat; this tolerance suppresses
            that noise.
        """
        if target_graph.number_of_nodes() == 0:
            raise ValueError("Graph is empty.")
        if not nx.is_connected(target_graph):
            raise ValueError(
                "Graph is disconnected. The shadow-chain spectral gap is "
                "identically zero for any alpha; sweep is ill-defined."
            )
        if threshold_lambda2 <= 0:
            raise ValueError("threshold_lambda2 must be > 0.")
        if gamma_interior <= 0:
            raise ValueError("gamma_interior must be > 0.")

        self.G = target_graph
        self.threshold = float(threshold_lambda2)
        self.gamma_interior = float(gamma_interior)
        self.orc_tol = float(orc_tolerance)

        # Validate and normalize the ORC dictionary: every graph edge must
        # have an entry in one of the two tuple orderings.
        self.kappa: Dict[frozenset, float] = {}
        missing = []
        for (u, v) in self.G.edges():
            k = None
            if (u, v) in orc_dict:
                k = orc_dict[(u, v)]
            elif (v, u) in orc_dict:
                k = orc_dict[(v, u)]
            else:
                missing.append((u, v))
                continue
            self.kappa[frozenset((u, v))] = float(k)
        if missing:
            raise KeyError(
                f"ORC values missing for {len(missing)} edges "
                f"(first few: {missing[:3]}). Every graph edge must have an "
                f"entry in orc_dict."
            )

        # Extract the minimum curvature and the negative-edge subgraph
        kappa_values = np.array(list(self.kappa.values()))
        self.kappa_min = float(kappa_values.min())

        neg_edges = [e for e in self.G.edges()
                     if self.kappa[frozenset(e)] < -self.orc_tol]

        if not neg_edges:
            raise ValueError(
                f"Graph has no edges with kappa < -{self.orc_tol}. "
                "No Phase C bottleneck intervention is required: the "
                "interior-rate Laplacian already controls the gap."
            )

        # Guard L3 (local-to-global): if removing all negative-curvature
        # edges disconnects the graph into k > 2 components, the Phase C
        # mapping with a scalar alpha cannot simultaneously control all
        # bottlenecks in general. We allow the sweep but warn.
        G_interior = self.G.copy()
        G_interior.remove_edges_from(neg_edges)
        n_components = nx.number_connected_components(G_interior)
        self.n_clusters = n_components
        self.neg_edges = neg_edges

        # Empirical Conjecture 1 ansatz
        self.alpha_ansatz = 1.0 / abs(self.kappa_min)

        # Cache node indexing for fast Laplacian assembly
        self._nodes = list(self.G.nodes())
        self._node_idx = {n: i for i, n in enumerate(self._nodes)}
        self._n = len(self._nodes)

    # ------------------------------------------------------------------
    # Core math
    # ------------------------------------------------------------------
    def _build_minus_Q(self, alpha: float) -> np.ndarray:
        """
        Build -Q^G (the PSD weighted Laplacian D - W) for the given alpha.

        Returns an (n x n) ndarray. Off-diagonals are -gamma_{uv}, diagonal
        is +sum of absolute off-diagonals -- i.e. this is the standard
        Laplacian L = D - W.
        """
        n = self._n
        L = np.zeros((n, n), dtype=float)

        for (u, v) in self.G.edges():
            i = self._node_idx[u]
            j = self._node_idx[v]
            k_e = self.kappa[frozenset((u, v))]

            if k_e < -self.orc_tol:
                gamma_e = alpha * abs(k_e)
            else:
                gamma_e = self.gamma_interior

            L[i, j] -= gamma_e
            L[j, i] -= gamma_e
            L[i, i] += gamma_e
            L[j, j] += gamma_e

        return L

    def _algebraic_connectivity(self, alpha: float) -> float:
        """
        Second-smallest eigenvalue of -Q^G. For a connected graph this is
        strictly positive; the smallest eigenvalue is 0 (up to numerical
        noise).
        """
        L = self._build_minus_Q(alpha)
        w = eigvalsh(L)
        # w is sorted ascending. w[0] ~ 0 (stationary mode); w[1] is the gap.
        return float(w[1])

    # ------------------------------------------------------------------
    # Optimization
    # ------------------------------------------------------------------
    def _objective(self, alpha: float) -> float:
        """
        Minimize (lambda_2(alpha) - threshold)^2. Robust to non-strict
        monotonicity in alpha because we find a minimum of a squared
        residual rather than a sign-changing zero.
        """
        return (self._algebraic_connectivity(alpha) - self.threshold) ** 2

    def run_sweep(
        self,
        bounds_factor: Tuple[float, float] = (0.1, 10.0),
        xatol: float = 1e-5,
        verbose: bool = True,
    ) -> Optional[SweepResult]:
        """
        Run the parameter sweep.

        Parameters
        ----------
        bounds_factor : tuple
            Multiplicative bounds on the seed ansatz. Default (0.1, 10.0)
            covers cluster-drift observed in the K_n-K_n universality tests
            plus a safety margin.
        xatol : float
            Convergence tolerance in alpha.
        verbose : bool
            Print progress and diagnostics.

        Returns
        -------
        SweepResult or None on feasibility failure.
        """
        lo = bounds_factor[0] * self.alpha_ansatz
        hi = bounds_factor[1] * self.alpha_ansatz

        # Feasibility check: does lambda_2 at alpha=hi actually meet the
        # threshold? If not, the sweep is infeasible and Brent will
        # silently converge to the boundary.
        lambda2_hi = self._algebraic_connectivity(hi)
        lambda2_lo = self._algebraic_connectivity(lo)

        if verbose:
            print(f"Seed ansatz alpha = 1/|kappa_min| = {self.alpha_ansatz:.5f}")
            print(f"kappa_min         = {self.kappa_min:.5f}")
            print(f"# neg-curv edges  = {len(self.neg_edges)}")
            print(f"# clusters (after removing neg edges) = {self.n_clusters}")
            print(f"Search bounds     = [{lo:.5f}, {hi:.5f}]")
            print(f"lambda_2 at lo    = {lambda2_lo:.5f}")
            print(f"lambda_2 at hi    = {lambda2_hi:.5f}")
            print(f"Target            = {self.threshold:.5f}")

        if lambda2_hi < self.threshold:
            msg = (
                f"Infeasible: at alpha={hi:.3f} (upper bound), "
                f"lambda_2={lambda2_hi:.5f} < threshold={self.threshold:.5f}. "
                "Either raise bounds_factor[1], lower the threshold, or "
                "accept that the Phase C mapping cannot synchronize this "
                "graph at the requested gap."
            )
            if verbose:
                print(f"[FAIL] {msg}")
            return SweepResult(
                alpha_c=float("nan"),
                lambda2_achieved=lambda2_hi,
                ratio_to_ansatz=float("nan"),
                lambda2_at_max_alpha=lambda2_hi,
                converged=False,
                message=msg,
            )

        if lambda2_lo > self.threshold:
            # Target already met at the lower bound: the threshold is
            # below the graph's natural gap. Report lo as alpha_c but flag.
            msg = (
                f"Threshold already met at alpha={lo:.3f}. The requested "
                "gap is below what the interior-rate structure achieves; "
                "no Phase C intervention needed above alpha_lo."
            )
            if verbose:
                print(f"[NOTE] {msg}")
            return SweepResult(
                alpha_c=lo,
                lambda2_achieved=lambda2_lo,
                ratio_to_ansatz=lo / self.alpha_ansatz,
                lambda2_at_max_alpha=lambda2_hi,
                converged=True,
                message=msg,
            )

        # Bracketed Brent on the squared residual. Since lambda_2 is
        # (usually) monotone-increasing in alpha on bracketed ranges
        # containing the threshold, the minimum is the unique point where
        # lambda_2 == threshold. If monotonicity locally fails, Brent still
        # returns a local minimum, which is the best we can do without
        # more structural information.
        result = minimize_scalar(
            self._objective,
            bounds=(lo, hi),
            method="bounded",
            options={"xatol": xatol},
        )

        alpha_c = float(result.x)
        achieved = self._algebraic_connectivity(alpha_c)
        ratio = alpha_c / self.alpha_ansatz
        # "Converged" here means both the optimizer reported success AND
        # we are close to the threshold (not stuck at a distant local min).
        residual = abs(achieved - self.threshold)
        converged = bool(result.success) and residual < 1e-3 * self.threshold

        msg = (
            f"alpha_c = {alpha_c:.5f} (ratio {ratio:.3f} x ansatz); "
            f"lambda_2 = {achieved:.5f} (residual {residual:.2e})"
        )
        if verbose:
            tag = "OK" if converged else "WEAK"
            print(f"[{tag}] {msg}")

        return SweepResult(
            alpha_c=alpha_c,
            lambda2_achieved=achieved,
            ratio_to_ansatz=ratio,
            lambda2_at_max_alpha=lambda2_hi,
            converged=converged,
            message=msg,
        )
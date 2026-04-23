// Phase D numerical verification: the Ricci-Dissipation Consistency Bound.
//
// Claim:  For the classical continuous-time Markov chain induced by the
// diagonal-sector Lindblad semigroup on the bowtie graph, the spectral gap
// (equivalently the relative-entropy decay rate) exhibits a sharp transition
// at a critical coupling alpha_c when gamma_e = alpha * max(0, -kappa_e).
// Below alpha_c the bridge edge acts as a bottleneck and the gap is
// parametrically suppressed; above alpha_c the gap saturates at the
// within-cluster mixing rate.
//
// We compute:
//   (i)   The single-excitation classical RW generator Q on V(G) with
//         edge rates given by the Phase C gamma mapping.
//   (ii)  The spectral gap of Q (the second-smallest eigenvalue in absolute
//         value of -Q, with the zero mode corresponding to stationarity).
//   (iii) The predicted critical coupling from the Cheeger-style bound.
//
// Output is a CSV file consumable by the manuscript's figure generator.

#include "omq/types.hpp"
#include "omq/graph.hpp"
#include "omq/curvature_monitor.hpp"
#include "omq/policy.hpp"

#include <Eigen/Dense>
#include <Eigen/Eigenvalues>
#include <iostream>
#include <fstream>
#include <iomanip>
#include <vector>

using namespace omq;

// Build the single-excitation classical RW generator on graph G with
// per-edge rates gamma_e from the policy.
//
// Q is |V| x |V|, real symmetric (reversible chain):
//   Q[u,v] = gamma_{uv}            (u != v, if edge exists)
//   Q[u,u] = -sum_{v ~ u} gamma_{uv}
//
// The stationary distribution for this construction is uniform on V, since
// all off-diagonal rates appear symmetrically.
static Eigen::MatrixXd build_generator(
        const std::vector<GraphNode>& nodes,
        const std::vector<GraphEdge>& edges,
        const DissipationPolicy& policy) {
    int n = static_cast<int>(nodes.size());
    // Map node id -> index
    std::unordered_map<int,int> idx;
    for (int i = 0; i < n; ++i) idx[nodes[i].id] = i;

    Eigen::MatrixXd Q = Eigen::MatrixXd::Zero(n, n);
    for (const auto& e : edges) {
        double g = policy.gamma_for(make_undirected_edge_key(e.u, e.v));
        int iu = idx[e.u], iv = idx[e.v];
        Q(iu, iv) += g;
        Q(iv, iu) += g;
    }
    // Diagonal entries: Q_ii = -sum_{j != i} Q_ij (row-sum = 0)
    for (int i = 0; i < n; ++i) {
        double s = 0.0;
        for (int j = 0; j < n; ++j) if (j != i) s += Q(i,j);
        Q(i,i) = -s;
    }
    return Q;
}

// Second-smallest-in-magnitude eigenvalue of -Q (i.e., the spectral gap
// of the Markov chain). The smallest is always 0 (stationary mode).
static double spectral_gap(const Eigen::MatrixXd& Q) {
    Eigen::MatrixXd A = -Q;
    // Symmetrize for numerical stability (the chain is reversible -> Q is
    // symmetric up to floating-point noise)
    A = 0.5 * (A + A.transpose());
    Eigen::SelfAdjointEigenSolver<Eigen::MatrixXd> es(A);
    if (es.info() != Eigen::Success) return -1.0;
    Eigen::VectorXd evals = es.eigenvalues();
    // Eigenvalues of -Q are >= 0. The smallest is ~0 (stationary).
    // Return the second-smallest.
    std::vector<double> v(evals.data(), evals.data() + evals.size());
    std::sort(v.begin(), v.end());
    // v[0] should be near 0; v[1] is the gap
    return v[1];
}

// Cheeger-style analytic lower bound for the gap given gamma values.
// For the bowtie, the gap is dominated by the bridge conductance when
// gamma_bridge is small.
static double cheeger_lower_bound(double gamma_bridge, double gamma_interior) {
    // Conductance of the bridge cut (separating {0,1,2} from {3,4,5}):
    //   Phi = gamma_bridge / min(vol(A), vol(B))
    // For uniform stationary weight 1/6 per node, vol(each side) = 3/6 = 0.5.
    // Total rate out of the bridge cut = gamma_bridge.
    // Cheeger: gap >= Phi^2 / 2
    (void)gamma_interior;
    double vol_min = 0.5;
    double phi = gamma_bridge / vol_min;
    return 0.5 * phi * phi;
}

int main() {
    // Bowtie graph: two triangles {0,1,2} and {3,4,5} joined by edge (2,3)
    std::vector<GraphNode> nodes = {{0},{1},{2},{3},{4},{5}};
    std::vector<GraphEdge> edges = {
        {0,1}, {1,2}, {0,2},
        {3,4}, {4,5}, {3,5},
        {2,3}
    };

    CurvatureMonitor::Config cfg;
    cfg.laziness = 0.5;
    cfg.sinkhorn_epsilon = 0.005;
    cfg.sinkhorn_max_iter = 2000;
    cfg.sinkhorn_tol = 1e-10;
    CurvatureMonitor mon(cfg);
    mon.set_graph(nodes, edges);
    mon.recompute_ricci();

    double k_bridge   = mon.ricci(2, 3);
    double k_triangle = mon.ricci(0, 1);
    std::cout << "# Bowtie Ricci curvatures:\n";
    std::cout << "#   bridge  edge (2,3):  kappa = " << k_bridge << "\n";
    std::cout << "#   triangle edge (0,1): kappa = " << k_triangle << "\n";
    std::cout << "#\n";

    // Sweep alpha in gamma_e = alpha * max(0, -kappa_e).
    // Because we want both a baseline mixing inside the triangles AND the
    // alpha-controlled bridge contribution, we use two mappings and compare:
    //   (A) baseline = 1.0 on all edges (uniform classical RW)
    //   (B) baseline = 1.0 on edges with kappa > 0 (within-cluster)
    //                  alpha * |kappa| on edges with kappa < 0 (bridge)
    //
    // In (A) the bridge has the same rate as the interior.
    // In (B) we can study the emergent bottleneck as alpha -> 0.

    std::ofstream csv("phase_d_gap_scan.csv");
    csv << "alpha,gamma_bridge,gamma_interior,gap_numerical,gap_cheeger_lb\n";

    // Build case (B) for varying alpha.
    for (double alpha = 0.001; alpha <= 5.0; alpha *= 1.2) {
        auto policy = std::make_shared<DissipationPolicy>();
        policy->generation = 1;
        // Interior (positive kappa): fixed baseline rate = 1
        policy->edge_gamma[make_undirected_edge_key(0,1)] = 1.0;
        policy->edge_gamma[make_undirected_edge_key(1,2)] = 1.0;
        policy->edge_gamma[make_undirected_edge_key(0,2)] = 1.0;
        policy->edge_gamma[make_undirected_edge_key(3,4)] = 1.0;
        policy->edge_gamma[make_undirected_edge_key(4,5)] = 1.0;
        policy->edge_gamma[make_undirected_edge_key(3,5)] = 1.0;
        // Bridge (negative kappa): alpha * |kappa|
        double g_bridge = alpha * std::max(0.0, -k_bridge);
        policy->edge_gamma[make_undirected_edge_key(2,3)] = g_bridge;

        Eigen::MatrixXd Q = build_generator(nodes, edges, *policy);
        double gap = spectral_gap(Q);
        double cheeger = cheeger_lower_bound(g_bridge, 1.0);

        csv << std::scientific << std::setprecision(6)
            << alpha << "," << g_bridge << ",1.0,"
            << gap << "," << cheeger << "\n";
    }
    csv.close();

    std::cout << "Wrote phase_d_gap_scan.csv\n";

    // --- Corollary: analytic prediction for where the bottleneck unlocks ---
    //
    // For the bowtie the gap of the uniform-rate RW (gamma=1 everywhere) is
    // computed analytically via the generator's eigenvalues. The bridge-
    // suppressed gap scales as O(gamma_bridge^2) by Cheeger. The crossover
    // point alpha_crit is where these two meet.
    //
    // With uniform rate 1, the interior gap is 3 (from K_3 block). The bridge
    // gap is ~ g_bridge^2 / 2 at small g_bridge. Set equal: g_bridge = sqrt(6)
    // -> alpha_crit = sqrt(6) / |kappa_bridge| = sqrt(6) / (1/3) = 3*sqrt(6).
    //
    // This is an upper bound; the true crossover is lower because the bridge
    // rate scales linearly in alpha until it's >~ interior rate, at which
    // point the second-eigenvalue structure changes.
    double kappa_abs = std::max(0.0, -k_bridge);
    double alpha_crit_upper = std::sqrt(6.0) / kappa_abs;
    std::cout << "Predicted upper bound on alpha_crit: " << alpha_crit_upper
              << "  (gamma_bridge_crit ~ " << std::sqrt(6.0) << ")\n";

    // A tighter prediction: crossover when gamma_bridge == interior_rate = 1.
    double alpha_crit_linear = 1.0 / kappa_abs;
    std::cout << "Predicted linear-response alpha_crit:  " << alpha_crit_linear
              << "  (gamma_bridge_crit ~ 1.0)\n";

    return 0;
}

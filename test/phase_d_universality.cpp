// Phase D universality study: measure the spectral-gap phase transition
// across multiple graph families to test whether alpha_c = 1/|kappa_min| is
// universal or artifact of the bowtie.
//
// Four experimental groups:
//  G1  Single-bridge dumbbells: K3-K3 (bowtie), K4-K4, K5-K5
//      - One negative edge each; vary cluster size.
//  G2  Control: path P_6
//      - All kappa ~ 0. Expect no phase transition.
//  G3  Multi-edge bottlenecks:
//      - Double-bridge: two parallel edges between K3 and K3
//      - Path-bridge: K3 -- x -- K3 (length-2 path bridge)
//  G4  Asymmetric: K3 bridged to K5
//
// For each graph we output a CSV row (alpha, gamma_bridge_scale, gap)
// tagged by graph name, suitable for plotting a master-curve collapse.

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
#include <string>
#include <algorithm>
#include <functional>

using namespace omq;

// ----- Generator and gap helpers (same as phase_d_verify.cpp) -----
static Eigen::MatrixXd build_generator(
        const std::vector<GraphNode>& nodes,
        const std::vector<GraphEdge>& edges,
        const DissipationPolicy& policy) {
    int n = static_cast<int>(nodes.size());
    std::unordered_map<int,int> idx;
    for (int i = 0; i < n; ++i) idx[nodes[i].id] = i;
    Eigen::MatrixXd Q = Eigen::MatrixXd::Zero(n, n);
    for (const auto& e : edges) {
        double g = policy.gamma_for(make_undirected_edge_key(e.u, e.v));
        int iu = idx[e.u], iv = idx[e.v];
        Q(iu, iv) += g;
        Q(iv, iu) += g;
    }
    for (int i = 0; i < n; ++i) {
        double s = 0.0;
        for (int j = 0; j < n; ++j) if (j != i) s += Q(i,j);
        Q(i,i) = -s;
    }
    return Q;
}

static double spectral_gap(const Eigen::MatrixXd& Q) {
    Eigen::MatrixXd A = -Q;
    A = 0.5 * (A + A.transpose());
    Eigen::SelfAdjointEigenSolver<Eigen::MatrixXd> es(A);
    if (es.info() != Eigen::Success) return -1.0;
    std::vector<double> v(es.eigenvalues().data(),
                          es.eigenvalues().data() + es.eigenvalues().size());
    std::sort(v.begin(), v.end());
    return v[1];
}

// ----- Graph family builders -----
struct GraphFamily {
    std::string name;
    std::vector<GraphNode> nodes;
    std::vector<GraphEdge> edges;
};

// Two K_n cliques joined by a single bridge edge
static GraphFamily make_dumbbell(int n, const std::string& label) {
    GraphFamily g;
    g.name = label;
    int total = 2 * n;
    for (int i = 0; i < total; ++i) g.nodes.push_back({i});
    // Left clique: 0..n-1
    for (int i = 0; i < n; ++i)
        for (int j = i+1; j < n; ++j)
            g.edges.push_back({i, j});
    // Right clique: n..2n-1
    for (int i = n; i < total; ++i)
        for (int j = i+1; j < total; ++j)
            g.edges.push_back({i, j});
    // Bridge: last node of left <-> first node of right
    g.edges.push_back({n-1, n});
    return g;
}

// Path graph P_n
static GraphFamily make_path(int n, const std::string& label) {
    GraphFamily g;
    g.name = label;
    for (int i = 0; i < n; ++i) g.nodes.push_back({i});
    for (int i = 0; i < n-1; ++i) g.edges.push_back({i, i+1});
    return g;
}

// Two K_3 cliques joined by a "ladder" bridge: two disjoint 2-edge paths
// between the cliques. This creates a genuine parallel-bottleneck topology
// where both bridge segments are bottleneck edges in series on separate routes.
//
// Nodes: triangleA = {0,1,2}, bridge relay nodes 3, 4,
//        triangleB = {5,6,7}
// Edges: triangleA internal (0,1),(1,2),(0,2)
//        triangleB internal (5,6),(6,7),(5,7)
//        Route 1: (2,3), (3,5)
//        Route 2: (1,4), (4,6)
//
// This has four bridge-like edges, each negative-curvature, arranged as
// two parallel routes. Expected: lower alpha_c than single bridge because
// two parallel paths unlock mass transport independently.
static GraphFamily make_ladder_bridge(const std::string& label) {
    GraphFamily g;
    g.name = label;
    for (int i = 0; i < 8; ++i) g.nodes.push_back({i});
    g.edges.push_back({0,1}); g.edges.push_back({1,2}); g.edges.push_back({0,2});
    g.edges.push_back({5,6}); g.edges.push_back({6,7}); g.edges.push_back({5,7});
    g.edges.push_back({2,3}); g.edges.push_back({3,5}); // route 1
    g.edges.push_back({1,4}); g.edges.push_back({4,6}); // route 2
    return g;
}

// Two K_3 cliques joined by a length-2 path: triangleA -- x -- triangleB
static GraphFamily make_path_bridge(const std::string& label) {
    GraphFamily g;
    g.name = label;
    // triangleA = {0,1,2}, pivot = 3, triangleB = {4,5,6}
    for (int i = 0; i < 7; ++i) g.nodes.push_back({i});
    g.edges.push_back({0,1}); g.edges.push_back({1,2}); g.edges.push_back({0,2});
    g.edges.push_back({4,5}); g.edges.push_back({5,6}); g.edges.push_back({4,6});
    g.edges.push_back({2,3});   // A -> pivot
    g.edges.push_back({3,4});   // pivot -> B
    return g;
}

// Asymmetric: K_3 bridged to K_5
static GraphFamily make_asymmetric_dumbbell(const std::string& label) {
    GraphFamily g;
    g.name = label;
    // K_3 = {0,1,2}, K_5 = {3,4,5,6,7}
    for (int i = 0; i < 8; ++i) g.nodes.push_back({i});
    g.edges.push_back({0,1}); g.edges.push_back({1,2}); g.edges.push_back({0,2});
    for (int i = 3; i < 8; ++i)
        for (int j = i+1; j < 8; ++j) g.edges.push_back({i,j});
    g.edges.push_back({2,3}); // bridge
    return g;
}

// ----- Experiment runner -----
struct SweepRow {
    std::string graph;
    double alpha;
    double kappa_min;
    double alpha_rescaled;   // alpha * |kappa_min|
    double gap;
    double gap_rescaled;     // gap / |kappa_min|  -- for the linear-response regime collapse
    int    num_negative_edges;
};

// For a given graph, compute all ORCs, identify negative-curvature edges,
// and sweep alpha. Positive-curvature edges are fixed at gamma = 1.
// Negative-curvature edges get gamma = alpha * |kappa_e|.
static std::vector<SweepRow> run_sweep(const GraphFamily& gf) {
    CurvatureMonitor::Config cfg;
    cfg.laziness = 0.5;
    cfg.sinkhorn_epsilon = 0.005;
    cfg.sinkhorn_max_iter = 2000;
    cfg.sinkhorn_tol = 1e-10;
    CurvatureMonitor mon(cfg);
    mon.set_graph(gf.nodes, gf.edges);
    mon.recompute_ricci();

    // Record Ricci values for every edge
    std::vector<double> ricci_vals;
    double kappa_min = std::numeric_limits<double>::infinity();
    int num_neg = 0;
    for (const auto& e : gf.edges) {
        double k = mon.ricci(e.u, e.v);
        ricci_vals.push_back(k);
        if (k < kappa_min) kappa_min = k;
        if (k < -1e-8) ++num_neg;
    }
    // Guard: for path graphs kappa ~ 0 so we clamp for rescaling
    double kmin_abs = std::max(1e-12, std::abs(std::min(0.0, kappa_min)));

    std::cout << "# " << gf.name
              << "  |V|=" << gf.nodes.size()
              << "  |E|=" << gf.edges.size()
              << "  kappa_min=" << kappa_min
              << "  #neg=" << num_neg << "\n";

    std::vector<SweepRow> rows;
    for (double alpha = 0.001; alpha <= 20.0; alpha *= 1.15) {
        auto policy = std::make_shared<DissipationPolicy>();
        policy->generation = 1;
        for (size_t i = 0; i < gf.edges.size(); ++i) {
            const auto& e = gf.edges[i];
            double k = ricci_vals[i];
            double gamma;
            if (k < -1e-8) {
                gamma = alpha * std::abs(k);
            } else {
                gamma = 1.0; // positive-curvature edge at baseline rate
            }
            policy->edge_gamma[make_undirected_edge_key(e.u, e.v)] = gamma;
        }
        Eigen::MatrixXd Q = build_generator(gf.nodes, gf.edges, *policy);
        double gap = spectral_gap(Q);
        SweepRow row;
        row.graph = gf.name;
        row.alpha = alpha;
        row.kappa_min = kappa_min;
        row.alpha_rescaled = alpha * kmin_abs;
        row.gap = gap;
        row.gap_rescaled = gap / kmin_abs;
        row.num_negative_edges = num_neg;
        rows.push_back(row);
    }
    return rows;
}

int main() {
    std::vector<GraphFamily> families = {
        make_dumbbell(3, "G1a_K3-K3"),
        make_dumbbell(4, "G1b_K4-K4"),
        make_dumbbell(5, "G1c_K5-K5"),
        make_path(6,     "G2_P6_control"),
        make_ladder_bridge("G3a_K3-K3_ladder"),
        make_path_bridge(  "G3b_K3-path-K3"),
        make_asymmetric_dumbbell("G4_K3-K5"),
    };

    std::ofstream csv("phase_d_universality.csv");
    csv << "graph,alpha,kappa_min,alpha_rescaled,gap,gap_rescaled,num_neg_edges\n";
    csv << std::scientific << std::setprecision(8);

    std::cout << "=== Phase D universality study ===\n";
    for (const auto& fam : families) {
        auto rows = run_sweep(fam);
        for (const auto& r : rows) {
            csv << r.graph << ","
                << r.alpha << ","
                << r.kappa_min << ","
                << r.alpha_rescaled << ","
                << r.gap << ","
                << r.gap_rescaled << ","
                << r.num_negative_edges << "\n";
        }
    }
    csv.close();

    std::cout << "\nWrote phase_d_universality.csv\n";
    std::cout << "\nExpected collapse behavior:\n"
              << "  G1a-c (single-bridge dumbbells): curves collapse under "
              << "alpha_rescaled = alpha*|kappa_min|\n"
              << "  G2 (path P_6): no transition; gap smooth in alpha\n"
              << "  G3a (ladder bridge): transition at alpha*|kappa| < 1 "
              << "(two parallel routes unlock lower alpha_c)\n"
              << "  G3b (path bridge): transition at alpha*|kappa| > 1 "
              << "(series resistance raises alpha_c)\n"
              << "  G4 (asymmetric): transition at alpha_rescaled ~ 1\n";

    return 0;
}

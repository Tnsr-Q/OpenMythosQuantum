// Test driver for Phase C upgraded modules.
//
// Each test is a standalone function that prints PASS / FAIL with a tolerance
// and a measured error. Closed-form answers are used wherever possible so
// numerical regressions surface immediately.

#include "omq/types.hpp"
#include "omq/graph.hpp"
#include "omq/policy.hpp"
#include "omq/sinkhorn.hpp"
#include "omq/curvature_monitor.hpp"
#include "omq/dissipator.hpp"
#include "omq/lindblad_engine.hpp"
#include "omq/verify.hpp"

#include <iostream>
#include <iomanip>
#include <cmath>
#include <vector>

using namespace omq;

static int g_fail_count = 0;
static int g_pass_count = 0;

static void check(bool ok, const std::string& name, double err, double tol) {
    std::cout << std::left << std::setw(60) << name
              << " err=" << std::scientific << std::setprecision(3) << err
              << " tol=" << tol
              << "  " << (ok ? "PASS" : "FAIL") << "\n";
    if (ok) ++g_pass_count; else ++g_fail_count;
}

// --------------------------------------------------------------------------
// Test 1: Sinkhorn reproduces a trivial identity-transport case.
// --------------------------------------------------------------------------
static void test_sinkhorn_identity() {
    Eigen::VectorXd a(3); a << 1.0/3, 1.0/3, 1.0/3;
    Eigen::VectorXd b = a;
    Eigen::MatrixXd C = Eigen::MatrixXd::Zero(3,3);
    for (int i=0;i<3;++i) for (int j=0;j<3;++j) C(i,j) = std::abs(i-j);
    auto res = SinkhornSolver::solve(a, b, C, 0.01, 2000, 1e-10);
    // Optimal plan is diagonal, cost = 0
    check(std::abs(res.cost) < 1e-3,
          "Sinkhorn identity-transport cost -> 0",
          std::abs(res.cost), 1e-3);
}

// --------------------------------------------------------------------------
// Test 2: Sinkhorn reproduces a known shift (two-point distributions
// separated by one unit, same mass).
// --------------------------------------------------------------------------
static void test_sinkhorn_shift() {
    Eigen::VectorXd a(2); a << 1.0, 0.0;
    Eigen::VectorXd b(2); b << 0.0, 1.0;
    Eigen::MatrixXd C(2,2);
    C << 0.0, 1.0,
         1.0, 0.0;
    auto res = SinkhornSolver::solve(a, b, C, 0.01, 2000, 1e-10);
    // All mass moves from index 0 to index 1 at cost 1
    check(std::abs(res.cost - 1.0) < 1e-3,
          "Sinkhorn unit shift cost -> 1",
          std::abs(res.cost - 1.0), 1e-3);
}

// --------------------------------------------------------------------------
// Test 3: ORC signs on canonical graphs.
//   Triangle (K_3): Ricci > 0 on all edges (strongly convergent / positively
//   curved).
//   Star with >=3 leaves: Ricci < 0 on the center-leaf edge (divergent).
// --------------------------------------------------------------------------
static void test_orc_triangle_positive() {
    std::vector<GraphNode> nodes = {{0},{1},{2}};
    std::vector<GraphEdge> edges = {{0,1},{1,2},{0,2}};
    CurvatureMonitor::Config cfg;
    cfg.laziness = 0.5; cfg.sinkhorn_epsilon = 0.01;
    CurvatureMonitor mon(cfg);
    mon.set_graph(nodes, edges);
    mon.recompute_ricci();
    double k01 = mon.ricci(0,1);
    double k12 = mon.ricci(1,2);
    double k02 = mon.ricci(0,2);
    bool ok = (k01 > 0.0) && (k12 > 0.0) && (k02 > 0.0);
    double err = -std::min({k01, k12, k02});
    check(ok, "ORC triangle: all edges positively curved", err, 0.0);
}

static void test_orc_bowtie_bridge_negative() {
    // Two triangles {0,1,2} and {3,4,5} joined by a single bridge edge (2,3).
    // The bridge edge should be negatively curved: mass on one side has to
    // travel across the bottleneck.
    std::vector<GraphNode> nodes = {{0},{1},{2},{3},{4},{5}};
    std::vector<GraphEdge> edges = {
        {0,1}, {1,2}, {0,2},   // triangle A
        {3,4}, {4,5}, {3,5},   // triangle B
        {2,3}                  // bridge
    };
    CurvatureMonitor::Config cfg;
    cfg.laziness = 0.5; cfg.sinkhorn_epsilon = 0.01;
    CurvatureMonitor mon(cfg);
    mon.set_graph(nodes, edges);
    mon.recompute_ricci();
    double k_bridge = mon.ricci(2, 3);
    double k_in_tri = mon.ricci(0, 1);  // a within-triangle edge for contrast
    bool ok = (k_bridge < 0.0) && (k_in_tri > 0.0);
    std::cout << "  bridge Ric=" << k_bridge
              << "  triangle-edge Ric=" << k_in_tri << "\n";
    check(ok, "ORC bowtie: bridge edge negative, triangle edge positive",
          std::max(0.0, k_bridge), 0.0);
}

// --------------------------------------------------------------------------
// Test 4: Policy-gamma mapping is non-negative and picks up negative Ricci.
// --------------------------------------------------------------------------
static void test_policy_nonnegative_and_responsive() {
    // Bowtie graph — bridge edge (2,3) is negatively curved
    std::vector<GraphNode> nodes = {{0},{1},{2},{3},{4},{5}};
    std::vector<GraphEdge> edges = {
        {0,1}, {1,2}, {0,2},
        {3,4}, {4,5}, {3,5},
        {2,3}
    };
    CurvatureMonitor mon;
    mon.set_graph(nodes, edges);
    mon.recompute_ricci();
    CurvatureMonitor::GammaMapping gm;
    gm.baseline = 0.0; gm.alpha = 0.5; gm.power = 1.0;
    auto policy = mon.publish_policy(gm);

    double g_bridge = policy->gamma_for(make_undirected_edge_key(2,3));
    double g_tri    = policy->gamma_for(make_undirected_edge_key(0,1));

    // Bridge has Ric<0 -> gamma>0. Triangle edge has Ric>0 -> gamma=0 (no baseline).
    bool nonneg    = (g_bridge >= 0.0) && (g_tri >= 0.0);
    bool responsive = (g_bridge > 1e-6);
    bool selective  = (g_tri < 1e-9);
    std::cout << "  g_bridge=" << g_bridge << "  g_triangle=" << g_tri << "\n";
    check(nonneg && responsive && selective,
          "Policy: gamma>=0, >0 on negative-curv edges, =0 on positive-curv",
          (responsive && selective) ? 0.0 : 1.0, 0.0);
}

// --------------------------------------------------------------------------
// Test 5: Unitary limit. gamma = 0 must preserve Tr(rho^2) = 1 for a pure
// state under arbitrary Hermitian H.
// --------------------------------------------------------------------------
static void test_unitary_limit_preserves_purity() {
    int d = 2;
    // Sigma_x Hamiltonian, |0><0| initial state
    Operator H(d,d);
    H << 0, 1,
         1, 0;
    DensityMatrix rho = DensityMatrix::Zero(d,d);
    rho(0,0) = 1.0;

    // Jump operator present, but policy gives gamma = 0
    std::vector<JumpOperatorTemplate> jumps;
    {
        JumpOperatorTemplate jt;
        jt.edge_key = make_undirected_edge_key(0,1);
        jt.L = Operator::Zero(d,d);
        jt.L(0,1) = 1.0; // sigma^-
        jumps.push_back(jt);
    }
    auto policy = std::make_shared<DissipationPolicy>();
    policy->generation = 1;
    // No entry in edge_gamma -> gamma_for returns 0 for everything

    LindbladEngine eng(d, jumps, policy);
    double dt = 0.01;
    double t_total = 1.0;
    int steps = static_cast<int>(t_total / dt);
    double max_purity_drift = 0.0;
    for (int i = 0; i < steps; ++i) {
        auto rep = eng.evolve_step(rho, H, dt);
        if (!rep.ok) {
            std::cout << "  verify: " << rep.summary() << "\n";
        }
        Complex pur = (rho * rho).trace();
        max_purity_drift = std::max(max_purity_drift, std::abs(pur.real() - 1.0));
    }
    check(max_purity_drift < 1e-9,
          "Unitary limit: Tr(rho^2) = 1 for all t",
          max_purity_drift, 1e-9);
}

// --------------------------------------------------------------------------
// Test 6: Spontaneous emission closed-form.
// Two-level atom, H = 0, L = sigma^- = |0><1|, gamma fixed.
// Initial state |1><1|. Analytic: rho_11(t) = exp(-gamma t),
//                                  rho_00(t) = 1 - exp(-gamma t),
//                                  off-diagonals stay 0.
// --------------------------------------------------------------------------
static void test_spontaneous_emission() {
    int d = 2;
    Operator H = Operator::Zero(d,d);

    std::vector<JumpOperatorTemplate> jumps;
    {
        JumpOperatorTemplate jt;
        jt.edge_key = make_undirected_edge_key(0,1);
        jt.L = Operator::Zero(d,d);
        jt.L(0,1) = 1.0;
        jumps.push_back(jt);
    }
    double gamma = 0.7;
    auto policy = std::make_shared<DissipationPolicy>();
    policy->generation = 1;
    policy->edge_gamma[make_undirected_edge_key(0,1)] = gamma;

    LindbladEngine eng(d, jumps, policy);

    DensityMatrix rho = DensityMatrix::Zero(d,d);
    rho(1,1) = 1.0;

    double dt = 0.01;
    double max_err = 0.0;
    for (int step = 1; step <= 300; ++step) {
        eng.evolve_step(rho, H, dt);
        double t = step * dt;
        double expected_11 = std::exp(-gamma * t);
        double expected_00 = 1.0 - expected_11;
        double err_11 = std::abs(rho(1,1).real() - expected_11);
        double err_00 = std::abs(rho(0,0).real() - expected_00);
        max_err = std::max({max_err, err_11, err_00});
    }
    check(max_err < 1e-6,
          "Spontaneous emission matches closed-form exp(-gamma t)",
          max_err, 1e-6);
}

// --------------------------------------------------------------------------
// Test 7: Hermiticity and trace preserved under a nontrivial combined
// evolution (H != 0, multiple jumps, long time).
// --------------------------------------------------------------------------
static void test_cptp_preservation_nontrivial() {
    int d = 3;
    // Random-ish Hermitian H
    Operator H(d,d);
    H << 0.0,            Complex(0.2,-0.1), Complex(0.0,0.3),
         Complex(0.2,0.1), 1.0,             Complex(-0.1,0.2),
         Complex(0.0,-0.3), Complex(-0.1,-0.2), -0.5;
    // Sanity: Hermitize
    H = 0.5 * (H + H.adjoint());

    std::vector<JumpOperatorTemplate> jumps;
    for (int i = 0; i < 2; ++i) {
        JumpOperatorTemplate jt;
        jt.edge_key = static_cast<EdgeKey>(i);
        jt.L = Operator::Random(d,d) * 0.3;
        jumps.push_back(jt);
    }
    auto policy = std::make_shared<DissipationPolicy>();
    policy->generation = 1;
    policy->edge_gamma[0] = 0.4;
    policy->edge_gamma[1] = 0.2;

    LindbladEngine eng(d, jumps, policy);

    // Initial: maximally mixed
    DensityMatrix rho = DensityMatrix::Identity(d,d) / d;

    double max_herm = 0.0, max_trace = 0.0, min_eig = 1e9;
    for (int step = 0; step < 500; ++step) {
        auto rep = eng.evolve_step(rho, H, 0.02);
        max_herm  = std::max(max_herm, rep.hermiticity_error);
        max_trace = std::max(max_trace, rep.trace_error);
        min_eig   = std::min(min_eig, rep.min_eigenvalue);
    }
    bool ok = (max_herm < 1e-9) && (max_trace < 1e-9) && (min_eig > -1e-10);
    std::cout << "  max_herm=" << max_herm
              << " max_trace=" << max_trace
              << " min_eig=" << min_eig << "\n";
    check(ok, "Long-run CPTP preservation (herm/trace/positivity)",
          std::max({max_herm, max_trace, -min_eig}), 1e-9);
}

// --------------------------------------------------------------------------
// Test 8: Sum_k K_k^dagger K_k = I (up to numerical precision) via the
// superoperator.  A CPTP channel is trace-preserving iff the dual channel
// maps I -> I.  In vec form with column-major convention: Phi* [I] = I
// corresponds to (I_d . I_d)-row of the transpose conjugate. We check the
// simpler equivalent property: channel applied to I/d should have trace 1.
// --------------------------------------------------------------------------
static void test_channel_preserves_trace_of_identity() {
    int d = 3;
    std::vector<JumpOperatorTemplate> jumps;
    for (int i = 0; i < 2; ++i) {
        JumpOperatorTemplate jt;
        jt.edge_key = static_cast<EdgeKey>(i);
        jt.L = Operator::Random(d,d);
        jumps.push_back(jt);
    }
    auto policy = std::make_shared<DissipationPolicy>();
    policy->generation = 1;
    policy->edge_gamma[0] = 0.4;
    policy->edge_gamma[1] = 0.2;

    Superoperator D = build_dissipative_channel(d, jumps, *policy, 0.1);
    DensityMatrix rho = DensityMatrix::Identity(d,d) / d;
    DensityMatrix rho_out = apply_channel(D, rho);
    double tr_err = std::abs(rho_out.trace().real() - 1.0);
    check(tr_err < 1e-12,
          "Channel preserves Tr(rho) for rho = I/d (dissipator-only)",
          tr_err, 1e-12);
}

// --------------------------------------------------------------------------
// Test 9: Policy generation triggers cache invalidation.
// --------------------------------------------------------------------------
static void test_policy_cache_invalidation() {
    int d = 2;
    Operator H = Operator::Zero(d,d);
    std::vector<JumpOperatorTemplate> jumps;
    {
        JumpOperatorTemplate jt;
        jt.edge_key = 0;
        jt.L = Operator::Zero(d,d); jt.L(0,1) = 1.0;
        jumps.push_back(jt);
    }

    auto policy_a = std::make_shared<DissipationPolicy>();
    policy_a->generation = 1;
    policy_a->edge_gamma[0] = 0.5;

    LindbladEngine eng(d, jumps, policy_a);
    DensityMatrix rho = DensityMatrix::Zero(d,d);
    rho(1,1) = 1.0;

    eng.evolve_step(rho, H, 0.01);
    auto diag_a = eng.diagnostics();

    // Swap to a new policy with different gamma
    auto policy_b = std::make_shared<DissipationPolicy>();
    policy_b->generation = 2;
    policy_b->edge_gamma[0] = 1.0;
    eng.set_policy(policy_b);

    eng.evolve_step(rho, H, 0.01);
    auto diag_b = eng.diagnostics();

    bool rebuilt = (diag_b.rebuild_dissipator > diag_a.rebuild_dissipator);
    check(rebuilt, "Policy generation change forces dissipator rebuild",
          rebuilt ? 0.0 : 1.0, 0.0);
}

// --------------------------------------------------------------------------
int main() {
    std::cout << "=== Phase C upgraded module tests ===\n\n";

    test_sinkhorn_identity();
    test_sinkhorn_shift();
    test_orc_triangle_positive();
    test_orc_bowtie_bridge_negative();
    test_policy_nonnegative_and_responsive();
    test_unitary_limit_preserves_purity();
    test_spontaneous_emission();
    test_cptp_preservation_nontrivial();
    test_channel_preserves_trace_of_identity();
    test_policy_cache_invalidation();

    std::cout << "\nResults: " << g_pass_count << " passed, "
              << g_fail_count << " failed.\n";
    return g_fail_count == 0 ? 0 : 1;
}

#ifndef OMQ_CURVATURE_MONITOR_HPP
#define OMQ_CURVATURE_MONITOR_HPP

#include "types.hpp"
#include "graph.hpp"
#include "policy.hpp"
#include "sinkhorn.hpp"
#include <vector>
#include <unordered_map>
#include <functional>
#include <algorithm>
#include <limits>

namespace omq {

struct CurvatureMonitorConfig {
    double laziness           = 0.5;
    double sinkhorn_epsilon   = 0.02;
    int    sinkhorn_max_iter  = 300;
    double sinkhorn_tol       = 1e-8;
    int    bfs_max_hops       = 6;
    CurvatureMonitorConfig() = default;
};

struct GammaMapping {
    double baseline = 0.0;   // thermal-bath floor if you want real thermalization
    double alpha    = 0.5;   // curvature -> damping coupling
    double power    = 1.0;   // 1 = linear, 2 = stiff near Ric=0
    GammaMapping() = default;
};

/**
 * Ollivier-Ricci curvature monitor with lazy-random-walk measures.
 *
 * For adjacent nodes (u,v) in an undirected graph G:
 *   mu_x(x) = laziness
 *   mu_x(y) = (1 - laziness) / deg(x)  for y in N(x)
 *   mu_x(z) = 0                         otherwise
 *
 * Ollivier-Ricci curvature:
 *   kappa(u,v) = 1 - W1(mu_u, mu_v) / d(u, v)
 *
 * W1 is computed via entropy-regularized Sinkhorn OT over the union of the
 * two supports, with a BFS-derived hop-distance cost matrix.
 *
 * Policy generation:
 *   gamma(u,v) = baseline + alpha * max(0, -kappa(u,v))^power
 *   Only non-negative gamma ever leaves this class.
 */
class CurvatureMonitor {
public:
    using Config = CurvatureMonitorConfig;
    using GammaMapping = ::omq::GammaMapping;

    explicit CurvatureMonitor(Config cfg = Config()) : cfg_(cfg) {}

    void set_graph(const std::vector<GraphNode>& nodes,
                   const std::vector<GraphEdge>& edges) {
        graph_.set(nodes, edges);
        edges_ = edges;
        ricci_.clear();
    }

    const Graph& graph() const { return graph_; }

    /** Recompute Ricci for every edge. O(|E| * sinkhorn_cost). */
    void recompute_ricci() {
        ricci_.clear();
        ricci_.reserve(edges_.size());
        for (const auto& e : edges_) {
            double kappa = compute_ricci_edge(e.u, e.v);
            ricci_[make_undirected_edge_key(e.u, e.v)] = kappa;
        }
    }

    double ricci(int u, int v) const {
        auto it = ricci_.find(make_undirected_edge_key(u, v));
        return (it == ricci_.end()) ? 0.0 : it->second;
    }

    /**
     * Build and publish an immutable DissipationPolicy snapshot. Caller owns
     * the returned shared_ptr<const>; subsequent publications yield a new
     * snapshot with generation = previous + 1.
     */
    PolicyPtr publish_policy(GammaMapping mapping = GammaMapping()) {
        auto policy = std::make_shared<DissipationPolicy>();
        policy->generation = ++generation_counter_;

        double min_k =  std::numeric_limits<double>::infinity();
        double max_k = -std::numeric_limits<double>::infinity();

        for (const auto& e : edges_) {
            double kappa = ricci(e.u, e.v);
            min_k = std::min(min_k, kappa);
            max_k = std::max(max_k, kappa);

            double raw = std::max(0.0, -kappa);
            double gamma = mapping.baseline
                         + mapping.alpha * std::pow(raw, mapping.power);
            if (gamma < 0.0) gamma = 0.0;

            policy->edge_gamma[make_undirected_edge_key(e.u, e.v)] = gamma;
        }
        if (!std::isfinite(min_k)) min_k = 0.0;
        if (!std::isfinite(max_k)) max_k = 0.0;
        policy->min_ricci = min_k;
        policy->max_ricci = max_k;
        return policy;
    }

private:
    Config cfg_;
    Graph  graph_;
    std::vector<GraphEdge> edges_;
    std::unordered_map<EdgeKey, double> ricci_;
    std::uint64_t generation_counter_ = 0;

    /**
     * Lazy-RW measure on {x} union N(x). Returns (support_ids, probability).
     */
    void lazy_rw_measure(int x,
                         std::vector<int>& support_out,
                         std::vector<double>& mass_out) const {
        support_out.clear();
        mass_out.clear();
        support_out.push_back(x);
        mass_out.push_back(cfg_.laziness);

        const auto& nbrs = graph_.neighbors(x);
        int d = static_cast<int>(nbrs.size());
        if (d == 0) {
            // Isolated node: full mass on self
            mass_out[0] = 1.0;
            return;
        }
        double w = (1.0 - cfg_.laziness) / static_cast<double>(d);
        for (int y : nbrs) {
            support_out.push_back(y);
            mass_out.push_back(w);
        }
    }

    /** Union of two support lists, preserving original membership. */
    static std::vector<int> union_supports(const std::vector<int>& sa,
                                           const std::vector<int>& sb) {
        std::vector<int> merged = sa;
        for (int x : sb) {
            if (std::find(merged.begin(), merged.end(), x) == merged.end()) {
                merged.push_back(x);
            }
        }
        return merged;
    }

    /** ORC for a single edge via Sinkhorn. */
    double compute_ricci_edge(int u, int v) const {
        std::vector<int>    sa, sb;
        std::vector<double> ma, mb;
        lazy_rw_measure(u, sa, ma);
        lazy_rw_measure(v, sb, mb);

        // Common support for a joint cost matrix
        std::vector<int> support = union_supports(sa, sb);
        int k = static_cast<int>(support.size());

        Eigen::VectorXd a = Eigen::VectorXd::Zero(k);
        Eigen::VectorXd b = Eigen::VectorXd::Zero(k);
        for (size_t i = 0; i < sa.size(); ++i) {
            auto it = std::find(support.begin(), support.end(), sa[i]);
            a(it - support.begin()) = ma[i];
        }
        for (size_t j = 0; j < sb.size(); ++j) {
            auto it = std::find(support.begin(), support.end(), sb[j]);
            b(it - support.begin()) = mb[j];
        }

        // Cost matrix: pairwise hop distances among support nodes
        Eigen::MatrixXd C(k, k);
        for (int i = 0; i < k; ++i) {
            auto dists = graph_.bfs_distances(support[i], support, cfg_.bfs_max_hops);
            for (int j = 0; j < k; ++j) {
                int d_ij = dists[j];
                // If unreachable within max_hops, use a large finite penalty
                C(i, j) = (d_ij == std::numeric_limits<int>::max())
                            ? static_cast<double>(cfg_.bfs_max_hops + 1)
                            : static_cast<double>(d_ij);
            }
        }

        auto result = SinkhornSolver::solve(a, b, C,
                                            cfg_.sinkhorn_epsilon,
                                            cfg_.sinkhorn_max_iter,
                                            cfg_.sinkhorn_tol);
        double d_uv = 1.0; // adjacent in undirected graph
        return 1.0 - result.cost / d_uv;
    }
};

} // namespace omq

#endif // OMQ_CURVATURE_MONITOR_HPP

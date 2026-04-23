#ifndef OMQ_GRAPH_HPP
#define OMQ_GRAPH_HPP

#include "types.hpp"
#include <vector>
#include <unordered_map>
#include <unordered_set>
#include <queue>
#include <stdexcept>

namespace omq {

struct GraphNode {
    int id;
};

struct GraphEdge {
    int u, v;
    double weight = 1.0; // reserved for weighted graphs; ORC currently uses hop distance
};

/**
 * Undirected graph with adjacency-list storage.
 * BFS is used for pairwise distances on the full support set used by Sinkhorn.
 */
class Graph {
public:
    void set(const std::vector<GraphNode>& nodes,
             const std::vector<GraphEdge>& edges) {
        adj_.clear();
        nodes_.clear();
        for (const auto& n : nodes) {
            nodes_.push_back(n.id);
            adj_[n.id]; // ensure key exists
        }
        for (const auto& e : edges) {
            adj_[e.u].insert(e.v);
            adj_[e.v].insert(e.u);
        }
    }

    const std::vector<int>& nodes() const { return nodes_; }

    const std::unordered_set<int>& neighbors(int u) const {
        auto it = adj_.find(u);
        if (it == adj_.end()) {
            static const std::unordered_set<int> empty;
            return empty;
        }
        return it->second;
    }

    int degree(int u) const {
        return static_cast<int>(neighbors(u).size());
    }

    bool has_node(int u) const { return adj_.find(u) != adj_.end(); }

    /**
     * Hop distance from source to each node in `targets`. Uses BFS truncated at
     * max_hops. Returns a vector aligned with targets; unreachable / beyond
     * max_hops receives std::numeric_limits<int>::max().
     */
    std::vector<int> bfs_distances(int source,
                                   const std::vector<int>& targets,
                                   int max_hops = 8) const {
        std::unordered_map<int,int> dist;
        dist[source] = 0;
        std::queue<int> q; q.push(source);
        while (!q.empty()) {
            int x = q.front(); q.pop();
            int dx = dist[x];
            if (dx >= max_hops) continue;
            auto it = adj_.find(x);
            if (it == adj_.end()) continue;
            for (int y : it->second) {
                if (dist.find(y) == dist.end()) {
                    dist[y] = dx + 1;
                    q.push(y);
                }
            }
        }
        std::vector<int> out;
        out.reserve(targets.size());
        for (int t : targets) {
            auto it = dist.find(t);
            out.push_back(it == dist.end()
                ? std::numeric_limits<int>::max()
                : it->second);
        }
        return out;
    }

private:
    std::vector<int> nodes_;
    std::unordered_map<int, std::unordered_set<int>> adj_;
};

} // namespace omq

#endif // OMQ_GRAPH_HPP

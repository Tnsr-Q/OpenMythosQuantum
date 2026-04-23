#ifndef OMQ_POLICY_HPP
#define OMQ_POLICY_HPP

#include "types.hpp"
#include <unordered_map>
#include <cstdint>
#include <memory>

namespace omq {

/**
 * Immutable snapshot of per-edge dissipation strengths.
 *
 * Produced exclusively by CurvatureMonitor::publish_policy().
 * Consumed by LindbladEngine via shared_ptr<const DissipationPolicy>.
 *
 * The generation counter is monotonically increasing across successive
 * policy publications from the same monitor; the engine uses it to decide
 * whether to invalidate its cached dissipator superoperator.
 *
 * Invariants (enforced by the producer):
 *   - All gamma values are finite and >= 0.
 *   - Keys are undirected edge keys (see types.hpp).
 *   - A missing key in edge_gamma means gamma = 0 for that edge.
 */
struct DissipationPolicy {
    std::unordered_map<EdgeKey, double> edge_gamma;
    std::uint64_t generation = 0;
    double        min_ricci  = 0.0;   // audit metadata: worst negative curvature seen
    double        max_ricci  = 0.0;

    double gamma_for(EdgeKey key) const {
        auto it = edge_gamma.find(key);
        return (it == edge_gamma.end()) ? 0.0 : it->second;
    }
};

using PolicyPtr = std::shared_ptr<const DissipationPolicy>;

} // namespace omq

#endif // OMQ_POLICY_HPP

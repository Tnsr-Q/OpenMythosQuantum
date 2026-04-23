#ifndef OMQ_TYPES_HPP
#define OMQ_TYPES_HPP

#include <Eigen/Dense>
#include <complex>
#include <cstdint>

namespace omq {

using Complex        = std::complex<double>;
using DensityMatrix  = Eigen::MatrixXcd;   // d x d, Hermitian, Tr=1, PSD
using Operator       = Eigen::MatrixXcd;   // generic d x d
using Superoperator  = Eigen::MatrixXcd;   // d^2 x d^2 acting on vec(rho)
using StateVector    = Eigen::VectorXcd;   // vec(rho), length d^2

// Edge key encoding - stable ordering so (u,v) and (v,u) collapse to the same key
// when the graph is treated as undirected (used by CurvatureMonitor). The engine
// uses directed keys because jump operators L_{u->v} are directional.
using EdgeKey = std::uint64_t;

inline EdgeKey make_directed_edge_key(int u, int v) {
    return (static_cast<std::uint64_t>(static_cast<std::uint32_t>(u)) << 32)
         |  static_cast<std::uint32_t>(v);
}

inline EdgeKey make_undirected_edge_key(int u, int v) {
    int a = std::min(u, v);
    int b = std::max(u, v);
    return make_directed_edge_key(a, b);
}

} // namespace omq

#endif // OMQ_TYPES_HPP

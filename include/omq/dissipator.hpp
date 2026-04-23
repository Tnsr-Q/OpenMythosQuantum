#ifndef OMQ_DISSIPATOR_HPP
#define OMQ_DISSIPATOR_HPP

#include "types.hpp"
#include "policy.hpp"
#include <unsupported/Eigen/MatrixFunctions>
#include <vector>
#include <stdexcept>

namespace omq {

/**
 * A jump operator template: the unscaled Lindblad operator L_k plus the edge
 * key that selects its gamma from the DissipationPolicy.
 *
 * The engine *never* stores gamma here; it is looked up at evolution time
 * from the current policy.
 */
struct JumpOperatorTemplate {
    EdgeKey  edge_key;
    Operator L;                 // d x d
    std::string label;          // optional, for diagnostics
};

/**
 * Build the Liouville-space superoperator for the purely dissipative part:
 *
 *   D[rho] = sum_k gamma_k ( L_k rho L_k^dag
 *                            - 1/2 { L_k^dag L_k, rho } )
 *
 * In column-major vec convention (vec stacks columns):
 *   vec(L rho L^dag)      = (L^dag)^T kron L  vec(rho)  =  (L^* kron L) vec(rho)
 *   vec(L^dag L rho)      = I kron (L^dag L)            vec(rho)
 *   vec(rho L^dag L)      = (L^dag L)^T kron I          vec(rho)
 *
 * Returns a d^2 x d^2 matrix Dsup such that vec(drho/dt)_diss = Dsup vec(rho).
 *
 * Exact CPTP evolution for time dt is:
 *   vec(rho(t+dt)) = expm(Dsup * dt) vec(rho(t))
 *
 * This is exactly trace-preserving and completely positive for any dt >= 0
 * when gamma_k >= 0, because it is the exact solution of the valid Lindblad
 * dissipator.
 */
inline Superoperator build_dissipator_superoperator(
        int dim,
        const std::vector<JumpOperatorTemplate>& jumps,
        const DissipationPolicy& policy) {
    int d2 = dim * dim;
    Superoperator D = Superoperator::Zero(d2, d2);
    Operator I = Operator::Identity(dim, dim);

    auto kron = [](const Operator& A, const Operator& B) -> Operator {
        int ar = A.rows(), ac = A.cols();
        int br = B.rows(), bc = B.cols();
        Operator K(ar * br, ac * bc);
        for (int i = 0; i < ar; ++i) {
            for (int j = 0; j < ac; ++j) {
                K.block(i*br, j*bc, br, bc) = A(i,j) * B;
            }
        }
        return K;
    };

    for (const auto& jt : jumps) {
        double gamma = policy.gamma_for(jt.edge_key);
        if (gamma <= 0.0) continue;

        Operator L     = jt.L;
        Operator Ldag  = L.adjoint();
        Operator LdagL = Ldag * L;

        // vec(L rho L^dag): (L^* kron L)
        Operator L_conj = L.conjugate();
        Superoperator term1 = kron(L_conj, L);

        // vec(L^dag L rho): (I kron L^dag L)
        Superoperator term2 = kron(I, LdagL);

        // vec(rho L^dag L): ((L^dag L)^T kron I)
        Operator LdagL_T = LdagL.transpose();
        Superoperator term3 = kron(LdagL_T, I);

        D += gamma * (term1 - 0.5 * term2 - 0.5 * term3);
    }
    return D;
}

/**
 * Exact dissipative channel for step dt, expressed as a superoperator.
 * Caller caches this and invalidates when the policy generation changes.
 */
inline Superoperator build_dissipative_channel(
        int dim,
        const std::vector<JumpOperatorTemplate>& jumps,
        const DissipationPolicy& policy,
        double dt) {
    Superoperator Dsup = build_dissipator_superoperator(dim, jumps, policy);
    Superoperator channel = (Dsup * dt).exp();  // expm via Eigen unsupported
    return channel;
}

/** Apply a channel superoperator to a density matrix. */
inline DensityMatrix apply_channel(const Superoperator& channel,
                                   const DensityMatrix& rho) {
    int d = static_cast<int>(rho.rows());
    int d2 = d * d;
    // Column-major vec of rho
    Eigen::Map<const StateVector> v(rho.data(), d2);
    StateVector w = channel * v;
    DensityMatrix out(d, d);
    Eigen::Map<StateVector>(out.data(), d2) = w;
    return out;
}

} // namespace omq

#endif // OMQ_DISSIPATOR_HPP

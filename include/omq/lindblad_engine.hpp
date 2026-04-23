#ifndef OMQ_LINDBLAD_ENGINE_HPP
#define OMQ_LINDBLAD_ENGINE_HPP

#include "types.hpp"
#include "policy.hpp"
#include "dissipator.hpp"
#include "verify.hpp"
#include <unsupported/Eigen/MatrixFunctions>
#include <memory>
#include <vector>
#include <stdexcept>
#include <iostream>

namespace omq {

/**
 * Lindblad engine with second-order Strang splitting:
 *
 *   rho(t + dt) = U_half * D_full( U_half * rho * U_half^dag ) * U_half^dag
 *
 * where
 *   U_half  = exp(-i H dt / 2)                          (exactly unitary)
 *   D_full  = exp(L_diss * dt)  applied in vec-space    (exactly CPTP)
 *
 * Each sub-block is individually exact, so their composition is CPTP to
 * machine precision. The splitting error is O(dt^2) from [H, L_diss] != 0,
 * which is the expected accuracy floor of a second-order method.
 *
 * Ownership:
 *   - Jump operator *templates* live in the engine.
 *   - Gamma values live exclusively in the DissipationPolicy (shared_ptr
 *     owned by the engine, produced by CurvatureMonitor).
 *   - The dissipator superoperator is cached and rebuilt only when the
 *     policy generation or dt changes.
 */
class LindbladEngine {
public:
    struct Diagnostics {
        std::uint64_t steps = 0;
        std::uint64_t rebuild_dissipator = 0;
        std::uint64_t rebuild_unitary    = 0;
        std::uint64_t verify_failures    = 0;
    };

    LindbladEngine(int dim,
                   std::vector<JumpOperatorTemplate> jumps,
                   PolicyPtr initial_policy = nullptr)
        : dim_(dim), jumps_(std::move(jumps)), policy_(std::move(initial_policy))
    {
        if (dim_ <= 0) throw std::invalid_argument("dim must be > 0");
        for (const auto& jt : jumps_) {
            if (jt.L.rows() != dim_ || jt.L.cols() != dim_) {
                throw std::invalid_argument("jump operator dimension mismatch");
            }
        }
    }

    void set_policy(PolicyPtr p) {
        policy_ = std::move(p);
        // Invalidate dissipator cache
        cached_dissipator_.resize(0, 0);
        cached_generation_ = 0;
        cached_dt_diss_ = -1.0;
    }

    PolicyPtr policy() const { return policy_; }
    const Diagnostics& diagnostics() const { return diag_; }

    /**
     * Evolve rho by dt using the second-order Strang split.
     * Returns a verification report; on failure the caller can inspect
     * the returned state and decide whether to abort / reduce dt / retry.
     */
    VerifyReport evolve_step(DensityMatrix& rho,
                             const Operator& H,
                             double dt,
                             VerifyTolerances tol = VerifyTolerances()) {
        if (rho.rows() != dim_ || rho.cols() != dim_) {
            throw std::invalid_argument("rho dimension mismatch");
        }
        if (H.rows() != dim_ || H.cols() != dim_) {
            throw std::invalid_argument("H dimension mismatch");
        }
        if (dt <= 0.0) throw std::invalid_argument("dt must be > 0");

        // --- build or reuse cached unitary for dt/2 ---
        const Operator& U_half = get_U_half(H, dt);

        // --- build or reuse cached dissipator channel for dt ---
        const Superoperator& D_full = get_D_full(dt);

        // --- Strang split ---
        DensityMatrix r = U_half * rho * U_half.adjoint();
        r = apply_channel(D_full, r);
        r = U_half * r * U_half.adjoint();

        // Verify BEFORE masking asymmetry from roundoff
        VerifyReport rep = verify_density_matrix(r, tol);
        if (!rep.ok) {
            ++diag_.verify_failures;
        }
        // Project away numerical asymmetry so downstream math stays clean.
        // (We do NOT renormalize trace here - that would mask real bugs.)
        symmetrize_inplace(r);

        rho = std::move(r);
        ++diag_.steps;
        return rep;
    }

    /** Accessor for the assembled dissipator superoperator (debug / audit). */
    Superoperator current_dissipator_superop(double dt) {
        return get_D_full(dt);
    }

private:
    int dim_;
    std::vector<JumpOperatorTemplate> jumps_;
    PolicyPtr policy_;

    // --- caches ---
    Superoperator   cached_dissipator_;     // exp(Ldiss * dt)
    std::uint64_t   cached_generation_ = 0;
    double          cached_dt_diss_   = -1.0;

    Operator        cached_U_half_;
    const Operator* cached_H_ptr_ = nullptr;
    double          cached_dt_unit_ = -1.0;

    Diagnostics     diag_{};

    const Operator& get_U_half(const Operator& H, double dt) {
        // Rebuild if H identity or dt changed. H is compared by address + dt;
        // conservative but avoids recomputing a matrix exp on every step.
        if (cached_H_ptr_ != &H || cached_dt_unit_ != dt
            || cached_U_half_.rows() != dim_) {
            Operator arg = Complex(0.0, -1.0) * H * (0.5 * dt);
            cached_U_half_ = arg.exp();
            cached_H_ptr_  = &H;
            cached_dt_unit_ = dt;
            ++diag_.rebuild_unitary;
        }
        return cached_U_half_;
    }

    const Superoperator& get_D_full(double dt) {
        if (!policy_) {
            throw std::runtime_error("LindbladEngine has no policy set");
        }
        bool stale = cached_dissipator_.rows() == 0
                  || cached_generation_ != policy_->generation
                  || cached_dt_diss_    != dt;
        if (stale) {
            cached_dissipator_ = build_dissipative_channel(dim_, jumps_,
                                                           *policy_, dt);
            cached_generation_ = policy_->generation;
            cached_dt_diss_    = dt;
            ++diag_.rebuild_dissipator;
        }
        return cached_dissipator_;
    }
};

} // namespace omq

#endif // OMQ_LINDBLAD_ENGINE_HPP

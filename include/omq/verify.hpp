#ifndef OMQ_VERIFY_HPP
#define OMQ_VERIFY_HPP

#include "types.hpp"
#include <Eigen/Eigenvalues>
#include <cmath>
#include <string>
#include <sstream>

namespace omq {

struct VerifyReport {
    double hermiticity_error;   // ||rho - rho^dagger||_F
    double trace_error;         // |Tr(rho) - 1|
    double min_eigenvalue;      // smallest eigenvalue of (rho + rho^dagger)/2
    bool   ok;                  // all three under tolerance
    std::string detail;

    std::string summary() const {
        std::ostringstream oss;
        oss << "[verify] herm=" << hermiticity_error
            << " trace_err=" << trace_error
            << " min_eig=" << min_eigenvalue
            << " ok=" << (ok ? "true" : "false");
        if (!detail.empty()) oss << " detail=" << detail;
        return oss.str();
    }
};

struct VerifyTolerances {
    double hermiticity = 1e-9;
    double trace       = 1e-9;
    double positivity  = -1e-10; // min eig must be >= this
    VerifyTolerances() = default;
};

inline VerifyReport verify_density_matrix(const DensityMatrix& rho,
                                          VerifyTolerances tol = VerifyTolerances()) {
    VerifyReport rep;
    rep.hermiticity_error = (rho - rho.adjoint()).norm();

    Complex tr = rho.trace();
    rep.trace_error = std::abs(tr - Complex(1.0, 0.0));

    // Symmetrize for eigenvalue check (positivity is defined on Hermitian part)
    Operator rho_sym = 0.5 * (rho + rho.adjoint());
    Eigen::SelfAdjointEigenSolver<Operator> es(rho_sym);
    if (es.info() != Eigen::Success) {
        rep.min_eigenvalue = -1.0;
        rep.ok = false;
        rep.detail = "eigensolver failed";
        return rep;
    }
    rep.min_eigenvalue = es.eigenvalues().minCoeff();

    rep.ok = (rep.hermiticity_error <= tol.hermiticity)
          && (rep.trace_error       <= tol.trace)
          && (rep.min_eigenvalue    >= tol.positivity);

    if (!rep.ok) {
        std::ostringstream oss;
        if (rep.hermiticity_error > tol.hermiticity)
            oss << "non-hermitian ";
        if (rep.trace_error > tol.trace)
            oss << "trace-drift ";
        if (rep.min_eigenvalue < tol.positivity)
            oss << "non-positive ";
        rep.detail = oss.str();
    }
    return rep;
}

/** Project out round-off asymmetry. Does NOT enforce positivity (which would
 *  hide real violations); use only after verify passes. */
inline void symmetrize_inplace(DensityMatrix& rho) {
    rho = 0.5 * (rho + rho.adjoint());
}

/** Rescale to unit trace. Use only after verify passes; this masks bugs. */
inline void renormalize_trace_inplace(DensityMatrix& rho) {
    Complex tr = rho.trace();
    if (std::abs(tr) > 0) rho /= tr.real();
}

} // namespace omq

#endif // OMQ_VERIFY_HPP

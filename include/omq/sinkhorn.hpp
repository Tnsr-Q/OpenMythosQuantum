#ifndef OMQ_SINKHORN_HPP
#define OMQ_SINKHORN_HPP

#include <Eigen/Dense>
#include <cmath>
#include <algorithm>
#include <limits>
#include <stdexcept>

namespace omq {

/**
 * Log-domain Sinkhorn solver for entropy-regularized optimal transport.
 *
 * Inputs:
 *   a, b     : source and target probability vectors (must each sum to ~1)
 *   C        : m x n cost matrix, entries >= 0
 *   epsilon  : regularization strength. Smaller -> closer to true W1, but
 *              slower convergence and more numerical stress.
 *   max_iter : hard iteration cap
 *   tol      : marginal violation L-infinity tolerance for early exit
 *
 * Returns the transport *cost* <T, C>_F where T is the optimal plan.
 *
 * Numerical notes:
 *   - Everything is log-domain (u, v are log-scaled dual potentials). This
 *     avoids overflow for small epsilon.
 *   - The update uses log-sum-exp, guaranteeing monotone marginal error
 *     reduction down to floating-point precision.
 *   - For entropy-regularized OT, the returned cost is an upper bound on
 *     true W1; convergence to W1 is as epsilon -> 0. For our curvature use,
 *     epsilon ~ 0.02 * typical_cost gives <1% bias which is well below the
 *     noise from policy coarse-graining.
 */
class SinkhornSolver {
public:
    struct Result {
        double cost;           // <T, C>
        int    iterations;
        double marginal_error; // final max marginal violation
        bool   converged;
    };

    static Result solve(const Eigen::VectorXd& a,
                        const Eigen::VectorXd& b,
                        const Eigen::MatrixXd& C,
                        double epsilon = 0.05,
                        int    max_iter = 500,
                        double tol = 1e-8) {
        const int m = static_cast<int>(a.size());
        const int n = static_cast<int>(b.size());
        if (C.rows() != m || C.cols() != n) {
            throw std::invalid_argument("Sinkhorn: cost matrix shape mismatch");
        }
        if (epsilon <= 0.0) {
            throw std::invalid_argument("Sinkhorn: epsilon must be > 0");
        }

        // log(a), log(b) with -inf for zero mass
        auto safe_log = [](const Eigen::VectorXd& x) {
            Eigen::VectorXd out(x.size());
            for (int i = 0; i < x.size(); ++i) {
                out(i) = (x(i) > 0.0) ? std::log(x(i))
                                       : -std::numeric_limits<double>::infinity();
            }
            return out;
        };
        Eigen::VectorXd log_a = safe_log(a);
        Eigen::VectorXd log_b = safe_log(b);

        // Kernel in log-domain: K_log[i,j] = -C[i,j] / epsilon
        Eigen::MatrixXd K_log = -C / epsilon;

        Eigen::VectorXd u = Eigen::VectorXd::Zero(m); // log potentials
        Eigen::VectorXd v = Eigen::VectorXd::Zero(n);

        auto log_sum_exp_row = [&](int i, const Eigen::VectorXd& v_cur) {
            // logsumexp over j of (K_log[i,j] + v_cur[j])
            double mx = -std::numeric_limits<double>::infinity();
            for (int j = 0; j < n; ++j) {
                double x = K_log(i,j) + v_cur(j);
                if (x > mx) mx = x;
            }
            if (mx == -std::numeric_limits<double>::infinity()) return mx;
            double s = 0.0;
            for (int j = 0; j < n; ++j) {
                s += std::exp(K_log(i,j) + v_cur(j) - mx);
            }
            return mx + std::log(s);
        };
        auto log_sum_exp_col = [&](int j, const Eigen::VectorXd& u_cur) {
            double mx = -std::numeric_limits<double>::infinity();
            for (int i = 0; i < m; ++i) {
                double x = K_log(i,j) + u_cur(i);
                if (x > mx) mx = x;
            }
            if (mx == -std::numeric_limits<double>::infinity()) return mx;
            double s = 0.0;
            for (int i = 0; i < m; ++i) {
                s += std::exp(K_log(i,j) + u_cur(i) - mx);
            }
            return mx + std::log(s);
        };

        Result res{0.0, 0, 0.0, false};
        for (int it = 0; it < max_iter; ++it) {
            for (int i = 0; i < m; ++i) {
                u(i) = log_a(i) - log_sum_exp_row(i, v);
            }
            for (int j = 0; j < n; ++j) {
                v(j) = log_b(j) - log_sum_exp_col(j, u);
            }

            // Marginal check every few iterations (expensive to do every pass)
            if ((it % 10 == 9) || (it == max_iter - 1)) {
                double err = 0.0;
                for (int i = 0; i < m; ++i) {
                    double row_sum = 0.0;
                    for (int j = 0; j < n; ++j) {
                        row_sum += std::exp(u(i) + K_log(i,j) + v(j));
                    }
                    err = std::max(err, std::abs(row_sum - a(i)));
                }
                if (err < tol) {
                    res.iterations = it + 1;
                    res.marginal_error = err;
                    res.converged = true;
                    break;
                }
                res.iterations = it + 1;
                res.marginal_error = err;
            }
        }

        // Compute transport cost <T, C>
        double cost = 0.0;
        for (int i = 0; i < m; ++i) {
            for (int j = 0; j < n; ++j) {
                double T_ij = std::exp(u(i) + K_log(i,j) + v(j));
                cost += T_ij * C(i,j);
            }
        }
        res.cost = cost;
        return res;
    }
};

} // namespace omq

#endif // OMQ_SINKHORN_HPP

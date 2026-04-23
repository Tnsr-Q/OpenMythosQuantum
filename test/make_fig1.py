"""Generate Figure 1 for the Phase D manuscript: spectral gap vs alpha
showing the Ricci-Dissipation Consistency threshold.

Output: phase_d_fig1.pdf
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

data = np.genfromtxt("phase_d_gap_scan.csv", delimiter=",", skip_header=1)
alpha       = data[:, 0]
gamma_br    = data[:, 1]
gap_num     = data[:, 3]
gap_cheeger = data[:, 4]

kappa_bridge_abs = 1.0 / 3.0
alpha_crit = 1.0 / kappa_bridge_abs  # = 3

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.3))

# Left panel: gap vs alpha
ax1.loglog(alpha, gap_num, "o-", color="#1f77b4", lw=1.6, ms=4,
           label=r"Numerical gap $\lambda_1(-Q)$")
ax1.loglog(alpha, gap_cheeger, "s--", color="#d62728", lw=1.2, ms=3,
           label=r"Cheeger bound $\Phi^2/2$")

# Linear-response asymptote: gap ~ (2/3) gamma_bridge = (2/3) alpha |kappa|
lr_asymptote = (2.0/3.0) * alpha * kappa_bridge_abs
ax1.loglog(alpha, lr_asymptote, ":", color="gray", lw=1.3,
           label=r"Linear response: $\frac{2}{3}\alpha|\kappa|$")

ax1.axvline(alpha_crit, color="k", ls="--", alpha=0.5, lw=1)
ax1.text(alpha_crit*1.1, 5e-4, r"$\alpha_c = 1/|\kappa|$",
         rotation=90, va="bottom", fontsize=9)

ax1.set_xlabel(r"Coupling $\alpha$  in  $\gamma_{e} = \alpha \max(0, -\kappa_e)$")
ax1.set_ylabel(r"Spectral gap $\lambda_1(-Q)$")
ax1.set_title("Bowtie graph: shadow-RW gap under Phase C mapping")
ax1.legend(loc="upper left", fontsize=9, framealpha=0.95)
ax1.grid(True, which="both", alpha=0.25)

# Right panel: same on linear axes, annotated
mask = alpha <= 6.0
ax2.plot(alpha[mask], gap_num[mask], "o-", color="#1f77b4", lw=1.6, ms=4)
ax2.axvline(alpha_crit, color="k", ls="--", alpha=0.5, lw=1)
ax2.axhline(gap_num[mask][-1], color="#2ca02c", ls=":", lw=1, alpha=0.6)
ax2.annotate(r"Bottleneck-dominated: $\lambda_1 \propto \alpha$",
             xy=(0.8, 0.2), xytext=(0.6, 0.38),
             fontsize=9,
             arrowprops=dict(arrowstyle="->", color="gray"))
ax2.annotate(r"Saturation: $\lambda_1 \to \lambda_{\rm interior}$",
             xy=(5.0, 0.53), xytext=(3.5, 0.35),
             fontsize=9,
             arrowprops=dict(arrowstyle="->", color="gray"))
ax2.text(alpha_crit*1.05, 0.08, r"$\alpha_c$",
         va="bottom", fontsize=10)

ax2.set_xlabel(r"$\alpha$")
ax2.set_ylabel(r"Spectral gap")
ax2.set_title("Phase transition at the consistency threshold")
ax2.set_xlim(0, 5.5)
ax2.set_ylim(0, 0.62)
ax2.grid(True, alpha=0.25)

plt.tight_layout()
plt.savefig("phase_d_fig1.pdf", dpi=200, bbox_inches="tight")
plt.savefig("phase_d_fig1.png", dpi=150, bbox_inches="tight")
print("Wrote phase_d_fig1.pdf and phase_d_fig1.png")

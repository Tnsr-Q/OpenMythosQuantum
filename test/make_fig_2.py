"""Generate Figure 2 for Phase D universality study.

Three panels:
  (a) Raw gap vs alpha, colored by graph.
  (b) Rescaled gap/|k_min| vs alpha*|k_min| -- partial collapse.
  (c) Measured alpha_c vs predicted 1/|k_min|; shows systematic drift.

Output: phase_d_fig2.pdf / phase_d_fig2.png
"""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Load raw CSV
rows = []
with open("phase_d_universality.csv") as f:
    f.readline()
    for line in f:
        p = line.strip().split(",")
        rows.append({
            "graph": p[0],
            "alpha": float(p[1]),
            "kappa_min": float(p[2]),
            "alpha_rescaled": float(p[3]),
            "gap": float(p[4]),
            "gap_rescaled": float(p[5]),
            "num_neg": int(p[6]),
        })

graphs = sorted(set(r["graph"] for r in rows))

style_map = {
    "G1a_K3-K3":              ("#1f77b4", "o", "K3-K3 (1 bridge)"),
    "G1b_K4-K4":              ("#2a5ba8", "s", "K4-K4 (1 bridge)"),
    "G1c_K5-K5":              ("#3a3f9f", "^", "K5-K5 (1 bridge)"),
    "G2_P6_control":          ("#7f7f7f", "x", "P_6 (control)"),
    "G3a_K3-K3_ladder":       ("#d62728", "D", "K3-K3 ladder (4 neg)"),
    "G3b_K3-path-K3":         ("#ff7f0e", "v", "K3-path-K3 (2 neg, series)"),
    "G4_K3-K5":               ("#2ca02c", "p", "K3-K5 (asymmetric)"),
}

fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.4))
ax1, ax2, ax3 = axes

# (a) Raw
for g in graphs:
    color, marker, label = style_map.get(g, ("#888888", "o", g))
    data = [r for r in rows if r["graph"] == g]
    a = np.array([r["alpha"] for r in data])
    y = np.array([r["gap"] for r in data])
    ax1.loglog(a, y, marker=marker, color=color, ms=4, lw=1.1, label=label, alpha=0.85)
ax1.set_xlabel(r"Coupling $\alpha$")
ax1.set_ylabel(r"Spectral gap $\lambda_1(-Q)$")
ax1.set_title("(a) Raw gap across 7 graphs")
ax1.grid(True, which="both", alpha=0.25)
ax1.legend(loc="lower right", fontsize=7.5, framealpha=0.95)

# (b) Rescaled
for g in graphs:
    if "control" in g: continue
    color, marker, label = style_map.get(g, ("#888888", "o", g))
    data = [r for r in rows if r["graph"] == g]
    x = np.array([r["alpha_rescaled"] for r in data])
    y = np.array([r["gap_rescaled"]   for r in data])
    ax2.loglog(x, y, marker=marker, color=color, ms=4, lw=1.1, label=label, alpha=0.85)

ax2.axvline(1.0, color="k", ls="--", alpha=0.5, lw=1)
ax2.text(1.05, 2e-3, r"$\alpha|\kappa_{\min}|{=}1$",
         fontsize=8, rotation=90, va="bottom")
x_line = np.logspace(-4, 0, 50)
ax2.loglog(x_line, (2.0/3.0) * x_line, "k:", lw=1.0, alpha=0.5,
           label=r"$(2/3)\,\alpha|\kappa|$")
ax2.set_xlabel(r"$\alpha\,|\kappa_{\min}|$")
ax2.set_ylabel(r"$\lambda_1 / |\kappa_{\min}|$")
ax2.set_title("(b) Partial collapse under rescaling")
ax2.grid(True, which="both", alpha=0.25)
ax2.legend(loc="lower right", fontsize=7.5, framealpha=0.95)

# (c) Critical alpha: measured vs predicted
def find_alpha_c(data):
    a = np.array([r["alpha"] for r in data])
    g = np.array([r["gap"]   for r in data])
    gap_sat = g[-1]
    half = 0.5 * gap_sat
    idx = np.argmax(g >= half)
    if g[idx] < half or idx == 0:
        return None
    la, lb = np.log(a[idx-1]), np.log(a[idx])
    ya, yb = g[idx-1], g[idx]
    t = (half - ya) / (yb - ya) if yb != ya else 0.0
    return float(np.exp(la + t * (lb - la)))

measured = []
for g in graphs:
    if "control" in g: continue
    data = [r for r in rows if r["graph"] == g]
    if not data: continue
    k_min = data[0]["kappa_min"]
    if k_min > -1e-6: continue
    a_c = find_alpha_c(data)
    pred = 1.0 / abs(k_min)
    if a_c is None: continue
    measured.append((g, pred, a_c))

xs_pred = [m[1] for m in measured]
ys_meas = [m[2] for m in measured]
for (g, xp, ym) in measured:
    color, marker, lab = style_map.get(g, ("#888888", "o", g))
    ax3.loglog([xp], [ym], marker=marker, color=color, ms=10, mec="black",
               mew=0.6, label=lab)

lo = 0.8 * min(min(xs_pred), min(ys_meas))
hi = 1.2 * max(max(xs_pred), max(ys_meas))
x_diag = np.logspace(np.log10(lo), np.log10(hi), 50)
ax3.loglog(x_diag, x_diag, "k--", lw=1, alpha=0.5,
           label=r"$\alpha_c^{\rm meas}=\alpha_c^{\rm pred}$")
ax3.loglog(x_diag, 1.5*x_diag, "k:", lw=0.8, alpha=0.35)
ax3.loglog(x_diag, 2.0*x_diag, "k:", lw=0.8, alpha=0.35)
ax3.text(3.5, 3.5*1.5, r"$1.5\times$", fontsize=7.5, color="gray", rotation=32)
ax3.text(2.2, 2.2*2.0, r"$2\times$",   fontsize=7.5, color="gray", rotation=32)

ax3.set_xlabel(r"Predicted $\alpha_c = 1/|\kappa_{\min}|$")
ax3.set_ylabel(r"Measured $\alpha_c$")
ax3.set_title("(c) $\\alpha_c$: measured vs predicted")
ax3.grid(True, which="both", alpha=0.25)
ax3.legend(loc="upper left", fontsize=7, framealpha=0.95)
ax3.set_xlim(lo, hi); ax3.set_ylim(lo, hi)

plt.tight_layout()
plt.savefig("phase_d_fig2.pdf", dpi=200, bbox_inches="tight")
plt.savefig("phase_d_fig2.png", dpi=150, bbox_inches="tight")
print("Wrote phase_d_fig2.pdf / .png")

print("\nalpha_c ratios (measured / predicted):")
for g, pred, meas in measured:
    print(f"  {g:30s}  pred={pred:6.3f}  meas={meas:6.3f}  ratio={meas/pred:5.3f}")

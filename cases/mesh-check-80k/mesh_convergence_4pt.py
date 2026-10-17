#!/usr/bin/env python
"""
Extended S809 (Re=2e6, CST pipeline) mesh convergence plot -- 10k/20k/40k/80k
cells, baseline vs optimized CD (each trimmed to CL=0.4), and the drag
reduction percentage vs mesh resolution.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

cells = [10270, 20792, 41340, 81984]
labels = ["10,270 cells\n(optimization mesh)", "20,792 cells\n(2x refined)",
          "41,340 cells\n(4x refined)", "81,984 cells\n(8x refined)"]
cd_base = [0.020615, 0.019537, 0.018995, 0.018665]
cd_opt = [0.016042, 0.015500, 0.015197, 0.015032]
reduction = [(b - o) / b * 100.0 for b, o in zip(cd_base, cd_opt)]

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("S809 CST Optimization — Mesh Sensitivity Check (10k / 20k / 40k / 80k cells)", fontsize=15)

# ---------------------------------------------------------------------------
# Left panel: grouped bar chart, baseline vs optimized CD per mesh
# ---------------------------------------------------------------------------
ax = axes[0]
x = np.arange(len(cells))
width = 0.35
ax.bar(x - width / 2, cd_base, width, label="Baseline", color="0.6")
ax.bar(x + width / 2, cd_opt, width, label="Optimized", color="#1f77b4")
for i, (b, o, pct) in enumerate(zip(cd_base, cd_opt, reduction)):
    ax.text(i, b + 0.0006, f"{b:.4f}", ha="center", fontsize=9)
    ax.text(i, o + 0.0006, f"{o:.4f}", ha="center", fontsize=9)
    ax.text(i, max(b, o) + 0.0022, f"-{pct:.1f}%", ha="center", fontsize=12,
            fontweight="bold", color="#d62728")
ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=9)
ax.set_ylabel("$C_D$ (trimmed to $C_L$ = 0.4)")
ax.set_title("S809, Re=2$\\times$10$^6$: Drag Reduction vs. Mesh Resolution")
ax.set_ylim(0, max(cd_base) * 1.25)
ax.legend(loc="lower right")

# ---------------------------------------------------------------------------
# Right panel: drag reduction % vs mesh cell count
# ---------------------------------------------------------------------------
ax = axes[1]
ax.plot(cells, reduction, "o-", color="#d62728", linewidth=2, markersize=10)
for c, r in zip(cells, reduction):
    ax.annotate(f"{r:.2f}%", (c, r), textcoords="offset points", xytext=(0, 12),
                ha="center", fontsize=11, fontweight="bold")
ax.set_xlabel("Mesh cell count")
ax.set_ylabel("Drag reduction, baseline $\\to$ optimized (%)")
ax.set_title("Mesh-Sensitivity Check: Reduction Holds Under Refinement")
ax.set_ylim(0, 30)
ax.set_xlim(5000, 90000)
ax.grid(True, alpha=0.3)

fig.tight_layout(rect=(0, 0, 1, 0.94))
fig.savefig("mesh_sensitivity_comparison_4pt.png", dpi=150)
print("Wrote mesh_sensitivity_comparison_4pt.png")

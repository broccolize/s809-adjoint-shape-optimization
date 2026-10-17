#!/usr/bin/env python
"""
Plot CD-vs-AoA and CL-vs-AoA polars from aoa_sweep_results.json, baseline vs
optimized S809 CST shapes overlaid (Re=2e6, 10k-cell mesh, no CL trim).
"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

with open("aoa_sweep_results.json", "r", encoding="utf-8") as fh:
    results = json.load(fh)

aoa_base = [pt["aoa"] for pt in results["baseline"]]
cd_base = [pt["CD"] for pt in results["baseline"]]
cl_base = [pt["CL"] for pt in results["baseline"]]

aoa_opt = [pt["aoa"] for pt in results["optimized"]]
cd_opt = [pt["CD"] for pt in results["optimized"]]
cl_opt = [pt["CL"] for pt in results["optimized"]]

BASE_COLOR = "#1f77b4"
OPT_COLOR = "#d62728"

# ---------------------------------------------------------------------------
# CD vs AoA
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(aoa_base, cd_base, "o-", color=BASE_COLOR, label="Baseline", linewidth=2, markersize=6)
ax.plot(aoa_opt, cd_opt, "s-", color=OPT_COLOR, label="Optimized", linewidth=2, markersize=6)
ax.set_xlabel("Angle of attack [deg]")
ax.set_ylabel("$C_D$")
ax.set_title("S809 (Re=2e6): $C_D$ vs AoA, baseline vs optimized")
ax.grid(True, alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig("plots/aoa_sweep_cd.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# CL vs AoA
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(aoa_base, cl_base, "o-", color=BASE_COLOR, label="Baseline", linewidth=2, markersize=6)
ax.plot(aoa_opt, cl_opt, "s-", color=OPT_COLOR, label="Optimized", linewidth=2, markersize=6)
ax.axhline(0.4, color="gray", linestyle="--", linewidth=1, label="Design $C_L$ = 0.4")
ax.set_xlabel("Angle of attack [deg]")
ax.set_ylabel("$C_L$")
ax.set_title("S809 (Re=2e6): $C_L$ vs AoA, baseline vs optimized")
ax.grid(True, alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig("plots/aoa_sweep_cl.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------------------
# Drag polar (CD vs CL)
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 5))
ax.plot(cl_base, cd_base, "o-", color=BASE_COLOR, label="Baseline", linewidth=2, markersize=6)
ax.plot(cl_opt, cd_opt, "s-", color=OPT_COLOR, label="Optimized", linewidth=2, markersize=6)
ax.axvline(0.4, color="gray", linestyle="--", linewidth=1, label="Design $C_L$ = 0.4")
ax.set_xlabel("$C_L$")
ax.set_ylabel("$C_D$")
ax.set_title("S809 (Re=2e6): drag polar, baseline vs optimized")
ax.grid(True, alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig("plots/aoa_sweep_drag_polar.png", dpi=150)
plt.close(fig)

print("Wrote plots/aoa_sweep_cd.png, plots/aoa_sweep_cl.png, plots/aoa_sweep_drag_polar.png")

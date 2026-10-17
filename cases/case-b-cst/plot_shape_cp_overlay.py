#!/usr/bin/env python
"""
Baseline-vs-optimized S809 shape + Cp overlay (Re=2e6, CST/docker pipeline,
10k-cell mesh, both trimmed to CL=0.4).

Pulls airfoil surface geometry and Cp directly from each case's own solved
VTK surface mesh (no analytic CST reconstruction), so what's plotted is
exactly what the solver saw:
  - baseline: ../aoa-sweep/VTK_baseline/boundary.vtp
  - optimized: ./VTK/boundary.vtp (this case's converged optimization result)

Cp convention matches step5_analyze.sh: incompressible (DASimpleFoam), p is
kinematic, reference_pressure=0, Cp scale = 0.5*rho*U0^2 = 450.
"""
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

P_REF = 0.0
CP_SCALE = 450.0

BASE_COLOR = "#1f77b4"
OPT_COLOR = "#d62728"

BASELINE_VTP = "../aoa-sweep/VTK_baseline/boundary.vtp"
OPTIMIZED_VTP = "VTK/boundary.vtp"


def load_wing_surface(path):
    """Return (x, z, Cp) for the wing-patch cell centroids, sorted around the
    perimeter. Wing cells are identified geometrically: they span both
    spanwise symmetry planes (y=0 and y=0.01), unlike the flat symmetry-plane
    cells which lie entirely within one plane."""
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(path)
    reader.Update()
    poly = reader.GetOutput()
    pts = vtk_to_numpy(poly.GetPoints().GetData())
    p = vtk_to_numpy(poly.GetCellData().GetArray("p"))

    n_cells = poly.GetNumberOfCells()
    wing_mask = np.zeros(n_cells, dtype=bool)
    centroids = np.zeros((n_cells, 3))
    for i in range(n_cells):
        cell = poly.GetCell(i)
        ids = [cell.GetPointId(j) for j in range(cell.GetNumberOfPoints())]
        ys = pts[ids, 1]
        centroids[i] = pts[ids].mean(axis=0)
        wing_mask[i] = not np.allclose(ys, ys[0], atol=1e-9)

    x = centroids[wing_mask, 0]
    z = centroids[wing_mask, 2]
    cp = (p[wing_mask] - P_REF) / CP_SCALE

    # Trace the perimeter by greedy nearest-neighbor walk starting at the
    # leading edge. Angle-about-centroid sorting is unstable right at the
    # blunt trailing edge (upper/lower points end up at nearly the same
    # angle and interleave into a zigzag); a nearest-neighbor walk follows
    # the actual boundary regardless of local point density.
    n = len(x)
    remaining = set(range(n))
    start = int(np.argmin(x))
    order = [start]
    remaining.discard(start)
    cur = start
    pts = np.column_stack([x, z])
    while remaining:
        rem_idx = np.array(list(remaining))
        d = np.hypot(pts[rem_idx, 0] - pts[cur, 0], pts[rem_idx, 1] - pts[cur, 1])
        nxt = rem_idx[np.argmin(d)]
        order.append(nxt)
        remaining.discard(nxt)
        cur = nxt
    order = np.array(order)
    return x[order], z[order], cp[order]


def split_surfaces(x, z, cp):
    """Split the traced perimeter (starting at the leading edge) into upper
    and lower surfaces at the trailing-edge point (max x), each sorted by x
    for a clean Cp-vs-x/c line plot."""
    te_idx = int(np.argmax(x))
    first, second = slice(0, te_idx + 1), slice(te_idx, len(x))
    surf_a = (x[first], z[first], cp[first])
    surf_b = (x[second], z[second], cp[second])
    # Whichever half has the larger mean z is "upper".
    if surf_a[1].mean() >= surf_b[1].mean():
        upper, lower = surf_a, surf_b
    else:
        upper, lower = surf_b, surf_a
    uo = np.argsort(upper[0])
    lo = np.argsort(lower[0])
    ux, uz, ucp = upper[0][uo], upper[1][uo], upper[2][uo]
    lx, lz, lcp = lower[0][lo], lower[1][lo], lower[2][lo]
    return (ux, uz, ucp), (lx, lz, lcp)


x_b, z_b, cp_b = load_wing_surface(BASELINE_VTP)
x_o, z_o, cp_o = load_wing_surface(OPTIMIZED_VTP)
(ux_b, uz_b, ucp_b), (lx_b, lz_b, lcp_b) = split_surfaces(x_b, z_b, cp_b)
(ux_o, uz_o, ucp_o), (lx_o, lz_o, lcp_o) = split_surfaces(x_o, z_o, cp_o)

fig, axes = plt.subplots(2, 1, figsize=(9, 9), sharex=True,
                          gridspec_kw={"height_ratios": [1, 2]})
fig.suptitle("S809 (Re=2e6): Baseline vs Optimized — Shape and $C_p$ (both trimmed to $C_L$=0.4)",
             fontsize=13)

# ---------------------------------------------------------------------------
# Top: airfoil shape overlay
# ---------------------------------------------------------------------------
ax = axes[0]
ax.plot(np.concatenate([ux_b, lx_b[::-1]]), np.concatenate([uz_b, lz_b[::-1]]),
        "-", color=BASE_COLOR, linewidth=1.8, label="Baseline")
ax.plot(np.concatenate([ux_o, lx_o[::-1]]), np.concatenate([uz_o, lz_o[::-1]]),
        "-", color=OPT_COLOR, linewidth=1.8, label="Optimized")
ax.set_ylabel("$z/c$")
ax.set_aspect("equal")
ax.grid(True, alpha=0.3)
ax.legend(loc="upper right")
ax.set_title("Airfoil shape (from solved surface mesh)")

# ---------------------------------------------------------------------------
# Bottom: Cp vs x/c, upper/lower surfaces, Cp axis inverted (aero convention)
# ---------------------------------------------------------------------------
ax = axes[1]
ax.plot(ux_b, ucp_b, "-", color=BASE_COLOR, linewidth=2, label="Baseline, upper")
ax.plot(lx_b, lcp_b, "--", color=BASE_COLOR, linewidth=2, label="Baseline, lower")
ax.plot(ux_o, ucp_o, "-", color=OPT_COLOR, linewidth=2, label="Optimized, upper")
ax.plot(lx_o, lcp_o, "--", color=OPT_COLOR, linewidth=2, label="Optimized, lower")
ax.invert_yaxis()
ax.set_xlabel("$x/c$")
ax.set_ylabel("$C_p$")
ax.grid(True, alpha=0.3)
ax.legend(loc="lower right", ncol=2, fontsize=9)
ax.set_title("Surface pressure distribution")

fig.tight_layout(rect=(0, 0, 1, 0.96))
fig.savefig("plots/shape_cp_overlay.png", dpi=150)
print("Wrote plots/shape_cp_overlay.png")
print(f"Baseline wing cells: {len(x_b)}, Optimized wing cells: {len(x_o)}")

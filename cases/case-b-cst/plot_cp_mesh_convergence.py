#!/usr/bin/env python
"""
S809 (Re=2e6, CST pipeline) optimized-shape Cp profile across mesh
resolutions (10k/20k/40k/80k cells), overlaid on one plot -- a direct visual
check that the pressure distribution itself (not just integrated CD) is
mesh-independent.

Pulls Cp directly from each mesh's own solved VTK surface mesh (same
extraction method as plot_shape_cp_overlay.py).
"""
import vtk
from vtk.util.numpy_support import vtk_to_numpy
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

P_REF = 0.0
CP_SCALE = 450.0

CASES = [
    ("10k",  "VTK/boundary.vtp", 10270, "#1f77b4"),
    ("20k",  "../mesh-check-20k/VTK/boundary.vtp", 20792, "#ff7f0e"),
    ("40k",  "../mesh-check-40k/VTK/boundary.vtp", 41340, "#2ca02c"),
    ("80k",  "../mesh-check-80k/VTK/boundary.vtp", 81984, "#d62728"),
]


def load_wing_surface(path):
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

    # Greedy nearest-neighbor perimeter trace from the leading edge (robust
    # at the blunt trailing edge, unlike angle-about-centroid sorting).
    n = len(x)
    remaining = set(range(n))
    start = int(np.argmin(x))
    order = [start]
    remaining.discard(start)
    cur = start
    pts2 = np.column_stack([x, z])
    while remaining:
        rem_idx = np.array(list(remaining))
        d = np.hypot(pts2[rem_idx, 0] - pts2[cur, 0], pts2[rem_idx, 1] - pts2[cur, 1])
        nxt = rem_idx[np.argmin(d)]
        order.append(nxt)
        remaining.discard(nxt)
        cur = nxt
    order = np.array(order)
    return x[order], z[order], cp[order]


def split_surfaces(x, z, cp):
    te_idx = int(np.argmax(x))
    first, second = slice(0, te_idx + 1), slice(te_idx, len(x))
    surf_a = (x[first], z[first], cp[first])
    surf_b = (x[second], z[second], cp[second])
    if surf_a[1].mean() >= surf_b[1].mean():
        upper, lower = surf_a, surf_b
    else:
        upper, lower = surf_b, surf_a
    uo = np.argsort(upper[0])
    lo = np.argsort(lower[0])
    return (upper[0][uo], upper[1][uo], upper[2][uo]), (lower[0][lo], lower[1][lo], lower[2][lo])


fig, ax = plt.subplots(figsize=(9, 7))
for label, path, ncells, color in CASES:
    x, z, cp = load_wing_surface(path)
    (ux, uz, ucp), (lx, lz, lcp) = split_surfaces(x, z, cp)
    ax.plot(ux, ucp, "-", color=color, linewidth=1.8, label=f"{label} ({ncells:,} cells)")
    ax.plot(lx, lcp, "--", color=color, linewidth=1.8)

ax.invert_yaxis()
ax.set_xlabel("$x/c$")
ax.set_ylabel("$C_p$")
ax.set_title("S809 (Re=2e6), Optimized Shape: $C_p$ vs Mesh Resolution\n(solid = upper surface, dashed = lower surface)")
ax.grid(True, alpha=0.3)
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig("plots/cp_mesh_convergence_optimized.png", dpi=150)
print("Wrote plots/cp_mesh_convergence_optimized.png")

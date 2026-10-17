# Recorded results and evidence audit

## What was checked

`tools/reproduce_results.py` audits the supplied artifacts and reconstructs:

1. Initial/final physical CD and CL for both optimization cases, matched to IPOPT objective values.
2. The four CST mesh-sensitivity rows, including generated mesh cell counts from logs.
3. All 18 angle-sweep JSON records against the corresponding printed solver results.
4. Final physical CD/CL per recorded primal solve for each optimization history.

The source manifest checks SHA-256 hashes of copied/normalized files and verifies that archived log compression is lossless. CSV generation and plotting were run during repository preparation. No new primal, adjoint, mesh-generation, gradient-check or optimization run was performed.

## Baseline and optimum selection

Startup flow solves do not necessarily satisfy the intended lift. Selecting the first plausible CD in a log can produce the wrong reference. The audit instead reads IPOPT iteration zero and its final objective, removes the objective scale (1 for FFD, 10 for CST), and matches the physical solver states to those values. This also avoids mistaking a later post-optimization replay for the optimizer's final accepted state.

The selected original primal IDs are 5/32 for the FFD baseline/optimum and 5/17 for CST. The recorded replay at CST primal 18 has a slightly different CD; it is kept in the history but is not substituted for IPOPT's final state. The CSVs retain more digits than the original report.

The CST baseline CD is 0.0206158180567 at CL 0.400227422893; the original report gives a nearby, shorter baseline value 0.020615. Its optimized CD is 0.0160418475794 at CL 0.400016759422. Both yield the reported approximately 22.2% benefit, but their displayed final digits should not be treated as identical. The README uses the states reconstructed by the documented rule rather than silently editing the saved logs or forcing an exact table match.

## Mesh checks and rounding

The 20k/40k/80k log summaries print CD and CL to six decimal places. Recomputing percentages from those displayed values gives approximately 20.6634%, 19.9947% and 19.4642%; the historical logs printed 20.66%, 19.99% and 19.47% from their internal values. Thus **19.46% in the reconstructed table, 19.47% in the log, and 19.5% in the report/CV describe the same finest-mesh check at different precision**. The audit does not invent additional precision for the underlying coefficients.

The coarsest row uses the optimization states above; finer rows use the printed mesh-check results. Lift trim was finite-tolerance, not exact: on the finest mesh the baseline CL is 0.399949 and optimized CL is 0.399737. The evaluation script uses a trim tolerance of 1e-3. These qualifications matter when interpreting small changes between meshes.

The retained drag benefit and shifting absolute CD values support a mesh-sensitivity observation. They do not, by themselves, establish a formal grid-independence error bound, GCI or experimental agreement. The unchanged original report uses stronger language about mesh independence; the README deliberately qualifies that interpretation.

## CST geometry correspondence needs verification

The packaging audit compared the input profile with the archived baseline and optimized boundary surfaces used by the original shape/pressure plotting script. The input profile ranges approximately from z/c = -0.10818 to 0.10183. The baseline wing-face centroids range from -0.15871 to 0.14617, despite a similar unit-chord streamwise range. Those are different sampling representations, but the large vertical-envelope discrepancy merits investigation; it is not treated as a negligible fit error.

The cause is not established. Geometry setup, deformation state or which surface was exported could be involved; these are possibilities, not a diagnosis. The recorded integrated coefficients remain traceable to their logs, but that alone does not establish that the CST flow geometry matches the intended S809 input.

`tools/check_surface_geometry.py` reads the two included boundary VTP files using Python's standard library, extracts wing-face centroids and pressure, and regenerates `data/*-geometry.csv`, `data/surface-geometry-audit.json` and the optional diagnostic plot. It reports `needs_geometry_verification`; passing the software's artifact checks is not a scientific validation pass. Envelope bounds are not maximum-section-thickness calculations. Resolve this correspondence and rerun affected cases before presenting the CST results as validated S809 performance.

## Pressure and sweep limitations

- The separate 80k baseline pressure evaluation was stopped without a valid pressure-profile result. The original baseline pressure overlay includes only the 10k/20k/40k cases. The successful, separate baseline drag/lift mesh-check result remains included.
- The baseline sweep has a non-monotonic CL change from 0° to 2°. The original report suggests under-convergence. That is a hypothesis; no rerun establishing its cause is included.
- Some pressure-overlay scripts expect `VTK/boundary.vtp`, whereas the original 80k folder retains a `VTK_optimized_backup` directory. The plot PNGs are historical artifacts; the current source folder does not independently guarantee every plotting path can be re-executed unchanged. Full volume and finer-mesh surface dumps are excluded; the two coarse boundary exports used for the geometry diagnostic are included explicitly.
- Original optimization scripts print aggregate residual diagnostics as well as functional convergence information. The packaging audit matches recorded outputs, not an independent point-by-point convergence adjudication. Review residuals and coefficient stability before using these results as validated reference data.

## Not a parameterization ranking

The FFD and CST studies differ in Reynolds number, mesh, wall treatment, constraint implementation and solver environment. FFD has direct pyGeo thickness/volume/leading-edge geometric constraints; CST uses coefficient-difference bounds, a leading-edge continuity relation and VSP volume. In particular, the CST variable named `le_radius_constraint` bounds a leading CST coefficient difference; it is not an independent geometric-radius measurement. The two constraint systems should not be described as identical.

Both optimizer receipts report an optimum within their configured tolerances, but that does not establish global optimality or prove that a particular constraint is the only reason further improvement stopped. No claim that CST is intrinsically better than FFD, or that a matched comparison was executed, is made.

## Packaging changes

The original folder was read without modification. In the copy, case folders were renamed, sibling paths updated, stale NACA0012/E205 comments corrected, shell environment initialization made configurable, and cleanup restricted to marked working copies. The numerical case settings and archived log bytes were retained. Unrelated generic SBO/multipoint runners, unused solver templates, generated meshes/fields, cached Jacobians, history binaries, duplicate plots and connection settings are excluded. Added audit/staging tools and README documentation were prepared with AI assistance after the original study.

# Reproduction guide

## Two levels of reproduction

The lightweight audit reconstructs saved numbers and four summary figures. A separate standard-library surface check reproduces the geometry diagnostic and its optional plot. Both were run during packaging. Full CFD reproduction means rebuilding meshes and executing the optimization/evaluation scripts in their compatible solver environments; that was not run during packaging. The archived CST baseline's correspondence to the input profile remains unresolved; see the results audit before interpreting that case as validated S809 geometry.

Run all commands from the repository root unless a `cd` is shown. On Windows, the analysis and staging tools run in Python; solver commands require Linux/WSL or an appropriate container. No Docker image is downloaded or assumed by this repository.

## Recorded environments

- Case A's log reports DAFoam 4.0.4 and OpenFOAM v1812.
- Case B and its follow-up cases report DAFoam 5.0.0 and OpenFOAM v2506. The log paths show a Python 3.10 installation, but do not establish a complete environment lock.
- Both IPOPT receipts identify version 3.13.5 with MUMPS.
- Exact MPhys, pyGeo, pyHyp, OpenVSP, pyOptSparse, NumPy and MDO Agent Deck versions and container image digests are not established by the archived evidence. Do not assume the newest environment reproduces an older case unchanged.

Consult [DAFoam installation](https://dafoam.github.io/) and the [MDO Agent Deck documentation](https://dafoam.github.io/ai-agent-installation.html) for external software. Current instructions may describe versions newer than the recorded runs. The `mdo_agent_airfoil`, `mdo_agent_mesh`, `mdo_agent_base` and `airfoil_assets` modules are required by the CST preparation/analysis wrappers. They are separately installed external dependencies, not included implementation code.

Before invoking a shell wrapper, activate the correct environment. The wrapper's helper accepts `DAFOAM_ENV` pointing to an initialization script, uses the historical `/home/dafoamuser/dafoam/loadDAFoam.sh` if present, or accepts an already activated OpenFOAM environment. It does not guarantee that an arbitrary active environment has compatible Python APIs.

## Case A: FFD optimization

```bash
python tools/stage_case.py case-a-ffd
cd runs/case-a-ffd

# The packaged profiles and FFD lattice are already present. These commands
# explicitly regenerate them if desired, using their expected working folders.
(cd profiles && python process_s809.py)
(cd FFD && python genFFD.py)
bash preProcessing.sh
set -o pipefail
mpirun -np 4 python runScript.py -optimizer IPOPT -task run_driver 2>&1 | tee logOpt.txt
```

`preProcessing.sh` runs the pyHyp mesh generation and OpenFOAM conversion/patching steps. It requires `plot3dToFoam`, `autoPatch`, `createPatch` and `renumberMesh`. The expected original mesh count is 26,522 cells; inspect mesh quality before accepting a newly generated mesh. The objective is physical CD with scale 1; target lift is enforced as an equality.

The legacy `plot_results.py` is retained as part of the original work. It selects the first plausible coefficient from a raw log, which can precede lift trimming. Use the root-level audit to reconstruct the archived reference history and baseline; for a new solver run, inspect its actual trim and iteration-zero state before reporting a percentage.

## Case B: CST optimization

```bash
python tools/stage_case.py case-b-cst
cd runs/case-b-cst
bash step1_prepare_airfoil.sh
bash step2_generate_mesh.sh
bash step3_prepare_case.sh
bash run_opt.sh
```

The prepare step fits the local S809 profile and establishes six upper plus six lower CST coefficients on the OpenVSP geometry carrier. Mesh generation requests 10,000 cells; the recorded generated mesh has 10,270 cells. The final actual cell count matters more than the requested target.

The local `prepare_case_local.py` includes the historical Windows bind-mount metadata workaround and re-stages the pristine external `airfoil_assets` geometry before establishing the CST representation. A saved `airfoil.vsp3` or `airfoil_opt.vsp3` is an artifact, not a substitute for this preparation sequence. The optimization script reads `cst_coeffs.prepare.json` for initial values and uses objective scale 10.

`step5_analyze.sh` and the legacy surface plots need the external analysis modules and newly generated VTK/history outputs. Those large outputs are excluded from the repository. Their original PNG results are retained under `results/figures/`; the lightweight result audit does not regenerate pressure-surface or FFD shape plots from nonexistent volume fields.

## Finer-mesh checks

Choose one case, then run inside its staged directory:

```bash
python tools/stage_case.py mesh-check-20k
cd runs/mesh-check-20k
bash step1_prepare_airfoil.sh
bash step2_generate_mesh.sh
bash step3_prepare_case.sh
bash run_check.sh
```

Repeat independently with `mesh-check-40k` and `mesh-check-80k`. These scripts hold the baseline/optimized CST coefficient sets fixed, trim angle of attack, and evaluate each shape. They do not re-optimize the shape. Several primal solves are used for each trim, so this is not literally just two solver calls. The saved final mesh counts are 20,792, 41,340 and 81,984.

## Fixed-angle sweep

```bash
python tools/stage_case.py aoa-sweep
cd runs/aoa-sweep
bash step1_prepare_airfoil.sh
bash step2_generate_mesh.sh
bash step3_prepare_case.sh
bash run_sweep.sh
```

This evaluates two fixed shapes at nine angles each, without CL trim. The baseline/optimized CST values are embedded in the supplied evaluation scripts. The historical JSON and its log are included separately under `data/` and `evidence/` for auditing. A fresh run produces new outputs under `runs/` and does not replace the archived evidence.

## Working-copy rules

Case cleanup and destructive Python initialization require the `.s809-run-dir` marker created by the staging tool. Run from the staged directory. The marker guards prevent launching cleanup from an input template or the repository root. Existing run directories are not overwritten; use `--name` with a new name for another run. The shell wrappers now propagate pipeline failures with `pipefail` and accept an installation-specific initialization path. Numerical solver settings, objectives and design-variable definitions were not altered for packaging.

Saved pressure-overlay scripts retain their sibling-case layout assumptions. To rerun cross-case overlays, stage the needed cases under their default names, regenerate and export the relevant surface files, and account for the missing/overwritten original VTK paths described in the audit. Do not treat the supplied plotting scripts as proof that all historical source VTK files still exist.

#!/usr/bin/env python
"""
=============================================================================
Single baseline-shape evaluation for shape/Cp overlay plotting
=============================================================================
Runs ONLY the baseline S809 CST shape, trimmed to CL=0.4 (matching the
convention used throughout this project's reported baseline numbers), on the
same 10k-cell mesh as the original optimization case
(case-b-cst). Reuses this folder's already-generated
mesh -- no new mesh generation.

The original optimization run never preserved a baseline flow-field snapshot
(each primal solve overwrote the same time directory), so this is a
dedicated re-solve purely to get baseline surface Cp + geometry for the
baseline-vs-optimized overlay plot. Single primal solve, no adjoint, no
optimizer.

Run (inside the container, from this case directory):
    mpirun -np 4 python baseline_cp_eval.py 2>&1 | tee log_baseline_eval.txt
=============================================================================
"""


# Packaging guard; numerical inputs below are unchanged.
from pathlib import Path as _PackagingPath
if (_PackagingPath.cwd().resolve() != _PackagingPath(__file__).resolve().parent
        or not _PackagingPath(".s809-run-dir").is_file()):
    raise SystemExit("Stage a fresh run with tools/stage_case.py and run from that directory.")

import os
import json
import numpy as np
from mpi4py import MPI
import openmdao.api as om
from mphys.multipoint import Multipoint
from dafoam.mphys import DAFoamBuilder, OptFuncs, DAFoamLinearConstraint, DAFoamVSPVolume
from mphys.scenario_aerodynamic import ScenarioAerodynamic
from pygeo.mphys import OM_DVGEOCOMP

# =============================================================================
# Same physics as the original S809 Re=2e6 case (runScript.py)
# =============================================================================
U0 = 30.0
Re = 2000000.0
L0 = 1.0
A0 = 0.01
aoa0 = 3.0
CL_target = 0.4
solverName = "DASimpleFoam"
turbulenceModel = "SpalartAllmaras"
useWallFunction = True
max_flow_iters = 5000
primal_std_tol = 1e-6
primal_slope_tol = 1e-5

with open("cst_coeffs.prepare.json", "r", encoding="utf-8") as fh:
    baseline_coeffs = json.load(fh)["cst_coeffs"]
n_cst_coeffs = len(baseline_coeffs) // 2

if MPI.COMM_WORLD.rank == 0:
    os.system("rm -rf postProcessing processor* 0.00* *.bin *.info *.jpeg *.png reports *.hst [1-9]* VTK_baseline")
    os.system(f"sed -i 's/^endTime.*/endTime         {int(max_flow_iters)};/' system/controlDict")
    os.system(f"sed -i 's/^writeInterval.*/writeInterval   {int(max_flow_iters)};/' system/controlDict")

T0 = 300.0
nu = U0 * L0 / Re
Ux = float(U0 * np.cos(np.radians(aoa0)))
Uz = float(U0 * np.sin(np.radians(aoa0)))
TURBULENCE_INTENSITY = 0.01
EDDY_VISCOSITY_RATIO = 10.0
nuTilda0 = EDDY_VISCOSITY_RATIO * nu
k0 = 1.5 * (U0 * TURBULENCE_INTENSITY) ** 2
omega0 = k0 / (EDDY_VISCOSITY_RATIO * nu)
p0 = 0.0
rho0 = 1.0
p_norm = U0 * U0 / 2.0
mu = nu * rho0

IC = {"U": [Ux, 0.0, Uz], "p": p0, "T": T0, "nuTilda": nuTilda0, "k": k0, "omega": omega0}
BC = {
    "U0": {"variable": "U", "patches": ["inout"], "value": [Ux, 0.0, Uz]},
    "p0": {"variable": "p", "patches": ["inout"], "value": [p0]},
    "nuTilda0": {"variable": "nuTilda", "patches": ["inout"], "value": [nuTilda0]},
    "k0": {"variable": "k", "patches": ["inout"], "value": [k0]},
    "omega0": {"variable": "omega", "patches": ["inout"], "value": [omega0]},
    "transport:nu": nu,
    "useWallFunction": useWallFunction,
}

daOptions = {
    "designSurfaces": ["wing"],
    "solverName": solverName,
    "transonicPCOption": 0,
    "primalMinResTol": 1.0e-7,
    "primalMinResTolDiff": 1e3,
    "primalFuncStdTol": {"stdTol": primal_std_tol, "slopeTol": primal_slope_tol,
                          "funcNames": ["CD", "CL"], "nStepsFrac": 0.2},
    "primalMinIters": 50,
    "printInterval": 10,
    "primalInitCondition": IC,
    "primalBC": BC,
    "function": {
        "CD": {"type": "force", "source": "patchToFace", "patches": ["wing"],
               "directionMode": "parallelToFlow", "patchVelocityInputName": "patchV",
               "scale": 1.0 / (0.5 * U0 * U0 * A0 * rho0), "timeOp": "final", "nStepsFrac": 0.2},
        "CL": {"type": "force", "source": "patchToFace", "patches": ["wing"],
               "directionMode": "normalToFlow", "patchVelocityInputName": "patchV",
               "scale": 1.0 / (0.5 * U0 * U0 * A0 * rho0), "timeOp": "final", "nStepsFrac": 0.2},
    },
    "adjStateOrdering": "cell",
    "adjEqnOption": {"gmresRelTol": 1.0e-5, "pcFillLevel": 1, "jacMatReOrdering": "natural",
                      "gmresMaxIters": 1000, "gmresRestart": 1000},
    "normalizeStates": {"U": U0, "p": p_norm, "T": T0, "nuTilda": nuTilda0 * 10.0,
                         "k": k0 * 10.0, "omega": omega0 * 0.1, "phi": 1.0},
    "inputInfo": {
        "aero_vol_coords": {"type": "volCoord", "components": ["solver", "function"]},
        "patchV": {"type": "patchVelocity", "patches": ["inout"], "flowAxis": "x",
                   "normalAxis": "z", "components": ["solver", "function"]},
    },
    "checkMeshThreshold": {"maxNonOrth": 70.0, "maxSkewness": 6.0, "maxAspectRatio": 10000.0},
}
meshOptions = {
    "gridFile": os.getcwd(), "fileType": "OpenFOAM",
    "symmetryPlanes": [[[0.0, 0.0, 0.0], [0.0, 1.0, 0.0]], [[0.0, 0.01, 0.0], [0.0, 1.0, 0.0]]],
}


class Top(Multipoint):
    def setup(self):
        dafoam_builder = DAFoamBuilder(daOptions, meshOptions, scenario="aerodynamic")
        dafoam_builder.initialize(self.comm)
        self.add_subsystem("dvs", om.IndepVarComp(), promotes=["*"])
        self.add_subsystem("mesh", dafoam_builder.get_mesh_coordinate_subsystem())
        self.add_subsystem("geometry", OM_DVGEOCOMP(file="airfoil.vsp3", type="vsp"))
        self.mphys_add_scenario("scenario1", ScenarioAerodynamic(aero_builder=dafoam_builder))
        self.connect("mesh.x_aero0", "geometry.x_aero_in")
        self.connect("geometry.x_aero0", "scenario1.x_aero")

    def configure(self):
        points = self.mesh.mphys_get_surface_mesh()
        self.geometry.nom_add_discipline_coords("aero", points)
        for i in range(2):
            for j in range(n_cst_coeffs):
                self.geometry.nom_addVSPVariable("Airfoil", f"UpperCoeff_{i}", f"Au_{j}", scaledStep=False, dh=1e-6)
                self.geometry.nom_addVSPVariable("Airfoil", f"LowerCoeff_{i}", f"Al_{j}", scaledStep=False, dh=1e-6)
        for j in range(n_cst_coeffs):
            self.dvs.add_output(f"UpperCoeff_{j}", val=baseline_coeffs[j])
            self.connect(f"UpperCoeff_{j}", f"geometry.Airfoil:UpperCoeff_0:Au_{j}")
            self.connect(f"UpperCoeff_{j}", f"geometry.Airfoil:UpperCoeff_1:Au_{j}")
            self.dvs.add_output(f"LowerCoeff_{j}", val=baseline_coeffs[j + n_cst_coeffs])
            self.connect(f"LowerCoeff_{j}", f"geometry.Airfoil:LowerCoeff_0:Al_{j}")
            self.connect(f"LowerCoeff_{j}", f"geometry.Airfoil:LowerCoeff_1:Al_{j}")
        self.dvs.add_output("patchV", val=np.array([U0, aoa0]))
        self.connect("patchV", "scenario1.patchV")
        self.add_design_var("patchV", lower=[U0, -10.0], upper=[U0, 10.0], scaler=0.1)


prob = om.Problem()
prob.model = Top()
prob.setup(mode="rev")
optFuncs = OptFuncs(daOptions, prob)

if MPI.COMM_WORLD.rank == 0:
    print("\n=========== BASELINE (10k mesh, CL=0.4 trim) ===========", flush=True)

optFuncs.findFeasibleDesign(
    ["scenario1.aero_post.CL"], ["patchV"], targets=[CL_target],
    designVarsComp=[1], epsFD=[1e-2], tol=1e-3,
)
prob.run_model()
cd = float(prob.get_val("scenario1.aero_post.CD"))
cl = float(prob.get_val("scenario1.aero_post.CL"))
aoa = float(prob.get_val("patchV")[1])

if MPI.COMM_WORLD.rank == 0:
    print(f"RESULT BASELINE: CD={cd:.6f}  CL={cl:.6f}  AoA={aoa:.4f} deg", flush=True)
    # Same recipe as step5_analyze.sh's VTK export, just renamed afterward so it
    # doesn't collide with a later VTK/ export of anything else in this folder.
    os.system("reconstructPar -latestTime >> log_baseline_eval.txt 2>&1")
    os.system("rm -rf VTK")
    os.system(
        "foamToVTK -latestTime -patches '(wing symmetry1 symmetry2)' -fields '(p U)' "
        "-one-boundary >> log_baseline_eval.txt 2>&1"
    )
    os.system("mv VTK/*/boundary.vtp VTK/ 2>/dev/null")
    os.system("rm -rf VTK_baseline && mv VTK VTK_baseline")
    print("VTK export done -> VTK_baseline/boundary.vtp")

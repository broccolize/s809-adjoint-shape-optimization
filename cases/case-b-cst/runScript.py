#!/usr/bin/env python
"""
=============================================================================
DAFoam run script  --  NREL S809 airfoil aero-shape optimization
=============================================================================
Minimize Cd at a target lift, incompressible RANS, at the S809 design
Reynolds number Re = 2e6.  Converted from the FFD-based gcc tutorial case to
this project's docker (VSP/CST) pipeline.

Style follows the standard DAFoam airfoil tutorials: all case-specific
physics lives in the INPUT PARAMETERS block below; the daOptions dict and
the OpenMDAO/mphys `Top` group are the usual tutorial machinery.  Geometry
is driven by the case-local OpenVSP/CST parametrisation (airfoil.vsp3), the
same path used for the NACA 64(4)-221 case in this project.

Tasks (choose with -task):
    run_driver    run the full gradient-based optimization  (default)
    run_model     single primal (flow) solve at the current shape
    check_totals  verify adjoint gradients against finite difference

Run (inside the container, from this case directory):
    mpirun -np 4 python runScript.py -task run_driver 2>&1 | tee log_opt.txt
=============================================================================
"""


# Packaging guard; numerical inputs below are unchanged.
from pathlib import Path as _PackagingPath
if (_PackagingPath.cwd().resolve() != _PackagingPath(__file__).resolve().parent
        or not _PackagingPath(".s809-run-dir").is_file()):
    raise SystemExit("Stage a fresh run with tools/stage_case.py and run from that directory.")

import os
import json
import argparse
import numpy as np
from mpi4py import MPI
import openmdao.api as om
from mphys.multipoint import Multipoint
from dafoam.mphys import DAFoamBuilder, OptFuncs, DAFoamLinearConstraint, DAFoamVSPVolume
from mphys.scenario_aerodynamic import ScenarioAerodynamic
from pygeo.mphys import OM_DVGEOCOMP

# -----------------------------------------------------------------------------
# Command-line switches (only task / optimizer, like the DAFoam tutorials).
# All physics parameters are fixed in the INPUT PARAMETERS block below.
# -----------------------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("-task", type=str, default="run_driver",
                    help="run_driver | run_model | check_totals")
parser.add_argument("-optimizer", type=str, default="SLSQP",
                    help="SLSQP | IPOPT | SNOPT")
args = parser.parse_args()

# =============================================================================
# INPUT PARAMETERS  --  NREL S809  (Re = 2e6 design condition)
# =============================================================================
# ---- Flow condition -----------------------------------------------------
U0 = 30.0            # freestream velocity [m/s]  -> Re = U*L/nu = 30/1.5e-5 = 2e6
Re = 2000000.0       # S809 design Reynolds number
L0 = 1.0             # reference chord [m]  (normalized airfoil)
A0 = 0.01            # reference area = chord * (2D span 0.01) [m^2]
aoa0 = 3.0           # initial angle of attack [deg] (start for CL search)

# ---- Design target / constraints ---------------------------------------
CL_target = 0.4      # lift constraint (matches the gcc S809 case)
thickness_constraint = 0.5   # normalized lower bound
le_radius_constraint = 0.8   # normalized lower bound (matches gcc rcon >= 0.8)
volume_constraint    = 1.0   # normalized lower bound

# ---- Solver / turbulence -----------------------------------------------
# 30 m/s -> Ma ~ 0.09 -> incompressible: use DASimpleFoam.
# SA uses the Spalding continuous wall function (valid down to y+~1), so with the
# y+~1 mesh from step 2 this is effectively wall-resolved-equivalent to the gcc
# case's low-Re BC, but more robust in this pipeline.
solverName      = "DASimpleFoam"
turbulenceModel = "SpalartAllmaras"
useWallFunction = True

# ---- Numerics -----------------------------------------------------------
max_opt_iters  = 50       # optimizer major iterations (gcc S809 converged in ~24, so 50 is ample headroom)
max_flow_iters = 5000     # primal (flow) iterations cap (higher for y+~1 mesh)
max_adj_iters  = 1000     # GMRES iterations for the adjoint solve
pc_fill_level  = 1
primal_std_tol   = 1e-6
primal_slope_tol = 1e-5

# ---- Initial geometry (CST coefficients) -------------------------------
# Produced by the prepare step:
#   python script_workflow_helpers.py prepare-airfoil-case \
#       --airfoil-profile s809 --n-cst-coeffs 6 \
#       --solver-name DASimpleFoam --turbulence-model SpalartAllmaras --case-dir .
# It writes cst_coeffs.prepare.json (6 upper + 6 lower). Read them here so
# the initial shape is the fitted S809, not a hardcoded guess.
with open("cst_coeffs.prepare.json", "r", encoding="utf-8") as fh:
    cst_coeffs = json.load(fh)["cst_coeffs"]
if len(cst_coeffs) < 2 or len(cst_coeffs) % 2 != 0:
    raise ValueError(f"cst_coeffs must be an even count (upper+lower); got {len(cst_coeffs)}")
n_cst_coeffs = len(cst_coeffs) // 2

# =============================================================================
# Derived quantities  (do not edit)
# =============================================================================
if MPI.COMM_WORLD.rank == 0:
    os.system("rm -rf postProcessing processor* 0.00* *.bin *.info *.jpeg *.png reports *.hst [1-9]*")
    os.system(f"sed -i 's/^endTime.*/endTime         {int(max_flow_iters)};/' system/controlDict")
    os.system(f"sed -i 's/^writeInterval.*/writeInterval   {int(max_flow_iters)};/' system/controlDict")

T0 = 300.0
nu = U0 * L0 / Re                       # kinematic viscosity from Re
Ux = float(U0 * np.cos(np.radians(aoa0)))
Uz = float(U0 * np.sin(np.radians(aoa0)))

TURBULENCE_INTENSITY = 0.01
EDDY_VISCOSITY_RATIO = 10.0
nuTilda0 = EDDY_VISCOSITY_RATIO * nu
k0 = 1.5 * (U0 * TURBULENCE_INTENSITY) ** 2
omega0 = k0 / (EDDY_VISCOSITY_RATIO * nu)

# Incompressible (DASimpleFoam) reference state
p0 = 0.0
rho0 = 1.0
p_norm = U0 * U0 / 2.0
mu = nu * rho0
transonicPC = 0

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

# =============================================================================
# DAFoam options
# =============================================================================
daOptions = {
    "designSurfaces": ["wing"],
    "solverName": solverName,
    "transonicPCOption": transonicPC,
    "primalMinResTol": 1.0e-7,
    "primalMinResTolDiff": 1e3,
    "primalFuncStdTol": {
        "stdTol": primal_std_tol,
        "slopeTol": primal_slope_tol,
        "funcNames": ["CD", "CL"],
        "nStepsFrac": 0.2,
    },
    "primalMinIters": 50,
    "printInterval": 10,
    "primalInitCondition": IC,
    "primalBC": BC,
    "function": {
        "CD": {
            "type": "force",
            "source": "patchToFace",
            "patches": ["wing"],
            "directionMode": "parallelToFlow",
            "patchVelocityInputName": "patchV",
            "scale": 1.0 / (0.5 * U0 * U0 * A0 * rho0),
            "timeOp": "final",
            "nStepsFrac": 0.2,
        },
        "CL": {
            "type": "force",
            "source": "patchToFace",
            "patches": ["wing"],
            "directionMode": "normalToFlow",
            "patchVelocityInputName": "patchV",
            "scale": 1.0 / (0.5 * U0 * U0 * A0 * rho0),
            "timeOp": "final",
            "nStepsFrac": 0.2,
        },
        "CM": {
            "type": "moment",
            "source": "patchToFace",
            "patches": ["wing"],
            "axis": [0.0, 1.0, 0.0],
            "center": [0.25, 0.0, 0.0],
            "scale": 1.0 / (0.5 * U0 * U0 * A0 * rho0 * L0),
            "timeOp": "final",
            "nStepsFrac": 0.2,
        },
    },
    "adjStateOrdering": "cell",
    "adjEqnOption": {
        "gmresRelTol": 1.0e-5,
        "pcFillLevel": pc_fill_level,
        "jacMatReOrdering": "natural",
        "gmresMaxIters": max_adj_iters,
        "gmresRestart": max_adj_iters,
    },
    "normalizeStates": {
        "U": U0,
        "p": p_norm,
        "T": T0,
        "nuTilda": nuTilda0 * 10.0,
        "k": k0 * 10.0,
        "omega": omega0 * 0.1,
        "phi": 1.0,
    },
    "inputInfo": {
        "aero_vol_coords": {"type": "volCoord", "components": ["solver", "function"]},
        "patchV": {
            "type": "patchVelocity",
            "patches": ["inout"],
            "flowAxis": "x",
            "normalAxis": "z",
            "components": ["solver", "function"],
        },
    },
    "checkMeshThreshold": {
        "maxNonOrth": 70.0,
        "maxSkewness": 6.0,
        "maxAspectRatio": 10000.0,
    },
}

meshOptions = {
    "gridFile": os.getcwd(),
    "fileType": "OpenFOAM",
    "symmetryPlanes": [
        [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        [[0.0, 0.01, 0.0], [0.0, 1.0, 0.0]],
    ],
}


# =============================================================================
# OpenMDAO / mphys optimization group
# =============================================================================
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

        # thickness (upper - lower CST) and LE-continuity linear constraints
        varA, varB = [], []
        for j in range(n_cst_coeffs):
            varA.append(f"UpperCoeff_{j}")
            varB.append(f"LowerCoeff_{j}")
        self.add_subsystem(
            "thickness",
            DAFoamLinearConstraint(varA=varA, coeffA=1.0, varB=varB, coeffB=-1.0, size=1, output_name="thickness_val"),
            promotes=["*"],
        )
        self.add_subsystem(
            "le_c1",
            DAFoamLinearConstraint(varA=["UpperCoeff_0"], coeffA=1.0, varB=["LowerCoeff_0"], coeffB=1.0,
                                   size=1, output_name="le_c1_val"),
            promotes=["*"],
        )

        vsp_vars = []
        for i in range(2):
            for j in range(n_cst_coeffs):
                vsp_vars.append(f"Airfoil:UpperCoeff_{i}:Au_{j}")
                vsp_vars.append(f"Airfoil:LowerCoeff_{i}:Al_{j}")
        self.add_subsystem(
            "volume",
            DAFoamVSPVolume(vsp_file="airfoil.vsp3", vsp_vars=vsp_vars, slice_dir="x", n_slices=10,
                            output_name="volume_val", step=1e-6, relativeStep=False),
        )

    def configure(self):
        points = self.mesh.mphys_get_surface_mesh()
        self.geometry.nom_add_discipline_coords("aero", points)
        tri_points = self.mesh.mphys_get_triangulated_surface()
        self.geometry.nom_setConstraintSurface(tri_points)

        # register CST coefficients on both 2D sections so one DV moves the whole extrusion
        for i in range(2):
            for j in range(n_cst_coeffs):
                self.geometry.nom_addVSPVariable("Airfoil", f"UpperCoeff_{i}", f"Au_{j}", scaledStep=False, dh=1e-6)
                self.geometry.nom_addVSPVariable("Airfoil", f"LowerCoeff_{i}", f"Al_{j}", scaledStep=False, dh=1e-6)

        for j in range(n_cst_coeffs):
            self.dvs.add_output(f"UpperCoeff_{j}", val=cst_coeffs[j])
            self.connect(f"UpperCoeff_{j}", f"geometry.Airfoil:UpperCoeff_0:Au_{j}")
            self.connect(f"UpperCoeff_{j}", f"geometry.Airfoil:UpperCoeff_1:Au_{j}")
            self.connect(f"UpperCoeff_{j}", f"volume.Airfoil:UpperCoeff_0:Au_{j}")
            self.connect(f"UpperCoeff_{j}", f"volume.Airfoil:UpperCoeff_1:Au_{j}")

            self.dvs.add_output(f"LowerCoeff_{j}", val=cst_coeffs[j + n_cst_coeffs])
            self.connect(f"LowerCoeff_{j}", f"geometry.Airfoil:LowerCoeff_0:Al_{j}")
            self.connect(f"LowerCoeff_{j}", f"geometry.Airfoil:LowerCoeff_1:Al_{j}")
            self.connect(f"LowerCoeff_{j}", f"volume.Airfoil:LowerCoeff_0:Al_{j}")
            self.connect(f"LowerCoeff_{j}", f"volume.Airfoil:LowerCoeff_1:Al_{j}")

        for j in range(n_cst_coeffs):
            self.add_design_var(f"UpperCoeff_{j}", lower=-1.0, upper=1.0, scaler=10.0)
            self.add_design_var(f"LowerCoeff_{j}", lower=-1.0, upper=1.0, scaler=10.0)

        # angle of attack is a design variable (velocity magnitude fixed at U0)
        self.dvs.add_output("patchV", val=np.array([U0, aoa0]))
        self.connect("patchV", "scenario1.patchV")
        self.add_design_var("patchV", lower=[U0, -10.0], upper=[U0, 10.0], scaler=0.1)

        # objective + constraints
        self.add_objective("scenario1.aero_post.CD", scaler=10.0)
        self.add_constraint("scenario1.aero_post.CL", lower=CL_target, scaler=1.0)
        if volume_constraint > 0:
            self.add_constraint("volume.volume_val", lower=volume_constraint, scaler=1.0)
        if thickness_constraint >= 0:
            for j in range(1, n_cst_coeffs):
                lb = thickness_constraint * (cst_coeffs[j] - cst_coeffs[n_cst_coeffs + j])
                self.add_constraint(f"thickness_val_{j}", lower=lb, scaler=1.0, linear=True)
        if le_radius_constraint >= 0:
            lb = le_radius_constraint * (cst_coeffs[0] - cst_coeffs[n_cst_coeffs])
            self.add_constraint("thickness_val_0", lower=lb, scaler=1.0, linear=True)
        self.add_constraint("le_c1_val_0", equals=0.0, scaler=1.0, linear=True)


# =============================================================================
# OpenMDAO problem + optimizer
# =============================================================================
prob = om.Problem()
prob.model = Top()
prob.setup(mode="rev")

optFuncs = OptFuncs(daOptions, prob)

prob.driver = om.pyOptSparseDriver()
prob.driver.options["optimizer"] = args.optimizer
if args.optimizer == "SLSQP":
    prob.driver.opt_settings = {"ACC": 1.0e-6, "MAXIT": max_opt_iters, "IFILE": "opt_SLSQP.txt"}
elif args.optimizer == "IPOPT":
    prob.driver.opt_settings = {
        "tol": 1.0e-4, "constr_viol_tol": 1.0e-4, "max_iter": max_opt_iters,
        "print_level": 5, "output_file": "opt_IPOPT.txt", "mu_strategy": "adaptive",
        "limited_memory_max_history": 10, "nlp_scaling_method": "none",
        "alpha_for_y": "full", "recalc_y": "yes", "bound_frac": 1e-3,
    }
elif args.optimizer == "SNOPT":
    prob.driver.opt_settings = {
        "Major feasibility tolerance": 1.0e-4, "Major optimality tolerance": 1.0e-4,
        "Minor feasibility tolerance": 1.0e-4, "Verify level": -1, "Function precision": 1.0e-5,
        "Major iterations limit": max_opt_iters, "Nonderivative linesearch": None,
        "Print file": "opt_SNOPT_print.txt", "Summary file": "opt_SNOPT_summary.txt",
    }
else:
    print("optimizer arg not valid!")
    exit(1)

prob.driver.options["debug_print"] = ["nl_cons", "objs", "desvars"]
prob.driver.options["print_opt_prob"] = True
prob.driver.hist_file = "OptView.hst"

# =============================================================================
# Run
# =============================================================================
if args.task == "run_driver":
    # first drive AoA so the initial CL meets the target, then optimize
    optFuncs.findFeasibleDesign(
        ["scenario1.aero_post.CL"], ["patchV"], targets=[CL_target * 1.001],
        designVarsComp=[1], epsFD=[1e-2], tol=1e-3,
    )
    prob.run_driver()
    if MPI.COMM_WORLD.rank == 0:
        prob.model.geometry.DVGeo.writeVSPFile("airfoil_opt.vsp3")
elif args.task == "run_model":
    prob.run_model()
elif args.task == "check_totals":
    prob.run_model()
    prob.check_totals(compact_print=False, step=1e-3, form="central", step_calc="abs")
else:
    print("task arg not found!")
    exit(1)

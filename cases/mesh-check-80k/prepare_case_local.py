#!/usr/bin/env python
"""
Local prepare-airfoil-case wrapper for the S809 case.

Two environment/workflow fixes vs. calling script_workflow_helpers.py directly:

1. Docker Desktop's Windows bind mount rejects utime()/copystat() with
   "Operation not permitted", so shutil.copy2 (used by copy_solver_files)
   fails. We make copystat a no-op — file *content* still copies; only the
   timestamp-preservation step is skipped, which is harmless for solver files.

2. The mesh step (script_generate_mesh.py) rewrites airfoil.vsp3 into an xsec
   type that convert_vsp3_to_cst cannot fit ("Not Fittable Airfoil Type").
   We re-stage the pristine airfoil_assets template first; convert_vsp3_to_cst
   then establishes the 6+6 CST parametrization on it. runScript.py sets the
   actual S809 coefficient *values* (from cst_coeffs.prepare.json) at startup,
   so the generic template geometry is only a carrier for the CST structure.
"""
import os
import json
import shutil

# (1) Windows bind mount can't set file times; skip metadata preservation.
shutil.copystat = lambda *args, **kwargs: None

import airfoil_assets
from mdo_agent_base import (
    copy_solver_files,
    convert_vsp3_to_cst,
    fit_airfoil_cst,
    write_turbulence_model,
)

PROFILE = "s809"
N_CST = 6
SOLVER = "DASimpleFoam"
TURBULENCE = "SpalartAllmaras"

# (2) Re-stage the pristine template (mesh step leaves a non-fittable xsec).
# airfoil_assets is a namespace package (__file__ is None), so use __path__.
assets_dir = list(airfoil_assets.__path__)[0]
template = os.path.join(assets_dir, "airfoil.vsp3")
shutil.copyfile(template, "airfoil.vsp3")
print(f"Staged pristine template from {template}")

# Fit S809 -> 6+6 CST coefficients (from profiles/s809.dat).
coeffs = fit_airfoil_cst(PROFILE, N_CST, profiles_dir="profiles")
cst_coeffs = list(coeffs["upper"]) + list(coeffs["lower"])

# Establish CST parametrization on the vsp3, stage solver files + 0/ fields.
convert_vsp3_to_cst(".", N_CST, "airfoil.vsp3", "Airfoil", xsec_indices=(0, 1))
os.makedirs("0", exist_ok=True)
copy_solver_files(".", SOLVER)
write_turbulence_model(".", TURBULENCE)

with open("cst_coeffs.prepare.json", "w", encoding="utf-8") as handle:
    json.dump({"cst_coeffs": [float(v) for v in cst_coeffs]}, handle, indent=2, sort_keys=True)

print("Prepare complete:")
print("  cst_coeffs.prepare.json written")
print(f"  0/ fields: {sorted(os.listdir('0'))}")

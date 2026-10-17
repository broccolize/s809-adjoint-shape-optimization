#!/bin/bash
set -eo pipefail
# Step 3 — fit S809 to 6+6 CST coeffs and write incompressible (DASimpleFoam)
# solver templates + 0/ fields. Produces cst_coeffs.prepare.json that
# runScript.py reads for the initial shape.
#
# Uses the local wrapper prepare_case_local.py instead of calling
# script_workflow_helpers.py directly, for two reasons (see that file):
#   1. neutralizes shutil.copystat (Docker Desktop Windows mount rejects utime)
#   2. re-stages the pristine airfoil.vsp3 template (the mesh step leaves an
#      xsec type that convert_vsp3_to_cst cannot fit)
# Run this AFTER step 2 (mesh); it does not touch constant/polyMesh.
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/dafoam_env.sh"
python prepare_case_local.py

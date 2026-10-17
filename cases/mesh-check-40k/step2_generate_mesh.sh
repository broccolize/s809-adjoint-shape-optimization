#!/bin/bash
set -eo pipefail
# Step 2 — generate the CFD mesh for S809 at Re=2e6, y+~1 (wall-resolved).
# Ma/Re size the first boundary-layer cell; U0=30 m/s -> Ma~0.0864, Re=2e6.
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/dafoam_env.sh"

# The mesh generator UPDATES an existing base airfoil.vsp3 (it does not create
# one). Stage the package's pristine template if it is missing.
# NOTE: airfoil_assets is a namespace package (__file__ is None) -> use __path__.
if [ ! -f airfoil.vsp3 ]; then
    TPL=$(python -c "import os, airfoil_assets; print(os.path.join(list(airfoil_assets.__path__)[0], 'airfoil.vsp3'))" 2>/dev/null)
    if [ -n "$TPL" ] && [ -f "$TPL" ]; then
        cp "$TPL" airfoil.vsp3
        echo "Staged base airfoil.vsp3 template."
    else
        echo "ERROR: base airfoil.vsp3 template not found in airfoil_assets package."; exit 1
    fi
fi

bash Allclean.sh > log_mesh.txt 2>&1
python script_generate_mesh.py -airfoil_profile=s809 -mesh_cells=40000 -blunt_te=0.01 -y_plus=1.0 -mach_number=0.0864 -reynolds_number=2000000.0 -d0=-1.0 >> log_mesh.txt 2>&1
createPatch -overwrite >> log_mesh.txt 2>&1
renumberMesh -overwrite >> log_mesh.txt 2>&1
checkMesh >> log_mesh.txt 2>&1 || true
echo "Mesh done. Quality summary:"
grep -E "cells:|Max (non-ortho|skewness|aspect)" log_mesh.txt | tail -5

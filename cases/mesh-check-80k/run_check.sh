#!/bin/bash
set -eo pipefail
# Runs the two-point mesh-sensitivity check (baseline + optimized CD/CL on
# the 80k-cell mesh). Much shorter than a full re-optimization: two primal
# trims + solves, not ~13 optimizer iterations.
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/dafoam_env.sh"
mpirun -np 4 python mesh_sensitivity_check.py 2>&1 | tee log_meshcheck.txt

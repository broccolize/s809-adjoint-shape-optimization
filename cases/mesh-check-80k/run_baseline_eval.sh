#!/bin/bash
set -eo pipefail
# Single baseline-shape solve (CL=0.4 trim) on the existing 80k-cell mesh,
# purely to recover baseline VTK/Cp data (overwritten by mesh_sensitivity_check.py's
# later optimized-shape solve). One point, no adjoint, no optimizer.
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/dafoam_env.sh"
mpirun -np 4 python baseline_cp_eval.py 2>&1 | tee log_baseline_eval.txt

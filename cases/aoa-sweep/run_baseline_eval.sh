#!/bin/bash
set -eo pipefail
# Single baseline-shape solve (CL=0.4 trim) on the existing 10k-cell mesh,
# purely to export VTK/Cp data for the baseline-vs-optimized overlay plot.
# One point, no adjoint, no optimizer -- much shorter than the AoA sweep.
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/dafoam_env.sh"
mpirun -np 4 python baseline_cp_eval.py 2>&1 | tee log_baseline_eval.txt

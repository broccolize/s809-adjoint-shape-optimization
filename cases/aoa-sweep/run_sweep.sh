#!/bin/bash
set -eo pipefail
# Runs the CD/CL vs AoA sweep (baseline + optimized shapes, 9 AoA points
# each, no CL trim) on the 10k-cell mesh. 18 primal solves total.
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/dafoam_env.sh"
mpirun -np 4 python aoa_sweep.py 2>&1 | tee log_sweep.txt

#!/bin/bash
set -eo pipefail
# Step 4 — run the optimization (this is the long one).
# IPOPT to match the original gcc S809 case.
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/dafoam_env.sh"
mpirun -np 4 python runScript.py -task run_driver -optimizer IPOPT 2>&1 | tee log_opt.txt

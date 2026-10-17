#!/bin/bash
set -eo pipefail
# Step 3 — fit S809 to 6+6 CST coeffs and write incompressible (DASimpleFoam)
# solver templates + 0/ fields, on the 20k-cell mesh. Run AFTER step 2.
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/dafoam_env.sh"
python prepare_case_local.py

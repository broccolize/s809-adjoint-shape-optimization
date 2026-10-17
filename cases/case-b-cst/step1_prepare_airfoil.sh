#!/bin/bash
set -eo pipefail
# Step 1 — normalize the local NREL S809 profile (profiles/s809.dat).
# S809 is NOT in the UIUC database (download 404s), so we normalize the
# coordinate file already staged in profiles/ instead of downloading.
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/dafoam_env.sh"
python script_prepare_airfoil.py --mode normalize --profile-file profiles/s809.dat --target-points 200

#!/usr/bin/env bash
# Source the caller's environment, or the historical container installation.
if [[ -n "${DAFOAM_ENV:-}" ]]; then
    if [[ ! -f "$DAFOAM_ENV" ]]; then
        echo "DAFOAM_ENV does not point to a readable initialization script." >&2
        return 1
    fi
    source "$DAFOAM_ENV"
elif [[ -f /home/dafoamuser/dafoam/loadDAFoam.sh ]]; then
    source /home/dafoamuser/dafoam/loadDAFoam.sh
elif [[ -z "${WM_PROJECT:-}" ]]; then
    echo "Activate a compatible DAFoam/OpenFOAM environment, or set DAFOAM_ENV." >&2
    return 1
fi

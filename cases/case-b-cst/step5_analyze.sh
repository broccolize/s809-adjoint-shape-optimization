#!/bin/bash
set -eo pipefail
# Step 5 — post-process + analyze the optimization result.
# All outputs land in this case's plots/ folder (nothing goes to the results root).
source "$(dirname "${BASH_SOURCE[0]}")/../../tools/dafoam_env.sh"

# Reconstruct the parallel case and export VTK for the optimized shape
reconstructPar -latestTime >> log_opt.txt 2>&1 || true
rm -rf VTK
foamToVTK -latestTime -patches '(wing symmetry1 symmetry2)' -fields '(p U)' -one-boundary >> log_opt.txt 2>&1 || true
mv VTK/*/boundary.vtp VTK/ 2>/dev/null || true

# The optimization-history reader expects the OpenMDAO scaling report under the
# framework's conventional reports/script_run_dafoam/ path, but because the
# driver is named runScript.py, OpenMDAO writes it to reports/runScript/.
# Alias it so general_plot_optimization_history can find the scaling report.
if [ -d reports/runScript ]; then
    rm -rf reports/script_run_dafoam
    cp -r reports/runScript reports/script_run_dafoam
fi

# --- Plots (all written into plots/) ---
# 1. Optimization history: Cd, Cl, design variables, constraints vs iteration
python script_plot_results.py -mode general_plot_optimization_history \
    -case_dir . -hist_file OptView.hst -optimizer_log opt_IPOPT.txt >> log_opt.txt 2>&1 || true

# 2. Surface pressure (Cp) profile. Incompressible (DASimpleFoam): p is kinematic,
#    reference_pressure = 0, Cp scale = 0.5*rho*U0^2 = 0.5*1.0*30^2 = 450
python script_plot_results.py -mode airfoil_plot_pressure_profile \
    -case_dir . -mesh_file VTK/boundary.vtp \
    -reference_pressure 0.0 -pressure_coefficient_scale 450.0 \
    -var_lower -6.0 -var_upper 1.5 -time_step -1 >> log_opt.txt 2>&1 || true

# 3. Pressure flow field around the optimized airfoil
python script_plot_results.py -mode airfoil_plot_flow_field \
    -case_dir . -flow_field p -time_step -1 >> log_opt.txt 2>&1 || true

echo "=== IPOPT objective (Cd) history — last iterations + exit status ==="
grep -E "^\s+[0-9]+ |EXIT|Optimal Solution" opt_IPOPT.txt | tail -14
echo ""
echo "Plots written to plots/:"
ls -1 plots/*.png 2>/dev/null | sed 's/^/  /'
echo "Optimized geometry: airfoil_opt.vsp3"

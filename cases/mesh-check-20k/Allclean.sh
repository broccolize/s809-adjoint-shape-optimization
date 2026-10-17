#!/bin/bash
set -eo pipefail

# Packaging guard: cleanup is allowed only in a staged run directory.
if [ ! -f .s809-run-dir ]; then
  echo "Use tools/stage_case.py before running case cleanup." >&2
  exit 1
fi

echo "Cleaning..."
rm -rf postProcessing
rm -rf constant/polyMesh/
rm -rf *.bin *.info *.dat *.xyz *.stl *.jpeg *.png reports *.txt *.hst
rm -rf processor* 0.00*
rm -rf .dafoam_run_finished
rm -rf plots/*
rm -rf {1..9}*

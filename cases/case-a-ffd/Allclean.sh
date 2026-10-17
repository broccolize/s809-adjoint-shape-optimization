#!/bin/bash
set -eo pipefail

# Packaging guard: cleanup is allowed only in a staged run directory.
if [ ! -f .s809-run-dir ]; then
  echo "Use tools/stage_case.py before running case cleanup." >&2
  exit 1
fi

while true 
do
    read -p "Delete everything and resume to the default setup (y/n)?" yn
    case $yn in
        [Yy]* ) 
            # clean everyting
            echo "Cleaning..."
            rm -rf 0
            rm -rf postProcessing
            rm -rf constant/extendedFeatureEdgeMesh
            rm -rf constant/triSurface
            rm -rf constant/polyMesh/
            rm -rf *.bin *.info *.dat *.xyz *.stl
            rm -rf processor* 0.0000*
            rm -rf {1..9}*
            echo "Cleaning Finished" # modification
            exit
            ;;
        [Nn]* ) exit;;
        * ) echo "Please answer yes or no.";;
    esac
done


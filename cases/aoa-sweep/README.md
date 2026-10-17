# CST fixed-angle sweep

This directory contains archived case inputs and scripts, not a new run.

Recorded baseline and optimized shapes at nine fixed angles each, from -4 to 12 degrees; no lift trimming at each angle.

The correspondence of the archived CST baseline surface to the supplied S809 profile remains unresolved. These numbers are recorded workflow outputs, not independent validation of that geometry. See the root geometry diagnostic and audit notes.

From the repository root, stage a fresh working copy:

```bash
python tools/stage_case.py aoa-sweep
```

The main solver/evaluation entry point is `aoa_sweep.py`. Use the commands and compatible environments in [the reproduction guide](../../docs/reproduction.md). Cleanup is restricted to working copies marked by the staging tool. Generated meshes/fields are excluded; rebuild them rather than assuming a solved state is included.

Original solver evidence is stored separately in [evidence/aoa-sweep](../../evidence/aoa-sweep/). Result tables, actual lift values, precision notes and limitations are documented in [the results audit](../../docs/results-audit.md). All results are simulated. No fresh CFD solve was performed for this repository package.

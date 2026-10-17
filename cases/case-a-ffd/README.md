# FFD optimization at Re=500,000

This directory contains archived case inputs and scripts, not a new run.

Recorded optimization: 26,522 cells, 24 IPOPT iterations, approximately 2.79% simulated drag reduction.

From the repository root, stage a fresh working copy:

```bash
python tools/stage_case.py case-a-ffd
```

The main solver/evaluation entry point is `runScript.py`. Use the commands and compatible environments in [the reproduction guide](../../docs/reproduction.md). Cleanup is restricted to working copies marked by the staging tool. Generated meshes/fields are excluded; rebuild them rather than assuming a solved state is included.

Original solver evidence is stored separately in [evidence/case-a-ffd](../../evidence/case-a-ffd/). Result tables, actual lift values, precision notes and limitations are documented in [the results audit](../../docs/results-audit.md). All results are simulated. No fresh CFD solve was performed for this repository package.

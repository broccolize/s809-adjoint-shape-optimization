# Attribution and licensing notes

## Study contribution

Mineth Lohiru Ariyarathna confirms personal responsibility for the case setup, case-script modifications, simulation runs, analysis and original report. These contributions use existing solver and tutorial infrastructure; they do not imply authorship of the underlying frameworks. The repository organization, audit/plotting and run-staging utilities were prepared later with AI assistance.

## Upstream components

| Component | Role | Source / status |
|---|---|---|
| DAFoam | Discrete-adjoint CFD and optimization interfaces | [MDO Lab source](https://github.com/mdolab/dafoam), [GPLv3 notice](https://github.com/mdolab/dafoam/blob/main/LICENSE.md) |
| DAFoam tutorials | Airfoil/OpenMDAO/MPhys case patterns adapted by the study | [Tutorial repository](https://github.com/DAFoam/tutorials); exact historical starting revision not recorded |
| OpenFOAM | Flow-solver infrastructure | [Project website](https://www.openfoam.com/) |
| OpenMDAO / MPhys, pyGeo / pyHyp, pyOptSparse / IPOPT | Coupling, geometry, meshing and optimization | External dependencies; their own notices/licenses apply |
| OpenVSP | CST geometry carrier | External dependency used by Case B |
| MDO Agent Deck | External `mdo_agent_*` APIs and airfoil assets used by CST wrappers | [Documentation](https://dafoam.github.io/ai-agent-overview.html), [publisher's terms](https://pypi.org/project/mdo-agent-deck/) |

DAFoam's GPLv3 notice does not automatically establish a blanket license for every tutorial, report, dataset or external dependency. The tutorial repository's checked tree (17 October 2026, `a5c4528e124140aacfd4133a68fba8d90c6b517e`) did not contain a root license file; that current snapshot does not establish the exact origin or redistribution terms of every older local file. Preserve individual file notices and confirm any applicable tutorial/template terms before selecting a repository-wide open-source license.

MDO Agent Deck is distributed under evaluation terms and is not described by its publisher as open source. No compiled framework modules, wheels, container image or copied framework implementation are bundled here. Case-local input files, wrappers and recorded outputs are supplied as study artifacts. Installing or using the external package remains subject to its publisher's terms; this repository does not grant rights to it or claim that all external/template redistribution questions have been resolved.

**No new blanket MIT or other repository-wide open-source license has been assigned.** This notice records attribution and known provenance, not a substitute license or a claim of legal clearance. The original report retains its own authorship and references. The coordinate sources available in the local folders are preserved; an exact download URL/revision was not established, so no provenance beyond the S809 profile labels and the report is invented.

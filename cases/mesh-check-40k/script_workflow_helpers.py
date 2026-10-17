#!/usr/bin/env python

import argparse
import json
import os

from mdo_agent_airfoil import AirfoilGenerateCFDMesh
from mdo_agent_airfoil import AirfoilRunAeroOptimization
from mdo_agent_airfoil import AirfoilRunCFDSimulation
from mdo_agent_base import copy_solver_files
from mdo_agent_base import convert_vsp3_to_cst
from mdo_agent_base import export_optimization_boundary_vtks
from mdo_agent_base import extract_opt_hst_data
from mdo_agent_base import fit_airfoil_cst
from mdo_agent_base import read_opt_hst
from mdo_agent_base import stage_warm_start_field
from mdo_agent_base import write_turbulence_model


def main():
    parser = argparse.ArgumentParser(
        description="Workflow helper commands for airfoil skill prepare/analyze phases."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    copy_parser = subparsers.add_parser("copy-solver-files")
    copy_parser.add_argument("--solver-name", required=True)

    prep_parser = subparsers.add_parser("prepare-airfoil-case")
    prep_parser.add_argument("--airfoil-profile", required=True)
    prep_parser.add_argument("--n-cst-coeffs", required=True, type=int)
    prep_parser.add_argument("--solver-name", required=True)
    prep_parser.add_argument("--turbulence-model", default="SpalartAllmaras")
    prep_parser.add_argument("--case-dir", default=".")
    prep_parser.add_argument("--cst-coeffs", nargs="+", type=float, default=None)

    warm_start_parser = subparsers.add_parser("stage-warm-start")
    warm_start_parser.add_argument("--initialize-from", required=True)
    warm_start_parser.add_argument("--case-dir", default=".")

    mesh_parser = subparsers.add_parser("write-mesh-analysis")
    mesh_parser.add_argument("--log-file", required=True)
    mesh_parser.add_argument("--output-file", required=True)

    cfd_parser = subparsers.add_parser("write-cfd-analysis")
    cfd_parser.add_argument("--log-file", required=True)
    cfd_parser.add_argument("--output-file", required=True)

    opt_parser = subparsers.add_parser("write-optimization-analysis")
    opt_parser.add_argument("--log-file", required=True)
    opt_parser.add_argument("--output-file", required=True)
    opt_parser.add_argument("--hist-file", default=None)
    opt_parser.add_argument("--scaling-report-file", default=None)

    export_opt_vtk_parser = subparsers.add_parser("export-optimization-boundary-vtks")
    export_opt_vtk_parser.add_argument("--case-dir", default=".")

    args = parser.parse_args()

    if args.command == "copy-solver-files":
        copy_solver_files(".", args.solver_name)
        return
    if args.command == "prepare-airfoil-case":
        cst_coeffs = args.cst_coeffs
        if cst_coeffs is None:
            coeffs = fit_airfoil_cst(
                str(args.airfoil_profile).strip().lower(),
                int(args.n_cst_coeffs),
                profiles_dir="profiles",
            )
            cst_coeffs = list(coeffs["upper"]) + list(coeffs["lower"])
        convert_vsp3_to_cst(
            args.case_dir,
            int(args.n_cst_coeffs),
            "airfoil.vsp3",
            "Airfoil",
            xsec_indices=(0, 1),
        )
        copy_solver_files(args.case_dir, args.solver_name)
        write_turbulence_model(args.case_dir, args.turbulence_model)
        with open("cst_coeffs.prepare.json", "w", encoding="utf-8") as handle:
            json.dump(
                {"cst_coeffs": [float(value) for value in cst_coeffs]},
                handle,
                indent=2,
                sort_keys=True,
            )
        return
    if args.command == "stage-warm-start":
        # Stage the source field at run time so HPC batches can chain cases sequentially.
        case_dir = os.path.abspath(args.case_dir)
        record = stage_warm_start_field(args.initialize_from, os.path.dirname(case_dir), case_dir)
        with open(os.path.join(case_dir, "warmstart.json"), "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, sort_keys=True)
        return
    if args.command == "export-optimization-boundary-vtks":
        export_optimization_boundary_vtks(
            case_dir=args.case_dir,
            patches="(wing symmetry1 symmetry2)",
            fields="(U p T rho nut)",
        )
        return

    if args.command == "write-mesh-analysis":
        skill = AirfoilGenerateCFDMesh()
        metrics = skill.parse_mesh_log(args.log_file)
    elif args.command == "write-cfd-analysis":
        skill = AirfoilRunCFDSimulation()
        metrics = skill.build_convergence_metrics(skill.parse_simulation_log(args.log_file))
    else:
        skill = AirfoilRunAeroOptimization()
        metrics = skill.parse_optimization_log(args.log_file)
        if args.hist_file and args.scaling_report_file:
            metrics.update(extract_airfoil_opt_hst_designs(args.hist_file, args.scaling_report_file))

    with open(args.output_file, "w", encoding="utf-8", errors="ignore") as handle:
        json.dump(metrics, handle, indent=2, sort_keys=True)


def extract_airfoil_opt_hst_designs(hist_file, scaling_report_file, n_cst_coeffs=6):
    """Extract baseline and optimized physical airfoil designs from optimization history."""
    history = read_opt_hst(hist_file, scaling_report_file)
    if not history:
        return {}

    designs = extract_opt_hst_data(
        history,
        [
            {
                "key": "angle_of_attack",
                "source": "design_variables",
                "name": "dvs.patchV",
                "index": 1,
            },
            {
                "key": "cst_coeffs",
                "source": "design_variables",
                "names": [
                    f"dvs.{surface}Coeff_{index}"
                    for surface in ("Upper", "Lower")
                    for index in range(n_cst_coeffs)
                ],
            },
        ],
        record_indices=[0, -1],
    )
    return {
        "baseline_design_variables": {key: value for key, value in designs[0].items() if key != "iteration"},
        "optimized_design_variables": {key: value for key, value in designs[1].items() if key != "iteration"},
    }


if __name__ == "__main__":
    main()

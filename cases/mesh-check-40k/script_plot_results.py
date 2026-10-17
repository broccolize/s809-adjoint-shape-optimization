#!/usr/bin/env python

import argparse

from mdo_agent_plot import (
    airfoil_plot_flow_field,
    airfoil_plot_mesh,
    airfoil_plot_pressure_profile,
    general_create_image_html,
    general_html_view,
    general_plot_function,
    general_plot_optimization_history,
    general_plot_residual,
    general_trame_view,
)


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def parse_args():
    parser = argparse.ArgumentParser(description="Thin mdo_agent_plot wrapper for case-local plotting.")
    parser.add_argument("-mode", type=str, required=True)
    parser.add_argument("-input_files", type=str, nargs="+", default=None)
    parser.add_argument("-image_files", type=str, nargs="+", default=None)
    parser.add_argument("-html_filename", type=str, default="results.html")
    parser.add_argument("-port", type=int, default=8002)
    parser.add_argument("-case_dir", type=str, default=".")
    parser.add_argument("-time_step", type=int, default=-1)
    parser.add_argument("-flow_field", type=str, default="p")
    parser.add_argument("-log_file", type=str, default="log_simulation.txt")
    parser.add_argument("-start_time", type=int, default=0)
    parser.add_argument("-end_time", type=int, default=-1)
    parser.add_argument("-start_time_cfd", type=int, default=0)
    parser.add_argument("-end_time_cfd", type=int, default=-1)
    parser.add_argument("-start_time_adjoint", type=int, default=0)
    parser.add_argument("-end_time_adjoint", type=int, default=-1)
    parser.add_argument("-x_location", type=float, default=0.5)
    parser.add_argument("-z_location", type=float, default=0.0)
    parser.add_argument("-zoom_in_scale", type=float, default=0.5)
    parser.add_argument("-plot_all_views", type=_parse_bool, default=False)
    parser.add_argument("-image_width", type=int, default=1200)
    parser.add_argument("-image_height", type=int, default=800)
    parser.add_argument("-mesh_file", type=str, nargs="+", default=["VTK/boundary.vtp"])
    parser.add_argument("-reference_pressure", type=float, default=None)
    parser.add_argument("-pressure_coefficient_scale", type=float, default=None)
    parser.add_argument("-var_ref", type=float, default=None)
    parser.add_argument("-var_scaling", type=float, default=None)
    parser.add_argument("-field_label", type=str, default=None)
    parser.add_argument("-var_lower", type=float, default=None)
    parser.add_argument("-var_upper", type=float, default=None)
    parser.add_argument("-colormap", type=str, default="coolwarm")
    parser.add_argument("-hist_file", type=str, default="OptView.hst")
    parser.add_argument("-optimizer_log", type=str, default="opt_SLSQP.txt")
    return parser.parse_args()


def main():
    args = parse_args()
    mesh_files = args.mesh_file

    if args.mode == "airfoil_plot_mesh":
        return airfoil_plot_mesh(
            case_dir=args.case_dir,
            mesh_file=mesh_files[0],
            x_location=args.x_location,
            z_location=args.z_location,
            zoom_in_scale=args.zoom_in_scale,
            plot_all_views=args.plot_all_views,
            image_width=args.image_width,
            image_height=args.image_height,
        )
    if args.mode == "airfoil_plot_pressure_profile":
        return airfoil_plot_pressure_profile(
            case_dir=args.case_dir,
            mesh_file=mesh_files,
            reference_pressure=args.reference_pressure,
            pressure_coefficient_scale=args.pressure_coefficient_scale,
            var_lower=args.var_lower,
            var_upper=args.var_upper,
        )
    if args.mode == "airfoil_plot_flow_field":
        return airfoil_plot_flow_field(
            case_dir=args.case_dir,
            flow_field=args.flow_field,
            time_step=args.time_step,
            field_file=mesh_files,
            x_location=args.x_location,
            z_location=args.z_location,
            zoom_in_scale=args.zoom_in_scale,
            colormap=args.colormap,
            image_width=args.image_width,
            image_height=args.image_height,
            var_ref=args.var_ref,
            var_scaling=args.var_scaling,
            field_label=args.field_label,
            var_lower=args.var_lower,
            var_upper=args.var_upper,
        )
    if args.mode == "general_plot_function":
        return general_plot_function(
            case_dir=args.case_dir,
            log_file=args.log_file,
            start_time=args.start_time,
            end_time=args.end_time,
        )
    if args.mode == "general_plot_optimization_history":
        return general_plot_optimization_history(
            case_dir=args.case_dir,
            hist_file=args.hist_file,
            optimizer_log=args.optimizer_log,
        )
    if args.mode == "general_plot_residual":
        return general_plot_residual(
            case_dir=args.case_dir,
            log_file=args.log_file,
            start_time_cfd=args.start_time_cfd,
            end_time_cfd=args.end_time_cfd,
            start_time_adjoint=args.start_time_adjoint,
            end_time_adjoint=args.end_time_adjoint,
            include_u1=False,
        )
    if args.mode == "trame_view":
        return general_trame_view(
            input_files=args.input_files,
            port=args.port,
        )
    if args.mode == "html_view":
        return general_html_view(
            root_dir=args.case_dir,
            port=args.port,
        )
    if args.mode == "html_gallery":
        return general_create_image_html(
            case_dir=args.case_dir,
            image_files=args.image_files,
            html_filename=args.html_filename,
        )

    raise ValueError(
        "Unsupported mode. Expected one of: "
        "airfoil_plot_mesh, airfoil_plot_pressure_profile, airfoil_plot_flow_field, "
        "general_plot_function, general_plot_optimization_history, general_plot_residual, "
        "trame_view, html_view, html_gallery."
    )


if __name__ == "__main__":
    main()

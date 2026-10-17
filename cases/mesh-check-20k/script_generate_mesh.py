#!/usr/bin/env python

import argparse
import json

from mdo_agent_mesh import _resolve_airfoil_mesh_settings
from mdo_agent_mesh import extrude_volume_mesh
from mdo_agent_mesh import generate_airfoil_surface_mesh


def parse_args():
    parser = argparse.ArgumentParser(
        description="Thin mdo_agent_airfoil wrapper for case-local airfoil mesh generation."
    )
    parser.add_argument("-airfoil_profile", type=str, default="naca0012")
    parser.add_argument("-mesh_cells", type=int, default=6000)
    parser.add_argument("-blunt_te", type=float, default=0.01)
    parser.add_argument("-y_plus", type=float, default=50.0)
    parser.add_argument("-mach_number", type=float, default=0.2)
    parser.add_argument("-reynolds_number", type=float, default=5e6)
    parser.add_argument("-d0", type=float, default=-1.0)
    return parser.parse_args()

def main():
    args = parse_args()
    with open("advanced_parameters.json", "r", encoding="utf-8") as handle:
        # Read only the advanced block for this skill from the flattened skill-scoped layout.
        advanced_parameters = json.load(handle).get("generate-cfd-mesh", {})

    # Compose the shared airfoil surface and shared volume-extrusion APIs in the case-local workflow script.
    generate_airfoil_surface_mesh(
        airfoil_profile=args.airfoil_profile,
        mesh_cells=args.mesh_cells,
        blunt_te=args.blunt_te,
        output_dir=".",
        vsp3_file="airfoil.vsp3",
    )
    _, _, resolved_extrusion_layers = _resolve_airfoil_mesh_settings(args.mesh_cells)
    resolved_d0 = args.d0 if args.d0 >= 0.0 else None
    extrude_volume_mesh(
        input="airfoil.xyz",
        out_dir="constant/polyMesh",
        L=30.0,
        d0=resolved_d0,
        y_plus=args.y_plus,
        mach_number=args.mach_number,
        reynolds_number=args.reynolds_number,
        ref_chord=1.0,
        N=resolved_extrusion_layers,
        hyperbolic_sweeps=int(advanced_parameters["hyperbolic_sweeps"]["value"]),
        neighbor_rings=int(advanced_parameters["neighbor_rings"]["value"]),
        diffuse_start=float(advanced_parameters["diffuse_start"]["value"]),
        mesh_2d=True,
        quiet=False,
    )


if __name__ == "__main__":
    main()

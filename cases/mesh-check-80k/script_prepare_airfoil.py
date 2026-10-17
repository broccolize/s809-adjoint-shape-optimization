#!/usr/bin/env python

import argparse
import os

from mdo_agent_base import download_airfoil_from_uiuc
from mdo_agent_base import ensure_airfoil_dat_format


def main():
    parser = argparse.ArgumentParser(
        description="Prepare an airfoil profile file for the mesh-generation workflow."
    )
    parser.add_argument(
        "--mode",
        choices=["normalize", "download"],
        required=True,
        help="Preparation mode to run.",
    )
    parser.add_argument(
        "--profile-file",
        required=True,
        help="Case-local output airfoil profile path.",
    )
    parser.add_argument(
        "--airfoil-profile",
        default="naca0012",
        help="Airfoil name used for download mode logging and UIUC lookup.",
    )
    parser.add_argument(
        "--target-points",
        type=int,
        default=200,
        help="Target number of points after normalization.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Download timeout in seconds for UIUC fetches.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=5,
        help="Download retry count for UIUC fetches.",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=5.0,
        help="Delay in seconds between UIUC download retries.",
    )
    args = parser.parse_args()

    profile_file = os.path.abspath(args.profile_file)
    profiles_dir = os.path.dirname(profile_file)
    if profiles_dir:
        os.makedirs(profiles_dir, exist_ok=True)

    if args.mode == "normalize":
        ensure_airfoil_dat_format(profile_file, target_points=args.target_points)
        return

    log_file = os.path.join(os.getcwd(), "log_download_airfoil.txt")
    with open(log_file, "w", encoding="utf-8", errors="ignore") as handle:
        handle.write(
            f"Downloading the {args.airfoil_profile} airfoil profile from the UIUC database\n"
        )
        download_status, download_info = download_airfoil_from_uiuc(
            args.airfoil_profile,
            profile_file,
            timeout=args.timeout,
            retries=args.retries,
            retry_delay=args.retry_delay,
            target_points=args.target_points,
        )
        if not download_status:
            handle.write(
                f"Error: the {args.airfoil_profile} airfoil profile could not be downloaded. "
                f"Last error: {download_info}\n"
            )
            raise RuntimeError(
                f"Failed to download airfoil profile {args.airfoil_profile}: {download_info}"
            )

        handle.write("Download completed\n")
        handle.write(f"Download source: {download_info}\n")
        handle.write(f"Saved profile: {profile_file}\n")


if __name__ == "__main__":
    main()

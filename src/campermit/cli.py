import argparse

from . import __version__
from .discovery import discover_cameras
from .output import cameras_json, cameras_list
from .sysfs import Sysfs


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="campermit",
        description="Control camera availability at the device and driver level.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
    )

    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser(
        "list",
        help="List discovered cameras.",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON.",
    )

    args = parser.parse_args()

    if args.command == "list":
        cameras = discover_cameras(Sysfs())

        if args.json:
            print(cameras_json(cameras))
        else:
            print(cameras_list(cameras))


if __name__ == "__main__":
    main()
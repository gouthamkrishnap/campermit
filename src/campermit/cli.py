import argparse

from . import __version__
from .discovery import discover_cameras
from .output import (
    camera_status,
    camera_status_json,
    cameras_json,
    cameras_list,
)
from .selectors import select_camera
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

    status_parser = subparsers.add_parser(
        "status",
        help="Show the state of a camera.",
    )
    status_parser.add_argument(
        "selector",
        help="Camera ID, bus path, or VID:PID.",
    )
    status_parser.add_argument(
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

    elif args.command == "status":
        cameras = discover_cameras(Sysfs())

        try:
            camera = select_camera(cameras, args.selector)
        except ValueError as error:
            parser.error(str(error))

        if args.json:
            print(camera_status_json(camera))
        else:
            print(camera_status(camera))


if __name__ == "__main__":
    main()
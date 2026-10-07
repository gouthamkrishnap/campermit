import argparse

from . import __version__
from .discovery import discover_cameras
from .output import (
    camera_info,
    camera_info_json,
    camera_status,
    camera_status_json,
    cameras_info_json,
    cameras_json,
    cameras_list,
    operation_result,
    operation_result_json,
)
from .selectors import select_camera
from .service import disable, enable, toggle
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

    info_parser = subparsers.add_parser(
        "info",
        help="Show detailed information about cameras.",
    )
    info_parser.add_argument(
        "selector",
        nargs="?",
        help="Camera ID, bus path, or VID:PID.",
    )
    info_parser.add_argument(
        "--all",
        action="store_true",
        help="Show information for all cameras.",
    )
    info_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON.",
    )

    enable_parser = subparsers.add_parser(
        "enable",
        help="Enable a camera.",
    )
    enable_parser.add_argument(
        "selector",
        help="Camera ID, bus path, or VID:PID.",
    )
    enable_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON.",
    )

    disable_parser = subparsers.add_parser(
        "disable",
        help="Disable a camera.",
    )
    disable_parser.add_argument(
        "selector",
        help="Camera ID, bus path, or VID:PID.",
    )
    disable_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON.",
    )

    toggle_parser = subparsers.add_parser(
        "toggle",
        help="Toggle a camera.",
    )
    toggle_parser.add_argument(
        "selector",
        help="Camera ID, bus path, or VID:PID.",
    )
    toggle_parser.add_argument(
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

    elif args.command == "info":
        if args.selector and args.all:
            info_parser.error(
                "camera selector and --all cannot be used together."
            )

        if not args.selector and not args.all:
            info_parser.error(
                "a camera selector or --all is required."
            )

        cameras = discover_cameras(Sysfs())

        if args.all:
            if args.json:
                print(cameras_info_json(cameras))
            else:
                for index, camera in enumerate(cameras):
                    if index:
                        print()
                    print(camera_info(camera))
        else:
            try:
                camera = select_camera(cameras, args.selector)
            except ValueError as error:
                info_parser.error(str(error))

            if args.json:
                print(camera_info_json(camera))
            else:
                print(camera_info(camera))

    elif args.command in {"enable", "disable", "toggle"}:
        cameras = discover_cameras(Sysfs())

        try:
            camera = select_camera(cameras, args.selector)
        except ValueError as error:
            parser.error(str(error))

        sysfs = Sysfs()

        try:
            if args.command == "enable":
                result = enable(
                    camera,
                    sysfs=sysfs,
                )
            elif args.command == "disable":
                result = disable(
                    camera,
                    sysfs=sysfs,
                )
            else:
                result = toggle(
                    camera,
                    sysfs=sysfs,
                )
        except ValueError as error:
            parser.error(str(error))

        if args.json:
            print(operation_result_json(camera, result))
        else:
            print(operation_result(camera, result))


if __name__ == "__main__":
    main()
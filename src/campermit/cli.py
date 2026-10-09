
import argparse
import sys

from . import __version__
from .discovery import discover_cameras
from .errors import CamPermitError
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
    operation_results,
    operation_results_json,
)
from .selectors import select_camera
from .service import (
    disable,
    disable_all,
    enable,
    enable_all,
    toggle,
)
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
        nargs="?",
        help="Camera ID, bus path, or VID:PID.",
    )
    enable_parser.add_argument(
        "--all",
        action="store_true",
        help="Enable all cameras.",
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
        nargs="?",
        help="Camera ID, bus path, or VID:PID.",
    )
    disable_parser.add_argument(
        "--all",
        action="store_true",
        help="Disable all cameras.",
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

    elif args.command in {"enable", "disable"}:
        if args.selector and args.all:
            if args.command == "enable":
                enable_parser.error(
                    "camera selector and --all cannot be used together."
                )

            disable_parser.error(
                "camera selector and --all cannot be used together."
            )

        if not args.selector and not args.all:
            if args.command == "enable":
                enable_parser.error(
                    "a camera selector or --all is required."
                )

            disable_parser.error(
                "a camera selector or --all is required."
            )

        sysfs = Sysfs()
        cameras = discover_cameras(sysfs)

        if args.all:
            if not cameras:
                if args.json:
                    print(operation_results_json(args.command, []))
                else:
                    print("No cameras found.")
                return

            if args.command == "enable":
                results = enable_all(
                    cameras,
                    sysfs=sysfs,
                )
            else:
                results = disable_all(
                    cameras,
                    sysfs=sysfs,
                )

            if args.json:
                print(
                    operation_results_json(
                        args.command,
                        results,
                    )
                )
            else:
                print(
                    operation_results(
                        args.command,
                        results,
                    )
                )

            if any(result.error is not None for result in results):
                raise SystemExit(1)

        else:
            try:
                camera = select_camera(
                    cameras,
                    args.selector,
                )
            except ValueError as error:
                if args.command == "enable":
                    enable_parser.error(str(error))

                disable_parser.error(str(error))

            try:
                if args.command == "enable":
                    result = enable(
                        camera,
                        sysfs=sysfs,
                    )
                else:
                    result = disable(
                        camera,
                        sysfs=sysfs,
                    )
            except CamPermitError as error:
                print(f"campermit: {error}", file=sys.stderr)
                raise SystemExit(1) from None

            if args.json:
                print(
                    operation_result_json(
                        camera,
                        result,
                    )
                )
            else:
                print(
                    operation_result(
                        camera,
                        result,
                    )
                )

    elif args.command == "toggle":
        cameras = discover_cameras(Sysfs())

        try:
            camera = select_camera(
                cameras,
                args.selector,
            )
        except ValueError as error:
            toggle_parser.error(str(error))

        sysfs = Sysfs()

        try:
            result = toggle(
                camera,
                sysfs=sysfs,
            )
        except CamPermitError as error:
            print(f"campermit: {error}", file=sys.stderr)
            raise SystemExit(1) from None

        if args.json:
            print(
                operation_result_json(
                    camera,
                    result,
                )
            )
        else:
            print(
                operation_result(
                    camera,
                    result,
                )
            )


if __name__ == "__main__":
    main()

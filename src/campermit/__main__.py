import argparse
import errno
import sys
from importlib.metadata import version
from pathlib import Path

from campermit import uvc
from campermit.discovery import Camera, discover, find_camera


def state(camera: Camera) -> str:
    if camera.driver is None:
        return "disabled"
    if camera.driver == "uvcvideo":
        return "enabled"
    return f"used by {camera.driver}"


def list_cameras(root: Path) -> int:
    cameras = discover(root)

    if not cameras:
        print("No USB cameras found.")
        return 0

    for camera in cameras:
        print(
            f"{camera.id}  {camera.name}  {camera.usb_id}  "
            f"{state(camera)}  {' '.join(camera.nodes)}"
        )
    return 0


def set_camera(root: Path, camera_id: str, *, enabled: bool) -> int:
    verb = "enable" if enabled else "disable"
    state = "enabled" if enabled else "disabled"

    matches = find_camera(discover(root), camera_id)

    if not matches:
        print(f"campermit: no camera named {camera_id}", file=sys.stderr)
        return 1

    if len(matches) > 1:
        ids = ", ".join(camera.id for camera in matches)
        print(
            f"campermit: {camera_id} matches several cameras: {ids}",
            file=sys.stderr,
        )
        return 1

    camera = matches[0]

    is_enabled = camera.driver == uvc.DRIVER

    if camera.driver is not None and not is_enabled:
        print(
            f"campermit: {camera.id} is used by {camera.driver}, not {uvc.DRIVER}",
            file=sys.stderr,
        )
        return 1

    if is_enabled == enabled:
        print(f"{camera.id} is already {state}")
        return 0

    change = uvc.enable if enabled else uvc.disable
    already_done = errno.EBUSY if enabled else errno.ENODEV

    try:
        change(root, camera)
    except PermissionError:
        print(
            "campermit: permission denied, this needs root (try sudo)",
            file=sys.stderr,
        )
        return 1
    except FileNotFoundError:
        if (root / "bus/usb/drivers" / uvc.DRIVER).is_dir():
            print(
                f"campermit: {camera.id} is no longer connected",
                file=sys.stderr,
            )
        else:
            print(
                f"campermit: the {uvc.DRIVER} driver is not loaded "
                f"(try: sudo modprobe {uvc.DRIVER})",
                file=sys.stderr,
            )
        return 1
    except OSError as error:
        if error.errno == already_done:
            print(f"{camera.id} is already {state}")
            return 0
        print(
            f"campermit: could not {verb} {camera.id}: {error.strerror}",
            file=sys.stderr,
        )
        return 1

    print(f"{state.capitalize()} {camera.id}  {camera.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="campermit",
        description="Enable and disable USB webcams on Linux.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"campermit {version('campermit')}",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("list", help="show the cameras and whether they are on")

    for name, text in (
        ("enable", "turn a camera on"),
        ("disable", "turn a camera off"),
    ):
        command = commands.add_parser(name, help=text)
        command.add_argument(
            "camera",
            help="a camera ID such as 3-6:1.0, or a USB device such as 3-6",
        )

    return parser


def main(argv: list[str] | None = None, root: Path = Path("/sys")) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as error:
        return int(error.code or 0)

    if args.command == "list":
        return list_cameras(root)

    return set_camera(root, args.camera, enabled=args.command == "enable")


if __name__ == "__main__":
    raise SystemExit(main())

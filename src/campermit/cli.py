import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path

from campermit import __version__, persist, uvc
from campermit.discovery import Camera, discover, find_camera
from campermit.elevate import ask_for_root
from campermit.errors import CampermitError

NO_CAMERAS = "No USB cameras found."


def state_name(camera: Camera) -> str:
    if camera.driver is None:
        return "disabled"
    if camera.driver == uvc.DRIVER:
        return "enabled"
    return "other"


def state(camera: Camera) -> str:
    name = state_name(camera)
    if name == "other":
        return f"used by {camera.driver}"
    return name


def table(rows: list[tuple[str, ...]]) -> str:
    widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
    return "\n".join(
        "  ".join(
            cell.ljust(width) for cell, width in zip(row, widths, strict=True)
        ).rstrip()
        for row in rows
    )


def camera_data(camera: Camera) -> dict:
    return {
        "id": camera.id,
        "name": camera.name,
        "usb_id": camera.usb_id,
        "state": state_name(camera),
        "driver": camera.driver,
        "nodes": camera.nodes,
    }


def list_cameras(root: Path, *, as_json: bool = False) -> int:
    cameras = discover(root)

    if as_json:
        import json

        data = {
            "schema_version": 1,
            "cameras": [camera_data(camera) for camera in cameras],
        }
        print(json.dumps(data, indent=2))
        return 0

    if not cameras:
        print(NO_CAMERAS)
        if any((root / "class/video4linux").glob("video*")):
            print(
                "Other video devices exist (for example a built-in MIPI "
                "camera), but they are not USB cameras, so campermit "
                "cannot control them."
            )
        return 0

    rows = [("ID", "NAME", "USB ID", "STATE", "NODES")]
    for camera in cameras:
        rows.append(
            (
                camera.id,
                camera.name,
                camera.usb_id,
                state(camera),
                " ".join(camera.nodes),
            )
        )
    print(table(rows))
    return 0


def show_status(root: Path, camera_id: str) -> int:
    camera = pick_camera(root, camera_id)

    if camera is None:
        return 1

    print(state(camera))
    return 0


def list_error(error: OSError) -> str:
    if isinstance(error, PermissionError):
        return "permission denied, this needs root (try sudo)"
    return error.strerror or str(error)


def apply(
    root: Path,
    camera: Camera,
    enabled: bool,
    disabled_file: Path,
    *,
    keep: bool = False,
) -> bool:
    word = "enabled" if enabled else "disabled"

    if enabled:
        # Forget the camera before binding it. Binding fires the udev rule,
        # which runs restore, and restore would switch the camera straight
        # off again if it were still on the list.
        try:
            persist.remove(disabled_file, camera)
        except OSError as error:
            print(
                f"campermit: {camera.id}: could not update {disabled_file}: "
                f"{list_error(error)}",
                file=sys.stderr,
            )
            return False

    try:
        changed = uvc.set_enabled(root, camera, enabled)
    except CampermitError as error:
        print(f"campermit: {camera.id}: {error}", file=sys.stderr)
        return False

    if changed:
        print(f"{word.capitalize()} {camera.id}  {camera.name}")
    else:
        print(f"{camera.id} is already {word}")

    if keep:
        try:
            persist.add(disabled_file, camera.id)
        except OSError as error:
            print(
                f"campermit: {camera.id}: disabled, but could not save that to "
                f"{disabled_file}: {list_error(error)}",
                file=sys.stderr,
            )
            return False
        print(f"{camera.id} will stay disabled after a reboot or replug")

    return True


def pick_camera(root: Path, name: str) -> Camera | None:
    matches = find_camera(discover(root), name)

    if not matches:
        hint = " (a name needs at least 3 characters)" if len(name.strip()) < 3 else ""
        print(f"campermit: no camera named {name}{hint}", file=sys.stderr)
        return None

    if len(matches) > 1:
        ids = ", ".join(camera.id for camera in matches)
        print(
            f"campermit: {name} matches several cameras: {ids}",
            file=sys.stderr,
        )
        return None

    return matches[0]


def needs_root(camera: Camera, enabled: bool, disabled_file: Path, keep: bool) -> bool:
    # A camera used by another driver is refused without touching anything.
    if camera.driver not in (None, uvc.DRIVER):
        return False

    if keep or (camera.driver == uvc.DRIVER) != enabled:
        return True

    # Already as wanted, but enabling still has to clear it from the list.
    if enabled:
        try:
            return persist.listed(disabled_file, camera)
        except OSError:
            return True

    return False


def root_arguments(enabled: bool, target: str, keep: bool) -> list[str]:
    return [
        "enable" if enabled else "disable",
        target,
        *(["--persist"] if keep else []),
    ]


def set_camera(
    root: Path,
    camera_id: str,
    disabled_file: Path,
    *,
    enabled: bool | None,
    keep: bool = False,
    elevate: Callable[[list[str]], int] | None = None,
) -> int:
    camera = pick_camera(root, camera_id)

    if camera is None:
        return 1

    if enabled is None:
        enabled = camera.driver != uvc.DRIVER

    if elevate is not None and needs_root(camera, enabled, disabled_file, keep):
        return elevate(root_arguments(enabled, camera.id, keep))

    return 0 if apply(root, camera, enabled, disabled_file, keep=keep) else 1


CAMERA_HELP = (
    "a camera ID such as 3-6:1.0, a USB device such as 3-6, "
    "a vendor:product pair such as 0408:5482, or part of its name "
    "(3 or more characters, in quotes if it has spaces)"
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="campermit",
        description="Enable and disable USB webcams on Linux.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"campermit {__version__}",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    list_command = commands.add_parser(
        "list", help="show the cameras and whether they are on"
    )
    list_command.add_argument(
        "--json",
        action="store_true",
        help="print the cameras as JSON, for scripts",
    )

    status = commands.add_parser(
        "status", help="print enabled, disabled, or which driver has it"
    )
    status.add_argument("camera", help=CAMERA_HELP)

    for name, text in (
        ("enable", "turn a camera on"),
        ("disable", "turn a camera off (add --persist to keep it off after a reboot)"),
    ):
        command = commands.add_parser(name, help=text)
        if name == "disable":
            command.add_argument(
                "--persist",
                action="store_true",
                help="also keep it off after a reboot or replug",
            )
        choice = command.add_mutually_exclusive_group(required=True)
        choice.add_argument(
            "camera",
            nargs="?",
            help=CAMERA_HELP,
        )
        choice.add_argument(
            "--all",
            action="store_true",
            help="do it for every camera instead of one",
        )

    toggle = commands.add_parser(
        "toggle", help="turn a camera on if it is off, and off if it is on"
    )
    toggle.add_argument(
        "camera",
        help=CAMERA_HELP,
    )

    restore_command = commands.add_parser(
        "restore",
        help="turn a camera off again if it was disabled with --persist "
        "(run by the udev rule, you rarely need it)",
    )
    restore_command.add_argument("camera", help="the exact camera ID, such as 3-6:1.0")

    return parser


def set_all(
    root: Path,
    disabled_file: Path,
    *,
    enabled: bool,
    keep: bool = False,
    elevate: Callable[[list[str]], int] | None = None,
) -> int:
    cameras = discover(root)

    if not cameras:
        print(NO_CAMERAS)
        return 0

    if elevate is not None and any(
        needs_root(camera, enabled, disabled_file, keep) for camera in cameras
    ):
        return elevate(root_arguments(enabled, "--all", keep))

    results = [
        apply(root, camera, enabled, disabled_file, keep=keep) for camera in cameras
    ]
    return 0 if all(results) else 1


def restore(root: Path, disabled_file: Path, camera_id: str) -> int:
    saved = persist.entries(disabled_file)
    camera = next((found for found in discover(root) if found.id == camera_id), None)

    if camera is None:
        return 0

    if any(entry.matches(camera) for entry in saved):
        return 0 if apply(root, camera, False, disabled_file) else 1

    for entry in saved:
        if entry.is_at(camera):
            print(
                f"campermit: {camera.id} was saved as {entry.usb_id}, but the "
                f"camera there is now {camera.usb_id}, so it was left on",
                file=sys.stderr,
            )

    return 0


def main(
    argv: list[str] | None = None,
    root: Path = Path("/sys"),
    disabled_file: Path | None = None,
    elevate: Callable[[list[str]], int] | None = None,
) -> int:
    if disabled_file is None:
        disabled_file = persist.DEFAULT_PATH
    try:
        args, extra = build_parser().parse_known_args(argv)
    except SystemExit as error:
        return int(error.code or 0)

    if extra:
        options = [word for word in extra if word.startswith("-")]

        if options:
            print(
                f'campermit: {args.command} does not take "{options[0]}". '
                f"Try campermit {args.command} --help.",
                file=sys.stderr,
            )
            return 2

        words = " ".join(extra)
        print(
            f'campermit: unexpected "{words}". A camera name with spaces needs quotes.',
            file=sys.stderr,
        )
        return 2

    if args.command == "list":
        return list_cameras(root, as_json=args.json)

    if args.command == "status":
        return show_status(root, args.camera)

    if args.command == "restore":
        return restore(root, disabled_file, args.camera)

    keep = getattr(args, "persist", False)

    if getattr(args, "all", False):
        return set_all(
            root,
            disabled_file,
            enabled=args.command == "enable",
            keep=keep,
            elevate=elevate,
        )

    wanted = {"enable": True, "disable": False, "toggle": None}
    return set_camera(
        root,
        args.camera,
        disabled_file,
        enabled=wanted[args.command],
        keep=keep,
        elevate=elevate,
    )


def run() -> int:
    return main(elevate=None if os.geteuid() == 0 else ask_for_root)

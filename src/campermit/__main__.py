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


def main(argv: list[str] | None = None, root: Path = Path("/sys")) -> int:
    args = sys.argv[1:] if argv is None else argv

    if args == ["list"]:
        return list_cameras(root)

    if len(args) == 2 and args[0] == "enable":
        return set_camera(root, args[1], enabled=True)

    if len(args) == 2 and args[0] == "disable":
        return set_camera(root, args[1], enabled=False)

    print(f"campermit {version('campermit')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

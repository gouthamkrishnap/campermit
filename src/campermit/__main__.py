import sys
from importlib.metadata import version
from pathlib import Path

from campermit import uvc
from campermit.discovery import Camera, discover


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


def disable_camera(root: Path, camera_id: str) -> int:
    camera = next((c for c in discover(root) if c.id == camera_id), None)

    if camera is None:
        print(f"campermit: no camera named {camera_id}", file=sys.stderr)
        return 1

    if camera.driver is None:
        print(f"{camera.id} is already disabled")
        return 0

    if camera.driver != uvc.DRIVER:
        print(
            f"campermit: {camera.id} is used by {camera.driver}, not {uvc.DRIVER}",
            file=sys.stderr,
        )
        return 1

    uvc.disable(root, camera)
    print(f"Disabled {camera.id}  {camera.name}")
    return 0


def main(argv: list[str] | None = None, root: Path = Path("/sys")) -> int:
    args = sys.argv[1:] if argv is None else argv

    if args == ["list"]:
        return list_cameras(root)

    if len(args) == 2 and args[0] == "disable":
        return disable_camera(root, args[1])

    print(f"campermit {version('campermit')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

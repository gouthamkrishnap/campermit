import sys
from importlib.metadata import version
from pathlib import Path

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


def main(argv: list[str] | None = None, root: Path = Path("/sys")) -> int:
    args = sys.argv[1:] if argv is None else argv

    if args == ["list"]:
        return list_cameras(root)

    print(f"campermit {version('campermit')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import re
from pathlib import Path
from typing import NamedTuple

UVC_CLASS = "0e"
VIDEO_CONTROL = "01"


class Camera(NamedTuple):
    id: str
    name: str
    usb_id: str
    driver: str | None
    nodes: list[str]


def read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        return None


def port_order(name: str) -> list[int]:
    return [int(number) for number in re.findall(r"\d+", name)]


def discover(root: Path) -> list[Camera]:
    devices = root / "bus/usb/devices"
    cameras = []

    for interface in sorted(
        devices.glob("*:*"), key=lambda path: port_order(path.name)
    ):
        if read(interface / "bInterfaceClass") != UVC_CLASS:
            continue
        if read(interface / "bInterfaceSubClass") != VIDEO_CONTROL:
            continue

        device = devices / interface.name.split(":")[0]
        usb_id = f"{read(device / 'idVendor')}:{read(device / 'idProduct')}"
        link = interface / "driver"
        nodes = sorted((interface / "video4linux").glob("video*"))

        cameras.append(
            Camera(
                id=interface.name,
                name=read(device / "product") or f"USB camera {usb_id}",
                usb_id=usb_id,
                driver=link.resolve().name if link.is_symlink() else None,
                nodes=[f"/dev/{node.name}" for node in nodes],
            )
        )

    return cameras


def find_camera(cameras: list[Camera], name: str) -> list[Camera]:
    for matches in (
        [camera for camera in cameras if camera.id == name],
        [camera for camera in cameras if camera.id.split(":")[0] == name],
        [camera for camera in cameras if camera.usb_id == name.lower()],
    ):
        if matches:
            return matches
    return []

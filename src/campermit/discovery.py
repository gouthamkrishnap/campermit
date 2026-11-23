import re
from itertools import pairwise
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
    controller: str | None = None


def read(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        return None


def numeric_order(name: str) -> list[int]:
    return [int(number) for number in re.findall(r"\d+", name)]


def controller_of(device: Path) -> str | None:
    for before, part in pairwise(device.resolve().parts):
        if re.fullmatch(r"usb\d+", part):
            return before
    return None


def discover(root: Path) -> list[Camera]:
    devices = root / "bus/usb/devices"
    cameras = []

    for interface in sorted(
        devices.glob("*:*"), key=lambda path: numeric_order(path.name)
    ):
        if read(interface / "bInterfaceClass") != UVC_CLASS:
            continue
        if read(interface / "bInterfaceSubClass") != VIDEO_CONTROL:
            continue

        device = devices / interface.name.split(":")[0]
        vendor_id = read(device / "idVendor")
        product_id = read(device / "idProduct")
        if vendor_id is None or product_id is None:
            continue
        usb_id = f"{vendor_id}:{product_id}"
        link = interface / "driver"
        nodes = sorted(
            (interface / "video4linux").glob("video*"),
            key=lambda path: numeric_order(path.name),
        )

        cameras.append(
            Camera(
                id=interface.name,
                name=read(device / "product") or f"USB camera {usb_id}",
                usb_id=usb_id,
                driver=link.resolve().name if link.is_symlink() else None,
                nodes=[f"/dev/{node.name}" for node in nodes],
                controller=controller_of(device),
            )
        )

    return cameras


def find_camera(cameras: list[Camera], name: str) -> list[Camera]:
    text = name.strip().lower()
    levels = [
        [camera for camera in cameras if camera.id == name],
        [camera for camera in cameras if camera.id.split(":")[0] == name],
        [camera for camera in cameras if camera.usb_id == text],
        [camera for camera in cameras if camera.name.lower() == text],
    ]
    if len(text) >= 3:
        levels.append([camera for camera in cameras if text in camera.name.lower()])

    for matches in levels:
        if matches:
            return matches
    return []

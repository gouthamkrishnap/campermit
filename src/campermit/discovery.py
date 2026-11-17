import re
from dataclasses import dataclass
from pathlib import Path

UVC_CLASS = "0e"
VIDEO_CONTROL = "01"


@dataclass(frozen=True)
class Camera:
    id: str
    name: str
    usb_id: str
    driver: str | None
    nodes: list[str]


def read(path: Path) -> str:
    return path.read_text().strip()


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
        link = interface / "driver"
        nodes = sorted((interface / "video4linux").glob("video*"))

        cameras.append(
            Camera(
                id=interface.name,
                name=read(device / "product"),
                usb_id=f"{read(device / 'idVendor')}:{read(device / 'idProduct')}",
                driver=link.resolve().name if link.is_symlink() else None,
                nodes=[f"/dev/{node.name}" for node in nodes],
            )
        )

    return cameras

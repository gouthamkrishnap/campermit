from pathlib import Path

from campermit.discovery import Camera

DRIVER = "uvcvideo"


def write(path: Path, text: str) -> None:
    path.write_text(text + "\n")


def disable(root: Path, camera: Camera) -> None:
    write(root / "bus/usb/drivers" / DRIVER / "unbind", camera.id)

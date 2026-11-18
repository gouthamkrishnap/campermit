import errno
import os
from pathlib import Path

from campermit.discovery import Camera
from campermit.errors import CampermitError

DRIVER = "uvcvideo"


def write(path: Path, text: str) -> None:
    data = (text + "\n").encode()
    fd = os.open(path, os.O_WRONLY)
    try:
        written = os.write(fd, data)
    finally:
        os.close(fd)
    if written != len(data):
        raise OSError(errno.EIO, "short write")


def disable(root: Path, camera: Camera) -> None:
    write(root / "bus/usb/drivers" / DRIVER / "unbind", camera.id)


def enable(root: Path, camera: Camera) -> None:
    write(root / "bus/usb/drivers" / DRIVER / "bind", camera.id)


def set_enabled(root: Path, camera: Camera, enabled: bool) -> bool:
    """Make the camera enabled or disabled.

    Returns True if it changed, False if it was already as wanted.
    """
    is_enabled = camera.driver == DRIVER

    if camera.driver is not None and not is_enabled:
        raise CampermitError(f"{camera.id} is used by {camera.driver}, not {DRIVER}")

    if is_enabled == enabled:
        return False

    change = enable if enabled else disable
    verb = "enable" if enabled else "disable"
    already_done = errno.EBUSY if enabled else errno.ENODEV

    try:
        change(root, camera)
    except PermissionError:
        raise CampermitError("permission denied, this needs root (try sudo)") from None
    except FileNotFoundError:
        if (root / "bus/usb/drivers" / DRIVER).is_dir():
            raise CampermitError(f"{camera.id} is no longer connected") from None
        raise CampermitError(
            f"the {DRIVER} driver is not loaded (try: sudo modprobe {DRIVER})"
        ) from None
    except OSError as error:
        if error.errno == already_done:
            return False
        raise CampermitError(
            f"could not {verb} {camera.id}: {error.strerror}"
        ) from None

    return True

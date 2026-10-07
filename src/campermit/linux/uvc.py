import errno
import os
import re
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable

from ..errors import (
    BoundToOtherDriver,
    CamPermitError,
    InterfaceGone,
    InvalidInterface,
    NotVideoControl,
    PermissionDenied,
    SysfsReadError,
    SysfsWriteError,
    VerificationFailed,
)


UVC_DRIVER = "uvcvideo"

_INTERFACE_NAME = re.compile(
    r"[0-9]+-[0-9]+(?:\.[0-9]+)*:[0-9]+\.[0-9]+"
)


class State(Enum):
    GONE = "gone"
    UNBOUND = "unbound"
    BOUND = "bound"
    OTHER = "other"


class Outcome(Enum):
    CHANGED = "changed"
    ALREADY = "already"


@dataclass(frozen=True)
class Observed:
    state: State
    driver: str | None = None


@dataclass(frozen=True)
class ControlInterface:
    name: str


def _device_path(root: Path, name: str) -> Path:
    return root / "bus" / "usb" / "devices" / name


def _read_hex(path: Path) -> int | None:
    try:
        value = path.read_text().strip()
    except OSError as error:
        raise SysfsReadError(
            f"Failed to read '{path}': {error}",
            errno_value=error.errno,
        ) from error

    try:
        return int(value, 16)
    except ValueError:
        return None


def parse_control_interface(
    root: Path,
    name: str,
) -> ControlInterface:
    if not _INTERFACE_NAME.fullmatch(name):
        raise InvalidInterface(name)

    device = _device_path(root, name)

    if not device.is_dir():
        raise InterfaceGone(name)

    if _read_hex(device / "bInterfaceClass") != 0x0E:
        raise NotVideoControl(name)

    if _read_hex(device / "bInterfaceSubClass") != 0x01:
        raise NotVideoControl(name)

    return ControlInterface(name)


def observe(
    root: Path,
    interface: ControlInterface,
) -> Observed:
    device = _device_path(root, interface.name)

    try:
        target = os.readlink(device / "driver")
    except FileNotFoundError:
        if device.is_dir():
            return Observed(State.UNBOUND)

        return Observed(State.GONE)
    except OSError as error:
        if error.errno in (
            errno.ENODEV,
            errno.ENOTDIR,
            errno.ESTALE,
        ):
            return Observed(State.GONE)

        raise SysfsReadError(
            f"Failed to read driver state for '{interface.name}': {error}",
            errno_value=error.errno,
        ) from error

    driver = os.path.basename(target)

    if driver == UVC_DRIVER:
        return Observed(State.BOUND, driver)

    return Observed(State.OTHER, driver)


def _write_sysfs(path: Path, payload: str) -> None:
    data = payload.encode("ascii")

    fd = os.open(
        path,
        os.O_WRONLY | os.O_CLOEXEC,
    )

    try:
        written = os.write(fd, data)

        if written != len(data):
            raise OSError(
                errno.EIO,
                "short write to sysfs",
            )
    finally:
        os.close(fd)


def _map_write_error(
    error: OSError,
    observed: Observed,
    interface: ControlInterface,
) -> CamPermitError:
    if error.errno in (
        errno.EACCES,
        errno.EPERM,
        errno.EROFS,
    ):
        return PermissionDenied(
            f"Permission denied while modifying '{interface.name}'."
        )

    if error.errno == errno.ENOENT:
        if observed.state is State.GONE:
            return InterfaceGone(interface.name)

    if error.errno == errno.EBUSY:
        if observed.state is State.OTHER:
            return BoundToOtherDriver(interface.name)

    if error.errno == errno.ENODEV:
        if observed.state is State.GONE:
            return InterfaceGone(interface.name)

    return SysfsWriteError(
        f"Failed to modify '{interface.name}': {error}",
        errno_value=error.errno,
    )


def _wait_for_state(
    root: Path,
    interface: ControlInterface,
    expected: State,
    *,
    clock: Callable[[], float],
    sleep: Callable[[float], None],
    timeout: float,
    interval: float,
) -> Observed:
    deadline = clock() + timeout

    while True:
        observed = observe(root, interface)

        if observed.state is expected:
            return observed

        remaining = deadline - clock()

        if remaining <= 0:
            return observed

        sleep(min(interval, remaining))


def set_bound(
    root: Path,
    interface: ControlInterface,
    want_bound: bool,
    *,
    writer: Callable[[Path, str], None] = _write_sysfs,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    timeout: float = 2.0,
    interval: float = 0.05,
) -> Outcome:
    target = State.BOUND if want_bound else State.UNBOUND

    before = observe(root, interface)

    if before.state is State.GONE:
        raise InterfaceGone(interface.name)

    if before.state is State.OTHER:
        raise BoundToOtherDriver(interface.name)

    if before.state is target:
        return Outcome.ALREADY

    action = "bind" if want_bound else "unbind"

    parse_control_interface(root, interface.name)

    try:
        writer(
            root
            / "bus"
            / "usb"
            / "drivers"
            / UVC_DRIVER
            / action,
            interface.name,
        )
    except OSError as error:
        after = observe(root, interface)

        if after.state is target:
            return Outcome.ALREADY

        raise _map_write_error(
            error,
            after,
            interface,
        ) from error

    final = _wait_for_state(
        root,
        interface,
        target,
        clock=clock,
        sleep=sleep,
        timeout=timeout,
        interval=interval,
    )

    if final.state is not target:
        raise VerificationFailed(interface.name)

    return Outcome.CHANGED
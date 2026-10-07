import fcntl
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from .errors import (
    BoundToOtherDriver,
    InterfaceGone,
)
from .linux.uvc import (
    Outcome,
    State,
    observe,
    parse_control_interface,
    set_bound,
)
from .models import Camera
from .sysfs import Sysfs


LOCK_PATH = Path("/run/lock/campermit.lock")


@dataclass(frozen=True)
class OperationResult:
    outcome: Outcome
    state: State


class OperationLock:
    def __init__(self, path: Path = LOCK_PATH):
        self.path = path
        self._file: IO[str] | None = None

    def __enter__(self) -> "OperationLock":
        self._file = self.path.open("a+")
        fcntl.flock(
            self._file.fileno(),
            fcntl.LOCK_EX,
        )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        if self._file is None:
            return

        try:
            fcntl.flock(
                self._file.fileno(),
                fcntl.LOCK_UN,
            )
        finally:
            self._file.close()
            self._file = None


def enable(
    camera: Camera,
    *,
    sysfs: Sysfs,
    lock_path: Path = LOCK_PATH,
) -> OperationResult:
    if len(camera.functions) != 1:
        raise ValueError(
            f"Camera '{camera.id}' must have exactly one UVC function."
        )

    with OperationLock(lock_path):
        interface = parse_control_interface(
            sysfs.root,
            camera.functions[0].control_interface,
        )

        outcome = set_bound(
            sysfs.root,
            interface,
            True,
        )

        return OperationResult(
            outcome=outcome,
            state=State.BOUND,
        )


def disable(
    camera: Camera,
    *,
    sysfs: Sysfs,
    lock_path: Path = LOCK_PATH,
) -> OperationResult:
    if len(camera.functions) != 1:
        raise ValueError(
            f"Camera '{camera.id}' must have exactly one UVC function."
        )

    with OperationLock(lock_path):
        interface = parse_control_interface(
            sysfs.root,
            camera.functions[0].control_interface,
        )

        outcome = set_bound(
            sysfs.root,
            interface,
            False,
        )

        return OperationResult(
            outcome=outcome,
            state=State.UNBOUND,
        )


def toggle(
    camera: Camera,
    *,
    sysfs: Sysfs,
    lock_path: Path = LOCK_PATH,
) -> OperationResult:
    if len(camera.functions) != 1:
        raise ValueError(
            f"Camera '{camera.id}' must have exactly one UVC function."
        )

    with OperationLock(lock_path):
        interface = parse_control_interface(
            sysfs.root,
            camera.functions[0].control_interface,
        )

        observed = observe(
            sysfs.root,
            interface,
        )

        if observed.state is State.BOUND:
            outcome = set_bound(
                sysfs.root,
                interface,
                False,
            )

            return OperationResult(
                outcome=outcome,
                state=State.UNBOUND,
            )

        if observed.state is State.UNBOUND:
            outcome = set_bound(
                sysfs.root,
                interface,
                True,
            )

            return OperationResult(
                outcome=outcome,
                state=State.BOUND,
            )

        if observed.state is State.GONE:
            raise InterfaceGone(interface.name)

        if observed.state is State.OTHER:
            raise BoundToOtherDriver(interface.name)

        raise ValueError(
            f"Cannot toggle camera '{camera.id}' "
            f"from state '{observed.state.value}'."
        )
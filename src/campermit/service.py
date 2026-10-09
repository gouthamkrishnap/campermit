
import fcntl
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from .errors import (
    BoundToOtherDriver,
    CamPermitError,
    InterfaceGone,
    PermissionDenied,
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


@dataclass(frozen=True)
class BatchOperationResult:
    camera_id: str
    result: OperationResult | None = None
    error: CamPermitError | None = None


class OperationLock:
    def __init__(self, path: Path = LOCK_PATH):
        self.path = path
        self._file: IO[str] | None = None

    def __enter__(self) -> "OperationLock":
        try:
            self._file = self.path.open("a+")
            fcntl.flock(
                self._file.fileno(),
                fcntl.LOCK_EX,
            )
        except PermissionError as error:
            if self._file is not None:
                self._file.close()
                self._file = None

            raise PermissionDenied(
                f"cannot access operation lock '{self.path}': "
                f"{error.strerror}"
            ) from None
        except OSError as error:
            if self._file is not None:
                self._file.close()
                self._file = None

            raise CamPermitError(
                f"cannot acquire operation lock '{self.path}': "
                f"{error.strerror}"
            ) from None

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


def _validate_camera(camera: Camera) -> None:
    if len(camera.functions) != 1:
        raise ValueError(
            f"Camera '{camera.id}' must have exactly one UVC function."
        )


def _enable_locked(
    camera: Camera,
    *,
    sysfs: Sysfs,
) -> OperationResult:
    _validate_camera(camera)

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


def _disable_locked(
    camera: Camera,
    *,
    sysfs: Sysfs,
) -> OperationResult:
    _validate_camera(camera)

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


def _toggle_locked(
    camera: Camera,
    *,
    sysfs: Sysfs,
) -> OperationResult:
    _validate_camera(camera)

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


def enable(
    camera: Camera,
    *,
    sysfs: Sysfs,
    lock_path: Path = LOCK_PATH,
) -> OperationResult:
    _validate_camera(camera)

    with OperationLock(lock_path):
        return _enable_locked(
            camera,
            sysfs=sysfs,
        )


def disable(
    camera: Camera,
    *,
    sysfs: Sysfs,
    lock_path: Path = LOCK_PATH,
) -> OperationResult:
    _validate_camera(camera)

    with OperationLock(lock_path):
        return _disable_locked(
            camera,
            sysfs=sysfs,
        )


def toggle(
    camera: Camera,
    *,
    sysfs: Sysfs,
    lock_path: Path = LOCK_PATH,
) -> OperationResult:
    _validate_camera(camera)

    with OperationLock(lock_path):
        return _toggle_locked(
            camera,
            sysfs=sysfs,
        )


def enable_all(
    cameras: list[Camera],
    *,
    sysfs: Sysfs,
    lock_path: Path = LOCK_PATH,
) -> list[BatchOperationResult]:
    for camera in cameras:
        _validate_camera(camera)

    results = []

    with OperationLock(lock_path):
        for camera in cameras:
            try:
                result = _enable_locked(
                    camera,
                    sysfs=sysfs,
                )
            except CamPermitError as error:
                results.append(
                    BatchOperationResult(
                        camera_id=camera.id,
                        error=error,
                    )
                )
            else:
                results.append(
                    BatchOperationResult(
                        camera_id=camera.id,
                        result=result,
                    )
                )

    return results


def disable_all(
    cameras: list[Camera],
    *,
    sysfs: Sysfs,
    lock_path: Path = LOCK_PATH,
) -> list[BatchOperationResult]:
    for camera in cameras:
        _validate_camera(camera)

    results = []

    with OperationLock(lock_path):
        for camera in cameras:
            try:
                result = _disable_locked(
                    camera,
                    sysfs=sysfs,
                )
            except CamPermitError as error:
                results.append(
                    BatchOperationResult(
                        camera_id=camera.id,
                        error=error,
                    )
                )
            else:
                results.append(
                    BatchOperationResult(
                        camera_id=camera.id,
                        result=result,
                    )
                )

    return results

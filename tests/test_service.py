import fcntl
from pathlib import Path

import pytest

from campermit.errors import BoundToOtherDriver
from campermit.linux.uvc import Outcome
from campermit.models import Camera, UvcFunction
from campermit.service import (
    OperationLock,
    disable,
    enable,
    toggle,
)
from campermit.sysfs import Sysfs


def test_operation_lock_acquires_and_releases(
    tmp_path: Path,
    monkeypatch,
) -> None:
    lock_path = tmp_path / "campermit.lock"
    calls = []

    def fake_flock(fd: int, operation: int) -> None:
        calls.append((fd, operation))

    monkeypatch.setattr(fcntl, "flock", fake_flock)

    with OperationLock(lock_path):
        assert lock_path.exists()

    assert calls[0][1] == fcntl.LOCK_EX
    assert calls[1][1] == fcntl.LOCK_UN


def test_operation_lock_releases_on_exception(
    tmp_path: Path,
    monkeypatch,
) -> None:
    lock_path = tmp_path / "campermit.lock"
    calls = []

    def fake_flock(fd: int, operation: int) -> None:
        calls.append(operation)

    monkeypatch.setattr(fcntl, "flock", fake_flock)

    try:
        with OperationLock(lock_path):
            raise RuntimeError("test error")
    except RuntimeError:
        pass

    assert calls == [
        fcntl.LOCK_EX,
        fcntl.LOCK_UN,
    ]


def test_enable_binds_camera(
    tmp_path: Path,
    monkeypatch,
) -> None:
    camera = Camera(
        id="1",
        bus_path="3-6",
        vid="0408",
        pid="5482",
        functions=[
            UvcFunction(
                control_interface="3-6:1.0",
            ),
        ],
    )

    interface_path = (
        tmp_path
        / "bus"
        / "usb"
        / "devices"
        / "3-6:1.0"
    )

    interface_path.mkdir(parents=True)

    (interface_path / "bInterfaceClass").write_text("0e")
    (interface_path / "bInterfaceSubClass").write_text("01")

    calls = []

    def fake_set_bound(
        root: Path,
        interface,
        want_bound: bool,
    ) -> Outcome:
        calls.append(
            (
                root,
                interface.name,
                want_bound,
            )
        )
        return Outcome.CHANGED

    monkeypatch.setattr(
        "campermit.service.set_bound",
        fake_set_bound,
    )

    result = enable(
        camera,
        sysfs=Sysfs(tmp_path),
        lock_path=tmp_path / "campermit.lock",
    )

    assert result is Outcome.CHANGED

    assert calls == [
        (
            tmp_path,
            "3-6:1.0",
            True,
        )
    ]


def test_enable_rejects_camera_with_multiple_functions(
    tmp_path: Path,
) -> None:
    camera = Camera(
        id="1",
        bus_path="3-6",
        vid="0408",
        pid="5482",
        functions=[
            UvcFunction(control_interface="3-6:1.0"),
            UvcFunction(control_interface="3-6:1.1"),
        ],
    )

    with pytest.raises(ValueError):
        enable(
            camera,
            sysfs=Sysfs(tmp_path),
        )


def test_enable_already_bound_returns_already(
    tmp_path: Path,
) -> None:
    camera = Camera(
        id="1",
        bus_path="3-6",
        vid="0408",
        pid="5482",
        functions=[
            UvcFunction(
                control_interface="3-6:1.0",
            ),
        ],
    )

    interface_path = (
        tmp_path
        / "bus"
        / "usb"
        / "devices"
        / "3-6:1.0"
    )

    interface_path.mkdir(parents=True)

    (interface_path / "bInterfaceClass").write_text("0e")
    (interface_path / "bInterfaceSubClass").write_text("01")

    driver_path = (
        tmp_path
        / "bus"
        / "usb"
        / "drivers"
        / "uvcvideo"
    )

    driver_path.mkdir(parents=True)
    (interface_path / "driver").symlink_to(driver_path)

    result = enable(
        camera,
        sysfs=Sysfs(tmp_path),
        lock_path=tmp_path / "campermit.lock",
    )

    assert result is Outcome.ALREADY


def test_disable_unbinds_camera(
    tmp_path: Path,
    monkeypatch,
) -> None:
    camera = Camera(
        id="1",
        bus_path="3-6",
        vid="0408",
        pid="5482",
        functions=[
            UvcFunction(
                control_interface="3-6:1.0",
            ),
        ],
    )

    interface_path = (
        tmp_path
        / "bus"
        / "usb"
        / "devices"
        / "3-6:1.0"
    )

    interface_path.mkdir(parents=True)

    (interface_path / "bInterfaceClass").write_text("0e")
    (interface_path / "bInterfaceSubClass").write_text("01")

    calls = []

    def fake_set_bound(
        root: Path,
        interface,
        want_bound: bool,
    ) -> Outcome:
        calls.append(
            (
                root,
                interface.name,
                want_bound,
            )
        )
        return Outcome.CHANGED

    monkeypatch.setattr(
        "campermit.service.set_bound",
        fake_set_bound,
    )

    result = disable(
        camera,
        sysfs=Sysfs(tmp_path),
        lock_path=tmp_path / "campermit.lock",
    )

    assert result is Outcome.CHANGED

    assert calls == [
        (
            tmp_path,
            "3-6:1.0",
            False,
        )
    ]


def test_disable_rejects_camera_with_multiple_functions(
    tmp_path: Path,
) -> None:
    camera = Camera(
        id="1",
        bus_path="3-6",
        vid="0408",
        pid="5482",
        functions=[
            UvcFunction(control_interface="3-6:1.0"),
            UvcFunction(control_interface="3-6:1.1"),
        ],
    )

    with pytest.raises(ValueError):
        disable(
            camera,
            sysfs=Sysfs(tmp_path),
        )


def test_disable_already_unbound_returns_already(
    tmp_path: Path,
) -> None:
    camera = Camera(
        id="1",
        bus_path="3-6",
        vid="0408",
        pid="5482",
        functions=[
            UvcFunction(
                control_interface="3-6:1.0",
            ),
        ],
    )

    interface_path = (
        tmp_path
        / "bus"
        / "usb"
        / "devices"
        / "3-6:1.0"
    )

    interface_path.mkdir(parents=True)

    (interface_path / "bInterfaceClass").write_text("0e")
    (interface_path / "bInterfaceSubClass").write_text("01")

    result = disable(
        camera,
        sysfs=Sysfs(tmp_path),
        lock_path=tmp_path / "campermit.lock",
    )

    assert result is Outcome.ALREADY


def test_toggle_disables_bound_camera(
    tmp_path: Path,
    monkeypatch,
) -> None:
    camera = Camera(
        id="1",
        bus_path="3-6",
        vid="0408",
        pid="5482",
        functions=[
            UvcFunction(control_interface="3-6:1.0"),
        ],
    )

    interface_path = (
        tmp_path
        / "bus"
        / "usb"
        / "devices"
        / "3-6:1.0"
    )

    interface_path.mkdir(parents=True)
    (interface_path / "bInterfaceClass").write_text("0e")
    (interface_path / "bInterfaceSubClass").write_text("01")

    driver_path = (
        tmp_path
        / "bus"
        / "usb"
        / "drivers"
        / "uvcvideo"
    )

    driver_path.mkdir(parents=True)
    (interface_path / "driver").symlink_to(driver_path)

    calls = []

    def fake_set_bound(
        root: Path,
        interface,
        want_bound: bool,
    ) -> Outcome:
        calls.append(want_bound)
        return Outcome.CHANGED

    monkeypatch.setattr(
        "campermit.service.set_bound",
        fake_set_bound,
    )

    result = toggle(
        camera,
        sysfs=Sysfs(tmp_path),
        lock_path=tmp_path / "campermit.lock",
    )

    assert result is Outcome.CHANGED
    assert calls == [False]


def test_toggle_enables_unbound_camera(
    tmp_path: Path,
    monkeypatch,
) -> None:
    camera = Camera(
        id="1",
        bus_path="3-6",
        vid="0408",
        pid="5482",
        functions=[
            UvcFunction(control_interface="3-6:1.0"),
        ],
    )

    interface_path = (
        tmp_path
        / "bus"
        / "usb"
        / "devices"
        / "3-6:1.0"
    )

    interface_path.mkdir(parents=True)
    (interface_path / "bInterfaceClass").write_text("0e")
    (interface_path / "bInterfaceSubClass").write_text("01")

    calls = []

    def fake_set_bound(
        root: Path,
        interface,
        want_bound: bool,
    ) -> Outcome:
        calls.append(want_bound)
        return Outcome.CHANGED

    monkeypatch.setattr(
        "campermit.service.set_bound",
        fake_set_bound,
    )

    result = toggle(
        camera,
        sysfs=Sysfs(tmp_path),
        lock_path=tmp_path / "campermit.lock",
    )

    assert result is Outcome.CHANGED
    assert calls == [True]


def test_toggle_rejects_other_driver(
    tmp_path: Path,
) -> None:
    camera = Camera(
        id="1",
        bus_path="3-6",
        vid="0408",
        pid="5482",
        functions=[
            UvcFunction(control_interface="3-6:1.0"),
        ],
    )

    interface_path = (
        tmp_path
        / "bus"
        / "usb"
        / "devices"
        / "3-6:1.0"
    )

    interface_path.mkdir(parents=True)
    (interface_path / "bInterfaceClass").write_text("0e")
    (interface_path / "bInterfaceSubClass").write_text("01")

    driver_path = (
        tmp_path
        / "bus"
        / "usb"
        / "drivers"
        / "otherdriver"
    )

    driver_path.mkdir(parents=True)
    (interface_path / "driver").symlink_to(driver_path)

    with pytest.raises(BoundToOtherDriver):
        toggle(
            camera,
            sysfs=Sysfs(tmp_path),
            lock_path=tmp_path / "campermit.lock",
        )
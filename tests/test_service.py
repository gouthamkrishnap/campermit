import fcntl
from pathlib import Path

import pytest

from campermit.errors import (
    BoundToOtherDriver,
    InterfaceGone,
)
from campermit.linux.uvc import Outcome, State
from campermit.models import Camera, UvcFunction
from campermit.service import (
    OperationLock,
    disable,
    disable_all,
    enable,
    enable_all,
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

    assert result.outcome is Outcome.CHANGED
    assert result.state is State.BOUND

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

    assert result.outcome is Outcome.ALREADY
    assert result.state is State.BOUND


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

    assert result.outcome is Outcome.CHANGED
    assert result.state is State.UNBOUND

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

    assert result.outcome is Outcome.ALREADY
    assert result.state is State.UNBOUND


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

    assert result.outcome is Outcome.CHANGED
    assert result.state is State.UNBOUND
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

    assert result.outcome is Outcome.CHANGED
    assert result.state is State.BOUND
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


def test_enable_all_binds_all_cameras(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cameras = [
        Camera(
            id="1",
            bus_path="3-6",
            vid="0408",
            pid="5482",
            functions=[
                UvcFunction(control_interface="3-6:1.0"),
            ],
        ),
        Camera(
            id="2",
            bus_path="4-2",
            vid="1234",
            pid="5678",
            functions=[
                UvcFunction(control_interface="4-2:1.0"),
            ],
        ),
    ]

    for interface in ("3-6:1.0", "4-2:1.0"):
        interface_path = (
            tmp_path
            / "bus"
            / "usb"
            / "devices"
            / interface
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

    results = enable_all(
        cameras,
        sysfs=Sysfs(tmp_path),
        lock_path=tmp_path / "campermit.lock",
    )

    assert [
        result.result.outcome
        for result in results
        if result.result is not None
    ] == [
        Outcome.CHANGED,
        Outcome.CHANGED,
    ]

    assert all(result.error is None for result in results)

    assert calls == [
        (tmp_path, "3-6:1.0", True),
        (tmp_path, "4-2:1.0", True),
    ]


def test_disable_all_unbinds_all_cameras(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cameras = [
        Camera(
            id="1",
            bus_path="3-6",
            vid="0408",
            pid="5482",
            functions=[
                UvcFunction(control_interface="3-6:1.0"),
            ],
        ),
        Camera(
            id="2",
            bus_path="4-2",
            vid="1234",
            pid="5678",
            functions=[
                UvcFunction(control_interface="4-2:1.0"),
            ],
        ),
    ]

    for interface in ("3-6:1.0", "4-2:1.0"):
        interface_path = (
            tmp_path
            / "bus"
            / "usb"
            / "devices"
            / interface
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

    results = disable_all(
        cameras,
        sysfs=Sysfs(tmp_path),
        lock_path=tmp_path / "campermit.lock",
    )

    assert [
        result.result.outcome
        for result in results
        if result.result is not None
    ] == [
        Outcome.CHANGED,
        Outcome.CHANGED,
    ]

    assert all(result.error is None for result in results)

    assert calls == [
        (tmp_path, "3-6:1.0", False),
        (tmp_path, "4-2:1.0", False),
    ]


def test_enable_all_preserves_already_enabled_result(
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
        / "uvcvideo"
    )

    driver_path.mkdir(parents=True)
    (interface_path / "driver").symlink_to(driver_path)

    results = enable_all(
        [camera],
        sysfs=Sysfs(tmp_path),
        lock_path=tmp_path / "campermit.lock",
    )

    assert results[0].result is not None
    assert results[0].result.outcome is Outcome.ALREADY
    assert results[0].result.state is State.BOUND
    assert results[0].error is None


def test_disable_all_preserves_already_disabled_result(
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

    results = disable_all(
        [camera],
        sysfs=Sysfs(tmp_path),
        lock_path=tmp_path / "campermit.lock",
    )

    assert results[0].result is not None
    assert results[0].result.outcome is Outcome.ALREADY
    assert results[0].result.state is State.UNBOUND
    assert results[0].error is None


def test_enable_all_continues_after_camera_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cameras = [
        Camera(
            id="1",
            bus_path="3-6",
            vid="0408",
            pid="5482",
            functions=[
                UvcFunction(control_interface="3-6:1.0"),
            ],
        ),
        Camera(
            id="2",
            bus_path="4-2",
            vid="1234",
            pid="5678",
            functions=[
                UvcFunction(control_interface="4-2:1.0"),
            ],
        ),
        Camera(
            id="3",
            bus_path="5-1",
            vid="abcd",
            pid="ef01",
            functions=[
                UvcFunction(control_interface="5-1:1.0"),
            ],
        ),
    ]

    for interface in ("3-6:1.0", "4-2:1.0", "5-1:1.0"):
        interface_path = (
            tmp_path
            / "bus"
            / "usb"
            / "devices"
            / interface
        )
        interface_path.mkdir(parents=True)
        (interface_path / "bInterfaceClass").write_text("0e")
        (interface_path / "bInterfaceSubClass").write_text("01")

    def fake_set_bound(
        root: Path,
        interface,
        want_bound: bool,
    ) -> Outcome:
        if interface.name == "4-2:1.0":
            raise InterfaceGone(interface.name)

        return Outcome.CHANGED

    monkeypatch.setattr(
        "campermit.service.set_bound",
        fake_set_bound,
    )

    results = enable_all(
        cameras,
        sysfs=Sysfs(tmp_path),
        lock_path=tmp_path / "campermit.lock",
    )

    assert results[0].result is not None
    assert results[0].result.outcome is Outcome.CHANGED

    assert results[1].result is None
    assert isinstance(results[1].error, InterfaceGone)

    assert results[2].result is not None
    assert results[2].result.outcome is Outcome.CHANGED


def test_enable_all_acquires_lock_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    cameras = [
        Camera(
            id="1",
            bus_path="3-6",
            vid="0408",
            pid="5482",
            functions=[
                UvcFunction(control_interface="3-6:1.0"),
            ],
        ),
        Camera(
            id="2",
            bus_path="4-2",
            vid="1234",
            pid="5678",
            functions=[
                UvcFunction(control_interface="4-2:1.0"),
            ],
        ),
    ]

    for interface in ("3-6:1.0", "4-2:1.0"):
        interface_path = (
            tmp_path
            / "bus"
            / "usb"
            / "devices"
            / interface
        )
        interface_path.mkdir(parents=True)
        (interface_path / "bInterfaceClass").write_text("0e")
        (interface_path / "bInterfaceSubClass").write_text("01")

    calls = []

    class FakeLock:
        def __init__(self, path: Path):
            calls.append(("init", path))

        def __enter__(self):
            calls.append(("enter",))
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            calls.append(("exit",))

    monkeypatch.setattr(
        "campermit.service.OperationLock",
        FakeLock,
    )

    monkeypatch.setattr(
        "campermit.service.set_bound",
        lambda root, interface, want_bound: Outcome.CHANGED,
    )

    enable_all(
        cameras,
        sysfs=Sysfs(tmp_path),
        lock_path=tmp_path / "campermit.lock",
    )

    assert calls == [
        ("init", tmp_path / "campermit.lock"),
        ("enter",),
        ("exit",),
    ]
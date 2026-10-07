import errno
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from campermit.errors import (
    BoundToOtherDriver,
    InterfaceGone,
    InvalidInterface,
    NotVideoControl,
    PermissionDenied,
    SysfsReadError,
    SysfsWriteError,
    VerificationFailed,
)
from campermit.linux.uvc import (
    Outcome,
    State,
    _write_sysfs,
    observe,
    parse_control_interface,
    set_bound,
)


def create_uvc_fixture(
    root: Path,
    *,
    bound: bool = True,
    driver: str = "uvcvideo",
) -> Path:
    interface = (
        root
        / "bus"
        / "usb"
        / "devices"
        / "3-6:1.0"
    )
    interface.mkdir(parents=True)

    (interface / "bInterfaceClass").write_text("0e\n")
    (interface / "bInterfaceSubClass").write_text("01\n")

    driver_root = (
        root
        / "bus"
        / "usb"
        / "drivers"
        / "uvcvideo"
    )
    driver_root.mkdir(parents=True)

    (driver_root / "bind").touch()
    (driver_root / "unbind").touch()

    if bound:
        target = (
            root
            / "bus"
            / "usb"
            / "drivers"
            / driver
        )

        target.mkdir(parents=True, exist_ok=True)

        (interface / "driver").symlink_to(target)

    return interface


def fake_writer_factory(
    root: Path,
) -> tuple[
    list[tuple[Path, str]],
    Callable[[Path, str], None],
]:
    writes = []

    def writer(path: Path, payload: str) -> None:
        writes.append((path, payload))

        interface = (
            root
            / "bus"
            / "usb"
            / "devices"
            / payload
        )

        driver = interface / "driver"

        if path.name == "unbind":
            driver.unlink()
        elif path.name == "bind":
            target = (
                root
                / "bus"
                / "usb"
                / "drivers"
                / "uvcvideo"
            )
            driver.symlink_to(target)

    return writes, writer


def test_parse_control_interface(tmp_path: Path) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    assert interface.name == "3-6:1.0"


def test_rejects_invalid_interface_name(tmp_path: Path) -> None:
    with pytest.raises(InvalidInterface):
        parse_control_interface(
            tmp_path,
            "../3-6:1.0",
        )


def test_rejects_non_video_control_interface(
    tmp_path: Path,
) -> None:
    interface = (
        tmp_path
        / "bus"
        / "usb"
        / "devices"
        / "3-6:1.1"
    )
    interface.mkdir(parents=True)

    (interface / "bInterfaceClass").write_text("0e\n")
    (interface / "bInterfaceSubClass").write_text("02\n")

    with pytest.raises(NotVideoControl):
        parse_control_interface(
            tmp_path,
            "3-6:1.1",
        )


def test_rejects_missing_interface(tmp_path: Path) -> None:
    with pytest.raises(InterfaceGone):
        parse_control_interface(
            tmp_path,
            "3-6:1.0",
        )


def test_observe_bound_interface(tmp_path: Path) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    observed = observe(tmp_path, interface)

    assert observed.state is State.BOUND
    assert observed.driver == "uvcvideo"


def test_observe_unbound_interface(tmp_path: Path) -> None:
    create_uvc_fixture(
        tmp_path,
        bound=False,
    )

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    observed = observe(tmp_path, interface)

    assert observed.state is State.UNBOUND
    assert observed.driver is None


def test_observe_other_driver(tmp_path: Path) -> None:
    create_uvc_fixture(
        tmp_path,
        driver="otherdriver",
    )

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    observed = observe(tmp_path, interface)

    assert observed.state is State.OTHER
    assert observed.driver == "otherdriver"


def test_set_bound_unbinds_interface(tmp_path: Path) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    writes, writer = fake_writer_factory(tmp_path)

    outcome = set_bound(
        tmp_path,
        interface,
        False,
        writer=writer,
    )

    assert outcome is Outcome.CHANGED
    assert observe(tmp_path, interface).state is State.UNBOUND
    assert writes == [
        (
            tmp_path
            / "bus"
            / "usb"
            / "drivers"
            / "uvcvideo"
            / "unbind",
            "3-6:1.0",
        )
    ]


def test_set_bound_binds_interface(tmp_path: Path) -> None:
    create_uvc_fixture(
        tmp_path,
        bound=False,
    )

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    writes, writer = fake_writer_factory(tmp_path)

    outcome = set_bound(
        tmp_path,
        interface,
        True,
        writer=writer,
    )

    assert outcome is Outcome.CHANGED
    assert observe(tmp_path, interface).state is State.BOUND
    assert writes == [
        (
            tmp_path
            / "bus"
            / "usb"
            / "drivers"
            / "uvcvideo"
            / "bind",
            "3-6:1.0",
        )
    ]


def test_set_bound_already_bound_does_not_write(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    writes, writer = fake_writer_factory(tmp_path)

    outcome = set_bound(
        tmp_path,
        interface,
        True,
        writer=writer,
    )

    assert outcome is Outcome.ALREADY
    assert writes == []


def test_set_unbound_already_unbound_does_not_write(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(
        tmp_path,
        bound=False,
    )

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    writes, writer = fake_writer_factory(tmp_path)

    outcome = set_bound(
        tmp_path,
        interface,
        False,
        writer=writer,
    )

    assert outcome is Outcome.ALREADY
    assert writes == []


def test_set_bound_rejects_other_driver(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(
        tmp_path,
        driver="otherdriver",
    )

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    writes, writer = fake_writer_factory(tmp_path)

    with pytest.raises(BoundToOtherDriver):
        set_bound(
            tmp_path,
            interface,
            False,
            writer=writer,
        )

    assert writes == []


def test_set_bound_rejects_missing_interface(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    shutil.rmtree(
        tmp_path
        / "bus"
        / "usb"
        / "devices"
        / "3-6:1.0",
    )

    writes, writer = fake_writer_factory(tmp_path)

    with pytest.raises(InterfaceGone):
        set_bound(
            tmp_path,
            interface,
            False,
            writer=writer,
        )

    assert writes == []


def test_set_bound_maps_permission_error(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    def writer(path: Path, payload: str) -> None:
        raise PermissionError(
            errno.EACCES,
            "Permission denied",
        )

    with pytest.raises(PermissionDenied):
        set_bound(
            tmp_path,
            interface,
            False,
            writer=writer,
        )


def test_set_bound_fails_when_state_does_not_change(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    def writer(path: Path, payload: str) -> None:
        pass

    with pytest.raises(VerificationFailed):
        set_bound(
            tmp_path,
            interface,
            False,
            writer=writer,
            timeout=0,
            interval=0,
        )


def test_set_bound_maps_enoent_to_write_error(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    def writer(path: Path, payload: str) -> None:
        raise OSError(
            errno.ENOENT,
            "No such file or directory",
        )

    with pytest.raises(SysfsWriteError) as error:
        set_bound(
            tmp_path,
            interface,
            False,
            writer=writer,
        )

    assert error.value.errno_value == errno.ENOENT


def test_set_bound_maps_enoent_to_interface_gone(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    def writer(path: Path, payload: str) -> None:
        shutil.rmtree(
            tmp_path
            / "bus"
            / "usb"
            / "devices"
            / "3-6:1.0",
        )

        raise OSError(
            errno.ENOENT,
            "No such file or directory",
        )

    with pytest.raises(InterfaceGone):
        set_bound(
            tmp_path,
            interface,
            False,
            writer=writer,
        )


def test_set_bound_maps_enodev(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    def writer(path: Path, payload: str) -> None:
        shutil.rmtree(
            tmp_path
            / "bus"
            / "usb"
            / "devices"
            / "3-6:1.0",
        )

        raise OSError(
            errno.ENODEV,
            "No such device",
        )

    with pytest.raises(InterfaceGone):
        set_bound(
            tmp_path,
            interface,
            False,
            writer=writer,
        )


def test_set_bound_maps_erofs(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    def writer(path: Path, payload: str) -> None:
        raise OSError(
            errno.EROFS,
            "Read-only file system",
        )

    with pytest.raises(PermissionDenied):
        set_bound(
            tmp_path,
            interface,
            False,
            writer=writer,
        )


def test_set_bound_maps_generic_write_error(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    def writer(path: Path, payload: str) -> None:
        raise OSError(
            errno.EIO,
            "I/O error",
        )

    with pytest.raises(SysfsWriteError) as error:
        set_bound(
            tmp_path,
            interface,
            False,
            writer=writer,
        )

    assert error.value.errno_value == errno.EIO


def test_set_bound_revalidates_control_interface(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    interface_path = (
        tmp_path
        / "bus"
        / "usb"
        / "devices"
        / "3-6:1.0"
    )

    (interface_path / "bInterfaceSubClass").write_text("02\n")

    writes, writer = fake_writer_factory(tmp_path)

    with pytest.raises(NotVideoControl):
        set_bound(
            tmp_path,
            interface,
            False,
            writer=writer,
        )

    assert writes == []


def test_set_bound_maps_ebusy_to_write_error(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    def writer(path: Path, payload: str) -> None:
        raise OSError(
            errno.EBUSY,
            "Device or resource busy",
        )

    with pytest.raises(SysfsWriteError) as error:
        set_bound(
            tmp_path,
            interface,
            False,
            writer=writer,
        )

    assert error.value.errno_value == errno.EBUSY


def test_set_bound_fails_if_interface_disappears_during_verification(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    def writer(path: Path, payload: str) -> None:
        shutil.rmtree(
            tmp_path
            / "bus"
            / "usb"
            / "devices"
            / "3-6:1.0",
        )

    with pytest.raises(VerificationFailed):
        set_bound(
            tmp_path,
            interface,
            False,
            writer=writer,
            timeout=0,
            interval=0,
        )


def test_write_sysfs_rejects_short_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "unbind"
    path.touch()

    monkeypatch.setattr(
        "campermit.linux.uvc.os.open",
        lambda path, flags: 123,
    )

    monkeypatch.setattr(
        "campermit.linux.uvc.os.write",
        lambda fd, data: 0,
    )

    monkeypatch.setattr(
        "campermit.linux.uvc.os.close",
        lambda fd: None,
    )

    with pytest.raises(OSError) as error:
        _write_sysfs(path, "3-6:1.0")

    assert error.value.errno == errno.EIO


def test_write_sysfs_propagates_open_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "unbind"

    def fail_open(path: Path, flags: int) -> int:
        raise OSError(
            errno.EACCES,
            "Permission denied",
        )

    monkeypatch.setattr(
        "campermit.linux.uvc.os.open",
        fail_open,
    )

    with pytest.raises(OSError) as error:
        _write_sysfs(path, "3-6:1.0")

    assert error.value.errno == errno.EACCES


def test_write_sysfs_propagates_write_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "unbind"
    path.touch()

    monkeypatch.setattr(
        "campermit.linux.uvc.os.open",
        lambda path, flags: 123,
    )

    def fail_write(fd: int, data: bytes) -> int:
        raise OSError(
            errno.EIO,
            "I/O error",
        )

    monkeypatch.setattr(
        "campermit.linux.uvc.os.write",
        fail_write,
    )

    monkeypatch.setattr(
        "campermit.linux.uvc.os.close",
        lambda fd: None,
    )

    with pytest.raises(OSError) as error:
        _write_sysfs(path, "3-6:1.0")

    assert error.value.errno == errno.EIO


def test_set_bound_times_out_deterministically(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    current_time = 0.0
    sleeps = []

    def writer(path: Path, payload: str) -> None:
        pass

    def clock() -> float:
        return current_time

    def sleep(seconds: float) -> None:
        nonlocal current_time
        sleeps.append(seconds)
        current_time += seconds

    with pytest.raises(VerificationFailed):
        set_bound(
            tmp_path,
            interface,
            False,
            writer=writer,
            clock=clock,
            sleep=sleep,
            timeout=0.2,
            interval=0.05,
        )

    assert sleeps
    assert current_time >= 0.2


def test_set_bound_fails_when_state_changes_to_wrong_driver(
    tmp_path: Path,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    def writer(path: Path, payload: str) -> None:
        driver = (
            tmp_path
            / "bus"
            / "usb"
            / "devices"
            / "3-6:1.0"
            / "driver"
        )

        driver.unlink()

        target = (
            tmp_path
            / "bus"
            / "usb"
            / "drivers"
            / "otherdriver"
        )
        target.mkdir(parents=True, exist_ok=True)

        driver.symlink_to(target)

    with pytest.raises(VerificationFailed):
        set_bound(
            tmp_path,
            interface,
            False,
            writer=writer,
            timeout=0,
            interval=0,
        )


def test_observe_maps_unexpected_read_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_uvc_fixture(tmp_path)

    interface = parse_control_interface(
        tmp_path,
        "3-6:1.0",
    )

    def fail_readlink(
        path: str | bytes | Path,
    ) -> str:
        raise OSError(errno.EIO, "I/O error")

    monkeypatch.setattr(
        "campermit.linux.uvc.os.readlink",
        fail_readlink,
    )

    with pytest.raises(SysfsReadError) as error:
        observe(tmp_path, interface)

    assert error.value.errno_value == errno.EIO


def test_parse_control_interface_maps_read_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_uvc_fixture(tmp_path)

    class_path = (
        tmp_path
        / "bus"
        / "usb"
        / "devices"
        / "3-6:1.0"
        / "bInterfaceClass"
    )

    original_read_text = Path.read_text

    def fail_read_text(
        self: Path,
        encoding: str | None = None,
        errors: str | None = None,
    ) -> str:
        if self == class_path:
            raise OSError(errno.EIO, "I/O error")

        return original_read_text(
            self,
            encoding=encoding,
            errors=errors,
        )

    monkeypatch.setattr(
        Path,
        "read_text",
        fail_read_text,
    )

    with pytest.raises(SysfsReadError) as error:
        parse_control_interface(
            tmp_path,
            "3-6:1.0",
        )

    assert error.value.errno_value == errno.EIO
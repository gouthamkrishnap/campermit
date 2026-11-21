import pytest
from fakesys import add_device, add_interface, unbind

from campermit import cli, persist, uvc
from campermit.cli import main
from campermit.elevate import ask_for_root


@pytest.fixture
def writes(monkeypatch):
    recorded = []
    monkeypatch.setattr(
        uvc, "write", lambda path, text: recorded.append((path.name, text))
    )
    return recorded


def asker(code=0):
    calls = []

    def ask(args):
        calls.append(args)
        return code

    return calls, ask


def add_second_camera(sysfs):
    add_device(sysfs, "1-2", "046d", "0825", "Logitech", "Webcam C270")
    add_interface(sysfs, "1-2:1.0", "0e", "01", "uvcvideo", nodes=("video2",))
    add_interface(sysfs, "1-2:1.1", "0e", "02", "uvcvideo")


def test_disabling_an_enabled_camera_asks_for_root(sysfs, writes, tmp_path):
    calls, ask = asker(code=7)

    exit_code = main(
        ["disable", "3-6"],
        root=sysfs,
        disabled_file=tmp_path / "disabled",
        elevate=ask,
    )

    assert exit_code == 7
    assert calls == [["disable", "3-6:1.0"]]
    assert writes == []


def test_enabling_a_disabled_camera_asks_for_root(sysfs, writes, tmp_path):
    unbind(sysfs, "3-6:1.0")
    calls, ask = asker()

    main(
        ["enable", "3-6"],
        root=sysfs,
        disabled_file=tmp_path / "disabled",
        elevate=ask,
    )

    assert calls == [["enable", "3-6:1.0"]]
    assert writes == []


def test_a_camera_that_is_already_disabled_does_not_ask(
    sysfs, writes, tmp_path, capsys
):
    unbind(sysfs, "3-6:1.0")
    calls, ask = asker()

    exit_code = main(
        ["disable", "3-6"],
        root=sysfs,
        disabled_file=tmp_path / "disabled",
        elevate=ask,
    )

    assert exit_code == 0
    assert calls == []
    assert writes == []
    assert "3-6:1.0 is already disabled" in capsys.readouterr().out


def test_a_camera_that_is_already_enabled_does_not_ask(sysfs, writes, tmp_path, capsys):
    calls, ask = asker()

    exit_code = main(
        ["enable", "3-6"],
        root=sysfs,
        disabled_file=tmp_path / "disabled",
        elevate=ask,
    )

    assert exit_code == 0
    assert calls == []
    assert "3-6:1.0 is already enabled" in capsys.readouterr().out


def test_enabling_asks_when_the_camera_is_still_on_the_list(sysfs, writes, tmp_path):
    listing = tmp_path / "disabled"
    listing.write_text("3-6:1.0\n")
    calls, ask = asker()

    main(["enable", "3-6"], root=sysfs, disabled_file=listing, elevate=ask)

    assert calls == [["enable", "3-6:1.0"]]


def test_enabling_asks_when_the_list_cannot_be_read(
    sysfs, writes, tmp_path, monkeypatch
):
    def unreadable(path):
        raise PermissionError("no")

    monkeypatch.setattr(persist, "load", unreadable)
    calls, ask = asker()

    main(
        ["enable", "3-6"],
        root=sysfs,
        disabled_file=tmp_path / "disabled",
        elevate=ask,
    )

    assert calls == [["enable", "3-6:1.0"]]


def test_persist_asks_even_when_the_camera_is_already_disabled(sysfs, writes, tmp_path):
    unbind(sysfs, "3-6:1.0")
    calls, ask = asker()

    main(
        ["disable", "3-6", "--persist"],
        root=sysfs,
        disabled_file=tmp_path / "disabled",
        elevate=ask,
    )

    assert calls == [["disable", "3-6:1.0", "--persist"]]


def test_toggle_asks_for_the_action_it_needs(sysfs, writes, tmp_path):
    listing = tmp_path / "disabled"
    calls, ask = asker()

    main(["toggle", "3-6"], root=sysfs, disabled_file=listing, elevate=ask)
    unbind(sysfs, "3-6:1.0")
    main(["toggle", "3-6"], root=sysfs, disabled_file=listing, elevate=ask)

    assert calls == [["disable", "3-6:1.0"], ["enable", "3-6:1.0"]]


def test_a_name_is_turned_into_the_exact_id_before_asking(sysfs, writes, tmp_path):
    calls, ask = asker()

    main(
        ["disable", "Wide Vision"],
        root=sysfs,
        disabled_file=tmp_path / "disabled",
        elevate=ask,
    )

    assert calls == [["disable", "3-6:1.0"]]


def test_disable_all_asks_once_for_all_cameras(sysfs, writes, tmp_path):
    add_second_camera(sysfs)
    calls, ask = asker()

    main(
        ["disable", "--all", "--persist"],
        root=sysfs,
        disabled_file=tmp_path / "disabled",
        elevate=ask,
    )

    assert calls == [["disable", "--all", "--persist"]]
    assert writes == []


def test_disable_all_does_not_ask_when_every_camera_is_off(sysfs, writes, tmp_path):
    add_second_camera(sysfs)
    unbind(sysfs, "3-6:1.0")
    unbind(sysfs, "1-2:1.0")
    calls, ask = asker()

    exit_code = main(
        ["disable", "--all"],
        root=sysfs,
        disabled_file=tmp_path / "disabled",
        elevate=ask,
    )

    assert exit_code == 0
    assert calls == []


def test_a_camera_used_by_another_driver_is_refused_without_asking(
    sysfs, writes, tmp_path, capsys
):
    link = sysfs / "bus/usb/devices/3-6:1.0/driver"
    link.unlink()
    other = sysfs / "bus/usb/drivers/vfio-pci"
    other.mkdir(parents=True)
    link.symlink_to(other)
    calls, ask = asker()

    exit_code = main(
        ["toggle", "3-6:1.0"],
        root=sysfs,
        disabled_file=tmp_path / "disabled",
        elevate=ask,
    )

    assert exit_code == 1
    assert calls == []
    assert "vfio-pci" in capsys.readouterr().err


def test_an_unknown_camera_is_reported_once_and_does_not_ask(sysfs, tmp_path, capsys):
    calls, ask = asker()

    exit_code = main(
        ["disable", "nonexistent"],
        root=sysfs,
        disabled_file=tmp_path / "disabled",
        elevate=ask,
    )

    assert exit_code == 1
    assert calls == []
    assert capsys.readouterr().err.count("no camera named") == 1


def test_without_an_elevator_the_camera_is_changed_directly(sysfs, tmp_path):
    exit_code = main(
        ["disable", "3-6"], root=sysfs, disabled_file=tmp_path / "disabled"
    )

    assert exit_code == 0
    assert (sysfs / "bus/usb/drivers/uvcvideo/unbind").read_text() == "3-6:1.0\n"


def test_a_normal_user_gets_the_elevator(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli.os, "geteuid", lambda: 1000)
    monkeypatch.setattr(cli, "main", lambda **kwargs: seen.update(kwargs) or 0)

    assert cli.run() == 0
    assert seen["elevate"] is ask_for_root


def test_root_gets_no_elevator(monkeypatch):
    seen = {}
    monkeypatch.setattr(cli.os, "geteuid", lambda: 0)
    monkeypatch.setattr(cli, "main", lambda **kwargs: seen.update(kwargs) or 0)

    assert cli.run() == 0
    assert seen["elevate"] is None

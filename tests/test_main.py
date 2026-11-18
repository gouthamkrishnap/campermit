import errno
import os
import shutil

import pytest
from fakesys import add_device, add_interface, unbind

from campermit import uvc
from campermit.__main__ import main


def test_version_flag_prints_the_version(capsys):
    exit_code = main(["--version"])

    assert exit_code == 0
    assert capsys.readouterr().out.startswith("campermit ")


def test_help_lists_the_commands(capsys):
    exit_code = main(["--help"])

    output = capsys.readouterr().out
    assert exit_code == 0
    for command in ("list", "enable", "disable"):
        assert command in output


def test_no_command_is_a_usage_error(capsys):
    exit_code = main([])

    assert exit_code == 2
    assert "usage" in capsys.readouterr().err.lower()


def test_disable_without_an_id_is_a_usage_error(capsys):
    exit_code = main(["disable"])

    assert exit_code == 2
    assert "usage" in capsys.readouterr().err.lower()


def test_unknown_command_is_a_usage_error(capsys):
    exit_code = main(["frobnicate"])

    assert exit_code == 2
    assert "usage" in capsys.readouterr().err.lower()


def test_list_shows_an_enabled_camera(sysfs, capsys):
    exit_code = main(["list"], root=sysfs)
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "3-6:1.0" in output
    assert "HP Wide Vision HD Camera" in output
    assert "enabled" in output
    assert "/dev/video0" in output


def test_list_shows_a_disabled_camera(sysfs, capsys):
    unbind(sysfs, "3-6:1.0")

    main(["list"], root=sysfs)

    assert "disabled" in capsys.readouterr().out


def test_list_shows_a_camera_used_by_another_driver(sysfs, capsys):
    link = sysfs / "bus/usb/devices/3-6:1.0/driver"
    link.unlink()
    other = sysfs / "bus/usb/drivers/vfio-pci"
    other.mkdir(parents=True)
    link.symlink_to(other)

    main(["list"], root=sysfs)

    assert "vfio-pci" in capsys.readouterr().out


def test_list_with_no_cameras_says_so(tmp_path, capsys):
    exit_code = main(["list"], root=tmp_path)

    assert exit_code == 0
    assert "No USB cameras found" in capsys.readouterr().out


def test_disable_unbinds_the_camera(sysfs):
    exit_code = main(["disable", "3-6:1.0"], root=sysfs)

    assert exit_code == 0
    unbind = sysfs / "bus/usb/drivers/uvcvideo/unbind"
    assert unbind.read_text() == "3-6:1.0\n"


def test_disable_unknown_camera_fails_and_writes_nothing(sysfs, capsys):
    exit_code = main(["disable", "9-9:1.0"], root=sysfs)

    assert exit_code == 1
    assert "9-9:1.0" in capsys.readouterr().err
    assert (sysfs / "bus/usb/drivers/uvcvideo/unbind").read_text() == ""


def test_disable_an_already_disabled_camera_writes_nothing(sysfs, capsys):
    unbind(sysfs, "3-6:1.0")

    exit_code = main(["disable", "3-6:1.0"], root=sysfs)

    assert exit_code == 0
    assert "already disabled" in capsys.readouterr().out
    assert (sysfs / "bus/usb/drivers/uvcvideo/unbind").read_text() == ""


def test_disable_refuses_a_camera_used_by_another_driver(sysfs, capsys):
    link = sysfs / "bus/usb/devices/3-6:1.0/driver"
    link.unlink()
    other = sysfs / "bus/usb/drivers/vfio-pci"
    other.mkdir(parents=True)
    link.symlink_to(other)

    exit_code = main(["disable", "3-6:1.0"], root=sysfs)

    assert exit_code == 1
    assert "vfio-pci" in capsys.readouterr().err
    assert (sysfs / "bus/usb/drivers/uvcvideo/unbind").read_text() == ""


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anywhere")
def test_disable_without_permission_suggests_sudo(sysfs, capsys):
    (sysfs / "bus/usb/drivers/uvcvideo/unbind").chmod(0o444)

    exit_code = main(["disable", "3-6:1.0"], root=sysfs)

    assert exit_code == 1
    assert "sudo" in capsys.readouterr().err


def test_disable_treats_a_vanished_camera_as_done(sysfs, capsys, monkeypatch):
    def vanished(path, text):
        raise OSError(errno.ENODEV, "No such device")

    monkeypatch.setattr(uvc, "write", vanished)

    exit_code = main(["disable", "3-6:1.0"], root=sysfs)

    assert exit_code == 0
    assert "already disabled" in capsys.readouterr().out


def test_disable_reports_any_other_write_error(sysfs, capsys, monkeypatch):
    def broken(path, text):
        raise OSError(errno.EIO, "Input/output error")

    monkeypatch.setattr(uvc, "write", broken)

    exit_code = main(["disable", "3-6:1.0"], root=sysfs)

    assert exit_code == 1
    assert "Input/output error" in capsys.readouterr().err


def test_enable_binds_the_camera(sysfs):
    unbind(sysfs, "3-6:1.0")

    exit_code = main(["enable", "3-6:1.0"], root=sysfs)

    assert exit_code == 0
    bind_file = sysfs / "bus/usb/drivers/uvcvideo/bind"
    assert bind_file.read_text() == "3-6:1.0\n"


def test_enable_unknown_camera_fails_and_writes_nothing(sysfs, capsys):
    exit_code = main(["enable", "9-9:1.0"], root=sysfs)

    assert exit_code == 1
    assert "9-9:1.0" in capsys.readouterr().err
    assert (sysfs / "bus/usb/drivers/uvcvideo/bind").read_text() == ""


def test_enable_an_already_enabled_camera_writes_nothing(sysfs, capsys):
    exit_code = main(["enable", "3-6:1.0"], root=sysfs)

    assert exit_code == 0
    assert "already enabled" in capsys.readouterr().out
    assert (sysfs / "bus/usb/drivers/uvcvideo/bind").read_text() == ""


def test_enable_refuses_a_camera_used_by_another_driver(sysfs, capsys):
    link = sysfs / "bus/usb/devices/3-6:1.0/driver"
    link.unlink()
    other = sysfs / "bus/usb/drivers/vfio-pci"
    other.mkdir(parents=True)
    link.symlink_to(other)

    exit_code = main(["enable", "3-6:1.0"], root=sysfs)

    assert exit_code == 1
    assert "vfio-pci" in capsys.readouterr().err
    assert (sysfs / "bus/usb/drivers/uvcvideo/bind").read_text() == ""


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anywhere")
def test_enable_without_permission_suggests_sudo(sysfs, capsys):
    unbind(sysfs, "3-6:1.0")
    (sysfs / "bus/usb/drivers/uvcvideo/bind").chmod(0o444)

    exit_code = main(["enable", "3-6:1.0"], root=sysfs)

    assert exit_code == 1
    assert "sudo" in capsys.readouterr().err


def test_enable_treats_busy_as_already_enabled(sysfs, capsys, monkeypatch):
    unbind(sysfs, "3-6:1.0")

    def already_bound(path, text):
        raise OSError(errno.EBUSY, "Device or resource busy")

    monkeypatch.setattr(uvc, "write", already_bound)

    exit_code = main(["enable", "3-6:1.0"], root=sysfs)

    assert exit_code == 0
    assert "already enabled" in capsys.readouterr().out


def test_enable_reports_any_other_write_error(sysfs, capsys, monkeypatch):
    unbind(sysfs, "3-6:1.0")

    def broken(path, text):
        raise OSError(errno.EIO, "Input/output error")

    monkeypatch.setattr(uvc, "write", broken)

    exit_code = main(["enable", "3-6:1.0"], root=sysfs)

    assert exit_code == 1
    assert "Input/output error" in capsys.readouterr().err


def add_dual_camera(sysfs):
    add_device(sysfs, "2-1", "0bda", "5830", "Realtek", "Dual Camera")
    add_interface(sysfs, "2-1:1.0", "0e", "01", "uvcvideo", nodes=("video4",))
    add_interface(sysfs, "2-1:1.1", "0e", "02", "uvcvideo")
    add_interface(sysfs, "2-1:1.2", "0e", "01", "uvcvideo", nodes=("video6",))
    add_interface(sysfs, "2-1:1.3", "0e", "02", "uvcvideo")


def test_disable_accepts_the_usb_device_name(sysfs):
    exit_code = main(["disable", "3-6"], root=sysfs)

    assert exit_code == 0
    unbind_file = sysfs / "bus/usb/drivers/uvcvideo/unbind"
    assert unbind_file.read_text() == "3-6:1.0\n"


def test_enable_accepts_the_usb_device_name(sysfs):
    unbind(sysfs, "3-6:1.0")

    exit_code = main(["enable", "3-6"], root=sysfs)

    assert exit_code == 0
    bind_file = sysfs / "bus/usb/drivers/uvcvideo/bind"
    assert bind_file.read_text() == "3-6:1.0\n"


def test_device_name_with_two_cameras_is_ambiguous(sysfs, capsys):
    add_dual_camera(sysfs)

    exit_code = main(["disable", "2-1"], root=sysfs)

    error = capsys.readouterr().err
    assert exit_code == 1
    assert "2-1:1.0" in error
    assert "2-1:1.2" in error
    assert (sysfs / "bus/usb/drivers/uvcvideo/unbind").read_text() == ""


def test_exact_id_works_even_when_the_device_has_two_cameras(sysfs):
    add_dual_camera(sysfs)

    exit_code = main(["disable", "2-1:1.2"], root=sysfs)

    assert exit_code == 0
    unbind_file = sysfs / "bus/usb/drivers/uvcvideo/unbind"
    assert unbind_file.read_text() == "2-1:1.2\n"


def test_unknown_device_name_fails(sysfs, capsys):
    exit_code = main(["disable", "9-9"], root=sysfs)

    assert exit_code == 1
    assert "9-9" in capsys.readouterr().err


def test_enable_says_so_when_the_driver_is_not_loaded(sysfs, capsys):
    unbind(sysfs, "3-6:1.0")
    shutil.rmtree(sysfs / "bus/usb/drivers/uvcvideo")

    exit_code = main(["enable", "3-6:1.0"], root=sysfs)

    assert exit_code == 1
    assert "modprobe uvcvideo" in capsys.readouterr().err


def test_disable_says_so_when_the_camera_vanished(sysfs, capsys, monkeypatch):
    def vanished(path, text):
        raise FileNotFoundError(errno.ENOENT, "No such file or directory")

    monkeypatch.setattr(uvc, "write", vanished)

    exit_code = main(["disable", "3-6:1.0"], root=sysfs)

    assert exit_code == 1
    assert "no longer connected" in capsys.readouterr().err


def test_toggle_disables_an_enabled_camera(sysfs, capsys):
    exit_code = main(["toggle", "3-6:1.0"], root=sysfs)

    assert exit_code == 0
    assert "Disabled" in capsys.readouterr().out
    assert (sysfs / "bus/usb/drivers/uvcvideo/unbind").read_text() == "3-6:1.0\n"
    assert (sysfs / "bus/usb/drivers/uvcvideo/bind").read_text() == ""


def test_toggle_enables_a_disabled_camera(sysfs, capsys):
    unbind(sysfs, "3-6:1.0")

    exit_code = main(["toggle", "3-6:1.0"], root=sysfs)

    assert exit_code == 0
    assert "Enabled" in capsys.readouterr().out
    assert (sysfs / "bus/usb/drivers/uvcvideo/bind").read_text() == "3-6:1.0\n"
    assert (sysfs / "bus/usb/drivers/uvcvideo/unbind").read_text() == ""


def test_toggle_refuses_a_camera_used_by_another_driver(sysfs, capsys):
    link = sysfs / "bus/usb/devices/3-6:1.0/driver"
    link.unlink()
    other = sysfs / "bus/usb/drivers/vfio-pci"
    other.mkdir(parents=True)
    link.symlink_to(other)

    exit_code = main(["toggle", "3-6:1.0"], root=sysfs)

    assert exit_code == 1
    assert "vfio-pci" in capsys.readouterr().err
    assert (sysfs / "bus/usb/drivers/uvcvideo/bind").read_text() == ""
    assert (sysfs / "bus/usb/drivers/uvcvideo/unbind").read_text() == ""


def test_toggle_unknown_camera_fails(sysfs, capsys):
    exit_code = main(["toggle", "9-9:1.0"], root=sysfs)

    assert exit_code == 1
    assert "9-9:1.0" in capsys.readouterr().err


def test_toggle_without_an_id_is_a_usage_error(capsys):
    exit_code = main(["toggle"], root=None)

    assert exit_code == 2
    assert "usage" in capsys.readouterr().err.lower()


def add_second_camera(sysfs):
    add_device(sysfs, "1-2", "046d", "0825", "Logitech", "Webcam C270")
    add_interface(sysfs, "1-2:1.0", "0e", "01", "uvcvideo", nodes=("video2",))
    add_interface(sysfs, "1-2:1.1", "0e", "02", "uvcvideo")


@pytest.fixture
def writes(monkeypatch):
    recorded = []
    monkeypatch.setattr(
        uvc, "write", lambda path, text: recorded.append((path.name, text))
    )
    return recorded


def test_disable_all_disables_every_camera(sysfs, writes, capsys):
    add_second_camera(sysfs)

    exit_code = main(["disable", "--all"], root=sysfs)

    assert exit_code == 0
    assert writes == [("unbind", "1-2:1.0"), ("unbind", "3-6:1.0")]
    output = capsys.readouterr().out
    assert "Disabled 1-2:1.0" in output
    assert "Disabled 3-6:1.0" in output


def test_enable_all_leaves_enabled_cameras_alone(sysfs, writes, capsys):
    add_second_camera(sysfs)
    unbind(sysfs, "1-2:1.0")

    exit_code = main(["enable", "--all"], root=sysfs)

    assert exit_code == 0
    assert writes == [("bind", "1-2:1.0")]
    assert "3-6:1.0 is already enabled" in capsys.readouterr().out


def test_all_carries_on_after_a_failure(sysfs, writes, capsys):
    add_second_camera(sysfs)
    link = sysfs / "bus/usb/devices/1-2:1.0/driver"
    link.unlink()
    other = sysfs / "bus/usb/drivers/vfio-pci"
    other.mkdir(parents=True)
    link.symlink_to(other)

    exit_code = main(["disable", "--all"], root=sysfs)

    assert exit_code == 1
    assert writes == [("unbind", "3-6:1.0")]
    assert "vfio-pci" in capsys.readouterr().err


def test_all_with_no_cameras_says_so(tmp_path, capsys):
    exit_code = main(["disable", "--all"], root=tmp_path)

    assert exit_code == 0
    assert "No USB cameras found" in capsys.readouterr().out


def test_an_id_and_all_together_is_a_usage_error(capsys):
    exit_code = main(["disable", "3-6", "--all"], root=None)

    assert exit_code == 2


def test_toggle_has_no_all_option(capsys):
    exit_code = main(["toggle", "--all"], root=None)

    assert exit_code == 2

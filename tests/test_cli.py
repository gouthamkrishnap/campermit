import errno
import json
import os
import shutil

import pytest
from fakesys import add_device, add_interface, unbind

from campermit import persist, uvc
from campermit.cli import main


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


def test_help_says_status_can_name_a_driver(capsys):
    main(["--help"])

    assert "which driver" in capsys.readouterr().out


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


def test_toggle_without_an_id_is_a_usage_error(tmp_path, capsys):
    exit_code = main(["toggle"], root=tmp_path)

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


def test_an_id_and_all_together_is_a_usage_error(tmp_path, capsys):
    exit_code = main(["disable", "3-6", "--all"], root=tmp_path)

    assert exit_code == 2


def test_toggle_has_no_all_option(tmp_path, capsys):
    exit_code = main(["toggle", "--all"], root=tmp_path)

    assert exit_code == 2


def test_disable_accepts_a_vendor_and_product_id(sysfs):
    exit_code = main(["disable", "0408:5482"], root=sysfs)

    assert exit_code == 0
    unbind_file = sysfs / "bus/usb/drivers/uvcvideo/unbind"
    assert unbind_file.read_text() == "3-6:1.0\n"


def test_status_of_an_enabled_camera(sysfs, capsys):
    exit_code = main(["status", "3-6"], root=sysfs)

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "enabled"


def test_status_of_a_disabled_camera(sysfs, capsys):
    unbind(sysfs, "3-6:1.0")

    exit_code = main(["status", "3-6"], root=sysfs)

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "disabled"


def test_status_of_a_camera_used_by_another_driver(sysfs, capsys):
    link = sysfs / "bus/usb/devices/3-6:1.0/driver"
    link.unlink()
    other = sysfs / "bus/usb/drivers/vfio-pci"
    other.mkdir(parents=True)
    link.symlink_to(other)

    exit_code = main(["status", "3-6"], root=sysfs)

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "used by vfio-pci"


def test_status_of_an_unknown_camera_fails(sysfs, capsys):
    exit_code = main(["status", "9-9"], root=sysfs)

    assert exit_code == 1
    assert "9-9" in capsys.readouterr().err


def test_status_of_an_ambiguous_name_fails(sysfs, capsys):
    add_dual_camera(sysfs)

    exit_code = main(["status", "2-1"], root=sysfs)

    error = capsys.readouterr().err
    assert exit_code == 1
    assert "2-1:1.0" in error
    assert "2-1:1.2" in error


def test_status_without_an_id_is_a_usage_error(tmp_path, capsys):
    exit_code = main(["status"], root=tmp_path)

    assert exit_code == 2


def test_list_starts_with_a_header_row(sysfs, capsys):
    main(["list"], root=sysfs)

    header = capsys.readouterr().out.splitlines()[0]
    assert header.startswith("ID")
    assert "NAME" in header
    assert "STATE" in header


def test_list_columns_line_up(sysfs, capsys):
    add_second_camera(sysfs)

    main(["list"], root=sysfs)

    lines = capsys.readouterr().out.splitlines()
    assert lines[1].index("enabled") == lines[2].index("enabled")


def test_list_lines_have_no_trailing_spaces(sysfs, capsys):
    unbind(sysfs, "3-6:1.0")

    main(["list"], root=sysfs)

    for line in capsys.readouterr().out.splitlines():
        assert line == line.rstrip()


def test_list_explains_video_devices_that_are_not_usb(tmp_path, capsys):
    (tmp_path / "class/video4linux/video0").mkdir(parents=True)

    exit_code = main(["list"], root=tmp_path)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "No USB cameras found" in output
    assert "not USB" in output


def test_list_has_no_extra_note_when_there_are_no_video_devices(tmp_path, capsys):
    main(["list"], root=tmp_path)

    assert "not USB" not in capsys.readouterr().out


def test_list_has_no_extra_note_when_a_usb_camera_is_found(sysfs, capsys):
    (sysfs / "class/video4linux/video9").mkdir(parents=True)

    main(["list"], root=sysfs)

    assert "not USB" not in capsys.readouterr().out


def test_list_json_describes_each_camera(sysfs, capsys):
    exit_code = main(["list", "--json"], root=sysfs)

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "schema_version": 1,
        "cameras": [
            {
                "id": "3-6:1.0",
                "name": "HP Wide Vision HD Camera",
                "usb_id": "0408:5482",
                "state": "enabled",
                "driver": "uvcvideo",
                "nodes": ["/dev/video0", "/dev/video1"],
            }
        ],
    }


def test_list_json_of_a_disabled_camera(sysfs, capsys):
    unbind(sysfs, "3-6:1.0")

    main(["list", "--json"], root=sysfs)

    [camera] = json.loads(capsys.readouterr().out)["cameras"]
    assert camera["state"] == "disabled"
    assert camera["driver"] is None
    assert camera["nodes"] == []


def test_list_json_of_a_camera_used_by_another_driver(sysfs, capsys):
    link = sysfs / "bus/usb/devices/3-6:1.0/driver"
    link.unlink()
    other = sysfs / "bus/usb/drivers/vfio-pci"
    other.mkdir(parents=True)
    link.symlink_to(other)

    main(["list", "--json"], root=sysfs)

    [camera] = json.loads(capsys.readouterr().out)["cameras"]
    assert camera["state"] == "other"
    assert camera["driver"] == "vfio-pci"


def test_list_json_with_no_cameras_is_an_empty_list(tmp_path, capsys):
    exit_code = main(["list", "--json"], root=tmp_path)

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "schema_version": 1,
        "cameras": [],
    }


def test_disable_accepts_part_of_the_camera_name(sysfs):
    exit_code = main(["disable", "wide vision"], root=sysfs)

    assert exit_code == 0
    unbind_file = sysfs / "bus/usb/drivers/uvcvideo/unbind"
    assert unbind_file.read_text() == "3-6:1.0\n"


def test_a_name_in_quotes_can_have_several_words(sysfs, capsys):
    exit_code = main(["status", "HP Wide"], root=sysfs)

    assert exit_code == 0
    assert capsys.readouterr().out.strip() == "enabled"


def test_extra_words_ask_for_quotes(sysfs, capsys):
    exit_code = main(["disable", "HP", "Wide"], root=sysfs)

    assert exit_code == 2
    assert "quotes" in capsys.readouterr().err


def test_extra_words_change_nothing(sysfs, writes):
    main(["disable", "HP", "Wide"], root=sysfs)

    assert writes == []


def test_an_option_the_command_does_not_take_is_named(sysfs, capsys):
    exit_code = main(["enable", "3-6", "--persist"], root=sysfs)

    error = capsys.readouterr().err
    assert exit_code == 2
    assert '"--persist"' in error
    assert "enable" in error
    assert "quotes" not in error


def test_an_unknown_option_changes_nothing(sysfs, writes):
    main(["enable", "3-6", "--persist"], root=sysfs)

    assert writes == []


def test_a_too_short_name_says_why_it_did_not_match(sysfs, capsys):
    exit_code = main(["status", "hp"], root=sysfs)

    assert exit_code == 1
    assert "3 characters" in capsys.readouterr().err


def test_restore_disables_a_camera_on_the_list(sysfs, tmp_path):
    listing = tmp_path / "disabled"
    listing.write_text("3-6:1.0\n")

    exit_code = main(["restore", "3-6:1.0"], root=sysfs, disabled_file=listing)

    assert exit_code == 0
    assert (sysfs / "bus/usb/drivers/uvcvideo/unbind").read_text() == "3-6:1.0\n"


def test_restore_leaves_a_camera_that_is_not_on_the_list(sysfs, tmp_path):
    listing = tmp_path / "disabled"
    listing.write_text("1-2:1.0\n")

    exit_code = main(["restore", "3-6:1.0"], root=sysfs, disabled_file=listing)

    assert exit_code == 0
    assert (sysfs / "bus/usb/drivers/uvcvideo/unbind").read_text() == ""


def test_restore_with_no_list_file_does_nothing(sysfs, tmp_path):
    exit_code = main(
        ["restore", "3-6:1.0"], root=sysfs, disabled_file=tmp_path / "missing"
    )

    assert exit_code == 0
    assert (sysfs / "bus/usb/drivers/uvcvideo/unbind").read_text() == ""


def test_restore_ignores_a_listed_camera_that_is_gone(sysfs, tmp_path):
    listing = tmp_path / "disabled"
    listing.write_text("9-9:1.0\n")

    exit_code = main(["restore", "9-9:1.0"], root=sysfs, disabled_file=listing)

    assert exit_code == 0
    assert (sysfs / "bus/usb/drivers/uvcvideo/unbind").read_text() == ""


def test_restore_is_fine_when_the_camera_is_already_off(sysfs, tmp_path):
    unbind(sysfs, "3-6:1.0")
    listing = tmp_path / "disabled"
    listing.write_text("3-6:1.0\n")

    exit_code = main(["restore", "3-6:1.0"], root=sysfs, disabled_file=listing)

    assert exit_code == 0
    assert (sysfs / "bus/usb/drivers/uvcvideo/unbind").read_text() == ""


UNBIND = "bus/usb/drivers/uvcvideo/unbind"
BIND = "bus/usb/drivers/uvcvideo/bind"


def test_restore_keeps_the_camera_on_the_list(sysfs, tmp_path):
    listing = tmp_path / "disabled"
    listing.write_text("3-6:1.0\n")

    main(["restore", "3-6:1.0"], root=sysfs, disabled_file=listing)

    assert persist.load(listing) == ["3-6:1.0"]


def test_disable_persist_unbinds_and_adds_to_the_list(sysfs, tmp_path):
    listing = tmp_path / "disabled"

    exit_code = main(
        ["disable", "3-6:1.0", "--persist"], root=sysfs, disabled_file=listing
    )

    assert exit_code == 0
    assert (sysfs / UNBIND).read_text() == "3-6:1.0\n"
    assert persist.load(listing) == ["3-6:1.0"]


def test_disable_without_persist_leaves_the_list_alone(sysfs, tmp_path):
    listing = tmp_path / "disabled"

    exit_code = main(["disable", "3-6:1.0"], root=sysfs, disabled_file=listing)

    assert exit_code == 0
    assert not listing.exists()


def test_disable_persist_on_an_already_disabled_camera_still_lists_it(sysfs, tmp_path):
    unbind(sysfs, "3-6:1.0")
    listing = tmp_path / "disabled"

    exit_code = main(
        ["disable", "3-6:1.0", "--persist"], root=sysfs, disabled_file=listing
    )

    assert exit_code == 0
    assert (sysfs / UNBIND).read_text() == ""
    assert persist.load(listing) == ["3-6:1.0"]


def test_disable_persist_does_not_list_a_camera_it_could_not_disable(sysfs, tmp_path):
    link = sysfs / "bus/usb/devices/3-6:1.0/driver"
    link.unlink()
    other = sysfs / "bus/usb/drivers/vfio-pci"
    other.mkdir(parents=True)
    link.symlink_to(other)
    listing = tmp_path / "disabled"

    exit_code = main(
        ["disable", "3-6:1.0", "--persist"], root=sysfs, disabled_file=listing
    )

    assert exit_code == 1
    assert not listing.exists()


def test_disable_all_persist_lists_every_camera(sysfs, tmp_path):
    add_device(sysfs, "1-2", "046d", "0825", "Logitech", "Webcam C270")
    add_interface(sysfs, "1-2:1.0", "0e", "01", "uvcvideo", nodes=("video2",))
    listing = tmp_path / "disabled"

    exit_code = main(
        ["disable", "--all", "--persist"], root=sysfs, disabled_file=listing
    )

    assert exit_code == 0
    assert sorted(persist.load(listing)) == ["1-2:1.0", "3-6:1.0"]


def test_disable_persist_reports_a_list_that_cannot_be_written(
    sysfs, tmp_path, capsys, monkeypatch
):
    def refuse(path, camera_id):
        raise PermissionError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(persist, "add", refuse)

    exit_code = main(
        ["disable", "3-6:1.0", "--persist"],
        root=sysfs,
        disabled_file=tmp_path / "disabled",
    )

    assert exit_code == 1
    assert (sysfs / UNBIND).read_text() == "3-6:1.0\n"
    assert "sudo" in capsys.readouterr().err


def test_enable_removes_the_camera_from_the_list(sysfs, tmp_path):
    unbind(sysfs, "3-6:1.0")
    listing = tmp_path / "disabled"
    listing.write_text("3-6:1.0\n1-2:1.0\n")

    exit_code = main(["enable", "3-6:1.0"], root=sysfs, disabled_file=listing)

    assert exit_code == 0
    assert (sysfs / BIND).read_text() == "3-6:1.0\n"
    assert persist.load(listing) == ["1-2:1.0"]


def test_enable_removes_the_camera_even_if_it_is_already_on(sysfs, tmp_path):
    listing = tmp_path / "disabled"
    listing.write_text("3-6:1.0\n")

    exit_code = main(["enable", "3-6:1.0"], root=sysfs, disabled_file=listing)

    assert exit_code == 0
    assert persist.load(listing) == []


def test_enable_forgets_the_camera_before_binding_it(sysfs, tmp_path, monkeypatch):
    unbind(sysfs, "3-6:1.0")
    listing = tmp_path / "disabled"
    listing.write_text("3-6:1.0\n")
    seen = []

    def spy(path, text):
        seen.append(persist.load(listing))

    monkeypatch.setattr(uvc, "write", spy)

    main(["enable", "3-6:1.0"], root=sysfs, disabled_file=listing)

    assert seen == [[]]


def test_toggling_a_camera_on_removes_it_from_the_list(sysfs, tmp_path):
    unbind(sysfs, "3-6:1.0")
    listing = tmp_path / "disabled"
    listing.write_text("3-6:1.0\n")

    exit_code = main(["toggle", "3-6:1.0"], root=sysfs, disabled_file=listing)

    assert exit_code == 0
    assert persist.load(listing) == []

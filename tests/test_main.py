from fakesys import unbind

from campermit.__main__ import main


def test_main_print_version_and_returns_zero(capsys):
    exit_code = main([])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert output.startswith("campermit")


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
